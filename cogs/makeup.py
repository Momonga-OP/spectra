import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import datetime
import re

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

# Font styles for channel names
FONTS = {
    "aesthetic": {
        "a": "ａ", "b": "ｂ", "c": "ｃ", "d": "ｄ", "e": "ｅ", "f": "ｆ", "g": "ｇ", "h": "ｈ", "i": "ｉ", "j": "ｊ",
        "k": "ｋ", "l": "ｌ", "m": "ｍ", "n": "ｎ", "o": "ｏ", "p": "ｐ", "q": "ｑ", "r": "ｒ", "s": "ｓ", "t": "ｔ",
        "u": "ｕ", "v": "ｖ", "w": "ｗ", "x": "ｘ", "y": "ｙ", "z": "ｚ", "0": "０", "1": "１", "2": "２", "3": "３",
        "4": "４", "5": "５", "6": "６", "7": "７", "8": "８", "9": "９", " ": "　"
    },
    "bold": {
        "a": "𝗮", "b": "𝗯", "c": "𝗰", "d": "𝗱", "e": "𝗲", "f": "𝗳", "g": "𝗴", "h": "𝗵", "i": "𝗶", "j": "𝗷",
        "k": "𝗸", "l": "𝗹", "m": "𝗺", "n": "𝗻", "o": "𝗼", "p": "𝗽", "q": "𝗾", "r": "𝗿", "s": "𝘀", "t": "𝘁",
        "u": "𝘂", "v": "𝘃", "w": "𝘄", "x": "𝘅", "y": "𝘆", "z": "𝘇", "0": "𝟬", "1": "𝟭", "2": "𝟮", "3": "𝟯",
        "4": "𝟰", "5": "𝟱", "6": "𝟲", "7": "𝟳", "8": "𝟴", "9": "𝟵", " ": " "
    },
    "bold-italic": {
        "a": "𝙖", "b": "𝙗", "c": "𝙘", "d": "𝙙", "e": "𝙚", "f": "𝙛", "g": "𝙜", "h": "𝙝", "i": "𝙞", "j": "𝙟",
        "k": "𝙠", "l": "𝙡", "m": "𝙢", "n": "𝙣", "o": "𝙤", "p": "𝙥", "q": "𝙦", "r": "𝙧", "s": "𝙨", "t": "𝙩",
        "u": "𝙪", "v": "𝙫", "w": "𝙬", "x": "𝙭", "y": "𝙮", "z": "𝙯", "0": "0", "1": "1", "2": "2", "3": "3",
        "4": "4", "5": "5", "6": "6", "7": "7", "8": "8", "9": "9", " ": " "
    },
    "cursive": {
        "a": "𝓪", "b": "𝓫", "c": "𝓬", "d": "𝓭", "e": "𝓮", "f": "𝓯", "g": "𝓰", "h": "𝓱", "i": "𝓲", "j": "𝓳",
        "k": "𝓴", "l": "𝓵", "m": "𝓶", "n": "𝓷", "o": "𝓸", "p": "𝓹", "q": "𝓺", "r": "𝓻", "s": "𝓼", "t": "𝓽",
        "u": "𝓾", "v": "𝓿", "w": "𝔀", "x": "𝔁", "y": "𝔂", "z": "𝔃", "0": "0", "1": "1", "2": "2", "3": "3",
        "4": "4", "5": "5", "6": "6", "7": "7", "8": "8", "9": "9", " ": " "
    },
    "monospace": {
        "a": "𝚊", "b": "𝚋", "c": "𝚌", "d": "𝚍", "e": "𝚎", "f": "𝚏", "g": "𝚐", "h": "𝚑", "i": "𝚒", "j": "𝚓",
        "k": "𝚔", "l": "𝚕", "m": "𝚖", "n": "𝚗", "o": "𝚘", "p": "𝚙", "q": "𝚚", "r": "𝚛", "s": "𝚜", "t": "𝚝",
        "u": "𝚞", "v": "𝚟", "w": "𝚠", "x": "𝚡", "y": "𝚢", "z": "𝚣", "0": "𝟶", "1": "𝟷", "2": "𝟸", "3": "𝟹",
        "4": "𝟺", "5": "𝟻", "6": "𝟼", "7": "𝟽", "8": "𝟾", "9": "𝟿", " ": " "
    },
    "small-caps": {
        "a": "ᴀ", "b": "ʙ", "c": "ᴄ", "d": "ᴅ", "e": "ᴇ", "f": "ꜰ", "g": "ɢ", "h": "ʜ", "i": "ɪ", "j": "ᴊ",
        "k": "ᴋ", "l": "ʟ", "m": "ᴍ", "n": "ɴ", "o": "ᴏ", "p": "ᴘ", "q": "ǫ", "r": "ʀ", "s": "s", "t": "ᴛ",
        "u": "ᴜ", "v": "ᴠ", "w": "ᴡ", "x": "x", "y": "ʏ", "z": "ᴢ", "0": "0", "1": "1", "2": "2", "3": "3",
        "4": "4", "5": "5", "6": "6", "7": "7", "8": "8", "9": "9", " ": " "
    }
}

