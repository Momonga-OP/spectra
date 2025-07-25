import discord
from discord.ext import commands, tasks
import asyncio
import logging

logger = logging.getLogger(__name__)

class PinSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.server_id = 1217700740949348443
        self.channel_id = 1237390434041462836
        self.pin_message_content = (
            "**Before posting, please follow this:**\n"
            "For better opportunities, include a picture of the item you're selling or buying.\n"
            "If selling Kamas, show a screenshot of the amount in your inventory and list payment methods.\n"
            "If buying Kamas, mention the amount you need and your payment method."
        )
        self.stored_message_id = None  # Store message ID in memory
        self.check_and_pin.start()

    async def cog_load(self):
        """Initialize the pin system when the cog loads"""
        await asyncio.sleep(5)  # Wait a bit for bot to be fully ready
        await self.ensure_pin_message()

    async def ensure_pin_message(self):
        """Ensure the pin message exists and is pinned"""
        try:
            guild = self.bot.get_guild(self.server_id)
            if not guild:
                logger.warning(f"Guild {self.server_id} not found")
                return

            channel = guild.get_channel(self.channel_id)
            if not channel:
                logger.warning(f"Channel {self.channel_id} not found")
                return

            # Check if we have a stored message ID in memory
            if self.stored_message_id:
                # Check if the stored message still exists and is pinned
                if await self.message_exists_and_pinned(channel, self.stored_message_id):
                    logger.info("Pin message already exists and is pinned")
                    return
                else:
                    # Message doesn't exist or isn't pinned, clear memory
                    self.stored_message_id = None
                    logger.info("Cleared non-existent pin message from memory")

            # Check if there's already a pinned message with our content
            pinned_messages = await channel.pins()
            for pinned_msg in pinned_messages:
                if (pinned_msg.author == self.bot.user and 
                    pinned_msg.content.strip() == self.pin_message_content.strip()):
                    # Found existing pin message, store its ID in memory
                    self.stored_message_id = pinned_msg.id
                    logger.info(f"Found existing pin message, stored ID: {pinned_msg.id}")
                    return

            # No valid pin message found, create a new one
            await self.create_and_pin_message(channel)

        except Exception as e:
            logger.exception("Error in ensure_pin_message")

    async def message_exists_and_pinned(self, channel, message_id):
        """Check if a message exists and is pinned"""
        try:
            message = await channel.fetch_message(message_id)
            return message.pinned
        except discord.NotFound:
            return False
        except Exception as e:
            logger.exception(f"Error checking message existence: {e}")
            return False

    async def create_and_pin_message(self, channel):
        """Create and pin a new message"""
        try:
            # Send the message
            message = await channel.send(self.pin_message_content)
            
            # Pin the message
            await message.pin()
            
            # Store the message ID in memory
            self.stored_message_id = message.id
            
            logger.info(f"Created and pinned new message with ID: {message.id}")
            
        except discord.Forbidden:
            logger.error("Bot doesn't have permission to pin messages")
        except Exception as e:
            logger.exception("Failed to create and pin message")

    @tasks.loop(minutes=10)
    async def check_and_pin(self):
        """Periodically check if the pin message is still the last pinned message"""
        try:
            await self.bot.wait_until_ready()
            
            guild = self.bot.get_guild(self.server_id)
            if not guild:
                return

            channel = guild.get_channel(self.channel_id)
            if not channel:
                return

            if not self.stored_message_id:
                await self.ensure_pin_message()
                return

            # Check if our message still exists and is pinned
            if not await self.message_exists_and_pinned(channel, self.stored_message_id):
                logger.info("Pin message no longer exists or isn't pinned, recreating...")
                self.stored_message_id = None
                await self.ensure_pin_message()
                return

            # Check if our message is the most recent pinned message
            pinned_messages = await channel.pins()
            if pinned_messages and pinned_messages[0].id != self.stored_message_id:
                # Our message is not the most recent pin, re-pin it
                try:
                    our_message = await channel.fetch_message(self.stored_message_id)
                    await our_message.unpin()
                    await asyncio.sleep(1)  # Small delay
                    await our_message.pin()
                    logger.info("Re-pinned our message to make it the most recent")
                except Exception as e:
                    logger.exception("Failed to re-pin message")

        except Exception as e:
            logger.exception("Error in check_and_pin task")

    @check_and_pin.before_loop
    async def before_check_and_pin(self):
        """Wait for bot to be ready before starting the loop"""
        await self.bot.wait_until_ready()

    @commands.command(name='force_pin')
    @commands.has_permissions(administrator=True)
    async def force_pin(self, ctx):
        """Force recreate the pin message (Admin only)"""
        if ctx.guild.id != self.server_id:
            await ctx.send("This command can only be used in the designated server.")
            return
            
        try:
            # Clear stored message info from memory
            self.stored_message_id = None
            
            # Recreate pin message
            await self.ensure_pin_message()
            
            await ctx.send("✅ Pin message has been force recreated!")
            
        except Exception as e:
            logger.exception("Error in force_pin command")
            await ctx.send("❌ Failed to recreate pin message.")

    @commands.command(name='pin_status')
    @commands.has_permissions(administrator=True)
    async def pin_status(self, ctx):
        """Check the status of the pin message (Admin only)"""
        if ctx.guild.id != self.server_id:
            await ctx.send("This command can only be used in the designated server.")
            return
            
        try:
            if not self.stored_message_id:
                await ctx.send("❌ No pin message stored in memory.")
                return
                
            channel = ctx.guild.get_channel(self.channel_id)
            if not channel:
                await ctx.send("❌ Target channel not found.")
                return
                
            exists_and_pinned = await self.message_exists_and_pinned(channel, self.stored_message_id)
            
            status_embed = discord.Embed(
                title="Pin Message Status",
                color=discord.Color.green() if exists_and_pinned else discord.Color.red()
            )
            status_embed.add_field(name="Message ID", value=str(self.stored_message_id), inline=True)
            status_embed.add_field(name="Exists & Pinned", value="✅ Yes" if exists_and_pinned else "❌ No", inline=True)
            status_embed.add_field(name="Channel", value=f"<#{self.channel_id}>", inline=True)
            
            await ctx.send(embed=status_embed)
            
        except Exception as e:
            logger.exception("Error in pin_status command")
            await ctx.send("❌ Failed to check pin status.")

    def cog_unload(self):
        """Clean up when cog is unloaded"""
        self.check_and_pin.cancel()

async def setup(bot):
    await bot.add_cog(PinSystem(bot))
