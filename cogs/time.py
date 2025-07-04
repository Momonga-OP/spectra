import discord
from discord.ext import commands, tasks
import datetime
import pytz
import logging

logger = logging.getLogger(__name__)

class DofusTimeUpdater(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channel_id = 1390752083363496096
        self.guild_id = 1213699457233985587
        self.paris_tz = pytz.timezone('Europe/Paris')
        self.update_dofus_time.start()
    
    def cog_unload(self):
        """Clean up when the cog is unloaded"""
        self.update_dofus_time.cancel()
    
    @tasks.loop(minutes=1)
    async def update_dofus_time(self):
        """Update the Dofus time channel every minute"""
        try:
            # Get the specific guild and channel
            guild = self.bot.get_guild(self.guild_id)
            if not guild:
                logger.error(f"Guild with ID {self.guild_id} not found")
                return
            
            channel = guild.get_channel(self.channel_id)
            if not channel:
                logger.error(f"Channel with ID {self.channel_id} not found")
                return
            
            # Get current Paris time
            utc_now = datetime.datetime.now(pytz.UTC)
            paris_time = utc_now.astimezone(self.paris_tz)
            
            # Format the time as HH:MM
            time_str = paris_time.strftime("%H:%M")
            
            # Create the new channel name
            new_name = f"🕐 {time_str} Dofus Time (GMT+2)"
            
            # Only update if the name has changed to avoid unnecessary API calls
            if channel.name != new_name:
                try:
                    await channel.edit(name=new_name)
                    logger.info(f"Updated Dofus time channel to: {new_name}")
                except discord.HTTPException as e:
                    if e.status == 429:  # Rate limit
                        logger.warning(f"Rate limited when updating channel name: {e}")
                    else:
                        logger.error(f"Failed to update channel name: {e}")
                except discord.Forbidden:
                    logger.error("Missing permissions to edit the channel")
                except Exception as e:
                    logger.error(f"Unexpected error updating channel: {e}")
            
        except Exception as e:
            logger.error(f"Error in update_dofus_time task: {e}")
    
    @update_dofus_time.before_loop
    async def before_update_dofus_time(self):
        """Wait until the bot is ready before starting the loop"""
        await self.bot.wait_until_ready()
        logger.info("Dofus time updater started")
    
    @update_dofus_time.after_loop
    async def after_update_dofus_time(self):
        """Log when the loop stops"""
        if self.update_dofus_time.is_being_cancelled():
            logger.info("Dofus time updater stopped")
    
    @commands.command(name='dofus_time')
    async def get_dofus_time(self, ctx):
        """Get the current Dofus time"""
        try:
            utc_now = datetime.datetime.now(pytz.UTC)
            paris_time = utc_now.astimezone(self.paris_tz)
            time_str = paris_time.strftime("%H:%M:%S")
            date_str = paris_time.strftime("%Y-%m-%d")
            
            embed = discord.Embed(
                title="🕐 Current Dofus Time",
                description=f"**Time:** {time_str}\n**Date:** {date_str}\n**Timezone:** GMT+2 (Paris)",
                color=0x00ff00
            )
            
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in dofus_time command: {e}")
            await ctx.send("Error getting Dofus time.")
    
    @commands.command(name='force_update_time')
    @commands.has_permissions(manage_channels=True)
    async def force_update_time(self, ctx):
        """Force update the Dofus time channel (Admin only)"""
        try:
            # Manually trigger the update
            await self.update_dofus_time()
            await ctx.send("✅ Dofus time channel updated!")
        except Exception as e:
            logger.error(f"Error in force_update_time command: {e}")
            await ctx.send("❌ Error updating Dofus time channel.")
    
    @commands.command(name='time_status')
    @commands.has_permissions(manage_channels=True)
    async def time_status(self, ctx):
        """Check the status of the time updater"""
        try:
            guild = self.bot.get_guild(self.guild_id)
            channel = guild.get_channel(self.channel_id) if guild else None
            
            utc_now = datetime.datetime.now(pytz.UTC)
            paris_time = utc_now.astimezone(self.paris_tz)
            current_time = paris_time.strftime("%H:%M")
            
            embed = discord.Embed(
                title="🔧 Dofus Time Updater Status",
                color=0x0099ff
            )
            
            embed.add_field(name="Task Running", value="✅ Yes" if self.update_dofus_time.is_running() else "❌ No", inline=True)
            embed.add_field(name="Current Paris Time", value=current_time, inline=True)
            embed.add_field(name="Guild Found", value="✅ Yes" if guild else "❌ No", inline=True)
            embed.add_field(name="Channel Found", value="✅ Yes" if channel else "❌ No", inline=True)
            
            if channel:
                embed.add_field(name="Current Channel Name", value=channel.name, inline=False)
            
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error in time_status command: {e}")
            await ctx.send("Error checking time status.")

async def setup(bot):
    """Setup function for the cog"""
    await bot.add_cog(DofusTimeUpdater(bot))
    logger.info("Dofus Time Updater cog loaded")

async def teardown(bot):
    """Teardown function for the cog"""
    logger.info("Dofus Time Updater cog unloaded")
