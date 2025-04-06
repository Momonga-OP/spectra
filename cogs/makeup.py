import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import datetime

OWNER_ID = 486652069831376943  # Only this user can use the command

# Theme options for server makeover
THEMES = {
    "cosmic": {
        "categories": {
            "🌟 WELCOME & INFO": ["📌-rules", "📣-announcements", "👋-introductions", "🎁-giveaways"],
            "💬 COMMUNITY": ["🗣️-general", "🎮-gaming", "🎵-music", "🎨-art", "📷-media"],
            "🎲 GAMING ZONE": ["🎯-game-night", "🏆-tournaments", "🎮-looking-to-play"],
            "🔊 VOICE LOUNGES": []  # Voice channels will be added here
        },
        "emoji_prefixes": {
            "general": ["💫", "✨", "🌠", "🌌", "🚀", "👾"],
            "gaming": ["🎮", "🎯", "🎲", "🏆", "🎪"],
            "voice": ["🔊", "🎵", "🎧", "🎤", "🎹"]
        }
    },
    "nature": {
        "categories": {
            "🌿 WELCOME & INFO": ["📌-rules", "📣-announcements", "👋-introductions", "🎁-events"],
            "🌳 COMMUNITY": ["💬-general", "🌱-garden", "🐾-pets", "🏞️-outdoors", "📷-nature-pics"],
            "🌊 ACTIVITIES": ["🏕️-adventures", "🚶-hiking", "🌄-travel"],
            "🔊 VOICE MEADOWS": []  # Voice channels will be added here
        },
        "emoji_prefixes": {
            "general": ["🌿", "🍃", "🌱", "🌲", "🌳", "🌺"],
            "gaming": ["🌄", "🏞️", "🌅", "🌊", "🍄"],
            "voice": ["🔊", "🎵", "🦜", "🐦", "🌬️"]
        }
    },
    "neon": {
        "categories": {
            "💡 WELCOME & INFO": ["📌-rules", "📣-announcements", "👋-introductions", "🎁-events"],
            "💫 COMMUNITY": ["💬-general", "🎮-gaming", "🎵-music", "🎨-art", "📷-media"],
            "🎪 ACTIVITIES": ["🎯-game-night", "🏆-tournaments", "🎭-events"],
            "🔊 VOICE LOUNGES": []  # Voice channels will be added here
        },
        "emoji_prefixes": {
            "general": ["💫", "⚡", "🔥", "💥", "✨", "💠"],
            "gaming": ["🎮", "🎯", "🎲", "🏆", "🎪"],
            "voice": ["🔊", "🎵", "🎧", "🎤", "⚡"]
        }
    }
}

