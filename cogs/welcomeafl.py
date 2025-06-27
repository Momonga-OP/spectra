import discord
from discord.ext import commands
import asyncio
import random
from datetime import datetime

class WelcomeAFL(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Multiple welcome messages for variety
        self.welcome_messages = [
            " {mention} has joined the AFL Alliance. \nWelcome to the alliance. Please review our channels and follow server guidelines.",
            " {mention} is now part of AFL Alliance. \nMembership confirmed. Familiarize yourself with our structure and rules.",
            " AFL Alliance welcomes {mention}. \nYour access has been granted. Check out our channels and stay informed.",
            " {mention} - AFL Alliance membership active. \nWelcome aboard. Review our channels and participate accordingly."
        ]

    @commands.Cog.listener()
    async def on_member_join(self, member):
        # Check if the member joined the AFL alliance server
        if member.guild.id == 1213699457233985587:  # AFL alliance server ID
            try:
                # Send public welcome message
                welcome_channel = member.guild.get_channel(1213699457695092807)  # Welcoming channel ID
                if welcome_channel:
                    # Select a random welcome message
                    welcome_text = random.choice(self.welcome_messages).format(mention=member.mention)
                    
                    # Create embed with enhanced styling
                    embed = discord.Embed(
                        title="🏆 AFL Alliance - New Member! 🏆",
                        description=welcome_text,
                        color=discord.Color.gold(),  # Gold color for alliance theme
                        timestamp=datetime.utcnow()
                    )
                    
                    # Set the image from URL
                    embed.set_image(url='https://github.com/Momonga-OP/spectra/blob/main/AFLbanner.png?raw=true')
                    
                    # Add member info
                    embed.add_field(
                        name="📊 Member Info",
                        value=f"**Account Created:** {member.created_at.strftime('%B %d, %Y')}\n**Member #{member.guild.member_count}**",
                        inline=True
                    )
                    
                    # Add server info
                    embed.add_field(
                        name="🎯 Quick Start",
                        value="• Read the rules\n• Introduce yourself\n• Check announcements\n• Join conversations!",
                        inline=True
                    )
                    
                    # Set footer
                    embed.set_footer(
                        text=f"AFL Alliance • {member.guild.name}",
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
                    title=" Welcome to AFL Alliance! ",
                    description=(
                        f"Hello {member.name}.\n\n"
                        "You have joined the AFL Alliance. This server contains various channels "
                        "for alliance coordination and communication.\n\n"
                        "**Getting started:**\n"
                        "• Review the available channels\n"
                        "• Follow server rules and guidelines\n"
                        "• Participate in alliance activities\n"
                        "• Stay updated with announcements\n\n"
                        "Your membership is now active."
                    ),
                    color=discord.Color.blue(),
                    timestamp=datetime.utcnow()
                )
                
                dm_embed.set_thumbnail(url=member.guild.icon.url if member.guild.icon else None)
                dm_embed.set_footer(text="AFL Alliance • We're stronger together!")
                
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
        await ctx.send("✅ Welcome message test sent!")

async def setup(bot):
    await bot.add_cog(WelcomeAFL(bot))
    print("WelcomeAFL cog loaded successfully.")
