# translator.py

import discord
from discord.ext import commands
from googletrans import Translator, LANGUAGES
import asyncio

class TranslatorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.translator = Translator()
        
        # Initialize with test translation
        try:
            test_translation = self.translator.translate("Hello", dest="es")
            print(f"Translator initialized successfully. Test translation: 'Hello' -> '{test_translation.text}'")
        except Exception as e:
            print(f"Error initializing Translator: {e}")

        # Language map for reactions
        self.LANGUAGE_MAP = {
            "🇺🇸": "en",  # English
            "🇫🇷": "fr",  # French
            "🇪🇸": "es",  # Spanish
            "🇦🇪": "ar",  # Arabic
            "🇩🇪": "de",  # German
            "🇮🇹": "it",  # Italian
            "🇯🇵": "ja",  # Japanese
            "🇨🇳": "zh-cn",  # Chinese (Simplified)
            "🇷🇺": "ru",  # Russian
            "🇵🇹": "pt",  # Portuguese
            "🇰🇷": "ko",  # Korean
            "🇳🇱": "nl",  # Dutch
        }

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle translation requests via emoji reactions"""
        # Ignore bot reactions
        if user.bot:
            return

        # Check permissions
        channel = reaction.message.channel
        bot_permissions = channel.permissions_for(channel.guild.me)
        if not (bot_permissions.read_message_history and bot_permissions.send_messages):
            return

        emoji_used = str(reaction.emoji)
        language_code = self.LANGUAGE_MAP.get(emoji_used)
        
        # If not a translation emoji, ignore
        if not language_code:
            return

        original_text = reaction.message.content.strip()
        
        # Skip empty messages
        if not original_text:
            return

        try:
            # Perform translation
            translation = self.translator.translate(original_text, dest=language_code)
            translated_text = translation.text
            
            # Send plain text translation
            translation_msg = await channel.send(translated_text)
            
            # Schedule deletion after 10 minutes (600 seconds)
            self.bot.loop.create_task(self.delete_after_delay(translation_msg, 600))
            
            # Add confirmation reaction
            try:
                await reaction.message.add_reaction("✅")
            except discord.Forbidden:
                pass
                
        except Exception as e:
            print(f"Translation failed: {e}")

    async def delete_after_delay(self, message, delay_seconds):
        """Delete a message after a specified delay"""
        await asyncio.sleep(delay_seconds)
        try:
            await message.delete()
        except (discord.NotFound, discord.Forbidden):
            pass  # Message already deleted or no permission

async def setup(bot):
    await bot.add_cog(TranslatorCog(bot))
