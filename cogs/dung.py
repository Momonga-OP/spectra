import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Configuration
HELPER_ROLE_ID = 1244077334668116050
LOG_CHANNEL_ID = 1247706162317758597  # Updated log channel
BANNER_URL = "https://github.com/Momonga-OP/spectra/blob/main/Life.png?raw=true"
COOLDOWN_MINUTES = 10

# Dungeon configuration with custom emoji IDs
DUNGEONS = {
    "nileza": {
        "name": "Nileza",
        "emoji": "<:Nileza:1414786134193733714>",
        "emoji_id": 1414786134193733714
    },
    "missiz": {
        "name": "Missiz Freezz", 
        "emoji": "<:Missiz:1414786130314002482>",
        "emoji_id": 1414786130314002482
    },
    "sylargh": {
        "name": "Sylargh",
        "emoji": "<:Sylargh:1414786126652117042>",
        "emoji_id": 1414786126652117042
    },
    "klime": {
        "name": "Klime",
        "emoji": "<:Klime:1414786120671166465>",
        "emoji_id": 1414786120671166465
    },
    "harebourg": {
        "name": "Count Harebourg",
        "emoji": "<:Harebourg:1414786116166619136>",
        "emoji_id": 1414786116166619136
    }
}


class DungeonButton(discord.ui.Button):
    """Individual dungeon button with cooldown tracking"""
    
    def __init__(self, dungeon_key: str, dungeon_data: dict):
        # Use custom emoji for button
        emoji = discord.PartialEmoji(
            name=dungeon_data["name"].replace(" ", ""),
            id=dungeon_data["emoji_id"]
        )
        
        # Shorter label for better alignment
        label = dungeon_data["name"]
        if label == "Count Harebourg":
            label = "C. Harebourg"  # Shorten for better fit
        
        super().__init__(
            style=discord.ButtonStyle.primary,
            label=label,
            emoji=emoji,
            custom_id=f"dung_button_{dungeon_key}"
        )
        
        self.dungeon_key = dungeon_key
        self.dungeon_data = dungeon_data
        # Track cooldowns per user
        self.cooldowns = {}
    
    async def callback(self, interaction: discord.Interaction):
        """Handle button click"""
        user_id = interaction.user.id
        current_time = datetime.utcnow()
        
        # Check cooldown
        if user_id in self.cooldowns:
            cooldown_end = self.cooldowns[user_id]
            if current_time < cooldown_end:
                remaining = (cooldown_end - current_time).total_seconds()
                minutes = int(remaining // 60)
                seconds = int(remaining % 60)
                await interaction.response.send_message(
                    f"⏰ **Cooldown Active**\nPlease wait **{minutes}m {seconds}s** before requesting help again.",
                    ephemeral=True
                )
                return
        
        # Set cooldown
        self.cooldowns[user_id] = current_time + timedelta(minutes=COOLDOWN_MINUTES)
        
        try:
            # Create thread for the dungeon request
            thread_name = f" {self.dungeon_data['name']} - {interaction.user.name}"
            thread = await interaction.channel.create_thread(
                name=thread_name[:100],  # Discord thread name limit
                type=discord.ChannelType.public_thread,
                auto_archive_duration=1440,  # 24 hours
                reason=f"Dungeon help request by {interaction.user}"
            )
            
            # Create embed for the thread with improved formatting
            embed = discord.Embed(
                title=f" Dungeon Help Request: {self.dungeon_data['name']}",
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            
            # Add fields with better formatting
            embed.add_field(
                name=" Request Details",
                value=(
                    f"**Requester:** {interaction.user.mention}\n"
                    f"**Dungeon:** {self.dungeon_data['emoji']} **{self.dungeon_data['name']}**\n"
                    f"**Created:** <t:{int(datetime.utcnow().timestamp())}:R>"
                ),
                inline=False
            )
            
            embed.add_field(
                name=" Helpers Needed",
                value=f"<@&{HELPER_ROLE_ID}>",
                inline=False
            )
            
            embed.add_field(
                name=" Instructions",
                value=(
                    "1. Coordinate the dungeon run details here\n"
                    "2. **After completion, please post a screenshot of the dungeon victory**\n"
                    "3. Use `/close` to archive this thread when finished"
                ),
                inline=False
            )
            
            embed.set_footer(
                text="Life Alliance • Fast Run Service",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )
            
            # Send embed in thread
            await thread.send(embed=embed)
            
            # Send follow-up message requesting screenshot
            followup_embed = discord.Embed(
                description=(
                    " **Screenshot Required**\n"
                    "Please post a screenshot showing the dungeon completion once you're done!\n"
                    "This helps us track successful runs and improve our service."
                ),
                color=discord.Color.gold()
            )
            await thread.send(embed=followup_embed)
            
            # Send ephemeral confirmation to user
            confirm_embed = discord.Embed(
                title="✅ Request Created Successfully",
                description=(
                    f"Your request for **{self.dungeon_data['name']}** help has been created!\n\n"
                    f" **Thread:** {thread.mention}\n"
                    f" **Cooldown:** {COOLDOWN_MINUTES} minutes"
                ),
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=confirm_embed, ephemeral=True)
            
            # Log the request
            await self.log_request(interaction)
            
        except discord.HTTPException as e:
            logger.error(f"Failed to create thread: {e}")
            await interaction.response.send_message(
                "❌ **Error**\nFailed to create help thread. Please try again or contact staff.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Unexpected error in dungeon button: {e}")
            await interaction.response.send_message(
                "❌ **Unexpected Error**\nPlease contact staff for assistance.",
                ephemeral=True
            )
    
    async def log_request(self, interaction: discord.Interaction):
        """Log the dungeon request to staff channel"""
        try:
            log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
            if not log_channel:
                logger.warning(f"Log channel {LOG_CHANNEL_ID} not found")
                return
            
            # Create a cleaner log embed
            log_embed = discord.Embed(
                title=" New Dungeon Help Request",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            
            log_embed.add_field(
                name="User",
                value=f"{interaction.user.mention} (`{interaction.user.name}`)",
                inline=True
            )
            
            log_embed.add_field(
                name="Dungeon",
                value=f"{self.dungeon_data['emoji']} {self.dungeon_data['name']}",
                inline=True
            )
            
            log_embed.add_field(
                name="Channel",
                value=interaction.channel.mention,
                inline=True
            )
            
            log_embed.add_field(
                name="Time",
                value=f"<t:{int(datetime.utcnow().timestamp())}:F>",
                inline=False
            )
            
            log_embed.set_thumbnail(url=interaction.user.display_avatar.url)
            log_embed.set_footer(text=f"User ID: {interaction.user.id}")
            
            await log_channel.send(embed=log_embed)
            
        except Exception as e:
            logger.error(f"Failed to log request: {e}")


class DungeonView(discord.ui.View):
    """Persistent view containing all dungeon buttons"""
    
    def __init__(self):
        super().__init__(timeout=None)  # Persistent view
        
        # Add all dungeon buttons in a specific order for better layout
        for key, data in DUNGEONS.items():
            self.add_item(DungeonButton(key, data))


class DungeonCog(commands.Cog):
    """Cog for Frigost 3 dungeon help system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.persistent_views_added = False
    
    async def cog_load(self):
        """Called when the cog is loaded"""
        # Add persistent view on startup
        if not self.persistent_views_added:
            self.bot.add_view(DungeonView())
            self.persistent_views_added = True
            logger.info("Persistent dungeon view registered")
    
    @app_commands.command(name="dung", description="Display the Frigost 3 dungeon help panel")
    async def dung_command(self, interaction: discord.Interaction):
        """Slash command to display the dungeon help panel"""
        
        # Create the main embed with improved formatting
        embed = discord.Embed(
            title="**Frigost 3 Dungeon Help Panel**",
            color=discord.Color.blue()
        )
        
        # Add description with better formatting
        embed.description = (
            "**This service is free for Life Alliance.**\n"
            "Dungeon keys will be provided for the helpers from the Alliance.\n"
            "\n"
            "** Service Information:**\n"
            "• Fast-run service (no achievements, no challenges)\n"
            "• Access to Frigost 3 zones\n"
            "• Quest assistance (Ice Dofus and more)\n"
        )
        
        # Set the banner image
        embed.set_image(url=BANNER_URL)
        
        # Add fields for clarity
        embed.add_field(
            name=" How to Request Help",
            value="Click on a dungeon button below to create a help request",
            inline=False
        )
        
        embed.add_field(
            name=" Cooldown",
            value=f"{COOLDOWN_MINUTES} minutes per user",
            inline=True
        )
        
        embed.add_field(
            name=" Requirements",
            value="Screenshot required after completion",
            inline=True
        )
        
        # Add footer with timestamp
        embed.set_footer(
            text="Life Alliance • Dungeon Service",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )
        embed.timestamp = datetime.utcnow()
        
        # Create the view with buttons
        view = DungeonView()
        
        try:
            # Send the embed with the view
            await interaction.response.send_message(embed=embed, view=view)
            logger.info(f"Dungeon panel sent by {interaction.user}")
            
        except discord.HTTPException as e:
            logger.error(f"Failed to send dungeon panel: {e}")
            await interaction.response.send_message(
                "❌ **Error**\nFailed to create the dungeon panel. Please try again.",
                ephemeral=True
            )
    
    @app_commands.command(name="close", description="Close and archive the current dungeon help thread")
    async def close_command(self, interaction: discord.Interaction):
        """Slash command to close/archive a dungeon help thread"""
        
        # Check if command is used in a thread
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message(
                "❌ **Invalid Channel**\nThis command can only be used in a dungeon help thread.",
                ephemeral=True
            )
            return
        
        # Check if user is the thread creator or has helper role
        thread = interaction.channel
        is_creator = thread.owner_id == interaction.user.id
        has_helper_role = any(role.id == HELPER_ROLE_ID for role in interaction.user.roles)
        is_moderator = interaction.user.guild_permissions.manage_threads
        
        if not (is_creator or has_helper_role or is_moderator):
            await interaction.response.send_message(
                "❌ **Permission Denied**\nOnly the requester, helpers, or moderators can close this thread.",
                ephemeral=True
            )
            return
        
        try:
            # Send closing message with better formatting
            close_embed = discord.Embed(
                description=f" **Thread Closed**\nClosed by {interaction.user.mention}\nArchiving in 3 seconds...",
                color=discord.Color.red(),
                timestamp=datetime.utcnow()
            )
            await interaction.response.send_message(embed=close_embed)
            
            # Wait a moment before archiving
            await asyncio.sleep(3)
            
            # Archive the thread
            await thread.edit(
                archived=True,
                locked=False,
                reason=f"Closed by {interaction.user}"
            )
            
            logger.info(f"Thread {thread.name} closed by {interaction.user}")
            
        except discord.HTTPException as e:
            logger.error(f"Failed to close thread: {e}")
            await interaction.response.send_message(
                "❌ **Error**\nFailed to close the thread. Please try again or contact staff.",
                ephemeral=True
            )
    
    @app_commands.command(name="dung_stats", description="View dungeon help statistics (Staff only)")
    @app_commands.default_permissions(manage_messages=True)
    async def dung_stats(self, interaction: discord.Interaction):
        """Staff command to view dungeon help statistics"""
        
        embed = discord.Embed(
            title="**Dungeon Help Statistics**",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )
        
        # List all available dungeons
        dungeon_list = "\n".join([
            f"{data['emoji']} **{data['name']}**" 
            for data in DUNGEONS.values()
        ])
        embed.add_field(
            name="Available Dungeons",
            value=dungeon_list,
            inline=False
        )
        
        # System information
        embed.add_field(
            name="System Configuration",
            value=(
                f"**Helper Role:** <@&{HELPER_ROLE_ID}>\n"
                f"**Log Channel:** <#{LOG_CHANNEL_ID}>\n"
                f"**Cooldown:** {COOLDOWN_MINUTES} minutes\n"
                f"**Auto-Archive:** 24 hours"
            ),
            inline=False
        )
        
        embed.set_footer(text="Life Alliance Dungeon Service")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


# Import asyncio for the close command delay
import asyncio

async def setup(bot):
    """Setup function to add the cog to the bot"""
    await bot.add_cog(DungeonCog(bot))
    logger.info("Dungeon cog loaded successfully")
