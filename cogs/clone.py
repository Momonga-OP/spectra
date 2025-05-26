import discord
from discord.ext import commands
import logging
import asyncio
from discord import app_commands

# Setup logging
logger = logging.getLogger(__name__)

class CloneFeature(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Server IDs
        self.source_server_id = 1213699457233985587  # Server 1 ID
        self.target_server_id = 1214430768143671377  # Server 2 ID
        # Category and channel IDs
        self.source_category_id = 1213702686822891531
        self.source_channels = {
            1348894829353897984: "alliance•counsel",
            1375693901809057912: "leaders"
        }
        # Dictionary to store mappings between source and target channels
        self.channel_mapping = {}
        
    async def cog_load(self):
        logger.info("CloneFeature cog loaded successfully")
        # Wait for the bot to be fully ready before attempting to clone
        await self.bot.wait_until_ready()
        # Start the automatic setup process
        await self.auto_setup()
        

    
    async def rate_limited_create(self, target_guild, target_category, source_channel, ctx):
        """Create a channel with rate limit handling"""
        try:
            # Create the channel in target guild
            target_channel = await target_guild.create_text_channel(
                name=source_channel.name,
                category=target_category,
                topic=source_channel.topic if hasattr(source_channel, 'topic') else None,
                slowmode_delay=source_channel.slowmode_delay if hasattr(source_channel, 'slowmode_delay') else 0
            )
            
            # Add delay to avoid rate limits
            await asyncio.sleep(1.5)
            
            return target_channel
        except discord.errors.HTTPException as e:
            if e.status == 429:  # Rate limited
                retry_after = e.retry_after
                await ctx.send(f"Rate limited by Discord API. Waiting {retry_after:.2f} seconds before retrying...")
                await asyncio.sleep(retry_after)
                return await self.rate_limited_create(target_guild, target_category, source_channel, ctx)
            else:
                raise
    
    async def auto_setup(self):
        """Automatically setup the category cloning without requiring a command"""
        logger.info("Starting automatic category cloning setup...")
        try:
            await self.clone_category_internal()
            logger.info("Automatic category cloning setup completed successfully")
        except Exception as e:
            logger.exception(f"Error in automatic setup: {e}")
    
    @commands.command(name="clone_category")
    @commands.has_permissions(administrator=True)
    async def clone_category(self, ctx):
        logger.info(f"Clone category command invoked by {ctx.author} in {ctx.guild.name if ctx.guild else 'DM'}")
        """Clone a category and its channels from source server to target server"""
        try:
            await self.clone_category_internal(ctx)
        except Exception as e:
            logger.exception(f"Error in clone_category command: {e}")
            if ctx:
                await ctx.send(f"An error occurred: {str(e)}")
    
    async def clone_category_internal(self, ctx=None):
        """Internal method to handle the category cloning logic"""
        try:
            # Get the source guild and category
            source_guild = self.bot.get_guild(self.source_server_id)
            if not source_guild:
                error_msg = f"Source guild with ID {self.source_server_id} not found!"
                logger.error(error_msg)
                if ctx:
                    await ctx.send(error_msg)
                return
                
            source_category = discord.utils.get(source_guild.categories, id=self.source_category_id)
            if not source_category:
                error_msg = "Source category not found!"
                logger.error(error_msg)
                if ctx:
                    await ctx.send(error_msg)
                return
                
            # Get the target guild
            target_guild = self.bot.get_guild(self.target_server_id)
            if not target_guild:
                error_msg = f"Target guild with ID {self.target_server_id} not found!"
                logger.error(error_msg)
                if ctx:
                    await ctx.send(error_msg)
                return
                
            # Check if bot has permissions in target guild
            bot_member = target_guild.get_member(self.bot.user.id)
            if not bot_member or not bot_member.guild_permissions.administrator:
                error_msg = "I need administrator permissions in the target guild!"
                logger.error(error_msg)
                if ctx:
                    await ctx.send(error_msg)
                return
            
            # Check if category already exists in target guild
            existing_category = discord.utils.get(target_guild.categories, name=source_category.name)
            if existing_category:
                target_category = existing_category
                msg = f"Using existing category '{source_category.name}' in target guild."
                logger.info(msg)
                if ctx:
                    await ctx.send(msg)
            else:
                # Create the category in the target guild with rate limit handling
                try:
                    target_category = await target_guild.create_category(source_category.name)
                    await asyncio.sleep(1.5)  # Add delay to avoid rate limits
                    msg = f"Created category '{source_category.name}' in target guild."
                    logger.info(msg)
                    if ctx:
                        await ctx.send(msg)
                except discord.errors.HTTPException as e:
                    if e.status == 429:  # Rate limited
                        retry_after = e.retry_after
                        msg = f"Rate limited by Discord API. Waiting {retry_after:.2f} seconds before retrying..."
                        logger.warning(msg)
                        if ctx:
                            await ctx.send(msg)
                        await asyncio.sleep(retry_after)
                        target_category = await target_guild.create_category(source_category.name)
                    else:
                        raise
            
            # Clone each channel in the category
            for channel_id, channel_name in self.source_channels.items():
                source_channel = source_guild.get_channel(channel_id)
                
                if source_channel:
                    # Check if we already have a mapping for this channel
                    if channel_id in self.channel_mapping:
                        target_channel_id = self.channel_mapping[channel_id]
                        target_channel = self.bot.get_channel(target_channel_id)
                        
                        if target_channel:
                            msg = f"Channel mapping for '{source_channel.name}' already exists."
                            logger.info(msg)
                            if ctx:
                                await ctx.send(msg)
                            continue
                    
                    # Check if a channel with the same name already exists in the target category
                    existing_channel = discord.utils.get(target_category.text_channels, name=source_channel.name)
                    if existing_channel:
                        target_channel = existing_channel
                        msg = f"Using existing channel '{source_channel.name}' in target guild."
                        logger.info(msg)
                        if ctx:
                            await ctx.send(msg)
                    else:
                        # Create the channel with rate limit handling
                        target_channel = await self.rate_limited_create(target_guild, target_category, source_channel, ctx)
                        msg = f"Created channel '{source_channel.name}' in target guild."
                        logger.info(msg)
                        if ctx:
                            await ctx.send(msg)
                    
                    # Store the mapping between source and target channels
                    self.channel_mapping[source_channel.id] = target_channel.id
                else:
                    msg = f"Source channel with ID {channel_id} not found!"
                    logger.warning(msg)
                    if ctx:
                        await ctx.send(msg)
            
            msg = "Category cloning complete! Messages will now be mirrored between the channels."
            logger.info(msg)
            if ctx:
                await ctx.send(msg)
            
        except Exception as e:
            logger.exception("Error cloning category")
            if ctx:
                await ctx.send(f"An error occurred: {str(e)}")
    
    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore messages from bots to prevent loops
        if message.author.bot:
            return
            
        # Check if the message is in one of our source channels
        if message.channel.id in self.channel_mapping:
            try:
                # Get the target channel
                target_channel_id = self.channel_mapping[message.channel.id]
                target_channel = self.bot.get_channel(target_channel_id)
                
                if not target_channel:
                    logger.error(f"Target channel with ID {target_channel_id} not found!")
                    return
                
                # Create an embed for the mirrored message
                embed = discord.Embed(
                    description=message.content,
                    color=discord.Color.blue(),
                    timestamp=message.created_at
                )
                
                # Add author information
                embed.set_author(
                    name=message.author.display_name,
                    icon_url=message.author.avatar.url if message.author.avatar else None
                )
                
                # Handle attachments
                if message.attachments:
                    attachment = message.attachments[0]
                    if attachment.content_type and attachment.content_type.startswith('image/'):
                        embed.set_image(url=attachment.url)
                    else:
                        embed.add_field(name="Attachment", value=f"[{attachment.filename}]({attachment.url})")
                
                # Send the mirrored message with rate limit handling
                try:
                    await target_channel.send(embed=embed)
                except discord.errors.HTTPException as e:
                    if e.status == 429:  # Rate limited
                        retry_after = e.retry_after
                        logger.warning(f"Rate limited when sending message. Waiting {retry_after:.2f} seconds")
                        await asyncio.sleep(retry_after)
                        await target_channel.send(embed=embed)
                    else:
                        raise
                
            except Exception as e:
                logger.exception("Error mirroring message")
    
    @commands.command(name="clonesetup")
    @commands.has_permissions(administrator=True)
    async def setup_clone(self, ctx):
        """Setup the category cloning and message mirroring between the configured servers"""
        logger.info(f"Clone setup command invoked by {ctx.author} in {ctx.guild.name if ctx.guild else 'DM'}")
        await self.clone_category(ctx)
    
    @commands.command(name="list_mappings")
    @commands.has_permissions(administrator=True)
    async def list_mappings(self, ctx):
        """List all channel mappings"""
        if not self.channel_mapping:
            await ctx.send("No channel mappings have been created yet.")
            return
            
        mappings = []
        for source_id, target_id in self.channel_mapping.items():
            source_channel = self.bot.get_channel(source_id)
            target_channel = self.bot.get_channel(target_id)
            
            source_name = source_channel.name if source_channel else f"Unknown ({source_id})"
            target_name = target_channel.name if target_channel else f"Unknown ({target_id})"
            
            mappings.append(f"• {source_name} → {target_name}")
        
        await ctx.send("**Channel Mappings:**\n" + "\n".join(mappings))
    
    @commands.command(name="clear_mappings")
    @commands.has_permissions(administrator=True)
    async def clear_mappings(self, ctx):
        """Clear all channel mappings"""
        self.channel_mapping = {}
        await ctx.send("All channel mappings have been cleared.")

async def setup(bot):
    try:
        await bot.add_cog(CloneFeature(bot))
        logger.info("CloneFeature cog added successfully")
    except Exception as e:
        logger.exception(f"Error adding CloneFeature cog: {e}")
