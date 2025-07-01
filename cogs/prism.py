import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import asyncio
from datetime import datetime, timedelta
import pytz
import re
import logging

logger = logging.getLogger(__name__)

class PrismCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sheet_url = "https://docs.google.com/spreadsheets/d/1uV8ULBHndwVyx-sOZFfRM69GvkPRCiHR0u-QCLiJRGU/export?format=csv&gid=0"
        self.prism_data = []
        self.last_update = None
        self.paris_tz = pytz.timezone('Europe/Paris')
        
        # Start data update task
        self.update_data.start()
    
    def cog_unload(self):
        self.update_data.cancel()
    
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
                        logger.info(f"Prism data updated successfully - {len(self.prism_data)} entries loaded")
                    else:
                        logger.error(f"Failed to fetch sheet data: {response.status}")
        except Exception as e:
            logger.exception(f"Error updating prism data: {e}")
    
    @update_data.before_loop
    async def before_update_data(self):
        await self.bot.wait_until_ready()
        # Initial data fetch
        await self.update_data()
    
    def parse_csv_data(self, csv_content):
        """Parse CSV content and extract relevant prism/AVA data"""
        lines = csv_content.strip().split('\n')
        data = []
        
        # Skip header row if it exists
        for i, line in enumerate(lines):
            if i == 0:
                # Check if first line looks like headers
                if any(header in line.lower() for header in ['prism', 'server', 'time', 'ava', 'alliance']):
                    continue
            
            # Parse CSV line (handling quoted fields)
            fields = []
            current_field = ""
            in_quotes = False
            
            for char in line:
                if char == '"':
                    in_quotes = not in_quotes
                elif char == ',' and not in_quotes:
                    fields.append(current_field.strip())
                    current_field = ""
                else:
                    current_field += char
            
            # Add the last field
            fields.append(current_field.strip())
            
            # Clean up fields
            fields = [field.strip('"').strip() for field in fields]
            
            if len(fields) >= 3 and fields[0]:  # Minimum required fields and non-empty prism name
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
        
        # Get AVAs for the next 3 days to ensure we cover 48 hours
        for day_offset in range(3):
            check_date = now + timedelta(days=day_offset)
            
            for prism in self.prism_data:
                if prism.get('ava_time'):
                    try:
                        # Parse AVA time (assuming format like "20:30" or "8:30 PM")
                        time_str = prism['ava_time'].strip()
                        
                        # Handle different time formats
                        time_match = re.match(r'(\d{1,2}):(\d{2})', time_str)
                        if time_match:
                            hour, minute = map(int, time_match.groups())
                            
                            # Create datetime for this day's AVA
                            ava_datetime = check_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                            
                            # Only include if it's within 48 hours and in the future
                            time_until = ava_datetime - now
                            if timedelta(minutes=1) < time_until <= timedelta(hours=48):
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
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        return day_names[date.weekday()]
    
    def create_ava_embed(self):
        """Create an embed with AVA information for next 48h"""
        embed = discord.Embed(
            title="🏰 AFL Alliance - AVA Schedule",
            description="Alliance vs Alliance schedule for the next 48 hours",
            color=0x9932cc,
            timestamp=datetime.utcnow()
        )
        
        if not self.prism_data:
            embed.add_field(
                name="⚠️ No Data Available", 
                value="Prism data is still loading. Please try again in a moment.", 
                inline=False
            )
            return embed
        
        # Current time information
        paris_time = datetime.now(self.paris_tz)
        embed.add_field(
            name="🕐 Current Dofus Touch Time (Paris)", 
            value=f"`{paris_time.strftime('%H:%M:%S')}` - {self.get_day_name(paris_time)}, {paris_time.strftime('%d/%m/%Y')}", 
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
                    ava_lines.append(f"📅 **{day_name}, {ava_day}**")
                    current_day = ava_day
                
                # Format AVA entry
                status_emoji = "✅" if prism.get('status', '').lower() in ['controlled', 'yes', '1'] else "❌"
                server = prism.get('server', 'Unknown')
                prism_name = prism.get('prism_name', 'Unknown')
                ava_time = ava_datetime.strftime('%H:%M')
                
                ava_line = f"{status_emoji} **{prism_name}** ({server}) - `{ava_time}` - ⏰ {countdown}"
                ava_lines.append(ava_line)
            
            # Split into multiple fields if too long
            ava_text = "\n".join(ava_lines)
            
            if len(ava_text) <= 1024:
                embed.add_field(
                    name="⚔️ Upcoming AVAs", 
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
                        field_name = f"⚔️ Upcoming AVAs (Part {field_count})" if field_count > 1 else "⚔️ Upcoming AVAs"
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
                    field_name = f"⚔️ Upcoming AVAs (Part {field_count})" if field_count > 1 else "⚔️ Upcoming AVAs"
                    embed.add_field(
                        name=field_name,
                        value="\n".join(current_field),
                        inline=False
                    )
        else:
            embed.add_field(
                name="😴 No Upcoming AVAs", 
                value="No AVA schedules found for the next 48 hours.", 
                inline=False
            )
        
        # Add footer with update info
        if self.last_update:
            embed.set_footer(text=f"Last updated: {self.last_update.strftime('%H:%M:%S')} • Data refreshes every 5 minutes")
        else:
            embed.set_footer(text="Data is loading...")
        
        return embed
    
    @app_commands.command(name="ava_panel", description="Display the AVA schedule for the next 48 hours")
    async def ava_panel_command(self, interaction: discord.Interaction):
        """Display AVA panel with schedule information"""
        await interaction.response.defer()
        
        try:
            # Force data refresh if no data is available
            if not self.prism_data:
                await self.update_data()
            
            # Create and send the embed
            embed = self.create_ava_embed()
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.exception("Error creating AVA panel")
            error_embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while fetching AVA data. Please try again later.",
                color=0xff0000
            )
            await interaction.followup.send(embed=error_embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(PrismCog(bot))
