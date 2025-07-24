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

# Attack Alert Messages
ALERT_MESSAGES = [
    "🚨 **ATTACK ALERT** 🚨 {role} - We're under attack! All hands on deck!",
    "⚔️ **BATTLE STATIONS** ⚔️ {role} - Enemy forces detected! Defend now!",
    "🛡️ **DEFEND THE REALM** 🛡️ {role} - Attack in progress! Rally your forces!",
    "⚡ **URGENT DEFENSE** ⚡ {role} - Under siege! Immediate response required!",
    "🔥 **WAR CALL** 🔥 {role} - Battle has begun! Join the fight!"
]

class NoteModal(Modal):
    """Modal for adding intel to alerts"""
    def __init__(self, message: discord.Message):
        super().__init__(title="Add Battle Intel", timeout=300)
        self.message = message

        self.note_title = TextInput(
            label="Intel Type",
            placeholder="e.g., Enemy Count, Strategy, Location",
            style=discord.TextStyle.short,
            max_length=50,
            required=True
        )

        self.note_content = TextInput(
            label="Intel Details",
            placeholder="Provide detailed information about the attack/defense",
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

            existing_notes = embed.fields[0].value if embed.fields else "No intel yet."
            updated_notes = f"{existing_notes}\n\n{note}"
            
            embed.clear_fields()
            embed.add_field(name="Battle Intel", value=updated_notes, inline=False)
            
            await self.message.edit(embed=embed)
            await interaction.response.send_message(
                "Intel added successfully!", 
                ephemeral=True
            )
        
        except Exception as e:
            await interaction.response.send_message(
                f"Error adding intel: {e}", 
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
            label="Add Intel", 
            style=discord.ButtonStyle.blurple, 
            emoji="📝"
        )
        add_note_btn.callback = self.open_note_modal
        self.add_item(add_note_btn)

        # Won button
        won_btn = Button(
            label="Won", 
            style=discord.ButtonStyle.green, 
            emoji="🏆"
        )
        won_btn.callback = lambda i: self.resolve_alert(i, "Won", discord.Color.green())
        self.add_item(won_btn)

        # Lost button
        lost_btn = Button(
            label="Lost", 
            style=discord.ButtonStyle.red, 
            emoji="💀"
        )
        lost_btn.callback = lambda i: self.resolve_alert(i, "Lost", discord.Color.red())
        self.add_item(lost_btn)

    async def open_note_modal(self, interaction: discord.Interaction):
        """Open intel modal"""
        if interaction.channel_id != GUILD_CONFIG['alert_channel_id']:
            await interaction.response.send_message(
                "You can only add intel in the alert channel.", 
                ephemeral=True
            )
            return

        modal = NoteModal(self.message)
        await interaction.response.send_modal(modal)

    async def resolve_alert(self, interaction: discord.Interaction, status: str, color: discord.Color):
        """Resolve alert with status update"""
        if self.is_resolved:
            await interaction.response.send_message(
                "This battle has already been resolved.", 
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
            name="Battle Result", 
            value=f"**Outcome:** {status}\n**Reported by:** {interaction.user.mention}", 
            inline=False
        )
        embed.set_footer(text=f"Battle ended at {datetime.now().strftime('%H:%M:%S')}")

        await self.message.edit(embed=embed)
        await interaction.response.send_message(
            f"Battle marked as **{status}**.", 
            ephemeral=True
        )

class GuildPingView(View):
    """Guild ping interface with buttons for each guild"""
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        
        # Define button colors for different guilds
        guild_colors = [
            discord.ButtonStyle.red,      # Tight
            discord.ButtonStyle.green,    # Guardians  
            discord.ButtonStyle.blurple,  # Perfect Guild
            discord.ButtonStyle.secondary, # Sausage Finger
            discord.ButtonStyle.red,      # SAQ
            discord.ButtonStyle.green,    # The Trenches
            discord.ButtonStyle.blurple,  # EV
            discord.ButtonStyle.secondary, # Punishment
            discord.ButtonStyle.red,      # Demigods
            discord.ButtonStyle.green,    # Nemesis
            discord.ButtonStyle.blurple,  # Uchiha
            discord.ButtonStyle.secondary, # Imperium
            discord.ButtonStyle.red,      # Thieves
            discord.ButtonStyle.green,    # Sparta
            discord.ButtonStyle.blurple,  # Italians
            discord.ButtonStyle.secondary, # Krosmic Flux
            discord.ButtonStyle.red       # Vendetta
        ]
        
        # Create a button for each guild with colors
        for i, (role_id, guild_name) in enumerate(GUILD_ROLES.items()):
            button = Button(
                label=guild_name,
                style=guild_colors[i % len(guild_colors)],
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
                    title=f"⚔️ ATTACK ALERT: {guild_name} ⚔️",
                    description=f"**Alert Called by:** {interaction.user.mention}\n**Guild Under Attack:** {guild_name}\n**Status:** 🔴 Active Battle",
                    color=discord.Color.dark_red()
                )
                
                embed.set_thumbnail(
                    url=interaction.user.avatar.url 
                    if interaction.user.avatar 
                    else interaction.user.default_avatar.url
                )
                
                embed.add_field(
                    name="Battle Intel", 
                    value="No intel yet.", 
                    inline=False
                )
                
                embed.set_footer(
                    text=f"Life Alliance Defense System | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
                )

                sent_message = await alert_channel.send(
                    content=alert_message, 
                    embed=embed
                )
                
                view = AlertView(self.bot, sent_message)
                await sent_message.edit(view=view)

                await interaction.response.send_message(
                    f"🚨 **ATTACK ALERT SENT** for **{guild_name}**! 🚨", 
                    ephemeral=True
                )

            except Exception as e:
                print(f"Error: {e}")
                await interaction.response.send_message(
                    "⚠️ Something went wrong while sending the attack alert.", 
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
            print(f"Looking for guild with ID: {GUILD_CONFIG['id']}")
            guild = self.bot.get_guild(GUILD_CONFIG['id'])
            if not guild:
                print("❌ Error: Could not find guild")
                return
            
            print(f"Found guild: {guild.name}")
            print(f"Looking for channel with ID: {GUILD_CONFIG['ping_channel_id']}")
            channel = guild.get_channel(GUILD_CONFIG['ping_channel_id'])
            if not channel:
                print("❌ Error: Could not find ping channel")
                return
            
            print(f"Found channel: {channel.name}")
            
            view = GuildPingView(self.bot)
            
            panel_embed = discord.Embed(
                title="⚔️ Life Alliance Attack Alert System ⚔️",
                description=(
                    "**Manual Attack & Defense Alert System**\n\n"
                    "🛡️ This system is used to alert your guild members when under attack\n"
                    "⚔️ Click your guild button below to send an immediate attack alert\n"
                    "🚨 Only use this system for actual attacks or defense situations\n"
                    "📊 Track battle progress and share intel in real-time"
                ),
                color=discord.Color.dark_gold()
            )
            
            panel_embed.add_field(
                name="⚡ Quick Instructions", 
                value="• Select your guild button to send attack alert\n• Add battle intel for coordination\n• Mark battles as Won/Lost when finished",
                inline=False
            )
            
            panel_embed.set_footer(
                text="Life Alliance Defense Network • Stay Strong, Fight Together"
            )

            # Check if there's already a pinned message to edit
            print("Checking for existing pinned messages...")
            async for message in channel.history(limit=50):
                if message.pinned and message.author == self.bot.user:
                    print("Found existing pinned message, updating...")
                    await message.edit(embed=panel_embed, view=view)
                    print("✅ Panel updated successfully!")
                    return

            # Create new message if no pinned message found
            print("No existing pinned message found, creating new one...")
            new_message = await channel.send(embed=panel_embed, view=view)
            await new_message.pin()
            print("✅ New panel created and pinned successfully!")

        except Exception as e:
            print(f"❌ Error deploying panel: {e}")
            import traceback
            traceback.print_exc()

    @commands.Cog.listener()
    async def on_ready(self):
        """Initialize system on bot startup"""
        print("Bot is ready, deploying panel...")
        await self.deploy_panel()
        print("⚔️ Life Alliance Attack Alert System is ready for battle! ⚔️")

async def setup(bot: commands.Bot):
    """Setup guild alert cog"""
    await bot.add_cog(GuildAlertCog(bot))
