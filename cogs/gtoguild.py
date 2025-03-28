import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import random
from typing import Dict, Any

# Configuration Constants
GUILD_CONFIG: Dict[str, Any] = {
    "id": 1234250450681724938,
    "ping_channel_id": 1307664199438307382,
    "alert_channel_id": 1307778272914051163,
    "emojis_roles": {
        "GTO": {
            "emoji": "<:GTO:1307691528096845905>", 
            "role_id": 1234253501308080239
        },
        # Easily extendable for more guilds
    }
}

# Enhanced Alert Messages with more variety
ALERT_MESSAGES = [
    "🚨 {role} Alerte DEF urgente ! Tous aux remparts !",
    "⚔️ {role}, la bataille commence maintenant !",
    "🛡️ Défense requise immédiatement pour {role} !",
    "💥 Alerte critique pour {role} - Mobilisation générale !",
    "⚠️ {role}, votre présence est cruciale pour la défense !",
    "🏰 {role}, notre forteresse est menacée !",
    "📡 Signal d'urgence pour {role} - Réaction immédiate nécessaire !",
]

class ComprehensiveNoteModal(Modal):
    """Enhanced modal for adding comprehensive notes to alerts."""
    def __init__(self, message: discord.Message):
        super().__init__(title="📝 Détails de l'Alerte")
        self.message = message

        self.note_input = TextInput(
            label="Informations Détaillées",
            placeholder="Ajoutez des détails (attaquant, heure, stratégie, etc.)",
            style=discord.TextStyle.paragraph,
            max_length=200,
            required=True
        )
        self.add_item(self.note_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Process and add note to the alert message."""
        try:
            embed = self.message.embeds[0] if self.message.embeds else None
            if not embed:
                await interaction.response.send_message("Impossible de modifier l'alerte.", ephemeral=True)
                return

            existing_notes = embed.fields[0].value if embed.fields else "Aucune note."
            updated_notes = (
                f"{existing_notes}\n"
                f"- **{interaction.user.display_name}**: {self.note_input.value.strip()}"
            )
            
            embed.clear_fields()
            embed.add_field(name="📝 Notes Détaillées", value=updated_notes, inline=False)
            
            await self.message.edit(embed=embed)
            await interaction.response.send_message("Note ajoutée avec succès !", ephemeral=True)
        
        except Exception as e:
            await interaction.response.send_message(f"Erreur lors de l'ajout de la note : {e}", ephemeral=True)


class AlertActionView(View):
    """Advanced view for managing defense alerts."""
    def __init__(self, bot: commands.Bot, message: discord.Message):
        super().__init__(timeout=None)
        self.bot = bot
        self.message = message
        self.is_locked = False

        # Add interactive buttons with clear styles and emojis
        buttons = [
            {
                "label": "Ajouter Note", 
                "style": discord.ButtonStyle.secondary, 
                "emoji": "📝", 
                "callback": self.add_note_callback
            },
            {
                "label": "Victoire", 
                "style": discord.ButtonStyle.success, 
                "emoji": "✅", 
                "callback": lambda i: self.mark_alert(i, "Gagnée", discord.Color.green())
            },
            {
                "label": "Défaite", 
                "style": discord.ButtonStyle.danger, 
                "emoji": "❌", 
                "callback": lambda i: self.mark_alert(i, "Perdue", discord.Color.red())
            }
        ]

        for btn_config in buttons:
            button = Button(
                label=btn_config["label"], 
                style=btn_config["style"], 
                emoji=btn_config["emoji"]
            )
            button.callback = btn_config["callback"]
            self.add_item(button)

    async def add_note_callback(self, interaction: discord.Interaction):
        """Validate and open note modal."""
        if interaction.channel_id != GUILD_CONFIG['alert_channel_id']:
            await interaction.response.send_message(
                "Les notes ne peuvent être ajoutées que dans le canal d'alerte.", 
                ephemeral=True
            )
            return

        modal = ComprehensiveNoteModal(self.message)
        await interaction.response.send_modal(modal)

    async def mark_alert(self, interaction: discord.Interaction, status: str, color: discord.Color):
        """Mark alert as won or lost with comprehensive handling."""
        if self.is_locked:
            await interaction.response.send_message("Cette alerte est déjà verrouillée.", ephemeral=True)
            return

        self.is_locked = True
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

        embed = self.message.embeds[0]
        embed.color = color
        embed.add_field(
            name="🏁 Statut Final", 
            value=f"Alerte marquée **{status}** par {interaction.user.mention}", 
            inline=False
        )

        await self.message.edit(embed=embed)
        await interaction.response.send_message(f"Alerte marquée **{status}** avec succès.", ephemeral=True)


class DefenseAlertCog(commands.Cog):
    """Comprehensive cog for managing defense alerts."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def setup_alert_panel(self):
        """Robust method to ensure alert panel exists and is up-to-date."""
        try:
            guild = self.bot.get_guild(GUILD_CONFIG['id'])
            if not guild:
                print("Erreur : Guilde non trouvée.")
                return

            channel = guild.get_channel(GUILD_CONFIG['ping_channel_id'])
            if not channel:
                print("Erreur : Canal de ping non trouvé.")
                return

            view = GuildPingView(self.bot)
            message_content = (
                "**🎯 Panneau d'Alerte Défense**\n\n"
                "Cliquez sur le bouton de votre guilde pour alerter votre équipe.\n"
                "📋 **Mode d'emploi :**\n"
                "• Sélectionnez votre guilde\n"
                "• Vérifiez le canal d'alerte\n"
                "• Ajoutez des notes si nécessaire\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
            )

            async for message in channel.history(limit=50):
                if message.pinned:
                    await message.edit(content=message_content, view=view)
                    return

            new_message = await channel.send(content=message_content, view=view)
            await new_message.pin()

        except Exception as e:
            print(f"Erreur lors de la configuration du panneau : {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        """Enhanced ready event handler."""
        await self.setup_alert_panel()
        
        guild = self.bot.get_guild(GUILD_CONFIG['id'])
        alert_channel = guild.get_channel(GUILD_CONFIG['alert_channel_id'])
        
        if alert_channel:
            await alert_channel.set_permissions(
                guild.default_role, 
                send_messages=False, 
                add_reactions=False
            )
        
        print("🚀 Bot prêt et configuré avec succès !")


class GuildPingView(View):
    """Dynamic view for guild-specific pings."""
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        
        for guild_name, data in GUILD_CONFIG['emojis_roles'].items():
            button = Button(
                label=f"  {guild_name.upper()}  ",
                emoji=data["emoji"],
                style=discord.ButtonStyle.primary
            )
            button.callback = self.create_ping_callback(guild_name, data["role_id"])
            self.add_item(button)

    def create_ping_callback(self, guild_name: str, role_id: int):
        """Create a dynamic callback for each guild button."""
        async def callback(interaction: discord.Interaction):
            try:
                if interaction.guild_id != GUILD_CONFIG['id']:
                    await interaction.response.send_message(
                        "Cette fonction n'est pas disponible ici.", 
                        ephemeral=True
                    )
                    return

                alert_channel = interaction.guild.get_channel(GUILD_CONFIG['alert_channel_id'])
                role = interaction.guild.get_role(role_id)

                if not alert_channel or not role:
                    await interaction.response.send_message(
                        "Configuration incorrecte. Contactez un administrateur.", 
                        ephemeral=True
                    )
                    return

                alert_message = random.choice(ALERT_MESSAGES).format(role=role.mention)
                embed = discord.Embed(
                    title="🚨 Alerte de Défense",
                    description=f"{interaction.user.mention} a déclenché une alerte pour **{guild_name}**.",
                    color=discord.Color.red()
                )
                embed.set_thumbnail(
                    url=interaction.user.avatar.url 
                    if interaction.user.avatar 
                    else interaction.user.default_avatar.url
                )
                embed.add_field(name="📝 Notes", value="Aucune note.", inline=False)

                sent_message = await alert_channel.send(
                    content=alert_message, 
                    embed=embed
                )
                view = AlertActionView(self.bot, sent_message)
                await sent_message.edit(view=view)

                await interaction.response.send_message(
                    f"Alerte envoyée pour {guild_name} !", 
                    ephemeral=True
                )

            except Exception as e:
                print(f"Erreur lors de l'envoi de l'alerte : {e}")
                await interaction.response.send_message(
                    "Une erreur inattendue s'est produite.", 
                    ephemeral=True
                )

        return callback


async def setup(bot: commands.Bot):
    """Setup function for the cog."""
    await bot.add_cog(DefenseAlertCog(bot))
