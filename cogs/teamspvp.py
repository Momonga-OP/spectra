import discord
from discord.ext import commands
from discord import app_commands
import json
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class TeamsPVPView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label='Attend the Mass Attack', style=discord.ButtonStyle.primary, custom_id='attend_mass_attack')
    async def attend_mass_attack(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Show user choice buttons
        view = TeamChoiceView(self.bot)
        embed = discord.Embed(
            title="Choose Your Team Option",
            description="Select how you'd like to participate in the mass attack:",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class TeamChoiceView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot

    @discord.ui.button(label='I Have My Own Team', style=discord.ButtonStyle.secondary)
    async def own_team(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self.bot.get_cog('TeamsPVP')
        if cog:
            await cog.create_own_team(interaction)

    @discord.ui.button(label='Autofill Me Into a Team', style=discord.ButtonStyle.success)
    async def autofill_team(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self.bot.get_cog('TeamsPVP')
        if cog:
            await cog.add_to_autofill_queue(interaction)

class ReplaceConfirmView(discord.ui.View):
    def __init__(self, bot, channel):
        super().__init__(timeout=60)
        self.bot = bot
        self.channel = channel

    @discord.ui.button(label='Yes, Replace', style=discord.ButtonStyle.danger)
    async def confirm_replace(self, interaction: discord.Interaction, button: discord.ui.Button):
        cog = self.bot.get_cog('TeamsPVP')
        if cog:
            await cog.post_mass_attack_message(interaction, self.channel, replace=True)

    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.secondary)
    async def cancel_replace(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Operation cancelled.", view=None, embed=None)

class TeamsPVP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.server_id = 1213699457233985587
        self.category_id = 1390730436103245824
        self.signup_channel_id = 1390730750336434336
        self.announcement_channel_id = 1390730829482692650
        self.data_channel_id = None  # Will be set when data channel is found/created
        self.data_message_id = None
        self.next_team_id = 1
        self.autofill_queue = []
        self.max_team_size = 5
        self.team_threads = {}  # Store thread info
        self.active_messages = {}  # Track active mass attack messages per channel
        
    async def cog_load(self):
        """Called when the cog is loaded"""
        await self.setup_data_channel()
        await self.load_data()
        # Remove the auto-setup of main message since we're using slash commands now

    async def setup_data_channel(self):
        """Find or create the data persistence channel"""
        guild = self.bot.get_guild(self.server_id)
        if not guild:
            logger.error(f"Guild {self.server_id} not found")
            return

        # Look for existing data channel
        data_channel = discord.utils.get(guild.channels, name='pvp-data-store')
        
        if not data_channel:
            # Create the data channel
            category = guild.get_channel(self.category_id)
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
            # Add permission for users with Manage Guild
            for role in guild.roles:
                if role.permissions.manage_guild:
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True)
            
            data_channel = await guild.create_text_channel(
                'pvp-data-store',
                category=category,
                overwrites=overwrites,
                topic="Data persistence for PVP teams - Do not delete messages here!"
            )
            logger.info(f"Created data channel: {data_channel.id}")
        
        self.data_channel_id = data_channel.id

    async def load_data(self):
        """Load persistent data from the data channel"""
        if not self.data_channel_id:
            return
        
        channel = self.bot.get_channel(self.data_channel_id)
        if not channel:
            return
        
        try:
            messages = [message async for message in channel.history(limit=10)]
            data_message = None
            
            for message in messages:
                if message.author == self.bot.user and message.content.startswith('```json'):
                    data_message = message
                    break
            
            if data_message:
                self.data_message_id = data_message.id
                # Extract JSON from code block
                content = data_message.content
                json_start = content.find('```json\n') + 8
                json_end = content.find('\n```')
                if json_start > 7 and json_end > json_start:
                    json_str = content[json_start:json_end]
                    data = json.loads(json_str)
                    
                    self.next_team_id = data.get('next_team_id', 1)
                    self.autofill_queue = data.get('autofill_queue', [])
                    self.max_team_size = data.get('max_team_size', 5)
                    self.team_threads = data.get('team_threads', {})
                    self.active_messages = data.get('active_messages', {})
                    
                    logger.info(f"Loaded data: {len(self.autofill_queue)} in queue, next team ID: {self.next_team_id}")
            else:
                # Create initial data message
                await self.save_data()
        except Exception as e:
            logger.exception("Error loading data")

    async def save_data(self):
        """Save persistent data to the data channel"""
        if not self.data_channel_id:
            return
        
        channel = self.bot.get_channel(self.data_channel_id)
        if not channel:
            return
        
        data = {
            'next_team_id': self.next_team_id,
            'autofill_queue': self.autofill_queue,
            'max_team_size': self.max_team_size,
            'team_threads': self.team_threads,
            'active_messages': self.active_messages,
            'last_updated': datetime.now().isoformat()
        }
        
        content = f"```json\n{json.dumps(data, indent=2)}\n```"
        
        try:
            if self.data_message_id:
                try:
                    message = await channel.fetch_message(self.data_message_id)
                    await message.edit(content=content)
                except discord.NotFound:
                    # Message was deleted, create new one
                    message = await channel.send(content)
                    self.data_message_id = message.id
            else:
                message = await channel.send(content)
                self.data_message_id = message.id
        except Exception as e:
            logger.exception("Error saving data")

    @app_commands.command(name="massattack", description="Post the Mass Attack team coordination message.")
    @app_commands.describe(
        channel="The channel to post the message in (defaults to current channel)"
    )
    async def mass_attack_command(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Slash command to post the Mass Attack coordination message"""
        
        # Check permissions
        if not interaction.user.guild_permissions.manage_guild:
            await interaction.response.send_message(
                "❌ You need 'Manage Guild' permission to use this command.", 
                ephemeral=True
            )
            return
        
        target_channel = channel or interaction.channel
        
        # Check if message already exists in this channel
        channel_id = str(target_channel.id)
        if channel_id in self.active_messages:
            # Check if the message still exists
            try:
                message = await target_channel.fetch_message(self.active_messages[channel_id])
                # Message exists, ask for confirmation
                embed = discord.Embed(
                    title="Mass Attack Message Already Exists",
                    description=f"A Mass Attack coordination message already exists in {target_channel.mention}.\n\n"
                               f"Do you want to replace it with a new one?",
                    color=0xff9900
                )
                view = ReplaceConfirmView(self.bot, target_channel)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                return
            except discord.NotFound:
                # Message was deleted, remove from tracking
                del self.active_messages[channel_id]
                await self.save_data()
        
        # Post the message
        await self.post_mass_attack_message(interaction, target_channel)

    async def post_mass_attack_message(self, interaction: discord.Interaction, channel: discord.TextChannel, replace: bool = False):
        """Post the mass attack coordination message"""
        
        # Clean message content without emojis
        content = """**Welcome to the PVP Mass Attack Coordination Hub**

• If you already have a team, you can create a private thread to coordinate with your teammates.
• If you want to be assigned to a team automatically, join the autofill queue.

Click the button below to begin."""
        
        view = TeamsPVPView(self.bot)
        
        try:
            # If replacing, delete the old message first
            if replace:
                channel_id = str(channel.id)
                if channel_id in self.active_messages:
                    try:
                        old_message = await channel.fetch_message(self.active_messages[channel_id])
                        await old_message.delete()
                    except discord.NotFound:
                        pass  # Message was already deleted
            
            # Post the new message
            message = await channel.send(content, view=view)
            
            # Track the message
            self.active_messages[str(channel.id)] = message.id
            await self.save_data()
            
            # Respond to the interaction
            action = "replaced" if replace else "posted"
            response_text = f"✅ Mass Attack coordination message {action} in {channel.mention}"
            
            if interaction.response.is_done():
                await interaction.edit_original_response(content=response_text, view=None, embed=None)
            else:
                await interaction.response.send_message(response_text, ephemeral=True)
                
            logger.info(f"Mass attack message {action} in {channel.name} by {interaction.user}")
            
        except Exception as e:
            logger.exception("Error posting mass attack message")
            error_text = f"❌ Failed to post the Mass Attack message in {channel.mention}"
            
            if interaction.response.is_done():
                await interaction.edit_original_response(content=error_text, view=None, embed=None)
            else:
                await interaction.response.send_message(error_text, ephemeral=True)

    async def create_own_team(self, interaction: discord.Interaction):
        """Create a private team thread for users with their own team"""
        guild = interaction.guild
        channel = guild.get_channel(self.signup_channel_id)
        
        if not channel:
            await interaction.response.send_message("❌ Setup error: Channel not found.", ephemeral=True)
            return
        
        # Create private thread
        thread_name = f"Team {self.next_team_id}"
        
        try:
            thread = await channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.private_thread,
                reason=f"PVP team created by {interaction.user}"
            )
            
            # Add the user to the thread
            await thread.add_user(interaction.user)
            
            # Store thread info
            self.team_threads[str(thread.id)] = {
                'id': thread.id,
                'name': thread_name,
                'creator': interaction.user.id,
                'members': [interaction.user.id],
                'locked': False,
                'created_at': datetime.now().isoformat()
            }
            
            self.next_team_id += 1
            await self.save_data()
            
            # Send instructions to the thread
            embed = discord.Embed(
                title=f"Welcome to {thread_name}!",
                description=f"Hello {interaction.user.mention}! This is your private team coordination thread.\n\n"
                           f"**Instructions:**\n"
                           f"• Tag your teammates here (they'll be given access automatically)\n"
                           f"• Coordinate your strategy and timing\n"
                           f"• Type `!done` when your team is complete to lock the thread\n\n"
                           f"**Current team size:** 1/{self.max_team_size}",
                color=0x00ff00
            )
            await thread.send(embed=embed)
            
            await interaction.response.send_message(f"✅ Created your team thread: {thread.mention}", ephemeral=True)
            
        except Exception as e:
            logger.exception("Error creating team thread")
            await interaction.response.send_message("❌ Failed to create team thread.", ephemeral=True)

    async def add_to_autofill_queue(self, interaction: discord.Interaction):
        """Add user to autofill queue"""
        user_id = interaction.user.id
        
        if user_id in self.autofill_queue:
            await interaction.response.send_message("❌ You're already in the autofill queue!", ephemeral=True)
            return
        
        self.autofill_queue.append(user_id)
        await self.save_data()
        
        queue_position = len(self.autofill_queue)
        needed_for_team = self.max_team_size - ((queue_position - 1) % self.max_team_size)
        
        embed = discord.Embed(
            title="Added to Autofill Queue",
            description=f"You've been added to the autofill queue!\n\n"
                       f"**Queue position:** {queue_position}\n"
                       f"**Players needed for next team:** {needed_for_team}\n\n"
                       f"You'll be notified when a team is ready. Use `!leavequeue` to exit the queue.",
            color=0x00ff00
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Check if we can form a team
        if len(self.autofill_queue) >= self.max_team_size:
            await self.create_autofill_team()

    async def create_autofill_team(self):
        """Create an autofilled team when enough players are queued"""
        if len(self.autofill_queue) < self.max_team_size:
            return
        
        guild = self.bot.get_guild(self.server_id)
        channel = guild.get_channel(self.signup_channel_id)
        
        if not channel:
            logger.error("Signup channel not found for autofill team creation")
            return
        
        # Get team members from queue
        team_members = self.autofill_queue[:self.max_team_size]
        self.autofill_queue = self.autofill_queue[self.max_team_size:]
        
        # Create private thread
        thread_name = f"Team {self.next_team_id}"
        
        try:
            thread = await channel.create_thread(
                name=thread_name,
                type=discord.ChannelType.private_thread,
                reason="Autofilled PVP team"
            )
            
            # Add all members to the thread
            members_added = []
            for user_id in team_members:
                try:
                    user = guild.get_member(user_id)
                    if user:
                        await thread.add_user(user)
                        members_added.append(user_id)
                except Exception as e:
                    logger.exception(f"Error adding user {user_id} to thread")
            
            # Store thread info
            self.team_threads[str(thread.id)] = {
                'id': thread.id,
                'name': thread_name,
                'creator': None,  # Autofilled team
                'members': members_added,
                'locked': False,
                'created_at': datetime.now().isoformat()
            }
            
            self.next_team_id += 1
            await self.save_data()
            
            # Send welcome message to the thread
            member_mentions = [f"<@{user_id}>" for user_id in members_added]
            embed = discord.Embed(
                title=f"Welcome to {thread_name}!",
                description=f"Hello {', '.join(member_mentions)}!\n\n"
                           f"You've been automatically assigned to this team for the mass attack.\n\n"
                           f"**Team size:** {len(members_added)}/{self.max_team_size}\n"
                           f"**Coordinate your strategy and timing here!**",
                color=0x00ff00
            )
            await thread.send(embed=embed)
            
            # Announce in announcement channel
            await self.announce_team_creation(thread_name, len(members_added), autofilled=True)
            
        except Exception as e:
            logger.exception("Error creating autofill team")
            # Add members back to queue if creation failed
            self.autofill_queue = team_members + self.autofill_queue
            await self.save_data()

    async def announce_team_creation(self, team_name, member_count, creator=None, autofilled=False):
        """Announce team creation in the announcement channel"""
        channel = self.bot.get_channel(self.announcement_channel_id)
        if not channel:
            return
        
        if autofilled:
            embed = discord.Embed(
                title="New Autofilled Team Created!",
                description=f"**{team_name}** has been created with {member_count} players.",
                color=0x00ff00,
                timestamp=datetime.now()
            )
        else:
            embed = discord.Embed(
                title="New Team Created!",
                description=f"**{team_name}** has been created by <@{creator}> with {member_count} players.",
                color=0x00ff00,
                timestamp=datetime.now()
            )
        
        await channel.send(embed=embed)

    @commands.command(name='done')
    async def done_team(self, ctx):
        """Mark a team as complete and lock the thread"""
        if not isinstance(ctx.channel, discord.Thread):
            return
        
        thread_id = str(ctx.channel.id)
        if thread_id not in self.team_threads:
            return
        
        team_info = self.team_threads[thread_id]
        
        # Check if user is the creator or has manage guild permission
        if (team_info['creator'] != ctx.author.id and 
            not ctx.author.guild_permissions.manage_guild):
            await ctx.send("❌ Only the team creator or administrators can lock the team.")
            return
        
        # Lock the thread
        await ctx.channel.edit(locked=True)
        team_info['locked'] = True
        await self.save_data()
        
        embed = discord.Embed(
            title="Team Locked!",
            description=f"This team has been locked and is ready for the mass attack.\n"
                       f"**Final team size:** {len(team_info['members'])}/{self.max_team_size}",
            color=0xff9900
        )
        await ctx.send(embed=embed)
        
        # Announce in announcement channel
        await self.announce_team_creation(
            team_info['name'], 
            len(team_info['members']), 
            team_info['creator'], 
            autofilled=team_info['creator'] is None
        )

    @commands.command(name='leavequeue')
    async def leave_queue(self, ctx):
        """Leave the autofill queue"""
        user_id = ctx.author.id
        
        if user_id not in self.autofill_queue:
            await ctx.send("❌ You're not in the autofill queue.")
            return
        
        self.autofill_queue.remove(user_id)
        await self.save_data()
        
        embed = discord.Embed(
            title="Left Autofill Queue",
            description="You've been removed from the autofill queue.",
            color=0xff9900
        )
        await ctx.send(embed=embed, delete_after=10)

    @commands.command(name='setteamsize')
    @commands.has_permissions(manage_guild=True)
    async def set_team_size(self, ctx, size: int):
        """Set the maximum team size"""
        if size < 1 or size > 20:
            await ctx.send("❌ Team size must be between 1 and 20.")
            return
        
        self.max_team_size = size
        await self.save_data()
        
        embed = discord.Embed(
            title="Team Size Updated",
            description=f"Maximum team size set to {size} players.",
            color=0x00ff00
        )
        await ctx.send(embed=embed)

    @commands.command(name='renameteam')
    @commands.has_permissions(manage_guild=True)
    async def rename_team(self, ctx, old_name: str, *, new_name: str):
        """Rename a team thread"""
        guild = ctx.guild
        
        # Find the thread
        thread = None
        for channel in guild.channels:
            if isinstance(channel, discord.Thread) and channel.name == old_name:
                thread = channel
                break
        
        if not thread:
            await ctx.send(f"❌ Thread '{old_name}' not found.")
            return
        
        try:
            await thread.edit(name=new_name)
            
            # Update stored data
            thread_id = str(thread.id)
            if thread_id in self.team_threads:
                self.team_threads[thread_id]['name'] = new_name
                await self.save_data()
            
            embed = discord.Embed(
                title="Team Renamed",
                description=f"Team '{old_name}' has been renamed to '{new_name}'.",
                color=0x00ff00
            )
            await ctx.send(embed=embed)
            
        except Exception as e:
            logger.exception("Error renaming team")
            await ctx.send("❌ Failed to rename the team.")

    @commands.command(name='scheduleevent')
    @commands.has_permissions(manage_guild=True)
    async def schedule_event(self, ctx, datetime_str: str, *, description: str):
        """Schedule a mass attack event"""
        channel = self.bot.get_channel(self.announcement_channel_id)
        if not channel:
            await ctx.send("❌ Announcement channel not found.")
            return
        
        embed = discord.Embed(
            title="Scheduled Mass Attack",
            color=0xff0000
        )
        embed.add_field(name="Time", value=datetime_str, inline=False)
        embed.add_field(name="Description", value=description, inline=False)
        embed.set_footer(text="Scheduled by " + str(ctx.author), icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        embed.timestamp = datetime.now()
        
        await channel.send("@everyone", embed=embed)
        await ctx.send("✅ Event scheduled and announced!")

    @commands.command(name='teamstats')
    @commands.has_permissions(manage_guild=True)
    async def team_stats(self, ctx):
        """Show team statistics"""
        total_teams = len(self.team_threads)
        locked_teams = sum(1 for team in self.team_threads.values() if team['locked'])
        queue_size = len(self.autofill_queue)
        active_messages = len(self.active_messages)
        
        embed = discord.Embed(
            title="Team Statistics",
            color=0x00ff00
        )
        embed.add_field(name="Total Teams", value=total_teams, inline=True)
        embed.add_field(name="Locked Teams", value=locked_teams, inline=True)
        embed.add_field(name="Queue Size", value=queue_size, inline=True)
        embed.add_field(name="Max Team Size", value=self.max_team_size, inline=True)
        embed.add_field(name="Next Team ID", value=self.next_team_id, inline=True)
        embed.add_field(name="Active Messages", value=active_messages, inline=True)
        
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Handle mentions in team threads"""
        if message.author.bot:
            return
        
        if not isinstance(message.channel, discord.Thread):
            return
        
        thread_id = str(message.channel.id)
        if thread_id not in self.team_threads:
            return
        
        team_info = self.team_threads[thread_id]
        if team_info['locked']:
            return
        
        # Check for mentions and add mentioned users to the thread
        for mention in message.mentions:
            if mention.id not in team_info['members']:
                try:
                    await message.channel.add_user(mention)
                    team_info['members'].append(mention.id)
                    await self.save_data()
                    
                    embed = discord.Embed(
                        description=f"✅ {mention.mention} has been added to the team!",
                        color=0x00ff00
                    )
                    await message.channel.send(embed=embed)
                    
                except Exception as e:
                    logger.exception(f"Error adding user {mention.id} to thread")

async def setup(bot):
    await bot.add_cog(TeamsPVP(bot))
