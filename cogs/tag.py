import discord
from discord.ext import commands
from discord import app_commands
import logging

logger = logging.getLogger(__name__)

class TagCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.first_server_id = 1213699457233985587  # First server ID
        self.second_server_id = 1363616633951748270  # Second server ID
        
    async def get_member_from_first_server(self, user_id):
        """Get member from the first server"""
        first_guild = self.bot.get_guild(self.first_server_id)
        if first_guild:
            return first_guild.get_member(user_id)
        return None
    
    async def get_member_from_second_server(self, user_id):
        """Get member from the second server"""
        second_guild = self.bot.get_guild(self.second_server_id)
        if second_guild:
            return second_guild.get_member(user_id)
        return None
    
    async def create_role_if_not_exists(self, guild, role_name, color=None):
        """Create a role if it doesn't exist, return the role"""
        # Check if role already exists (case-insensitive)
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
        
        # Sync roles and nickname
        await self.sync_member_data(member, first_server_member)
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Handle member updates in the first server to sync to second server"""
        # Only process updates in the first server
        if before.guild.id != self.first_server_id:
            return
        
        # Check if roles or nickname changed
        roles_changed = set(before.roles) != set(after.roles)
        nickname_changed = before.display_name != after.display_name
        
        if not (roles_changed or nickname_changed):
            return
        
        # Get the same member from second server
        second_server_member = await self.get_member_from_second_server(after.id)
        
        if not second_server_member:
            logger.info(f"Member {after} not found in second server")
            return
        
        logger.info(f"Member {after} updated in first server, syncing to second server...")
        
        # Sync the updated data
        await self.sync_member_data(second_server_member, after)
    
    async def sync_member_data(self, second_server_member, first_server_member):
        """Sync both roles and nickname from first server to second server"""
        await self.sync_member_roles(second_server_member, first_server_member)
        await self.sync_member_nickname(second_server_member, first_server_member)
    
    async def sync_member_roles(self, second_server_member, first_server_member):
        """Sync roles from first server to second server (avoiding duplicates)"""
        second_guild = second_server_member.guild
        
        # Get target roles from first server (excluding @everyone and bot roles)
        target_roles = []
        first_server_roles = [role for role in first_server_member.roles 
                            if role.name != "@everyone" and not role.managed]
        
        for role in first_server_roles:
            # Create or get the role in second server
            new_role = await self.create_role_if_not_exists(
                second_guild, 
                role.name, 
                role.color
            )
            
            if new_role:
                target_roles.append(new_role)
        
        # Get current roles in second server (excluding @everyone and bot roles)
        current_roles = [role for role in second_server_member.roles 
                        if role.name != "@everyone" and not role.managed]
        
        # Find roles to add and remove
        target_role_names = {role.name for role in target_roles}
        current_role_names = {role.name for role in current_roles}
        
        roles_to_add = [role for role in target_roles 
                       if role.name not in current_role_names]
        roles_to_remove = [role for role in current_roles 
                          if role.name not in target_role_names]
        
        # Remove roles that shouldn't be there
        if roles_to_remove:
            try:
                await second_server_member.remove_roles(
                    *roles_to_remove,
                    reason="Auto-sync: removing roles not in first server"
                )
                removed_names = [role.name for role in roles_to_remove]
                logger.info(f"Removed roles {removed_names} from {second_server_member}")
            except discord.Forbidden:
                logger.error(f"No permission to remove roles from {second_server_member}")
            except Exception as e:
                logger.exception(f"Error removing roles from {second_server_member}: {e}")
        
        # Add roles that should be there
        if roles_to_add:
            try:
                await second_server_member.add_roles(
                    *roles_to_add, 
                    reason="Auto-sync: adding roles from first server"
                )
                added_names = [role.name for role in roles_to_add]
                logger.info(f"Added roles {added_names} to {second_server_member}")
            except discord.Forbidden:
                logger.error(f"No permission to add roles to {second_server_member}")
            except Exception as e:
                logger.exception(f"Error adding roles to {second_server_member}: {e}")
    
    async def sync_member_nickname(self, second_server_member, first_server_member):
        """Sync nickname from first server to second server"""
        first_server_nickname = first_server_member.display_name
        current_nickname = second_server_member.display_name
        
        # Only change nickname if it's different
        if first_server_nickname != current_nickname:
            try:
                # If the display name is the same as username, set nick to None
                nick_to_set = None if first_server_nickname == first_server_member.name else first_server_nickname
                
                await second_server_member.edit(
                    nick=nick_to_set,
                    reason="Auto-sync nickname from first server"
                )
                logger.info(f"Changed nickname of {second_server_member} to '{first_server_nickname}'")
            except discord.Forbidden:
                logger.error(f"No permission to change nickname of {second_server_member}")
            except Exception as e:
                logger.exception(f"Error changing nickname of {second_server_member}: {e}")
    
    @app_commands.command(name="sync_member", description="Manually sync a specific member with their first server profile")
    @app_commands.describe(member="The member to sync (leave empty to sync yourself)")
    @app_commands.default_permissions(administrator=True)
    async def manual_sync_member(self, interaction: discord.Interaction, member: discord.Member = None):
        """Manually sync a specific member (admin only)"""
        if interaction.guild.id != self.second_server_id:
            await interaction.response.send_message("This command can only be used in the second server.", ephemeral=True)
            return
        
        if member is None:
            member = interaction.user
        
        first_server_member = await self.get_member_from_first_server(member.id)
        
        if not first_server_member:
            await interaction.response.send_message(f"{member.mention} is not found in the first server.", ephemeral=True)
            return
        
        await interaction.response.send_message(f"Starting manual sync for {member.mention}...")
        
        # Sync roles and nickname
        await self.sync_member_data(member, first_server_member)
        
        await interaction.followup.send(f"✅ Successfully synced {member.mention} with their first server profile!")
    
    @app_commands.command(name="sync_all", description="Sync all members in the second server with their first server profiles")
    @app_commands.default_permissions(administrator=True)
    async def sync_all_members(self, interaction: discord.Interaction):
        """Sync all members in the second server (admin only)"""
        if interaction.guild.id != self.second_server_id:
            await interaction.response.send_message("This command can only be used in the second server.", ephemeral=True)
            return
        
        await interaction.response.send_message("Starting bulk sync... This may take a while.")
        
        synced_count = 0
        failed_count = 0
        not_found_count = 0
        
        for member in interaction.guild.members:
            if member.bot:
                continue
                
            first_server_member = await self.get_member_from_first_server(member.id)
            
            if first_server_member:
                try:
                    await self.sync_member_data(member, first_server_member)
                    synced_count += 1
                except Exception as e:
                    logger.exception(f"Failed to sync {member}: {e}")
                    failed_count += 1
            else:
                not_found_count += 1
        
        await interaction.followup.send(f"✅ Bulk sync completed!\n"
                      f"Synced: {synced_count} members\n"
                      f"Failed: {failed_count} members\n"
                      f"Not found in first server: {not_found_count} members")
    
    @app_commands.command(name="sync_from_first", description="Sync all members from first server to second server")
    @app_commands.default_permissions(administrator=True)
    async def sync_from_first_server(self, interaction: discord.Interaction):
        """Sync all members from first server to second server (admin only)"""
        if interaction.guild.id != self.second_server_id:
            await interaction.response.send_message("This command can only be used in the second server.", ephemeral=True)
            return
        
        first_guild = self.bot.get_guild(self.first_server_id)
        if not first_guild:
            await interaction.response.send_message("❌ Cannot access the first server.", ephemeral=True)
            return
        
        await interaction.response.send_message("Starting sync from first server... This may take a while.")
        
        synced_count = 0
        failed_count = 0
        not_found_count = 0
        
        for first_server_member in first_guild.members:
            if first_server_member.bot:
                continue
                
            second_server_member = await self.get_member_from_second_server(first_server_member.id)
            
            if second_server_member:
                try:
                    await self.sync_member_data(second_server_member, first_server_member)
                    synced_count += 1
                except Exception as e:
                    logger.exception(f"Failed to sync {first_server_member}: {e}")
                    failed_count += 1
            else:
                not_found_count += 1
        
        await interaction.followup.send(f"✅ Sync from first server completed!\n"
                      f"Synced: {synced_count} members\n"
                      f"Failed: {failed_count} members\n"
                      f"Not found in second server: {not_found_count} members")
    
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
        first_server_roles = [role.name for role in first_server_member.roles 
                            if role.name != "@everyone" and not role.managed]
        second_server_roles = [role.name for role in member.roles 
                             if role.name != "@everyone" and not role.managed]
        
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
        
        # Show role differences
        missing_roles = set(first_server_roles) - set(second_server_roles)
        extra_roles = set(second_server_roles) - set(first_server_roles)
        
        if missing_roles:
            embed.add_field(
                name="Missing Roles",
                value=", ".join(missing_roles),
                inline=True
            )
        
        if extra_roles:
            embed.add_field(
                name="Extra Roles",
                value=", ".join(extra_roles),
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
        
        # Sync status
        roles_match = set(first_server_roles) == set(second_server_roles)
        nickname_match = first_server_member.display_name == member.display_name
        
        status = "✅ In Sync" if roles_match and nickname_match else "⚠️ Out of Sync"
        embed.add_field(
            name="Sync Status",
            value=status,
            inline=False
        )
        
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(TagCog(bot))
