import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class Zubic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.target_member_count = 200
        self.announcement_channel_id = 1213971902775689336
        self.gifter_user_id = 851039092976386079
        self.prize_amount = "5 MK"
        self.triggered = False  # To ensure it only triggers once
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Triggered when a new member joins the server"""
        try:
            guild = member.guild
            member_count = guild.member_count
            
            logger.info(f"New member joined: {member.name}. Current member count: {member_count}")
            
            # Check if this is the 200th member and hasn't been triggered yet
            if member_count == self.target_member_count and not self.triggered:
                await self.celebrate_200th_member(member)
                self.triggered = True  # Prevent multiple triggers
                
        except Exception as e:
            logger.exception(f"Error in on_member_join: {e}")
    
    async def celebrate_200th_member(self, member):
        """Send the celebration announcement for the 200th member"""
        try:
            # Get the announcement channel
            channel = self.bot.get_channel(self.announcement_channel_id)
            if not channel:
                logger.error(f"Could not find announcement channel with ID: {self.announcement_channel_id}")
                return
            
            # Get the gifter user
            gifter = await self.bot.fetch_user(self.gifter_user_id)
            if not gifter:
                logger.error(f"Could not find gifter user with ID: {self.gifter_user_id}")
                return
            
            # Create the embedded announcement
            embed = discord.Embed(
                title="🎉 CONGRATULATIONS! 🎉",
                description=f"**{member.mention} is our 200th Member!**",
                color=0x00ff00  # Green color
            )
            
            embed.add_field(
                name="🏆 Special Prize Winner!",
                value=(
                    f"Congrats for being our Number 200 Member welcome to our AFL Alliance!\n\n"
                    f"For this occasion you have won **{self.prize_amount}** gifted to you by {gifter.mention}!\n\n"
                    f"Please Contact {gifter.mention} to get your Reward.\n\n"
                    f"*Next time don't call me Drunk KAREN* 😂"
                ),
                inline=False
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            embed.set_footer(text=f"Welcome to the server, {member.display_name}!")
            
            # Send the announcement with @everyone ping
            await channel.send(
                content="@everyone 🎊 **SPECIAL ANNOUNCEMENT** 🎊",
                embed=embed
            )
            
            logger.info(f"200th member celebration sent for {member.name}")
            
        except Exception as e:
            logger.exception(f"Error sending 200th member celebration: {e}")
    
    @commands.command(name='reset_zubic')
    @commands.has_permissions(administrator=True)
    async def reset_zubic(self, ctx):
        """Reset the zubic trigger (Admin only)"""
        self.triggered = False
        await ctx.send("✅ Zubic trigger has been reset!")
    
    @commands.command(name='test_zubic')
    @commands.has_permissions(administrator=True)
    async def test_zubic(self, ctx):
        """Test the zubic announcement (Admin only)"""
        await self.celebrate_200th_member(ctx.author)
        await ctx.send("✅ Zubic test announcement sent!")
    
    @commands.command(name='zubic_status')
    async def zubic_status(self, ctx):
        """Check the current status of the zubic system"""
        guild = ctx.guild
        member_count = guild.member_count
        remaining = self.target_member_count - member_count
        
        embed = discord.Embed(
            title="Zubic Status",
            color=0x0099ff
        )
        
        embed.add_field(
            name="Current Members",
            value=f"{member_count}/{self.target_member_count}",
            inline=True
        )
        
        embed.add_field(
            name="Members Remaining",
            value=f"{remaining if remaining > 0 else 0}",
            inline=True
        )
        
        embed.add_field(
            name="Status",
            value="✅ Triggered" if self.triggered else "⏳ Waiting",
            inline=True
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Zubic(bot))
    logger.info("Zubic cog loaded successfully")
