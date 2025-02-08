import discord
from discord.ext import commands
from googletrans import Translator
from gtts import gTTS
import os
import asyncio

class TranslationVoice(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.translator = Translator()
        self.audio_file = "translated.mp3"
        self.active_vc = {}  # Track active voice connections per guild
        self.text_channel_id = 1258426636496404510  # Set your text channel ID

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.channel.id != self.text_channel_id:
            return  # Ignore bot messages and non-targeted channels

        try:
            # Translate to French
            translated_text = self.translator.translate(message.content, src="en", dest="fr").text
            tts = gTTS(translated_text, lang="fr")
            tts.save(self.audio_file)

            # Check if user is in a voice channel
            if message.author.voice and message.author.voice.channel:
                voice_channel = message.author.voice.channel
                guild_id = message.guild.id

                # Prevent multiple connections in the same server
                if guild_id in self.active_vc and self.active_vc[guild_id].is_connected():
                    vc = self.active_vc[guild_id]
                else:
                    vc = await voice_channel.connect()
                    self.active_vc[guild_id] = vc

                # Play the audio
                vc.play(discord.FFmpegPCMAudio(self.audio_file), after=lambda e: print("Finished playing."))

                # Wait for audio to finish
                while vc.is_playing():
                    await asyncio.sleep(1)

            # Send text translation
            await message.channel.send(f"🇫🇷 **Translated:** {translated_text}")

        except Exception as e:
            print(f"Error: {e}")
            await message.channel.send("⚠️ Translation failed.")

async def setup(bot):
    await bot.add_cog(TranslationVoice(bot))
