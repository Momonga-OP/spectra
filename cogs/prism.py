import discord
from discord.ext import commands, tasks
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
        self.update_data.start()
    
    def cog_unload(self):
        self.update_data.cancel()
    
    @tasks.loop(minutes=5)  # Update every 5 minutes
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
    
    @update_data.before_loop
    async def before_update_data(self):
        await self.bot.wait_until_ready()
    
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
    
    def get_next_ava_times(self):
        """Calculate next AVA times and countdowns"""
        now = datetime.now(self.paris_tz)
        upcoming_avas = []
        
        for prism in self.prism_data:
            if prism.get('ava_time'):
                try:
                    # Parse AVA time (assuming format like "20:30" for daily AVA)
                    time_match = re.match(r'(\d{1,2}):(\d{2})', prism['ava_time'])
                    if time_match:
                        hour, minute = map(int, time_match.groups())
                        
                        # Create datetime for today's AVA
                        ava_today = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        
                        # If today's AVA has passed, get tomorrow's
                        if ava_today <= now:
                            ava_today += timedelta(days=1)
                        
                        time_until = ava_today - now
                        
                        upcoming_avas.append({
                            'prism': prism,
                            'ava_datetime': ava_today,
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
        
        if hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"
    
    def create_ava_embed(self, user_timezone=None):
        """Create Discord embed with AVA information"""
        embed = discord.Embed(
            title="🏰 AFL Alliance - AVA Times",
            description="Alliance vs Alliance schedule and countdowns",
            color=0x00ff88,
            timestamp=datetime.utcnow()
        )
        
        if not self.prism_data:
            embed.add_field(
                name="⚠️ No Data", 
                value="Prism data not available. Please try again later.", 
                inline=False
            )
            return embed
        
        # Get Paris time
        paris_time = datetime.now(self.paris_tz)
        embed.add_field(
            name="🕐 Dofus Touch Time (Paris)", 
            value=paris_time.strftime("%H:%M:%S - %d/%m/%Y"), 
            inline=True
        )
        
        # Show user's timezone if provided
        if user_timezone:
            try:
                user_tz = pytz.timezone(user_timezone)
                user_time = paris_time.astimezone(user_tz)
                embed.add_field(
                    name=f"🌍 Your Time ({user_timezone})", 
                    value=user_time.strftime("%H:%M:%S - %d/%m/%Y"), 
                    inline=True
                )
            except:
                pass
        
        # Get upcoming AVAs
        upcoming_avas = self.get_next_ava_times()
        
        if upcoming_avas:
            # Show next 3 AVAs
            for i, ava in enumerate(upcoming_avas[:3]):
                prism = ava['prism']
                countdown = self.format_countdown(ava['countdown'])
                ava_time = ava['ava_datetime'].strftime("%H:%M")
                
                field_name = f"⚔️ {prism.get('prism_name', 'Unknown')} ({prism.get('server', 'Unknown')})"
                field_value = f"**Time:** {ava_time} Paris\n**Countdown:** {countdown}\n**Status:** {prism.get('status', 'Unknown')}"
                
                embed.add_field(name=field_name, value=field_value, inline=False)
        else:
            embed.add_field(
                name="📅 No Upcoming AVAs", 
                value="No AVA schedules found in the data.", 
                inline=False
            )
        
        # Add last update info
        if self.last_update:
            embed.set_footer(text=f"Last updated: {self.last_update.strftime('%H:%M:%S')}")
        
        return embed
    
    def create_comprehensive_embed(self):
        """Create a comprehensive embed with all AVA and prism information"""
        embed = discord.Embed(
            title="🏰 AFL Alliance - AVA Dashboard",
            description="Complete Alliance vs Alliance information panel",
            color=0x9932cc,
            timestamp=datetime.utcnow()
        )
        
        if not self.prism_data:
            embed.add_field(
                name="⚠️ No Data Available", 
                value="Prism data not loaded. Please wait for the next update or contact an administrator.", 
                inline=False
            )
            return embed
        
        # Current time information
        paris_time = datetime.now(self.paris_tz)
        embed.add_field(
            name="🕐 Current Dofus Touch Time (Paris)", 
            value=f"**{paris_time.strftime('%H:%M:%S')}** - {paris_time.strftime('%d/%m/%Y')}", 
            inline=True
        )
        
        # Next AVA countdown
        upcoming_avas = self.get_next_ava_times()
        if upcoming_avas:
            next_ava = upcoming_avas[0]
            countdown = self.format_countdown(next_ava['countdown'])
            embed.add_field(
                name="⏰ Next AVA Countdown", 
                value=f"**{countdown}**\n({next_ava['prism']['prism_name']} - {next_ava['ava_datetime'].strftime('%H:%M')})", 
                inline=True
            )
        
        embed.add_field(name="\u200b", value="\u200b", inline=True)  # Empty field for spacing
        
        # Upcoming AVAs (next 5)
        if upcoming_avas:
            ava_list = []
            for i, ava in enumerate(upcoming_avas[:5]):
                prism = ava['prism']
                countdown = self.format_countdown(ava['countdown'])
                ava_time = ava['ava_datetime'].strftime('%H:%M')
                status_emoji = "🟢" if prism.get('status', '').lower() == 'controlled' else "🔴"
                
                ava_list.append(
                    f"{status_emoji} **{prism.get('prism_name', 'Unknown')}** ({prism.get('server', 'Unknown')})\n"
                    f"⏰ {ava_time} Paris - *{countdown}*"
                )
            
            embed.add_field(
                name="⚔️ Upcoming AVAs", 
                value="\n\n".join(ava_list), 
                inline=False
            )
        
        # All prisms grouped by server
        servers = {}
        for prism in self.prism_data:
            server = prism.get('server', 'Unknown')
            if server not in servers:
                servers[server] = []
            servers[server].append(prism)
        
        for server, prisms in list(servers.items())[:3]:  # Limit to 3 servers to avoid embed limits
            prism_list = []
            for prism in prisms[:8]:  # Limit prisms per server
                status_emoji = "🟢" if prism.get('status', '').lower() == 'controlled' else "🔴"
                alliance_info = f" ({prism.get('alliance', 'Unknown')})" if prism.get('alliance') else ""
                prism_info = f"{status_emoji} **{prism.get('prism_name', 'Unknown')}**{alliance_info}"
                if prism.get('ava_time'):
                    prism_info += f"\n⏰ AVA: {prism.get('ava_time')}"
                prism_list.append(prism_info)
            
            if prism_list:
                embed.add_field(
                    name=f"🌍 {server} Server", 
                    value="\n\n".join(prism_list),
                    inline=True
                )
        
        # Footer with last update
        if self.last_update:
            embed.set_footer(
                text=f"Last updated: {self.last_update.strftime('%H:%M:%S')} • Auto-refreshes every 5 minutes",
                icon_url="https://cdn.discordapp.com/emojis/1234567890123456789.png"  # Optional: Add AFL logo
            )
        
        return embed

    class AVAPanelView(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)  # Persistent view
            self.cog = cog
        
        @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.secondary, custom_id="refresh_ava_panel")
        async def refresh_button(self, button: discord.ui.Button, interaction: discord.Interaction):
            await interaction.response.defer()
            
            try:
                # Force update data
                await self.cog.update_data()
                
                # Create new embed
                embed = self.cog.create_comprehensive_embed()
                
                # Update the message
                await interaction.edit_original_response(embed=embed, view=self)
                
                # Send ephemeral confirmation
                await interaction.followup.send("✅ Panel refreshed successfully!", ephemeral=True)
                
            except Exception as e:
                logger.exception("Error refreshing AVA panel")
                await interaction.followup.send("❌ Failed to refresh panel. Please try again.", ephemeral=True)
        
        @discord.ui.button(label="⏰ Timezone", style=discord.ButtonStyle.primary, custom_id="timezone_ava_panel")
        async def timezone_button(self, button: discord.ui.Button, interaction: discord.Interaction):
            modal = TimezoneModal(self.cog)
            await interaction.response.send_modal(modal)
    
    class TimezoneModal(discord.ui.Modal):
        def __init__(self, cog):
            super().__init__(title="Set Your Timezone")
            self.cog = cog
            
            self.timezone_input = discord.ui.TextInput(
                label="Timezone",
                placeholder="e.g., America/New_York, Europe/London, Asia/Tokyo",
                required=True,
                max_length=50
            )
            self.add_item(self.timezone_input)
        
        async def on_submit(self, interaction: discord.Interaction):
            try:
                timezone_str = self.timezone_input.value
                user_tz = pytz.timezone(timezone_str)
                paris_time = datetime.now(self.cog.paris_tz)
                user_time = paris_time.astimezone(user_tz)
                
                embed = discord.Embed(
                    title="🌍 Timezone Conversion",
                    color=0x00ff88
                )
                embed.add_field(
                    name="🕐 Dofus Touch Time (Paris)",
                    value=paris_time.strftime("%H:%M:%S - %d/%m/%Y"),
                    inline=False
                )
                embed.add_field(
                    name=f"🌍 Your Time ({timezone_str})",
                    value=user_time.strftime("%H:%M:%S - %d/%m/%Y"),
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            except Exception as e:
                await interaction.response.send_message(
                    "❌ Invalid timezone format. Please use formats like 'America/New_York', 'Europe/London', etc.",
                    ephemeral=True
                )

    @commands.slash_command(name="ava_panel", description="Create an interactive AVA information panel")
    async def ava_panel_command(self, ctx):
        """Create a comprehensive AVA panel with all information"""
        # Check if user has manage messages permission
        if not ctx.author.guild_permissions.manage_messages:
            await ctx.respond("❌ You need 'Manage Messages' permission to create AVA panels.", ephemeral=True)
            return
        
        await ctx.defer()
        
        try:
            # Create the comprehensive embed
            embed = self.create_comprehensive_embed()
            
            # Create the interactive view
            view = self.AVAPanelView(self)
            
            # Send the panel
            await ctx.followup.send(embed=embed, view=view)
            
        except Exception as e:
            logger.exception("Error creating AVA panel")
            error_embed = discord.Embed(
                title="❌ Error", 
                description="An error occurred while creating the AVA panel.", 
                color=0xff0000
            )
            await ctx.followup.send(embed=error_embed)
    
    @commands.slash_command(name="refresh_ava", description="Manually refresh AVA data (Admin only)")
    async def refresh_ava_command(self, ctx):
        """Manually refresh the AVA data"""
        # Check if user has admin permissions
        if not ctx.author.guild_permissions.administrator:
            await ctx.respond("❌ You need administrator permissions to use this command.", ephemeral=True)
            return
        
        await ctx.defer()
        
        try:
            await self.update_data()
            embed = discord.Embed(
                title="✅ Data Refreshed", 
                description=f"AVA data updated successfully at {datetime.now(self.paris_tz).strftime('%H:%M:%S')}", 
                color=0x00ff00
            )
            await ctx.followup.send(embed=embed)
        except Exception as e:
            logger.exception("Error refreshing AVA data")
            embed = discord.Embed(
                title="❌ Refresh Failed", 
                description="Failed to refresh AVA data. Check logs for details.", 
                color=0xff0000
            )
            await ctx.followup.send(embed=embed)

def setup(bot):
    bot.add_cog(PrismCog(bot))
