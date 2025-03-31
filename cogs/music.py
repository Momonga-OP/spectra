import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
from discord import app_commands
import asyncio
import os

USER_ID = 853328704552566814  # Your ID

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_clients = {}
        self.welcoming_enabled = True  # Track the state of welcoming feature

    async def disable_welcoming(self):
        # Implement disabling welcoming feature in your bot's logic
        self.welcoming_enabled = False

    async def enable_welcoming(self):
        # Implement enabling welcoming feature in your bot's logic
        self.welcoming_enabled = True

    @app_commands.command(name="music", description="Plays music")
    async def music(self, interaction: discord.Interaction):
        if interaction.user.id != USER_ID:
            return await interaction.response.send_message("You are not allowed to use this command.", ephemeral=True)
        
        # Find the user's current voice channel
        if interaction.user.voice and interaction.user.voice.channel:
            channel = interaction.user.voice.channel
        else:
            return await interaction.response.send_message("You need to be in a voice channel.", ephemeral=True)

        # Join voice channel
        vc = await channel.connect()
        self.voice_clients[interaction.user.id] = vc
        await interaction.response.send_message("What do you want?")
        await asyncio.sleep(5)
        await interaction.followup.send("Okay, I will see what I can do with that.")
        
        def check(m):
            return m.author.id == USER_ID and isinstance(m.channel, discord.DMChannel) and m.attachments

        await interaction.user.send("Upload an MP3 file.")
        msg = await self.bot.wait_for("message", check=check)
        attachment = msg.attachments[0]

        if not attachment.filename.endswith(".mp3"):
            return await interaction.user.send("Please upload a valid MP3 file.")

        file_path = f"music_{interaction.user.id}.mp3"
        await attachment.save(file_path)

        await self.disable_welcoming()

        # Play the music
        vc.play(FFmpegPCMAudio(file_path), after=lambda e: asyncio.run_coroutine_threadsafe(self.enable_welcoming(), self.bot.loop))
        
        await interaction.user.send("Playing your music now.")
        while vc.is_playing():
            await asyncio.sleep(1)

        await asyncio.sleep(1)
        await self.enable_welcoming()
        
        # Disconnect bot from voice
        await vc.disconnect()
        del self.voice_clients[interaction.user.id]
        os.remove(file_path)

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.tree.add_command(self.music)

async def setup(bot):
    await bot.add_cog(Music(bot))
