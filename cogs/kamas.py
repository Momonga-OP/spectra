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
PANEL_CHANNEL_ID = 1258426636496404510
TICKET_CHANNEL_ID = 1358383554798817410
VERIFIED_DATA_CHANNEL_ID = 1248345019333611561
SERVER_ID = 1217700740949348443

# Kamas logo URL
KAMAS_LOGO_URL = "https://static.wikia.nocookie.net/dofus/images/1/1e/Kama.png"

# Currency symbols
CURRENCY_SYMBOLS = {
    "EUR": "€",
    "USD": "$"
}

# Verification data file
VERIFICATION_DATA_FILE = "verified_sellers.json"

async def get_verified_role(guild):
    """Get or create the verified seller role."""
    verified_role = discord.utils.get(guild.roles, name="Verified Seller")
    if not verified_role:
        # Create the role with permissions
        verified_role = await guild.create_role(
            name="Verified Seller",
            color=discord.Color.gold(),
            mentionable=True
        )
        # Add permissions if needed
        # Example: await verified_role.edit(permissions=discord.Permissions())
    return verified_role

async def store_verification_data(interaction, user_id, verification_data):
    """Store verification data in the verified sellers channel."""
    try:
        channel = interaction.client.get_channel(VERIFIED_DATA_CHANNEL_ID)
        if not channel:
            channel = await interaction.client.fetch_channel(VERIFIED_DATA_CHANNEL_ID)
            
        # Create a text file with verification info
        file_content = f"""Verified Seller Information:
User ID: {user_id}
Username: {verification_data['username']}
Social Platform: {verification_data['social_platform']}
Social Handle: {verification_data['social_handle']}
Trading Experience: {verification_data['trading_experience']}
Additional Info: {verification_data['additional_info']}
Application Date: {verification_data['application_date']}
Verified Date: {verification_data['verified_date']}
Verified By: {verification_data['verified_by']}"""
        
        # Create a file with a unique name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"verified_seller_{user_id}_{timestamp}.txt"
        
        # Send the file to the channel
        await channel.send(
            f"New verified seller: <@{user_id}>",
            file=discord.File(BytesIO(file_content.encode()), filename=filename)
        )
        
        # Add the verified seller role
        guild = interaction.guild
        verified_role = await get_verified_role(guild)
        member = await guild.fetch_member(int(user_id))
        if member:
            await member.add_roles(verified_role)
            
        return True
        
    except Exception as e:
        logger.exception(f"Error storing verification data: {e}")
        return False

def hash_sensitive_data(data):
    """Hash sensitive data for security."""
    return hashlib.sha256(data.encode()).hexdigest()

def is_verified_seller(user_id):
    """Check if a user is a verified seller."""
    verification_data = load_verification_data()
    return str(user_id) in verification_data and verification_data[str(user_id)].get('verified', False)

def get_seller_profile(user_id):
    """Get seller profile data."""
    verification_data = load_verification_data()
    return verification_data.get(str(user_id), {})

class ThreadManagementView(ui.View):
    """Provides buttons for thread management (close/delete)."""
    
    def __init__(self):
        super().__init__(timeout=None)  # No timeout for persistent view

