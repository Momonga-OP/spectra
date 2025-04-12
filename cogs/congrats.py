# cogs/congrats.py
import discord
from discord import app_commands
from discord.ext import commands
import asyncio
import pyfiglet

class Congrats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="congrats", description="Send a special celebration message for level 200 Spartan achievement")
    @app_commands.describe(user="The user who reached level 200")
    async def congrats(self, interaction: discord.Interaction, user: discord.User):
        """Sends a Spartan-themed congratulation message for reaching level 200"""
        
        # Defer the response since we'll be adding animations
        await interaction.response.defer()
        
        # Generate ASCII art for CONGRATS
        congrats_ascii = pyfiglet.figlet_format("CONGRATS")
        
        # Generate ASCII art for the user's name
        # Get the user's display name without any special characters that might break ASCII art
        clean_name = ''.join(char for char in user.display_name if char.isalnum() or char.isspace())
        user_ascii = pyfiglet.figlet_format(clean_name)
        
        # Create a simple, impactful message
        congrats_message = f"""
{user.mention} has reached **LEVEL 200**!

✧･ﾟ: ✧･ﾟ:  **NOW TRULY A SPARTAN MEMBER**  :･ﾟ✧:･ﾟ✧

 Your journey has just begun 

```
{congrats_ascii}
```

```
{user_ascii}
```

*"Welcome to the Elite Where 99% of the Server Population Are."*

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
            content=f"@everyone!  **ATTENTION SPARTANS!** \n\n{congrats_message}",
            allowed_mentions=discord.AllowedMentions(everyone=True)
        )
        
        # Add flashy reactions
        reactions = ["🔥", "⚔️", "🛡️", "✨", "💪"]
        for reaction in reactions:
            await final_message.add_reaction(reaction)

async def setup(bot):
    await bot.add_cog(Congrats(bot))
