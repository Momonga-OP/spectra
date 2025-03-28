import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
import random
from typing import Dict, Any
from datetime import datetime

# Advanced Configuration with Futuristic Touch
GUILD_CONFIG: Dict[str, Any] = {
    "id": 1234250450681724938,
    "ping_channel_id": 1307664199438307382,
    "alert_channel_id": 1307778272914051163,
    "emojis_roles": {
        "GTO": {
            "emoji": "<:GTO:1307691528096845905>", 
            "role_id": 1234253501308080239,
            "color": 0x3498db,  # Sleek blue
            "description": "Groupe Tactique Opérationnel"
        },
        # Easy to extend with more guilds
    }
}

# Futuristic Alert Messages
ALERT_MESSAGES = [
    "🌐 **SYSTEME D'ALERTE GLOBALE** : {role} - Intervention immédiate requise !",
    "⚡ **PROTOCOLE D'URGENCE ACTIVE** : {role} - Activation de la défense en cours !",
    "🔴 **STATUT : MENACE DETECTEE** {role} - Mobilisation stratégique !",
    "🛡️ **BOUCLIER CYBER ACTIVE** : {role} - Contre-mesures en préparation !",
    "📡 **SIGNAL D'URGENCE** : {role} - Coordination tactique nécessaire !"
]

class FuturisticNoteModal(Modal):
    """Advanced modal with a futuristic design for detailed alert notes"""
    def __init__(self, message: discord.Message):
        super().__init__(title="🌐 Analyse Tactique Détaillée", timeout=300)
        self.message = message

        self.threat_type = TextInput(
            label="Type de Menace",
            placeholder="Ex: Attaque Cyber, Invasion Territoriale",
            style=discord.TextStyle.short,
            max_length=50,
            required=True
        )

        self.strategic_details = TextInput(
            label="Détails Stratégiques",
            placeholder="Information cruciale pour la défense",
            style=discord.TextStyle.paragraph,
            max_length=300,
            required=True
        )

        self.add_item(self.threat_type)
        self.add_item(self.strategic_details)

    async def on_submit(self, interaction: discord.Interaction):
        """Process and enhance alert message with strategic details"""
        try:
            embed = self.message.embeds[0]
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            strategic_note = (
                f"**🕒 {timestamp} | {interaction.user.display_name}**\n"
                f"**Menace:** {self.threat_type.value}\n"
                f"**Analyse:** {self.strategic_details.value}"
            )

            existing_notes = embed.fields[0].value if embed.fields else "Aucune analyse."
            updated_notes = f"{existing_notes}\n\n{strategic_note}"
            
            embed.clear_fields()
            embed.add_field(name="📡 Intelligence Tactique", value=updated_notes, inline=False)
            embed.color = discord.Color.darker_gray()  # Subtle color change
            
            await self.message.edit(embed=embed)
            await interaction.response.send_message(
                "🌟 Analyse tactique mise à jour avec succès !", 
                ephemeral=True
            )
        
        except Exception as e:
            await interaction.response.send_message(
                f"⚠️ Erreur de transmission : {e}", 
                ephemeral=True
            )

