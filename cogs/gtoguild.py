import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import random
from typing import Dict, Any
from datetime import datetime

# Server Configuration
GUILD_CONFIG: Dict[str, Any] = {
    "id": 1213699457233985587,
    "ping_channel_id": 1387971918417891368,
    "alert_channel_id": 1398025562206765208,
}

# Guild Roles
GUILD_ROLES = {
    1213699577568428074: "Tight",
    1231487845798248458: "Guardians",
    1255591594179170407: "Perfect Guild",
    1387964877770981439: "Sausage Finger",
    1397597190779699200: "SAQ",
    1397689982721851602: "The Trenches",
    1231573508556066847: "EV",
    1392462864429744238: "Punishment",
    1231573194687774851: "Demigods",
    1231740379515322418: "Nemesis",
    1364708638668619786: "Imperium",
    1394808571308412948: "Thieves",
    1325581624129097872: "Sparta",
    1357443037311275108: "Italians",
    1231573740018470962: "Krosmic Flux",
    1366855660632936468: "Vendetta"
}

# Alert Messages
ALERT_MESSAGES = [
    "Alert: {role} - Action needed!",
    "Urgent: {role} - Please respond!",
    "Attention: {role} - Guild activity required!",
    "Notice: {role} - Your guild is being called!",
    "Alert: {role} - Time to gather!"
]

class NoteModal(Modal):
    """Modal for adding notes to alerts"""
    def __init__(self, message: discord.Message):
        super().__init__(title="Add Note", timeout=300)
        self.message = message

        self.note_title = TextInput(
            label="Note Title",
            placeholder="Brief title for your note",
            style=discord.TextStyle.short,
            max_length=50,
            required=True
        )

        self.note_content = TextInput(
            label="Note Details",
            placeholder="Add details about the situation",
            style=discord.TextStyle.paragraph,
            max_length=300,
            required=True
        )

        self.add_item(self.note_title)
        self.add_item(self.note_content)

    async def on_submit(self, interaction: discord.Interaction):
        """Process and add note to alert message"""
        try:
            embed = self.message.embeds[0]
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            note = (
                f"**{timestamp} | {interaction.user.display_name}**\n"
                f"**{self.note_title.value}**\n"
                f"{self.note_content.value}"
            )

            existing_notes = embed.fields[0].value if embed.fields else "No notes yet."
            updated_notes = f"{existing_notes}\n\n{note}"
            
            embed.clear_fields()
            embed.add_field(name="Notes", value=updated_notes, inline=False)
            
            await self.message.edit(embed=embed)
            await interaction.response.send_message(
                "Note added successfully!", 
                ephemeral=True
            )
        
        except Exception as e:
            await interaction.response.send_message(
                f"Error adding note: {e}", 
                ephemeral=True
            )

class AlertView(View):
    """Interactive view for guild alerts"""
    def __init__(self, bot: commands.Bot, message: discord.Message):
        super().__init__(timeout=None)
        self.bot = bot
        self.message = message
        self.is_resolved = False

        # Add Note button
        add_note_btn = Button(
            label="Add Note", 
            style=discord.ButtonStyle.blurple, 
            emoji="📝"
        )
        add_note_btn.callback = self.open_note_modal
        self.add_item(add_note_btn)

        # Resolved button
        resolved_btn = Button(
            label="Mark Resolved", 
            style=discord.ButtonStyle.green, 
            emoji="✅"
        )
        resolved_btn.callback = lambda i: self.resolve_alert(i, "Resolved", discord.Color.green())
        self.add_item(resolved_btn)

        # Failed button
        failed_btn = Button(
            label="Mark Failed", 
            style=discord.ButtonStyle.red, 
            emoji="❌"
        )
        failed_btn.callback = lambda i: self.resolve_alert(i, "Failed", discord.Color.red())
        self.add_item(failed_btn)

    async def open_note_modal(self, interaction: discord.Interaction):
        """Open note modal"""
        if interaction.channel_id != GUILD_CONFIG['alert_channel_id']:
            await interaction.response.send_message(
                "You can only add notes in the alert channel.", 
                ephemeral=True
            )
            return

        modal = NoteModal(self.message)
        await interaction.response.send_modal(modal)

    async def resolve_alert(self, interaction: discord.Interaction, status: str, color: discord.Color):
        """Resolve alert with status update"""
        if self.is_resolved:
            await interaction.response.send_message(
                "This alert has already been resolved.", 
                ephemeral=True
            )
            return

        self.is_resolved = True
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

        embed = self.message.embeds[0]
        embed.color = color
        embed.add_field(
            name="Status", 
            value=f"**Result:** {status}\n**Resolved by:** {interaction.user.mention}", 
            inline=False
        )
        embed.set_footer(text=f"Resolved at {datetime.now().strftime('%H:%M:%S')}")

        await self.message.edit(embed=embed)
        await interaction.response.send_message(
            f"Alert marked as **{status}**.", 
            ephemeral=True
        )

