# Standard library imports
import os
import asyncio
import logging
import random
import tempfile
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
from typing import Optional, Set, Dict, List, Tuple
from dataclasses import dataclass  # Import the dataclass decorator

# Third-party imports
import discord
from discord.ext import commands
from gtts import gTTS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class WelcomeConfig:
    """Configuration class for welcome messages"""
    messages: List[str]
    language: str
    name_only_messages: List[str]  # Messages for frequent rejoins

@dataclass
class UserJoinInfo:
    """Tracks user join patterns"""
    last_welcome: datetime
    join_count: int
    last_join: datetime

class RateLimiter:
    """Handles rate limiting for welcome messages"""
    def __init__(self, cooldown_minutes: int = 30, rejoin_threshold: int = 3,
                 rejoin_window_minutes: int = 10):
        self.cooldown = timedelta(minutes=cooldown_minutes)
        self.rejoin_threshold = rejoin_threshold
        self.rejoin_window = timedelta(minutes=rejoin_window_minutes)
        self.user_joins: Dict[Tuple[int, int], UserJoinInfo] = {}
        logger.info(f"RateLimiter initialized with {cooldown_minutes}min cooldown, "
                   f"{rejoin_threshold} rejoin threshold")

    def should_welcome(self, guild_id: int, user_id: int) -> Tuple[bool, bool]:
        """
        Returns (should_welcome, name_only)
        name_only is True if user should get name-only welcome due to frequent rejoins
        """
        key = (guild_id, user_id)
        now = datetime.now()
        
        if key not in self.user_joins:
            self.user_joins[key] = UserJoinInfo(
                last_welcome=now,
                join_count=1,
                last_join=now
            )
            logger.debug(f"New user join tracked for Guild:{guild_id} User:{user_id}")
            return True, False

        user_info = self.user_joins[key]
        
        # Reset join count if outside rejoin window
        if now - user_info.last_join > self.rejoin_window:
            user_info.join_count = 0
            logger.debug(f"Reset join count for Guild:{guild_id} User:{user_id}")
        
        user_info.join_count += 1
        user_info.last_join = now

        # Check if we're still in cooldown period
        if now - user_info.last_welcome < self.cooldown:
            if user_info.join_count >= self.rejoin_threshold:
                logger.info(f"Name-only welcome for frequent rejoin User:{user_id}")
                return True, True
            logger.debug(f"User:{user_id} in cooldown period")
            return False, False

        # Update last welcome time and reset join count
        user_info.last_welcome = now
        return True, False

    def cleanup_old_entries(self, max_age_hours: int = 24):
        """Remove old entries to prevent memory leaks"""
        now = datetime.now()
        max_age = timedelta(hours=max_age_hours)
        
        old_count = len(self.user_joins)
        self.user_joins = {
            key: info for key, info in self.user_joins.items()
            if now - info.last_join < max_age
        }
        removed = old_count - len(self.user_joins)
        if removed > 0:
            logger.info(f"Cleaned up {removed} old rate limit entries")

class VoiceManager:
    """Handles voice-related operations"""
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "discord_bot_audio"
        self.temp_dir.mkdir(exist_ok=True)
        self.audio_cache: Dict[str, Path] = {}
        logger.info(f"VoiceManager initialized with temp directory: {self.temp_dir}")

    async def create_welcome_audio(self, text: str, lang: str = 'en') -> Path:
        """Creates and saves TTS audio file with caching"""
        cache_key = f"{text}_{lang}"
        
        if cache_key in self.audio_cache and self.audio_cache[cache_key].exists():
            logger.debug(f"Using cached audio for: {text[:20]}...")
            return self.audio_cache[cache_key]

        try:
            tts = gTTS(text=text, lang=lang)
            temp_file = self.temp_dir / f"welcome_{hash(text)}_{lang}.mp3"
            tts.save(str(temp_file))
            self.audio_cache[cache_key] = temp_file
            logger.debug(f"Created new audio file: {temp_file.name}")
            return temp_file
        except Exception as e:
            logger.error(f"Failed to create TTS audio: {e}")
            raise

    async def play_audio(self, voice_client: discord.VoiceClient, audio_path: Path) -> None:
        """Plays audio file in voice channel"""
        if not voice_client or not voice_client.is_connected():
            raise ValueError("Voice client is not connected")

        try:
            audio_source = discord.FFmpegPCMAudio(str(audio_path))
            if voice_client.is_playing():
                voice_client.stop()
            
            voice_client.play(audio_source)
            logger.debug(f"Started playing audio: {audio_path.name}")
            
            while voice_client.is_playing():
                await asyncio.sleep(0.1)
            
            logger.debug("Finished playing audio")
            
        except Exception as e:
            logger.error(f"Error playing audio: {e}")
            raise

    def cleanup_cache(self, max_files: int = 50):
        """Cleanup old cached audio files"""
        if len(self.audio_cache) > max_files:
            files_to_remove = list(self.audio_cache.items())[:-max_files]
            for key, path in files_to_remove:
                if path.exists():
                    path.unlink()
                del self.audio_cache[key]
            logger.info(f"Cleaned up {len(files_to_remove)} cached audio files")

