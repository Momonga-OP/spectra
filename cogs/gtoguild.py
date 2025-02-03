import discord
from discord.ui import View, Button
from discord.ext import commands
from typing import Dict, Any
from config import GUILD_ID, ALERTE_DEF_CHANNEL_ID

class GuildPingView(View):
    def __init__(self, bot: commands.Bot, guild_data: Dict[str, Dict[str, Any]]):
        super().__init__(timeout=None)
        self.bot = bot
        for guild_name, data in guild_data.items():
            try:
                # Handle Unicode emoji
                if len(data["emoji"]) <= 2:  # Unicode emoji
                    emoji = data["emoji"]
                # Handle custom emoji
                else:
                    emoji = discord.PartialEmoji.from_str(data["emoji"])

                button = Button(
                    label=f"  {guild_name.upper()}  ",
                    emoji=emoji,
                    style=discord.ButtonStyle.primary
                )
                button.callback = self.create_ping_callback(guild_name, data["role_id"])
                self.add_item(button)
            except Exception as e:
                print(f"Error creating button for guild {guild_name}: {e}")
                continue

    def create_ping_callback(self, guild_name, role_id):
        async def callback(interaction: discord.Interaction):
            try:
                if interaction.guild_id != GUILD_ID:
                    await interaction.response.send_message(
                        "Cette fonction n'est pas disponible sur ce serveur.", ephemeral=True
                    )
                    return

                alert_channel = interaction.guild.get_channel(ALERTE_DEF_CHANNEL_ID)
                if not alert_channel:
                    await interaction.response.send_message("Canal d'alerte introuvable !", ephemeral=True)
                    return

                role = interaction.guild.get_role(role_id)
                if not role:
                    await interaction.response.send_message(f"Rôle pour {guild_name} introuvable !", ephemeral=True)
                    return

                alert_message = random.choice(ALERT_MESSAGES).format(role=role.mention)
                embed = discord.Embed(
                    title="🔔 Alerte envoyée !",
                    description=f"**{interaction.user.mention}** a déclenché une alerte pour **{guild_name}**.",
                    color=discord.Color.red()
                )
                embed.set_thumbnail(
                    url=interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url)
                embed.add_field(name="📝 Notes", value="Aucune note.", inline=False)

                sent_message = await alert_channel.send(content=alert_message, embed=embed)
                view = AlertActionView(self.bot, sent_message)
                await sent_message.edit(view=view)

                await interaction.response.send_message(
                    f"Alerte envoyée à {guild_name} dans le canal d'alerte !", ephemeral=True
                )

            except Exception as e:
                print(f"Error in ping callback for {guild_name}: {e}")
                await interaction.response.send_message("Une erreur est survenue.", ephemeral=True)

        return callback
