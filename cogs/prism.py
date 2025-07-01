import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import asyncio
from datetime import datetime, timedelta
import pytz
import re
import logging
import json
import os

logger = logging.getLogger(__name__)

class PrismCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sheet_url = "https://docs.google.com/spreadsheets/d/1uV8ULBHndwVyx-sOZFfRM69GvkPRCiHR0u-QCLiJRGU/export?format=csv&gid=0"
        self.prism_data = []
        self.last_update = None
        self.paris_tz = pytz.timezone('Europe/Paris')
        self.panel_messages = []  # Store panel message IDs and channel IDs for persistence
        self.data_file = "prism_panels.json"
        
        # Load persistent panel data
        self.load_panel_data()
        
        # Start tasks
        self.update_data.start()
        self.update_panels.start()
    
    def cog_unload(self):
        self.update_data.cancel()
        self.update_panels.cancel()
        self.save_panel_data()
    
    def load_panel_data(self):
        """Load persistent panel data from file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r') as f:
                    self.panel_messages = json.load(f)
            else:
                self.panel_messages = []
        except Exception as e:
            logger.error(f"Error loading panel data: {e}")
            self.panel_messages = []
    
    def save_panel_data(self):
        """Save persistent panel data to file"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.panel_messages, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving panel data: {e}")
    
    @tasks.loop(minutes=5)  # Update data every 5 minutes
    async def update_data(self):
        """Fetch data from Google Sheets"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.sheet_url) as response:
                    if response.status == 200:
                        content = await response.text()
                        self.prism_data = self.parse_csv_data(content)
                        self.last_update = datetime.now(self.paris_tz)
                        logger.info("Prism data updated successfully")
                    else:
                        logger.error(f"Failed to fetch sheet data: {response.status}")
        except Exception as e:
            logger.exception("Error updating prism data")
    
    @tasks.loop(minutes=1)  # Update panels every minute for accurate countdowns
    async def update_panels(self):
        """Update all persistent panels"""
        if not self.panel_messages:
            return
        
        panels_to_remove = []
        
        for panel_info in self.panel_messages:
            try:
                channel = self.bot.get_channel(panel_info['channel_id'])
                if channel:
                    try:
                        message = await channel.fetch_message(panel_info['message_id'])
                        embed = self.create_comprehensive_embed()
                        await message.edit(embed=embed)
                    except discord.NotFound:
                        # Message was deleted, remove from list
                        panels_to_remove.append(panel_info)
                    except discord.Forbidden:
                        logger.warning(f"No permission to edit message in channel {panel_info['channel_id']}")
                    except Exception as e:
                        logger.error(f"Error updating panel message: {e}")
                else:
                    # Channel not found, remove from list
                    panels_to_remove.append(panel_info)
            except Exception as e:
                logger.error(f"Error processing panel update: {e}")
                panels_to_remove.append(panel_info)
        
        # Remove invalid panels
        for panel_info in panels_to_remove:
            self.panel_messages.remove(panel_info)
        
        if panels_to_remove:
            self.save_panel_data()
    
    @update_data.before_loop
    async def before_update_data(self):
        await self.bot.wait_until_ready()
    
    @update_panels.before_loop
    async def before_update_panels(self):
        await self.bot.wait_until_ready()
        # Wait a bit for the bot to fully initialize
        await asyncio.sleep(5)
    
    def parse_csv_data(self, csv_content):
        """Parse CSV content and extract relevant prism/AVA data"""
        lines = csv_content.strip().split('\n')
        data = []
        
        # Skip header row
        for line in lines[1:]:
            # Basic CSV parsing (you may need to adjust based on actual sheet structure)
            fields = [field.strip('"') for field in line.split(',')]
            if len(fields) >= 4:  # Assuming minimum required fields
                data.append({
                    'prism_name': fields[0] if len(fields) > 0 else '',
                    'server': fields[1] if len(fields) > 1 else '',
                    'ava_time': fields[2] if len(fields) > 2 else '',
                    'status': fields[3] if len(fields) > 3 else '',
                    'alliance': fields[4] if len(fields) > 4 else ''
                })
        return data
    
    def get_next_48h_avas(self):
        """Calculate AVA times for the next 48 hours"""
        now = datetime.now(self.paris_tz)
        upcoming_avas = []
        
        # Get AVAs for the next 2 days
        for day_offset in range(3):  # Today, tomorrow, day after
            check_date = now + timedelta(days=day_offset)
            
            for prism in self.prism_data:
                if prism.get('ava_time'):
                    try:
                        # Parse AVA time (assuming format like "20:30" for daily AVA)
                        time_match = re.match(r'(\d{1,2}):(\d{2})', prism['ava_time'])
                        if time_match:
                            hour, minute = map(int, time_match.groups())
                            
                            # Create datetime for this day's AVA
                            ava_datetime = check_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                            
                            # Only include if it's within 48 hours and in the future
                            time_until = ava_datetime - now
                            if timedelta(0) < time_until <= timedelta(hours=48):
                                upcoming_avas.append({
                                    'prism': prism,
                                    'ava_datetime': ava_datetime,
                                    'countdown': time_until
                                })
                    except Exception as e:
                        logger.warning(f"Error parsing AVA time for {prism.get('prism_name')}: {e}")
        
        # Sort by soonest AVA first
        upcoming_avas.sort(key=lambda x: x['countdown'])
        return upcoming_avas
    
    def format_countdown(self, delta):
        """Format timedelta into human-readable countdown"""
        total_seconds = int(delta.total_seconds())
        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours >= 24:
            days = hours // 24
            remaining_hours = hours % 24
            return f"{days}d {remaining_hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m"
        else:
            return f"{seconds}s"
    
    def get_day_name(self, date):
        """Get day name from date"""
        day_names = {
            0: 'Monday',
            1: 'Tuesday', 
            2: 'Wednesday',
            3: 'Thursday',
            4: 'Friday',
            5: 'Saturday',
            6: 'Sunday'
        }
        return day_names[date.weekday()]
    
    def create_comprehensive_embed(self):
        """Create a comprehensive embed with all AVA information for next 48h"""
        embed = discord.Embed(
            title="AFL Alliance - AVA Schedule (Next 48 Hours)",
            description="Alliance vs Alliance schedule and countdowns",
            color=0x9932cc,
            timestamp=datetime.utcnow()
        )
        
        if not self.prism_data:
            embed.add_field(
                name="No Data Available", 
                value="Prism data not loaded. Please wait for the next update.", 
                inline=False
            )
            return embed
        
        # Current time information
        paris_time = datetime.now(self.paris_tz)
        embed.add_field(
            name="Current Dofus Touch Time (Paris)", 
            value=f"{paris_time.strftime('%H:%M:%S')} - {self.get_day_name(paris_time)}, {paris_time.strftime('%d/%m/%Y')}", 
            inline=False
        )
        
        # Get upcoming AVAs for next 48 hours
        upcoming_avas = self.get_next_48h_avas()
        
        if upcoming_avas:
            ava_lines = []
            current_day = None
            
            for ava in upcoming_avas:
                prism = ava['prism']
                ava_datetime = ava['ava_datetime']
                countdown = self.format_countdown(ava['countdown'])
                
                # Check if we need to add a day separator
                ava_day = ava_datetime.strftime('%d/%m/%Y')
                day_name = self.get_day_name(ava_datetime)
                
                if current_day != ava_day:
                    if current_day is not None:  # Not the first day
                        ava_lines.append("")  # Add blank line between days
                    ava_lines.append(f"**{day_name}, {ava_day}**")
                    current_day = ava_day
                
                # Format AVA entry
                status = "Controlled" if prism.get('status', '').lower() == 'controlled' else "Not Controlled"
                server = prism.get('server', 'Unknown')
                prism_name = prism.get('prism_name', 'Unknown')
                ava_time = ava_datetime.strftime('%H:%M')
                
                ava_line = f"{prism_name} ({server}) - {ava_time} - {countdown} - {status}"
                ava_lines.append(ava_line)
            
            # Split into multiple fields if too long
            ava_text = "\n".join(ava_lines)
            
            if len(ava_text) <= 1024:
                embed.add_field(
                    name="Upcoming AVAs", 
                    value=ava_text, 
                    inline=False
                )
            else:
                # Split into multiple fields
                field_count = 1
                current_field = []
                current_length = 0
                
                for line in ava_lines:
                    line_length = len(line) + 1  # +1 for newline
                    
                    if current_length + line_length > 1020 and current_field:  # Leave some margin
                        # Add current field
                        field_name = f"Upcoming AVAs {field_count}" if field_count > 1 else "Upcoming AVAs"
                        embed.add_field(
                            name=field_name,
                            value="\n".join(current_field),
                            inline=False
                        )
                        
                        # Start new field
                        current_field = [line]
                        current_length = line_length
                        field_count += 1
                    else:
                        current_field.append(line)
                        current_length += line_length
                
                # Add remaining field
                if current_field:
                    field_name = f"Upcoming AVAs {field_count}" if field_count > 1 else "Upcoming AVAs"
                    embed.add_field(
                        name=field_name,
                        value="\n".join(current_field),
                        inline=False
                    )
        else:
            embed.add_field(
                name="No Upcoming AVAs", 
                value="No AVA schedules found for the next 48 hours.", 
                inline=False
            )
        
        # Add last update info
        if self.last_update:
            embed.set_footer(text=f"Last updated: {self.last_update.strftime('%H:%M:%S')} • Auto-refreshes every minute")
        
        return embed
    
    @app_commands.command(name="ava_panel", description="Create a persistent AVA information panel")
    async def ava_panel_command(self, interaction: discord.Interaction):
        """Create a persistent AVA panel"""
        # Check if user has manage messages permission
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("You need 'Manage Messages' permission to create AVA panels.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            # Create the comprehensive embed
            embed = self.create_comprehensive_embed()
            
            # Send the panel
            message = await interaction.followup.send(embed=embed)
            
            # Add to persistent panels list
            panel_info = {
                'message_id': message.id,
                'channel_id': interaction.channel.id,
                'created_by': interaction.user.id,
                'created_at': datetime.now().isoformat()
            }
            
            self.panel_messages.append(panel_info)
            self.save_panel_data()
            
            # Send confirmation
            await interaction.followup.send(
                "AVA panel created successfully! It will auto-update every minute and persist across bot restarts.", 
                ephemeral=True
            )
            
        except Exception as e:
            logger.exception("Error creating AVA panel")
            await interaction.followup.send("An error occurred while creating the AVA panel.", ephemeral=True)
    
    @commands.command(name='ava_panel')
    async def ava_panel_prefix_command(self, ctx):
        """Prefix version of AVA panel command"""
        # Check if user has manage messages permission
        if not ctx.author.guild_permissions.manage_messages:
            await ctx.send("You need 'Manage Messages' permission to create AVA panels.")
            return
        
        try:
            # Create the comprehensive embed
            embed = self.create_comprehensive_embed()
            
            # Send the panel
            message = await ctx.send(embed=embed)
            
            # Add to persistent panels list
            panel_info = {
                'message_id': message.id,
                'channel_id': ctx.channel.id,
                'created_by': ctx.author.id,
                'created_at': datetime.now().isoformat()
            }
            
            self.panel_messages.append(panel_info)
            self.save_panel_data()
            
            await ctx.send("AVA panel created successfully! It will auto-update every minute and persist across bot restarts.", delete_after=5)
            
        except Exception as e:
            logger.exception("Error creating AVA panel")
            await ctx.send("An error occurred while creating the AVA panel.")
    
    @app_commands.command(name="refresh_ava", description="Manually refresh AVA data (Admin only)")
    async def refresh_ava_command(self, interaction: discord.Interaction):
        """Manually refresh the AVA data"""
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            await self.update_data()
            embed = discord.Embed(
                title="Data Refreshed", 
                description=f"AVA data updated successfully at {datetime.now(self.paris_tz).strftime('%H:%M:%S')}", 
                color=0x00ff00
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            logger.exception("Error refreshing AVA data")
            embed = discord.Embed(
                title="Refresh Failed", 
                description="Failed to refresh AVA data. Check logs for details.", 
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    @app_commands.command(name="clear_panels", description="Clear all persistent AVA panels (Admin only)")
    async def clear_panels_command(self, interaction: discord.Interaction):
        """Clear all persistent panels"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You need administrator permissions to use this command.", ephemeral=True)
            return
        
        panel_count = len(self.panel_messages)
        self.panel_messages = []
        self.save_panel_data()
        
        await interaction.response.send_message(f"Cleared {panel_count} persistent AVA panels.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(PrismCog(bot))
