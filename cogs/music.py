import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import os

BOT_OWNER_ID = 486652069831376943  # Only you can upload music
MUSIC_FILE = "music.mp3"  # Temporary storage for the uploaded file

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_clients = {}  # Store voice clients per guild

    @app_commands.command(name="music", description="Plays music in all servers where Spectra is in.")
    async def music(self, interaction: discord.Interaction):
        if interaction.user.id != BOT_OWNER_ID:
            return await interaction.response.send_message("You are not allowed to use this command!", ephemeral=True)
        
        await interaction.response.send_message("Please upload the music file in DMs.", ephemeral=True)
        dm_channel = await interaction.user.create_dm()
        await dm_channel.send("Upload an MP3 file to start playing in all servers.")

        def check(msg):
            return msg.author.id == BOT_OWNER_ID and msg.attachments and msg.attachments[0].filename.endswith(".mp3")

        try:
            msg = await self.bot.wait_for("message", check=check, timeout=60)
            await msg.attachments[0].save(MUSIC_FILE)
            await dm_channel.send("Music uploaded! Starting playback.")
            
            await self.play_music_globally()
        except asyncio.TimeoutError:
            await dm_channel.send("Music upload timed out. Try again.")

    async def play_music_globally(self):
        for guild in self.bot.guilds:
            if guild.id in self.voice_clients:
                continue  # Already connected
            
            voice_channel = None
            for channel in guild.voice_channels:
                if channel.permissions_for(guild.me).connect:
                    voice_channel = channel
                    break

            if voice_channel:
                vc = await voice_channel.connect()
                self.voice_clients[guild.id] = vc
                self.bot.loop.create_task(self.loop_music(vc))
            else:
                print(f"No available voice channel in {guild.name} ({guild.id})")

    async def loop_music(self, vc):
        while True:
            if os.path.exists(MUSIC_FILE):
                vc.play(discord.FFmpegPCMAudio(MUSIC_FILE), after=lambda e: None)
                while vc.is_playing():
                    await asyncio.sleep(1)
            else:
                await asyncio.sleep(10)

async def setup(bot):
    await bot.add_cog(Music(bot))
