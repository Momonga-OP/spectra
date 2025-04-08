import discord
from discord.ext import commands
from discord import app_commands, ui
import asyncio
import logging

logger = logging.getLogger(__name__)

class VoiceMasterButtons(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)  # Persistent view that doesn't timeout
        self.bot = bot

    @ui.button(label="", emoji="🔒", style=discord.ButtonStyle.gray, custom_id="voicemaster:lock", row=0)
    async def lock_channel(self, interaction: discord.Interaction, button: ui.Button):
        """Lock the voice channel"""
        if not interaction.user.voice:
            return await interaction.response.send_message("You need to be in a voice channel to use this!", ephemeral=True)
            
        voice_channel = interaction.user.voice.channel
        overwrites = voice_channel.overwrites
        overwrites[interaction.guild.default_role] = discord.PermissionOverwrite(connect=False)
        
        await voice_channel.edit(overwrites=overwrites)
        await interaction.response.send_message(f"Voice channel {voice_channel.name} has been locked!", ephemeral=True)

    @ui.button(label="", emoji="🔓", style=discord.ButtonStyle.gray, custom_id="voicemaster:unlock", row=0)
    async def unlock_channel(self, interaction: discord.Interaction, button: ui.Button):
        """Unlock the voice channel"""
        if not interaction.user.voice:
            return await interaction.response.send_message("You need to be in a voice channel to use this!", ephemeral=True)
            
        voice_channel = interaction.user.voice.channel
        overwrites = voice_channel.overwrites
        overwrites[interaction.guild.default_role] = discord.PermissionOverwrite(connect=True)
        
        await voice_channel.edit(overwrites=overwrites)
        await interaction.response.send_message(f"Voice channel {voice_channel.name} has been unlocked!", ephemeral=True)

    @ui.button(label="", emoji="👻", style=discord.ButtonStyle.gray, custom_id="voicemaster:ghost", row=0)
    async def ghost_channel(self, interaction: discord.Interaction, button: ui.Button):
        """Ghost the voice channel"""
        if not interaction.user.voice:
            return await interaction.response.send_message("You need to be in a voice channel to use this!", ephemeral=True)
            
        voice_channel = interaction.user.voice.channel
        overwrites = voice_channel.overwrites
        overwrites[interaction.guild.default_role] = discord.PermissionOverwrite(connect=False, view_channel=False)
        
        await voice_channel.edit(overwrites=overwrites)
        await interaction.response.send_message(f"Voice channel {voice_channel.name} has been ghosted!", ephemeral=True)

    @ui.button(label="", emoji="👁️", style=discord.ButtonStyle.gray, custom_id="voicemaster:reveal", row=0)
    async def reveal_channel(self, interaction: discord.Interaction, button: ui.Button):
        """Reveal the voice channel"""
        if not interaction.user.voice:
            return await interaction.response.send_message("You need to be in a voice channel to use this!", ephemeral=True)
            
        voice_channel = interaction.user.voice.channel
        overwrites = voice_channel.overwrites
        overwrites[interaction.guild.default_role] = discord.PermissionOverwrite(view_channel=True)
        
        await voice_channel.edit(overwrites=overwrites)
        await interaction.response.send_message(f"Voice channel {voice_channel.name} is now visible to everyone!", ephemeral=True)

    @ui.button(label="", emoji="🔑", style=discord.ButtonStyle.gray, custom_id="voicemaster:claim", row=0)
    async def claim_channel(self, interaction: discord.Interaction, button: ui.Button):
        """Claim the voice channel"""
        if not interaction.user.voice:
            return await interaction.response.send_message("You need to be in a voice channel to use this!", ephemeral=True)
            
        voice_channel = interaction.user.voice.channel
        
        # Give management permissions to the user who claimed it
        overwrites = voice_channel.overwrites
        overwrites[interaction.user] = discord.PermissionOverwrite(
            manage_channels=True,
            manage_permissions=True,
            mute_members=True,
            deafen_members=True,
            move_members=True
        )
        
        await voice_channel.edit(overwrites=overwrites)
        await interaction.response.send_message(f"You have claimed ownership of {voice_channel.name}!", ephemeral=True)

    @ui.button(label="", emoji="🔌", style=discord.ButtonStyle.gray, custom_id="voicemaster:disconnect", row=1)
    async def disconnect_member(self, interaction: discord.Interaction, button: ui.Button):
        """Disconnect a member"""
        if not interaction.user.voice:
            return await interaction.response.send_message("You need to be in a voice channel to use this!", ephemeral=True)
            
        # Create a modal to get the member to disconnect
        modal = DisconnectMemberModal(interaction.user.voice.channel)
        await interaction.response.send_modal(modal)

    @ui.button(label="", emoji="🎮", style=discord.ButtonStyle.gray, custom_id="voicemaster:start", row=1)
    async def start_activity(self, interaction: discord.Interaction, button: ui.Button):
        """Start an activity"""
        if not interaction.user.voice:
            return await interaction.response.send_message("You need to be in a voice channel to use this!", ephemeral=True)
            
        # List of available activities
        activities = [
            ("YouTube Together", "880218394199220334"),
            ("Poker Night", "755827207812677713"),
            ("Chess", "832012774040141894"),
            ("Letter League", "879863686565621790"),
            ("Word Snacks", "879863976006127627"),
            ("Sketch Heads", "902271654783242291"),
            ("Awkword", "879863881349087252")
        ]
            
        # Create a select menu for activities
        activity_select = ActivitySelect(activities)
        view = discord.ui.View()
        view.add_item(activity_select)
        
        await interaction.response.send_message("Select an activity to start:", view=view, ephemeral=True)

    @ui.button(label="", emoji="ℹ️", style=discord.ButtonStyle.gray, custom_id="voicemaster:info", row=1)
    async def view_info(self, interaction: discord.Interaction, button: ui.Button):
        """View voice channel info"""
        if not interaction.user.voice:
            return await interaction.response.send_message("You need to be in a voice channel to use this!", ephemeral=True)
            
        voice_channel = interaction.user.voice.channel
        
        # Get member info
        members = voice_channel.members
        member_count = len(members)
        
        # Create an embed with voice channel info
        embed = discord.Embed(
            title=f"Voice Channel: {voice_channel.name}",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Member Count", value=f"{member_count}/{voice_channel.user_limit if voice_channel.user_limit else '∞'}", inline=False)
        embed.add_field(name="Bitrate", value=f"{voice_channel.bitrate // 1000} kbps", inline=False)
        
        # List members if not too many
        if member_count <= 15:
            member_list = "\n".join([f"• {member.display_name}" for member in members])
            embed.add_field(name="Members", value=member_list if member_list else "No members", inline=False)
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @ui.button(label="", emoji="➕", style=discord.ButtonStyle.gray, custom_id="voicemaster:increase", row=1)
    async def increase_limit(self, interaction: discord.Interaction, button: ui.Button):
        """Increase user limit"""
        if not interaction.user.voice:
            return await interaction.response.send_message("You need to be in a voice channel to use this!", ephemeral=True)
            
        voice_channel = interaction.user.voice.channel
        current_limit = voice_channel.user_limit
        
        # If no limit is set (0), set it to 2
        new_limit = 2 if current_limit == 0 else min(99, current_limit + 1)
        
        await voice_channel.edit(user_limit=new_limit)
        await interaction.response.send_message(f"User limit for {voice_channel.name} has been increased to {new_limit}!", ephemeral=True)

    @ui.button(label="", emoji="➖", style=discord.ButtonStyle.gray, custom_id="voicemaster:decrease", row=1)
    async def decrease_limit(self, interaction: discord.Interaction, button: ui.Button):
        """Decrease user limit"""
        if not interaction.user.voice:
            return await interaction.response.send_message("You need to be in a voice channel to use this!", ephemeral=True)
            
        voice_channel = interaction.user.voice.channel
        current_limit = voice_channel.user_limit
        
        # If current limit is 0 (unlimited) or 1, we can't decrease further
        if current_limit <= 1:
            await interaction.response.send_message(f"Cannot decrease the user limit for {voice_channel.name} any further!", ephemeral=True)
            return
            
        new_limit = current_limit - 1
        await voice_channel.edit(user_limit=new_limit)
        await interaction.response.send_message(f"User limit for {voice_channel.name} has been decreased to {new_limit}!", ephemeral=True)


class DisconnectMemberModal(ui.Modal, title="Disconnect Member"):
    member_name = ui.TextInput(label="Enter the member's name", placeholder="Type the username here")
    
    def __init__(self, voice_channel):
        super().__init__()
        self.voice_channel = voice_channel
        
    async def on_submit(self, interaction: discord.Interaction):
        member_name = self.member_name.value.lower()
        
        # Find the member in the voice channel
        target = None
        for member in self.voice_channel.members:
            if member.name.lower() == member_name or member.display_name.lower() == member_name:
                target = member
                break
        
        if not target:
            await interaction.response.send_message(f"Could not find a member named '{self.member_name.value}' in the voice channel.", ephemeral=True)
            return
            
        try:
            await target.move_to(None)  # Disconnect the member
            await interaction.response.send_message(f"Successfully disconnected {target.display_name} from the voice channel!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(f"I don't have permission to disconnect {target.display_name}.", ephemeral=True)


class ActivitySelect(ui.Select):
    def __init__(self, activities):
        options = [
            discord.SelectOption(label=name, value=app_id)
            for name, app_id in activities
        ]
        super().__init__(placeholder="Choose an activity...", min_values=1, max_values=1, options=options)
        
    async def callback(self, interaction: discord.Interaction):
        activity_id = self.values[0]
        
        # Create invite for the activity
        try:
            invite = await interaction.user.voice.channel.create_invite(
                target_type=discord.InviteTarget.embedded_application,
                target_application_id=int(activity_id)
            )
            await interaction.response.send_message(f"Activity started! Join here: {invite.url}", ephemeral=False)
        except discord.Forbidden:
            await interaction.response.send_message("I don't have permission to create invites for this channel.", ephemeral=True)
        except discord.HTTPException as e:
            await interaction.response.send_message(f"Failed to create activity: {e}", ephemeral=True)


class VoiceChannel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    async def cog_load(self):
        # Create and register the persistent view
        self.bot.add_view(VoiceMasterButtons(self.bot))
        logger.info("VoiceChannel cog loaded successfully")
    
    @app_commands.command(name="voicemaster", description="Create a voice control interface")
    @app_commands.default_permissions(manage_channels=True)
    async def voicemaster(self, interaction: discord.Interaction):
        """Creates an interface for controlling voice channels"""
        embed = discord.Embed(
            title="VoiceMaster Interface",
            description="Use the buttons below to control your voice channel.",
            color=discord.Color.dark_gray()
        )
        
        # Add an image URL that resembles the waveform in your image
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/123456789/123456789/waveform_icon.png")
        
        embed.add_field(name="Button Usage", value="""
🔒 — Lock  the voice channel
🔓 — Unlock  the voice channel
👻 — Ghost  the voice channel
👁️ — Reveal  the voice channel
🔑 — Claim  the voice channel
🔌 — Disconnect  a member
🎮 — Start  an activity
ℹ️ — View  channel information
➕ — Increase  the user limit
➖ — Decrease  the user limit
        """, inline=False)

        view = VoiceMasterButtons(self.bot)
        
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(VoiceChannel(bot))
