import discord
from discord.ext import commands
from discord import ui, app_commands
import asyncio
import logging
from datetime import datetime
import os
import uuid
import aiohttp
from io import BytesIO

logger = logging.getLogger(__name__)

# Constants for channel IDs
PANEL_CHANNEL_ID = 1359303967766741073
TICKET_CHANNEL_ID = 1359304110557364447
SERVER_ID = 1214430768143671377

# Kamas logo URL
KAMAS_LOGO_URL = "https://static.wikia.nocookie.net/dofus/images/1/1e/Kama.png"

class PrivateThreadButton(ui.View):
    """Button to create a private thread for transactions."""
    
    def __init__(self, seller_id, buyer_id=None, transaction_type=None):
        super().__init__(timeout=None)
        self.seller_id = seller_id
        self.buyer_id = buyer_id
        self.transaction_type = transaction_type
        self.thread_id = None
    
    @discord.ui.button(label="Start Private Discussion", style=discord.ButtonStyle.primary, emoji="🔒", custom_id="private_thread")
    async def create_thread(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Only allow the admin, seller or buyer to create/access the thread
            if not (interaction.user.guild_permissions.administrator or 
                   interaction.user.id == self.seller_id or 
                   (self.buyer_id and interaction.user.id == self.buyer_id)):
                await interaction.response.send_message(
                    "You don't have permission to access this transaction thread.", 
                    ephemeral=True
                )
                return
            
            # If thread already exists, direct to it
            if self.thread_id:
                try:
                    thread = await interaction.guild.fetch_channel(self.thread_id)
                    await interaction.response.send_message(
                        f"Thread already exists. [Click here to join](<https://discord.com/channels/{interaction.guild.id}/{self.thread_id}>)",
                        ephemeral=True
                    )
                    return
                except discord.NotFound:
                    # Thread was deleted, create a new one
                    self.thread_id = None
            
            # Create a unique thread name
            unique_id = str(uuid.uuid4())[:8]
            thread_name = f"Transaction-{unique_id}"
            
            # Create a private thread from the message
            thread = await interaction.channel.create_thread(
                name=thread_name,
                message=interaction.message,
                type=discord.ChannelType.private_thread
            )
            
            # Store the thread ID
            self.thread_id = thread.id
            
            # Add the seller and buyer to the thread
            seller = await interaction.client.fetch_user(self.seller_id)
            await thread.add_user(seller)
            
            if self.buyer_id:
                buyer = await interaction.client.fetch_user(self.buyer_id)
                await thread.add_user(buyer)
            
            # Acknowledge the interaction
            await interaction.response.send_message(
                f"Private thread created! [Click here to join](<https://discord.com/channels/{interaction.guild.id}/{thread.id}>)",
                ephemeral=True
            )
            
            # Send initial message in thread
            transaction_text = "listing" if not self.transaction_type else self.transaction_type.lower()
            await thread.send(
                f"### Secure Transaction Thread\n\n"
                f"This is a private thread for discussing the kamas {transaction_text}.\n"
                f"Only the involved parties and administrators can see this thread.\n\n"
                f"**Guidelines:**\n"
                f"• Be respectful and clear in your communication\n"
                f"• Discuss and agree on the transaction details\n"
                f"• Once agreed, an administrator can help secure the transaction\n\n"
                f"*Wall Street is facilitating this meeting but not directly involved in buying or selling We just Pimpers .*"
            )
            
        except Exception as e:
            logger.exception(f"Error creating private thread: {e}")
            await interaction.response.send_message(
                "There was an error creating the private thread. Please try again later.",
                ephemeral=True
            )


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
    
    contact_info = ui.TextInput(
        label="Contact Information",
        placeholder="Discord tag or preferred contact method",
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
                title=f"Wall Street - Kamas {self.transaction_type}",
                description=f"A new kamas {self.transaction_type.lower()} listing has been created.",
                color=discord.Color.gold() if self.transaction_type == "SELL" else discord.Color.blue()
            )
            
            embed.add_field(name="Amount", value=self.amount.value, inline=True)
            embed.add_field(name="Price", value=self.price.value, inline=True)
            embed.add_field(name="Payment Method", value=self.payment_method.value, inline=True)
            
            if self.additional_info.value:
                embed.add_field(name="Additional Information", value=self.additional_info.value, inline=False)
                
            embed.add_field(name="Reference ID", value=f"`{ticket_ref}`", inline=False)
            embed.set_footer(text=f"Listed on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Try to download and use the Kamas logo as the thumbnail
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(KAMAS_LOGO_URL) as resp:
                        if resp.status == 200:
                            data = await resp.read()
                            embed.set_thumbnail(url=KAMAS_LOGO_URL)
            except Exception as e:
                logger.warning(f"Could not set Kamas logo: {e}")
            
            # Create the view with the private discussion button
            view = PrivateThreadButton(seller_id=user_id, transaction_type=self.transaction_type)
            
            # Send the ticket to the ticket channel
            await ticket_channel.send(embed=embed, view=view)
            
            # Confirm to the user
            await interaction.response.send_message(
                f"Your {self.transaction_type.lower()} listing has been created! Check the transactions channel for inquiries.",
                ephemeral=True
            )
            
            logger.info(f"Created kamas {self.transaction_type.lower()} listing for user {interaction.user.id}")
            
        except Exception as e:
            logger.exception(f"Error creating kamas listing: {e}")
            await interaction.response.send_message(
                "There was an error creating your listing. Please try again later.",
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
            
            # Download the Kamas logo for embedding
            kamas_logo = None
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(KAMAS_LOGO_URL) as resp:
                        if resp.status == 200:
                            kamas_logo = KAMAS_LOGO_URL
            except Exception as e:
                logger.warning(f"Failed to get Kamas logo: {e}")
            
            # Create embed for the panel
            embed = discord.Embed(
                title=" Wall Street - Kamas Trading ",
                description=(
                    "**Secure & Reliable Kamas Trading Platform**\n\n"
                    "Looking to buy or sell kamas safely? Wall Street facilitates secure meetings "
                    "between buyers and sellers.\n\n"
                    "Sparta is not supporting this action but it's done anyway so we are just securing it "
                    "- it's like giving a clean needle to junkies.\n\n"
                    "**Please provide the following information:**\n"
                    "• Amount of kamas you're buying/selling\n"
                    "• Your price\n"
                    "• Your preferred payment method\n"
                    "• Contact information"
                ),
                color=discord.Color.gold()
            )
            
            # Set the Kamas logo as thumbnail if available
            if kamas_logo:
                embed.set_thumbnail(url=kamas_logo)
            
            embed.add_field(name="📈 Attractive Rates & Safe Transactions", value="\u200b", inline=False)
            embed.add_field(name="🔒 Secure & Private Communications", value="\u200b", inline=False)
            embed.add_field(name="👥 Trusted Intermediary Service", value="\u200b", inline=False)
            
            embed.add_field(
                name="How It Works",
                value=(
                    "1. Click one of the buttons below and fill out the form\n"
                    "2. A listing will be created in our transactions channel\n"
                    "3. Interested parties can use the private discussion button\n"
                    "4. Complete your transaction safely through our secure system (Maybe)"
                ),
                inline=False
            )
            
            embed.set_footer(text="Wall Street - Making transactions secure since Today we are just Testing this Idea")
            
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
    
    @app_commands.command(name="wallstreet_reset", description="Reset the Wall Street kamas trading panel")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_panel(self, interaction: discord.Interaction):
        """Admin command to reset the kamas trading panel."""
        try:
            if os.path.exists("kamas_panel_id.txt"):
                os.remove("kamas_panel_id.txt")
            
            await self.setup_panel()
            await interaction.response.send_message("Wall Street trading panel has been reset!", ephemeral=True)
        except Exception as e:
            logger.exception(f"Error resetting Wall Street panel: {e}")
            await interaction.response.send_message("Failed to reset the Wall Street panel.", ephemeral=True)
    
    @app_commands.command(name="wallstreet_connect", description="Connect a buyer to a seller's listing")
    @app_commands.checks.has_permissions(administrator=True)
    async def connect_users(self, interaction: discord.Interaction, listing_message_id: str, user: discord.Member):
        """Admin command to connect a buyer to a seller's listing."""
        try:
            # Get the message from the ticket channel
            ticket_channel = interaction.client.get_channel(TICKET_CHANNEL_ID)
            if not ticket_channel:
                ticket_channel = await interaction.client.fetch_channel(TICKET_CHANNEL_ID)
            
            message = await ticket_channel.fetch_message(int(listing_message_id))
            
            # Check if the message has a PrivateThreadButton view
            if not message.components:
                await interaction.response.send_message("This message doesn't have a transaction button.", ephemeral=True)
                return
            
            # Extract the seller ID from the Reference ID field in the embed
            seller_id = None
            if message.embeds and message.embeds[0].fields:
                for field in message.embeds[0].fields:
                    if field.name == "Reference ID":
                        # Format is usually TRANSACTION_TYPE-USER_ID-TIMESTAMP
                        try:
                            ref_parts = field.value.strip('`').split('-')
                            if len(ref_parts) >= 2:
                                seller_id = int(ref_parts[1])
                        except:
                            pass
            
            if not seller_id:
                await interaction.response.send_message("Could not identify the seller from this listing.", ephemeral=True)
                return
            
            # Create a new view with both seller and buyer IDs
            new_view = PrivateThreadButton(seller_id=seller_id, buyer_id=user.id, 
                                          transaction_type=message.embeds[0].title.split(' - Kamas ')[1] if message.embeds else None)
            
            # Update the message with the new view
            await message.edit(view=new_view)
            
            await interaction.response.send_message(
                f"Connected {user.mention} to the listing. They can now access the private thread.",
                ephemeral=True
            )
            
        except discord.NotFound:
            await interaction.response.send_message("Message not found. Check the ID and try again.", ephemeral=True)
        except Exception as e:
            logger.exception(f"Error connecting users: {e}")
            await interaction.response.send_message("There was an error connecting the users.", ephemeral=True)


async def setup(bot):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(KamasCog(bot), guilds=[discord.Object(id=SERVER_ID)])
    logger.info("Wall Street kamas trading module has been loaded")
