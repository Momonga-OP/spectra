import discord
from discord.ext import commands
from googletrans import Translator
import pyttsx3
import os
import asyncio
from collections import deque
from typing import Dict, Optional
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

class AudioQueue:
    def __init__(self):
        self.queue = deque()
        self.current_playing = None
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
        self.text_channel_id = 1258426636496404510  # Your channel ID here
        self.target_language = 'fr'
        self.audio_folder = 'temp_audio'
        self.setup_voice_engine()
        
        # Create audio folder if it doesn't exist
        os.makedirs(self.audio_folder, exist_ok=True)

    def setup_voice_engine(self):
        """Initialize the pyttsx3 engine with male voice"""
        self.engine = pyttsx3.init()
        voices = self.engine.getProperty('voices')
        # Set male voice (usually index 0)
        self.engine.setProperty('voice', voices[0].id)
        # Adjust speed and volume as needed
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 0.9)

    def get_audio_file_path(self, message_id: int) -> str:
        return os.path.join(self.audio_folder, f'translated_{message_id}.mp3')

    async def cleanup_audio_file(self, file_path: str):
        try:
            if os.path.exists(file_path):
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
                asyncio.run_coroutine_threadsafe(
                    self.cleanup_audio_file(audio_file),
                    self.bot.loop
                )
                asyncio.run_coroutine_threadsafe(
                    self.play_next(guild_id),
                    self.bot.loop
                )

            try:
                vc.play(discord.FFmpegPCMAudio(audio_file), after=after_playing)
            except Exception as e:
                logging.error(f"Error starting playback: {e}")
                await self.play_next(guild_id)

    def generate_audio(self, text: str, file_path: str):
        """Generate audio file using pyttsx3"""
        try:
            self.engine.save_to_file(text, file_path)
            self.engine.runAndWait()
        except Exception as e:
            logging.error(f"Error generating audio: {e}")
            raise

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or message.channel.id != self.text_channel_id:
            return

        try:
            # Translate the message
            translated = await self.bot.loop.run_in_executor(
                None,
                lambda: self.translator.translate(message.content, src='auto', dest=self.target_language)
            )
            
            # Generate audio file with male voice
            audio_file = self.get_audio_file_path(message.id)
            await self.bot.loop.run_in_executor(
                None,
                lambda: self.generate_audio(translated.text, audio_file)
            )

            # Handle voice channel connection
            if message.author.voice and message.author.voice.channel:
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
                        raise

                # Add to queue and start playing if not already playing
                queue = self.audio_queues[guild_id]
                await queue.add_to_queue(audio_file, message)
                
                if not queue.is_playing:
                    queue.is_playing = True
                    await self.play_next(guild_id)

            # Send text translation
            flag = '🇫🇷' if self.target_language == 'fr' else '🌐'
            await message.channel.send(
                f"{flag} **Original:** {message.content}\n"
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
                del self.audio_queues[guild_id]
            await ctx.send("👋 Left the voice channel.")

async def setup(bot):
    await bot.add_cog(TranslationVoice(bot))
