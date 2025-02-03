import discord
from discord.ext import commands
from discord import app_commands
import asyncpg
import os
from typing import Dict, Any

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
