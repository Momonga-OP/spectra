import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image
import os
import imghdr

# Ensure the temp directory exists
if not os.path.exists("temp"):
    os.makedirs("temp")

# Allowed formats
FORMATS = ["JPEG", "JPG", "PNG", "WEBP", "BMP"]

class ImageConverter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="image_converter", description="Convert an image to different formats (JPEG, JPG, PNG, WEBP, BMP).")
    async def image_converter(self, interaction: discord.Interaction, attachment: discord.Attachment):
        # Check if the attachment is an image by its MIME type
        if not attachment.content_type or not attachment.content_type.startswith('image/'):
            await interaction.response.send_message("Please upload an image file.", ephemeral=True)
            return

        await interaction.response.send_message("Please select the format you want to convert to:", ephemeral=True)

        # Create a select menu for formats
        class FormatSelect(discord.ui.Select):
            def __init__(self):
                options = [discord.SelectOption(label=format) for format in FORMATS]
                super().__init__(placeholder="Choose an image format...", min_values=1, max_values=1, options=options)

            async def callback(self, select_interaction: discord.Interaction):
                format = self.values[0]
                await select_interaction.response.send_message("Processing your image...", ephemeral=True)
                
                try:
                    # Download the image
                    file_path = f"temp/{attachment.filename}"
                    await attachment.save(file_path)

                    # Verify it's a valid image file
                    if not imghdr.what(file_path):
                        await select_interaction.followup.send("The uploaded file is not a valid image.", ephemeral=True)
                        os.remove(file_path)  # Clean up
                        return

                    # Open the image
                    img = Image.open(file_path)

                    # Determine output path with safe naming
                    base_name = os.path.basename(file_path).rsplit('.', 1)[0]
                    output_path = f"temp/{base_name}.{format.lower()}"
                    
                    # Save the image in the desired format
                    img.save(output_path, format.upper())

                    # Send the converted image to the user
                    await select_interaction.followup.send(
                        f"Image converted from {os.path.splitext(attachment.filename)[1][1:].upper()} to {format.upper()}:", 
                        file=discord.File(output_path)
                    )

                    # Clean up the files
                    os.remove(file_path)
                    os.remove(output_path)

                except Exception as e:
                    await select_interaction.followup.send(f"An error occurred: {e}", ephemeral=True)
                    # Ensure files are cleaned up even if there's an error
                    for path in [file_path, output_path]:
                        if 'path' in locals() and os.path.exists(path):
                            os.remove(path)

        view = discord.ui.View()
        view.add_item(FormatSelect())
        await interaction.followup.send(view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ImageConverter(bot))
