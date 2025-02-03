import discord
from discord.ext import commands
from discord import app_commands
import asyncpg
import os
from typing import Dict, Any
from .views import AlertActionView
from .gtoguild import GuildPingView

# Configuration - REPLACE THESE WITH YOUR ACTUAL IDs
GUILD_ID = 1234250450681724938  # Your main server ID
PING_DEF_CHANNEL_ID = 1307664199438307382  # Channel for ping panel
ALERTE_DEF_CHANNEL_ID = 1307778272914051163  # Channel for alerts

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

class SecondServerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = Database()
        self.is_synced = False

    async def cog_load(self):
        try:
            await self.db.connect()
        except Exception as e:
            print(f"Failed to load database: {e}")

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
            # Convert role_id to integer
            role_id_int = int(role_id)

            # Verify role exists
            role = interaction.guild.get_role(role_id_int)
            if not role:
                await interaction.response.send_message("Le rôle spécifié n'existe pas.", ephemeral=True)
                return

            # Validate emoji
            try:
                if len(emoji_id) <= 2:  # Unicode emoji
                    pass  # No validation needed
                else:
                    discord.PartialEmoji.from_str(emoji_id)
            except:
                await interaction.response.send_message("L'emoji spécifié n'est pas valide.", ephemeral=True)
                return

            # Add guild to database
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
        await self.update_panel()
        await interaction.response.send_message("Le panneau d'alerte a été mis à jour avec succès !", ephemeral=True)

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            if not self.is_synced:
                await self.bot.tree.sync()
                self.is_synced = True

            guild = self.bot.get_guild(GUILD_ID)
            if guild:
                alert_channel = guild.get_channel(ALERTE_DEF_CHANNEL_ID)
                if alert_channel:
                    await alert_channel.set_permissions(
                        guild.default_role, send_messages=False, add_reactions=False
                    )
                    print("Alert channel permissions updated.")

            print("Bot is fully ready.")
        except Exception as e:
            print(f"Error in on_ready: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(SecondServerCog(bot))
