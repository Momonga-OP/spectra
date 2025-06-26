import discord
from discord.ext import commands
import logging

logger = logging.getLogger(__name__)

class TagCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.first_server_id = 1213699457233985587  # First server ID
        self.second_server_id = 1243943760086171759  # Second server ID
        
    async def get_member_from_first_server(self, user_id):
        """Get member from the first server"""
        first_guild = self.bot.get_guild(self.first_server_id)
        if first_guild:
            return first_guild.get_member(user_id)
        return None
    
    async def create_role_if_not_exists(self, guild, role_name, color=None):
        """Create a role if it doesn't exist, return the role"""
        # Check if role already exists
        existing_role = discord.utils.get(guild.roles, name=role_name)
        if existing_role:
            return existing_role
        
        try:
            # Create new role without any permissions
            new_role = await guild.create_role(
                name=role_name,
                color=color or discord.Color.default(),
                permissions=discord.Permissions.none(),
                reason="Auto-sync role from first server"
            )
            logger.info(f"Created role '{role_name}' in {guild.name}")
            return new_role
        except discord.Forbidden:
            logger.error(f"No permission to create role '{role_name}' in {guild.name}")
            return None
        except Exception as e:
            logger.exception(f"Error creating role '{role_name}': {e}")
            return None
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Handle member joining the second server"""
        # Only process if member joins the second server
        if member.guild.id != self.second_server_id:
            return
        
        logger.info(f"Member {member} joined second server")
        
        # Get the same member from first server
        first_server_member = await self.get_member_from_first_server(member.id)
        
        if not first_server_member:
            logger.info(f"Member {member} not found in first server")
            return
        
        logger.info(f"Found member {first_server_member} in first server, starting sync...")
        
        # Sync roles
        await self.sync_member_roles(member, first_server_member)
        
        # Sync nickname
        await self.sync_member_nickname(member, first_server_member)
    
    async def sync_member_roles(self, second_server_member, first_server_member):
        """Sync roles from first server to second server"""
        second_guild = second_server_member.guild
        roles_to_add = []
        
        # Get all roles from first server member (excluding @everyone)
        first_server_roles = [role for role in first_server_member.roles if role.name != "@everyone"]
        
        for role in first_server_roles:
            # Create or get the role in second server
            new_role = await self.create_role_if_not_exists(
                second_guild, 
                role.name, 
                role.color
            )
            
            if new_role:
                roles_to_add.append(new_role)
        
        # Add all roles to the member
        if roles_to_add:
            try:
                await second_server_member.add_roles(
                    *roles_to_add, 
                    reason="Auto-sync roles from first server"
                )
                role_names = [role.name for role in roles_to_add]
                logger.info(f"Added roles {role_names} to {second_server_member}")
            except discord.Forbidden:
                logger.error(f"No permission to add roles to {second_server_member}")
            except Exception as e:
                logger.exception(f"Error adding roles to {second_server_member}: {e}")
    
    async def sync_member_nickname(self, second_server_member, first_server_member):
        """Sync nickname from first server to second server"""
        first_server_nickname = first_server_member.display_name
        
        # Only change nickname if it's different and not the username
        if (first_server_nickname != first_server_member.name and 
            first_server_nickname != second_server_member.display_name):
            
            try:
                await second_server_member.edit(
                    nick=first_server_nickname,
                    reason="Auto-sync nickname from first server"
                )
                logger.info(f"Changed nickname of {second_server_member} to '{first_server_nickname}'")
            except discord.Forbidden:
                logger.error(f"No permission to change nickname of {second_server_member}")
            except Exception as e:
                logger.exception(f"Error changing nickname of {second_server_member}: {e}")
    
    @commands.command(name='sync_member')
    @commands.has_permissions(administrator=True)
    async def manual_sync_member(self, ctx, member: discord.Member = None):
        """Manually sync a specific member (admin only)"""
        if ctx.guild.id != self.second_server_id:
            await ctx.send("This command can only be used in the second server.")
            return
        
        if member is None:
            member = ctx.author
        
        first_server_member = await self.get_member_from_first_server(member.id)
        
        if not first_server_member:
            await ctx.send(f"{member.mention} is not found in the first server.")
            return
        
        await ctx.send(f"Starting manual sync for {member.mention}...")
        
        # Sync roles and nickname
        await self.sync_member_roles(member, first_server_member)
        await self.sync_member_nickname(member, first_server_member)
        
        await ctx.send(f"✅ Successfully synced {member.mention} with their first server profile!")
    
    @commands.command(name='sync_all')
    @commands.has_permissions(administrator=True)
    async def sync_all_members(self, ctx):
        """Sync all members in the second server (admin only)"""
        if ctx.guild.id != self.second_server_id:
            await ctx.send("This command can only be used in the second server.")
            return
        
        await ctx.send("Starting bulk sync... This may take a while.")
        
        synced_count = 0
        failed_count = 0
        
        for member in ctx.guild.members:
            if member.bot:
                continue
                
            first_server_member = await self.get_member_from_first_server(member.id)
            
            if first_server_member:
                try:
                    await self.sync_member_roles(member, first_server_member)
                    await self.sync_member_nickname(member, first_server_member)
                    synced_count += 1
                except Exception as e:
                    logger.exception(f"Failed to sync {member}: {e}")
                    failed_count += 1
        
        await ctx.send(f"✅ Bulk sync completed!\n"
                      f"Synced: {synced_count} members\n"
                      f"Failed: {failed_count} members")
    
    @commands.command(name='check_sync')
    async def check_sync_status(self, ctx, member: discord.Member = None):
        """Check if a member can be synced"""
        if ctx.guild.id != self.second_server_id:
            await ctx.send("This command can only be used in the second server.")
            return
        
        if member is None:
            member = ctx.author
        
        first_server_member = await self.get_member_from_first_server(member.id)
        
        if not first_server_member:
            await ctx.send(f"❌ {member.mention} is not found in the first server.")
            return
        
        embed = discord.Embed(
            title="Sync Status Check",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Member Found",
            value=f"✅ {first_server_member.mention}",
            inline=False
        )
        
        # Check roles
        first_server_roles = [role.name for role in first_server_member.roles if role.name != "@everyone"]
        second_server_roles = [role.name for role in member.roles if role.name != "@everyone"]
        
        embed.add_field(
            name="First Server Roles",
            value=", ".join(first_server_roles) if first_server_roles else "None",
            inline=True
        )
        
        embed.add_field(
            name="Second Server Roles",
            value=", ".join(second_server_roles) if second_server_roles else "None",
            inline=True
        )
        
        # Check nickname
        embed.add_field(
            name="First Server Nickname",
            value=first_server_member.display_name,
            inline=True
        )
        
        embed.add_field(
            name="Second Server Nickname",
            value=member.display_name,
            inline=True
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(TagCog(bot))