class Voice(commands.Cog):
    """Voice Channel Welcome Bot"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_manager = VoiceManager()
        self.blocked_users: Dict[int, Set[int]] = {}
        self.rate_limiter = RateLimiter()
        self.active_connections: Set[int] = set()  # Track active voice connections
        
        # Server-specific configurations
        self.welcome_configs = {
            1300093554064097400: WelcomeConfig(  # French server
                messages=[
                    "Bonjour {name}! Ravi de vous avoir parmi nous.",
                    "Bienvenue, {name}! Nous espérons que vous passerez un bon moment.",
                    "Salut {name}! Bienvenue dans notre communauté!"
                ],
                language='fr',
                name_only_messages=[
                    "{name} est de retour!",
                    "{name} nous rejoint à nouveau.",
                ]
            ),
            None: WelcomeConfig(  # Default English config
                messages=[
                    "Hello there! Glad you could join us, {name}!",
                    "Welcome, {name}! We hope you have a great time!",
                    "Hi {name}! Welcome to our community!"
                ],
                language='en',
                name_only_messages=[
                    "{name} is back!",
                    "{name} has returned.",
                ]
            )
        }

        # Start cleanup tasks
        self.cleanup_task = bot.loop.create_task(self._periodic_cleanup())
        logger.info("Voice Cog initialized")

    async def _periodic_cleanup(self):
        """Periodically clean up caches and old data"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                self.rate_limiter.cleanup_old_entries()
                self.voice_manager.cleanup_cache()
                logger.info("Performed periodic cleanup")
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")

    async def connect_to_channel(self, channel: discord.VoiceChannel, 
                           retries: int = 3, delay: float = 5) -> Optional[discord.VoiceClient]:
        """Enhanced connect to voice channel with retry logic"""
        if not isinstance(channel, discord.VoiceChannel):
            logger.error(f"Invalid channel type: {type(channel)}")
            return None
            
        if channel.guild.id in self.active_connections:
            logger.debug(f"Already connected to guild {channel.guild.id}")
            return None

        # Get guild's voice region if available
        voice_region = getattr(channel.guild, 'region', 'us-central')
        logger.info(f"Attempting connection to {channel.id} in region: {voice_region}")

        for attempt in range(retries):
            try:
                logger.info(f"Connecting to voice channel {channel.id} (attempt {attempt + 1})")
                
                # Verify permissions
                perms = channel.permissions_for(channel.guild.me)
                if not all([perms.connect, perms.speak]):
                    logger.error(f"Missing permissions in channel {channel.id}: Connect={perms.connect}, Speak={perms.speak}")
                    return None
                    
                # Force new voice connection with specified region
                voice_client = await channel.connect(
                    timeout=20.0, 
                    reconnect=True,
                    self_deaf=True
                )
                
                # Workaround for connection issues
                await asyncio.sleep(1)  # Brief pause after connection
                
                if not voice_client.is_connected():
                    raise ConnectionError("Voice client failed to establish connection")
                    
                self.active_connections.add(channel.guild.id)
                return voice_client
                
            except discord.ClientException as e:
                if "Already connected" in str(e):
                    return None
                logger.error(f"ClientException during connection: {e}")
                raise
            except asyncio.TimeoutError:
                logger.warning(f"Timeout connecting to channel {channel.id}")
            except Exception as e:
                logger.error(f"Connection attempt {attempt + 1}/{retries} failed: {type(e).__name__}: {e}")
                if attempt < retries - 1:
                    await asyncio.sleep(delay * (attempt + 1))
                else:
                    logger.error(f"Failed to connect after {retries} attempts")
                    raise
        return None

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, 
                                  before: discord.VoiceState, 
                                  after: discord.VoiceState):
        """Enhanced voice state update handler with rate limiting"""
        if not self._should_welcome_member(member, before, after):
            return

        guild_id = member.guild.id
        should_welcome, name_only = self.rate_limiter.should_welcome(guild_id, member.id)
        
        if not should_welcome:
            logger.debug(f"Skipping welcome for {member.name} (rate limited)")
            return

        config = self.welcome_configs.get(guild_id, self.welcome_configs[None])
        
        try:
            logger.info(f"Preparing welcome for {member.name} in guild {guild_id}")
            vc = await self.connect_to_channel(after.channel)
            if not vc:
                return

            welcome_text = self._get_welcome_message(member.name, config, name_only)
            audio_file = await self.voice_manager.create_welcome_audio(
                welcome_text, 
                config.language
            )
            
            await self.voice_manager.play_audio(vc, audio_file)
            
        except Exception as e:
            logger.error(f"Error in welcome sequence: {e}")
        finally:
            if vc and vc.is_connected():
                await vc.disconnect()
                self.active_connections.remove(guild_id)
                logger.debug(f"Disconnected from guild {guild_id}")

    def _should_welcome_member(self, member: discord.Member, 
                             before: discord.VoiceState, 
                             after: discord.VoiceState) -> bool:
        """Determines if member should receive welcome message"""
        return (
            before.channel is None and 
            after.channel is not None and
            not member.bot and
            member.id not in self.blocked_users.get(member.guild.id, set())
        )

    def _get_welcome_message(self, member_name: str, config: WelcomeConfig, 
                           name_only: bool = False) -> str:
        """Generates welcome message from config"""
        messages = config.name_only_messages if name_only else config.messages
        message_template = random.choice(messages)
        return message_template.format(name=member_name)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def toggle_welcome(self, ctx: commands.Context, member: discord.Member):
        """Toggles welcome messages for a specific user"""
        guild_id = ctx.guild.id
        if guild_id not in self.blocked_users:
            self.blocked_users[guild_id] = set()

        if member.id in self.blocked_users[guild_id]:
            self.blocked_users[guild_id].remove(member.id)
            await ctx.send(f"Welcome messages enabled for {member.name}")
            logger.info(f"Enabled welcome messages for {member.name} in guild {guild_id}")
        else:
            self.blocked_users[guild_id].add(member.id)
            await ctx.send(f"Welcome messages disabled for {member.name}")
            logger.info(f"Disabled welcome messages for {member.name} in guild {guild_id}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def set_cooldown(self, ctx: commands.Context, minutes: int):
        """Sets the cooldown time for welcome messages"""
        if minutes < 1:
            await ctx.send("Cooldown time must be at least 1 minute")
            return
        
        self.rate_limiter.cooldown = timedelta(minutes=minutes)
        await ctx.send(f"Welcome message cooldown set to {minutes} minutes")
        logger.info(f"Cooldown set to {minutes} minutes in guild {ctx.guild.id}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def welcome_status(self, ctx: commands.Context):
        """Shows current welcome message settings"""
        guild_id = ctx.guild.id
        blocked_count = len(self.blocked_users.get(guild_id, set()))
        cooldown_mins = self.rate_limiter.cooldown.total_seconds() / 60
        
        status = (
            f"🔊 Welcome Status for {ctx.guild.name}:\n"
            f"• Cooldown: {cooldown_mins:.0f} minutes\n"
            f"• Blocked Users: {blocked_count}\n"
            f"• Active Voice Connection: {'Yes' if guild_id in self.active_connections else 'No'}\n"
            f"• Language: {self.welcome_configs.get(guild_id, self.welcome_configs[None]).language}"
        )
        await ctx.send(status)

    async def cog_unload(self):
        """Cleanup when cog is unloaded"""
        logger.info("Unloading Voice cog...")
        
        # Cancel cleanup task
        if hasattr(self, 'cleanup_task'):
            self.cleanup_task.cancel()
            
        # Disconnect from voice channels
        for vc in self.bot.voice_clients:
            if vc.is_connected():
                await vc.disconnect()
        
        # Cleanup temporary files
        if hasattr(self, 'voice_manager'):
            temp_dir = self.voice_manager.temp_dir
            if temp_dir.exists():
                for file in temp_dir.glob("*.mp3"):
                    file.unlink(missing_ok=True)
                temp_dir.rmdir()
        
        logger.info("Voice cog unloaded successfully")

async def setup(bot: commands.Bot):
    """Adds the Voice cog to the bot"""
    await bot.add_cog(Voice(bot))
    logger.info("Voice cog loaded successfully")
