import discord
from discord.ext import commands
from googletrans import Translator
from gtts import gTTS
import os
import asyncio
from collections import deque
from typing import Dict, Optional, List
import logging
import re
import langdetect
from langdetect import detect

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

# Constants for allowed server and channel
ALLOWED_SERVER_ID = 1214430768143671377  # Replace with your server ID
ALLOWED_CHANNEL_ID = 1351381443812655317  # Replace with your channel ID

class AudioQueue:
    def __init__(self):
        self.queue = deque()
        self.is_playing = False

    async def add_to_queue(self, audio_file: str, message: discord.Message):
        self.queue.append((audio_file, message))
        
    def get_next(self) -> Optional[tuple]:
        return self.queue.popleft() if self.queue else None

class TranslationVoice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.translator = Translator()
        self.audio_queues: Dict[int, AudioQueue] = {}
        self.active_vc: Dict[int, discord.VoiceClient] = {}
        self.audio_folder = 'temp_audio'
        
        # Create audio folder if it doesn't exist
        os.makedirs(self.audio_folder, exist_ok=True)

    def get_audio_file_path(self, message_id: int) -> str:
        return os.path.join(self.audio_folder, f'translated_{message_id}.mp3')

    async def cleanup_audio_file(self, file_path: str):
        try:
            if os.path.exists(file_path):
                await asyncio.sleep(0.1)  # Small delay to ensure file is closed
                os.remove(file_path)
        except Exception as e:
            logging.error(f"Error cleaning up audio file: {e}")

    async def play_next(self, guild_id: int):
        if guild_id not in self.audio_queues:
            return

        queue = self.audio_queues[guild_id]
        if not queue.queue:
            queue.is_playing = False
            return

        if guild_id not in self.active_vc or not self.active_vc[guild_id].is_connected():
            queue.is_playing = False
            return

        next_item = queue.get_next()
        if next_item:
            audio_file, message = next_item
            vc = self.active_vc[guild_id]
            
            def after_playing(error):
                if error:
                    logging.error(f"Error playing audio: {error}")
                
                # Schedule cleanup and next play
                asyncio.run_coroutine_threadsafe(
                    self.cleanup_and_continue(audio_file, guild_id),
                    self.bot.loop
                )

            try:
                if os.path.exists(audio_file):
                    vc.play(discord.FFmpegPCMAudio(audio_file), after=after_playing)
                else:
                    logging.error(f"Audio file not found: {audio_file}")
                    await self.play_next(guild_id)
            except Exception as e:
                logging.error(f"Error starting playback: {e}")
                await self.cleanup_audio_file(audio_file)
                await self.play_next(guild_id)

    async def cleanup_and_continue(self, audio_file: str, guild_id: int):
        """Helper method to cleanup and continue playback"""
        await self.cleanup_audio_file(audio_file)
        await self.play_next(guild_id)

    def generate_audio(self, text: str, file_path: str, lang: str):
        """Generate audio file using gTTS with the appropriate language"""
        try:
            # Limit text length to avoid gTTS issues
            if len(text) > 500:
                text = text[:497] + "..."
            
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(file_path)
            return True
        except Exception as e:
            logging.error(f"Error generating audio: {e}")
            return False

    def detect_language_improved(self, text: str) -> str:
        """Improved language detection using langdetect library"""
        try:
            # Remove URLs, mentions, and special characters
            clean_text = re.sub(r'http\S+|@\S+|<@\S+>|[^\w\s]', '', text.lower())
            
            if len(clean_text.strip()) < 3:
                return 'en'  # Default to English for very short text
            
            detected = detect(clean_text)
            
            # Only support English and Spanish
            if detected == 'es':
                return 'es'
            else:
                return 'en'
        except:
            # Fallback to simple detection
            return self.detect_language_simple(text)

    def detect_language_simple(self, text: str) -> str:
        """Simple fallback language detection"""
        es_words = ['el', 'la', 'los', 'las', 'un', 'una', 'y', 'o', 'pero', 'porque', 'como', 
                   'qué', 'quién', 'cuándo', 'dónde', 'por qué', 'sí', 'no', 'muy', 'más', 
                   'aquí', 'allí', 'con', 'sin', 'para', 'por', 'en', 'de', 'del', 'al']
        
        clean_text = re.sub(r'[^\w\s]', '', text.lower())
        words = clean_text.split()
        
        if not words:
            return 'en'
        
        spanish_count = sum(1 for word in words if word in es_words)
        
        if spanish_count / len(words) >= 0.15:
            return 'es'
        return 'en'

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore messages from bots or in threads
        if message.author.bot or isinstance(message.channel, discord.Thread):
            return
            
        # Ignore if message is a command
        ctx = await self.bot.get_context(message)
        if ctx.valid:
            return

        # Ignore empty messages or very short messages
        if not message.content.strip() or len(message.content.strip()) < 2:
            return

        # Check if the message is in the allowed server and channel
        if message.guild.id != ALLOWED_SERVER_ID or message.channel.id != ALLOWED_CHANNEL_ID:
            return

        try:
            # Detect language of the message
            detected_lang = self.detect_language_improved(message.content)
            
            # Set target language based on detected language
            target_lang = 'es' if detected_lang == 'en' else 'en'
            
            # Translate the message with retry logic
            translated = None
            max_retries = 3
            
            for attempt in range(max_retries):
                try:
                    translated = await self.bot.loop.run_in_executor(
                        None,
                        lambda: self.translator.translate(message.content, src=detected_lang, dest=target_lang)
                    )
                    break
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise e
                    await asyncio.sleep(1)  # Wait before retry
            
            if not translated or not translated.text:
                raise Exception("Translation returned empty result")
            
            # Generate audio file with appropriate voice
            audio_file = self.get_audio_file_path(message.id)
            audio_success = await self.bot.loop.run_in_executor(
                None,
                lambda: self.generate_audio(translated.text, audio_file, target_lang)
            )

            # Handle voice channel connection
            if message.author.voice and message.author.voice.channel and audio_success:
                guild_id = message.guild.id
                
                # Initialize queue if needed
                if guild_id not in self.audio_queues:
                    self.audio_queues[guild_id] = AudioQueue()

                # Connect to voice if not already connected
                if guild_id not in self.active_vc or not self.active_vc[guild_id].is_connected():
                    try:
                        vc = await message.author.voice.channel.connect()
                        self.active_vc[guild_id] = vc
                    except Exception as e:
                        logging.error(f"Error connecting to voice: {e}")
                        await self.cleanup_audio_file(audio_file)
                        # Don't return here, still send text translation

                # Add to queue and start playing if not already playing
                if guild_id in self.active_vc and self.active_vc[guild_id].is_connected():
                    queue = self.audio_queues[guild_id]
                    await queue.add_to_queue(audio_file, message)
                    
                    if not queue.is_playing:
                        queue.is_playing = True
                        await self.play_next(guild_id)

            # Send text translation with appropriate flag
            flag = '🇪🇸' if target_lang == 'es' else '🇺🇸'
            source_flag = '🇺🇸' if detected_lang == 'en' else '🇪🇸'
            
            await message.channel.send(
                f"{source_flag} **Original:** {message.content}\n"
                f"{flag} **Translated:** {translated.text}"
            )

        except Exception as e:
            logging.error(f"Translation error: {e}")
            await message.channel.send("⚠️ Translation failed. Please try again later.")
            await self.cleanup_audio_file(self.get_audio_file_path(message.id))

    @commands.command()
    async def leave(self, ctx):
        """Command to make the bot leave the voice channel"""
        guild_id = ctx.guild.id
        if guild_id in self.active_vc and self.active_vc[guild_id].is_connected():
            await self.active_vc[guild_id].disconnect()
            del self.active_vc[guild_id]
            if guild_id in self.audio_queues:
                # Clear queue and cleanup remaining audio files
                queue = self.audio_queues[guild_id]
                while queue.queue:
                    audio_file, _ = queue.get_next()
                    await self.cleanup_audio_file(audio_file)
                del self.audio_queues[guild_id]
            await ctx.send("👋 Left the voice channel.")
        else:
            await ctx.send("❌ Not connected to any voice channel.")
            
    @commands.command(name='translator_help')
    async def translator_help(self, ctx):
        """Display help information for the translator"""
        embed = discord.Embed(
            title="Translation Bot Help",
            description="This bot automatically translates messages between English and Spanish!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="How it works",
            value="Just type messages in English or Spanish, and the bot will automatically translate them and speak the translation if you're in a voice channel.",
            inline=False
        )
        
        embed.add_field(
            name="Commands",
            value="**/leave** - Make the bot leave the voice channel\n"
                  "**/translator_help** - Show this help message",
            inline=False
        )
        
        embed.add_field(
            name="Requirements",
            value="• Join a voice channel before sending messages to hear translations\n"
                  "• Bot works only in designated channels\n"
                  "• Supports English ↔ Spanish translation",
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(TranslationVoice(bot))
