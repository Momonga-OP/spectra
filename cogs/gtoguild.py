import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput
from discord import app_commands
import random
import asyncpg
import os
from typing import Dict, Any

# Configuration
GUILD_ID = 1234250450681724938  # Replace with your guild ID
PING_DEF_CHANNEL_ID = 1307664199438307382  # Replace with your ping channel ID
ALERTE_DEF_CHANNEL_ID = 1307778272914051163  # Replace with your alert channel ID

ALERT_MESSAGES = [
    "🚨 {role} Alerte DEF ! Connectez-vous maintenant !",
    "⚔️ {role}, il est temps de défendre !",
    "🛡️ {role} Défendez votre guilde !",
    "💥 {role} est attaquée ! Rejoignez la défense !",
    "⚠️ {role}, mobilisez votre équipe pour défendre !",
]

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        try:
            self.pool = await asyncpg.create_pool(os.environ.get('DATABASE_URL'))
            if not self.pool:
                raise ValueError("Failed to create database pool")
            await self.create_tables()
        except Exception as e:
            print(f"Database connection error: {e}")
            raise

    async def create_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS guilds (
                    id SERIAL PRIMARY KEY,
                    guild_name VARCHAR(100) UNIQUE NOT NULL,
                    emoji_id TEXT NOT NULL,
                    role_id BIGINT NOT NULL
                )
            ''')

    async def add_guild(self, guild_name: str, emoji_id: str, role_id: int) -> bool:
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    'INSERT INTO guilds (guild_name, emoji_id, role_id) VALUES ($1, $2, $3)',
                    guild_name, emoji_id, role_id
                )
                return True
        except asyncpg.UniqueViolationError:
            print(f"Guild {guild_name} already exists")
            return False
        except Exception as e:
            print(f"Error adding guild: {e}")
            return False

    async def remove_guild(self, guild_name: str) -> bool:
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(
                    'DELETE FROM guilds WHERE guild_name = $1',
                    guild_name
                )
                return 'DELETE 1' in result
        except Exception as e:
            print(f"Error removing guild: {e}")
            return False

    async def get_all_guilds(self) -> Dict[str, Dict[str, Any]]:
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch('SELECT * FROM guilds')
                return {
                    row['guild_name']: {
                        "emoji": row['emoji_id'],
                        "role_id": row['role_id']
                    }
                    for row in rows
                }
        except Exception as e:
            print(f"Error fetching guilds: {e}")
            return {}

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
                    style=discord.ButtonStyle.primary,
                    custom_id=f"guild_button_{guild_name}"  # Add custom_id
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

class SecondServerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = Database()
        self.is_synced = False
        self.panel_message = None  # Add this to track the panel message

    async def cog_load(self):
        try:
            await self.db.connect()
        except Exception as e:
            print(f"Failed to load database: {e}")

    async def update_panel(self):
        try:
            guild = self.bot.get_guild(GUILD_ID)
            if not guild:
                print("Guild not found. Check the GUILD_ID.")
                return

            channel = guild.get_channel(PING_DEF_CHANNEL_ID)
            if not channel:
                print("Ping definition channel not found. Check the PING_DEF_CHANNEL_ID.")
                return

            guild_data = await self.db.get_all_guilds()
            if not guild_data:
                print("No guild data found. Ensure guilds are added to the database.")
                return

            view = GuildPingView(self.bot, guild_data)
            message_content = (
                "**🎯 Panneau d'Alerte DEF**\n\n"
                "Bienvenue sur le Panneau d'Alerte Défense ! Cliquez sur le bouton de votre guilde ci-dessous pour envoyer une alerte à votre équipe. "
                "💡 **Comment l'utiliser :**\n"
                "1️⃣ Cliquez sur le bouton de votre guilde.\n"
                "2️⃣ Vérifiez le canal d'alerte pour les mises à jour.\n"
                "3️⃣ Ajoutez des notes aux alertes si nécessaire.\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
            )

            # Delete existing panel message if it exists
            try:
                if self.panel_message:
                    await self.panel_message.delete()
            except discord.NotFound:
                pass

            # Create a new panel message
            self.panel_message = await channel.send(content=message_content, view=view)
            
            # Unpin all messages and pin the new one
            async for message in channel.history(limit=50):
                if message.pinned:
                    await message.unpin()
            await self.panel_message.pin()
            
            print("Panel created and pinned successfully.")

        except Exception as e:
            print(f"Detailed error in update_panel: {e}")
            raise  # Re-raise the exception for debugging

    @app_commands.command(name="add_guild", description="Ajouter une nouvelle guilde au panneau d'alerte")
    @app_commands.checks.has_permissions(administrator=True)
    async def add_guild(
            self,
            interaction: discord.Interaction,
            guild_name: str,
            emoji_id: str,
            role_id: str
    ):
        try:
            role_id_int = int(role_id)
            role = interaction.guild.get_role(role_id_int)
            if not role:
                await interaction.response.send_message("Le rôle spécifié n'existe pas.", ephemeral=True)
                return

            try:
                if len(emoji_id) <= 2:  # Unicode emoji
                    pass
                else:
                    discord.PartialEmoji.from_str(emoji_id)
            except:
                await interaction.response.send_message("L'emoji spécifié n'est pas valide.", ephemeral=True)
                return

            success = await self.db.add_guild(guild_name, emoji_id, role_id_int)
            if success:
                await self.update_panel()
                await interaction.response.send_message(f"La guilde {guild_name} a été ajoutée avec succès !",
                                                     ephemeral=True)
            else:
                await interaction.response.send_message("Une erreur est survenue lors de l'ajout de la guilde.",
                                                     ephemeral=True)
        except ValueError:
            await interaction.response.send_message("Le role_id doit être un nombre valide.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Une erreur est survenue: {str(e)}", ephemeral=True)

    @app_commands.command(name="remove_guild", description="Retirer une guilde du panneau d'alerte")
    @app_commands.checks.has_permissions(administrator=True)
    async def remove_guild(self, interaction: discord.Interaction, guild_name: str):
        success = await self.db.remove_guild(guild_name)
        if success:
            await self.update_panel()
            await interaction.response.send_message(f"La guilde {guild_name} a été retirée avec succès !",
                                                 ephemeral=True)
        else:
            await interaction.response.send_message("La guilde spécifiée n'a pas été trouvée.", ephemeral=True)

    @app_commands.command(name="update_panel", description="Mettre à jour ou poster le panneau d'alerte")
    @app_commands.checks.has_permissions(administrator=True)
    async def update_panel_command(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(ephemeral=True)
            await self.update_panel()
            await interaction.followup.send("Le panneau d'alerte a été mis à jour avec succès !", ephemeral=True)
        except Exception as e:
            print(f"Error in update_panel_command: {e}")
            await interaction.followup.send("Une erreur est survenue lors de la mise à jour du panneau.", ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            if not self.is_synced:
                await self.bot.tree.sync()
                self.is_synced = True

            guild = self.bot.get_guild(GUILD_ID)
            if guild:
                alert_channel = guild.get_channel(ALERTE_DEF_CHANNEL_ID)
                ping_channel = guild.get_channel(PING_DEF_CHANNEL_ID)
                
                if alert_channel:
                    await alert_channel.set_permissions(
                        guild.default_role, 
                        send_messages=False, 
                        add_reactions=False
                    )
                    print("Alert channel permissions updated.")
                
                if ping_channel:
                    await ping_channel.set_permissions(
                        guild.default_role,
                        send_messages=False,
                        add_reactions=False
                    )
                    print("Ping channel permissions updated.")
                
                # Create initial panel on startup
                await self.update_panel()
            
            print("Bot is fully ready.")
        except Exception as e:
            print(f"Error in on_ready: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(SecondServerCog(bot))
