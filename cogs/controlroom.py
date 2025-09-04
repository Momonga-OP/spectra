import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from typing import Optional

class ControlRoom(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="controlroom", description="Open the server control room panel")
    @app_commands.describe(
        persistent="Whether the control room should stay active after bot restart (default: False)"
    )
    async def controlroom(self, interaction: discord.Interaction, persistent: bool = False):
        """Opens the main control room panel"""
        
        # Check if user has administrator permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need administrator permissions to access the control room.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🎛️ Server Control Room",
            description="Welcome to the server control panel. Use the buttons below to manage various server functions.",
            color=0x2F3136
        )
        
        embed.add_field(
            name="🔒 Channel Management", 
            value="Lock/Unlock channels, manage permissions", 
            inline=True
        )
        
        embed.add_field(
            name="🎭 Role Management", 
            value="Create roles, assign colors, manage permissions", 
            inline=True
        )
        
        embed.add_field(
            name="📢 Server Announcements", 
            value="Send announcements to specific channels", 
            inline=True
        )
        
        embed.add_field(
            name="🎵 Voice Management", 
            value="Create temporary voice channels, manage voice settings", 
            inline=True
        )
        
        embed.add_field(
            name="🎨 Server Customization", 
            value="Update server settings, manage emojis", 
            inline=True
        )
        
        embed.add_field(
            name="📊 Server Statistics", 
            value="View detailed server analytics", 
            inline=True
        )

        embed.set_footer(text=f"Control Room accessed by {interaction.user.display_name}")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)

        view = ControlRoomView(persistent=persistent)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)

