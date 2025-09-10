# dung.py
# Discord.py v2.x cog implementing a persistent Frigost 3 dungeon help panel with verification form
# Changes in this version:
# - Added verification modal form before thread creation
# - Collects: in-game name, character class, preferred time, spot confirmation
# - Added service time estimation in thread messages
# - Enhanced thread embed with user-provided information

import re
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Tuple

import discord
from discord.ext import commands
from discord import app_commands

logger = logging.getLogger(__name__)

# ===== Configuration =====
HELPER_ROLE_ID = 1214188383606149170  # Role to ping for helpers
LOG_CHANNEL_ID = 1376299601358885066  # Staff log channel (update if needed)
BANNER_URL = "https://github.com/Momonga-OP/spectra/blob/main/Life.png?raw=true"
COOLDOWN_MINUTES = 10  # Global per-user cooldown across all dungeons
AUTO_ARCHIVE_MINUTES = 1440  # 24 hours

# Character classes for the dropdown
CHARACTER_CLASSES = [
    "Iop", "Cra", "Eniripsa", "Enutrof", "Sram", "Xelor", "Ecaflip", "Sacrier",
    "Sadida", "Osamodas", "Pandawa", "Feca",
    "Masqueraider", "Rogue"
]

# Custom emojis (IDs must exist in the guild)
DUNGEONS = {
    "nileza": {
        "name": "Nileza",
        "emoji_id": 1414937682240344204,
        "label": "Nileza",
    },
    "missiz": {
        "name": "Missiz Freezz",
        "emoji_id": 1414937676444078262,
        "label": "Missiz Freezz",
    },
    "sylargh": {
        "name": "Sylargh",
        "emoji_id": 1414937670538235955,
        "label": "Sylargh",
    },
    "klime": {
        "name": "Klime",
        "emoji_id": 1414937664758484993,
        "label": "Klime",
    },
    "harebourg": {
        "name": "Count Harebourg",
        "emoji_id": 1414937659566194749,
        "label": "C. Harebourg",
    },
}

