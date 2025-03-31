import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('music_cog')

BOT_OWNER_ID = 486652069831376943  # Only you can upload music
MUSIC_FILE = "music.mp3"  # Temporary storage for the uploaded file

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_clients = {}  # Store voice clients per guild
        self.currently_playing = False
        self.music_task = None

    @app_commands.command(name="music", description="Plays music in all servers where Spectra is in.")
    async def music(self, interaction: discord.Interaction):
        if interaction.user.id != BOT_OWNER_ID:
            return await interaction.response.send_message("You are not allowed to use this command!", ephemeral=True)
        
        await interaction.response.send_message("Please upload an MP3 file in DMs to broadcast.", ephemeral=True)
        
        # Create DM channel
        try:
            dm_channel = await interaction.user.create_dm()
            await dm_channel.send("Upload an MP3 file to start playing in all servers.")
        except Exception as e:
            logger.error(f"Failed to create DM: {e}")
            return
        
        # Wait for file upload
        def check(msg):
            return (msg.channel.type == discord.ChannelType.private and 
                   msg.author.id == BOT_OWNER_ID and 
                   msg.attachments and 
                   msg.attachments[0].filename.lower().endswith(".mp3"))

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=120)
            
            # Stop any existing playback
            await self.stop_all_playback()
            
            # Save the new file
            await dm_channel.send("Downloading music file...")
            await msg.attachments[0].save(MUSIC_FILE)
            await dm_channel.send(f"Music file '{msg.attachments[0].filename}' downloaded! Starting playback in all servers.")
            
            # Start global playback
            self.music_task = self.bot.loop.create_task(self.start_global_playback())
            
        except asyncio.TimeoutError:
            await dm_channel.send("Music upload timed out. Please try again.")
        except Exception as e:
            logger.error(f"Error in music command: {e}")
            await dm_channel.send(f"An error occurred: {str(e)}")

    async def stop_all_playback(self):
        """Stop playback in all voice clients and disconnect"""
        if self.music_task and not self.music_task.done():
            self.music_task.cancel()
            
        for guild_id, voice_client in list(self.voice_clients.items()):
            try:
                if voice_client.is_playing():
                    voice_client.stop()
                await voice_client.disconnect(force=True)
            except Exception as e:
                logger.error(f"Error disconnecting from guild {guild_id}: {e}")
            finally:
                self.voice_clients.pop(guild_id, None)
        
        self.currently_playing = False
    
    async def start_global_playback(self):
        """Start music playback in all available servers"""
        if not os.path.exists(MUSIC_FILE):
            logger.error("Music file not found!")
            return
        
        logger.info(f"Starting global playback in {len(self.bot.guilds)} servers")
        connection_tasks = []
        
        # Connect to all servers simultaneously
        for guild in self.bot.guilds:
            connection_tasks.append(self.connect_to_guild(guild))
        
        # Wait for all connections to complete
        await asyncio.gather(*connection_tasks, return_exceptions=True)
        
        # Set playback flag
        self.currently_playing = True
        
        # Log connection results
        connected_count = len(self.voice_clients)
        total_guilds = len(self.bot.guilds)
        logger.info(f"Connected to {connected_count}/{total_guilds} servers")
        
        # Start playback loops for all connected voice clients
        playback_tasks = []
        for guild_id, voice_client in self.voice_clients.items():
            playback_tasks.append(self.loop_music(guild_id, voice_client))
        
        # Keep all playback tasks running
        if playback_tasks:
            await asyncio.gather(*playback_tasks, return_exceptions=True)

    async def connect_to_guild(self, guild):
        """Connect to the first available voice channel in the guild"""
        if guild.id in self.voice_clients:
            return  # Already connected
        
        try:
            # Find an accessible voice channel
            for voice_channel in guild.voice_channels:
                permissions = voice_channel.permissions_for(guild.me)
                if permissions.connect and permissions.speak:
                    voice_client = await voice_channel.connect(timeout=10, reconnect=True)
                    self.voice_clients[guild.id] = voice_client
                    logger.info(f"Connected to '{voice_channel.name}' in '{guild.name}'")
                    return
            
            logger.warning(f"No accessible voice channel found in '{guild.name}'")
        except Exception as e:
            logger.error(f"Failed to connect to a voice channel in '{guild.name}': {e}")

    async def loop_music(self, guild_id, voice_client):
        """Loop music playback indefinitely for a specific voice client"""
        guild = self.bot.get_guild(guild_id)
        guild_name = guild.name if guild else f"Unknown ({guild_id})"
        
        logger.info(f"Starting music loop for '{guild_name}'")
        
        while self.currently_playing and voice_client.is_connected():
            try:
                if not voice_client.is_playing():
                    # Start playback
                    logger.debug(f"Starting/restarting playback in '{guild_name}'")
                    voice_client.play(
                        discord.FFmpegPCMAudio(MUSIC_FILE), 
                        after=lambda e: logger.debug(f"Playback finished in '{guild_name}': {e}" if e else "Playback finished")
                    )
                await asyncio.sleep(2)  # Check every 2 seconds
                
            except discord.errors.ClientException as e:
                logger.error(f"ClientException in '{guild_name}': {e}")
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in music loop for '{guild_name}': {e}")
                break
                
        logger.info(f"Music loop ended for '{guild_name}'")

    def cog_unload(self):
        """Clean up when cog is unloaded"""
        if self.music_task:
            self.music_task.cancel()
        asyncio.create_task(self.stop_all_playback())

async def setup(bot):
    await bot.add_cog(Music(bot))
