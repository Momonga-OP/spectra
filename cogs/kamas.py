import discord
from discord.ext import commands
from discord import ui, app_commands
import asyncio
import logging
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# Constants for channel IDs
PANEL_CHANNEL_ID = 1237390434041462836
TICKET_CHANNEL_ID = 1247728738326679583
SERVER_ID = 1217700740949348443

class KamasModal(ui.Modal, title="Kamas Transaction Details"):
    """Modal form that appears when a user clicks Buy or Sell."""
    
    amount = ui.TextInput(
        label="Amount of Kamas",
        placeholder="Enter the amount of kamas (e.g. 10M)",
        required=True,
        max_length=20
    )
    
    price = ui.TextInput(
        label="Price",
        placeholder="Enter your price (e.g. €50)",
        required=True,
        max_length=20
    )
    
    payment_method = ui.TextInput(
        label="Payment Method",
        placeholder="Enter your preferred payment method",
        required=True,
        max_length=100
    )
    
    additional_info = ui.TextInput(
        label="Additional Information",
        placeholder="Any other details you want to share",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=500
    )
    
    def __init__(self, transaction_type):
        super().__init__()
        self.transaction_type = transaction_type  # "BUY" or "SELL"
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Get the ticket channel
            ticket_channel = interaction.client.get_channel(TICKET_CHANNEL_ID)
            if not ticket_channel:
                ticket_channel = await interaction.client.fetch_channel(TICKET_CHANNEL_ID)
            
            # Create timestamp for ticket reference
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            user_id = interaction.user.id
            ticket_ref = f"{self.transaction_type}-{user_id}-{timestamp}"
            
            # Create an embed for the ticket
            embed = discord.Embed(
                title=f"Kamas {self.transaction_type} Request - {interaction.user.name}",
                description=f"Transaction type: **{self.transaction_type}**",
                color=discord.Color.gold() if self.transaction_type == "SELL" else discord.Color.blue()
            )
            
            embed.add_field(name="Amount", value=self.amount.value, inline=True)
            embed.add_field(name="Price", value=self.price.value, inline=True)
            embed.add_field(name="Payment Method", value=self.payment_method.value, inline=True)
            
            if self.additional_info.value:
                embed.add_field(name="Additional Information", value=self.additional_info.value, inline=False)
                
            embed.add_field(name="Reference", value=f"`{ticket_ref}`", inline=False)
            embed.add_field(name="User ID", value=f"{interaction.user.id}", inline=False)
            embed.set_footer(text=f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Send the ticket to the ticket channel
            await ticket_channel.send(
                content=f"New kamas {self.transaction_type.lower()} request from {interaction.user.mention}",
                embed=embed
            )
            
            # Confirm to the user
            await interaction.response.send_message(
                f"Your {self.transaction_type.lower()} request has been submitted! A representative will contact you soon.",
                ephemeral=True
            )
            
            logger.info(f"Created kamas {self.transaction_type.lower()} ticket for user {interaction.user.id}")
            
        except Exception as e:
            logger.exception(f"Error creating kamas ticket: {e}")
            await interaction.response.send_message(
                "There was an error processing your request. Please try again later.",
                ephemeral=True
            )


class KamasView(ui.View):
    """View containing the Buy and Sell buttons."""
    
    def __init__(self):
        super().__init__(timeout=None)  # Set timeout to None for persistence
    
    @discord.ui.button(label="BUY KAMAS", style=discord.ButtonStyle.primary, custom_id="buy_kamas", emoji="💰")
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button for users who want to buy kamas."""
        await interaction.response.send_modal(KamasModal("BUY"))
    
    @discord.ui.button(label="SELL KAMAS", style=discord.ButtonStyle.success, custom_id="sell_kamas", emoji="💎")
    async def sell_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button for users who want to sell kamas."""
        await interaction.response.send_modal(KamasModal("SELL"))


class KamasCog(commands.Cog):
    """Cog for managing kamas buying and selling functionality."""
    
    def __init__(self, bot):
        self.bot = bot
        self.panel_message = None
        self.bot.loop.create_task(self.setup_panel())
    
    async def setup_panel(self):
        """Set up the kamas trading panel on bot startup."""
        await self.bot.wait_until_ready()
        
        try:
            # Get the panel channel
            panel_channel = self.bot.get_channel(PANEL_CHANNEL_ID)
            if not panel_channel:
                panel_channel = await self.bot.fetch_channel(PANEL_CHANNEL_ID)
            
            # Check if we already have a panel message stored in a file
            panel_message_id = None
            if os.path.exists("kamas_panel_id.txt"):
                with open("kamas_panel_id.txt", "r") as f:
                    try:
                        panel_message_id = int(f.read().strip())
                    except (ValueError, IOError):
                        logger.warning("Could not read panel message ID from file")
            
            # If we have a stored message ID, try to fetch the message
            existing_message = None
            if panel_message_id:
                try:
                    existing_message = await panel_channel.fetch_message(panel_message_id)
                    logger.info(f"Found existing kamas panel message: {panel_message_id}")
                except discord.NotFound:
                    logger.info("Stored kamas panel message not found, creating new one")
                except Exception as e:
                    logger.exception(f"Error fetching kamas panel message: {e}")
            
            # Create embed for the panel
            embed = discord.Embed(
                title="💎 Kamas Trading Service 💎",
                description=(
                    "**Secure & Fast Kamas Trading Service!**\n\n"
                    "Looking to buy or sell kamas safely and at the best price? "
                    "Our team of professionals is here to ensure a fast and reliable transaction.\n\n"
                    "Sparta is not supporting this action but it's done anyway so we are just securing it "
                    "- it's like giving a clean needle to junkies.\n\n"
                    "**Please provide the following information:**\n"
                    "• Amount of kamas you're buying/selling\n"
                    "• Your price\n"
                    "• Your preferred payment method"
                ),
                color=discord.Color.gold()
            )
            
            embed.add_field(name="📈 Attractive Rates & Immediate Payment", value="\u200b", inline=False)
            embed.add_field(name="🔒 Secure & Guaranteed Service", value="\u200b", inline=False)
            embed.add_field(name="👥 Certified Members at Your Service", value="\u200b", inline=False)
            
            embed.add_field(
                name="How It Works",
                value=(
                    "Click one of the buttons below and fill out the form. "
                    "One of our certified agents will assist you with your transaction shortly."
                ),
                inline=False
            )
            
            embed.set_footer(text="All transactions are secured and guaranteed by our server.")
            
            # Update existing message or create new one
            view = KamasView()
            if existing_message:
                await existing_message.edit(content=None, embed=embed, view=view)
                self.panel_message = existing_message
            else:
                self.panel_message = await panel_channel.send(embed=embed, view=view)
                
                # Save the message ID for future reference
                with open("kamas_panel_id.txt", "w") as f:
                    f.write(str(self.panel_message.id))
                
                logger.info(f"Created new kamas panel message: {self.panel_message.id}")
                
        except Exception as e:
            logger.exception(f"Error setting up kamas panel: {e}")
    
    @app_commands.command(name="kamas_reset_panel", description="Reset the kamas trading panel")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_panel(self, interaction: discord.Interaction):
        """Admin command to reset the kamas trading panel."""
        try:
            if os.path.exists("kamas_panel_id.txt"):
                os.remove("kamas_panel_id.txt")
            
            await self.setup_panel()
            await interaction.response.send_message("Kamas trading panel has been reset!", ephemeral=True)
        except Exception as e:
            logger.exception(f"Error resetting kamas panel: {e}")
            await interaction.response.send_message("Failed to reset the kamas panel.", ephemeral=True)


async def setup(bot):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(KamasCog(bot), guilds=[discord.Object(id=SERVER_ID)])
    logger.info("Kamas trading module has been loaded")