class VerificationModal(ui.Modal, title="Seller Verification Application"):
    """Modal for seller verification submission."""
    
    phone_number = ui.TextInput(
        label="Phone Number",
        placeholder="Enter your phone number (e.g., +1234567890)",
        required=True,
        max_length=20
    )
    
    social_media_type = ui.TextInput(
        label="Social Media Platform",
        placeholder="Twitter, Instagram, or Facebook",
        required=True,
        max_length=20
    )
    
    social_media_handle = ui.TextInput(
        label="Social Media Handle/Username",
        placeholder="Your username/handle (without @)",
        required=True,
        max_length=100
    )
    
    trading_experience = ui.TextInput(
        label="Trading Experience",
        placeholder="How long have you been trading kamas?",
        required=True,
        max_length=200
    )
    
    additional_info = ui.TextInput(
        label="Additional Information",
        placeholder="Any additional info that helps verify your legitimacy",
        required=False,
        style=discord.TextStyle.paragraph,
        max_length=500
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Validate social media platform
            valid_platforms = ['twitter', 'instagram', 'facebook']
            platform = self.social_media_type.value.lower().strip()
            if platform not in valid_platforms:
                await interaction.response.send_message(
                    "Please enter a valid social media platform: Twitter, Instagram, or Facebook",
                    ephemeral=True
                )
                return
            
            # Create verification entry
            verification_data = load_verification_data()
            user_id = str(interaction.user.id)
            
            verification_entry = {
                'user_id': user_id,
                'username': interaction.user.display_name,
                'phone_hash': hash_sensitive_data(self.phone_number.value),
                'social_platform': platform.capitalize(),
                'social_handle': self.social_media_handle.value.strip(),
                'trading_experience': self.trading_experience.value,
                'additional_info': self.additional_info.value,
                'application_date': datetime.now().isoformat(),
                'verified': False,
                'verified_date': None,
                'verified_by': None
            }
            
            verification_data[user_id] = verification_entry
            save_verification_data(verification_data)
            
            # Create admin notification embed
            admin_embed = discord.Embed(
                title="🔍 New Seller Verification Application",
                description=f"**User:** {interaction.user.mention} ({interaction.user.display_name})",
                color=discord.Color.orange()
            )
            
            admin_embed.add_field(name="Social Media", value=f"{platform.capitalize()}: @{self.social_media_handle.value}", inline=True)
            admin_embed.add_field(name="Trading Experience", value=self.trading_experience.value, inline=False)
            
            if self.additional_info.value:
                admin_embed.add_field(name="Additional Info", value=self.additional_info.value, inline=False)
            
            admin_embed.add_field(name="Application ID", value=f"`{user_id}`", inline=False)
            admin_embed.set_footer(text=f"Applied on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Send to ticket channel for admin review
            ticket_channel = interaction.client.get_channel(TICKET_CHANNEL_ID)
            if not ticket_channel:
                ticket_channel = await interaction.client.fetch_channel(TICKET_CHANNEL_ID)
            
            admin_view = VerificationAdminView(user_id)
            await ticket_channel.send(embed=admin_embed, view=admin_view)
            
            await interaction.response.send_message(
                "✅ **Verification Application Submitted!**\n\n"
                "Your application has been submitted for review. Our administrators will verify your information and get back to you soon.\n\n"
                "**What happens next:**\n"
                "• Admins will review your social media profile\n"
                "• Your phone number is securely hashed and stored\n"
                "• You'll be notified once verified\n"
                "• Verified sellers get a special badge on their listings\n\n"
                "*Please allow 24-48 hours for processing.*",
                ephemeral=True
            )
            
            logger.info(f"Verification application submitted by user {user_id}")
            
        except Exception as e:
            logger.exception(f"Error processing verification application: {e}")
            await interaction.response.send_message(
                "There was an error processing your application. Please try again later.",
                ephemeral=True
            )
        
    @discord.ui.button(label="Close Transaction", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="close_thread")
    async def close_thread_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Button to close the transaction thread."""
        try:
            # Check if user is admin, or is buyer/seller
            if not (interaction.user.guild_permissions.administrator or 
                   interaction.channel.owner_id == interaction.user.id):
                await interaction.response.send_message(
                    "Only administrators or the thread creator can close this transaction.", 
                    ephemeral=True
                )
                return
            
            thread = interaction.channel
            if not isinstance(thread, discord.Thread):
                await interaction.response.send_message(
                    "This command can only be used in transaction threads.", 
                    ephemeral=True
                )
                return
            
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
            
            await interaction.response.send_message("Closing this transaction thread. Thank you for using AFL Wall Street!")
            
            await asyncio.sleep(3)
            
            await thread.edit(archived=True, locked=True)
            logger.info(f"Thread {thread.id} has been closed and archived")
            
        except Exception as e:
            logger.exception(f"Error closing thread: {e}")
            await interaction.response.send_message(
                "There was an error closing the thread. Please try again or contact an administrator.",
                ephemeral=True
            )

class VerificationAdminView(ui.View):
    """Admin view for approving/rejecting verification applications."""
    
    def __init__(self, applicant_user_id):
        super().__init__(timeout=None)
        self.applicant_user_id = applicant_user_id
        
    @discord.ui.button(label="Approve", style=discord.ButtonStyle.success, emoji="✅")
    async def approve_verification(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only administrators can approve verifications.", ephemeral=True)
            return
        
        try:
            verification_data = load_verification_data()
            if self.applicant_user_id in verification_data:
                # Update verification status
                verification_data[self.applicant_user_id]['verified'] = True
                verification_data[self.applicant_user_id]['verified_date'] = datetime.now().isoformat()
                verification_data[self.applicant_user_id]['verified_by'] = str(interaction.user.id)
                
                # Store data in Discord channel
                if await store_verification_data(interaction, self.applicant_user_id, verification_data[self.applicant_user_id]):
                    # Notify the applicant
                    try:
                        applicant = await interaction.client.fetch_user(int(self.applicant_user_id))
                        await applicant.send(
                            "🎉 **Congratulations! You're now a Verified Seller!**\n\n"
                            "Your seller verification has been approved. You now have access to:\n"
                            "• ✅ Verified badge on all your listings\n"
                            "• 🏆 Enhanced trust and credibility\n"
                            "• 📈 Higher visibility in the marketplace\n\n"
                            "Thank you for helping make AFL Wall Street a safer trading environment!"
                        )
                    except:
                        pass
                    
                    # Update the embed
                    embed = interaction.message.embeds[0]
                    embed.color = discord.Color.green()
                    embed.title = "✅ Seller Verification APPROVED"
                    embed.add_field(name="Approved By", value=interaction.user.mention, inline=True)
                    embed.add_field(name="Approved On", value=datetime.now().strftime('%Y-%m-%d %H:%M:%S'), inline=True)
                    
                    await interaction.response.edit_message(embed=embed, view=None)
                else:
                    await interaction.response.send_message("Error storing verification data. Please try again.", ephemeral=True)
                    
            else:
                await interaction.response.send_message("Verification data not found.", ephemeral=True)
                
        except Exception as e:
            logger.exception(f"Error approving verification: {e}")
            await interaction.response.send_message("Error processing approval.", ephemeral=True)
    
    @discord.ui.button(label="Reject", style=discord.ButtonStyle.danger, emoji="❌")
    async def reject_verification(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Only administrators can reject verifications.", ephemeral=True)
            return
        
        await interaction.response.send_modal(RejectionReasonModal(self.applicant_user_id))

class RejectionReasonModal(ui.Modal, title="Rejection Reason"):
    """Modal for providing rejection reason."""
    
    reason = ui.TextInput(
        label="Reason for Rejection",
        placeholder="Please provide a reason for rejecting this application",
        required=True,
        style=discord.TextStyle.paragraph,
        max_length=500
    )
    
    def __init__(self, applicant_user_id):
        super().__init__()
        self.applicant_user_id = applicant_user_id
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            verification_data = load_verification_data()
            if self.applicant_user_id in verification_data:
                del verification_data[self.applicant_user_id]
                save_verification_data(verification_data)
                
                # Notify the applicant
                try:
                    applicant = await interaction.client.fetch_user(int(self.applicant_user_id))
                    await applicant.send(
                        "❌ **Seller Verification Application Rejected**\n\n"
                        f"**Reason:** {self.reason.value}\n\n"
                        "You can reapply for verification once you've addressed the concerns mentioned above.\n"
                        "If you have questions, please contact an administrator."
                    )
                except:
                    pass
                
                # Update the embed
                embed = interaction.message.embeds[0]
                embed.color = discord.Color.red()
                embed.title = "❌ Seller Verification REJECTED"
                embed.add_field(name="Rejected By", value=interaction.user.mention, inline=True)
                embed.add_field(name="Rejection Reason", value=self.reason.value, inline=False)
                
                await interaction.response.edit_message(embed=embed, view=None)
                
            else:
                await interaction.response.send_message("Verification data not found.", ephemeral=True)
                
        except Exception as e:
            logger.exception(f"Error rejecting verification: {e}")
            await interaction.response.send_message("Error processing rejection.", ephemeral=True)

class PrivateThreadButton(ui.View):
    """Button to create a private thread for transactions."""
    
    def __init__(self, seller_id, buyer_id=None, transaction_type=None):
        super().__init__(timeout=None)
        self.seller_id = seller_id
        self.buyer_id = buyer_id
        self.transaction_type = transaction_type
        self.custom_id = f"private_thread_{seller_id}_{buyer_id if buyer_id else '0'}"
        self.create_thread_button.custom_id = self.custom_id
    
    @discord.ui.button(label="Start Private Discussion", style=discord.ButtonStyle.primary, emoji="🔒", custom_id="private_thread")
    async def create_thread_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if not (interaction.user.guild_permissions.administrator or 
                   interaction.user.id == self.seller_id or 
                   (self.buyer_id and interaction.user.id == self.buyer_id)):
                await interaction.response.send_message(
                    "You don't have permission to access this transaction thread.", 
                    ephemeral=True
                )
                return
            
            existing_thread_id = None
            thread_file_path = f"thread_{self.custom_id}.txt"
            
            if os.path.exists(thread_file_path):
                try:
                    with open(thread_file_path, "r") as f:
                        existing_thread_id = int(f.read().strip())
                    try:
                        thread = await interaction.guild.fetch_channel(existing_thread_id)
                        await interaction.response.send_message(
                            f"Thread already exists. [Click here to join](<https://discord.com/channels/{interaction.guild.id}/{existing_thread_id}>)",
                            ephemeral=True
                        )
                        return
                    except discord.NotFound:
                        existing_thread_id = None
                        os.remove(thread_file_path)
                except:
                    existing_thread_id = None
            
            unique_id = str(uuid.uuid4())[:8]
            thread_name = f"Transaction-{unique_id}"
            
            thread = await interaction.channel.create_thread(
                name=thread_name,
                message=interaction.message,
                type=discord.ChannelType.private_thread,
                auto_archive_duration=10080
            )
            
            with open(thread_file_path, "w") as f:
                f.write(str(thread.id))
            
            try:
                seller = await interaction.client.fetch_user(self.seller_id)
                await thread.add_user(seller)
                if self.buyer_id:
                    buyer = await interaction.client.fetch_user(self.buyer_id)
                    await thread.add_user(buyer)
            except Exception as e:
                logger.error(f"Error adding users to thread: {e}")
            
            await interaction.response.send_message(
                f"Private thread created! [Click here to join](<https://discord.com/channels/{interaction.guild.id}/{thread.id}>)",
                ephemeral=True
            )
            
            transaction_text = "listing" if not self.transaction_type else self.transaction_type.lower()
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
                f"*AFL Wall Street is facilitating this meeting but not directly involved in buying or selling.*",
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
        self.transaction_type = transaction_type
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            kamas_amount_str = self.amount.value
            kamas_amount = parse_kamas_amount(kamas_amount_str)
            if kamas_amount is None:
                await interaction.response.send_message(
                    "Invalid kamas amount format. Please use formats like '10M', '500K', or '1000000'.",
                    ephemeral=True
                )
                return
                
            try:
                price_per_m = float(self.price_per_million.value.replace(',', '.'))
            except ValueError:
                await interaction.response.send_message(
                    "Invalid price format. Please enter a numeric value.",
                    ephemeral=True
                )
                return
                
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
            
            temp_file_name = f"temp_form_{interaction.user.id}.txt"
            with open(temp_file_name, "w") as f:
                for key, value in form_data.items():
                    f.write(f"{key}:{value}\n")
            
            view = ui.View(timeout=300)
            currency_select = CurrencySelect()
            view.add_item(currency_select)
            
            async def currency_callback(interaction: discord.Interaction):
                selected_currency = currency_select.values[0]
                await process_listing(interaction, selected_currency, temp_file_name)
                
            currency_select.callback = currency_callback
            
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
    try:
        form_data = {}
        with open(temp_file_path, "r") as f:
            for line in f:
                key, value = line.strip().split(":", 1)
                form_data[key] = value
        
        os.remove(temp_file_path)
        
        ticket_channel = interaction.client.get_channel(TICKET_CHANNEL_ID)
        if not ticket_channel:
            ticket_channel = await interaction.client.fetch_channel(TICKET_CHANNEL_ID)
        
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        user_id = int(form_data["user_id"])
        transaction_type = form_data["transaction_type"]
        ticket_ref = f"{transaction_type}-{user_id}-{timestamp}"
        
        kamas_amount = float(form_data["kamas_amount"])
        kamas_amount_str = form_data["kamas_amount_str"]
        price_per_m = float(form_data["price_per_m"])
        
        total_price = (kamas_amount / 1000000) * price_per_m
        currency_symbol = CURRENCY_SYMBOLS[currency]
        
        if currency == "EUR":
            formatted_total = f"{total_price:.2f} {currency_symbol}"
            formatted_price_per_m = f"{price_per_m:.2f} {currency_symbol}"
        else:
            formatted_total = f"{currency_symbol}{total_price:.2f}"
            formatted_price_per_m = f"{currency_symbol}{price_per_m:.2f}"
        
        embed = discord.Embed(
            title=f"AFL Wall Street - Kamas {transaction_type}",
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
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(KAMAS_LOGO_URL) as resp:
                    if resp.status == 200:
                        data = await resp.read()
                        embed.set_thumbnail(url=KAMAS_LOGO_URL)
        except Exception as e:
            logger.warning(f"Could not set Kamas logo: {e}")
        
        view = PrivateThreadButton(seller_id=user_id, transaction_type=transaction_type)
        message = await ticket_channel.send(embed=embed, view=view)
        
        with open(f"listing_{ticket_ref}.txt", "w") as f:
            f.write(str(message.id))
        
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
    amount_str = amount_str.replace(" ", "").upper()
    if "M" in amount_str:
        try:
            num_part = amount_str.replace("M", "")
            num_part = num_part.replace(",", ".")
            return float(num_part) * 1000000
        except ValueError:
            return None
    elif "K" in amount_str:
        try:
            num_part = amount_str.replace("K", "")
            num_part = num_part.replace(",", ".")
            return float(num_part) * 1000
        except ValueError:
            return None
    else:
        try:
            return float(amount_str.replace(",", "."))
        except ValueError:
            return None

def format_kamas_amount(amount_num):
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
    """View containing the Buy, Sell, and Verification buttons."""
    
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="BUY KAMAS", style=discord.ButtonStyle.primary, custom_id="buy_kamas", emoji="💰")
    async def buy_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(KamasModal("BUY"))
    
    @discord.ui.button(label="SELL KAMAS", style=discord.ButtonStyle.success, custom_id="sell_kamas", emoji="💎")
    async def sell_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(KamasModal("SELL"))
    
    @discord.ui.button(label="BECOME VERIFIED SELLER", style=discord.ButtonStyle.secondary, custom_id="verify_seller", emoji="🏆")
    async def verify_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if already verified
        if is_verified_seller(interaction.user.id):
            profile = get_seller_profile(interaction.user.id)
            verified_date = datetime.fromisoformat(profile['verified_date']).strftime('%Y-%m-%d')
            await interaction.response.send_message(
                f"🏆 **You are already a Verified Seller!**\n\n"
                f"✅ Verified on: {verified_date}\n"
                f"🎯 Status: Active\n\n"
                f"Your listings automatically show the verified badge. Thank you for being a trusted member of AFL Wall Street!",
                ephemeral=True
            )
            return
        
        # Check if already has pending application
        verification_data = load_verification_data()
        if str(interaction.user.id) in verification_data:
            await interaction.response.send_message(
                "⚠️ You already have a pending verification application. Please wait for it to be processed.\n"
                "If you need to update your information, please contact an administrator.",
                ephemeral=True
            )
            return
        
        # Show verification modal
        await interaction.response.send_modal(VerificationModal())

class KamasCog(commands.Cog):
    """Cog for managing kamas buying and selling functionality."""
    
    def __init__(self, bot):
        self.bot = bot
        self.panel_message = None
        self.bot.loop.create_task(self.setup_panel())
        self.bot.loop.create_task(self.restore_active_views())
    
    async def restore_active_views(self):
        await self.bot.wait_until_ready()
        try:
            ticket_channel = self.bot.get_channel(TICKET_CHANNEL_ID)
            if not ticket_channel:
                ticket_channel = await self.bot.fetch_channel(TICKET_CHANNEL_ID)
                
            listing_files = [f for f in os.listdir() if f.startswith("listing_")]
            
            for file in listing_files:
                try:
                    with open(file, "r") as f:
                        message_id = int(f.read().strip())
                    
                    parts = file.replace("listing_", "").replace(".txt", "").split("-")
                    transaction_type = parts[0]
                    seller_id = int(parts[1])
                    
                    try:
                        message = await ticket_channel.fetch_message(message_id)
                        thread_files = [tf for tf in os.listdir() if tf.startswith(f"thread_private_thread_{seller_id}_")]
                        buyer_id = None
                        
                        if thread_files and not thread_files[0].endswith("_0.txt"):
                            buyer_part = thread_files[0].split("_")[-1].replace(".txt", "")
                            if buyer_part != "0":
                                buyer_id = int(buyer_part)
                        
                        view = PrivateThreadButton(seller_id=seller_id, buyer_id=buyer_id, transaction_type=transaction_type)
                        await message.edit(view=view)
                        logger.info(f"Restored view for listing {file}")
                    except discord.NotFound:
                        os.remove(file)
                        logger.info(f"Removed stale listing file {file}")
                    except Exception as e:
                        logger.error(f"Error restoring view for {file}: {e}")
                except Exception as e:
                    logger.error(f"Error processing listing file {file}: {e}")
            
            thread_files = [f for f in os.listdir() if f.startswith("thread_private_thread_")]
            for file in thread_files:
                try:
                    with open(file, "r") as f:
                        thread_id = int(f.read().strip())
                    
                    try:
                        thread = await self.bot.fetch_channel(thread_id)
                        messages = [msg async for msg in thread.history(limit=10)]
                        has_management_view = False
                        
                        for msg in messages:
                            if msg.author.id == self.bot.user.id and "Secure Transaction Thread" in msg.content and msg.components:
                                has_management_view = True
                                break
                        
                        if not has_management_view:
                            await thread.send(
                                "**Transaction Thread Management**\n\n"
                                "Use the button below to close this thread when your transaction is complete:",
                                view=ThreadManagementView()
                            )
                    except discord.NotFound:
                        os.remove(file)
                    except Exception as e:
                        logger.error(f"Error restoring thread management for {file}: {e}")
                except Exception as e:
                    logger.error(f"Error processing thread file {file}: {e}")
            
            logger.info("Completed restoration of active views and threads")
            
        except Exception as e:
            logger.exception(f"Error in restore_active_views: {e}")
    
    async def setup_panel(self):
        await self.bot.wait_until_ready()
        try:
            panel_channel = self.bot.get_channel(PANEL_CHANNEL_ID)
            if not panel_channel:
                panel_channel = await self.bot.fetch_channel(PANEL_CHANNEL_ID)
            
            panel_message_id = None
            panel_file_path = "kamas_panel_id.txt"
            if os.path.exists(panel_file_path):
                with open(panel_file_path, "r") as f:
                    try:
                        panel_message_id = int(f.read().strip())
                    except (ValueError, IOError):
                        logger.warning("Could not read panel message ID from file")
            
            existing_message = None
            if panel_message_id:
                try:
                    existing_message = await panel_channel.fetch_message(panel_message_id)
                    logger.info(f"Found existing kamas panel message: {panel_message_id}")
                except discord.NotFound:
                    logger.info("Stored kamas panel message not found, creating new one")
                except Exception as e:
                    logger.exception(f"Error fetching kamas panel message: {e}")
            
            kamas_logo = None
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(KAMAS_LOGO_URL) as resp:
                        if resp.status == 200:
                            kamas_logo = KAMAS_LOGO_URL
            except Exception as e:
                logger.warning(f"Failed to get Kamas logo: {e}")
            
            embed = discord.Embed(
                title=" AFL Wall Street - Kamas Trading ",
                description=(
                    "**Secure & Reliable Kamas Trading Platform**\n\n"
                    "Looking to buy or sell kamas safely? AFL Wall Street facilitates secure meetings "
                    "between buyers and sellers within the AFL alliance.\n\n"
                    "AFL Wall Street is dedicated to providing a secure platform for kamas trading "
                    "among AFL members.\n\n"
                    "**Please provide the following information:**\n"
                    "• Amount of kamas you're buying/selling\n"
                    "• Your price per million kamas\n"
                    "• Select your currency (€ or $)\n"
                    "• Your preferred payment method\n"
                    "• Contact information"
                ),
                color=discord.Color.gold()
            )
            
            if kamas_logo:
                embed.set_thumbnail(url=kamas_logo)
            
            embed.add_field(name="📈 Attractive Rates & Safe Transactions", value="\u200b", inline=False)
            embed.add_field(name="🔒 Secure & Private Communications", value="\u200b", inline=False)
            embed.add_field(name="👥 Trusted Intermediary Service", value="\u200b", inline=False)
            
            embed.add_field(
                name="How It Works",
                value=(
                    "1. Click one of the buttons below and fill out the form\n"
                    "2. Select your preferred currency (€ or $)\n"
                    "3. A listing will be created in our transactions channel\n"
                    "4. Interested parties can use the private discussion button\n"
                    "5. Complete your transaction safely through our secure system\n"
                    "6. Close the thread when your transaction is complete"
                ),
                inline=False
            )
            
            embed.set_footer(text="AFL Wall Street - Making transactions secure since Today we are just Testing this Idea")
            
            view = KamasView()
            
            if existing_message:
                await existing_message.edit(embed=embed, view=view)
                self.panel_message = existing_message
                logger.info(f"Updated existing kamas panel message: {existing_message.id}")
            else:
                self.panel_message = await panel_channel.send(embed=embed, view=view)
                with open(panel_file_path, "w") as f:
                    f.write(str(self.panel_message.id))
                logger.info(f"Created new kamas panel message: {self.panel_message.id}")
                
        except Exception as e:
            logger.exception(f"Error setting up kamas panel: {e}")
    
    @app_commands.command(name="wallstreet_reset", description="Reset the AFL Wall Street kamas trading panel")
    @app_commands.checks.has_permissions(administrator=True)
    async def reset_panel(self, interaction: discord.Interaction):
        try:
            panel_file_path = "kamas_panel_id.txt"
            if os.path.exists(panel_file_path):
                os.remove(panel_file_path)
            await self.setup_panel()
            await interaction.response.send_message("AFL Wall Street trading panel has been reset!", ephemeral=True)
        except Exception as e:
            logger.exception(f"Error resetting AFL Wall Street panel: {e}")
            await interaction.response.send_message("Failed to reset the AFL Wall Street panel.", ephemeral=True)
    
    @app_commands.command(name="wallstreet_connect", description="Connect a buyer to a seller's listing")
    @app_commands.checks.has_permissions(administrator=True)
    async def connect_users(self, interaction: discord.Interaction, listing_message_id: str, user: discord.Member):
        try:
            ticket_channel = interaction.client.get_channel(TICKET_CHANNEL_ID)
            if not ticket_channel:
                ticket_channel = await interaction.client.fetch_channel(TICKET_CHANNEL_ID)
            
            message = await ticket_channel.fetch_message(int(listing_message_id))
            
            if not message.components:
                await interaction.response.send_message("This message doesn't have a transaction button.", ephemeral=True)
                return
            
            seller_id = None
            transaction_type = None
            ref_value = None
            
            if message.embeds and message.embeds[0].fields:
                if message.embeds[0].title:
                    title_parts = message.embeds[0].title.split(' - Kamas ')
                    if len(title_parts) > 1:
                        transaction_type = title_parts[1]
                
                for field in message.embeds[0].fields:
                    if field.name == "Reference ID":
                        ref_value = field.value.strip('`')
                        try:
                            ref_parts = ref_value.split('-')
                            if len(ref_parts) >= 2:
                                seller_id = int(ref_parts[1])
                        except:
                            pass
            
            if not seller_id:
                await interaction.response.send_message("Could not identify the seller from this listing.", ephemeral=True)
                return
            
            new_view = PrivateThreadButton(seller_id=seller_id, buyer_id=user.id, transaction_type=transaction_type)
            await message.edit(view=new_view)
            
            if ref_value:
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
    bot.add_view(KamasView())
    await bot.add_cog(KamasCog(bot), guilds=[discord.Object(id=SERVER_ID)])
    logger.info("AFL Wall Street kamas trading module has been loaded")