class FuturisticAlertView(View):
    """Advanced interactive view for tactical alerts"""
    def __init__(self, bot: commands.Bot, message: discord.Message):
        super().__init__(timeout=None)
        self.bot = bot
        self.message = message
        self.is_resolved = False

        buttons = [
            {
                "label": "Analyse Tactique", 
                "style": discord.ButtonStyle.blurple, 
                "emoji": "🔍", 
                "callback": self.open_strategic_modal
            },
            {
                "label": "Mission Accomplie", 
                "style": discord.ButtonStyle.green, 
                "emoji": "✅", 
                "callback": lambda i: self.resolve_alert(i, "Succès", discord.Color.green())
            },
            {
                "label": "Mission Compromise", 
                "style": discord.ButtonStyle.red, 
                "emoji": "❌", 
                "callback": lambda i: self.resolve_alert(i, "Échec", discord.Color.red())
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

    async def open_strategic_modal(self, interaction: discord.Interaction):
        """Open strategic analysis modal"""
        if interaction.channel_id != GUILD_CONFIG['alert_channel_id']:
            await interaction.response.send_message(
                "🚫 Analyse restreinte à la zone de communication tactique.", 
                ephemeral=True
            )
            return

        modal = FuturisticNoteModal(self.message)
        await interaction.response.send_modal(modal)

    async def resolve_alert(self, interaction: discord.Interaction, status: str, color: discord.Color):
        """Resolve alert with comprehensive status update"""
        if self.is_resolved:
            await interaction.response.send_message(
                "🔒 Alerte déjà verrouillée. Aucune modification possible.", 
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
            name="🏁 Statut Final de Mission", 
            value=f"**Résultat:** {status}\n**Opérateur:** {interaction.user.mention}", 
            inline=False
        )
        embed.set_footer(text=f"Mission résolue à {datetime.now().strftime('%H:%M:%S')}")

        await self.message.edit(embed=embed)
        await interaction.response.send_message(
            f"🌐 Rapport de mission : **{status}** enregistré.", 
            ephemeral=True
        )

class FuturisticGuildPingView(View):
    """Dynamically generated futuristic ping interface"""
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        
        for guild_name, data in GUILD_CONFIG['emojis_roles'].items():
            button = Button(
                label=f"{guild_name} | {data['description']}",
                emoji=data["emoji"],
                style=discord.ButtonStyle.blurple
            )
            button.callback = self.create_tactical_ping_callback(guild_name, data)
            self.add_item(button)

    def create_tactical_ping_callback(self, guild_name: str, guild_data: Dict[str, Any]):
        """Generate a dynamic, context-aware tactical ping callback"""
        async def callback(interaction: discord.Interaction):
            try:
                if interaction.guild_id != GUILD_CONFIG['id']:
                    await interaction.response.send_message(
                        "🚫 Opération non autorisée dans cette zone.", 
                        ephemeral=True
                    )
                    return

                alert_channel = interaction.guild.get_channel(GUILD_CONFIG['alert_channel_id'])
                role = interaction.guild.get_role(guild_data['role_id'])

                if not alert_channel or not role:
                    await interaction.response.send_message(
                        "⚠️ Configuration tactique incomplète.", 
                        ephemeral=True
                    )
                    return

                alert_message = random.choice(ALERT_MESSAGES).format(role=role.mention)
                
                embed = discord.Embed(
                    title=f"🚨 ALERTE TACTIQUE : {guild_name}",
                    description=f"**Initiateur:** {interaction.user.mention}\n**Groupe:** {guild_data['description']}",
                    color=discord.Color.from_rgb(
                        *[int(x) for x in bytes.fromhex(hex(guild_data['color'])[2:].zfill(6))]
                    )
                )
                
                embed.set_thumbnail(
                    url=interaction.user.avatar.url 
                    if interaction.user.avatar 
                    else interaction.user.default_avatar.url
                )
                
                embed.add_field(
                    name="📡 Intelligence Initiale", 
                    value="Aucune analyse disponible.", 
                    inline=False
                )
                
                embed.set_footer(
                    text=f"Système d'Alerte Tactique | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
                )

                sent_message = await alert_channel.send(
                    content=alert_message, 
                    embed=embed
                )
                
                view = FuturisticAlertView(self.bot, sent_message)
                await sent_message.edit(view=view)

                await interaction.response.send_message(
                    f"🌐 Alerte tactique pour **{guild_name}** transmise !", 
                    ephemeral=True
                )

            except Exception as e:
                print(f"Erreur système : {e}")
                await interaction.response.send_message(
                    "🔥 Défaillance du système de communication.", 
                    ephemeral=True
                )

        return callback

class TacticalAlertCog(commands.Cog):
    """Advanced tactical alert management system"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def deploy_tactical_panel(self):
        """Deploy an advanced, dynamic tactical communication panel"""
        try:
            guild = self.bot.get_guild(GUILD_CONFIG['id'])
            channel = guild.get_channel(GUILD_CONFIG['ping_channel_id'])

            if not guild or not channel:
                print("🚨 Déploiement impossible : Configuration invalide")
                return

            view = FuturisticGuildPingView(self.bot)
            
            panel_embed = discord.Embed(
                title="🌐 CENTRE DE COMMUNICATION TACTIQUE",
                description=(
                    "**Système d'Alerte Avancé**\n\n"
                    "🔹 Sélectionnez votre unité pour initialiser un protocole d'urgence\n"
                    "🔹 Chaque alerte génère un rapport tactique complet\n"
                    "🔹 Mises à jour et analyses en temps réel"
                ),
                color=0x2c3e50  # Dark futuristic background
            )
            
            panel_embed.add_field(
                name="📡 Protocoles Disponibles", 
                value="\n".join(
                    f"• **{name}**: {data['description']}" 
                    for name, data in GUILD_CONFIG['emojis_roles'].items()
                ),
                inline=False
            )
            
            panel_embed.set_footer(
                text="Système de Communication Tactique | Dernière Mise à Jour"
            )

            async for message in channel.history(limit=50):
                if message.pinned:
                    await message.edit(embed=panel_embed, view=view)
                    return

            new_message = await channel.send(embed=panel_embed, view=view)
            await new_message.pin()

        except Exception as e:
            print(f"🔥 Erreur de déploiement : {e}")

    @commands.Cog.listener()
    async def on_ready(self):
        """Initialize tactical systems on bot startup"""
        await self.deploy_tactical_panel()
        print("🚀 Système Tactique Opérationnel")

async def setup(bot: commands.Bot):
    """Setup advanced tactical alert cog"""
    await bot.add_cog(TacticalAlertCog(bot))
