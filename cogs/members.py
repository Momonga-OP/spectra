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
    1231573740018470962: "Soul",
    1231573194687774851: "Demigods",
    1231740379515322418: "Nemesis",
    1255591594179170407: "Uchiha",
    1364708638668619786: "Imperium",
    1365322130270715904: "OldNLazy",
    1325581624129097872: "Sparta",
    1357443037311275108: "Italians",
    1372865125366763550: "Mafia",
    1366855660632936468: "Vendetta"
}

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
        
        # Get the member's roles
        guild_leader_role = discord.utils.get(member.roles, id=GUILD_LEADER_ROLE_ID)
        second_in_command_role = discord.utils.get(member.roles, id=SECOND_IN_COMMAND_ROLE_ID)
        
        # Determine the prefix based on roles
        prefix = ""
        if guild_leader_role:
            prefix = "{GL} "
        elif second_in_command_role:
            prefix = "{SIC} "
        
        # Find guild name from roles
        guild_name = ""
        for role_id, name in GUILD_ROLES.items():
            role = discord.utils.get(member.roles, id=role_id)
            if role:
                guild_name = f"{{{name}}} "
                break
        
        # Format the new nickname
        in_game_name = self.ingame_name.value.strip()
        new_nickname = f"{prefix}{guild_name}{in_game_name}"
        
        # Truncate if too long (Discord has a 32 character limit for nicknames)
        if len(new_nickname) > 32:
            new_nickname = new_nickname[:32]
        
        try:
            # Update the nickname
            await member.edit(nick=new_nickname)
            
            # Confirm to the user
            await interaction.response.send_message(
                f"Thank you! Your nickname has been updated to: **{new_nickname}**", 
                ephemeral=True
            )
            logger.info(f"Updated nickname for {member.name} to {new_nickname}")
        except Exception as e:
            await interaction.response.send_message(
                "Sorry, I couldn't update your nickname. Please contact a server administrator.", 
                ephemeral=True
            )
            logger.error(f"Error updating nickname for {member.name}: {e}")

def generate_nickname_from_roles(member):
    """Generate a nickname based on member's roles"""
    # Get the member's roles
    guild_leader_role = discord.utils.get(member.roles, id=GUILD_LEADER_ROLE_ID)
    second_in_command_role = discord.utils.get(member.roles, id=SECOND_IN_COMMAND_ROLE_ID)
    
    # Determine the prefix based on roles
    prefix = ""
    if guild_leader_role:
        prefix = "{GL} "
    elif second_in_command_role:
        prefix = "{SIC} "
    
    # Find guild name from roles
    guild_name = ""
    for role_id, name in GUILD_ROLES.items():
        role = discord.utils.get(member.roles, id=role_id)
        if role:
            guild_name = f"{{{name}}} "
            break
    
    # If no relevant roles found, return None
    if not prefix and not guild_name:
        return None
    
    # Extract current in-game name from existing nickname or use display name
    current_nickname = member.display_name
    in_game_name = current_nickname
    
    # Try to extract the in-game name from existing formatted nickname
    if current_nickname.startswith(("{GL}", "{SIC}")):
        # Parse existing formatted nickname
        parts = current_nickname.split("} ")
        if len(parts) >= 2:
            # Get the last part which should be the in-game name
            in_game_name = parts[-1]
        elif len(parts) == 1 and "}" in current_nickname:
            # Handle case where there's only one part with }
            temp = current_nickname.split("}")[-1].strip()
            if temp:
                in_game_name = temp
    
    # Format the new nickname
    new_nickname = f"{prefix}{guild_name}{in_game_name}"
    
    # Truncate if too long (Discord has a 32 character limit for nicknames)
    if len(new_nickname) > 32:
        new_nickname = new_nickname[:32]
    
    return new_nickname

