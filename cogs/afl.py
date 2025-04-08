import discord
from discord.ext import commands
from discord.ui import View, Button, Select, Modal, TextInput
from datetime import datetime, timedelta
import asyncio
from typing import Optional, Dict, List
import random

class AFLPanel(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.panel_message: Optional[discord.Message] = None
        self.PANEL_CHANNEL_ID = 1247977324293652530
        
        # In-memory data for the panel
        self.attack_teams = {
            "available": 12,
            "efficiency": 50,
            "cooldown": False,
            "cooldown_ends": None
        }
        
        self.targets = {
            "count": 3,
            "details": [
                {"name": "Pandora", "coordinates": "[12,5]", "priority": "HIGH"},
                {"name": "Blackwater", "coordinates": "[8,-3]", "priority": "MEDIUM"},
                {"name": "Brakmar", "coordinates": "[-13,27]", "priority": "LOW"}
            ]
        }
        
        self.stats = {
            "success": 15,
            "total": 20,
            "in_progress": 2,
            "failures": 3,
            "last_attack": datetime.now() - timedelta(hours=3)
        }
        
        # Color themes
        self.themes = {
            "default": {
                "primary": discord.Color.purple(),
                "success": discord.Color.green(),
                "danger": discord.Color.red(),
                "warning": discord.Color.gold(),
                "info": discord.Color.blue()
            },
            "dark": {
                "primary": discord.Color.from_rgb(30, 30, 46),
                "success": discord.Color.from_rgb(166, 227, 161),
                "danger": discord.Color.from_rgb(243, 139, 168),
                "warning": discord.Color.from_rgb(249, 226, 175),
                "info": discord.Color.from_rgb(137, 180, 250)
            }
        }
        self.current_theme = "default"
        
        # Task for auto-updating the panel
        self.update_task = None

    def cog_unload(self):
        if self.update_task:
            self.update_task.cancel()

    async def start_update_loop(self):
        self.update_task = self.bot.loop.create_task(self._update_loop())
        
    async def _update_loop(self):
        try:
            while True:
                # Simulate some random data changes
                if random.random() > 0.7:
                    self._simulate_data_change()
                
                # Update cooldown status
                if self.attack_teams["cooldown"] and self.attack_teams["cooldown_ends"] and datetime.now() > self.attack_teams["cooldown_ends"]:
                    self.attack_teams["cooldown"] = False
                
                # Update the panel
                await self.update_panel()
                
                # Wait for 5-10 minutes before next update
                await asyncio.sleep(random.randint(300, 600))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Update loop error: {e}")

    def _simulate_data_change(self):
        """Simulate some random data changes to make the panel more dynamic"""
        # Random team availability changes
        change = random.randint(-2, 2)
        self.attack_teams["available"] = max(0, min(20, self.attack_teams["available"] + change))
        
        # Random efficiency changes
        self.attack_teams["efficiency"] = max(10, min(90, self.attack_teams["efficiency"] + random.randint(-5, 5)))
        
        # Random target changes
        if random.random() > 0.8:
            self.targets["count"] = max(1, min(5, self.targets["count"] + random.choice([-1, 0, 1])))
        
        # Random stats
        if random.random() > 0.9 and not self.attack_teams["cooldown"]:
            result = random.choices(["success", "failure"], weights=[0.8, 0.2])[0]
            self.stats["total"] += 1
            self.stats[result + "es" if result == "success" else "s"] += 1
            self.stats["last_attack"] = datetime.now()
            
            # Set cooldown
            if random.random() > 0.6:
                self.attack_teams["cooldown"] = True
                self.attack_teams["cooldown_ends"] = datetime.now() + timedelta(minutes=random.randint(10, 30))

    async def create_panel_embed(self, is_admin: bool) -> discord.Embed:
        theme = self.themes[self.current_theme]
        
        embed = discord.Embed(
            title="🏹 AFL Panel System v2.0",
            color=theme["primary"],
            timestamp=datetime.now()
        )

        embed.set_author(
            name="AFL Attack System",
            icon_url="https://i.imgur.com/qwJnpQr.png"  # Generic game icon
        )

        if is_admin:
            # Progress bar function
            def progress_bar(value, max_value=100, length=10):
                filled = int((value / max_value) * length)
                return '▰' * filled + '▱' * (length - filled)
            
            # Calculate time remaining for cooldown
            cooldown_status = "🟢 Ready"
            if self.attack_teams["cooldown"] and self.attack_teams["cooldown_ends"]:
                time_remaining = self.attack_teams["cooldown_ends"] - datetime.now()
                if time_remaining.total_seconds() > 0:
                    minutes, seconds = divmod(time_remaining.total_seconds(), 60)
                    cooldown_status = f"🔴 {int(minutes)}m {int(seconds)}s"
                else:
                    self.attack_teams["cooldown"] = False

            embed.description = (
                "```ansi\n"
                "[2;31m╔═══════════════════════════════════════╗[0m\n"
                "[2;31m║[0m [2;34mPERCEPTOR ATTACK SYSTEM[0m               [2;31m║[0m\n"
                "[2;31m║[0m [2;37mVersion[0m: 2.0.0                        [2;31m║[0m\n"
                "[2;31m║[0m [2;32mStatus[0m: [2;32mOPERATIONAL[0m                    [2;31m║[0m\n"
                "[2;31m╚═══════════════════════════════════════╝[0m\n```\n"
                
                "**📡 System Overview:**\n"
                "• Real-time perceptor monitoring active\n"
                "• Tactical AVA deployment ready\n"
                "• Neural network prediction engine online\n"
                f"• Last attack: {self.stats['last_attack'].strftime('%H:%M:%S')}\n"
            )

            # Add team status
            efficiency_bar = progress_bar(self.attack_teams["efficiency"])
            embed.add_field(
                name="📌 Attack Team",
                value=(
                    "```ml\n"
                    f"◉ Available: {self.attack_teams['available']} members\n"
                    f"◉ Efficiency: {efficiency_bar} {self.attack_teams['efficiency']}%\n"
                    f"◉ Cooldown: {cooldown_status}\n```"
                ),
                inline=True
            )

            # Target information
            priority_colors = {"HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟡"}
            target_display = "\n".join([
                f"◉ {priority_colors[t['priority']]} {t['name']} {t['coordinates']}"
                for t in self.targets["details"][:3]
            ])
            
            if not target_display:
                target_display = "◉ No active targets"
                
            embed.add_field(
                name="📌 Priority Targets",
                value=(
                    "```ml\n"
                    f"{target_display}\n"
                    f"◉ Total targets: {self.targets['count']}\n```"
                ),
                inline=True
            )

            # Statistics information
            success_rate = int((self.stats["success"] / self.stats["total"]) * 100) if self.stats["total"] > 0 else 0
            success_bar = progress_bar(success_rate)
            
            embed.add_field(
                name="📌 Operation Stats",
                value=(
                    "```ml\n"
                    f"◉ Success rate: {success_bar} {success_rate}%\n"
                    f"◉ Complete: {self.stats['success']}/{self.stats['total']}\n"
                    f"◉ Active: {self.stats['in_progress']}\n```"
                ),
                inline=True
            )

            # Add a live map with pseudo-ASCII art
            embed.add_field(
                name="🗺️ Tactical Map",
                value=(
                    "```\n"
                    "      N       \n"
                    "      ↑       \n"
                    "  ┌───┼───┐   \n"
                    "W ←   •   → E \n"
                    "  └───┼───┘   \n"
                    "      ↓       \n"
                    "      S       \n"
                    "```"
                ),
                inline=False
            )

            # Add recent activity log
            embed.add_field(
                name="📋 Recent Activity",
                value=(
                    "```diff\n"
                    "+ [12:45] Target acquired: Eastern Perceptor\n"
                    "- [11:30] Defense alert: Western approach\n"
                    "+ [10:15] Attack successful: +25 territories\n"
                    "```"
                ),
                inline=False
            )

        else:
            # Non-admin view
            embed.description = (
                "```ansi\n"
                "[2;31m╔═══════════════════════════════════════╗[0m\n"
                "[2;31m║[0m [2;34mAFL ATTACK SYSTEM[0m                     [2;31m║[0m\n"
                "[2;31m║[0m [2;37mSECURITY LEVEL[0m: [2;31mRED[0m                  [2;31m║[0m\n"
                "[2;31m║[0m [2;31mACCESS DENIED - ADMIN PRIVILEGES REQUIRED[0m [2;31m║[0m\n"
                "[2;31m╚═══════════════════════════════════════╝[0m\n```\n"
                
                "**⚠️ RESTRICTED ACCESS ⚠️**\n\n"
                "This terminal requires elevated permissions.\n"
                "Please contact a guild officer for assistance.\n\n"
                "```\nSYSTEM: LOCKED\nBIOSCAN: NEGATIVE\nIDENTITY: UNVERIFIED\n```"
            )

            # Add encrypted fields
            for i in range(3):
                embed.add_field(
                    name=f"📌 {"▓" * random.randint(5, 10)}",
                    value="```\n" + "\n".join(["█" * random.randint(10, 20) for _ in range(3)]) + "\n```",
                    inline=True
                )

        # Add system info footer
        uptime = "98.7%"
        latency = f"{round(self.bot.latency * 1000)}ms"
        embed.set_footer(
            text=f"⚡ System Uptime: {uptime} • Latency: {latency} • Last updated: {datetime.now().strftime('%H:%M:%S')}",
            icon_url="https://i.imgur.com/JrRBTVu.png"  # Generic system icon
        )

        return embed

    class AFLPanelView(View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

            # Attack Button
            attack_button = Button(
                label="Attack", 
                style=discord.ButtonStyle.danger, 
                emoji="⚔️", 
                custom_id="afl_attack_button"
            )
            attack_button.callback = self.attack_callback
            self.add_item(attack_button)
            
            # Targets Button
            targets_button = Button(
                label="Targets", 
                style=discord.ButtonStyle.primary, 
                emoji="🎯", 
                custom_id="afl_targets_button"
            )
            targets_button.callback = self.target_callback
            self.add_item(targets_button)
            
            # Team Button
            team_button = Button(
                label="Team", 
                style=discord.ButtonStyle.success, 
                emoji="👥", 
                custom_id="afl_team_button"
            )
            team_button.callback = self.team_callback
            self.add_item(team_button)

            # Stats Button
            stats_button = Button(
                label="Intel", 
                style=discord.ButtonStyle.secondary, 
                emoji="📊", 
                custom_id="afl_stats_button"
            )
            stats_button.callback = self.stats_callback
            self.add_item(stats_button)
            
            # Help Button
            help_button = Button(
                label="Help", 
                style=discord.ButtonStyle.secondary, 
                emoji="❓", 
                custom_id="afl_help_button"
            )
            help_button.callback = self.help_callback
            self.add_item(help_button)

            # Add theme selector (second row)
            theme_select = Select(
                placeholder="🎨 Theme",
                custom_id="afl_theme_select",
                options=[
                    discord.SelectOption(label="Default Theme", value="default", emoji="🟣"),
                    discord.SelectOption(label="Dark Theme", value="dark", emoji="🖤")
                ]
            )
            theme_select.callback = self.theme_callback
            self.add_item(theme_select)

        async def check_admin(self, interaction: discord.Interaction) -> bool:
            if interaction.user.guild_permissions.administrator:
                return True
            await interaction.response.send_message(
                "⛔ Access denied. You need administrator permissions to use the AFL Panel.",
                ephemeral=True
            )
            return False

        async def attack_callback(self, interaction: discord.Interaction):
            if not await self.check_admin(interaction): return
            
            if self.cog.attack_teams["cooldown"]:
                time_remaining = self.cog.attack_teams["cooldown_ends"] - datetime.now()
                if time_remaining.total_seconds() > 0:
                    minutes, seconds = divmod(time_remaining.total_seconds(), 60)
                    await interaction.response.send_message(
                        f"⏳ Attack teams are on cooldown. Ready in {int(minutes)}m {int(seconds)}s.",
                        ephemeral=True
                    )
                    return
            
            # Attack modal
            class AttackModal(Modal, title="🏹 Launch Attack Operation"):
                target = TextInput(
                    label="Target Name",
                    placeholder="Enter target name or coordinates",
                    required=True,
                    style=discord.TextStyle.short
                )
                
                squad_size = TextInput(
                    label="Squad Size",
                    placeholder="Enter number of attackers (1-10)",
                    required=True,
                    style=discord.TextStyle.short
                )
                
                strategy = TextInput(
                    label="Attack Strategy",
                    placeholder="Brief description of attack plan",
                    required=True,
                    style=discord.TextStyle.paragraph
                )
                
                async def on_submit(self, modal_interaction: discord.Interaction):
                    embed = discord.Embed(
                        title="🔥 Attack Operation Launched",
                        description=(
                            f"**Target:** {self.target.value}\n"
                            f"**Squad Size:** {self.squad_size.value}\n"
                            f"**Strategy:** {self.strategy.value}\n\n"
                            "Operation has been initiated. Stand by for results."
                        ),
                        color=discord.Color.brand_red()
                    )
                    
                    # Set a cooldown
                    view.cog.attack_teams["cooldown"] = True
                    view.cog.attack_teams["cooldown_ends"] = datetime.now() + timedelta(minutes=random.randint(5, 15))
                    view.cog.stats["in_progress"] += 1
                    
                    # Schedule a result to appear later
                    view.cog.bot.loop.create_task(
                        view.simulate_attack_result(modal_interaction, self.target.value, int(self.squad_size.value))
                    )
                    
                    await modal_interaction.response.send_message(embed=embed, ephemeral=True)
                    await view.cog.update_panel()
            
            view = self
            await interaction.response.send_modal(AttackModal())

        async def simulate_attack_result(self, interaction, target, squad_size):
            # Wait for a random amount of time to simulate attack duration
            await asyncio.sleep(random.randint(30, 60))
            
            # Determine result
            success = random.random() < (0.7 + (squad_size * 0.03))  # Larger squads have better chance
            
            # Update stats
            self.cog.stats["in_progress"] -= 1
            self.cog.stats["total"] += 1
            
            if success:
                self.cog.stats["success"] += 1
                loot = random.randint(1000, 5000) * squad_size
                embed = discord.Embed(
                    title="✅ Attack Operation Successful",
                    description=(
                        f"**Target:** {target}\n"
                        f"**Squad:** {squad_size} members\n"
                        f"**Reward:** {loot:,} kamas\n\n"
                        "All team members have returned safely."
                    ),
                    color=discord.Color.green()
                )
            else:
                self.cog.stats["failures"] += 1
                embed = discord.Embed(
                    title="❌ Attack Operation Failed",
                    description=(
                        f"**Target:** {target}\n"
                        f"**Squad:** {squad_size} members\n"
                        f"**Reason:** Enemy perceptor was too well defended\n\n"
                        "Team retreated to safety. No casualties reported."
                    ),
                    color=discord.Color.red()
                )
            
            self.cog.stats["last_attack"] = datetime.now()
            
            # Send result message to user if they're still around
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except:
                pass
                
            # Update the panel
            await self.cog.update_panel()

        async def target_callback(self, interaction: discord.Interaction):
            if not await self.check_admin(interaction): return
            
            embed = discord.Embed(
                title="🎯 Target Management System",
                description="Current active targets in our tracking system.",
                color=discord.Color.blue()
            )
            
            # Display all targets with details
            for i, target in enumerate(self.cog.targets["details"]):
                priority_colors = {"HIGH": "🔴", "MEDIUM": "🟠", "LOW": "🟡"}
                embed.add_field(
                    name=f"{priority_colors[target['priority']]} {target['name']}",
                    value=(
                        f"**Location:** {target['coordinates']}\n"
                        f"**Priority:** {target['priority']}\n"
                        f"**Est. Difficulty:** {'⭐' * random.randint(1, 5)}\n"
                    ),
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)

        async def team_callback(self, interaction: discord.Interaction):
            if not await self.check_admin(interaction): return
            
            # Create members with random stats
            members = []
            for i in range(self.cog.attack_teams["available"]):
                status = random.choice(["Ready", "Available", "Standby"])
                specialty = random.choice(["Sniper", "Frontline", "Support", "Scout"])
                level = random.randint(150, 200)
                members.append({
                    "name": f"Agent {(100 + i):03d}",
                    "status": status,
                    "specialty": specialty,
                    "level": level
                })
            
            embed = discord.Embed(
                title="👥 Attack Team Management",
                description=f"**Total Members:** {self.cog.attack_teams['available']}\n**Team Efficiency:** {self.cog.attack_teams['efficiency']}%",
                color=discord.Color.green()
            )
            
            # Show first 9 members in fields
            for i, member in enumerate(members[:9]):
                embed.add_field(
                    name=f"{member['name']} - Lvl {member['level']}",
                    value=f"**Status:** {member['status']}\n**Role:** {member['specialty']}",
                    inline=True
                )
            
            # If more members, show count
            if len(members) > 9:
                embed.set_footer(text=f"+ {len(members) - 9} more members not shown")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)

        async def stats_callback(self, interaction: discord.Interaction):
            if not await self.check_admin(interaction): return
            
            embed = discord.Embed(
                title="📊 Intelligence Center",
                description="Strategic data and operational metrics",
                color=discord.Color.gold()
            )
            
            # Calculate success rate
            success_rate = int((self.cog.stats["success"] / self.cog.stats["total"]) * 100) if self.cog.stats["total"] > 0 else 0
            
            # Historical data (simulated)
            embed.add_field(
                name="Historical Performance",
                value=(
                    f"**Success Rate:** {success_rate}%\n"
                    f"**Total Operations:** {self.cog.stats['total']}\n"
                    f"**Successful:** {self.cog.stats['success']}\n"
                    f"**Failed:** {self.cog.stats['failures']}\n"
                    f"**In Progress:** {self.cog.stats['in_progress']}"
                ),
                inline=True
            )
            
            # Territory control (simulated)
            territories = random.randint(10, 50)
            embed.add_field(
                name="Territory Control",
                value=(
                    f"**Total Territories:** {territories}\n"
                    f"**Defended:** {int(territories * 0.8)}\n"
                    f"**At Risk:** {int(territories * 0.2)}\n"
                    f"**Weekly Change:** +{random.randint(0, 5)}"
                ),
                inline=True
            )
            
            # Resource metrics (simulated)
            embed.add_field(
                name="Resource Metrics",
                value=(
                    f"**Kamas Earned:** {random.randint(50000, 250000):,}\n"
                    f"**Resources Gathered:** {random.randint(1000, 5000):,}\n"
                    f"**Cost per Operation:** {random.randint(1000, 3000):,}"
                ),
                inline=True
            )
            
            # Enemy activity (simulated)
            activity_levels = ["Low", "Moderate", "High", "Critical"]
            current_level = random.choice(activity_levels)
            embed.add_field(
                name="Enemy Activity",
                value=(
                    f"**Current Level:** {current_level}\n"
                    f"**Hot Zones:** {random.randint(1, 3)}\n"
                    f"**Recent Attacks:** {random.randint(0, 5)}\n"
                    f"**Threat Assessment:** {'⚠️' * random.randint(1, 3)}"
                ),
                inline=True
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)

        async def help_callback(self, interaction: discord.Interaction):
            is_admin = await self.check_admin(interaction)
            if not is_admin:
                embed = discord.Embed(
                    title="❓ Help - Access Denied",
                    description=(
                        "```\nERROR: INSUFFICIENT CLEARANCE\n"
                        "ACCESS TO DOCUMENTATION RESTRICTED\n"
                        "CONTACT SYSTEM ADMINISTRATOR\n```"
                    ),
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            embed = discord.Embed(
                title="❓ AFL Panel System - Command Guide",
                description=(
                    "Welcome to the AFL Attack System v2.0! This control panel allows you to "
                    "manage and coordinate attacks against enemy perceptors.\n\n"
                    "**Available Commands:**"
                ),
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="⚔️ Attack",
                value="Launch a coordinated attack on an enemy perceptor. You'll be prompted to enter target details and strategy.",
                inline=False
            )
            
            embed.add_field(
                name="🎯 Targets",
                value="View and manage potential targets. Displays locations, priorities, and estimated difficulty.",
                inline=False
            )
            
            embed.add_field(
                name="👥 Team",
                value="Manage your attack team members, view their status, specialties, and availability.",
                inline=False
            )
            
            embed.add_field(
                name="📊 Intel",
                value="Access strategic data including historical performance, territory control, and enemy activity reports.",
                inline=False
            )
            
            embed.add_field(
                name="🎨 Theme",
                value="Change the visual theme of your private panel view.",
                inline=False
            )
            
            embed.set_footer(text="AFL Panel System v2.0 • Administrator Access Granted")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        async def theme_callback(self, interaction: discord.Interaction):
            if not await self.check_admin(interaction): return
            
            selected_theme = interaction.data["values"][0]
            self.cog.current_theme = selected_theme
            
            theme_names = {"default": "Default Purple", "dark": "Dark Mode"}
            
            await interaction.response.send_message(
                f"🎨 Theme changed to **{theme_names[selected_theme]}**. Your personal view will be updated.",
                ephemeral=True
            )
            
            updated_embed = await self.cog.create_panel_embed(is_admin=True)
            await interaction.followup.send(
                content="🔄 Your updated panel view:",
                embed=updated_embed,
                ephemeral=True
            )

    async def update_panel(self):
        """Update the panel message with the latest data"""
        if not self.panel_message:
            await self.ensure_panel()
            return
            
        try:
            channel = self.bot.get_channel(self.PANEL_CHANNEL_ID)
            if not channel:
                return
                
            # Update with default view (non-admin)
            default_embed = await self.create_panel_embed(is_admin=False)
            view = self.AFLPanelView(self)
            
            await self.panel_message.edit(embed=default_embed, view=view)
        except discord.NotFound:
            self.panel_message = None
            await self.ensure_panel()
        except Exception as e:
            print(f"Error updating panel: {e}")

    async def ensure_panel(self):
        """Make sure the panel exists in the channel"""
        channel = self.bot.get_channel(self.PANEL_CHANNEL_ID)
        if not channel:
            print(f"❌ Channel {self.PANEL_CHANNEL_ID} not found.")
            return

        if not self.panel_message:
            async for msg in channel.history(limit=20):
                if msg.author == self.bot.user and msg.pinned:
                    self.panel_message = msg
                    break

        view = self.AFLPanelView(self)
        default_embed = await self.create_panel_embed(is_admin=False)

        if self.panel_message:
            try:
                await self.panel_message.edit(embed=default_embed, view=view)
            except discord.NotFound:
                self.panel_message = None
                await self.ensure_panel()
        else:
            self.panel_message = await channel.send(embed=default_embed, view=view)
            await self.panel_message.pin(reason="AFL Panel System")

    @commands.Cog.listener()
    async def on_ready(self):
        await self.ensure_panel()
        await self.start_update_loop()
        print(f"✅ AFL Panel System v2.0 operational • {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def refreshpanel(self, ctx):
        """Admin command to force refresh the panel"""
        await ctx.message.delete()
        await self.update_panel()
        await ctx.send("🔄 AFL Panel refreshed!", delete_after=5)

async def setup(bot: commands.Bot):
    await bot.add_cog(AFLPanel(bot))
