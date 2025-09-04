import discord
from discord.ext import commands
from discord import app_commands, ui
import logging
import asyncio

logger = logging.getLogger(__name__)

OWNER_ID = 486652069831376943  # Your Discord user ID
SERVER_ID = 1213699457233985587  # Your server ID
CHANNEL_ID = 1358250304306544740  # Channel to post the message in

# Guild role IDs
GUILD_LEADER_ROLE_ID = 1213701307324440646  # {GL}
SECOND_IN_COMMAND_ROLE_ID = 1213701571771367464  # {SIC}

# Guild name role IDs with their corresponding prefixes
GUILD_ROLES = {
    1213699577568428074: "Tight",
    1231487845798248458: "Guardians",
    1231573508556066847: "EV",
    1392462864429744238: "Punishment",
    1231573194687774851: "Demigods",
    1231740379515322418: "Nemesis",
    1255591594179170407: "Perfect",
    1364708638668619786: "Imperium",
    1394808571308412948: "Thieves",
    1397597190779699200: "SAQ",
    1397689982721851602: "Trenches",
    1410478721072103556: "Amanacer",
    1325581624129097872: "Sparta",
    1357443037311275108: "Italians",
    1387964877770981439: "Sausage",
    1231573740018470962: "Krosmic Flux",
    1366855660632936468: "Vendetta",
    1412884625096704051: "Family",
    1412884525347901581: "Vesperion",
}

def get_clean_display_name(member):
    """Get the user's actual display name (not username) by checking their global name first"""
    # Priority: global_name (display name) > username
    # member.global_name is the "display name" feature Discord introduced
    return member.global_name or member.name

def clean_name_from_tags(name):
    """Remove all existing tags from a name"""
    if not name:
        return ""
    
    # Remove role prefixes
    name = name.replace("{GL}", "").replace("{SIC}", "").strip()
    
    # Remove guild tags
    for guild_name in GUILD_ROLES.values():
        name = name.replace(f"{{{guild_name}}}", "").strip()
    
    # Clean up extra spaces
    name = " ".join(name.split())
    
    return name

def generate_proper_nickname(member, custom_name=None):
    """Generate properly formatted nickname with no duplications"""
    # Get role prefix
    role_prefix = ""
    if discord.utils.get(member.roles, id=GUILD_LEADER_ROLE_ID):
        role_prefix = "{GL} "
    elif discord.utils.get(member.roles, id=SECOND_IN_COMMAND_ROLE_ID):
        role_prefix = "{SIC} "
    
    # Get guild tag
    guild_tag = ""
    for role_id, guild_name in GUILD_ROLES.items():
        if discord.utils.get(member.roles, id=role_id):
            guild_tag = f"{{{guild_name}}} "
            break
    
    # Get base name - priority: custom_name > clean display name > clean username
    if custom_name:
        base_name = clean_name_from_tags(custom_name.strip())
    else:
        # Use the member's actual display name (global_name) or username
        display_name = get_clean_display_name(member)
        base_name = clean_name_from_tags(display_name)
    
    # If no relevant roles, return None (member shouldn't be renamed)
    if not role_prefix and not guild_tag:
        return None
    
    # Build final nickname
    nickname = f"{role_prefix}{guild_tag}{base_name}".strip()
    
    # Clean up any extra spaces
    nickname = " ".join(nickname.split())
    
    # Truncate if too long (Discord limit is 32 characters)
    if len(nickname) > 32:
        nickname = nickname[:32]
    
    return nickname

# Persistent view for the button
class NameButtonView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SetNameButton())

# Button for setting in-game name
class SetNameButton(ui.Button):
    def __init__(self):
        super().__init__(style=discord.ButtonStyle.primary, label="Set Your In-game Name", custom_id="set_ingame_name")
    
    async def callback(self, interaction: discord.Interaction):
        # Create a modal for the user to input their in-game name
        modal = NameInputModal()
        await interaction.response.send_modal(modal)

