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
import re

logger = logging.getLogger(__name__)

# Constants for channel IDs
PANEL_CHANNEL_ID = 1359303967766741073
TICKET_CHANNEL_ID = 1359304110557364447
SERVER_ID = 1214430768143671377

# Kamas logo URL
KAMAS_LOGO_URL = "https://static.wikia.nocookie.net/dofus/images/1/1e/Kama.png"

# Currency symbols
CURRENCY_SYMBOLS = {
    "MAD": "DH",
    "EUR": "€",
    "USD": "$"
}

class ThreadManagementView(ui.View):
    """Provides buttons for thread management (close/delete)."""
    
    def __init__(self):
        super().__init__(timeout=None)  # No timeout for persistent view
        
    @discord.ui.button(label="Close Transaction", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_thread")
    async def close_thread_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to close the transaction thread."""
        try:
            # Check if user is admin, or is buyer/seller
            # Since this is inside the thread, we don't have direct access to buyer/seller IDs
            # So we allow only admins and the thread owner to close it
            if not (interaction.user.guild_permissions.administrator or 
                   interaction.channel.owner_id == interaction.user.id):
                await interaction.response.send_message(
                    "Only administrators or the thread creator can close this transaction.", 
                    ephemeral=True
                )
                return
            
            # Get the thread
            thread = interaction.channel
            if not isinstance(thread, discord.Thread):
                await interaction.response.send_message(
                    "This command can only be used in transaction threads.", 
                    ephemeral=True
                )
                return
            
            # Find and remove the thread file
            thread_file_paths = [f for f in os.listdir() if f.startswith("thread_") and f.endswith(".txt")]
            for file_path in thread_file_paths:
                try:
                    with open(file_path, "r") as f:
                        thread_id = int(f.read().strip())
                        if thread_id == thread.id:
                            os.remove(file_path)
                            logger.info(f"Removed thread file {file_path}")
                            break
                except:
                    pass
            
            await interaction.response.send_message("Closing this transaction thread. Thank you for using Wall Street!")
            
            # Add a small delay before archiving
            await asyncio.sleep(3)
            
            # Archive and lock the thread
            await thread.edit(archived=True, locked=True)
            logger.info(f"Thread {thread.id} has been closed and archived")
            
        except Exception as e:
            logger.exception(f"Error closing thread: {e}")
            await interaction.response.send_message(
                "There was an error closing the thread. Please try again or contact an administrator.",
                ephemeral=True
            )


class PrivateThreadButton(ui.View):
    """Button to create a private thread for transactions."""
    
    def __init__(self, seller_id, buyer_id=None, transaction_type=None):
        super().__init__(timeout=None)  # No timeout for persistent view
        self.seller_id = seller_id
        self.buyer_id = buyer_id
        self.transaction_type = transaction_type
        
        # Store thread_id as a class attribute instead of instance
        # This ensures it persists across bot restarts
        self.custom_id = f"private_thread_{seller_id}_{buyer_id if buyer_id else '0'}"
        self.create_thread_button.custom_id = self.custom_id
    
    @discord.ui.button(label="Start Private Discussion", style=discord.ButtonStyle.primary, emoji="🔒", custom_id="private_thread")
    async def create_thread_button(self, interaction: discord.Interaction, button: discord.ui.Button):
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
            
            # Check if thread already exists by looking for thread in channel attributes
            existing_thread_id = None
            thread_file_path = f"thread_{self.custom_id}.txt"
            
            if os.path.exists(thread_file_path):
                try:
                    with open(thread_file_path, "r") as f:
                        existing_thread_id = int(f.read().strip())
                        
                    # Try to fetch the thread
                    try:
                        thread = await interaction.guild.fetch_channel(existing_thread_id)
                        await interaction.response.send_message(
                            f"Thread already exists. [Click here to join](<https://discord.com/channels/{interaction.guild.id}/{existing_thread_id}>)",
                            ephemeral=True
                        )
                        return
                    except discord.NotFound:
                        # Thread was deleted, create a new one
                        existing_thread_id = None
                        os.remove(thread_file_path)
                except:
                    # Handle file read issues
                    existing_thread_id = None
            
            # Create a unique thread name
            unique_id = str(uuid.uuid4())[:8]
            thread_name = f"Transaction-{unique_id}"
            
            # Create a private thread from the message with proper permissions
            thread = await interaction.channel.create_thread(
                name=thread_name,
                message=interaction.message,
                type=discord.ChannelType.private_thread,
                auto_archive_duration=10080  # 7 days, maximum duration
            )
            
            # Store the thread ID in a file for persistence across restarts
            with open(thread_file_path, "w") as f:
                f.write(str(thread.id))
            
            # Add the seller and buyer to the thread
            try:
                seller = await interaction.client.fetch_user(self.seller_id)
                await thread.add_user(seller)
                
                if self.buyer_id:
                    buyer = await interaction.client.fetch_user(self.buyer_id)
                    await thread.add_user(buyer)
            except Exception as e:
                logger.error(f"Error adding users to thread: {e}")
            
            # Acknowledge the interaction
            await interaction.response.send_message(
                f"Private thread created! [Click here to join](<https://discord.com/channels/{interaction.guild.id}/{thread.id}>)",
                ephemeral=True
            )
            
            # Send initial message in thread with thread management buttons
            transaction_text = "listing" if not self.transaction_type else self.transaction_type.lower()
            
            # Create thread management view
            thread_management = ThreadManagementView()
            
            await thread.send(
                f"### Secure Transaction Thread\n\n"
                f"This is a private thread for discussing the kamas {transaction_text}.\n"
                f"Only the involved parties and administrators can see this thread.\n\n"
                f"**Guidelines:**\n"
                f"• Be respectful and clear in your communication\n"
                f"• Discuss and agree on the transaction details\n"
                f"• Once agreed, an administrator can help secure the transaction\n"
                f"• When finished, click the 'Close Transaction' button below\n\n"
                f"*Wall Street is facilitating this meeting but not directly involved in buying or selling. We just Pimpers.*",
                view=thread_management
            )
            
        except Exception as e:
            logger.exception(f"Error creating private thread: {e}")
            await interaction.response.send_message(
                "There was an error creating the private thread. Please try again later.",
                ephemeral=True
            )


class CurrencySelect(ui.Select):
    """Dropdown menu for selecting currency."""
    
    def __init__(self):
        options = [
            discord.SelectOption(label="Moroccan Dirham (DH)", value="MAD", emoji="💰"),
            discord.SelectOption(label="Euro (€)", value="EUR", emoji="💶"),
            discord.SelectOption(label="US Dollar ($)", value="USD", emoji="💵")
        ]
        super().__init__(placeholder="Select currency", min_values=1, max_values=1, options=options, custom_id="currency_select")


class KamasModal(ui.Modal, title="Kamas Transaction Details"):
    """Modal form that appears when a user clicks Buy or Sell."""
    
    amount = ui.TextInput(
        label="Amount of Kamas",
        placeholder="Enter the amount of kamas (e.g. 10M)",
        required=True,
        max_length=20
    )
    
    price_per_million = ui.TextInput(
        label="Price Per Million Kamas",
        placeholder="Enter price per million kamas (e.g. 5)",
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
        # We need to show a follow-up with currency selection
        # Store the form data temporarily
        try:
            # Process kamas amount to standardize format and calculate total
            kamas_amount_str = self.amount.value
            kamas_amount = parse_kamas_amount(kamas_amount_str)
            if kamas_amount is None:
                await interaction.response.send_message(
                    "Invalid kamas amount format. Please use formats like '10M', '500K', or '1000000'.",
                    ephemeral=True
                )
                return
                
            # Process price per million
            try:
                price_per_m = float(self.price_per_million.value.replace(',', '.'))
            except ValueError:
                await interaction.response.send_message(
                    "Invalid price format. Please enter a numeric value.",
                    ephemeral=True
                )
                return
                
            # Save form data in a temporary dictionary
            form_data = {
                "transaction_type": self.transaction_type,
                "kamas_amount": kamas_amount,
                "kamas_amount_str": format_kamas_amount(kamas_amount),
                "price_per_m": price_per_m,
                "payment_method": self.payment_method.value,
                "contact_info": self.contact_info.value,
                "additional_info": self.additional_info.value,
                "user_id": interaction.user.id
            }
            
            # Create a temporary file to store the form data
            temp_file_name = f"temp_form_{interaction.user.id}.txt"
            with open(temp_file_name, "w") as f:
                for key, value in form_data.items():
                    f.write(f"{key}:{value}\n")
            
            # Create currency selection view
            view = ui.View(timeout=300)  # 5 minute timeout
            currency_select = CurrencySelect()
            view.add_item(currency_select)
            
            # Add callback for the currency selection
            async def currency_callback(interaction: discord.Interaction):
                selected_currency = currency_select.values[0]
                await process_listing(interaction, selected_currency, temp_file_name)
                
            currency_select.callback = currency_callback
            
            # Show the currency selection
            await interaction.response.send_message(
                "Please select the currency for your transaction:", 
                view=view,
                ephemeral=True
            )
            
        except Exception as e:
            logger.exception(f"Error processing kamas form: {e}")
            await interaction.response.send_message(
                "There was an error processing your listing. Please try again later.",
                ephemeral=True
            )


async def process_listing(interaction: discord.Interaction, currency: str, temp_file_path: str):
    """Process the listing after currency selection."""
    try:
        # Load the form data from temporary file
        form_data = {}
        with open(temp_file_path, "r") as f:
            for line in f:
                key, value = line.strip().split(":", 1)
                form_data[key] = value
        
        # Clean up the temporary file
        os.remove(temp_file_path)
        
        # Get the ticket channel
        ticket_channel = interaction.client.get_channel(TICKET_CHANNEL_ID)
        if not ticket_channel:
            ticket_channel = await interaction.client.fetch_channel(TICKET_CHANNEL_ID)
        
        # Create timestamp for ticket reference
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        user_id = int(form_data["user_id"])
        transaction_type = form_data["transaction_type"]
        ticket_ref = f"{transaction_type}-{user_id}-{timestamp}"
        
        # Parse kamas amount and calculate total price
        kamas_amount = float(form_data["kamas_amount"])
        kamas_amount_str = form_data["kamas_amount_str"]
        price_per_m = float(form_data["price_per_m"])
        
        # Calculate total price based on kamas amount (in millions)
        total_price = (kamas_amount / 1000000) * price_per_m
        currency_symbol = CURRENCY_SYMBOLS[currency]
        
        # Format total price
        if currency == "MAD":
            formatted_total = f"{total_price:.2f} {currency_symbol}"
        else:
            formatted_total = f"{currency_symbol}{total_price:.2f}"
            
        # Format price per million
        if currency == "MAD":
            formatted_price_per_m = f"{price_per_m:.2f} {currency_symbol}"
        else:
            formatted_price_per_m = f"{currency_symbol}{price_per_m:.2f}"
        
        # Create an embed for the ticket
        embed = discord.Embed(
            title=f"Wall Street - Kamas {transaction_type}",
            description=f"A new kamas {transaction_type.lower()} listing has been created.",
            color=discord.Color.gold() if transaction_type == "SELL" else discord.Color.blue()
        )
        
        embed.add_field(name="Amount", value=kamas_amount_str, inline=True)
        embed.add_field(name="Price per Million", value=formatted_price_per_m, inline=True)
        embed.add_field(name="Total Price", value=formatted_total, inline=True)
        embed.add_field(name="Payment Method", value=form_data["payment_method"], inline=True)
        embed.add_field(name="Currency", value=f"{currency} ({currency_symbol})", inline=True)
        
        if form_data["additional_info"]:
            embed.add_field(name="Additional Information", value=form_data["additional_info"], inline=False)
            
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
        view = PrivateThreadButton(seller_id=user_id, transaction_type=transaction_type)
        
        # Send the ticket to the ticket channel
        message = await ticket_channel.send(embed=embed, view=view)
        
        # Store the message ID with its view ID for persistence
        with open(f"listing_{ticket_ref}.txt", "w") as f:
            f.write(str(message.id))
        
        # Confirm to the user
        await interaction.response.edit_message(
            content=f"Your {transaction_type.lower()} listing has been created! Check the transactions channel for inquiries.",
            view=None
        )
        
        logger.info(f"Created kamas {transaction_type.lower()} listing for user {user_id}")
        
    except Exception as e:
        logger.exception(f"Error creating kamas listing: {e}")
        await interaction.response.edit_message(
            content="There was an error creating your listing. Please try again later.",
            view=None
        )


def parse_kamas_amount(amount_str):
    """Parse kamas amount from string to a standardized number."""
    # Remove all spaces
    amount_str = amount_str.replace(" ", "").upper()
    
    # Check for "M" (millions)
    if "M" in amount_str:
        try:
            # Extract the number part before "M"
            num_part = amount_str.replace("M", "")
            num_part = num_part.replace(",", ".")
            return float(num_part) * 1000000
        except ValueError:
            return None
    
    # Check for "K" (thousands)
    elif "K" in amount_str:
        try:
            # Extract the number part before "K"
            num_part = amount_str.replace("K", "")
            num_part = num_part.replace(",", ".")
            return float(num_part) * 1000
        except ValueError:
            return None
    
    # Otherwise, try to parse as a regular number
    else:
        try:
            return float(amount_str.replace(",", "."))
        except ValueError:
            return None


def format_kamas_amount(amount_num):
    """Format kamas amount to a readable string."""
    if amount_num >= 1000000:
        if amount_num % 1000000 == 0:
            return f"{int(amount_num / 1000000)}M"
        else:
            return f"{amount_num / 1000000:.2f}M"
    elif amount_num >= 1000:
        if amount_num % 1000 == 0:
            return f"{int(amount_num / 1000)}K"
        else:
            return f"{amount_num / 1000:.2f}K"
    else:
        return str(int(amount_num) if amount_num.is_integer() else amount_num)


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
        # Load all active transaction views on startup
        self.bot.loop.create_task(self.setup_panel())
        self.bot.loop.create_task(self.restore_active_views())
    
    async def restore_active_views(self):
        """Restore all active views from previous sessions."""
        await self.bot.wait_until_ready()
        
        try:
            # Get the ticket channel
            ticket_channel = self.bot.get_channel(TICKET_CHANNEL_ID)
            if not ticket_channel:
                ticket_channel = await self.bot.fetch_channel(TICKET_CHANNEL_ID)
                
            # Find all listing files
            listing_files = [f for f in os.listdir() if f.startswith("listing_")]
            
            for file in listing_files:
                try:
                    with open(file, "r") as f:
                        message_id = int(f.read().strip())
                    
                    # Extract info from filename (format: listing_TYPE-USERID-TIMESTAMP.txt)
                    parts = file.replace("listing_", "").replace(".txt", "").split("-")
                    transaction_type = parts[0]
                    seller_id = int(parts[1])
                    
                    # Try to fetch the message
                    try:
                        message = await ticket_channel.fetch_message(message_id)
                        
                        # Check if there's a buyer ID in thread files
                        thread_files = [tf for tf in os.listdir() if tf.startswith(f"thread_private_thread_{seller_id}_")]
                        buyer_id = None
                        
                        if thread_files and not thread_files[0].endswith("_0.txt"):
                            buyer_part = thread_files[0].split("_")[-1].replace(".txt", "")
                            if buyer_part != "0":
                                buyer_id = int(buyer_part)
                        
                        # Recreate the view
                        view = PrivateThreadButton(seller_id=seller_id, buyer_id=buyer_id, transaction_type=transaction_type)
                        await message.edit(view=view)
                        
                        logger.info(f"Restored view for listing {file}")
                    except discord.NotFound:
                        # Message was deleted, clean up the file
                        os.remove(file)
                        logger.info(f"Removed stale listing file {file}")
                    except Exception as e:
                        logger.error(f"Error restoring view for {file}: {e}")
                        
                except Exception as e:
                    logger.error(f"Error processing listing file {file}: {e}")
                    
            # Also restore active threads with their management buttons
            thread_files = [f for f in os.listdir() if f.startswith("thread_private_thread_")]
            for file in thread_files:
                try:
                    with open(file, "r") as f:
                        thread_id = int(f.read().strip())
                    
                    # Try to fetch the thread and add management view if needed
                    try:
                        thread = await self.bot.fetch_channel(thread_id)
                        
                        # Check the last 10 messages to see if we need to add a management view
                        messages = [msg async for msg in thread.history(limit=10)]
                        has_management_view = False
                        
                        for msg in messages:
                            if msg.author.id == self.bot.user.id and "Secure Transaction Thread" in msg.content and msg.components:
                                has_management_view = True
                                break
                        
                        if not has_management_view:
                            # Need to add a management view
                            await thread.send(
                                "**Transaction Thread Management**\n\n"
                                "Use the button below to close this thread when your transaction is complete:",
                                view=ThreadManagementView()
                            )
                    except discord.NotFound:
                        # Thread was deleted, clean up the file
                        os.remove(file)
                    except Exception as e:
                        logger.error(f"Error restoring thread management for {file}: {e}")
                
                except Exception as e:
                    logger.error(f"Error processing thread file {file}: {e}")
            
            logger.info("Completed restoration of active views and threads")
            
        except Exception as e:
            logger.exception(f"Error in restore_active_views: {e}")
    
    async def setup_panel(self):
        """Set up the kamas trading panel on bot startup."""
        await self.bot.wait_until_ready()
        
        try:
            # Get the panel channel
            panel_channel = self.bot.get_channel(PANEL_CHANNEL_ID)
            if not panel_channel:
                panel_channel = await self.bot.fetch_channel(PANEL_CHANNEL_ID)
            
            # IMPORTANT: Check if we already have a panel message stored in a file
            panel_message_id = None
            panel_file_path = "kamas_panel_id.txt"
            if os.path.exists(panel_file_path):
                with open(panel_file_path, "r") as f:
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
                    "• Your price per million kamas\n"
                    "• Select your currency (DH, €, or $)\n"
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
                    "2. Select your preferred currency\n"
                    "3. A listing will be created in our transactions channel\n"
                    "4. Interested parties can use the private discussion button\n"
                    "5. Complete your transaction safely through our secure system\n"
                    "6. Close the thread when your transaction is complete"
                ),
                inline=False
            )
            
            embed.set_footer(text="Wall Street - Making transactions secure since Today we are just Testing this Idea")
            
            # Update existing message or create new one
            view = KamasView()
            
            if existing_message:
                # Only update the existing message with new view for button persistence
                await existing_message.edit(embed=embed, view=view)
                self.panel_message = existing_message
                logger.info(f"Updated existing kamas panel message: {existing_message.id}")
            else:
                # Create new panel only if no existing one was found
                self.panel_message = await panel_channel.send(embed=embed, view=view)
                
                # Save the message ID for future reference
                with open(panel_file_path, "w") as f:
                    f.write(str(self.panel_message.id))
                
                logger.info(f"Created new kamas panel message: {self.panel_message.id}")
                
        except Exception as e:
            logger.exception(f"Error setting up kamas panel: {e}")
    
    @app_commands.command(name="wallstreet_reset", description="Reset the Wall Street kamas trading panel")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_panel(self, interaction: discord.Interaction):
        """Admin command to reset the kamas trading panel."""
        try:
            panel_file_path = "kamas_panel_id.txt"
            if os.path.exists(panel_file_path):
                os.remove(panel_file_path)
            
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
            transaction_type = None
            ref_value = None
            
            if message.embeds and message.embeds[0].fields:
                # Get transaction type from title
                if message.embeds[0].title:
                    title_parts = message.embeds[0].title.split(' - Kamas ')
                    if len(title_parts) > 1:
                        transaction_type = title_parts[1]
                
                # Get seller ID from reference field
                for field in message.embeds[0].fields:
                    if field.name == "Reference ID":
                        ref_value = field.value.strip('`')
                        # Format is usually TRANSACTION_TYPE-USER_ID-TIMESTAMP
                        try:
                            ref_parts = ref_value.split('-')
                            if len(ref_parts) >= 2:
                                seller_id = int(ref_parts[1])
                        except:
                            pass
            
            if not seller_id:
                await interaction.response.send_message("Could not identify the seller from this listing.", ephemeral=True)
                return
            
            # Create a new view with both seller and buyer IDs
            new_view = PrivateThreadButton(seller_id=seller_id, buyer_id=user.id, transaction_type=transaction_type)
            
            # Update the message with the new view
            await message.edit(view=new_view)
            
            # Update file to include buyer info if ref_value is available
            if ref_value:
                # Ensure old thread file is removed if it exists
                old_thread_path = f"thread_private_thread_{seller_id}_0.txt"
                if os.path.exists(old_thread_path):
                    os.remove(old_thread_path)
            
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
    # Add persistent views support
    bot.add_view(KamasView())  # Add the main panel view for persistence
    
    # Register the cog
    await bot.add_cog(KamasCog(bot), guilds=[discord.Object(id=SERVER_ID)])
    logger.info("Wall Street kamas trading module has been loaded")