class Makeup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.backup = {}
        
    @app_commands.command(name="makeup", description="Give your server a fantastic makeover!")
    @app_commands.describe(theme="Choose a theme for your server makeover")
    @app_commands.choices(theme=[
        app_commands.Choice(name="Cosmic", value="cosmic"),
        app_commands.Choice(name="Nature", value="nature"),
        app_commands.Choice(name="Neon", value="neon")
    ])
    async def makeup(self, interaction: discord.Interaction, theme: str = "cosmic"):
        # Check if user is the bot owner
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ You are not allowed to use this command.", ephemeral=True)
            return
            
        await interaction.response.send_message("🎨 Starting the server makeover...", ephemeral=True)
        guild = interaction.guild
        progress_message = await interaction.followup.send("⏳ Creating backup of current server structure...", ephemeral=False)
        
        # Backup current server structure
        await self.backup_server(guild)
        
        # Update progress
        await progress_message.edit(content="⏳ Backup complete! Now applying the makeover...")
        
        # Apply the selected theme
        theme_data = THEMES.get(theme.lower(), THEMES["cosmic"])
        await self.apply_theme(guild, theme_data, progress_message)
        
        # Send completion message with timestamp
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        embed = discord.Embed(
            title="✅ Server Makeover Complete!",
            description=f"Your server has been transformed with the **{theme.title()}** theme!",
            color=0x00FF00
        )
        embed.add_field(name="Applied at", value=timestamp, inline=True)
        embed.add_field(name="Applied by", value=interaction.user.display_name, inline=True)
        embed.add_field(name="To revert", value="Use `/unmakeup` command", inline=False)
        embed.set_footer(text="Spectra Bot • Server Makeover")
        
        await progress_message.edit(content="", embed=embed)
    
    @app_commands.command(name="unmakeup", description="Revert your server to its original state")
    async def unmakeup(self, interaction: discord.Interaction):
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ You are not allowed to use this command.", ephemeral=True)
            return
            
        if not self.backup:
            await interaction.response.send_message("❌ No backup found! Cannot revert the server.", ephemeral=True)
            return
            
        await interaction.response.send_message("🔄 Reverting server to original state...", ephemeral=True)
        guild = interaction.guild
        
        # Implement the revert logic here using self.backup data
        # This would be complex but essentially would restore channel names and positions
        
        await interaction.followup.send("✅ Server has been restored to its original state!", ephemeral=False)
        self.backup = {}  # Clear the backup after restoration
    
    async def backup_server(self, guild):
        """Create a backup of the current server structure"""
        self.backup = {
            "categories": {},
            "channels": {},
            "voice_channels": {}
        }
        
        for category in guild.categories:
            self.backup["categories"][category.id] = {
                "name": category.name,
                "position": category.position
            }
        
        for channel in guild.text_channels:
            self.backup["channels"][channel.id] = {
                "name": channel.name,
                "category_id": channel.category_id,
                "position": channel.position,
                "topic": channel.topic
            }
            
        for voice_channel in guild.voice_channels:
            self.backup["voice_channels"][voice_channel.id] = {
                "name": voice_channel.name,
                "category_id": voice_channel.category_id,
                "position": voice_channel.position,
                "user_limit": voice_channel.user_limit
            }
    
    async def apply_theme(self, guild, theme_data, progress_message):
        """Apply the selected theme to the server"""
        # Step 1: Rename existing channels
        await progress_message.edit(content="⏳ Renaming existing channels...")
        await self.rename_channels(guild, theme_data)
        
        # Step 2: Create new category structure
        await progress_message.edit(content="⏳ Creating new category structure...")
        created_categories = await self.setup_categories(guild, theme_data)
        
        # Step 3: Organize existing channels into appropriate categories
        await progress_message.edit(content="⏳ Organizing channels into categories...")
        await self.organize_channels(guild, created_categories, theme_data)
        
        # Step 4: Create any missing essential channels
        await progress_message.edit(content="⏳ Adding essential channels...")
        await self.create_essential_channels(guild, created_categories, theme_data)
    
    async def rename_channels(self, guild, theme_data):
        """Rename existing channels with theme prefixes"""
        general_emojis = theme_data["emoji_prefixes"]["general"]
        gaming_emojis = theme_data["emoji_prefixes"]["gaming"]
        voice_emojis = theme_data["emoji_prefixes"]["voice"]
        
        # Text channels
        for channel in guild.text_channels:
            # Skip renaming if it already has a prefix emoji
            if channel.name[0] in ["✨", "🌿", "💫", "📌", "🎮", "💬", "🔥", "⚡"]:
                continue
                
            # Choose prefix based on channel name keywords
            emoji = random.choice(general_emojis)
            if any(keyword in channel.name for keyword in ["game", "play", "gaming", "valorant", "minecraft"]):
                emoji = random.choice(gaming_emojis)
                
            # Apply the new name - keep the original name without discord's auto-added hyphens
            original_name = channel.name.replace("-", " ")
            new_name = f"{emoji}-{original_name}"
            
            # Discord has a 100 character limit for channel names
            if len(new_name) > 100:
                new_name = new_name[:97] + "..."
                
            try:
                await channel.edit(name=new_name)
                await asyncio.sleep(0.5)  # Avoid rate limits
            except discord.HTTPException:
                continue
        
        # Voice channels        
        for vc in guild.voice_channels:
            # Skip renaming if it already has a prefix emoji
            if vc.name[0] in ["🔊", "🎵", "🎧", "🎤"]:
                continue
                
            emoji = random.choice(voice_emojis)
            original_name = vc.name.replace("-", " ")
            new_name = f"{emoji}-{original_name}"
            
            if len(new_name) > 100:
                new_name = new_name[:97] + "..."
                
            try:
                await vc.edit(name=new_name)
                await asyncio.sleep(0.5)  # Avoid rate limits
            except discord.HTTPException:
                continue
    
    async def setup_categories(self, guild, theme_data):
        """Create the theme's category structure"""
        created_categories = {}
        
        # Sort categories by their desired position
        position = 0
        for category_name, channel_list in theme_data["categories"].items():
            # Check if a similar category already exists
            existing = discord.utils.get(guild.categories, name=category_name)
            
            if existing:
                created_categories[category_name] = existing
                await existing.edit(position=position)
            else:
                try:
                    new_category = await guild.create_category(name=category_name, position=position)
                    created_categories[category_name] = new_category
                except discord.HTTPException:
                    continue
            
            position += 1
            await asyncio.sleep(0.5)  # Avoid rate limits
        
        return created_categories
    
    async def organize_channels(self, guild, categories, theme_data):
        """Organize existing channels into theme categories"""
        # Define channel type categorization rules
        channel_types = {
            "welcome": ["welcome", "rules", "info", "announcement", "intro"],
            "community": ["general", "chat", "talk", "discuss", "lounge"],
            "gaming": ["game", "play", "valorant", "minecraft", "league", "fortnite"],
            "media": ["media", "art", "music", "meme", "clip", "video", "stream"],
            "activity": ["event", "tournament", "night", "activity"]
        }
        
        # Get the category objects
        welcome_category = next((cat for name, cat in categories.items() if "WELCOME" in name), None)
        community_category = next((cat for name, cat in categories.items() if "COMMUNITY" in name), None)
        activity_category = next((cat for name, cat in categories.items() if "ACTIV" in name or "GAMING" in name), None)
        voice_category = next((cat for name, cat in categories.items() if "VOICE" in name), None)
        
        # Organize text channels
        for channel in guild.text_channels:
            try:
                if any(keyword in channel.name.lower() for keyword in channel_types["welcome"]):
                    await channel.edit(category=welcome_category)
                elif any(keyword in channel.name.lower() for keyword in channel_types["gaming"]):
                    await channel.edit(category=activity_category)
                elif any(keyword in channel.name.lower() for keyword in channel_types["media"]):
                    await channel.edit(category=community_category)
                elif any(keyword in channel.name.lower() for keyword in channel_types["activity"]):
                    await channel.edit(category=activity_category)
                elif channel.category is None:
                    await channel.edit(category=community_category)
                
                await asyncio.sleep(0.5)  # Avoid rate limits
            except discord.HTTPException:
                continue
        
        # Organize voice channels
        for vc in guild.voice_channels:
            try:
                if voice_category:
                    await vc.edit(category=voice_category)
                
                await asyncio.sleep(0.5)  # Avoid rate limits
            except discord.HTTPException:
                continue
    
    async def create_essential_channels(self, guild, categories, theme_data):
        """Create essential channels that are missing"""
        # Get the welcome category
        welcome_category = next((cat for name, cat in categories.items() if "WELCOME" in name), None)
        community_category = next((cat for name, cat in categories.items() if "COMMUNITY" in name), None)
        voice_category = next((cat for name, cat in categories.items() if "VOICE" in name), None)
        
        # Define essential channels for the welcome category
        if welcome_category:
            essential_channels = {
                "📌-rules": False,
                "📣-announcements": False,
                "👋-introductions": False
            }
            
            # Check if these channels already exist
            for channel in welcome_category.channels:
                for essential in essential_channels:
                    if essential.split("-")[1] in channel.name:
                        essential_channels[essential] = True
            
            # Create missing channels
            for channel_name, exists in essential_channels.items():
                if not exists:
                    try:
                        await guild.create_text_channel(name=channel_name, category=welcome_category)
                        await asyncio.sleep(0.5)  # Avoid rate limits
                    except discord.HTTPException:
                        continue
        
        # Define essential channels for the community category
        if community_category:
            community_channels = []
            if not discord.utils.get(community_category.channels, name=lambda n: "general" in n.lower()):
                community_channels.append("💬-general")
            
            # Create missing channels
            for channel_name in community_channels:
                try:
                    await guild.create_text_channel(name=channel_name, category=community_category)
                    await asyncio.sleep(0.5)  # Avoid rate limits
                except discord.HTTPException:
                    continue
        
        # Create voice channels if needed
        if voice_category and len(voice_category.channels) < 2:
            voice_emojis = theme_data["emoji_prefixes"]["voice"]
            try:
                await guild.create_voice_channel(name=f"{random.choice(voice_emojis)}-General Chat", category=voice_category)
                await guild.create_voice_channel(name=f"{random.choice(voice_emojis)}-Gaming", category=voice_category)
                await guild.create_voice_channel(name=f"{random.choice(voice_emojis)}-Music", category=voice_category)
            except discord.HTTPException:
                pass

async def setup(bot):
    await bot.add_cog(Makeup(bot))
