import discord
from discord.ext import commands
import asyncio
import random
from datetime import datetime

class WelcomeLIFE(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Multiple welcome messages for variety
        self.welcome_messages = [
            " {mention} has joined the LIFE Alliance. \nWelcome to the alliance. Please review our channels and follow server guidelines.",
            " {mention} is now part of LIFE Alliance. \nMembership confirmed. Familiarize yourself with our structure and rules.",
            " LIFE Alliance welcomes {mention}. \nYour access has been granted. Check out our channels and stay informed.",
            " {mention} - LIFE Alliance membership active. \nWelcome aboard. Review our channels and participate accordingly.",
            " {mention} has entered the LIFE Alliance. \nGreat to have you here. Explore our community and get involved!"
        ]
        
        # Member milestones
        self.milestones = [10, 25, 50, 100, 250, 500, 1000, 2500, 5000]

    def is_milestone(self, member_count):
        """Check if member count is a milestone"""
        return member_count in self.milestones

    def get_member_rank(self, member_count):
        """Get a fun rank based on member count"""
        if member_count < 10:
            return "Seedling"
        elif member_count < 50:
            return "Sprout"
        elif member_count < 100:
            return "Growing Strong"
        elif member_count < 250:
            return "Established"
        elif member_count < 500:
            return "Thriving"
        elif member_count < 1000:
            return "Legendary"
        else:
            return "Epic Alliance"

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Check if the member joined the LIFE alliance server
        if member.guild.id == 1213699457233985587:  # LIFE alliance server ID
            try:
                # Send public welcome message
                welcome_channel = member.guild.get_channel(1213699457695092807)  # Welcoming channel ID
                if welcome_channel:
                    # Select a random welcome message
                    welcome_text = random.choice(self.welcome_messages).format(mention=member.mention)
                    
                    # Determine if this is a milestone
                    member_count = member.guild.member_count
                    is_milestone = self.is_milestone(member_count)
                    
                    # Create embed with enhanced styling
                    embed_color = discord.Color.gold() if is_milestone else discord.Color.from_rgb(0, 255, 127)
                    
                    embed = discord.Embed(
                        title="LIFE Alliance - New Member!" if not is_milestone else f"MILESTONE! Member #{member_count}",
                        description=welcome_text,
                        color=embed_color,
                        timestamp=datetime.utcnow()
                    )
                    
                    # Set the banner image
                    embed.set_image(url='https://github.com/Momonga-OP/spectra/blob/main/lifebanner.png?raw=true')
                    
                    # Add member info
                    account_age = (datetime.utcnow() - member.created_at).days
                    embed.add_field(
                        name="Member Info",
                        value=f"**Account Created:** {member.created_at.strftime('%B %d, %Y')}\n**Account Age:** {account_age} days\n**Member #{member_count}**",
                        inline=True
                    )
                    
                    # Add server info with channel tags
                    embed.add_field(
                        name="Quick Start",
                        value=f"• Read the rules in <#1358247995606569061>\n• Set your name in <#1358250304306544740>\n• Check <#1213971902775689336> for updates\n• Join conversations!\n• Explore our channels",
                        inline=True
                    )
                    
                    # Add alliance status
                    rank = self.get_member_rank(member_count)
                    embed.add_field(
                        name="Alliance Status",
                        value=f"**Rank:** {rank}\n**Total Members:** {member_count}",
                        inline=True
                    )
                    
                    # Add milestone celebration
                    if is_milestone:
                        embed.add_field(
                            name="Milestone Celebration!",
                            value=f"Congratulations! We've reached **{member_count}** members!\nThanks to everyone who made this possible!",
                            inline=False
                        )
                    
                    # Set footer
                    embed.set_footer(
                        text=f"LIFE Alliance • {member.guild.name}",
                        icon_url=member.guild.icon.url if member.guild.icon else None
                    )
                    
                    # Set thumbnail to member's avatar
                    embed.set_thumbnail(url=member.display_avatar.url)
                    
                    # Send the message with embed
                    await welcome_channel.send(embed=embed)
                    
                    print(f"Welcome message sent for {member.name} ({member.id})")
                    
                else:
                    print("Welcome channel not found or inaccessible.")

                # Send enhanced private welcome message
                dm_embed = discord.Embed(
                    title="Welcome to LIFE Alliance!",
                    description=(
                        f"Hello {member.name}!\n\n"
                        "You have joined the **LIFE Alliance** - where we grow stronger together! "
                        "This server contains various channels for alliance coordination and communication.\n\n"
                        "**Getting Started:**\n"
                        f"• Review the available channels\n"
                        f"• Read the rules in <#1358247995606569061>\n"
                        f"• Set your in-game name in <#1358250304306544740>\n"
                        f"• Check <#1213971902775689336> for announcements\n"
                        f"• Participate in alliance activities\n"
                        f"• Introduce yourself to the community\n\n"
                        f"**Your Stats:**\n"
                        f"• Member #{member_count}\n"
                        f"• Account Age: {(datetime.utcnow() - member.created_at).days} days\n"
                        f"• Alliance Rank: {self.get_member_rank(member_count)}\n\n"
                        "Your membership is now **active**! We're excited to have you here!"
                    ),
                    color=discord.Color.from_rgb(0, 255, 127),
                    timestamp=datetime.utcnow()
                )
                
                dm_embed.set_thumbnail(url=member.guild.icon.url if member.guild.icon else None)
                dm_embed.set_footer(text="LIFE Alliance • Living In Full Excellence!")
                
                await member.send(embed=dm_embed)
                print(f"DM welcome message sent to {member.name}")
                
            except discord.Forbidden:
                print(f"Could not send DM to {member.name} - DMs disabled")
            except Exception as e:
                print(f"Error in on_member_join: {e}")

    @commands.command(name="testwelcome")
    @commands.has_permissions(administrator=True)
    async def test_welcome(self, ctx):
        """Test the welcome message (Admin only)"""
        await self.on_member_join(ctx.author)
        await ctx.send("Welcome message test sent!")

    @commands.command(name="nextmilestone")
    async def next_milestone(self, ctx):
        """Show the next member milestone"""
        current_count = ctx.guild.member_count
        next_milestone = None
        
        for milestone in self.milestones:
            if milestone > current_count:
                next_milestone = milestone
                break
        
        if next_milestone:
            remaining = next_milestone - current_count
            embed = discord.Embed(
                title="Next Milestone",
                description=f"**Current Members:** {current_count}\n**Next Milestone:** {next_milestone}\n**Members Needed:** {remaining}",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                title="Maximum Milestone Reached!",
                description=f"Congratulations! You've surpassed all milestones with {current_count} members!",
                color=discord.Color.gold()
            )
        
        await ctx.send(embed=embed)

    @commands.command(name="setwelcomechannel")
    @commands.has_permissions(administrator=True)
    async def set_welcome_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the welcome channel (Admin only)"""
        if channel is None:
            channel = ctx.channel
        
        await ctx.send(f"Welcome channel would be set to {channel.mention}\n*Note: Update the channel ID in the code manually.*")

async def setup(bot):
    await bot.add_cog(WelcomeLIFE(bot))
    print("WelcomeLIFE cog loaded successfully.")