# Modal for inputting in-game name
class NameInputModal(ui.Modal, title="Set Your In-game Name"):
    ingame_name = ui.TextInput(
        label="In-game Name",
        placeholder="Enter your main character name in Dofus Touch",
        required=True,
        max_length=25
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        # Get the member
        member = interaction.user
        
        # Generate new nickname with the provided in-game name
        new_nickname = generate_proper_nickname(member, self.ingame_name.value)
        
        if not new_nickname:
            await interaction.response.send_message(
                "You don't have any guild roles assigned. Please contact an admin to get your roles first.",
                ephemeral=True
            )
            return
        
        try:
            await member.edit(nick=new_nickname)
            await interaction.response.send_message(
                f"Your in-game name has been set to: **{new_nickname}**", 
                ephemeral=True
            )
            logger.info(f"Set nickname for {member.name} to {new_nickname}")
        except discord.Forbidden:
            await interaction.response.send_message(
                "I don't have permission to change your nickname. Please contact a server admin.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"An error occurred: {str(e)}",
                ephemeral=True
            )
            logger.error(f"Error setting nickname for {member.name}: {e}")

class Members(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_id = None
        
        # Register the persistent view
        self.bot.add_view(NameButtonView())
    
    @app_commands.command(name="fixnames", description="Fix all member nicknames using their proper display names")
    async def fixnames(self, interaction: discord.Interaction):
        """Fix all member nicknames using their proper display names"""
        # Check if the user is the owner
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("Only the server owner can use this command.", ephemeral=True)
            return
        
        # Respond immediately to avoid timeout
        await interaction.response.send_message(
            "🔧 **Starting display name fix process...**\n"
            "I'll fix all nicknames using proper display names and post updates in this channel.",
            ephemeral=True
        )
        
        # Send initial public message
        public_msg = await interaction.channel.send("🔧 **Starting display name fix process initiated by the server owner**")
        
        # Start the background task
        self.bot.loop.create_task(self._process_fix_names(interaction, public_msg))
    
    async def _process_fix_names(self, interaction: discord.Interaction, public_msg: discord.Message):
        """Background task to fix all member names with proper display names"""
        try:
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("❌ Error: Could not access server information.", ephemeral=True)
                return
            
            # Statistics tracking
            fixed_count = 0
            skipped_no_roles = 0
            skipped_permissions = 0
            errors = 0
            
            # Get all members
            try:
                members = guild.members
                if len(members) < guild.member_count:
                    await public_msg.edit(content=f"{public_msg.content}\n📥 Fetching all server members...")
                    members = [member async for member in guild.fetch_members(limit=None)]
            except Exception as e:
                logger.error(f"Error fetching members: {e}")
                await public_msg.edit(content=f"{public_msg.content}\n❌ Error fetching server members")
                return
            
            # Filter out bots
            real_members = [member for member in members if not member.bot]
            
            await public_msg.edit(
                content=f"{public_msg.content}\n"
                f"🎯 **Processing {len(real_members)} members**\n"
                f"Estimated time: ~{len(real_members) * 0.3 / 60:.1f} minutes"
            )
            
            # Process each member
            for i, member in enumerate(real_members):
                try:
                    # Generate proper nickname using display name
                    new_nickname = generate_proper_nickname(member)
                    
                    # Skip if no relevant roles
                    if new_nickname is None:
                        skipped_no_roles += 1
                        logger.info(f"Skipped {get_clean_display_name(member)} - no relevant roles")
                        continue
                    
                    # Skip if nickname is already correct
                    if member.nick == new_nickname:
                        logger.info(f"Skipped {get_clean_display_name(member)} - nickname already correct")
                        continue
                    
                    # Try to update the nickname
                    try:
                        await member.edit(nick=new_nickname, reason="Fix display name formatting")
                        fixed_count += 1
                        logger.info(f"Fixed nickname for {member.name} to {new_nickname}")
                        
                    except discord.Forbidden:
                        skipped_permissions += 1
                        logger.warning(f"No permission to rename {get_clean_display_name(member)}")
                        
                    except discord.HTTPException as e:
                        errors += 1
                        logger.error(f"HTTP error renaming {get_clean_display_name(member)}: {e}")
                        
                except Exception as e:
                    errors += 1
                    logger.error(f"Unexpected error processing {get_clean_display_name(member)}: {e}")
                
                # Add delay to avoid rate limits
                await asyncio.sleep(0.3)
                
                # Update progress every 25 members
                if (i + 1) % 25 == 0:
                    try:
                        progress_percentage = ((i + 1) / len(real_members)) * 100
                        await public_msg.edit(
                            content=f"{public_msg.content.split('🎯')[0]}🎯 **Processing {len(real_members)} members**\n"
                            f"⏳ Progress: {i + 1}/{len(real_members)} ({progress_percentage:.1f}%)\n"
                            f"✅ Fixed: {fixed_count} | ⏭️ Skipped: {skipped_no_roles + skipped_permissions}"
                        )
                    except Exception as e:
                        logger.error(f"Error updating progress: {e}")
            
            # Send final summary
            summary = (
                f"✅ **Display Name Fix Complete!**\n"
                f"**Successfully Fixed:** {fixed_count}\n"
                f"**Skipped (No Roles):** {skipped_no_roles}\n"
                f"**Skipped (Permissions):** {skipped_permissions}\n"
                f"**Errors:** {errors}\n"
                f"**Total Processed:** {len(real_members)}"
            )
            
            if errors > 0:
                summary += "\n\n⚠️ Some errors occurred. Check bot logs for details."
            
            await public_msg.edit(content=f"{public_msg.content}\n\n{summary}")
            
        except Exception as e:
            logger.error(f"Error in fix process: {e}")
            await public_msg.edit(content=f"{public_msg.content}\n❌ Process failed: {str(e)}")
    
    @app_commands.command(name="renameall", description="Automatically rename all members based on their roles")
    async def renameall(self, interaction: discord.Interaction):
        """Automatically rename all members in the server based on their roles"""
        # Check if the user is the owner
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("Only the server owner can use this command.", ephemeral=True)
            return
        
        # Respond immediately to avoid timeout
        await interaction.response.send_message(
            "🔄 **Starting automatic rename process...**\n"
            "I'll post public updates in this channel as I process members.",
            ephemeral=True
        )
        
        # Send initial public message
        public_msg = await interaction.channel.send("🔧 **Starting member rename process initiated by the server owner**")
        
        # Start the background task
        self.bot.loop.create_task(self._process_rename_all(interaction, public_msg))
    
    async def _process_rename_all(self, interaction: discord.Interaction, public_msg: discord.Message):
        """Background task to process all member renames"""
        try:
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("❌ Error: Could not access server information.", ephemeral=True)
                return
            
            # Statistics tracking
            renamed_count = 0
            skipped_no_roles = 0
            skipped_permissions = 0
            errors = 0
            
            # Get all members
            try:
                members = guild.members
                if len(members) < guild.member_count:
                    await public_msg.edit(content=f"{public_msg.content}\n📥 Fetching all server members...")
                    members = [member async for member in guild.fetch_members(limit=None)]
            except Exception as e:
                logger.error(f"Error fetching members: {e}")
                await public_msg.edit(content=f"{public_msg.content}\n❌ Error fetching server members")
                return
            
            # Filter out bots
            real_members = [member for member in members if not member.bot]
            
            await public_msg.edit(
                content=f"{public_msg.content}\n"
                f"🎯 **Processing {len(real_members)} members**\n"
                f"Estimated time: ~{len(real_members) * 0.3 / 60:.1f} minutes"
            )
            
            # Process each member
            for i, member in enumerate(real_members):
                try:
                    # Generate new nickname based on roles
                    new_nickname = generate_proper_nickname(member)
                    
                    # Skip if no relevant roles found
                    if new_nickname is None:
                        skipped_no_roles += 1
                        logger.info(f"Skipped {get_clean_display_name(member)} - no relevant roles")
                        continue
                    
                    # Skip if nickname is already correct
                    if member.nick == new_nickname:
                        logger.info(f"Skipped {get_clean_display_name(member)} - nickname already correct")
                        continue
                    
                    # Try to update the nickname
                    try:
                        await member.edit(nick=new_nickname, reason="Automatic role-based rename")
                        renamed_count += 1
                        logger.info(f"Renamed {member.name} to {new_nickname}")
                        
                    except discord.Forbidden:
                        skipped_permissions += 1
                        logger.warning(f"No permission to rename {get_clean_display_name(member)}")
                        
                    except discord.HTTPException as e:
                        errors += 1
                        logger.error(f"HTTP error renaming {get_clean_display_name(member)}: {e}")
                        
                except Exception as e:
                    errors += 1
                    logger.error(f"Unexpected error processing {get_clean_display_name(member)}: {e}")
                
                # Add delay to avoid rate limits
                await asyncio.sleep(0.3)
                
                # Update progress every 25 members
                if (i + 1) % 25 == 0:
                    try:
                        progress_percentage = ((i + 1) / len(real_members)) * 100
                        await public_msg.edit(
                            content=f"{public_msg.content.split('🎯')[0]}🎯 **Processing {len(real_members)} members**\n"
                            f"⏳ Progress: {i + 1}/{len(real_members)} ({progress_percentage:.1f}%)\n"
                            f"✅ Renamed: {renamed_count} | ⏭️ Skipped: {skipped_no_roles + skipped_permissions}"
                        )
                    except Exception as e:
                        logger.error(f"Error updating progress: {e}")
            
            # Send final summary
            summary = (
                f"✅ **Automatic Rename Complete!**\n"
                f"**Successfully Renamed:** {renamed_count}\n"
                f"**Skipped (No Roles):** {skipped_no_roles}\n"
                f"**Skipped (Permissions):** {skipped_permissions}\n"
                f"**Errors:** {errors}\n"
                f"**Total Processed:** {len(real_members)}"
            )
            
            if errors > 0:
                summary += "\n\n⚠️ Some errors occurred. Check bot logs for details."
            
            await public_msg.edit(content=f"{public_msg.content}\n\n{summary}")
            
        except Exception as e:
            logger.error(f"Error in rename process: {e}")
            await public_msg.edit(content=f"{public_msg.content}\n❌ Process failed: {str(e)}")
    
    @app_commands.command(name="setname", description="Post a message asking members to set their in-game name")
    async def setname(self, interaction: discord.Interaction):
        """Post a message asking members to set their in-game name"""
        # Check if the user is the owner
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("Only the server owner can use this command.", ephemeral=True)
            return
        
        # Get the channel to post the message in
        channel = self.bot.get_channel(CHANNEL_ID)
        if not channel:
            await interaction.response.send_message(f"Could not find channel with ID {CHANNEL_ID}", ephemeral=True)
            return
        
        # Check if we already have a message
        if self.message_id:
            try:
                existing_message = await channel.fetch_message(self.message_id)
                await interaction.response.send_message(
                    "A setup message already exists. Use /resetname to delete and create a new one.", 
                    ephemeral=True
                )
                return
            except discord.NotFound:
                # Message was deleted, we can create a new one
                self.message_id = None
            except Exception as e:
                logger.error(f"Error fetching existing message: {e}")
        
        # Create the embed message
        embed = discord.Embed(
            title="Welcome to AfterLife Community!",
            description=(
                "Hello AfterLife members! 👋\n\n"
                "We hope you're all doing well. To help us get to know each other better and keep our Discord server organized, "
                "please set your in-game name for your main Dofus Touch character by clicking the button below.\n\n"
                "This will update your nickname on the server to include your guild information and character name, "
                "making it easier for everyone to recognize each other both in-game and on Discord.\n\n"
                "Thank you for being part of AfterLife!"
            ),
            color=discord.Color.blue()
        )
        embed.set_footer(text="AfterLife Community | Dofus Touch")
        
        # Create the persistent view with the button
        view = NameButtonView()
        
        # Send the message
        message = await channel.send(embed=embed, view=view)
        
        # Save the message ID for future reference
        self.message_id = message.id
        
        await interaction.response.send_message("Message posted successfully!", ephemeral=True)
        logger.info(f"Set name message posted by {interaction.user.name} with ID {message.id}")
    
    @app_commands.command(name="resetname", description="Reset the name setup message")
    async def resetname(self, interaction: discord.Interaction):
        """Reset the name setup message"""
        # Check if the user is the owner
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("Only the server owner can use this command.", ephemeral=True)
            return
        
        # Get the channel
        channel = self.bot.get_channel(CHANNEL_ID)
        
        if not channel:
            await interaction.response.send_message(f"Could not find channel with ID {CHANNEL_ID}", ephemeral=True)
            return
        
        # Try to delete the existing message
        if self.message_id:
            try:
                message = await channel.fetch_message(self.message_id)
                await message.delete()
                logger.info(f"Deleted existing setup message with ID {self.message_id}")
            except discord.NotFound:
                logger.info(f"Message with ID {self.message_id} already deleted")
            except Exception as e:
                logger.error(f"Error deleting message: {e}")
        
        # Reset the message ID
        self.message_id = None
        
        await interaction.response.send_message("Setup message has been reset. Use /setname to create a new one.", ephemeral=True)

    @app_commands.command(name="resetnames", description="Reset all members' nicknames to their usernames")
    async def resetnames(self, interaction: discord.Interaction):
        """Reset all nicknames to usernames"""
        # Check if the user is the owner
        if interaction.user.id != OWNER_ID:
            await interaction.response.send_message("Only the server owner can use this command.", ephemeral=True)
            return
        
        # Respond immediately to avoid timeout
        await interaction.response.send_message(
            "🔄 **Starting nickname reset process...**\n"
            "I'll reset all nicknames and post updates in this channel.",
            ephemeral=True
        )
        
        # Send initial public message
        public_msg = await interaction.channel.send("🔧 **Starting nickname reset process initiated by the server owner**")
        
        # Start the background task
        self.bot.loop.create_task(self._process_reset_names(interaction, public_msg))
    
    async def _process_reset_names(self, interaction: discord.Interaction, public_msg: discord.Message):
        """Background task to reset all nicknames"""
        try:
            guild = interaction.guild
            if not guild:
                await interaction.followup.send("❌ Error: Could not access server information.", ephemeral=True)
                return
            
            # Statistics tracking
            reset_count = 0
            skipped_count = 0
            errors = 0
            
            # Get all members
            try:
                members = guild.members
                if len(members) < guild.member_count:
                    await public_msg.edit(content=f"{public_msg.content}\n📥 Fetching all server members...")
                    members = [member async for member in guild.fetch_members(limit=None)]
            except Exception as e:
                logger.error(f"Error fetching members: {e}")
                await public_msg.edit(content=f"{public_msg.content}\n❌ Error fetching server members")
                return
            
            # Filter out bots
            real_members = [member for member in members if not member.bot]
            
            await public_msg.edit(
                content=f"{public_msg.content}\n"
                f"🎯 **Processing {len(real_members)} members**\n"
                f"Estimated time: ~{len(real_members) * 0.3 / 60:.1f} minutes"
            )
            
            # Process each member
            for i, member in enumerate(real_members):
                try:
                    # Skip if no nickname set
                    if not member.nick:
                        skipped_count += 1
                        continue
                        
                    # Reset to username
                    try:
                        await member.edit(nick=None, reason="Reset nickname")
                        reset_count += 1
                        logger.info(f"Reset nickname for {member.name}")
                        
                    except discord.Forbidden:
                        skipped_count += 1
                        logger.warning(f"No permission to reset {get_clean_display_name(member)}")
                        
                    except discord.HTTPException as e:
                        errors += 1
                        logger.error(f"HTTP error resetting {get_clean_display_name(member)}: {e}")
                        
                except Exception as e:
                    errors += 1
                    logger.error(f"Unexpected error processing {get_clean_display_name(member)}: {e}")
                
                # Add delay to avoid rate limits
                await asyncio.sleep(0.3)
                
                # Update progress every 25 members
                if (i + 1) % 25 == 0:
                    try:
                        progress_percentage = ((i + 1) / len(real_members)) * 100
                        await public_msg.edit(
                            content=f"{public_msg.content.split('🎯')[0]}🎯 **Processing {len(real_members)} members**\n"
                            f"⏳ Progress: {i + 1}/{len(real_members)} ({progress_percentage:.1f}%)\n"
                            f"✅ Reset: {reset_count} | ⏭️ Skipped: {skipped_count}"
                        )
                    except Exception as e:
                        logger.error(f"Error updating progress: {e}")
            
            # Send final summary
            summary = (
                f"✅ **Nickname Reset Complete!**\n"
                f"**Successfully Reset:** {reset_count}\n"
                f"**Skipped:** {skipped_count}\n"
                f"**Errors:** {errors}\n"
                f"**Total Processed:** {len(real_members)}"
            )
            
            if errors > 0:
                summary += "\n\n⚠️ Some errors occurred. Check bot logs for details."
            
            await public_msg.edit(content=f"{public_msg.content}\n\n{summary}")
            
        except Exception as e:
            logger.error(f"Error in reset process: {e}")
            await public_msg.edit(content=f"{public_msg.content}\n❌ Process failed: {str(e)}")

async def setup(bot):
    await bot.add_cog(Members(bot))
