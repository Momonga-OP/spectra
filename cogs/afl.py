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
        self.PANEL_CHANNEL_ID = 1247728759780413480

    async def create_panel_embed(self, is_admin: bool) -> discord.Embed:
        embed = discord.Embed(
            title="🏹 AFL Panel System for Attack Perco",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )

        embed.set_author(
            name="AFL Attack System",
            icon_url="https://github.com/your-repo/assets/attack-icon.png?raw=true"
        )

        if is_admin:
            embed.description = (
                "```diff\n+ PERCEPTOR ATTACK SYSTEM [v1.0.0]\n```\n"
                "**📋 Panel Capabilities:**\n"
                "• Auto-locates enemy perceptors\n"
                "• Registers and dispatches attacks\n"
                "• Early warning for enemy aggression\n"
                "• Acts as AVA Coordination Center\n"
                "• Uses external data for real-time insights\n\n"
                "```ansi\n[2;34m[!] System status: [0m[2;32mOPERATIONAL[0m```"
            )

            embed.add_field(
                name="📌 Attack Team",
                value=(
                    "```prolog\n"
                    "[🟢 Available] 12\n"
                    "[📊 Efficiency] ▰▰▰▰▰▱▱▱▱▱ 50%\n"
                    "[⏱ Cooldown] 🟢 Inactive\n```"
                ),
                inline=True
            )

            embed.add_field(
                name="📌 Points of Interest",
                value=(
                    "```prolog\n"
                    "[🎯 Targets] 3\n"
                    "[💰 Est. Gains] ? kamas\n"
                    "[📈 Priority] HIGH\n```"
                ),
                inline=True
            )

            embed.add_field(
                name="📌 Statistics",
                value=(
                    "```prolog\n"
                    "[✅ Success] 15/20\n"
                    "[🔄 In Progress] 2\n"
                    "[❌ Failures] 3\n```"
                ),
                inline=True
            )

        else:
            embed.description = (
                "```diff\n+ AFL ATTACK SYSTEM [v1.0.0]\n```\n"
                "**⚠️ Restricted Access ⚠️**\n"
                "```\nC0D3 4CC35S R3QU1R3D\n45FL-P4N3L-3NCRYPT3D\nC0NT4CT 4DM1N F0R 4CC35S\n```\n"
                "```ansi\n[2;31m[!] Status: [0m[2;31mACCESS DENIED[0m```"
            )

            for _ in range(3):
                embed.add_field(
                    name="📌 ##########",
                    value="```\n**********\n**********\n**********\n```",
                    inline=True
                )

        embed.set_footer(
            text=f"Last update: {datetime.now().strftime('%H:%M:%S')}",
            icon_url="https://github.com/your-repo/assets/hourglass.png?raw=true"
        )

        return embed

    class AFLPanelView(View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

            buttons = [
                ("Attack", discord.ButtonStyle.danger, "⚔️", self.attack_callback),
                ("Targets", discord.ButtonStyle.primary, "🎯", self.target_callback),
                ("Team", discord.ButtonStyle.success, "👥", self.team_callback),
                ("Stats", discord.ButtonStyle.secondary, "📊", self.stats_callback),
                ("Help", discord.ButtonStyle.secondary, "❓", self.help_callback)
            ]

            for label, style, emoji, callback in buttons:
                button = Button(label=label, style=style, emoji=emoji, custom_id=f"afl_{label.lower()}_button")
                button.callback = callback
                self.add_item(button)

        async def check_admin(self, interaction: discord.Interaction) -> bool:
            if interaction.user.guild_permissions.administrator:
                return True
            await interaction.response.send_message("⛔ You don't have the necessary permissions for this action.", ephemeral=True)
            return False

        async def attack_callback(self, interaction: discord.Interaction):
            if not await self.check_admin(interaction): return
            await interaction.response.send_message("🏹 Attack system under development...", ephemeral=True)

        async def target_callback(self, interaction: discord.Interaction):
            if not await self.check_admin(interaction): return
            await interaction.response.send_message("🎯 Target management under development...", ephemeral=True)

        async def team_callback(self, interaction: discord.Interaction):
            if not await self.check_admin(interaction): return
            await interaction.response.send_message("👥 Team management under development...", ephemeral=True)

        async def stats_callback(self, interaction: discord.Interaction):
            if not await self.check_admin(interaction): return
            await interaction.response.send_message("📊 Statistics under development...", ephemeral=True)

        async def help_callback(self, interaction: discord.Interaction):
            is_admin = await self.check_admin(interaction)
            if not is_admin:
                embed = discord.Embed(
                    title="❓ 4FL 5Y5T3M H3LP",
                    description=(
                        "```\n3NCRYPT3D H3LP F1L3\n4CC355 D3N13D\nR3QU35T 4DM1N P3RM15510N5\n```"
                    ),
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            embed = discord.Embed(
                title="❓ Help - AFL Panel System",
                description=(
                    "**🛠 AFL Control Suite Overview:**\n\n"
                    "• **AVA Tactics** — strategic positioning and engagement zones\n"
                    "• **Zone Knowledge** — real-time map alerts & region tracking\n"
                    "• **Live Player Count** — real-world ally & enemy activity awareness\n"
                    "• **Enemy Fetching** — fast lookup for enemy stats & gear\n"
                    "• **AI Assistance** — automated threat level & priority analysis\n"
                    "• **File Integration** — sync with `Sparta True power.xlsx` for extended data tracking\n"
                ),
                color=discord.Color.blurple()
            )
            embed.set_footer(text="AFL Panel Assistant — Intelligence First.")
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def ensure_panel(self):
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
        print(f"✅ AFL Panel System operational • {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if not self.panel_message or interaction.message.id != self.panel_message.id:
            return

        if interaction.type == discord.InteractionType.component:
            is_admin = interaction.user.guild_permissions.administrator
            updated_embed = await self.create_panel_embed(is_admin=is_admin)
            await interaction.response.send_message("Refreshing panel...", ephemeral=True, delete_after=0.1)
            if is_admin:
                await interaction.followup.send(
                    content="🔒 Your admin view of the AFL panel:",
                    embed=updated_embed,
                    ephemeral=True
                )

async def setup(bot: commands.Bot):
    await bot.add_cog(AFLPanel(bot))