# Requester marker persisted in thread message content (survives restarts)
REQUESTER_MARKER_RE = re.compile(r"REQUESTER_ID:(\d+)")
# Allowed mentions: allow role + user pings, never @everyone
ALLOWED_MENTIONS = discord.AllowedMentions(everyone=False, users=True, roles=True)
# Fixed custom_id prefix for persistent buttons
CUSTOM_ID_PREFIX = "f3_dung_btn"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DungeonVerificationModal(discord.ui.Modal):
    """Modal form for collecting user information before creating a dungeon thread."""
    
    def __init__(self, dungeon_key: str, dungeon_data: dict, cog: "DungeonCog", base_channel: discord.TextChannel):
        super().__init__(title=f"Request Help: {dungeon_data['name']}")
        self.dungeon_key = dungeon_key
        self.dungeon_data = dungeon_data
        self.cog = cog
        self.base_channel = base_channel
        
        # Text inputs for the form
        self.ingame_name = discord.ui.TextInput(
            label="In-Game Name",
            placeholder="Enter your Dofus character name...",
            required=True,
            max_length=50
        )
        
        self.character_class = discord.ui.TextInput(
            label="Character Class",
            placeholder="e.g., Iop, Cra, Eniripsa, etc.",
            required=True,
            max_length=20
        )
        
        self.preferred_time = discord.ui.TextInput(
            label="Preferred Time",
            placeholder="When would you like to do this dungeon? (e.g., 'Now', 'In 2 hours', 'Tomorrow evening')",
            required=True,
            max_length=100,
            style=discord.TextStyle.paragraph
        )
        
        self.confirmation = discord.ui.TextInput(
            label="Confirm Your Spot",
            placeholder="Type 'CONFIRM' to verify you want to request help for this dungeon",
            required=True,
            max_length=10
        )
        
        # Add all inputs to the modal
        self.add_item(self.ingame_name)
        self.add_item(self.character_class)
        self.add_item(self.preferred_time)
        self.add_item(self.confirmation)
    
    async def on_submit(self, interaction: discord.Interaction):
        """Handle the form submission and create the thread."""
        # Validate confirmation
        if self.confirmation.value.upper() != "CONFIRM":
            return await interaction.response.send_message(
                "❌ You must type 'CONFIRM' to proceed with the request.", 
                ephemeral=True
            )
        
        # Validate character class (case insensitive)
        provided_class = self.character_class.value.strip()
        valid_class = None
        for cls in CHARACTER_CLASSES:
            if cls.lower() == provided_class.lower():
                valid_class = cls
                break
        
        if not valid_class:
            class_list = ", ".join(CHARACTER_CLASSES[:10]) + "..."  # Show first 10 classes
            return await interaction.response.send_message(
                f"❌ Invalid character class. Please use one of: {class_list}", 
                ephemeral=True
            )
        
        dungeon_name = self.dungeon_data["name"]
        thread_name = f"[F3] {dungeon_name} — {self.ingame_name.value} ({valid_class})"
        thread_name = thread_name[:100]  # Discord limit
        
        try:
            # Create a public thread in the same channel
            thread = await self.base_channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.public_thread,
                auto_archive_duration=AUTO_ARCHIVE_MINUTES,
                reason=f"Dungeon help request by {interaction.user} for {dungeon_name}",
            )

            # Persist requester mapping in memory and in a thread message marker
            self.cog.thread_requesters[thread.id] = interaction.user.id

            # Compose a single text message that includes actual pings + durable markers
            role_mention = f"<@&{HELPER_ROLE_ID}>"
            requester_mention = interaction.user.mention
            marker_line = f"REQUESTER_ID:{interaction.user.id} | DUNGEON_KEY:{self.dungeon_key}"

            intro_content = (
                f"{requester_mention} requested help for **{dungeon_name}**. {role_mention}\n"
                f"{marker_line}"
            )

            # Enhanced embed with user-provided details
            embed = discord.Embed(
                title=f"🏰 Dungeon Help Request: {dungeon_name}",
                color=discord.Color.blue(),
                timestamp=utcnow(),
            )
            
            # User information section
            embed.add_field(
                name="👤 Requester Information",
                value=(
                    f"**Discord:** {requester_mention}\n"
                    f"**In-Game:** {self.ingame_name.value}\n"
                    f"**Class:** {valid_class}\n"
                    f"**Preferred Time:** {self.preferred_time.value}"
                ),
                inline=False,
            )
            
            # Service details
            embed.add_field(
                name="⏱️ Service Information",
                value=(
                    f"**Dungeon:** {dungeon_name}\n"
                    f"**Estimated Time:** 6-24 hours\n"
                    f"**Created:** <t:{int(utcnow().timestamp())}:R>"
                ),
                inline=False,
            )
            
            embed.add_field(
                name="👥 Helpers Needed", 
                value=f"{role_mention}\nHelpers will be assigned soon!", 
                inline=False
            )
            
            embed.add_field(
                name="📋 Instructions",
                value=(
                    "• Coordinate the run details here\n"
                    "• Keys will be provided by Life Alliance\n"
                    "• This is a **fast-run service** (no achievements/challenges)\n"
                    "• Post a victory screenshot when completed\n"
                    "• Use `/close` to archive this thread when finished"
                ),
                inline=False,
            )
            
            embed.add_field(
                name="⚠️ Important Notes",
                value=(
                    "• Service time estimation: **6-24 hours**\n"
                    "• Please be patient and available when helpers are ready\n"
                    "• This service is **free for Life Alliance members**"
                ),
                inline=False,
            )
            
            embed.set_footer(text="Life Alliance • Fast Run Service")
            if interaction.user.avatar:
                embed.set_thumbnail(url=interaction.user.avatar.url)

            # Send the ping + enhanced embed
            await thread.send(content=intro_content, embed=embed, allowed_mentions=ALLOWED_MENTIONS)

            # Ephemeral confirmation to requester with enhanced details
            confirm = discord.Embed(
                title="✅ Request Created Successfully",
                description=f"Your request for **{dungeon_name}** has been created: {thread.mention}",
                color=discord.Color.green(),
                timestamp=utcnow(),
            )
            confirm.add_field(
                name="📝 Your Details",
                value=(
                    f"**In-Game Name:** {self.ingame_name.value}\n"
                    f"**Class:** {valid_class}\n"
                    f"**Preferred Time:** {self.preferred_time.value}"
                ),
                inline=False,
            )
            confirm.add_field(
                name="⏱️ What's Next?",
                value=(
                    "• Helpers will be notified automatically\n"
                    "• Expected response time: 6-24 hours\n"
                    "• You'll receive a ping when helpers are ready"
                ),
                inline=False,
            )
            await interaction.response.send_message(embed=confirm, ephemeral=True)

            # Log to staff channel with enhanced information
            await self.cog.log_request(
                guild=interaction.guild,
                user=interaction.user,
                dungeon=dungeon_name,
                channel=self.base_channel,
                thread=thread,
                ingame_name=self.ingame_name.value,
                character_class=valid_class,
                preferred_time=self.preferred_time.value
            )

        except discord.Forbidden:
            logger.exception("Missing permissions to create/send in thread.")
            return await interaction.response.send_message(
                "❌ Error: I don't have permission to create or send messages in threads here.",
                ephemeral=True,
            )
        except discord.HTTPException as e:
            logger.exception("HTTPException while creating thread: %s", e)
            return await interaction.response.send_message(
                "❌ Error: Failed to create a help thread. Please try again or contact staff.",
                ephemeral=True,
            )
        except Exception:
            logger.exception("Unexpected error in DungeonVerificationModal.")
            return await interaction.response.send_message(
                "❌ Unexpected error. Please contact staff.",
                ephemeral=True,
            )


