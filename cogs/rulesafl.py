import discord
from discord.ext import commands
from discord import app_commands
import os
import logging

logger = logging.getLogger(__name__)

class RulesAFL(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Language role IDs
        self.language_roles = {
            'EN': 1387997877854273547,
            'ES': 1387997802176577616,
            'FR': 1387997922943041688
        }
        
        # File paths for rules
        self.rules_files = {
            'EN': './rules/Rules and Regulations EN (Formatted).txt',
            'ES': './rules/Rules and Regulations ES (Formatted).txt',
            'FR': './rules/Rules and Regulations FR (Formatted).txt'
        }
        
        # Language texts - must be defined BEFORE initializing views
        self.language_texts = {
            'EN': {
                'welcome_title': '🌍 Welcome to the Alliance Server!',
                'choose_language': 'Please choose your preferred language:',
                'rules_title': '📋 Server Rules & Regulations',
                'agree_button': 'I Agree to the Rules',
                'name_modal_title': 'Enter Your In-Game Name',
                'name_input_label': 'In-Game Name',
                'name_input_placeholder': 'Enter your in-game name here...',
                'verification_complete': '✅ Verification Complete!',
                'welcome_message': 'Welcome to the server! You have been verified and assigned the English role.',
                'error_reading_rules': '❌ Error reading rules file. Please contact an administrator.',
                'verification_failed': '❌ Verification failed. Please try again or contact an administrator.'
            },
            'ES': {
                'welcome_title': '🌍 ¡Bienvenido al Servidor de la Alianza!',
                'choose_language': 'Por favor, elige tu idioma preferido:',
                'rules_title': '📋 Reglas y Regulaciones del Servidor',
                'agree_button': 'Acepto las Reglas',
                'name_modal_title': 'Ingresa tu Nombre en el Juego',
                'name_input_label': 'Nombre en el Juego',
                'name_input_placeholder': 'Ingresa tu nombre en el juego aquí...',
                'verification_complete': '✅ ¡Verificación Completa!',
                'welcome_message': '¡Bienvenido al servidor! Has sido verificado y se te ha asignado el rol en español.',
                'error_reading_rules': '❌ Error al leer el archivo de reglas. Por favor contacta a un administrador.',
                'verification_failed': '❌ La verificación falló. Por favor intenta de nuevo o contacta a un administrador.'
            },
            'FR': {
                'welcome_title': '🌍 Bienvenue sur le Serveur de l\'Alliance!',
                'choose_language': 'Veuillez choisir votre langue préférée:',
                'rules_title': '📋 Règles et Règlements du Serveur',
                'agree_button': 'J\'accepte les Règles',
                'name_modal_title': 'Entrez votre Nom de Jeu',
                'name_input_label': 'Nom de Jeu',
                'name_input_placeholder': 'Entrez votre nom de jeu ici...',
                'verification_complete': '✅ Vérification Terminée!',
                'welcome_message': 'Bienvenue sur le serveur! Vous avez été vérifié et le rôle français vous a été attribué.',
                'error_reading_rules': '❌ Erreur lors de la lecture du fichier de règles. Veuillez contacter un administrateur.',
                'verification_failed': '❌ La vérification a échoué. Veuillez réessayer ou contacter un administrateur.'
            }
        }

        # Register persistent views AFTER all attributes are initialized
        self.bot.add_view(PersistentLanguageSelectionView(self))
        self.bot.add_view(PersistentRulesAgreementView(self, 'EN'))
        self.bot.add_view(PersistentRulesAgreementView(self, 'ES'))
        self.bot.add_view(PersistentRulesAgreementView(self, 'FR'))

    def read_rules_file(self, language):
        """Read rules from the specified language file"""
        try:
            file_path = self.rules_files[language]
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as file:
                    return file.read()
            else:
                logger.error(f"Rules file not found: {file_path}")
                return None
        except Exception as e:
            logger.error(f"Error reading rules file for {language}: {e}")
            return None

    @commands.hybrid_command(name="setup_verification", description="Setup language verification buttons")
    @app_commands.default_permissions(administrator=True)
    async def setup_verification(self, ctx):
        """Slash command to setup the verification buttons in a channel"""
        try:
            # Create persistent language selection view
            view = PersistentLanguageSelectionView(self)
            
            # Create embed for language selection
            embed = discord.Embed(
                title="🌍 Welcome! | ¡Bienvenido! | Bienvenue!",
                description="Please choose your preferred language to continue:\n"
                           "Por favor, elige tu idioma preferido para continuar:\n"
                           "Veuillez choisir votre langue préférée pour continuer:",
                color=0x00ff00
            )
            
            # Send the persistent message in the channel
            await ctx.send(embed=embed, view=view)
            
            if isinstance(ctx, discord.Interaction):
                await ctx.response.send_message("Verification setup complete!", ephemeral=True)
            else:
                await ctx.reply("Verification setup complete!", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in setup_verification: {e}")
            if isinstance(ctx, discord.Interaction):
                await ctx.response.send_message("An error occurred while setting up verification.", ephemeral=True)
            else:
                await ctx.reply("An error occurred while setting up verification.", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Send language selection message when a new member joins"""
        try:
            # Create language selection view
            view = LanguageSelectionView(self)
            
            # Create embed for language selection
            embed = discord.Embed(
                title="🌍 Welcome! | ¡Bienvenido! | Bienvenue!",
                description="Please choose your preferred language to continue:\n"
                           "Por favor, elige tu idioma preferido para continuar:\n"
                           "Veuillez choisir votre langue préférée pour continuer:",
                color=0x00ff00
            )
            
            # Send DM to the new member
            await member.send(embed=embed, view=view)
            
        except discord.Forbidden:
            # If DM fails, try to find a welcome channel
            logger.warning(f"Could not send DM to {member}. DMs might be disabled.")
        except Exception as e:
            logger.error(f"Error in on_member_join: {e}")

class PersistentLanguageSelectionView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=None)  # Persistent view, no timeout
        self.cog = cog

    @discord.ui.button(label='English', style=discord.ButtonStyle.primary, emoji='🇺🇸', custom_id='lang_en')
    async def english_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_language_selection(interaction, 'EN')

    @discord.ui.button(label='Español', style=discord.ButtonStyle.primary, emoji='🇪🇸', custom_id='lang_es')
    async def spanish_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_language_selection(interaction, 'ES')

    @discord.ui.button(label='Français', style=discord.ButtonStyle.primary, emoji='🇫🇷', custom_id='lang_fr')
    async def french_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_language_selection(interaction, 'FR')

    async def handle_language_selection(self, interaction: discord.Interaction, language):
        """Handle language selection and show rules"""
        try:
            # Read rules file
            rules_content = self.cog.read_rules_file(language)
            
            if rules_content is None:
                error_msg = self.cog.language_texts[language]['error_reading_rules']
                await interaction.response.send_message(error_msg, ephemeral=True)
                return

            # Create rules embed
            texts = self.cog.language_texts[language]
            embed = discord.Embed(
                title=texts['rules_title'],
                description=rules_content,
                color=0xff9900
            )
            
            # Create persistent agreement view
            agreement_view = PersistentRulesAgreementView(self.cog, language)
            
            await interaction.response.send_message(embed=embed, view=agreement_view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in handle_language_selection: {e}")
            await interaction.response.send_message("An error occurred. Please try again.", ephemeral=True)

class PersistentRulesAgreementView(discord.ui.View):
    def __init__(self, cog, language):
        super().__init__(timeout=None)  # Persistent view, no timeout
        self.cog = cog
        self.language = language
        
        # Set button label and custom_id based on language
        texts = self.cog.language_texts[language]
        self.agree_button.label = texts['agree_button']
        self.agree_button.custom_id = f'agree_{language.lower()}'

    @discord.ui.button(label='I Agree', style=discord.ButtonStyle.success, emoji='✅')
    async def agree_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle rules agreement and show name input modal"""
        try:
            modal = InGameNameModal(self.cog, self.language)
            await interaction.response.send_modal(modal)
        except Exception as e:
            logger.error(f"Error in agree_button: {e}")
            await interaction.response.send_message("An error occurred. Please try again.", ephemeral=True)

class LanguageSelectionView(discord.ui.View):
    def __init__(self, cog):
        super().__init__(timeout=300)  # 5 minute timeout for DM version
        self.cog = cog

    @discord.ui.button(label='English', style=discord.ButtonStyle.primary, emoji='🇺🇸')
    async def english_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_language_selection(interaction, 'EN')

    @discord.ui.button(label='Español', style=discord.ButtonStyle.primary, emoji='🇪🇸')
    async def spanish_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_language_selection(interaction, 'ES')

    @discord.ui.button(label='Français', style=discord.ButtonStyle.primary, emoji='🇫🇷')
    async def french_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_language_selection(interaction, 'FR')

    async def handle_language_selection(self, interaction: discord.Interaction, language):
        """Handle language selection and show rules"""
        try:
            # Read rules file
            rules_content = self.cog.read_rules_file(language)
            
            if rules_content is None:
                error_msg = self.cog.language_texts[language]['error_reading_rules']
                await interaction.response.send_message(error_msg, ephemeral=True)
                return

            # Create rules embed
            texts = self.cog.language_texts[language]
            embed = discord.Embed(
                title=texts['rules_title'],
                description=rules_content,
                color=0xff9900
            )
            
            # Create agreement view (non-persistent for DM)
            agreement_view = RulesAgreementView(self.cog, language)
            
            await interaction.response.send_message(embed=embed, view=agreement_view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in handle_language_selection: {e}")
            await interaction.response.send_message("An error occurred. Please try again.", ephemeral=True)

class RulesAgreementView(discord.ui.View):
    def __init__(self, cog, language):
        super().__init__(timeout=300)  # 5 minute timeout for DM version
        self.cog = cog
        self.language = language
        
        # Set button label based on language
        texts = self.cog.language_texts[language]
        self.agree_button.label = texts['agree_button']

    @discord.ui.button(label='I Agree', style=discord.ButtonStyle.success, emoji='✅')
    async def agree_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle rules agreement and show name input modal"""
        try:
            modal = InGameNameModal(self.cog, self.language)
            await interaction.response.send_modal(modal)
        except Exception as e:
            logger.error(f"Error in agree_button: {e}")
            await interaction.response.send_message("An error occurred. Please try again.", ephemeral=True)

class InGameNameModal(discord.ui.Modal):
    def __init__(self, cog, language):
        self.cog = cog
        self.language = language
        texts = self.cog.language_texts[language]
        
        super().__init__(title=texts['name_modal_title'])
        
        # Add text input for in-game name
        self.name_input = discord.ui.TextInput(
            label=texts['name_input_label'],
            placeholder=texts['name_input_placeholder'],
            required=True,
            max_length=32
        )
        self.add_item(self.name_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle name submission and complete verification"""
        try:
            ingame_name = self.name_input.value.strip()
            
            if not ingame_name:
                await interaction.response.send_message("Please enter a valid name.", ephemeral=True)
                return

            # Get the member object
            member = interaction.user
            guild = interaction.guild
            
            if guild is None:
                guild = discord.utils.get(self.cog.bot.guilds, id=interaction.guild_id) if interaction.guild_id else None
                if guild:
                    member = guild.get_member(interaction.user.id)
            
            if member and guild:
                # Change nickname to in-game name
                try:
                    await member.edit(nick=ingame_name)
                except discord.Forbidden:
                    logger.warning(f"Could not change nickname for {member}")
                
                # Assign language role
                role_id = self.cog.language_roles[self.language]
                role = guild.get_role(role_id)
                
                if role:
                    await member.add_roles(role)
                else:
                    logger.error(f"Could not find role with ID {role_id}")
                
                # Send completion message
                texts = self.cog.language_texts[self.language]
                embed = discord.Embed(
                    title=texts['verification_complete'],
                    description=texts['welcome_message'],
                    color=0x00ff00
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            else:
                texts = self.cog.language_texts[self.language]
                await interaction.response.send_message(texts['verification_failed'], ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error in on_submit: {e}")
            texts = self.cog.language_texts[self.language]
            await interaction.response.send_message(texts['verification_failed'], ephemeral=True)

async def setup(bot):
    await bot.add_cog(RulesAFL(bot))
