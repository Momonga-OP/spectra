import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging
import os
from datetime import datetime
import io

logger = logging.getLogger(__name__)

class MemberStats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.OWNER_ID = 486652069831376943
    
    @app_commands.command(name="memberstats", description="Get all messages from a specific user (Owner only)")
    @app_commands.describe(user_id="The Discord user ID to get stats for")
    async def memberstats(self, interaction: discord.Interaction, user_id: str):
        # Check if the user is the owner
        if interaction.user.id != self.OWNER_ID:
            await interaction.response.send_message("❌ This command can only be used by the bot owner.", ephemeral=True)
            return
        
        # Defer the response as this might take a while
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Convert user_id to int
            target_user_id = int(user_id)
        except ValueError:
            await interaction.followup.send("❌ Invalid user ID. Please provide a valid Discord user ID.", ephemeral=True)
            return
        
        try:
            # Get the user object
            target_user = await self.bot.fetch_user(target_user_id)
        except discord.NotFound:
            await interaction.followup.send("❌ User not found.", ephemeral=True)
            return
        except discord.HTTPException:
            await interaction.followup.send("❌ Failed to fetch user information.", ephemeral=True)
            return
        
        # Get the guild (server)
        guild = interaction.guild
        if not guild:
            await interaction.followup.send("❌ This command can only be used in a server.", ephemeral=True)
            return
        
        # Check if user is in the guild
        member = guild.get_member(target_user_id)
        if not member:
            await interaction.followup.send(f"❌ User {target_user.name} is not in this server.", ephemeral=True)
            return
        
        await interaction.followup.send(f"🔍 Collecting messages from {target_user.name}... This may take a while.", ephemeral=True)
        
        # Collect all messages from the user
        messages = []
        message_count = 0
        
        # Iterate through all text channels in the guild
        for channel in guild.text_channels:
            try:
                # Check if bot has permission to read message history
                if not channel.permissions_for(guild.me).read_message_history:
                    continue
                
                # Get messages from this channel
                async for message in channel.history(limit=None):
                    if message.author.id == target_user_id:
                        messages.append({
                            'channel': channel.name,
                            'channel_id': channel.id,
                            'message_id': message.id,
                            'content': message.content,
                            'timestamp': message.created_at,
                            'attachments': [att.url for att in message.attachments],
                            'embeds': len(message.embeds),
                            'reactions': [f"{reaction.emoji}: {reaction.count}" for reaction in message.reactions]
                        })
                        message_count += 1
                
                # Add a small delay to avoid rate limits
                await asyncio.sleep(0.1)
                
            except discord.Forbidden:
                logger.warning(f"No permission to read history in channel: {channel.name}")
                continue
            except Exception as e:
                logger.error(f"Error reading channel {channel.name}: {e}")
                continue
        
        if not messages:
            await interaction.followup.send(f"❌ No messages found from {target_user.name} in this server.", ephemeral=True)
            return
        
        # Sort messages by timestamp (oldest first)
        messages.sort(key=lambda x: x['timestamp'])
        
        # Create the text file content
        file_content = []
        file_content.append(f"MEMBER STATISTICS REPORT")
        file_content.append(f"=" * 50)
        file_content.append(f"User: {target_user.name}#{target_user.discriminator}")
        file_content.append(f"User ID: {target_user.id}")
        file_content.append(f"Server: {guild.name}")
        file_content.append(f"Server ID: {guild.id}")
        file_content.append(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
        file_content.append(f"Total Messages Found: {message_count}")
        file_content.append(f"=" * 50)
        file_content.append("")
        
        # Add member information
        if member:
            file_content.append(f"MEMBER INFORMATION:")
            file_content.append(f"Display Name: {member.display_name}")
            file_content.append(f"Joined Server: {member.joined_at.strftime('%Y-%m-%d %H:%M:%S UTC') if member.joined_at else 'Unknown'}")
            file_content.append(f"Account Created: {target_user.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            file_content.append(f"Roles: {', '.join([role.name for role in member.roles[1:]])}")  # Skip @everyone role
            file_content.append(f"Top Role: {member.top_role.name}")
            file_content.append(f"Bot: {target_user.bot}")
            file_content.append("")
        
        # Add channel statistics
        channel_stats = {}
        for msg in messages:
            channel_name = msg['channel']
            if channel_name not in channel_stats:
                channel_stats[channel_name] = 0
            channel_stats[channel_name] += 1
        
        file_content.append(f"MESSAGES BY CHANNEL:")
        for channel_name, count in sorted(channel_stats.items(), key=lambda x: x[1], reverse=True):
            file_content.append(f"#{channel_name}: {count} messages")
        file_content.append("")
        
        # Add all messages
        file_content.append(f"ALL MESSAGES:")
        file_content.append(f"-" * 50)
        
        for i, msg in enumerate(messages, 1):
            file_content.append(f"Message #{i}")
            file_content.append(f"Channel: #{msg['channel']}")
            file_content.append(f"Timestamp: {msg['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')}")
            file_content.append(f"Message ID: {msg['message_id']}")
            file_content.append(f"Content: {msg['content'] if msg['content'] else '[No text content]'}")
            
            if msg['attachments']:
                file_content.append(f"Attachments: {', '.join(msg['attachments'])}")
            
            if msg['embeds'] > 0:
                file_content.append(f"Embeds: {msg['embeds']}")
            
            if msg['reactions']:
                file_content.append(f"Reactions: {', '.join(msg['reactions'])}")
            
            file_content.append("-" * 30)
        
        # Create the file
        file_text = "\n".join(file_content)
        file_buffer = io.BytesIO(file_text.encode('utf-8'))
        
        # Create filename
        filename = f"{target_user.name}_{target_user.id}_messages_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        # Send the file
        discord_file = discord.File(file_buffer, filename=filename)
        
        try:
            await interaction.followup.send(
                f"✅ **Member Statistics Report Complete**\n"
                f"👤 **User:** {target_user.name}#{target_user.discriminator}\n"
                f"📊 **Total Messages:** {message_count}\n"
                f"🏠 **Server:** {guild.name}\n"
                f"📁 **File:** {filename}",
                file=discord_file,
                ephemeral=True
            )
        except discord.HTTPException as e:
            if "Request entity too large" in str(e):
                # If file is too large, try to save it and send a message
                try:
                    with open(filename, 'w', encoding='utf-8') as f:
                        f.write(file_text)
                    await interaction.followup.send(
                        f"⚠️ **File too large for Discord**\n"
                        f"The report has been saved as `{filename}` on the server.\n"
                        f"Total messages found: {message_count}",
                        ephemeral=True
                    )
                except Exception as save_error:
                    await interaction.followup.send(
                        f"❌ **Error:** File too large to send and couldn't save to disk.\n"
                        f"Found {message_count} messages but unable to deliver the report.",
                        ephemeral=True
                    )
            else:
                await interaction.followup.send(f"❌ Error sending file: {e}", ephemeral=True)
        
        logger.info(f"Member stats command completed for user {target_user.name} ({target_user.id}) by {interaction.user.name}")

async def setup(bot):
    await bot.add_cog(MemberStats(bot))
