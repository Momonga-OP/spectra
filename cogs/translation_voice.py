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

    def generate_audio(self, text: str, file_path: str, lang: str):
        """Generate audio file using gTTS with the appropriate language"""
        try:
            tts = gTTS(text=text, lang=lang, slow=False)
            tts.save(file_path)
        except Exception as e:
            logging.error(f"Error generating audio: {e}")
            raise

    def detect_language(self, text: str) -> str:
        """Detect if text is primarily English or Spanish"""
        # Simple detection based on common words
        es_words = ['el', 'la', 'los', 'las', 'un', 'una', 'y', 'o', 'pero', 'porque', 'como', 'qué', 'quién', 'cuándo', 'dónde', 'por qué']
        
        # Clean the text and convert to lowercase
        clean_text = re.sub(r'[^\w\s]', '', text.lower())
        words = clean_text.split()
        
        # Count Spanish words
        spanish_count = sum(1 for word in words if word in es_words)
        
        # If at least 20% of words are Spanish markers, consider it Spanish
        if spanish_count / max(len(words), 1) >= 0.2:
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

        # Ignore empty messages
        if not message.content.strip():
            return

        try:
            # Detect language of the message
            detected_lang = self.detect_language(message.content)
            
            # Set target language based on detected language
            target_lang = 'es' if detected_lang == 'en' else 'en'
            
            # Translate the message
            translated = await self.bot.loop.run_in_executor(
                None,
                lambda: self.translator.translate(message.content, src=detected_lang, dest=target_lang)
            )
            
            # Generate audio file with appropriate voice
            audio_file = self.get_audio_file_path(message.id)
            await self.bot.loop.run_in_executor(
                None,
                lambda: self.generate_audio(translated.text, audio_file, target_lang)
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
                        return

                # Add to queue and start playing if not already playing
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
                del self.audio_queues[guild_id]
            await ctx.send("👋 Left the voice channel.")
            
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
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(TranslationVoice(bot))
