import discord
from discord.ext import commands
from discord import app_commands
import PyPDF2
import os
import secrets
import string
import logging
from pathlib import Path
from typing import Optional
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
TEMP_DIR = Path("temp")
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25MB Discord limit
TIMEOUT_DURATION = 300  # 5 minutes for file operations
ALLOWED_EXTENSIONS = ['.pdf']

class PDFPasswordProtector(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._ensure_temp_dir()
    
    def _ensure_temp_dir(self) -> None:
        """Ensure the temp directory exists."""
        TEMP_DIR.mkdir(exist_ok=True)
    
    async def _cleanup_files(self, *file_paths: Path) -> None:
        """Safely clean up temporary files."""
        for path in file_paths:
            try:
                if path and path.exists():
                    path.unlink()
                    logger.info(f"Cleaned up file: {path}")
            except Exception as e:
                logger.error(f"Failed to clean up {path}: {e}")
    
    def _generate_secure_password(self, length: int = 12) -> str:
        """Generate a cryptographically secure password."""
        # Define character sets
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        special_chars = "!@#$%^&*"
        
        # Ensure at least one character from each set
        password = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
            secrets.choice(special_chars)
        ]
        
        # Fill the rest randomly
        all_chars = lowercase + uppercase + digits + special_chars
        for _ in range(length - 4):
            password.append(secrets.choice(all_chars))
        
        # Shuffle the password list
        secrets.SystemRandom().shuffle(password)
        return ''.join(password)
    
    def _validate_pdf(self, file_path: Path) -> bool:
        """Validate if the file is a proper PDF."""
        try:
            with open(file_path, 'rb') as file:
                PyPDF2.PdfReader(file)
            return True
        except Exception as e:
            logger.error(f"PDF validation failed: {e}")
            return False
    
    def _get_safe_filename(self, original_name: str) -> str:
        """Generate a safe filename for the protected PDF."""
        base_name = Path(original_name).stem
        # Remove any potentially dangerous characters
        safe_name = "".join(c for c in base_name if c.isalnum() or c in (' ', '-', '_')).strip()
        if not safe_name:
            safe_name = "protected_document"
        return f"{safe_name}_protected.pdf"

    @app_commands.command(
        name="protect_pdf", 
        description="Password protect a PDF file with an auto-generated secure password"
    )
    @app_commands.describe(
        pdf_file="The PDF file to password protect",
        custom_password="Optional: Use your own password instead of auto-generated one",
        password_length="Length of auto-generated password (8-32 characters, default: 12)"
    )
    async def protect_pdf(
        self, 
        interaction: discord.Interaction, 
        pdf_file: discord.Attachment,
        custom_password: Optional[str] = None,
        password_length: Optional[int] = 12
    ):
        # Validate file size
        if pdf_file.size > MAX_FILE_SIZE:
            await interaction.response.send_message(
                f"❌ File too large! Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB.",
                ephemeral=True
            )
            return
        
        # Check if the attachment is a PDF
        if not pdf_file.filename.lower().endswith('.pdf'):
            await interaction.response.send_message(
                "❌ Please upload a PDF file only.", 
                ephemeral=True
            )
            return
        
        # Validate password length
        if password_length and (password_length < 8 or password_length > 32):
            await interaction.response.send_message(
                "❌ Password length must be between 8 and 32 characters.",
                ephemeral=True
            )
            return
        
        await interaction.response.send_message("🔒 Processing your PDF file...", ephemeral=True)
        await self._protect_pdf_file(interaction, pdf_file, custom_password, password_length)

    async def _protect_pdf_file(
        self, 
        interaction: discord.Interaction, 
        pdf_file: discord.Attachment, 
        custom_password: Optional[str],
        password_length: int
    ) -> None:
        """Handle the actual PDF protection process."""
        input_path = None
        output_path = None
        
        try:
            # Create file paths
            input_path = TEMP_DIR / f"input_{interaction.user.id}_{pdf_file.filename}"
            output_filename = self._get_safe_filename(pdf_file.filename)
            output_path = TEMP_DIR / f"output_{interaction.user.id}_{output_filename}"
            
            # Download the PDF
            await pdf_file.save(input_path)
            
            # Validate the PDF
            if not self._validate_pdf(input_path):
                await interaction.followup.send(
                    "❌ The uploaded file is not a valid PDF or is corrupted.", 
                    ephemeral=True
                )
                return
            
            # Generate or use custom password
            if custom_password:
                password = custom_password
                password_source = "Custom"
            else:
                password = self._generate_secure_password(password_length)
                password_source = "Auto-generated"
            
            # Protect the PDF
            with open(input_path, 'rb') as input_file:
                pdf_reader = PyPDF2.PdfReader(input_file)
                pdf_writer = PyPDF2.PdfWriter()
                
                # Check if PDF is already encrypted
                if pdf_reader.is_encrypted:
                    await interaction.followup.send(
                        "❌ This PDF is already password protected.", 
                        ephemeral=True
                    )
                    return
                
                # Copy all pages to the writer
                for page_num in range(len(pdf_reader.pages)):
                    pdf_writer.add_page(pdf_reader.pages[page_num])
                
                # Encrypt the PDF
                pdf_writer.encrypt(password)
                
                # Write the protected PDF
                with open(output_path, 'wb') as output_file:
                    pdf_writer.write(output_file)
            
            # Check output file size
            if output_path.stat().st_size > MAX_FILE_SIZE:
                await interaction.followup.send(
                    "❌ Protected PDF is too large to send via Discord.", 
                    ephemeral=True
                )
                return
            
            # Create embed with file info
            embed = discord.Embed(
                title="🔒 PDF Successfully Protected",
                description="Your PDF has been password protected!",
                color=0x00ff00
            )
            embed.add_field(
                name="📁 Original File", 
                value=pdf_file.filename, 
                inline=False
            )
            embed.add_field(
                name="🔐 Password Type", 
                value=password_source, 
                inline=True
            )
            embed.add_field(
                name="📊 File Size", 
                value=f"{output_path.stat().st_size / 1024:.1f} KB", 
                inline=True
            )
            embed.add_field(
                name="📄 Pages", 
                value=str(len(pdf_reader.pages)), 
                inline=True
            )
            embed.set_footer(text="⚠️ Keep your password safe! You'll need it to open the PDF.")
            
            # Send the protected PDF
            await interaction.followup.send(
                embed=embed,
                file=discord.File(output_path, filename=output_filename)
            )
            
            # Send password in a separate ephemeral message for security
            password_embed = discord.Embed(
                title="🔑 Your PDF Password",
                description=f"```\n{password}\n```",
                color=0xff9900
            )
            password_embed.add_field(
                name="⚠️ Security Notice",
                value="• This password is shown only to you\n• Save it securely before closing this message\n• This message will disappear when you restart Discord",
                inline=False
            )
            
            await interaction.followup.send(embed=password_embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error protecting PDF: {e}")
            error_msg = "❌ An error occurred while protecting the PDF."
            
            # Provide more specific error messages
            if "corrupted" in str(e).lower():
                error_msg += " The PDF file appears to be corrupted."
            elif "permission" in str(e).lower():
                error_msg += " Permission denied - the PDF might have restrictions."
            elif "memory" in str(e).lower():
                error_msg += " The PDF is too large to process."
            
            await interaction.followup.send(error_msg, ephemeral=True)
            
        finally:
            # Clean up temporary files
            if input_path or output_path:
                await self._cleanup_files(
                    *(path for path in [input_path, output_path] if path is not None)
                )

    @app_commands.command(
        name="generate_password", 
        description="Generate a secure password"
    )
    @app_commands.describe(
        length="Password length (8-32 characters, default: 12)",
        include_symbols="Include special symbols (!@#$%^&*)"
    )
    async def generate_password(
        self, 
        interaction: discord.Interaction,
        length: Optional[int] = 12,
        include_symbols: Optional[bool] = True
    ):
        # Validate password length
        if length < 8 or length > 32:
            await interaction.response.send_message(
                "❌ Password length must be between 8 and 32 characters.",
                ephemeral=True
            )
            return
        
        # Generate password
        if include_symbols:
            password = self._generate_secure_password(length)
        else:
            # Generate without special symbols
            chars = string.ascii_letters + string.digits
            password = ''.join(secrets.choice(chars) for _ in range(length))
        
        # Create embed
        embed = discord.Embed(
            title="🔑 Generated Password",
            description=f"```\n{password}\n```",
            color=0x00ff00
        )
        embed.add_field(
            name="📊 Password Info",
            value=f"• Length: {len(password)} characters\n• Symbols: {'Yes' if include_symbols else 'No'}",
            inline=False
        )
        embed.add_field(
            name="💡 Security Tips",
            value="• Don't share this password\n• Store it in a password manager\n• Use unique passwords for each account",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(PDFPasswordProtector(bot))
