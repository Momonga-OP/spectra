import discord
from discord.ui import View, Button, Modal, TextInput
from discord.ext import commands
import random

# French alert messages
ALERT_MESSAGES = [
    "🚨 {role} Alerte DEF ! Connectez-vous maintenant !",
    "⚔️ {role}, il est temps de défendre !",
    "🛡️ {role} Défendez votre guilde !",
    "💥 {role} est attaquée ! Rejoignez la défense !",
    "⚠️ {role}, mobilisez votre équipe pour défendre !",
]

class NoteModal(Modal):
    def __init__(self, message: discord.Message):
        super().__init__(title="Ajouter une note")
        self.message = message

        self.note_input = TextInput(
            label="Votre note",
            placeholder="Ajoutez des détails sur l'alerte (nom de la guilde attaquante, heure, etc.)",
            max_length=100,
            style=discord.TextStyle.paragraph,
        )
        self.add_item(self.note_input)

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.message.embeds[0] if self.message.embeds else None
        if not embed:
            await interaction.response.send_message("Impossible de récupérer l'embed à modifier.", ephemeral=True)
            return

        existing_notes = embed.fields[0].value if embed.fields else "Aucune note."
        updated_notes = f"{existing_notes}\n- **{interaction.user.display_name}**: {self.note_input.value.strip()}"
        embed.clear_fields()
        embed.add_field(name="📝 Notes", value=updated_notes, inline=False)

        await self.message.edit(embed=embed)
        await interaction.response.send_message("Votre note a été ajoutée avec succès !", ephemeral=True)

class AlertActionView(View):
    def __init__(self, bot: commands.Bot, message: discord.Message):
        super().__init__(timeout=None)
        self.bot = bot
        self.message = message
        self.is_locked = False

        self.add_note_button = Button(
            label="Ajouter une note",
            style=discord.ButtonStyle.secondary,
            emoji="📝"
        )
        self.add_note_button.callback = self.add_note_callback
        self.add_item(self.add_note_button)

        self.won_button = Button(
            label="Won",
            style=discord.ButtonStyle.success,
        )
        self.won_button.callback = self.mark_as_won
        self.add_item(self.won_button)

        self.lost_button = Button(
            label="Lost",
            style=discord.ButtonStyle.danger,
        )
        self.lost_button.callback = self.mark_as_lost
        self.add_item(self.lost_button)

    async def add_note_callback(self, interaction: discord.Interaction):
        if interaction.channel_id != ALERTE_DEF_CHANNEL_ID:
            await interaction.response.send_message("Vous ne pouvez pas ajouter de note ici.", ephemeral=True)
            return

        modal = NoteModal(self.message)
        await interaction.response.send_modal(modal)

    async def mark_as_won(self, interaction: discord.Interaction):
        await self.mark_alert(interaction, "Gagnée", discord.Color.green())

    async def mark_as_lost(self, interaction: discord.Interaction):
        await self.mark_alert(interaction, "Perdue", discord.Color.red())

    async def mark_alert(self, interaction: discord.Interaction, status: str, color: discord.Color):
        if self.is_locked:
            await interaction.response.send_message("Cette alerte a déjà été marquée.", ephemeral=True)
            return

        self.is_locked = True
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

        embed = self.message.embeds[0]
        embed.color = color
        embed.add_field(name="Statut",
                        value=f"L'alerte a été marquée comme **{status}** par {interaction.user.mention}.",
                        inline=False)

        await self.message.edit(embed=embed)
        await interaction.response.send_message(f"Alerte marquée comme **{status}** avec succès.", ephemeral=True)
