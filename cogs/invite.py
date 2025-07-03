import discord
from discord.ext import commands

class MultiServerInviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Configuration for multiple servers
        self.server_configs = {
            1214430768143671377: {  # Server 1
                'notification_channel_id': 1214430770962239492,
                'invites': {},
                'member_inviter_map': {}  # Track who invited each member
            },
            1213699457233985587: {  # Server 2
                'notification_channel_id': 1376299601358885066,
                'invites': {},
                'member_inviter_map': {}  # Track who invited each member
            },
            1363616633951748270: {  # Server 3
                'notification_channel_id': 1390328355458383993,
                'invites': {},
                'member_inviter_map': {}  # Track who invited each member
            }
        }

    async def fetch_invites_for_guild(self, guild_id):
        """Fetch invites for a specific guild"""
        guild = self.bot.get_guild(guild_id)
        if guild and guild_id in self.server_configs:
            try:
                invites = await guild.invites()
                self.server_configs[guild_id]['invites'] = {invite.code: invite for invite in invites}
                print(f"Fetched {len(invites)} invites for guild {guild_id}")
            except Exception as e:
                print(f"Error fetching invites for guild {guild_id}: {e}")

    async def fetch_all_invites(self):
        """Fetch invites for all configured guilds"""
        for guild_id in self.server_configs.keys():
            await self.fetch_invites_for_guild(guild_id)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.fetch_all_invites()
        print(f"Multi-server invite tracker is ready and monitoring {len(self.server_configs)} guilds.")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild_id = member.guild.id
        
        # Check if this guild is being tracked
        if guild_id not in self.server_configs:
            return

        guild = member.guild
        config = self.server_configs[guild_id]
        notification_channel = guild.get_channel(config['notification_channel_id'])

        try:
            new_invites = await guild.invites()
            inviter_found = None
            invite_code_used = None
            
            # Find which invite was used
            for invite in new_invites:
                if invite.code in config['invites']:
                    if invite.uses > config['invites'][invite.code].uses:
                        inviter_found = invite.inviter
                        invite_code_used = invite.code
                        # Store who invited this member
                        config['member_inviter_map'][member.id] = {
                            'inviter_id': inviter_found.id if inviter_found else None,
                            'inviter_name': inviter_found.display_name if inviter_found else 'Unknown',
                            'invite_code': invite_code_used,
                            'joined_at': member.joined_at
                        }
                        break
            
            # Send organized join notification
            if notification_channel:
                if inviter_found and invite_code_used:
                    embed = discord.Embed(
                        title="Member Joined",
                        color=0x00ff00,  # Green color
                        timestamp=discord.utils.utcnow()
                    )
                    embed.add_field(
                        name="New Member",
                        value=f"**Name:** {member.display_name}\n**Tag:** {member.name}#{member.discriminator}\n**ID:** {member.id}",
                        inline=True
                    )
                    embed.add_field(
                        name="Invitation Details",
                        value=f"**Invited by:** {inviter_found.display_name}\n**Inviter ID:** {inviter_found.id}\n**Invite Code:** {invite_code_used}",
                        inline=True
                    )
                    embed.add_field(
                        name="Account Information",
                        value=f"**Account Created:** {member.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n**Account Age:** {(discord.utils.utcnow() - member.created_at).days} days",
                        inline=False
                    )
                    await notification_channel.send(embed=embed)
                else:
                    # Fallback for unknown invite source
                    embed = discord.Embed(
                        title="Member Joined",
                        color=0xffaa00,  # Orange color for unknown
                        timestamp=discord.utils.utcnow()
                    )
                    embed.add_field(
                        name="New Member",
                        value=f"**Name:** {member.display_name}\n**Tag:** {member.name}#{member.discriminator}\n**ID:** {member.id}",
                        inline=True
                    )
                    embed.add_field(
                        name="Invitation Details",
                        value="**Source:** Unknown (possibly vanity URL, widget, or other)",
                        inline=True
                    )
                    embed.add_field(
                        name="Account Information",
                        value=f"**Account Created:** {member.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n**Account Age:** {(discord.utils.utcnow() - member.created_at).days} days",
                        inline=False
                    )
                    await notification_channel.send(embed=embed)
            
            # Update stored invites for this guild
            config['invites'] = {invite.code: invite for invite in new_invites}
            
        except Exception as e:
            if notification_channel:
                embed = discord.Embed(
                    title="Invite Tracking Error",
                    description=f"An error occurred while tracking invites: {str(e)}",
                    color=0xff0000,  # Red color
                    timestamp=discord.utils.utcnow()
                )
                await notification_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild_id = member.guild.id
        
        # Check if this guild is being tracked
        if guild_id not in self.server_configs:
            return

        config = self.server_configs[guild_id]
        notification_channel = member.guild.get_channel(config['notification_channel_id'])
        
        if notification_channel:
            # Get inviter information if available
            inviter_info = config['member_inviter_map'].get(member.id)
            
            embed = discord.Embed(
                title="Member Left",
                color=0xff4444,  # Red color
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(
                name="Member Information",
                value=f"**Name:** {member.display_name}\n**Tag:** {member.name}#{member.discriminator}\n**ID:** {member.id}",
                inline=True
            )
            
            if inviter_info:
                # Calculate how long they stayed
                time_in_server = discord.utils.utcnow() - inviter_info['joined_at'] if inviter_info['joined_at'] else None
                time_stayed = f"{time_in_server.days} days, {time_in_server.seconds // 3600} hours" if time_in_server else "Unknown"
                
                embed.add_field(
                    name="Original Invitation",
                    value=f"**Invited by:** {inviter_info['inviter_name']}\n**Inviter ID:** {inviter_info['inviter_id']}\n**Invite Code:** {inviter_info['invite_code']}",
                    inline=True
                )
                embed.add_field(
                    name="Time in Server",
                    value=f"**Duration:** {time_stayed}",
                    inline=False
                )
            else:
                embed.add_field(
                    name="Original Invitation",
                    value="**Source:** Unknown (joined before tracking started)",
                    inline=True
                )
            
            await notification_channel.send(embed=embed)
            
            # Clean up the inviter mapping
            if member.id in config['member_inviter_map']:
                del config['member_inviter_map'][member.id]

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        guild_id = invite.guild.id
        
        # Check if this guild is being tracked
        if guild_id not in self.server_configs:
            return

        config = self.server_configs[guild_id]
        config['invites'][invite.code] = invite

        notification_channel = invite.guild.get_channel(config['notification_channel_id'])
        if notification_channel:
            embed = discord.Embed(
                title="Invite Created",
                color=0x0099ff,  # Blue color
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(
                name="Invite Details",
                value=f"**Code:** {invite.code}\n**Created by:** {invite.inviter.display_name}\n**Creator ID:** {invite.inviter.id}",
                inline=True
            )
            
            embed.add_field(
                name="Settings",
                value=f"**Max Uses:** {'Unlimited' if invite.max_uses == 0 else invite.max_uses}\n**Expires:** {'Never' if invite.max_age == 0 else f'{invite.max_age} seconds'}\n**Channel:** {invite.channel.name}",
                inline=True
            )
            
            await notification_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        guild_id = invite.guild.id
        
        # Check if this guild is being tracked
        if guild_id not in self.server_configs:
            return

        config = self.server_configs[guild_id]
        
        if invite.code in config['invites']:
            del config['invites'][invite.code]

        notification_channel = invite.guild.get_channel(config['notification_channel_id'])
        if notification_channel:
            embed = discord.Embed(
                title="Invite Deleted",
                color=0x666666,  # Gray color
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(
                name="Deleted Invite",
                value=f"**Code:** {invite.code}\n**Total Uses:** {invite.uses}",
                inline=True
            )
            
            await notification_channel.send(embed=embed)

    @commands.command(name='invite_stats')
    @commands.has_permissions(administrator=True)
    async def invite_stats(self, ctx):
        """Show invite statistics for the current server"""
        guild_id = ctx.guild.id
        
        if guild_id not in self.server_configs:
            await ctx.send("This server is not being tracked for invites.")
            return
        
        config = self.server_configs[guild_id]
        invites = config['invites']
        
        if not invites:
            await ctx.send("No invites found for this server.")
            return
        
        embed = discord.Embed(
            title=f"Invite Statistics - {ctx.guild.name}",
            color=0x00ff99,
            timestamp=discord.utils.utcnow()
        )
        
        # Sort invites by usage
        sorted_invites = sorted(invites.items(), key=lambda x: x[1].uses, reverse=True)
        
        for i, (code, invite) in enumerate(sorted_invites[:10]):  # Show top 10
            inviter_name = invite.inviter.display_name if invite.inviter else "Unknown"
            embed.add_field(
                name=f"#{i+1} - Code: {code}",
                value=f"**Inviter:** {inviter_name}\n**Uses:** {invite.uses}\n**Max Uses:** {'Unlimited' if invite.max_uses == 0 else invite.max_uses}",
                inline=True
            )
        
        total_uses = sum(invite.uses for invite in invites.values())
        embed.add_field(
            name="Summary",
            value=f"**Total Invites:** {len(invites)}\n**Total Uses:** {total_uses}\n**Active Members Tracked:** {len(config['member_inviter_map'])}",
            inline=False
        )
        
        await ctx.send(embed=embed)

    @commands.command(name='who_invited')
    @commands.has_permissions(administrator=True)
    async def who_invited(self, ctx, member: discord.Member = None):
        """Check who invited a specific member"""
        if member is None:
            member = ctx.author
        
        guild_id = ctx.guild.id
        
        if guild_id not in self.server_configs:
            await ctx.send("This server is not being tracked for invites.")
            return
        
        config = self.server_configs[guild_id]
        inviter_info = config['member_inviter_map'].get(member.id)
        
        embed = discord.Embed(
            title=f"Invitation Information - {member.display_name}",
            color=0x00aaff,
            timestamp=discord.utils.utcnow()
        )
        
        embed.add_field(
            name="Member",
            value=f"**Name:** {member.display_name}\n**Tag:** {member.name}#{member.discriminator}\n**ID:** {member.id}",
            inline=True
        )
        
        if inviter_info:
            time_in_server = discord.utils.utcnow() - inviter_info['joined_at'] if inviter_info['joined_at'] else None
            time_stayed = f"{time_in_server.days} days, {time_in_server.seconds // 3600} hours" if time_in_server else "Unknown"
            
            embed.add_field(
                name="Invitation Details",
                value=f"**Invited by:** {inviter_info['inviter_name']}\n**Inviter ID:** {inviter_info['inviter_id']}\n**Invite Code:** {inviter_info['invite_code']}\n**Time in Server:** {time_stayed}",
                inline=True
            )
        else:
            embed.add_field(
                name="Invitation Details",
                value="**Status:** No invitation data found\n**Reason:** Member joined before tracking started or through unknown source",
                inline=True
            )
        
        await ctx.send(embed=embed)

async def setup(bot):
    # Remove any existing invite tracker cogs to prevent conflicts
    cogs_to_remove = []
    for cog_name, cog in bot.cogs.items():
        if 'invite' in cog_name.lower() or isinstance(cog, type) and 'InviteTracker' in cog.__class__.__name__:
            cogs_to_remove.append(cog_name)
    
    for cog_name in cogs_to_remove:
        await bot.remove_cog(cog_name)
        print(f"Removed existing cog: {cog_name}")
    
    await bot.add_cog(MultiServerInviteTracker(bot))
    print("MultiServerInviteTracker cog loaded successfully")

async def teardown(bot):
    # Clean up when the cog is unloaded
    if 'MultiServerInviteTracker' in bot.cogs:
        await bot.remove_cog('MultiServerInviteTracker')
