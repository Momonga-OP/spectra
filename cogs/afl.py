import discord
from discord.ext import commands
from discord.ui import View, Button
from datetime import datetime
import asyncio
from typing import Optional

class AFLPanel(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.panel_message: Optional[discord.Message] = None
        # Channel ID for the panel
        self.PANEL_CHANNEL_ID = 1247728759780413480

    async def create_panel_embed(self, is_admin: bool) -> discord.Embed:
        """Create the panel embed with content visibility based on admin status"""
        embed = discord.Embed(
            title="🏹 AFL Panel System for Attack Perco",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        
        embed.set_author(
            name="AFL Attack System",
            icon_url="https://github.com/your-repo/assets/attack-icon.png?raw=true"  # Replace with actual icon URL
        )
        
        if is_admin:
            # Admin view - can see all content
            embed.description = (
                "```diff\n+ PERCEPTOR ATTACK SYSTEM [v1.0.0]\n```\n"
                "**📋 Instructions:**\n"
                "1️⃣ Select target guild\n"
                "2️⃣ Indicate number of perceptors\n"
                "3️⃣ Launch coordinated attack\n\n"
                "```ansi\n[2;34m[!] System status: [0m[2;32mOPERATIONAL[0m```"
            )
            
            # Add fields for status tracking
            embed.add_field(
                name="📌 Attack Team",
                value=(
                    "```prolog\n"
                    "[🟢 Available] 12\n"
                    "[📊 Efficiency] ▰▰▰▰▰▱▱▱▱▱ 50%\n"
                    "[⏱ Cooldown] 🟢 Inactive```"
                ),
                inline=True
            )
            
            embed.add_field(
                name="📌 Points of Interest",
                value=(
                    "```prolog\n"
                    "[🎯 Targets] 3\n"
                    "[💰 Est. Gains] 250000 kamas\n"
                    "[📈 Priority] HIGH```"
                ),
                inline=True
            )
            
            embed.add_field(
                name="📌 Statistics",
                value=(
                    "```prolog\n"
                    "[✅ Success] 15/20\n"
                    "[🔄 In Progress] 2\n"
                    "[❌ Failures] 3```"
                ),
                inline=True
            )
        else:
            # Non-admin view - encrypted content
            embed.description = (
                "```diff\n+ AFL ATTACK SYSTEM [v1.0.0]\n```\n"
                "**⚠️ Restricted Access ⚠️**\n"
                "```\n"
                "C0D3 4CC35S R3QU1R3D\n"
                "45FL-P4N3L-3NCRYPT3D\n"
                "C0NT4CT 4DM1N F0R 4CC35S\n"
                "```\n"
                "```ansi\n[2;31m[!] Status: [0m[2;31mACCESS DENIED[0m```"
            )
            
            # Add encrypted fields
            embed.add_field(
                name="📌 ##########",
                value="```\n**********\n**********\n**********```",
                inline=True
            )
            
            embed.add_field(
                name="📌 ##########",
                value="```\n**********\n**********\n**********```",
                inline=True
            )
            
            embed.add_field(
                name="📌 ##########",
                value="```\n**********\n**********\n**********```",
                inline=True
            )
        
        embed.set_footer(
            text=f"Last update: {datetime.now().strftime('%H:%M:%S')}",
            icon_url="https://github.com/your-repo/assets/hourglass.png?raw=true"  # Replace with actual icon URL
        )
        
        return embed

    class AFLPanelView(View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog
            
            # Attack button
            self.attack_button = Button(
                label="Attack",
                style=discord.ButtonStyle.danger,
                emoji="⚔️",
                custom_id="afl_attack_button"
            )
            self.attack_button.callback = self.attack_callback
            self.add_item(self.attack_button)
            
            # Target button
            self.target_button = Button(
                label="Targets",
                style=discord.ButtonStyle.primary,
                emoji="🎯",
                custom_id="afl_target_button"
            )
            self.target_button.callback = self.target_callback
            self.add_item(self.target_button)
            
            # Team button
            self.team_button = Button(
                label="Team",
                style=discord.ButtonStyle.success,
                emoji="👥",
                custom_id="afl_team_button"
            )
            self.team_button.callback = self.team_callback
            self.add_item(self.team_button)
            
            # Stats button
            self.stats_button = Button(
                label="Stats",
                style=discord.ButtonStyle.secondary,
                emoji="📊",
                custom_id="afl_stats_button"
            )
            self.stats_button.callback = self.stats_callback
            self.add_item(self.stats_button)
            
            # Help button
            self.help_button = Button(
                label="Help",
                style=discord.ButtonStyle.secondary,
                emoji="❓",
                custom_id="afl_help_button"
            )
            self.help_button.callback = self.help_callback
            self.add_item(self.help_button)
        
        async def check_admin(self, interaction: discord.Interaction) -> bool:
            """Check if the user has admin permissions"""
            # Check for admin permission
            if interaction.user.guild_permissions.administrator:
                return True
            await interaction.response.send_message("⛔ You don't have the necessary permissions for this action.", ephemeral=True)
            return False
            
        async def attack_callback(self, interaction: discord.Interaction):
            if not await self.check_admin(interaction):
                return
                
            await interaction.response.send_message("🏹 Attack system under development...", ephemeral=True)
            
        async def target_callback(self, interaction: discord.Interaction):
            if not await self.check_admin(interaction):
                return
                
            await interaction.response.send_message("🎯 Target management under development...", ephemeral=True)
            
        async def team_callback(self, interaction: discord.Interaction):
            if not await self.check_admin(interaction):
                return
                
            await interaction.response.send_message("👥 Team management under development...", ephemeral=True)
            
        async def stats_callback(self, interaction: discord.Interaction):
            if not await self.check_admin(interaction):
                return
                
            await interaction.response.send_message("📊 Statistics under development...", ephemeral=True)
            
        async def help_callback(self, interaction: discord.Interaction):
            # Non-admin help is also encrypted
            if not await self.check_admin(interaction):
                embed = discord.Embed(
                    title="❓ 4FL 5Y5T3M H3LP",
                    description=(
                        "```\n"
                        "3NCRYPT3D H3LP F1L3\n"
                        "4CC355 D3N13D\n"
                        "R3QU35T 4DM1N P3RM15510N5\n"
                        "```"
                    ),
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
                
            # Admin help view
            embed = discord.Embed(
                title="❓ Help - AFL Panel System",
                description=(
                    "The AFL Panel System is designed for managing perceptor attacks.\n\n"
                    "**Main features:**\n"
                    "• Attack coordination\n"
                    "• Target tracking\n"
                    "• Team management\n"
                    "• Statistics\n\n"
                    "**Note:** Full system access requires administrator permissions."
                ),
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def ensure_panel(self):
        """Make sure the panel exists in the designated channel"""
        channel = self.bot.get_channel(self.PANEL_CHANNEL_ID)
        if not channel:
            print(f"❌ Channel {self.PANEL_CHANNEL_ID} not found.")
            return

        # Try to find an existing panel message
        if not self.panel_message:
            async for msg in channel.history(limit=20):
                if msg.author == self.bot.user and msg.pinned:
                    self.panel_message = msg
                    break

        view = self.AFLPanelView(self)
        
        # Default embed (non-admin view)
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
        """Initialize the panel when the bot starts"""
        await self.ensure_panel()
        print(f"✅ AFL Panel System operational • {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle dynamic panel updating based on who views it"""
        # Only process interactions with our panel message
        if not self.panel_message or interaction.message.id != self.panel_message.id:
            return
            
        # Check if this is a view interaction
        if interaction.type == discord.InteractionType.component:
            # Update the panel based on who's viewing it
            is_admin = interaction.user.guild_permissions.administrator
            updated_embed = await self.create_panel_embed(is_admin=is_admin)
            
            # Only show the updated embed to the current user
            await interaction.response.send_message(
                "Refreshing panel...",
                ephemeral=True,
                delete_after=0.1
            )
            
            # Send the personalized view as an ephemeral follow-up
            if is_admin:
                admin_embed = updated_embed
                await interaction.followup.send(
                    content="🔒 Your admin view of the AFL panel:",
                    embed=admin_embed,
                    ephemeral=True
                )

async def setup(bot: commands.Bot):
    await bot.add_cog(AFLPanel(bot))