class Members(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_id = None
        
        # Register the persistent view
        self.bot.add_view(NameButtonView())
    
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
            "I'll send you updates in this channel as I process members.\n"
            "This process runs in the background and won't timeout!",
            ephemeral=True
        )
        
        # Start the background task
        self.bot.loop.create_task(self._process_rename_all(interaction))
    
    async def _process_rename_all(self, interaction: discord.Interaction):
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
            
            # Get all members (fetch if needed for larger servers)
            try:
                members = guild.members
                if len(members) < guild.member_count:
                    # Fetch all members if not all are cached
                    await interaction.followup.send("📥 Fetching all server members...", ephemeral=True)
                    members = [member async for member in guild.fetch_members(limit=None)]
            except Exception as e:
                logger.error(f"Error fetching members: {e}")
                await interaction.followup.send(f"❌ Error fetching server members: {e}", ephemeral=True)
                return
            
            # Filter out bots
            real_members = [member for member in members if not member.bot]
            
            await interaction.followup.send(
                f"🎯 **Processing {len(real_members)} members**\n"
                f"Estimated time: ~{len(real_members) * 0.5 / 60:.1f} minutes\n"
                "I'll update you every 25 members processed.",
                ephemeral=True
            )
            
            # Process each member
            for i, member in enumerate(real_members):
                try:
                    # Generate new nickname based on roles
                    new_nickname = generate_nickname_from_roles(member)
                    
                    # Skip if no relevant roles found
                    if new_nickname is None:
                        skipped_no_roles += 1
                        logger.info(f"Skipped {member.display_name} - no relevant roles")
                        continue
                    
                    # Skip if nickname is already correct
                    if member.display_name == new_nickname:
                        logger.info(f"Skipped {member.display_name} - nickname already correct")
                        continue
                    
                    # Try to update the nickname
                    try:
                        await member.edit(nick=new_nickname, reason="Automatic role-based rename")
                        renamed_count += 1
                        logger.info(f"Renamed {member.name} to {new_nickname}")
                        
                    except discord.Forbidden:
                        # Bot doesn't have permission to rename this user
                        skipped_permissions += 1
                        logger.warning(f"No permission to rename {member.display_name}")
                        
                    except discord.HTTPException as e:
                        errors += 1
                        logger.error(f"HTTP error renaming {member.display_name}: {e}")
                        
                except Exception as e:
                    errors += 1
                    logger.error(f"Unexpected error processing {member.display_name}: {e}")
                
                # Add delay to avoid rate limits (reduced from 0.5 to 0.3 seconds)
                await asyncio.sleep(0.3)
                
                # Send progress updates every 25 members
                if (i + 1) % 25 == 0:
                    try:
                        progress_percentage = ((i + 1) / len(real_members)) * 100
                        await interaction.followup.send(
                            f"⏳ **Progress Update**\n"
                            f"Processed: {i + 1}/{len(real_members)} ({progress_percentage:.1f}%)\n"
                            f"Renamed: {renamed_count} | Skipped: {skipped_no_roles + skipped_permissions}",
                            ephemeral=True
                        )
                    except Exception as e:
                        logger.error(f"Error sending progress update: {e}")
            
            # Send final summary
            summary_embed = discord.Embed(
                title="✅ Automatic Rename Complete!",
                description="All members have been processed successfully!",
                color=discord.Color.green()
            )
            summary_embed.add_field(
                name="📊 Final Results",
                value=(
                    f"**✅ Successfully Renamed:** {renamed_count}\n"
                    f"**⏭️ Skipped (No Roles):** {skipped_no_roles}\n"
                    f"**🔒 Skipped (Permissions):** {skipped_permissions}\n"
                    f"**❌ Errors:** {errors}\n"
                    f"**👥 Total Processed:** {len(real_members)}"
                ),
                inline=False
            )
            
            if errors > 0:
                summary_embed.add_field(
                    name="⚠️ Note",
                    value="Some errors occurred during the process. Check the bot logs for details.",
                    inline=False
                )
            
            summary_embed.set_footer(text=f"Process completed • AfterLife Community")
            
            await interaction.followup.send(embed=summary_embed, ephemeral=True)
            logger.info(f"Automatic rename completed: {renamed_count} renamed, {skipped_no_roles} skipped (no roles), {skipped_permissions} skipped (permissions), {errors} errors")
            
        except Exception as e:
            logger.error(f"Critical error in rename process: {e}")
            await interaction.followup.send(
                f"❌ **Critical Error**\n"
                f"The rename process encountered a fatal error: {e}\n"
                f"Please check the bot logs and try again.",
                ephemeral=True
            )
    
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
                "please set your in-game name for your main Dofus Touch  by clicking the button below.\n\n"
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

async def setup(bot):
    await bot.add_cog(Members(bot))