class ControlRoomView(discord.ui.View):
    def __init__(self, persistent: bool = False):
        super().__init__(timeout=300 if not persistent else None)
        self.persistent = persistent

    @discord.ui.button(label="🔒 Channel Control", style=discord.ButtonStyle.primary, row=0)
    async def channel_control(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ChannelControlView()
        embed = discord.Embed(
            title="🔒 Channel Control Panel",
            description="Select a channel management action:",
            color=0x5865F2
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🎭 Role Manager", style=discord.ButtonStyle.primary, row=0)
    async def role_manager(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = RoleManagerView()
        embed = discord.Embed(
            title="🎭 Role Management Panel",
            description="Manage server roles and permissions:",
            color=0x5865F2
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="📢 Announcements", style=discord.ButtonStyle.success, row=0)
    async def announcements(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = AnnouncementView()
        embed = discord.Embed(
            title="📢 Announcement System",
            description="Send announcements to your server:",
            color=0x57F287
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🎵 Voice Control", style=discord.ButtonStyle.secondary, row=1)
    async def voice_control(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = VoiceControlView()
        embed = discord.Embed(
            title="🎵 Voice Channel Management",
            description="Manage voice channels and settings:",
            color=0x95A5A6
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="🎨 Server Settings", style=discord.ButtonStyle.secondary, row=1)
    async def server_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ServerSettingsView()
        embed = discord.Embed(
            title="🎨 Server Customization",
            description="Customize your server settings:",
            color=0x95A5A6
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="📊 Statistics", style=discord.ButtonStyle.secondary, row=1)
    async def statistics(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📊 Server Statistics",
            color=0xF39C12
        )
        
        guild = interaction.guild
        
        # Basic stats
        embed.add_field(name="👥 Total Members", value=f"{guild.member_count}", inline=True)
        embed.add_field(name="💬 Text Channels", value=f"{len(guild.text_channels)}", inline=True)
        embed.add_field(name="🎵 Voice Channels", value=f"{len(guild.voice_channels)}", inline=True)
        embed.add_field(name="🎭 Roles", value=f"{len(guild.roles)}", inline=True)
        embed.add_field(name="😀 Emojis", value=f"{len(guild.emojis)}", inline=True)
        embed.add_field(name="🚀 Boost Level", value=f"Level {guild.premium_tier}", inline=True)
        
        # Member status
        online = len([m for m in guild.members if m.status == discord.Status.online])
        idle = len([m for m in guild.members if m.status == discord.Status.idle])
        dnd = len([m for m in guild.members if m.status == discord.Status.dnd])
        offline = len([m for m in guild.members if m.status == discord.Status.offline])
        
        embed.add_field(
            name="👥 Member Status", 
            value=f"🟢 Online: {online}\n🟡 Idle: {idle}\n🔴 DND: {dnd}\n⚫ Offline: {offline}", 
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ChannelControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="🔒 Lock Channel", style=discord.ButtonStyle.danger)
    async def lock_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ChannelSelectView(action="lock")
        await interaction.response.send_message("Select a channel to lock:", view=view, ephemeral=True)

    @discord.ui.button(label="🔓 Unlock Channel", style=discord.ButtonStyle.success)
    async def unlock_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ChannelSelectView(action="unlock")
        await interaction.response.send_message("Select a channel to unlock:", view=view, ephemeral=True)

    @discord.ui.button(label="👁️ Hide Channel", style=discord.ButtonStyle.secondary)
    async def hide_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ChannelSelectView(action="hide")
        await interaction.response.send_message("Select a channel to hide:", view=view, ephemeral=True)

    @discord.ui.button(label="👀 Show Channel", style=discord.ButtonStyle.primary)
    async def show_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = ChannelSelectView(action="show")
        await interaction.response.send_message("Select a channel to show:", view=view, ephemeral=True)

class ChannelSelectView(discord.ui.View):
    def __init__(self, action: str):
        super().__init__(timeout=300)
        self.action = action

    @discord.ui.select(placeholder="Choose a channel...", cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.text])
    async def select_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        channel = select.values[0]
        
        try:
            if self.action == "lock":
                await channel.set_permissions(interaction.guild.default_role, send_messages=False)
                await interaction.response.send_message(f"🔒 Successfully locked {channel.mention}", ephemeral=True)
                
            elif self.action == "unlock":
                await channel.set_permissions(interaction.guild.default_role, send_messages=True)
                await interaction.response.send_message(f"🔓 Successfully unlocked {channel.mention}", ephemeral=True)
                
            elif self.action == "hide":
                await channel.set_permissions(interaction.guild.default_role, view_channel=False)
                await interaction.response.send_message(f"👁️ Successfully hid {channel.name}", ephemeral=True)
                
            elif self.action == "show":
                await channel.set_permissions(interaction.guild.default_role, view_channel=True)
                await interaction.response.send_message(f"👀 Successfully showed {channel.mention}", ephemeral=True)
                
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to modify that channel.", ephemeral=True)

class RoleManagerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="🎨 Create Role", style=discord.ButtonStyle.primary)
    async def create_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CreateRoleModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🌈 Role Colors", style=discord.ButtonStyle.secondary)
    async def role_colors(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = RoleColorView()
        await interaction.response.send_message("Select a role to change its color:", view=view, ephemeral=True)

    @discord.ui.button(label="🔄 Mass Role Assign", style=discord.ButtonStyle.success)
    async def mass_assign(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = MassRoleView()
        await interaction.response.send_message("Mass role assignment:", view=view, ephemeral=True)

class CreateRoleModal(discord.ui.Modal, title='Create New Role'):
    def __init__(self):
        super().__init__()

    name = discord.ui.TextInput(label='Role Name', placeholder='Enter role name...', required=True, max_length=100)
    color = discord.ui.TextInput(label='Role Color (Hex)', placeholder='#FF5733 or red, blue, green...', required=False, max_length=20)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse color
            color_value = discord.Color.default()
            if self.color.value:
                if self.color.value.startswith('#'):
                    color_value = discord.Color(int(self.color.value[1:], 16))
                else:
                    color_map = {
                        'red': discord.Color.red(),
                        'blue': discord.Color.blue(),
                        'green': discord.Color.green(),
                        'yellow': discord.Color.yellow(),
                        'purple': discord.Color.purple(),
                        'orange': discord.Color.orange(),
                    }
                    color_value = color_map.get(self.color.value.lower(), discord.Color.default())

            role = await interaction.guild.create_role(name=self.name.value, color=color_value)
            await interaction.response.send_message(f"✅ Successfully created role {role.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to create role: {str(e)}", ephemeral=True)

class RoleColorView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(placeholder="Choose a role...", cls=discord.ui.RoleSelect)
    async def select_role(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        role = select.values[0]
        view = ColorPickerView(role)
        embed = discord.Embed(
            title=f"🌈 Color Picker for {role.name}",
            description="Choose a new color for this role:",
            color=role.color
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class ColorPickerView(discord.ui.View):
    def __init__(self, role: discord.Role):
        super().__init__(timeout=300)
        self.role = role

    @discord.ui.button(label="🔴", style=discord.ButtonStyle.danger)
    async def red(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.change_color(interaction, discord.Color.red(), "Red")

    @discord.ui.button(label="🔵", style=discord.ButtonStyle.primary)
    async def blue(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.change_color(interaction, discord.Color.blue(), "Blue")

    @discord.ui.button(label="🟢", style=discord.ButtonStyle.success)
    async def green(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.change_color(interaction, discord.Color.green(), "Green")

    @discord.ui.button(label="🟡", style=discord.ButtonStyle.secondary)
    async def yellow(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.change_color(interaction, discord.Color.yellow(), "Yellow")

    @discord.ui.button(label="🟣", style=discord.ButtonStyle.secondary)
    async def purple(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.change_color(interaction, discord.Color.purple(), "Purple")

    async def change_color(self, interaction: discord.Interaction, color: discord.Color, color_name: str):
        try:
            await self.role.edit(color=color)
            await interaction.response.send_message(f"✅ Changed {self.role.mention} color to {color_name}!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to edit that role.", ephemeral=True)

class MassRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.select(placeholder="Choose a role to mass assign...", cls=discord.ui.RoleSelect)
    async def select_role(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        role = select.values[0]
        view = MassAssignmentView(role)
        await interaction.response.send_message(f"Mass assignment options for {role.mention}:", view=view, ephemeral=True)

class MassAssignmentView(discord.ui.View):
    def __init__(self, role: discord.Role):
        super().__init__(timeout=300)
        self.role = role

    @discord.ui.button(label="👥 All Members", style=discord.ButtonStyle.primary)
    async def assign_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        count = 0
        for member in interaction.guild.members:
            if not member.bot and self.role not in member.roles:
                try:
                    await member.add_roles(self.role)
                    count += 1
                except:
                    pass
        await interaction.followup.send(f"✅ Assigned {self.role.mention} to {count} members!", ephemeral=True)

    @discord.ui.button(label="🤖 All Bots", style=discord.ButtonStyle.secondary)
    async def assign_bots(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        count = 0
        for member in interaction.guild.members:
            if member.bot and self.role not in member.roles:
                try:
                    await member.add_roles(self.role)
                    count += 1
                except:
                    pass
        await interaction.followup.send(f"✅ Assigned {self.role.mention} to {count} bots!", ephemeral=True)

    @discord.ui.button(label="🟢 Online Members", style=discord.ButtonStyle.success)
    async def assign_online(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        count = 0
        for member in interaction.guild.members:
            if member.status == discord.Status.online and self.role not in member.roles:
                try:
                    await member.add_roles(self.role)
                    count += 1
                except:
                    pass
        await interaction.followup.send(f"✅ Assigned {self.role.mention} to {count} online members!", ephemeral=True)

class AnnouncementView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="📢 Send Announcement", style=discord.ButtonStyle.primary)
    async def send_announcement(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = AnnouncementModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="📌 Send Embed", style=discord.ButtonStyle.success)
    async def send_embed(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = EmbedModal()
        await interaction.response.send_modal(modal)

class AnnouncementModal(discord.ui.Modal, title='Send Announcement'):
    def __init__(self):
        super().__init__()

    channel = discord.ui.TextInput(label='Channel Name', placeholder='general, announcements, etc...', required=True)
    message = discord.ui.TextInput(label='Message', placeholder='Your announcement message...', required=True, style=discord.TextStyle.long, max_length=2000)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel = discord.utils.get(interaction.guild.text_channels, name=self.channel.value)
            if channel:
                await channel.send(self.message.value)
                await interaction.response.send_message(f"✅ Announcement sent to {channel.mention}!", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Channel '{self.channel.value}' not found!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to send announcement: {str(e)}", ephemeral=True)

class EmbedModal(discord.ui.Modal, title='Send Embed Message'):
    def __init__(self):
        super().__init__()

    channel = discord.ui.TextInput(label='Channel Name', placeholder='general, announcements, etc...', required=True)
    title = discord.ui.TextInput(label='Embed Title', placeholder='Announcement Title', required=True, max_length=256)
    description = discord.ui.TextInput(label='Embed Description', placeholder='Your message here...', required=True, style=discord.TextStyle.long, max_length=2048)
    color = discord.ui.TextInput(label='Embed Color (Hex)', placeholder='#FF5733', required=False)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            channel = discord.utils.get(interaction.guild.text_channels, name=self.channel.value)
            if not channel:
                await interaction.response.send_message(f"❌ Channel '{self.channel.value}' not found!", ephemeral=True)
                return

            # Parse color
            color_value = discord.Color.blue()
            if self.color.value and self.color.value.startswith('#'):
                try:
                    color_value = discord.Color(int(self.color.value[1:], 16))
                except:
                    pass

            embed = discord.Embed(
                title=self.title.value,
                description=self.description.value,
                color=color_value
            )
            embed.set_footer(text=f"Sent by {interaction.user.display_name}")
            
            await channel.send(embed=embed)
            await interaction.response.send_message(f"✅ Embed sent to {channel.mention}!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to send embed: {str(e)}", ephemeral=True)

class VoiceControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="🎤 Create Voice Channel", style=discord.ButtonStyle.primary)
    async def create_voice(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = CreateVoiceModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🔇 Mute All in VC", style=discord.ButtonStyle.danger)
    async def mute_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = VoiceChannelSelectView(action="mute")
        await interaction.response.send_message("Select a voice channel to mute all members:", view=view, ephemeral=True)

    @discord.ui.button(label="🔊 Unmute All in VC", style=discord.ButtonStyle.success)
    async def unmute_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = VoiceChannelSelectView(action="unmute")
        await interaction.response.send_message("Select a voice channel to unmute all members:", view=view, ephemeral=True)

    @discord.ui.button(label="🚫 Disconnect All", style=discord.ButtonStyle.secondary)
    async def disconnect_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = VoiceChannelSelectView(action="disconnect")
        await interaction.response.send_message("Select a voice channel to disconnect all members:", view=view, ephemeral=True)

class CreateVoiceModal(discord.ui.Modal, title='Create Voice Channel'):
    def __init__(self):
        super().__init__()

    name = discord.ui.TextInput(label='Channel Name', placeholder='Voice Channel Name', required=True, max_length=100)
    limit = discord.ui.TextInput(label='User Limit (0 = unlimited)', placeholder='0', required=False)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_limit = 0
            if self.limit.value and self.limit.value.isdigit():
                user_limit = min(int(self.limit.value), 99)

            channel = await interaction.guild.create_voice_channel(
                name=self.name.value,
                user_limit=user_limit
            )
            await interaction.response.send_message(f"✅ Created voice channel: {channel.name}", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to create voice channel: {str(e)}", ephemeral=True)

class VoiceChannelSelectView(discord.ui.View):
    def __init__(self, action: str):
        super().__init__(timeout=300)
        self.action = action

    @discord.ui.select(placeholder="Choose a voice channel...", cls=discord.ui.ChannelSelect, channel_types=[discord.ChannelType.voice])
    async def select_voice_channel(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        channel = select.values[0]
        
        try:
            if self.action == "mute":
                count = 0
                for member in channel.members:
                    if not member.voice.mute:
                        await member.edit(mute=True)
                        count += 1
                await interaction.response.send_message(f"🔇 Muted {count} members in {channel.name}", ephemeral=True)
                
            elif self.action == "unmute":
                count = 0
                for member in channel.members:
                    if member.voice.mute:
                        await member.edit(mute=False)
                        count += 1
                await interaction.response.send_message(f"🔊 Unmuted {count} members in {channel.name}", ephemeral=True)
                
            elif self.action == "disconnect":
                count = len(channel.members)
                for member in channel.members:
                    await member.edit(voice_channel=None)
                await interaction.response.send_message(f"🚫 Disconnected {count} members from {channel.name}", ephemeral=True)
                
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to manage that voice channel.", ephemeral=True)

class ServerSettingsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300)

    @discord.ui.button(label="📝 Change Server Name", style=discord.ButtonStyle.primary)
    async def change_name(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ServerNameModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🎭 Manage Emojis", style=discord.ButtonStyle.secondary)
    async def manage_emojis(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🎭 Server Emojis",
            description=f"Total emojis: {len(interaction.guild.emojis)}/{interaction.guild.emoji_limit}",
            color=0x95A5A6
        )
        
        if interaction.guild.emojis:
            emoji_list = " ".join([str(emoji) for emoji in interaction.guild.emojis[:20]])  # Show first 20
            embed.add_field(name="Emojis", value=emoji_list, inline=False)
            if len(interaction.guild.emojis) > 20:
                embed.add_field(name="Note", value=f"Showing first 20 of {len(interaction.guild.emojis)} emojis", inline=False)
        else:
            embed.add_field(name="Emojis", value="No custom emojis", inline=False)
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🌟 Server Boost Info", style=discord.ButtonStyle.success)
    async def boost_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        embed = discord.Embed(
            title="🌟 Server Boost Information",
            color=0xF47FFF
        )
        
        embed.add_field(name="Boost Level", value=f"Level {guild.premium_tier}", inline=True)
        embed.add_field(name="Boosts", value=f"{guild.premium_subscription_count}", inline=True)
        embed.add_field(name="Boosters", value=f"{len(guild.premium_subscribers)}", inline=True)
        
        # Boost benefits
        benefits = []
        if guild.premium_tier >= 1:
            benefits.append("• 50 custom emojis")
            benefits.append("• 128 Kbps audio quality")
        if guild.premium_tier >= 2:
            benefits.append("• 150 custom emojis")
            benefits.append("• 256 Kbps audio quality")
            benefits.append("• Server banner")
        if guild.premium_tier >= 3:
            benefits.append("• 250 custom emojis")
            benefits.append("• 384 Kbps audio quality")
            benefits.append("• Vanity URL")
        
        if benefits:
            embed.add_field(name="Current Benefits", value="\n".join(benefits), inline=False)
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ServerNameModal(discord.ui.Modal, title='Change Server Name'):
    def __init__(self):
        super().__init__()

    name = discord.ui.TextInput(label='New Server Name', placeholder='Enter new server name...', required=True, max_length=100)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            old_name = interaction.guild.name
            await interaction.guild.edit(name=self.name.value)
            await interaction.response.send_message(f"✅ Server name changed from '{old_name}' to '{self.name.value}'!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to change the server name.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to change server name: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ControlRoom(bot))
