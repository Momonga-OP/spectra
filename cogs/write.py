import discord
from discord.ext import commands
from discord import app_commands
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

class WriteCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Define allowed file types for security
        self.allowed_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
        self.max_file_size = 8 * 1024 * 1024  # 8MB limit

    @app_commands.command(
        name="write", 
        description="Send."
    )
    @app_commands.describe(
        message="The message to send (max 2000 characters)",
        image="Optional image to include with the message",
        channel="Channel to send the message to (defaults to current channel)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def write(
        self, 
        interaction: discord.Interaction, 
        message: str, 
        image: discord.Attachment = None,
        channel: discord.TextChannel = None
    ):
        # Validate message length
        if len(message) > 2000:
            await interaction.response.send_message(
                "Message is too long! Discord messages can't exceed 2000 characters.", 
                ephemeral=True
            )
            return

        # Use current channel if none specified
        target_channel = channel or interaction.channel

        # Check bot permissions in target channel
        if not target_channel.permissions_for(interaction.guild.me).send_messages:
            await interaction.response.send_message(
                f"I don't have permission to send messages in {target_channel.mention}.", 
                ephemeral=True
            )
            return

        files = []
        
        # Validate and process image if provided
        if image:
            # Check file size
            if image.size > self.max_file_size:
                await interaction.response.send_message(
                    f"Image file is too large! Maximum size is {self.max_file_size // (1024*1024)}MB.", 
                    ephemeral=True
                )
                return
            
            # Check file extension
            file_ext = '.' + image.filename.split('.')[-1].lower() if '.' in image.filename else ''
            if file_ext not in self.allowed_extensions:
                await interaction.response.send_message(
                    f"Invalid file type! Allowed types: {', '.join(self.allowed_extensions)}", 
                    ephemeral=True
                )
                return
            
            try:
                # Read and prepare the image file
                img_bytes = await image.read()
                img_file = discord.File(fp=BytesIO(img_bytes), filename=image.filename)
                files.append(img_file)
            except Exception as e:
                logger.error(f"Error processing image: {e}")
                await interaction.response.send_message(
                    "Failed to process the image file.", 
                    ephemeral=True
                )
                return

        try:
            # Send the anonymous message
            await target_channel.send(content=message, files=files)
            
            # Confirm success to the user
            success_msg = f"Anonymous message sent successfully to {target_channel.mention}!"
            await interaction.response.send_message(success_msg, ephemeral=True)
            
            # Log the action for audit purposes (without revealing content)
            logger.info(
                f"Anonymous message sent by {interaction.user} ({interaction.user.id}) "
                f"to #{target_channel.name} in {interaction.guild.name}"
            )
            
        except discord.Forbidden:
            await interaction.response.send_message(
                f"I don't have permission to send messages in {target_channel.mention}.", 
                ephemeral=True
            )
        except discord.HTTPException as e:
            logger.error(f"HTTP error sending message: {e}")
            await interaction.response.send_message(
                "Failed to send the message due to a Discord API error.", 
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Unexpected error in write command: {e}")
            await interaction.response.send_message(
                "An unexpected error occurred while sending the message.", 
                ephemeral=True
            )

    @write.error
    async def write_error(self, interaction: discord.Interaction, error):
        """Handle command-level errors"""
        try:
            if isinstance(error, app_commands.MissingPermissions):
                await interaction.response.send_message(
                    "You need administrator permissions to use this command.", 
                    ephemeral=True
                )
            elif isinstance(error, app_commands.CommandOnCooldown):
                await interaction.response.send_message(
                    f"Command is on cooldown. Try again in {error.retry_after:.2f} seconds.", 
                    ephemeral=True
                )
            else:
                logger.error(f"Unhandled error in write command: {error}")
                await interaction.response.send_message(
                    "An error occurred while processing the command.", 
                    ephemeral=True
                )
        except discord.errors.InteractionResponded:
            # Interaction was already responded to
            logger.warning("Attempted to respond to already responded interaction")

    @commands.Cog.listener()
    async def on_ready(self):
        """Log when the cog is ready"""
        logger.info(f"{self.__class__.__name__} cog is ready")

async def setup(bot):
    """Set up the cog"""
    await bot.add_cog(WriteCog(bot))
    logger.info("WriteCog loaded successfully")