class GuildPingView(View):
    """Guild ping interface with buttons for each guild"""
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        
        # Create a button for each guild
        for role_id, guild_name in GUILD_ROLES.items():
            button = Button(
                label=guild_name,
                style=discord.ButtonStyle.secondary,
                custom_id=f"guild_ping_{role_id}"
            )
            button.callback = self.create_ping_callback(role_id, guild_name)
            self.add_item(button)

    def create_ping_callback(self, role_id: int, guild_name: str):
        """Generate callback for guild ping button"""
        async def callback(interaction: discord.Interaction):
            try:
                if interaction.guild_id != GUILD_CONFIG['id']:
                    await interaction.response.send_message(
                        "This command can only be used in this server.", 
                        ephemeral=True
                    )
                    return

                alert_channel = interaction.guild.get_channel(GUILD_CONFIG['alert_channel_id'])
                role = interaction.guild.get_role(role_id)

                if not alert_channel or not role:
                    await interaction.response.send_message(
                        "Could not find the alert channel or role.", 
                        ephemeral=True
                    )
                    return

                alert_message = random.choice(ALERT_MESSAGES).format(role=role.mention)
                
                embed = discord.Embed(
                    title=f"Guild Alert: {guild_name}",
                    description=f"**Called by:** {interaction.user.mention}\n**Guild:** {guild_name}",
                    color=discord.Color.blue()
                )
                
                embed.set_thumbnail(
                    url=interaction.user.avatar.url 
                    if interaction.user.avatar 
                    else interaction.user.default_avatar.url
                )
                
                embed.add_field(
                    name="Notes", 
                    value="No notes yet.", 
                    inline=False
                )
                
                embed.set_footer(
                    text=f"Life Alliance Alert System | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
                )

                sent_message = await alert_channel.send(
                    content=alert_message, 
                    embed=embed
                )
                
                view = AlertView(self.bot, sent_message)
                await sent_message.edit(view=view)

                await interaction.response.send_message(
                    f"Alert sent for **{guild_name}**!", 
                    ephemeral=True
                )

            except Exception as e:
                print(f"Error: {e}")
                await interaction.response.send_message(
                    "Something went wrong while sending the alert.", 
                    ephemeral=True
                )

        return callback

class GuildAlertCog(commands.Cog):
    """Guild alert management system"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def deploy_panel(self):
        """Deploy the guild ping panel"""
        try:
            guild = self.bot.get_guild(GUILD_CONFIG['id'])
            channel = guild.get_channel(GUILD_CONFIG['ping_channel_id'])

            if not guild or not channel:
                print("Error: Could not find guild or channel")
                return

            view = GuildPingView(self.bot)
            
            panel_embed = discord.Embed(
                title="Life Alliance Guild Alert System",
                description=(
                    "**Guild Communication Panel**\n\n"
                    "Click on your guild button below to send an alert to your guild members.\n"
                    "This will ping your guild in the alert channel and create a discussion thread."
                ),
                color=discord.Color.dark_blue()
            )
            
            guild_list = "\n".join(f"• {name}" for name in GUILD_ROLES.values())
            panel_embed.add_field(
                name="Available Guilds", 
                value=guild_list,
                inline=False
            )
            
            panel_embed.set_footer(
                text="Life Alliance Alert System"
            )

            # Check if there's already a pinned message to edit
            async for message in channel.history(limit=50):
                if message.pinned and message.author == self.bot.user:
                    await message.edit(embed=panel_embed, view=view)
                    return

            # Create new message if no pinned message found
            new_message = await channel.send(embed=panel_embed, view=view)
            await new_message.pin()

        except Exception as e:
            print(f"Error deploying panel: {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        """Initialize system on bot startup"""
        await self.deploy_panel()
        print("Life Alliance Guild Alert System is ready!")

async def setup(bot: commands.Bot):
    """Setup guild alert cog"""
    await bot.add_cog(GuildAlertCog(bot))
