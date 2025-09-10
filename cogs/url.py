import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import os
import uuid
import asyncio
import time
from datetime import datetime, timedelta
import mimetypes
import logging

logger = logging.getLogger(__name__)

class URLCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.temp_files = {}  # Store file info temporarily
        self.cleanup_task = None
        self.start_cleanup_task()

    def start_cleanup_task(self):
        """Start the cleanup task for expired files"""
        if self.cleanup_task is None or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self.cleanup_expired_files())

    async def cleanup_expired_files(self):
        """Clean up expired files every 30 minutes"""
        while True:
            try:
                current_time = time.time()
                expired_files = []
                
                for file_id, file_info in self.temp_files.items():
                    if current_time > file_info['expires_at']:
                        expired_files.append(file_id)
                
                for file_id in expired_files:
                    file_info = self.temp_files.pop(file_id, None)
                    if file_info and os.path.exists(file_info['path']):
                        try:
                            os.remove(file_info['path'])
                            logger.info(f"Cleaned up expired file: {file_id}")
                        except OSError:
                            pass
                
                await asyncio.sleep(1800)  # 30 minutes
            except Exception as e:
                logger.exception("Error in cleanup task")
                await asyncio.sleep(300)  # 5 minutes on error

    async def upload_to_temp_host(self, file_data, filename, content_type):
        """
        Upload file to a temporary hosting service
        This example uses file.io (24-hour hosting, single download)
        You can replace this with other services like:
        - 0x0.st (permanent until manually deleted)
        - transfer.sh (14 days)
        - tmpfiles.org (1 hour to 30 days)
        """
        try:
            # Using file.io as an example (24-hour hosting)
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('file', file_data, filename=filename, content_type=content_type)
                
                async with session.post('https://file.io/', data=data) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get('success'):
                            return result.get('link')
                    
                # Fallback to 0x0.st if file.io fails
                data = aiohttp.FormData()
                data.add_field('file', file_data, filename=filename, content_type=content_type)
                
                async with session.post('https://0x0.st', data=data) as response:
                    if response.status == 200:
                        url = await response.text()
                        return url.strip()
                        
        except Exception as e:
            logger.exception("Failed to upload to temporary host")
            
        return None

    async def create_local_temp_url(self, file_data, filename, content_type):
        """
        Alternative: Create a temporary local file and serve it via webhook
        This requires your bot to have a web server component
        """
        try:
            # Create temp directory if it doesn't exist
            temp_dir = "temp_files"
            os.makedirs(temp_dir, exist_ok=True)
            
            # Generate unique file ID
            file_id = str(uuid.uuid4())
            file_extension = os.path.splitext(filename)[1] or ''
            temp_filename = f"{file_id}{file_extension}"
            temp_path = os.path.join(temp_dir, temp_filename)
            
            # Save file temporarily
            with open(temp_path, 'wb') as f:
                f.write(file_data)
            
            # Store file info (expires in 24 hours)
            expires_at = time.time() + (24 * 60 * 60)  # 24 hours
            self.temp_files[file_id] = {
                'path': temp_path,
                'filename': filename,
                'content_type': content_type,
                'expires_at': expires_at,
                'created_at': time.time()
            }
            
            # Return a placeholder URL (you'll need to implement a web server)
            # This would be your bot's domain + file endpoint
            return f"https://your-bot-domain.com/temp/{file_id}"
            
        except Exception as e:
            logger.exception("Failed to create local temp file")
            return None

    @app_commands.command(name="url", description="Generate a shareable URL for an uploaded file")
    @app_commands.describe(file="The file to upload and generate URL for")
    async def generate_url(self, interaction: discord.Interaction, file: discord.Attachment):
        """Generate a shareable URL for an uploaded file"""
        await interaction.response.defer(thinking=True)
        
        try:
            # Check file size (most services have limits, typically 100MB)
            max_size = 100 * 1024 * 1024  # 100MB
            if file.size > max_size:
                await interaction.followup.send(
                    "❌ File is too large! Maximum size is 100MB.",
                    ephemeral=True
                )
                return
            
            # Download the file
            file_data = await file.read()
            
            # Get content type
            content_type = file.content_type or mimetypes.guess_type(file.filename)[0] or 'application/octet-stream'
            
            # Upload to temporary hosting service
            url = await self.upload_to_temp_host(file_data, file.filename, content_type)
            
            if url:
                embed = discord.Embed(
                    title="🔗 File URL Generated!",
                    color=discord.Color.green(),
                    timestamp=datetime.utcnow()
                )
                embed.add_field(name="Filename", value=file.filename, inline=True)
                embed.add_field(name="Size", value=f"{file.size:,} bytes", inline=True)
                embed.add_field(name="Type", value=content_type, inline=True)
                embed.add_field(name="📎 Shareable URL", value=f"[Click here to access]({url})", inline=False)
                embed.add_field(
                    name="⚠️ Important Notes", 
                    value="• This URL is temporary and may expire\n• Some services allow only one download\n• Don't share sensitive files", 
                    inline=False
                )
                embed.set_footer(text=f"Uploaded by {interaction.user.display_name}")
                
                # Also send the raw URL for easy copying
                await interaction.followup.send(embed=embed)
                await interaction.followup.send(f"**Direct URL:** {url}", ephemeral=True)
                
                logger.info(f"Generated URL for {file.filename} by {interaction.user}")
                
            else:
                embed = discord.Embed(
                    title="❌ Upload Failed",
                    description="Failed to upload file to temporary hosting service. Please try again later.",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=embed, ephemeral=True)
                
        except Exception as e:
            logger.exception("Error in generate_url command")
            await interaction.followup.send(
                "❌ An error occurred while processing your file. Please try again.",
                ephemeral=True
            )

    @app_commands.command(name="url_info", description="Get information about temporary file hosting")
    async def url_info(self, interaction: discord.Interaction):
        """Show information about the URL generation feature"""
        embed = discord.Embed(
            title="📎 File URL Generator",
            description="Generate shareable URLs for any file you upload!",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📤 Supported Files",
            value="• Text files (.txt, .md, .json, etc.)\n• Images (.png, .jpg, .gif, etc.)\n• Videos (.mp4, .avi, .mov, etc.)\n• Archives (.zip, .rar, etc.)\n• Any other file type",
            inline=False
        )
        
        embed.add_field(
            name="📏 Limits",
            value="• Maximum file size: 100MB\n• URLs are temporary (24 hours)\n• Some services allow single download only",
            inline=False
        )
        
        embed.add_field(
            name="🚀 How to Use",
            value="1. Use `/url` command\n2. Upload your file\n3. Get a shareable URL\n4. Share the URL with anyone!",
            inline=False
        )
        
        embed.add_field(
            name="⚠️ Security",
            value="• Don't upload sensitive/private files\n• URLs can be accessed by anyone\n• Files are automatically deleted after expiry",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

    def cog_unload(self):
        """Clean up when cog is unloaded"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        # Clean up any remaining temp files
        temp_dir = "temp_files"
        if os.path.exists(temp_dir):
            try:
                for filename in os.listdir(temp_dir):
                    filepath = os.path.join(temp_dir, filename)
                    if os.path.isfile(filepath):
                        os.remove(filepath)
                os.rmdir(temp_dir)
            except OSError:
                pass

async def setup(bot):
    await bot.add_cog(URLCog(bot))
