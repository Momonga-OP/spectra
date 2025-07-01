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
        self.created_events = set()  # Track created event IDs to avoid duplicates
        
        # Start data update task (data only, no automatic event creation)
        self.update_data.start()
    
    def cog_unload(self):
        self.update_data.cancel()
    
    @tasks.loop(minutes=30)  # Check every 30 minutes for data updates only
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
        
        # Skip header row - CSV structure: TIME,AREA - ENG,AREA - ES,%POS%,DATE,ALLIANCE,STATUS
        start_index = 1 if lines else 0
        
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
                parsed_data = {
                    'ava_time': fields[0],           # TIME (e.g., "00:00")
                    'prism_name': fields[1],         # AREA - ENG (English prism name)
                    'prism_name_es': fields[2] if len(fields) > 2 else '',  # AREA - ES (Spanish name)
                    'position': fields[3] if len(fields) > 3 else '',       # %POS% (coordinates)
                    'date': fields[4] if len(fields) > 4 else '',           # DATE
                    'alliance': fields[5] if len(fields) > 5 else '',       # ALLIANCE
                    'status': fields[6] if len(fields) > 6 else '',         # STATUS
                }
                data.append(parsed_data)
        
        logger.info(f"Total parsed entries: {len(data)}")
        return data
    
    def get_next_24h_avas(self, weakened_only=True):
        """Calculate AVA times for the next 24 hours, optionally filter for weakened only"""
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
                    # If no date specified, assume it's today
                    ava_date = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                
                # Calculate time until AVA
                time_until = ava_date - now
                
                # Only include if it's within 24 hours and in the future
                if timedelta(0) < time_until <= timedelta(hours=24):
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
    
    async def create_ava_events(self, guild=None):
        """Create Discord events for upcoming AVAs in specified guild or all guilds"""
        # If guild is specified, only create events in that guild
        guilds_to_process = [guild] if guild else self.bot.guilds
        
        if not guilds_to_process:
            logger.warning("No guilds available to create events")
            return
        
        # Get upcoming weakened AVAs for next 24 hours
        upcoming_avas = self.get_next_24h_avas(weakened_only=True)
        
        for target_guild in guilds_to_process:
            try:
                # Get existing events to avoid duplicates
                existing_events = target_guild.scheduled_events
                
                for ava in upcoming_avas:
                    prism = ava['prism']
                    ava_datetime = ava['ava_datetime']
                    prism_name = prism.get('prism_name', 'Unknown')
                    position = prism.get('position', '')
                    alliance = prism.get('alliance', '')
                    
                    # Create unique event identifier (include guild ID to avoid conflicts)
                    event_id = f"{target_guild.id}_{prism_name}_{ava_datetime.strftime('%Y%m%d_%H%M')}"
                    
                    # Skip if we already created this event
                    if event_id in self.created_events:
                        continue
                    
                    # Check if event already exists
                    event_exists = any(
                        event.name.startswith(f"⚔️ {prism_name} AVA") and 
                        abs((event.start_time.replace(tzinfo=self.paris_tz) - ava_datetime).total_seconds()) < 300
                        for event in existing_events
                    )
                    
                    if event_exists:
                        self.created_events.add(event_id)
                        continue
                    
                    # Create event name and description
                    event_name = f"⚔️ {prism_name} AVA"
                    
                    description_parts = [
                        f"⚔️ **AVA TIME - PRISM READY** ⚔️",
                        f"",
                        f"📍 **Prism:** {prism_name}",
                        f"⏰ **AVA Time:** {ava_datetime.strftime('%H:%M')} (Paris Time)",
                        f"📅 **Date:** {ava_datetime.strftime('%d/%m/%Y')}",
                    ]
                    
                    if position:
                        description_parts.append(f"🗺️ **Position:** {position}")
                    
                    if alliance:
                        description_parts.append(f"🛡️ **Alliance:** {alliance}")
                    
                    description_parts.extend([
                        f"",
                        f"✅ **This prism has been attacked and timer has passed!**",
                        f"⚔️ **AVA can now be performed - the prism is ready to be taken!**",
                        f"🚀 **Time to mobilize and secure the prism!**",
                        f"",
                        f"*Event created from prism schedule*"
                    ])
                    
                    description = "\n".join(description_parts)
                    
                    # Calculate start time (1 hour earlier to fix timezone and 30 minutes earlier for gathering)
                    start_time = ava_datetime - timedelta(hours=1, minutes=30)
                    # Calculate end time (30 minutes after the original AVA time)
                    end_time = ava_datetime + timedelta(minutes=30)
                    
                    try:
                        # Create the scheduled event
                        event = await target_guild.create_scheduled_event(
                            name=event_name,
                            description=description,
                            start_time=start_time,
                            end_time=end_time,
                            entity_type=discord.EntityType.external,
                            location="Dofus Touch - In Game",
                            privacy_level=discord.PrivacyLevel.guild_only
                        )
                        
                        self.created_events.add(event_id)
                        logger.info(f"Created event for {prism_name} AVA at {ava_datetime.strftime('%H:%M %d/%m/%Y')} in guild {target_guild.name}")
                        
                    except discord.Forbidden:
                        logger.warning(f"No permission to create events in guild {target_guild.name}")
                    except discord.HTTPException as e:
                        logger.error(f"Failed to create event in guild {target_guild.name}: {e}")
                    
            except Exception as e:
                logger.exception(f"Error creating events for guild {target_guild.name}: {e}")
    
    @app_commands.command(name="create_ava_events", description="Create events for upcoming weakened prism AVAs (manual only)")
    async def create_ava_events_command(self, interaction: discord.Interaction):
        """Manually create events for upcoming AVAs"""
        await interaction.response.defer()
        
        try:
            # Force data refresh
            await self.update_data()
            
            # Get upcoming AVAs
            upcoming_avas = self.get_next_24h_avas(weakened_only=True)
            
            if not upcoming_avas:
                embed = discord.Embed(
                    title="✅ No Weakened Prisms",
                    description="No weakened prisms found for the next 24 hours. No AVA events to create.",
                    color=0x00ff00
                )
                await interaction.followup.send(embed=embed)
                return
            
            # Create events ONLY in the guild where the command was invoked
            await self.create_ava_events(guild=interaction.guild)
            
            embed = discord.Embed(
                title="⚔️ AVA Events Created",
                description=f"Successfully processed {len(upcoming_avas)} weakened prism AVAs for the next 24 hours in **{interaction.guild.name}**.\n\n**These prisms are ready for AVA - they have been attacked and the timer has passed!**",
                color=0xff6b35
            )
            
            # Add list of created events
            event_list = []
            for ava in upcoming_avas[:10]:  # Limit to first 10 to avoid embed size issues
                prism = ava['prism']
                ava_datetime = ava['ava_datetime']
                prism_name = prism.get('prism_name', 'Unknown')
                event_list.append(f"⚔️ **{prism_name}** - {ava_datetime.strftime('%H:%M %d/%m')}")
            
            if event_list:
                embed.add_field(
                    name="📋 Upcoming AVAs (Ready for Action)",
                    value="\n".join(event_list),
                    inline=False
                )
            
            if len(upcoming_avas) > 10:
                embed.add_field(
                    name="📝 Note",
                    value=f"... and {len(upcoming_avas) - 10} more AVA events created",
                    inline=False
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.exception("Error in create_ava_events_command")
            error_embed = discord.Embed(
                title="❌ Error",
                description="An error occurred while creating events. Please try again later.",
                color=0xff0000
            )
            await interaction.followup.send(embed=error_embed)

async def setup(bot):
    await bot.add_cog(PrismCog(bot))
