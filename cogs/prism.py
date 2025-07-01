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
        
        logger.info(f"CSV Content (first 3 lines):")
        for i, line in enumerate(lines[:3]):
            logger.info(f"Line {i}: {line}")
        
        # Skip header row - CSV structure: TIME,AREA - ENG,AREA - ES,%POS%,DATE,ALLIANCE,STATUS
        start_index = 1 if lines else 0
        logger.info(f"Header: {lines[0] if lines else 'No data'}")
        
        for i, line in enumerate(lines[start_index:], start_index):
            if not line.strip():  # Skip empty lines
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
            
            if len(fields) >= 6 and fields[0] and fields[1]:  # Need at least time and prism name
                # Parse the data according to actual CSV structure
                # CSV: TIME,AREA - ENG,AREA - ES,%POS%,DATE,ALLIANCE,STATUS
                parsed_data = {
                    'ava_time': fields[0],           # TIME (e.g., "00:00")
                    'prism_name': fields[1],         # AREA - ENG (English prism name)
                    'prism_name_es': fields[2] if len(fields) > 2 else '',  # AREA - ES (Spanish name)
                    'position': fields[3] if len(fields) > 3 else '',       # %POS% (coordinates)
                    'date': fields[4] if len(fields) > 4 else '',           # DATE
                    'alliance': fields[5] if len(fields) > 5 else '',       # ALLIANCE
                    'status': fields[6] if len(fields) > 6 else '',         # STATUS
                    'server': 'Dofus Touch'  # All entries are from the same server based on the data
                }
                data.append(parsed_data)
                logger.info(f"Added data: {parsed_data['prism_name']} at {parsed_data['ava_time']} - {parsed_data['status']}")
        
        logger.info(f"Total parsed entries: {len(data)}")
        return data
    
    def get_next_48h_avas(self, weakened_only=True):
        """Calculate AVA times for the next 48 hours, optionally filter for weakened only"""
        now = datetime.now(self.paris_tz)
        upcoming_avas = []
        
        for prism in self.prism_data:
            # Filter for weakened prisms if requested
            if weakened_only and prism.get('status', '').lower() != 'weakened':
                continue
                
            ava_time_str = prism.get('ava_time', '').strip()
            date_str = prism.get('date', '').strip()
            
            if not ava_time_str:
                continue
                
            try:
                # Parse AVA time (format: "HH:MM")
                time_match = re.match(r'(\d{1,2}):(\d{2})', ava_time_str)
                if not time_match:
                    continue
                    
                hour, minute = map(int, time_match.groups())
                
                # Parse date if available (format: "DD/MM/YYYY")
                if date_str:
                    try:
                        # Parse date string "02/07/2025" -> day/month/year
                        date_parts = date_str.split('/')
                        if len(date_parts) == 3:
                            day, month, year = map(int, date_parts)
                            ava_date = datetime(year, month, day, hour, minute, 0, tzinfo=self.paris_tz)
                        else:
                            continue
                    except ValueError:
                        logger.warning(f"Invalid date format for {prism.get('prism_name')}: {date_str}")
                        continue
                else:
                    # If no date specified, assume it's today (this shouldn't happen with your data)
                    ava_date = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # Calculate time until AVA
                time_until = ava_date - now
                
                # Only include if it's within 48 hours and in the future (allow 1 minute past for ongoing AVAs)
                if timedelta(minutes=-1) < time_until <= timedelta(hours=48):
                    upcoming_avas.append({
                        'prism': prism,
                        'ava_datetime': ava_date,
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
    
    def calculate_embed_size(self, embed):
        """Calculate the total size of an embed in characters"""
        size = 0
        if embed.title:
            size += len(embed.title)
        if embed.description:
            size += len(embed.description)
        for field in embed.fields:
            if field.name:
                size += len(field.name)
            if field.value:
                size += len(field.value)
        if embed.footer and embed.footer.text:
            size += len(embed.footer.text)
        return size
    
    def create_ava_embed(self):
        """Create an embed with AVA information for next 48h (weakened prisms only)"""
        embed = discord.Embed(
            title="⚠️ AFL Alliance - Weakened Prisms AVA Schedule",
            description="Weakened prism AVA schedule for the next 48 hours",
            color=0xff6b35,  # Orange color for weakened status
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
        time_field = f"`{paris_time.strftime('%H:%M:%S')}` - {self.get_day_name(paris_time)}, {paris_time.strftime('%d/%m/%Y')}"
        embed.add_field(
            name="🕐 Current Dofus Touch Time (Paris)", 
            value=time_field, 
            inline=False
        )
        
        # Get upcoming weakened AVAs for next 48 hours
        upcoming_avas = self.get_next_48h_avas(weakened_only=True)
        
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
                
                # Format AVA entry (simplified for weakened prisms)
                prism_name = prism.get('prism_name', 'Unknown')
                ava_time = ava_datetime.strftime('%H:%M')
                position = prism.get('position', '')
                
                # Create the AVA line
                ava_line = f"⚠️ **{prism_name}** - `{ava_time}` - ⏰ {countdown}"
                if position:
                    ava_line += f" - 📍 {position}"
                
                ava_lines.append(ava_line)
            
            # Build fields while checking size limits
            current_field_lines = []
            field_count = 1
            MAX_FIELD_SIZE = 1024
            MAX_EMBED_SIZE = 5500  # Leave some buffer under 6000
            
            for line in ava_lines:
                # Check if adding this line would exceed field size
                test_field = "\n".join(current_field_lines + [line])
                
                if len(test_field) > MAX_FIELD_SIZE and current_field_lines:
                    # Add current field and start a new one
                    field_name = f"⚔️ Weakened Prisms (Part {field_count})" if field_count > 1 else "⚔️ Weakened Prisms"
                    embed.add_field(
                        name=field_name,
                        value="\n".join(current_field_lines),
                        inline=False
                    )
                    
                    # Check if we're approaching embed size limit
                    if self.calculate_embed_size(embed) > MAX_EMBED_SIZE:
                        # Remove the last field and add a truncation notice
                        embed.remove_field(-1)
                        embed.add_field(
                            name="📋 Note",
                            value="Some entries were truncated due to Discord's size limits. Use `/ava_panel` again for updated information.",
                            inline=False
                        )
                        break
                    
                    current_field_lines = [line]
                    field_count += 1
                else:
                    current_field_lines.append(line)
            
            # Add remaining field if we haven't hit size limits
            if current_field_lines and self.calculate_embed_size(embed) < MAX_EMBED_SIZE:
                field_name = f"⚔️ Weakened Prisms (Part {field_count})" if field_count > 1 else "⚔️ Weakened Prisms"
                test_embed_size = self.calculate_embed_size(embed) + len(field_name) + len("\n".join(current_field_lines))
                
                if test_embed_size <= MAX_EMBED_SIZE:
                    embed.add_field(
                        name=field_name,
                        value="\n".join(current_field_lines),
                        inline=False
                    )
        else:
            embed.add_field(
                name="✅ No Weakened Prisms", 
                value="No weakened prisms found for the next 48 hours. Great news!", 
                inline=False
            )
        
        # Add footer with update info
        footer_text = "Only showing WEAKENED prisms • "
        if self.last_update:
            footer_text += f"Last updated: {self.last_update.strftime('%H:%M:%S')} • Data refreshes every 5 minutes"
        else:
            footer_text += "Data is loading..."
        
        embed.set_footer(text=footer_text)
        
        return embed
    
    @app_commands.command(name="ava_panel", description="Display weakened prisms AVA schedule for the next 48 hours")
    async def ava_panel_command(self, interaction: discord.Interaction):
        """Display AVA panel with weakened prisms schedule information"""
        await interaction.response.defer()
        
        try:
            # Force data refresh if no data is available
            if not self.prism_data:
                await self.update_data()
            
            # Create and send the embed
            embed = self.create_ava_embed()
            
            # Final size check before sending
            embed_size = self.calculate_embed_size(embed)
            logger.info(f"Embed size: {embed_size} characters")
            
            if embed_size > 6000:
                # Fallback: create a minimal embed
                fallback_embed = discord.Embed(
                    title="⚠️ AFL Alliance - Weakened Prisms",
                    description="Too much data to display. Please contact an admin to check the prism schedule.",
                    color=0xff6b35
                )
                await interaction.followup.send(embed=fallback_embed)
                logger.warning(f"Embed too large ({embed_size} chars), sent fallback")
            else:
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
