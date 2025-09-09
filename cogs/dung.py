import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Configuration
HELPER_ROLE_ID = 1244077334668116050
LOG_CHANNEL_ID = 1370180452995825765
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
        
        super().__init__(
            style=discord.ButtonStyle.primary,
            label=dungeon_data["name"],
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
                    f"⏰ You're on cooldown! Please wait {minutes}m {seconds}s before requesting help again.",
                    ephemeral=True
                )
                return
        
        # Set cooldown
        self.cooldowns[user_id] = current_time + timedelta(minutes=COOLDOWN_MINUTES)
        
        try:
            # Create thread for the dungeon request
            thread_name = f"{self.dungeon_data['name']} - {interaction.user.name}"
            thread = await interaction.channel.create_thread(
                name=thread_name[:100],  # Discord thread name limit
                type=discord.ChannelType.public_thread,
                auto_archive_duration=1440,  # 24 hours
                reason=f"Dungeon help request by {interaction.user}"
            )
            
            # Create embed for the thread
            embed = discord.Embed(
                title=f"Dungeon Help Request: {self.dungeon_data['name']}",
                description=(
                    f"**Requester:** {interaction.user.mention}\n"
                    f"**Helpers:** <@&{HELPER_ROLE_ID}>\n\n"
                    f"Please coordinate here for the dungeon run.\n"
                    f"Once completed, use `/close` to archive this thread."
                ),
                color=discord.Color.blue(),
                timestamp=datetime.utcnow()
            )
            embed.set_footer(text="Life Alliance Dungeon Service")
            
            # Send embed in thread
            await thread.send(embed=embed)
            
            # Send ephemeral confirmation to user
            await interaction.response.send_message(
                f"✅ Your request for **{self.dungeon_data['name']}** help has been opened in {thread.mention}",
                ephemeral=True
            )
            
            # Log the request
            await self.log_request(interaction)
            
        except discord.HTTPException as e:
            logger.error(f"Failed to create thread: {e}")
            await interaction.response.send_message(
                "❌ Failed to create help thread. Please try again or contact staff.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Unexpected error in dungeon button: {e}")
            await interaction.response.send_message(
                "❌ An unexpected error occurred. Please contact staff.",
                ephemeral=True
            )
    
    async def log_request(self, interaction: discord.Interaction):
        """Log the dungeon request to staff channel"""
        try:
            log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
            if not log_channel:
                logger.warning(f"Log channel {LOG_CHANNEL_ID} not found")
                return
            
            log_embed = discord.Embed(
                title="🎮 New Dungeon Help Request",
                description=(
                    f"**User:** {interaction.user.mention} ({interaction.user.name})\n"
                    f"**Dungeon:** {self.dungeon_data['name']}\n"
                    f"**Channel:** {interaction.channel.mention}\n"
                    f"**Time:** <t:{int(datetime.utcnow().timestamp())}:F>"
                ),
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            log_embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            await log_channel.send(embed=log_embed)
            
        except Exception as e:
            logger.error(f"Failed to log request: {e}")


class DungeonView(discord.ui.View):
    """Persistent view containing all dungeon buttons"""
    
    def __init__(self):
        super().__init__(timeout=None)  # Persistent view
        
        # Add all dungeon buttons
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
        
        # Create the main embed
        embed = discord.Embed(
            title="Frigost 3 Dungeon Help Panel",
            description=(
                "This service is free for Life Alliance.\n"
                "Dungeon keys will be provided for the helpers from the Alliance.\n\n"
                "This is a fast-run service (no achievements, no challenges).\n"
                "Purpose: To give members access to Frigost 3 zones and help with their Quest (Ice Dofus...)."
            ),
            color=discord.Color.blue()
        )
        
        # Set the banner image
        embed.set_image(url=BANNER_URL)
        
        # Add footer
        embed.set_footer(
            text="Click a button below to request help • 10 minute cooldown per user",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )
        
        # Create the view with buttons
        view = DungeonView()
        
        try:
            # Send the embed with the view
            await interaction.response.send_message(embed=embed, view=view)
            logger.info(f"Dungeon panel sent by {interaction.user}")
            
        except discord.HTTPException as e:
            logger.error(f"Failed to send dungeon panel: {e}")
            await interaction.response.send_message(
                "❌ Failed to create the dungeon panel. Please try again.",
                ephemeral=True
            )
    
    @app_commands.command(name="close", description="Close and archive the current dungeon help thread")
    async def close_command(self, interaction: discord.Interaction):
        """Slash command to close/archive a dungeon help thread"""
        
        # Check if command is used in a thread
        if not isinstance(interaction.channel, discord.Thread):
            await interaction.response.send_message(
                "❌ This command can only be used in a dungeon help thread.",
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
                "❌ Only the requester, helpers, or moderators can close this thread.",
                ephemeral=True
            )
            return
        
        try:
            # Send closing message
            await interaction.response.send_message(
                f"🔒 Thread closed by {interaction.user.mention}. Archiving..."
            )
            
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
                "❌ Failed to close the thread. Please try again or contact staff.",
                ephemeral=True
            )
    
    @app_commands.command(name="dung_stats", description="View dungeon help statistics (Staff only)")
    @app_commands.default_permissions(manage_messages=True)
    async def dung_stats(self, interaction: discord.Interaction):
        """Staff command to view dungeon help statistics"""
        
        # This is a placeholder for potential statistics tracking
        # You could expand this to track requests in a database
        
        embed = discord.Embed(
            title="📊 Dungeon Help Statistics",
            description="Statistics tracking coming soon!",
            color=discord.Color.gold(),
            timestamp=datetime.utcnow()
        )
        
        embed.add_field(
            name="Available Dungeons",
            value="\n".join([f"{data['emoji']} {data['name']}" for data in DUNGEONS.values()]),
            inline=False
        )
        
        embed.add_field(name="Helper Role", value=f"<@&{HELPER_ROLE_ID}>", inline=True)
        embed.add_field(name="Cooldown", value=f"{COOLDOWN_MINUTES} minutes", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    """Setup function to add the cog to the bot"""
    await bot.add_cog(DungeonCog(bot))
    logger.info("Dungeon cog loaded successfully")
