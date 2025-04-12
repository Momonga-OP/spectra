# cogs/congrats.py
import discord
from discord import app_commands
from discord.ext import commands
import asyncio

class Congrats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="congrats", description="Send a special celebration message for level 200 Spartan achievement")
    @app_commands.describe(user="The user who reached level 200")
    async def congrats(self, interaction: discord.Interaction, user: discord.User):
        """Sends a Spartan-themed congratulation message for reaching level 200"""
        
        # Defer the response since we'll be adding animations
        await interaction.response.defer()
        
        # Create a simple, impactful message
        congrats_message = f"""
{user.mention} has reached **LEVEL 200**!

✧･ﾟ: ✧･ﾟ:  **NOW TRULY A SPARTAN MEMBER**  :･ﾟ✧:･ﾟ✧

⚔️ Your journey has just begun, warrior! ⚔️

```
   _____                             _       _ 
  / ____|                           | |     | |
 | |     ___  _ __   __ _ _ __ __ _| |_ ___| |
 | |    / _ \| '_ \ / _` | '__/ _` | __/ __| |
 | |___| (_) | | | | (_| | | | (_| | |_\__ \_|
  \_____\___/|_| |_|\__, |_|  \__,_|\__|___(_)
                     __/ |                    
                    |___/                     
```

*"At the gates of glory, only the strongest survive. Level 200 is where legends begin their true path."*

💥 WELCOME TO THE ELITE RANKS! 💥
"""
        
        # Prepare the first animation frame
        start_message = await interaction.followup.send("**PREPARING SPARTAN ANNOUNCEMENT...**")
        
        # Animation frames with your custom messages
        frames = [
            "**Now you have the right to Vote**",
            "**Now No one will Scream at you**",
            "**Now No one will Will kick You**"
        ]
        
        # Show animation
        for frame in frames:
            await asyncio.sleep(0.8)
            await start_message.edit(content=frame)
        
        # Delete animation message
        await start_message.delete()
        
        # Create the final announcement with @everyone tag
        final_message = await interaction.followup.send(
            content=f"@everyone! 🎉 **ATTENTION SPARTANS!** 🎉\n\n{congrats_message}",
            allowed_mentions=discord.AllowedMentions(everyone=True)
        )
        
        # Add flashy reactions
        reactions = ["🔥", "⚔️", "🛡️", "✨", "💪"]
        for reaction in reactions:
            await final_message.add_reaction(reaction)

async def setup(bot):
    await bot.add_cog(Congrats(bot))
