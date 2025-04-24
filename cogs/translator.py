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

        # Store active translations messages for cleanup
        self.active_translations = {}

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
        
        # Skip empty messages or embeds without text
        if not original_text:
            await channel.send(f"{user.mention}, that message doesn't contain text that can be translated.", delete_after=10)
            return

        try:
            # Perform translation
            translation = self.translator.translate(original_text, dest=language_code)
            translated_text = translation.text
            source_lang = LANGUAGES.get(translation.src, translation.src).capitalize()
            target_lang = LANGUAGES.get(language_code, language_code).capitalize()
            
            # Create embed for the translation result
            embed = discord.Embed(
                title="Translation Result",
                description=f"Translation from {reaction.message.author.mention}'s message:",
                color=discord.Color.blue()
            )
            embed.add_field(name="Original Text", value=f"```{original_text}```", inline=False)
            embed.add_field(name="Translated Text", value=f"```{translated_text}```", inline=False)
            embed.add_field(name="Languages", value=f"**From:** {source_lang}\n**To:** {target_lang}", inline=False)
            embed.set_footer(text="This translation will be deleted in 10 minutes")
            
            # Add who requested it
            embed.set_author(
                name=f"Requested by {user.display_name}", 
                icon_url=user.display_avatar.url if hasattr(user, 'display_avatar') else None
            )
            
            # Send in channel where everyone (including requester) can see it
            translation_msg = await channel.send(
                content=f"{user.mention}, here's your translation:",
                embed=embed
            )
            
            self.active_translations[translation_msg.id] = translation_msg
            
            # Schedule deletion after 10 minutes
            self.bot.loop.create_task(self.delete_after_delay(translation_msg, 600))
            
            # Add confirmation reaction
            try:
                await reaction.message.add_reaction("✅")
            except discord.Forbidden:
                pass
                
        except Exception as e:
            print(f"Translation failed: {e}")
            await channel.send(
                f"{user.mention}, an error occurred while translating the message. Please try again later.",
                delete_after=15
            )

    @commands.command()
    async def translate(self, ctx, lang: str, *, text=None):
        """
        Translate text or reply to a message to translate it.
        Usage: !translate [language_code] [text]
        Example: !translate es Hello, how are you?
        Or reply to a message with: !translate es
        """
        # Check if valid language code
        if lang not in LANGUAGES:
            language_list = ", ".join([f"`{code}` ({name.capitalize()})" for code, name in list(LANGUAGES.items())[:10]])
            await ctx.send(f"Invalid language code. Examples of valid codes: {language_list}...")
            return
            
        # Get text to translate (either from command or from replied message)
        original_text = text
        if not original_text and ctx.message.reference:
            try:
                referenced_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                original_text = referenced_msg.content
            except discord.NotFound:
                await ctx.send("Could not find the referenced message.")
                return
                
        if not original_text:
            await ctx.send("Please provide text to translate or reply to a message you want to translate.")
            return
            
        try:
            # Perform translation
            translation = self.translator.translate(original_text, dest=lang)
            translated_text = translation.text
            source_lang = LANGUAGES.get(translation.src, translation.src).capitalize()
            target_lang = LANGUAGES.get(lang, lang).capitalize()
            
            # Create embed for the translation result
            embed = discord.Embed(
                title="Translation Result",
                description=f"Translation requested by {ctx.author.mention}:",
                color=discord.Color.blue()
            )
            embed.add_field(name="Original Text", value=f"```{original_text}```", inline=False)
            embed.add_field(name="Translated Text", value=f"```{translated_text}```", inline=False)
            embed.add_field(name="Languages", value=f"**From:** {source_lang}\n**To:** {target_lang}", inline=False)
            embed.set_footer(text="This translation will be deleted in 10 minutes")
            
            # Set author info
            embed.set_author(
                name=ctx.author.display_name, 
                icon_url=ctx.author.display_avatar.url if hasattr(ctx.author, 'display_avatar') else None
            )
            
            # Send the translation and schedule deletion
            translation_msg = await ctx.send(embed=embed)
            self.active_translations[translation_msg.id] = translation_msg
            
            # Schedule deletion after 10 minutes
            self.bot.loop.create_task(self.delete_after_delay(translation_msg, 600))
            
            # Try to delete the command message to keep chat clean
            try:
                await ctx.message.delete()
            except discord.Forbidden:
                pass
                
        except Exception as e:
            print(f"Translation failed: {e}")
            await ctx.send("An error occurred while translating the message. Please try again later.")

    @commands.command()
    async def translate_message(self, ctx, message_id: int, lang: str):
        """Translate an older message given its ID and target language."""
        # Check if valid language code
        if lang not in LANGUAGES:
            language_list = ", ".join([f"`{code}` ({name.capitalize()})" for code, name in list(LANGUAGES.items())[:10]])
            await ctx.send(f"Invalid language code. Examples of valid codes: {language_list}...")
            return
            
        try:
            message = await ctx.channel.fetch_message(message_id)
            original_text = message.content.strip()

            if not original_text:
                await ctx.send("The specified message is empty or non-text.")
                return

            translation = self.translator.translate(original_text, dest=lang)
            translated_text = translation.text
            source_lang = LANGUAGES.get(translation.src, translation.src).capitalize()
            target_lang = LANGUAGES.get(lang, lang).capitalize()

            embed = discord.Embed(
                title="Translation Result",
                description=f"Translation of message from {message.author.mention}:",
                color=discord.Color.green()
            )
            embed.add_field(name="Original Text", value=f"```{original_text}```", inline=False)
            embed.add_field(name="Translated Text", value=f"```{translated_text}```", inline=False)
            embed.add_field(name="Languages", value=f"**From:** {source_lang}\n**To:** {target_lang}", inline=False)
            
            # Set author info
            embed.set_author(
                name=ctx.author.display_name, 
                icon_url=ctx.author.display_avatar.url if hasattr(ctx.author, 'display_avatar') else None
            )
            
            embed.set_footer(text="This translation will be deleted in 10 minutes")

            translation_msg = await ctx.send(embed=embed)
            self.active_translations[translation_msg.id] = translation_msg
            
            # Schedule deletion after 10 minutes
            self.bot.loop.create_task(self.delete_after_delay(translation_msg, 600))

        except discord.NotFound:
            await ctx.send("Message not found. Make sure the message ID is correct and in this channel.")
        except Exception as e:
            print(f"Translation failed: {e}")
            await ctx.send("An error occurred while translating the message. Please try again later.")

    @commands.command()
    async def languages(self, ctx):
        """Display a list of available language codes and their flag emoji"""
        language_info = []
        for emoji, code in self.LANGUAGE_MAP.items():
            language_name = LANGUAGES.get(code, code).capitalize()
            language_info.append(f"{emoji} - `{code}` ({language_name})")
        
        embed = discord.Embed(
            title="Available Translation Languages",
            description="React to messages with these flags to translate them:",
            color=discord.Color.blue()
        )
        
        # Split into groups of 6 to keep fields manageable
        chunks = [language_info[i:i+6] for i in range(0, len(language_info), 6)]
        for i, chunk in enumerate(chunks):
            embed.add_field(
                name=f"Languages {i+1}" if i > 0 else "Languages",
                value="\n".join(chunk),
                inline=True
            )
            
        embed.add_field(
            name="Command Usage",
            value=(
                "**React with flag:** Translate message to that language\n"
                "**!translate [lang] [text]:** Translate text\n"
                "**!translate [lang]:** Reply to translate a message\n"
                "**!translate_message [message_id] [lang]:** Translate older message\n"
                "**!languages:** Show this list"
            ),
            inline=False
        )
        
        await ctx.send(embed=embed)

    async def delete_after_delay(self, message, delay_seconds):
        """Delete a message after a specified delay"""
        await asyncio.sleep(delay_seconds)
        try:
            await message.delete()
            # Remove from active translations if it's there
            if hasattr(message, 'id') and message.id in self.active_translations:
                del self.active_translations[message.id]
        except (discord.NotFound, discord.Forbidden):
            pass  # Message already deleted or no permission

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """Clean up stored messages when channels are deleted"""
        # Remove any stored messages from this channel
        to_remove = []
        for msg_id, msg in self.active_translations.items():
            if msg.channel.id == channel.id:
                to_remove.append(msg_id)
                
        for msg_id in to_remove:
            del self.active_translations[msg_id]

async def setup(bot):
    await bot.add_cog(TranslatorCog(bot))