class DungeonButton(discord.ui.Button):
    """A persistent button for a specific dungeon."""

    def __init__(self, dungeon_key: str, dungeon_data: dict, cog: "DungeonCog"):
        emoji = discord.PartialEmoji(
            name=dungeon_data["name"].replace(" ", ""),
            id=dungeon_data["emoji_id"],
        )
        label = dungeon_data.get("label", dungeon_data["name"])
        custom_id = f"{CUSTOM_ID_PREFIX}:{dungeon_key}"

        super().__init__(
            style=discord.ButtonStyle.primary,
            label=label,
            emoji=emoji,
            custom_id=custom_id,
        )
        self.dungeon_key = dungeon_key
        self.dungeon_data = dungeon_data
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        """Handle a click on the dungeon button - show verification form."""
        # Guard: Ensure guild + channel availability
        if interaction.guild is None:
            return await interaction.response.send_message(
                "❌ Error: This can only be used in a server.", ephemeral=True
            )

        base_channel: Optional[discord.TextChannel] = None
        ch = interaction.channel

        # Only allow from a TextChannel (not from a thread or DM)
        if isinstance(ch, discord.TextChannel):
            base_channel = ch
        elif isinstance(ch, discord.Thread) and isinstance(ch.parent, discord.TextChannel):
            return await interaction.response.send_message(
                "❌ Please use the panel in a text channel to create a request.",
                ephemeral=True,
            )
        else:
            return await interaction.response.send_message(
                "❌ This isn't a supported channel for creating threads.",
                ephemeral=True,
            )

        # Global cooldown check (shared across all buttons)
        ok, remaining = self.cog.check_cooldown(interaction.user.id)
        if not ok:
            mins = int(remaining // 60)
            secs = int(remaining % 60)
            return await interaction.response.send_message(
                f"⏰ Cooldown active. Please wait {mins}m {secs}s before requesting help again.",
                ephemeral=True,
            )

        # Set cooldown immediately on click to prevent spamming
        self.cog.set_cooldown(interaction.user.id)

        # Show the verification modal
        modal = DungeonVerificationModal(self.dungeon_key, self.dungeon_data, self.cog, base_channel)
        await interaction.response.send_modal(modal)


class DungeonView(discord.ui.View):
    """Persistent view containing all dungeon buttons."""

    def __init__(self, cog: "DungeonCog"):
        super().__init__(timeout=None)  # persistent
        # Deterministic order
        for key in ("nileza", "missiz", "sylargh", "klime", "harebourg"):
            data = DUNGEONS[key]
            self.add_item(DungeonButton(key, data, cog))


class DungeonCog(commands.Cog):
    """Frigost 3 dungeon help system (persistent panel + ticket threads)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

        # Global per-user cooldowns (shared across all buttons)
        self._cooldowns: Dict[int, datetime] = {}

        # Thread -> requester mapping (in-memory) + persisted via message marker
        self.thread_requesters: Dict[int, int] = {}

        # Track if persistent view has been registered
        self._views_registered = False

    async def cog_load(self):
        """Register the persistent view at cog load."""
        if not self._views_registered:
            self.bot.add_view(DungeonView(self))
            self._views_registered = True
            logger.info("Persistent Frigost 3 dungeon view registered.")

        # Member intent sanity check
        if not getattr(self.bot.intents, "members", False):
            logger.warning(
                "Bot started without the Server Members Intent. "
                "Role checks and some user data may be unreliable."
            )

    # ===== Cooldown helpers =====
    def check_cooldown(self, user_id: int) -> Tuple[bool, float]:
        """Return (ok, seconds_remaining)."""
        now = utcnow()
        until = self._cooldowns.get(user_id)
        if not until:
            return True, 0.0
        if now >= until:
            self._cooldowns.pop(user_id, None)
            return True, 0.0
        remaining = (until - now).total_seconds()
        return False, remaining

    def set_cooldown(self, user_id: int):
        self._cooldowns[user_id] = utcnow() + timedelta(minutes=COOLDOWN_MINUTES)

    # ===== Logging =====
    async def log_request(
        self,
        guild: discord.Guild,
        user: discord.abc.User,
        dungeon: str,
        channel: discord.TextChannel,
        thread: discord.Thread,
        ingame_name: str = None,
        character_class: str = None,
        preferred_time: str = None,
    ):
        log_channel = guild.get_channel(LOG_CHANNEL_ID)
        if not isinstance(log_channel, (discord.TextChannel, discord.Thread)):
            logger.warning("Log channel %s not found or wrong type.", LOG_CHANNEL_ID)
            return

        embed = discord.Embed(
            title="🆕 New Dungeon Help Request",
            color=discord.Color.green(),
            timestamp=utcnow(),
        )
        embed.add_field(name="👤 Discord User", value=f"{user.mention} (`{user}`)", inline=True)
        embed.add_field(name="🏰 Dungeon", value=dungeon, inline=True)
        embed.add_field(name="📍 Origin", value=channel.mention, inline=True)
        
        if ingame_name:
            embed.add_field(name="🎮 In-Game Name", value=ingame_name, inline=True)
        if character_class:
            embed.add_field(name="⚔️ Character Class", value=character_class, inline=True)
        if preferred_time:
            embed.add_field(name="⏰ Preferred Time", value=preferred_time, inline=True)
            
        embed.add_field(name="🧵 Thread", value=thread.mention, inline=False)
        embed.set_footer(text=f"User ID: {user.id}")
        if isinstance(user, discord.Member) and user.display_avatar:
            embed.set_thumbnail(url=user.display_avatar.url)

        try:
            await log_channel.send(embed=embed)
        except Exception:
            logger.exception("Failed to send log message.")

    # ===== Utilities =====
    async def resolve_requester_id_from_thread(self, thread: discord.Thread) -> Optional[int]:
        """Resolve requester ID for a thread via in-memory map or by scanning messages."""
        # 1) In-memory first
        requester_id = self.thread_requesters.get(thread.id)
        if requester_id:
            return requester_id

        # 2) Scan thread history for marker
        try:
            async for msg in thread.history(limit=100, oldest_first=True):
                if msg.author.id == self.bot.user.id and msg.content:
                    m = REQUESTER_MARKER_RE.search(msg.content)
                    if m:
                        rid = int(m.group(1))
                        self.thread_requesters[thread.id] = rid
                        return rid
        except discord.HTTPException:
            logger.exception("Failed to scan thread history to resolve requester.")

        return None

    async def member_has_helper_role(self, member: discord.Member) -> bool:
        """Check helper role with fallbacks."""
        try:
            if any(r.id == HELPER_ROLE_ID for r in member.roles):
                return True
        except AttributeError:
            pass  # roles may be None in rare cases

        # Fallback: try refetching member (may still work without privileged intent)
        try:
            fresh = await member.guild.fetch_member(member.id)
            return any(r.id == HELPER_ROLE_ID for r in fresh.roles)
        except Exception:
            return False

    # ===== Commands =====
    @app_commands.command(name="dung", description="Display the Frigost 3 dungeon help panel.")
    async def dung_command(self, interaction: discord.Interaction):
        if interaction.guild is None:
            return await interaction.response.send_message(
                "❌ Error: This command can only be used in a server.", ephemeral=True
            )

        if not isinstance(interaction.channel, discord.TextChannel):
            return await interaction.response.send_message(
                "❌ Please use this in a text channel.", ephemeral=True
            )

        embed = discord.Embed(
            title="🏰 Frigost 3 Dungeon Help Panel",
            color=discord.Color.blue(),
            timestamp=utcnow(),
        )
        embed.description = (
            "**Free dungeon service for Life Alliance members!**\n\n"
            "🔑 **Dungeon keys provided** by the Alliance\n"
            "⚡ **Fast-run service** (no achievements, no challenges)\n"
            "🎯 **Purpose:** Access to Frigost 3 zones + Ice Dofus quest progression\n"
            "⏱️ **Service time:** 6-24 hours response time\n\n"
            "Click a dungeon button below to start your request!"
        )
        embed.add_field(
            name="📋 How to Request Help",
            value=(
                "1️⃣ Click a dungeon button below\n"
                "2️⃣ Fill out the verification form\n"
                "3️⃣ Wait for helpers to be assigned\n"
                "4️⃣ Coordinate and complete your run!"
            ),
            inline=False,
        )
        embed.add_field(
            name="ℹ️ What You'll Need to Provide",
            value=(
                "• Your in-game character name\n"
                "• Your character class\n"
                "• Preferred time for the run\n"
                "• Confirmation of your request"
            ),
            inline=False,
        )
        embed.set_image(url=BANNER_URL)
        embed.set_footer(text="Life Alliance • Dungeon Service")

        view = DungeonView(self)

        try:
            await interaction.response.send_message(embed=embed, view=view)
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ Error: I can't send the panel here (missing permissions).", ephemeral=True
            )
        except discord.HTTPException:
            await interaction.response.send_message(
                "❌ Error: Failed to send the panel. Please try again.", ephemeral=True
            )

    @app_commands.command(name="close", description="Close and archive the current dungeon help thread.")
    async def close_command(self, interaction: discord.Interaction):
        if interaction.guild is None or not isinstance(interaction.channel, discord.Thread):
            return await interaction.response.send_message(
                "❌ This command must be used inside a dungeon help thread.", ephemeral=True
            )

        thread: discord.Thread = interaction.channel

        # Determine if the user can close:
        # - requester of the thread
        # - helper role
        # - moderators (manage_threads)
        requester_id = await self.resolve_requester_id_from_thread(thread)
        is_requester = requester_id == interaction.user.id

        has_helper_role = False
        if isinstance(interaction.user, discord.Member):
            has_helper_role = await self.member_has_helper_role(interaction.user)

        is_moderator = (
            isinstance(interaction.user, discord.Member)
            and interaction.user.guild_permissions.manage_threads
        )

        if not (is_requester or has_helper_role or is_moderator):
            return await interaction.response.send_message(
                "Only the requester, helpers, or moderators can close this thread.",
                ephemeral=True,
            )

        try:
            await interaction.response.send_message(
                "Thread will be archived shortly…", ephemeral=True
            )
            await asyncio.sleep(2)
            await thread.edit(archived=True, locked=True, reason=f"Closed by {interaction.user}")
        except discord.HTTPException:
            return await interaction.followup.send(
                "Failed to archive this thread. Please try again or contact staff.",
                ephemeral=True,
            )


async def setup(bot: commands.Bot):
    """discord.py extension entrypoint."""
    await bot.add_cog(DungeonCog(bot))
    logger.info("DungeonCog loaded with verification system.")
