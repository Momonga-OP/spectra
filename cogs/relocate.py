import discord
from discord.ext import commands
from discord import app_commands
import logging
import asyncio
from asyncio import Lock
from datetime import datetime, timedelta
import re

class Relocate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.relocating_messages = {}  # Dictionary to keep track of relocating messages
        self.locks = {}  # Locks to prevent race conditions
        self.reaction_relocate = {}  # Track messages marked for relocation via reaction
        self.AUTHORIZED_USER_ID = 486652069831376943  # Latif's user ID

    def is_authorized(self, user_id):
        """Check if the user is authorized to use relocate commands"""
        return user_id == self.AUTHORIZED_USER_ID

    async def check_authorization(self, interaction):
        """Check authorization and send error message if unauthorized"""
        if not self.is_authorized(interaction.user.id):
            await interaction.response.send_message(
                "❌ You are not authorized to use this command. Only Latif can use relocation commands.",
                ephemeral=True
            )
            logging.warning(f"Unauthorized user {interaction.user} ({interaction.user.id}) tried to use relocate command")
            return False
        return True
        """Create an embedded message with author info and content"""
        embed = discord.Embed(
            description=message.content if message.content else "*No text content*",
            color=message.author.color if hasattr(message.author, 'color') else discord.Color.default(),
            timestamp=message.created_at
        )
        
        # Set author with profile picture
        embed.set_author(
            name=message.author.display_name,
            icon_url=message.author.display_avatar.url
        )
        
        # Add source channel info
        embed.set_footer(text=f"Originally from #{source_channel.name}")
        
        # Handle message replies
        if message.reference and message.reference.message_id:
            try:
                replied_message = await source_channel.fetch_message(message.reference.message_id)
                embed.add_field(
                    name="Replying to:",
                    value=f"{replied_message.author.mention}: {replied_message.content[:100]}{'...' if len(replied_message.content) > 100 else ''}",
                    inline=False
                )
            except discord.errors.NotFound:
                embed.add_field(name="Replying to:", value="*Message not found*", inline=False)
        
        # Handle message attachments in embed
        if message.attachments:
            if len(message.attachments) == 1 and message.attachments[0].content_type and message.attachments[0].content_type.startswith('image/'):
                # Single image - display in embed
                embed.set_image(url=message.attachments[0].url)
            else:
                # Multiple attachments or non-image files
                attachment_info = []
                for i, attachment in enumerate(message.attachments, 1):
                    attachment_info.append(f"{i}. [{attachment.filename}]({attachment.url})")
                embed.add_field(
                    name=f"Attachments ({len(message.attachments)})",
                    value="\n".join(attachment_info),
                    inline=False
                )
        
        # Handle embeds in the original message
        if message.embeds:
            embed.add_field(
                name="Original message contained embeds",
                value=f"This message had {len(message.embeds)} embed(s)",
                inline=False
            )
        
        return embed

    async def relocate_message(self, message, target_channel, source_channel=None):
        """Relocate a single message with all its content"""
        if source_channel is None:
            source_channel = message.channel
            
        embed = await self.create_embed_message(message, source_channel)
        
        # Send the embed
        sent_message = await target_channel.send(embed=embed)
        
        # Send attachments separately if there are multiple or non-image files
        if message.attachments:
            if len(message.attachments) > 1 or not (message.attachments[0].content_type and message.attachments[0].content_type.startswith('image/')):
                files = []
                for attachment in message.attachments:
                    try:
                        file = await attachment.to_file()
                        files.append(file)
                    except discord.errors.HTTPException:
                        # Handle files that are too large or can't be downloaded
                        await target_channel.send(f"⚠️ Could not relocate attachment: {attachment.filename} (too large or inaccessible)")
                
                if files:
                    # Send files in batches (Discord limit is 10 files per message)
                    for i in range(0, len(files), 10):
                        batch = files[i:i+10]
                        await target_channel.send(files=batch)
        
        # Handle original embeds
        for original_embed in message.embeds:
            await target_channel.send(embed=original_embed)
        
        return sent_message

    @app_commands.command(name="relocate", description="Relocate a message to a different channel")
    async def relocate(self, interaction: discord.Interaction, message_id: str, target_channel: discord.TextChannel):
        # Check authorization first
        if not await self.check_authorization(interaction):
            return
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.NotFound:
            logging.error("Interaction not found when attempting to defer response")
            return

        logging.info(f"Relocate command invoked by {interaction.user} for message {message_id} to {target_channel}")

        try:
            # Ensure a lock exists for this message
            if message_id not in self.locks:
                self.locks[message_id] = Lock()

            async with self.locks[message_id]:
                # Check if the message is already being relocated
                if message_id in self.relocating_messages:
                    await interaction.followup.send("This message is already being relocated.")
                    return

                # Mark the message as being relocated
                self.relocating_messages[message_id] = True

                # Fetch the message by ID
                channel = interaction.channel
                try:
                    message = await channel.fetch_message(message_id)
                except discord.errors.NotFound:
                    logging.error("The message ID provided does not exist")
                    await interaction.followup.send("The message ID provided does not exist.")
                    return

                logging.info(f"Fetched message from {message.author.name}: {message.content[:50] if message.content else 'Media/Embed'}")

                # Relocate the message
                await self.relocate_message(message, target_channel)

                # Delete the original message with retry logic
                await asyncio.sleep(1)  # Small delay to ensure the message is sent before deleting
                
                if not channel.permissions_for(interaction.guild.me).manage_messages:
                    logging.warning("Missing permission to manage messages in the source channel.")
                    await interaction.followup.send("Relocation was successful, but the bot lacks permissions to delete the original message.")
                else:
                    for attempt in range(3):
                        try:
                            await message.delete()
                            logging.info("Original message deleted")
                            await interaction.followup.send("Message relocated successfully.")
                            break
                        except discord.errors.NotFound:
                            logging.warning(f"Message was not found or already deleted on attempt {attempt+1}")
                            if attempt == 2:
                                await interaction.followup.send("Message was not found or already deleted after multiple attempts.")
                        except discord.errors.Forbidden:
                            logging.error("The bot lacks permissions to delete the message")
                            await interaction.followup.send("Relocation was successful, but the bot lacks permissions to delete the original message.")
                            break
                        await asyncio.sleep(1)

        except discord.errors.Forbidden:
            logging.error("The bot lacks permissions to perform this action")
            await interaction.followup.send("The bot lacks permissions to perform this action. Please ensure the bot has 'Manage Messages' permission.")
        except Exception as e:
            logging.exception(f"Error in relocate command: {e}")
            await interaction.followup.send(f"An error occurred while processing your request: {e}")
        finally:
            # Clear the relocating state for the message and remove the lock
            self.relocating_messages.pop(message_id, None)
            self.locks.pop(message_id, None)

    @app_commands.command(name="relocate_last", description="Relocate the last N messages from this channel")
    async def relocate_last(self, interaction: discord.Interaction, count: int, target_channel: discord.TextChannel):
        """Relocate the last N messages from the current channel"""
        # Check authorization first
        if not await self.check_authorization(interaction):
            return
        if count < 1 or count > 50:
            await interaction.response.send_message("Please specify a count between 1 and 50.", ephemeral=True)
            return

        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.NotFound:
            logging.error("Interaction not found when attempting to defer response")
            return

        try:
            # Fetch the last N messages
            messages = []
            async for message in interaction.channel.history(limit=count + 1):  # +1 to exclude the command message
                if message.id != interaction.id:  # Skip the command message
                    messages.append(message)

            if not messages:
                await interaction.followup.send("No messages found to relocate.")
                return

            # Relocate messages in reverse order (oldest first)
            messages.reverse()
            relocated_count = 0

            for message in messages:
                try:
                    await self.relocate_message(message, target_channel)
                    
                    # Delete original message if we have permission
                    if interaction.channel.permissions_for(interaction.guild.me).manage_messages:
                        await message.delete()
                    
                    relocated_count += 1
                    await asyncio.sleep(0.5)  # Small delay between relocations
                except Exception as e:
                    logging.error(f"Error relocating message {message.id}: {e}")
                    continue

            await interaction.followup.send(f"Successfully relocated {relocated_count} out of {len(messages)} messages.")

        except Exception as e:
            logging.exception(f"Error in relocate_last command: {e}")
            await interaction.followup.send(f"An error occurred: {e}")

    @app_commands.command(name="relocate_from_user", description="Relocate recent messages from a specific user")
    async def relocate_from_user(self, interaction: discord.Interaction, user: discord.Member, count: int, target_channel: discord.TextChannel):
        """Relocate the last N messages from a specific user"""
        # Check authorization first
        if not await self.check_authorization(interaction):
            return
        if count < 1 or count > 20:
            await interaction.response.send_message("Please specify a count between 1 and 20.", ephemeral=True)
            return

        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.NotFound:
            logging.error("Interaction not found when attempting to defer response")
            return

        try:
            # Fetch messages from the specific user
            messages = []
            async for message in interaction.channel.history(limit=200):  # Search last 200 messages
                if message.author == user and len(messages) < count:
                    messages.append(message)

            if not messages:
                await interaction.followup.send(f"No recent messages found from {user.mention}.")
                return

            # Relocate messages in reverse order (oldest first)
            messages.reverse()
            relocated_count = 0

            for message in messages:
                try:
                    await self.relocate_message(message, target_channel)
                    
                    # Delete original message if we have permission
                    if interaction.channel.permissions_for(interaction.guild.me).manage_messages:
                        await message.delete()
                    
                    relocated_count += 1
                    await asyncio.sleep(0.5)  # Small delay between relocations
                except Exception as e:
                    logging.error(f"Error relocating message {message.id}: {e}")
                    continue

            await interaction.followup.send(f"Successfully relocated {relocated_count} messages from {user.mention}.")

        except Exception as e:
            logging.exception(f"Error in relocate_from_user command: {e}")
            await interaction.followup.send(f"An error occurred: {e}")

    @app_commands.command(name="relocate_range", description="Relocate messages between two message IDs")
    async def relocate_range(self, interaction: discord.Interaction, start_message_id: str, end_message_id: str, target_channel: discord.TextChannel):
        """Relocate all messages between two message IDs (inclusive)"""
        # Check authorization first
        if not await self.check_authorization(interaction):
            return
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.NotFound:
            logging.error("Interaction not found when attempting to defer response")
            return

        try:
            # Fetch both messages to validate IDs
            try:
                start_message = await interaction.channel.fetch_message(start_message_id)
                end_message = await interaction.channel.fetch_message(end_message_id)
            except discord.errors.NotFound:
                await interaction.followup.send("One or both message IDs are invalid.")
                return

            # Ensure start_message is older than end_message
            if start_message.created_at > end_message.created_at:
                start_message, end_message = end_message, start_message

            # Fetch messages in the range
            messages = []
            async for message in interaction.channel.history(
                after=start_message.created_at - timedelta(seconds=1),
                before=end_message.created_at + timedelta(seconds=1)
            ):
                messages.append(message)

            if not messages:
                await interaction.followup.send("No messages found in the specified range.")
                return

            # Sort messages by timestamp (oldest first)
            messages.sort(key=lambda m: m.created_at)
            relocated_count = 0

            for message in messages:
                try:
                    await self.relocate_message(message, target_channel)
                    
                    # Delete original message if we have permission
                    if interaction.channel.permissions_for(interaction.guild.me).manage_messages:
                        await message.delete()
                    
                    relocated_count += 1
                    await asyncio.sleep(0.5)  # Small delay between relocations
                except Exception as e:
                    logging.error(f"Error relocating message {message.id}: {e}")
                    continue

            await interaction.followup.send(f"Successfully relocated {relocated_count} messages from the specified range.")

        except Exception as e:
            logging.exception(f"Error in relocate_range command: {e}")
            await interaction.followup.send(f"An error occurred: {e}")

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle reaction-based relocation"""
        if user.bot:
            return
            
        # Check if user is authorized
        if not self.is_authorized(user.id):
            return
            
        # Check if the reaction is the relocate emoji (📦 or 🔄)
        if str(reaction.emoji) not in ['📦', '🔄']:
            return
            
        message_id = str(reaction.message.id)
        
        # Avoid duplicate relocations
        if message_id in self.relocating_messages:
            return
            
        # Store the message for relocation (you'd need to implement a way to specify target channel)
        self.reaction_relocate[message_id] = {
            'message': reaction.message,
            'user': user,
            'timestamp': datetime.now()
        }
        
        # Add a checkmark to indicate the message is marked for relocation
        await reaction.message.add_reaction('✅')

async def setup(bot):
    cog = Relocate(bot)
    await bot.add_cog(cog)
    # Register slash commands
    commands_to_add = ['relocate', 'relocate_last', 'relocate_from_user', 'relocate_range']
    for command_name in commands_to_add:
        if not bot.tree.get_command(command_name):
            command = getattr(cog, command_name)
            bot.tree.add_command(command)
