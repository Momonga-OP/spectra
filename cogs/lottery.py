import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import random
import time
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class LotteryCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_lottery = None
        self.participants = set()
        self.lottery_message = None
        self.draw_time = None
        self.prize_amount = "1 MK"
        
    @app_commands.command(name="lottery", description="Start a weekly lottery event")
    @app_commands.describe(prize="Prize amount (default: 1 MK)")
    async def start_lottery(self, interaction: discord.Interaction, prize: str = "1 MK"):
        """Start a lottery event with announcement"""
        
        # Check if user has permission (you can modify this based on your roles)
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You don't have permission to start a lottery.", ephemeral=True)
            return
            
        # Check if lottery is already active
        if self.active_lottery:
            await interaction.response.send_message("A lottery is already active! Please wait for it to finish.", ephemeral=True)
            return
            
        # Set lottery details
        self.prize_amount = prize
        self.participants = set()
        self.draw_time = datetime.utcnow() + timedelta(hours=4)  # Changed from 1 hour to 4 hours
        self.active_lottery = True
        
        # Create announcement embed
        embed = discord.Embed(
            title="Weekly Lottery Drawing",
            description=f"Hello Life Alliance, are you feeling lucky today? Today is the weekly lottery day and all you need to do is react with the checkmark emoji below to participate. This is our Second week, so the prize is going to be Either 1 mk or 10 Mk depends on the winner and which guild is from.",
            color=0x00ff00
        )
        
        embed.add_field(
            name="How to Participate",
            value="Simply react to this message with ✅ to enter the lottery",
            inline=False
        )
        
        embed.add_field(
            name="Prize Pool",
            value=f"**{self.prize_amount}**",
            inline=True
        )
        
        embed.add_field(
            name="Drawing Time",
            value=f"<t:{int(self.draw_time.timestamp())}:R>",
            inline=True
        )
        
        embed.add_field(
            name="Status",
            value="🟢 Active - React to participate!",
            inline=True
        )
        
        embed.set_footer(text="Good luck to all participants!")
        embed.timestamp = datetime.utcnow()
        
        # Send announcement with @everyone ping
        await interaction.response.send_message("@everyone", embed=embed)
        message = await interaction.original_response()
        
        # Add reaction for participation
        await message.add_reaction("✅")
        
        # Store message reference
        self.lottery_message = message
        
        # Schedule the drawing
        asyncio.create_task(self.schedule_drawing())
        
    async def schedule_drawing(self):
        """Schedule the lottery drawing after 4 hours"""
        await asyncio.sleep(14400)  # Wait 4 hours (14400 seconds) - Changed from 3600
        await self.conduct_drawing()
        
    async def conduct_drawing(self):
        """Conduct the lottery drawing and announce winner"""
        if not self.participants:
            # No participants
            embed = discord.Embed(
                title="Lottery Drawing Results",
                description="Unfortunately, no one participated in this week's lottery. Better luck next time!",
                color=0xff0000
            )
            embed.timestamp = datetime.utcnow()
            
            # Send results as a new message instead of editing
            if self.lottery_message:
                try:
                    await self.lottery_message.channel.send(embed=embed)
                except Exception as e:
                    logger.error(f"Failed to send lottery results: {e}")
        else:
            # Pick random winner
            winner_id = random.choice(list(self.participants))
            winner = await self.bot.fetch_user(winner_id)
            
            # Create winner announcement
            embed = discord.Embed(
                title="Lottery Drawing Results",
                description=f"Congratulations to **{winner.display_name}**! You have won this week's lottery drawing.",
                color=0xffd700
            )
            
            embed.add_field(
                name="Winner",
                value=f"{winner.mention}",
                inline=True
            )
            
            embed.add_field(
                name="Prize Won",
                value=f"**{self.prize_amount}**",
                inline=True
            )
            
            embed.add_field(
                name="Total Participants",
                value=f"{len(self.participants)} members",
                inline=True
            )
            
            embed.add_field(
                name="Next Steps",
                value="A member of our leadership team will contact you soon to arrange your prize collection.",
                inline=False
            )
            
            embed.set_footer(text="Thank you to everyone who participated!")
            embed.timestamp = datetime.utcnow()
            
            # Send results as a new message instead of editing
            if self.lottery_message:
                try:
                    await self.lottery_message.channel.send(embed=embed)
                except Exception as e:
                    logger.error(f"Failed to send lottery results: {e}")
                
            # Send winner their voucher via DM
            await self.send_winner_voucher(winner)
            
        # Reset lottery state
        self.reset_lottery()
        
    async def send_winner_voucher(self, winner):
        """Send the winner their prize voucher"""
        voucher_embed = discord.Embed(
            title="Lottery Winner Voucher",
            description=f"Congratulations **{winner.display_name}**! You are the official winner of this week's lottery drawing.",
            color=0xffd700
        )
        
        voucher_embed.add_field(
            name="Winner Details",
            value=f"Name: {winner.display_name}\nUser ID: {winner.id}",
            inline=False
        )
        
        voucher_embed.add_field(
            name="Prize Amount",
            value=f"**{self.prize_amount}**",
            inline=True
        )
        
        voucher_embed.add_field(
            name="Voucher ID",
            value=f"LT-{int(time.time())}-{winner.id}",
            inline=True
        )
        
        voucher_embed.add_field(
            name="What's Next?",
            value="A member of our leadership team will contact you within 24 hours to arrange the collection of your prize. Please keep this voucher as proof of your win.",
            inline=False
        )
        
        voucher_embed.set_footer(text="Life Alliance Lottery System")
        voucher_embed.timestamp = datetime.utcnow()
        
        try:
            await winner.send(embed=voucher_embed)
        except discord.Forbidden:
            logger.warning(f"Could not send DM to winner {winner.id}")
            
    def reset_lottery(self):
        """Reset lottery state"""
        self.active_lottery = None
        self.participants = set()
        self.lottery_message = None
        self.lottery_channel = None
        self.draw_time = None
        
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle lottery participation via reactions"""
        if user.bot:
            return
            
        # Check if this is the lottery message and correct reaction
        if (self.lottery_message and 
            reaction.message.id == self.lottery_message.id and 
            str(reaction.emoji) == "✅" and
            self.active_lottery):
            
            # Add user to participants
            if user.id not in self.participants:
                self.participants.add(user.id)
                
                # Send participation ticket via DM
                await self.send_participation_ticket(user)
                
    async def send_participation_ticket(self, user):
        """Send participation confirmation ticket to user"""
        ticket_embed = discord.Embed(
            title="Lottery Participation Confirmed",
            description=f"Hello **{user.display_name}**! Your participation in this week's lottery has been confirmed. Good luck!",
            color=0x00ff00
        )
        
        ticket_embed.add_field(
            name="Participant Details",
            value=f"Name: {user.display_name}\nUser ID: {user.id}",
            inline=False
        )
        
        ticket_embed.add_field(
            name="Drawing Time",
            value=f"<t:{int(self.draw_time.timestamp())}:R>",
            inline=True
        )
        
        ticket_embed.add_field(
            name="Prize Pool",
            value=f"**{self.prize_amount}**",
            inline=True
        )
        
        ticket_embed.add_field(
            name="Ticket Number",
            value=f"#{len(self.participants):04d}",
            inline=True
        )
        
        ticket_embed.add_field(
            name="Status",
            value="Your entry is confirmed! The drawing will happen automatically at the scheduled time.",
            inline=False
        )
        
        ticket_embed.set_footer(text="Life Alliance Lottery System - Keep this ticket for your records")
        ticket_embed.timestamp = datetime.utcnow()
        
        try:
            await user.send(embed=ticket_embed)
        except discord.Forbidden:
            logger.warning(f"Could not send participation ticket to {user.id}")
            
    @commands.Cog.listener()
    async def on_reaction_remove(self, reaction, user):
        """Handle lottery participation removal"""
        if user.bot:
            return
            
        # Check if this is the lottery message and correct reaction
        if (self.lottery_message and 
            reaction.message.id == self.lottery_message.id and 
            str(reaction.emoji) == "✅" and
            self.active_lottery):
            
            # Remove user from participants
            if user.id in self.participants:
                self.participants.discard(user.id)
                
                # Send removal confirmation
                try:
                    await user.send(f"Hello **{user.display_name}**, you have been removed from the current lottery. You can react again if you want to participate.")
                except discord.Forbidden:
                    pass
                    
    @app_commands.command(name="lottery_status", description="Check current lottery status")
    async def lottery_status(self, interaction: discord.Interaction):
        """Check the current lottery status"""
        if not self.active_lottery:
            embed = discord.Embed(
                title="Lottery Status",
                description="There is currently no active lottery. Use `/lottery` to start one!",
                color=0xff0000
            )
        else:
            embed = discord.Embed(
                title="Current Lottery Status",
                description="A lottery is currently active!",
                color=0x00ff00
            )
            
            embed.add_field(
                name="Participants",
                value=f"{len(self.participants)} members",
                inline=True
            )
            
            embed.add_field(
                name="Prize Pool",
                value=f"**{self.prize_amount}**",
                inline=True
            )
            
            embed.add_field(
                name="Drawing Time",
                value=f"<t:{int(self.draw_time.timestamp())}:R>",
                inline=True
            )
            
        embed.timestamp = datetime.utcnow()
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    @app_commands.command(name="end_lottery", description="Manually end the current lottery (Admin only)")
    async def end_lottery(self, interaction: discord.Interaction):
        """Manually end the current lottery"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You don't have permission to end the lottery.", ephemeral=True)
            return
            
        if not self.active_lottery:
            await interaction.response.send_message("No active lottery to end.", ephemeral=True)
            return
            
        await interaction.response.send_message("Ending lottery and conducting drawing...", ephemeral=True)
        await self.conduct_drawing()

async def setup(bot):
    await bot.add_cog(LotteryCog(bot))
