import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import datetime
import logging
import io
import os
from typing import Optional

logger = logging.getLogger(__name__)

class ServerAFL(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.target_guild_id = 1213699457233985587  # Target server ID
        self.export_in_progress = False
        
    @app_commands.command(name="serverafl", description="Export 2 months of server communication to TXT file")
    async def serverafl(self, interaction: discord.Interaction):
        """Export server communication from the last 2 months"""
        
        # Check if export is already in progress
        if self.export_in_progress:
            await interaction.response.send_message("❌ Export is already in progress. Please wait for it to complete.", ephemeral=True)
            return
            
        # Check if user has admin permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return
            
        # Get the target guild
        guild = self.bot.get_guild(self.target_guild_id)
        if not guild:
            await interaction.response.send_message("❌ Target server not found or bot is not in the server.", ephemeral=True)
            return
            
        # Defer the response since this will take time
        await interaction.response.defer(ephemeral=True)
        
        self.export_in_progress = True
        
        try:
            # Calculate date range (2 months ago)
            now = datetime.datetime.now(datetime.timezone.utc)
            two_months_ago = now - datetime.timedelta(days=60)
            
            # Create progress message
            progress_embed = discord.Embed(
                title="📊 Server Export in Progress",
                description="Starting export process...",
                color=0x00ff00
            )
            await interaction.followup.send(embed=progress_embed)
            
            # Export data
            export_data = await self._export_server_data(guild, two_months_ago, interaction)
            
            if not export_data:
                await interaction.followup.send("❌ No messages found in the specified time range.", ephemeral=True)
                return
                
            # Create the text file
            filename = f"server_export_{guild.name}_{now.strftime('%Y%m%d_%H%M%S')}.txt"
            file_content = self._format_export_data(export_data, guild, two_months_ago, now)
            
            # Create file object
            file_obj = io.StringIO(file_content)
            file_bytes = io.BytesIO(file_obj.getvalue().encode('utf-8'))
            
            # Send the file
            discord_file = discord.File(file_bytes, filename=filename)
            
            success_embed = discord.Embed(
                title="✅ Export Complete",
                description=f"Successfully exported {len(export_data)} messages from the last 2 months.",
                color=0x00ff00
            )
            success_embed.add_field(name="Server", value=guild.name, inline=True)
            success_embed.add_field(name="Date Range", value=f"{two_months_ago.strftime('%Y-%m-%d')} to {now.strftime('%Y-%m-%d')}", inline=True)
            success_embed.add_field(name="File Size", value=f"{len(file_content.encode('utf-8')) / 1024:.2f} KB", inline=True)
            
            await interaction.followup.send(embed=success_embed, file=discord_file)
            
        except Exception as e:
            logger.exception("Error during server export")
            error_embed = discord.Embed(
                title="❌ Export Failed",
                description=f"An error occurred during export: {str(e)[:1000]}",
                color=0xff0000
            )
            await interaction.followup.send(embed=error_embed)
            
        finally:
            self.export_in_progress = False
    
    async def _export_server_data(self, guild: discord.Guild, since: datetime.datetime, interaction: discord.Interaction):
        """Export server data with progress updates"""
        export_data = []
        processed_channels = 0
        total_channels = len([c for c in guild.channels if isinstance(c, discord.TextChannel)])
        
        # Process each text channel
        for channel in guild.channels:
            if not isinstance(channel, discord.TextChannel):
                continue
                
            # Check if bot has read permissions
            if not channel.permissions_for(guild.me).read_message_history:
                continue
                
            try:
                # Update progress
                processed_channels += 1
                progress_embed = discord.Embed(
                    title="📊 Server Export in Progress",
                    description=f"Processing channel: {channel.name}",
                    color=0xffff00
                )
                progress_embed.add_field(
                    name="Progress", 
                    value=f"{processed_channels}/{total_channels} channels processed", 
                    inline=True
                )
                
                # Edit the progress message every few channels to avoid rate limits
                if processed_channels % 3 == 0:
                    try:
                        await interaction.edit_original_response(embed=progress_embed)
                    except:
                        pass  # Ignore edit failures
                
                # Fetch messages from the channel
                message_count = 0
                async for message in channel.history(after=since, limit=None):
                    if message.author.bot:
                        continue  # Skip bot messages
                        
                    # Extract message data
                    message_data = {
                        'channel_name': channel.name,
                        'channel_id': channel.id,
                        'author_name': message.author.display_name,
                        'author_id': message.author.id,
                        'content': message.content,
                        'timestamp': message.created_at,
                        'attachments': [att.url for att in message.attachments],
                        'embeds': len(message.embeds),
                        'reactions': [f"{reaction.emoji}:{reaction.count}" for reaction in message.reactions]
                    }
                    export_data.append(message_data)
                    message_count += 1
                    
                    # Add small delay every 100 messages to prevent rate limiting
                    if message_count % 100 == 0:
                        await asyncio.sleep(0.1)
                
                logger.info(f"Processed {message_count} messages from #{channel.name}")
                
            except discord.Forbidden:
                logger.warning(f"No permission to read #{channel.name}")
                continue
            except Exception as e:
                logger.exception(f"Error processing channel #{channel.name}")
                continue
        
        return export_data
    
    def _format_export_data(self, export_data: list, guild: discord.Guild, start_date: datetime.datetime, end_date: datetime.datetime) -> str:
        """Format the export data into a readable text format"""
        
        # Sort messages by timestamp
        export_data.sort(key=lambda x: x['timestamp'])
        
        # Create header
        header = f"""
================================================================================
                        SERVER COMMUNICATION EXPORT
================================================================================
Server: {guild.name} (ID: {guild.id})
Export Date: {end_date.strftime('%Y-%m-%d %H:%M:%S UTC')}
Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}
Total Messages: {len(export_data)}
================================================================================

"""
        
        # Group messages by channel
        channels = {}
        for msg in export_data:
            channel_name = msg['channel_name']
            if channel_name not in channels:
                channels[channel_name] = []
            channels[channel_name].append(msg)
        
        # Format content
        content = header
        
        for channel_name, messages in channels.items():
            content += f"\n\n{'='*80}\n"
            content += f"CHANNEL: #{channel_name} ({len(messages)} messages)\n"
            content += f"{'='*80}\n\n"
            
            for msg in messages:
                # Format timestamp
                timestamp = msg['timestamp'].strftime('%Y-%m-%d %H:%M:%S UTC')
                
                # Format message
                content += f"[{timestamp}] {msg['author_name']} (ID: {msg['author_id']}):\n"
                
                # Add message content
                if msg['content']:
                    content += f"  {msg['content']}\n"
                
                # Add attachments info
                if msg['attachments']:
                    content += f"  📎 Attachments: {', '.join(msg['attachments'])}\n"
                
                # Add embeds info
                if msg['embeds'] > 0:
                    content += f"  📋 Embeds: {msg['embeds']}\n"
                
                # Add reactions info
                if msg['reactions']:
                    content += f"  🔄 Reactions: {', '.join(msg['reactions'])}\n"
                
                content += "\n"
        
        # Add footer
        footer = f"""
================================================================================
                                END OF EXPORT
================================================================================
Export completed: {end_date.strftime('%Y-%m-%d %H:%M:%S UTC')}
Total channels processed: {len(channels)}
Total messages exported: {len(export_data)}
================================================================================
"""
        
        content += footer
        return content

async def setup(bot):
    await bot.add_cog(ServerAFL(bot))
