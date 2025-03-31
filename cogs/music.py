import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
import asyncio
import os

USER_ID = 486652069831376943  # Your ID

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

    @commands.dm_only()
    @commands.command()
    async def music(self, ctx):
        if ctx.author.id != USER_ID:
            return await ctx.send("You are not allowed to use this command.")
        
        # Find the user's current voice channel
        if ctx.author.voice and ctx.author.voice.channel:
            channel = ctx.author.voice.channel
        else:
            return await ctx.send("You need to be in a voice channel.")

        # Join voice channel
        vc = await channel.connect()
        self.voice_clients[ctx.author.id] = vc
        await ctx.send("What do you want?")
        await asyncio.sleep(5)
        await ctx.send("Okay, I will see what I can do with that.")
        
        def check(m):
            return m.author.id == USER_ID and m.channel == ctx.channel and m.attachments

        await ctx.send("Upload an MP3 file.")
        msg = await self.bot.wait_for("message", check=check)
        attachment = msg.attachments[0]

        if not attachment.filename.endswith(".mp3"):
            return await ctx.send("Please upload a valid MP3 file.")

        file_path = f"music_{ctx.author.id}.mp3"
        await attachment.save(file_path)

        await self.disable_welcoming()

        # Play the music
        vc.play(FFmpegPCMAudio(file_path), after=lambda e: asyncio.run_coroutine_threadsafe(self.enable_welcoming(), self.bot.loop))
        
        await ctx.send("Playing your music now.")
        while vc.is_playing():
            await asyncio.sleep(1)

        await asyncio.sleep(1)
        await self.enable_welcoming()
        
        # Disconnect bot from voice
        await vc.disconnect()
        del self.voice_clients[ctx.author.id]
        os.remove(file_path)

async def setup(bot):
    await bot.add_cog(Music(bot))