class Makeup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.backup = {}
        self.font_backup = {}
        
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
    
    @app_commands.command(name="font", description="Change the font style of channel names")
    @app_commands.describe(style="Choose a font style for your channel names")
    @app_commands.choices(style=[
        app_commands.Choice(name="Aesthetic", value="aesthetic"),
        app_commands.Choice(name="Bold", value="bold"),
        app_commands.Choice(name="Bold Italic", value="bold-italic"),
        app_commands.Choice(name="Cursive", value="cursive"),
        app_commands.Choice(name="Monospace", value="monospace"),
        app_commands.Choice(name="Small Caps", value="small-caps"),
        app_commands.Choice(name="Normal", value="normal")
    ])
    async def font(self, interaction: discord.Interaction, style: str):
        # Check if user is the bot owner
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("❌ You are not allowed to use this command.", ephemeral=True)
            return
        
        await interaction.response.send_message(f"🔤 Changing channel fonts to {style} style...", ephemeral=True)
        guild = interaction.guild
        progress_message = await interaction.followup.send("⏳ Creating backup of current channel names...", ephemeral=False)
        
        # Backup current channel names
        await self.backup_font(guild)
        
        # Update progress
        await progress_message.edit(content="⏳ Backup complete! Now applying font style...")
        
        # Apply the selected font style
        if style.lower() == "normal":
            await self.restore_font(guild, progress_message)
        else:
            await self.apply_font(guild, style.lower(), progress_message)
        
        # Send completion message
        embed = discord.Embed(
            title="✅ Font Style Applied!",
            description=f"Channel names have been updated to the **{style.title()}** font style!",
            color=0x00FF00
        )
        embed.add_field(name="Applied by", value=interaction.user.display_name, inline=True)
        embed.add_field(name="To revert", value="Use `/font normal` command", inline=False)
        embed.set_footer(text="Spectra Bot • Font Styling")
        
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
        progress_message = await interaction.followup.send("⏳ Restoring original server structure...", ephemeral=False)
        
        # Restore the original server structure
        await self.restore_server(guild, progress_message)
        
        # Send completion message
        embed = discord.Embed(
            title="✅ Server Restoration Complete!",
            description="Your server has been restored to its original state!",
            color=0x00FF00
        )
        embed.add_field(name="Restored by", value=interaction.user.display_name, inline=True)
        embed.set_footer(text="Spectra Bot • Server Restoration")
        
        await progress_message.edit(content="", embed=embed)
    
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
    
    async def backup_font(self, guild):
        """Create a backup of current channel names for font styling"""
        self.font_backup = {
            "categories": {},
            "text_channels": {},
            "voice_channels": {}
        }
        
        for category in guild.categories:
            self.font_backup["categories"][category.id] = category.name
            
        for channel in guild.text_channels:
            self.font_backup["text_channels"][channel.id] = channel.name
            
        for voice_channel in guild.voice_channels:
            self.font_backup["voice_channels"][voice_channel.id] = voice_channel.name
    
    async def restore_server(self, guild, progress_message):
        """Restore the server to its original state"""
        if not self.backup:
            return
        
        # Step 1: Restore categories
        await progress_message.edit(content="⏳ Restoring categories...")
        for category_id, category_data in self.backup["categories"].items():
            category = guild.get_channel(category_id)
            if category:
                try:
                    await category.edit(name=category_data["name"], position=category_data["position"])
                    await asyncio.sleep(0.5)  # Avoid rate limits
                except discord.HTTPException:
                    continue
        
        # Step 2: Restore text channels
        await progress_message.edit(content="⏳ Restoring text channels...")
        for channel_id, channel_data in self.backup["channels"].items():
            channel = guild.get_channel(channel_id)
            if channel:
                try:
                    await channel.edit(
                        name=channel_data["name"],
                        topic=channel_data["topic"],
                        position=channel_data["position"],
                        category=guild.get_channel(channel_data["category_id"])
                    )
                    await asyncio.sleep(0.5)  # Avoid rate limits
                except discord.HTTPException:
                    continue
        
        # Step 3: Restore voice channels
        await progress_message.edit(content="⏳ Restoring voice channels...")
        for vc_id, vc_data in self.backup["voice_channels"].items():
            vc = guild.get_channel(vc_id)
            if vc:
                try:
                    await vc.edit(
                        name=vc_data["name"],
                        position=vc_data["position"],
                        category=guild.get_channel(vc_data["category_id"]),
                        user_limit=vc_data["user_limit"]
                    )
                    await asyncio.sleep(0.5)  # Avoid rate limits
                except discord.HTTPException:
                    continue
        
        # Clear the backup after restoration
        self.backup = {}
    
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
    
    async def apply_font(self, guild, font_style, progress_message):
        """Apply the selected font style to channel names"""
        if font_style not in FONTS:
            return
            
        font_map = FONTS[font_style]
        count = 0
        total = len(guild.categories) + len(guild.text_channels) + len(guild.voice_channels)
        
        # Function to convert text to the selected font style
        def convert_to_font(text):
            # Preserve emojis and non-alphanumeric characters
            emoji_pattern = re.compile(r'([\U00010000-\U0010ffff]|\ud83d[\udc00-\ude4f]|\ud83c[\udf00-\udfff]|[^\w\s-])')
            parts = emoji_pattern.split(text)
            
            result = ""
            for part in parts:
                if emoji_pattern.match(part):
                    # Keep emojis unchanged
                    result += part
                else:
                    # Convert alphanumeric characters to the font style
                    for char in part.lower():
                        if char in font_map:
                            result += font_map[char]
                        else:
                            result += char
            return result
        
        # Step 1: Apply font to categories
        for category in guild.categories:
            try:
                # Extract emojis and preserve them
                match = re.match(r'^([\U00010000-\U0010ffff]|\ud83d[\udc00-\ude4f]|\ud83c[\udf00-\udfff]|[^\w\s-]+)\s(.+)$', category.name)
                if match:
                    emoji = match.group(1)
                    name = match.group(2)
                    new_name = f"{emoji} {convert_to_font(name)}"
                else:
                    new_name = convert_to_font(category.name)
                
                await category.edit(name=new_name)
                await asyncio.sleep(0.5)  # Avoid rate limits
                count += 1
                if count % 5 == 0:
                    await progress_message.edit(content=f"⏳ Applying font style... ({count}/{total})")
            except discord.HTTPException:
                continue
        
        # Step 2: Apply font to text channels
        for channel in guild.text_channels:
            try:
                # Extract emojis and preserve them
                match = re.match(r'^([\U00010000-\U0010ffff]|\ud83d[\udc00-\ude4f]|\ud83c[\udf00-\udfff]|[^\w\s-]+)-(.+)$', channel.name)
                if match:
                    emoji = match.group(1)
                    name = match.group(2)
                    new_name = f"{emoji}-{convert_to_font(name)}"
                else:
                    new_name = convert_to_font(channel.name)
                
                await channel.edit(name=new_name)
                await asyncio.sleep(0.5)  # Avoid rate limits
                count += 1
                if count % 5 == 0:
                    await progress_message.edit(content=f"⏳ Applying font style... ({count}/{total})")
            except discord.HTTPException:
                continue
        
        # Step 3: Apply font to voice channels
        for vc in guild.voice_channels:
            try:
                # Extract emojis and preserve them
                match = re.match(r'^([\U00010000-\U0010ffff]|\ud83d[\udc00-\ude4f]|\ud83c[\udf00-\udfff]|[^\w\s-]+)-(.+)$', vc.name)
                if match:
                    emoji = match.group(1)
                    name = match.group(2)
                    new_name = f"{emoji}-{convert_to_font(name)}"
                else:
                    new_name = convert_to_font(vc.name)
                
                await vc.edit(name=new_name)
                await asyncio.sleep(0.5)  # Avoid rate limits
                count += 1
                if count % 5 == 0:
                    await progress_message.edit(content=f"⏳ Applying font style... ({count}/{total})")
            except discord.HTTPException:
                continue
    
    async def restore_font(self, guild, progress_message):
        """Restore channel names to normal font"""
        if not self.font_backup:
            await progress_message.edit(content="❌ No font backup found! Cannot restore original names.")
            return
        
        count = 0
        total = len(self.font_backup["categories"]) + len(self.font_backup["text_channels"]) + len(self.font_backup["voice_channels"])
        
        # Step 1: Restore category names
        for category_id, name in self.font_backup["categories"].items():
            category = guild.get_channel(category_id)
            if category:
                try:
                    await category.edit(name=name)
                    await asyncio.sleep(0.5)  # Avoid rate limits
                    count += 1
                    if count % 5 == 0:
                        await progress_message.edit(content=f"⏳ Restoring original names... ({count}/{total})")
                except discord.HTTPException:
                    continue
        
        # Step 2: Restore text channel names
        for channel_id, name in self.font_backup["text_channels"].items():
            channel = guild.get_channel(channel_id)
            if channel:
                try:
                    await channel.edit(name=name)
                    await asyncio.sleep(0.5)  # Avoid rate limits
                    count += 1
                    if count % 5 == 0:
                        await progress_message.edit(content=f"⏳ Restoring original names... ({count}/{total})")
                except discord.HTTPException:
                    continue
        
        # Step 3: Restore voice channel names
        for vc_id, name in self.font_backup["voice_channels"].items():
            vc = guild.get_channel(vc_id)
            if vc:
                try:
                    await vc.edit(name=name)
                    await asyncio.sleep(0.5)  # Avoid rate limits
                    count += 1
                    if count % 5 == 0:
                        await progress_message.edit(content=f"⏳ Restoring original names... ({count}/{total})")
                except discord.HTTPException:
                    continue
        
        # Clear the font backup after restoration
        self.font_backup = {}
    
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
