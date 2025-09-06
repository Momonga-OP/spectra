import discord
from discord.ext import commands
from discord import app_commands
import re
from typing import Optional

class Announcement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="announcement", description="Send an announcement message in embedded format")
    @app_commands.describe(
        message="The message content (supports **bold**, *italic*, __underline__, ~~strikethrough~~)",
        title="Title for the embed (optional)",
        color="Embed color in hex format (e.g., #FF0000 for red) or color name",
        channel="Target channel (use #channel-name or channel ID, defaults to current channel)",
        footer="Footer text for the embed (optional)",
        thumbnail="Thumbnail URL for the embed (optional)",
        image="Image URL for the embed (optional)"
    )
    async def announcement(
        self, 
        interaction: discord.Interaction,
        message: str,
        title: Optional[str] = None,
        color: Optional[str] = None,
        channel: Optional[str] = None,
        footer: Optional[str] = None,
        thumbnail: Optional[str] = None,
        image: Optional[str] = None
    ):
        # Check if user has permissions to send announcements
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ You don't have permission to send announcements.", ephemeral=True)
            return

        try:
            # Determine target channel
            target_channel = interaction.channel  # Default to current channel
            
            if channel:
                # Handle channel mention format (#channel-name)
                if channel.startswith('#'):
                    channel_name = channel[1:]  # Remove the #
                    target_channel = discord.utils.get(interaction.guild.channels, name=channel_name)
                    if not target_channel:
                        await interaction.response.send_message(f"❌ Channel '{channel}' not found.", ephemeral=True)
                        return
                # Handle channel ID
                elif channel.isdigit():
                    target_channel = self.bot.get_channel(int(channel))
                    if not target_channel:
                        await interaction.response.send_message(f"❌ Channel with ID '{channel}' not found.", ephemeral=True)
                        return
                else:
                    # Try to find channel by name without #
                    target_channel = discord.utils.get(interaction.guild.channels, name=channel)
                    if not target_channel:
                        await interaction.response.send_message(f"❌ Channel '{channel}' not found.", ephemeral=True)
                        return

            # Check if bot has permissions to send messages in target channel
            if not target_channel.permissions_for(interaction.guild.me).send_messages:
                await interaction.response.send_message(f"❌ I don't have permission to send messages in {target_channel.mention}.", ephemeral=True)
                return

            # Create embed
            embed = discord.Embed()
            
            # Set embed color
            if color:
                embed_color = self.parse_color(color)
                if embed_color:
                    embed.color = embed_color
                else:
                    embed.color = discord.Color.blue()  # Default color
            else:
                embed.color = discord.Color.blue()  # Default color

            # Set title if provided
            if title:
                embed.title = title

            # Process message content for formatting
            processed_message = self.process_formatting(message)
            embed.description = processed_message

            # Set footer if provided
            if footer:
                embed.set_footer(text=footer)

            # Set thumbnail if provided
            if thumbnail:
                if self.is_valid_url(thumbnail):
                    embed.set_thumbnail(url=thumbnail)
                else:
                    await interaction.response.send_message("❌ Invalid thumbnail URL provided.", ephemeral=True)
                    return

            # Set image if provided
            if image:
                if self.is_valid_url(image):
                    embed.set_image(url=image)
                else:
                    await interaction.response.send_message("❌ Invalid image URL provided.", ephemeral=True)
                    return

            # Add timestamp
            embed.timestamp = discord.utils.utcnow()
            
            # Send the embed
            await target_channel.send(embed=embed)
            
            # Confirm to user
            if target_channel == interaction.channel:
                await interaction.response.send_message("✅ Announcement sent!", ephemeral=True)
            else:
                await interaction.response.send_message(f"✅ Announcement sent to {target_channel.mention}!", ephemeral=True)

        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to send messages in that channel.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

    def process_formatting(self, text: str) -> str:
        """Process text formatting for Discord markdown"""
        # Replace common formatting patterns
        # Discord already supports **bold**, *italic*, __underline__, ~~strikethrough~~
        # We can also add support for line breaks
        text = text.replace('\\n', '\n')
        return text

    def parse_color(self, color_input: str) -> Optional[discord.Color]:
        """Parse color input and return discord.Color object"""
        color_input = color_input.lower().strip()
        
        # Predefined color names
        color_map = {
            'red': discord.Color.red(),
            'green': discord.Color.green(),
            'blue': discord.Color.blue(),
            'yellow': discord.Color.gold(),
            'orange': discord.Color.orange(),
            'purple': discord.Color.purple(),
            'pink': discord.Color.magenta(),
            'cyan': discord.Color.teal(),
            'white': discord.Color.from_rgb(255, 255, 255),
            'black': discord.Color.from_rgb(0, 0, 0),
            'grey': discord.Color.light_grey(),
            'gray': discord.Color.light_grey(),
        }
        
        # Check if it's a predefined color name
        if color_input in color_map:
            return color_map[color_input]
        
        # Check if it's a hex color
        if color_input.startswith('#'):
            try:
                hex_color = color_input[1:]  # Remove #
                if len(hex_color) == 6:
                    return discord.Color(int(hex_color, 16))
            except ValueError:
                pass
        
        # Check if it's a hex color without #
        try:
            if len(color_input) == 6:
                return discord.Color(int(color_input, 16))
        except ValueError:
            pass
        
        return None

    def is_valid_url(self, url: str) -> bool:
        """Basic URL validation"""
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return url_pattern.match(url) is not None

    @app_commands.command(name="quick_announcement", description="Send a quick announcement with just message and optional channel")
    @app_commands.describe(
        message="The message content",
        channel="Target channel (optional)"
    )
    async def quick_announcement(
        self, 
        interaction: discord.Interaction,
        message: str,
        channel: Optional[str] = None
    ):
        """Simplified version of announcement command - Admin only"""
        # Check if user has administrator permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Only administrators can send announcements.", ephemeral=True)
            return
            
        await self.announcement(
            interaction=interaction,
            message=message,
            channel=channel,
            title="📢 Announcement",
            color="blue"
        )

async def setup(bot):
    await bot.add_cog(Announcement(bot))
