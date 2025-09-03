import discord
from discord.ext import commands
from discord import app_commands
import re
import asyncio

class ActivityTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="prize", description="Rank people based on their activity (messages, links, media sent).")
    async def prize(self, interaction: discord.Interaction):
        # Try to defer immediately, with error handling
        try:
            await interaction.response.defer(ephemeral=True)
        except discord.errors.NotFound:
            # If the interaction expired, try to send a regular message instead
            try:
                await interaction.followup.send("⚠️ Interaction expired, but processing your request...", ephemeral=True)
            except:
                return  # If we can't respond at all, exit gracefully
        except Exception as e:
            print(f"Error deferring interaction: {e}")
            return

        guild = interaction.guild
        if not guild:
            try:
                await interaction.followup.send("This command can only be used in a server.", ephemeral=True)
            except:
                pass
            return

        message_counts = {}
        link_counts = {}
        media_counts = {}

        processed_channels = 0
        total_channels = len(guild.text_channels)

        # Process channels with periodic updates and rate limiting
        for channel in guild.text_channels:
            try:
                # Check if we have permission to read this channel
                if not channel.permissions_for(guild.me).read_message_history:
                    continue

                processed_channels += 1
                
                # Add a small delay every few channels to prevent rate limiting
                if processed_channels % 3 == 0:
                    await asyncio.sleep(1)

                # Limit message history to prevent timeout (adjust as needed)
                message_limit = 1000  # Consider making this configurable
                
                async for message in channel.history(limit=message_limit):
                    if message.author.bot:
                        continue

                    user_id = message.author.id

                    # Initialize counters if user not seen before
                    if user_id not in message_counts:
                        message_counts[user_id] = 0
                        link_counts[user_id] = 0
                        media_counts[user_id] = 0

                    message_counts[user_id] += 1

                    # Count links (improved regex)
                    if re.search(r'https?://\S+', message.content):
                        link_counts[user_id] += 1

                    # Count media
                    if message.attachments:
                        media_counts[user_id] += 1

                # Send periodic updates for long-running operations
                if processed_channels % 5 == 0:
                    try:
                        await interaction.edit_original_response(
                            content=f"Processing channels... {processed_channels}/{total_channels} complete"
                        )
                    except:
                        pass  # Continue even if we can't update

            except discord.Forbidden:
                continue  # Skip channels we can't access
            except Exception as e:
                print(f"Error processing channel {channel.name}: {e}")
                continue

        # Calculate points and prepare leaderboard
        points = {}
        all_users = set(message_counts.keys()).union(link_counts.keys()).union(media_counts.keys())
        
        for user_id in all_users:
            points[user_id] = (
                message_counts.get(user_id, 0) +
                link_counts.get(user_id, 0) +
                media_counts.get(user_id, 0)
            )

        if not points:
            try:
                await interaction.edit_original_response(content="No activity data found or no accessible channels.")
            except:
                try:
                    await interaction.followup.send("No activity data found or no accessible channels.", ephemeral=True)
                except:
                    pass
            return

        leaderboard = sorted(points.items(), key=lambda x: x[1], reverse=True)

        # Build result with better formatting
        embed = discord.Embed(
            title="🏆 Activity Leaderboard",
            color=discord.Color.gold(),
            description=f"Based on messages from {processed_channels} channels"
        )

        leaderboard_text = ""
        for i, (user_id, point) in enumerate(leaderboard[:10], 1):  # Top 10 users
            user = guild.get_member(user_id)
            if user:
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                leaderboard_text += (
                    f"{emoji} **{user.display_name}**: {point} points\n"
                    f"   Messages: {message_counts.get(user_id, 0)} | "
                    f"Links: {link_counts.get(user_id, 0)} | "
                    f"Media: {media_counts.get(user_id, 0)}\n\n"
                )

        if len(leaderboard_text) > 2000:  # Discord embed field limit
            leaderboard_text = leaderboard_text[:1900] + "...\n*(Truncated due to length)*"

        embed.add_field(name="Top Contributors", value=leaderboard_text or "No data available", inline=False)

        try:
            await interaction.edit_original_response(content=None, embed=embed)
        except discord.errors.NotFound:
            try:
                await interaction.followup.send(embed=embed, ephemeral=True)
            except Exception as e:
                # Fallback to text if embed fails
                result = f"**🏆 Activity Leaderboard**\nBased on messages from {processed_channels} channels\n\n"
                for i, (user_id, point) in enumerate(leaderboard[:10], 1):
                    user = guild.get_member(user_id)
                    if user:
                        result += (f"{i}. {user.display_name}: {point} points "
                                 f"(Msg: {message_counts.get(user_id, 0)}, "
                                 f"Links: {link_counts.get(user_id, 0)}, "
                                 f"Media: {media_counts.get(user_id, 0)})\n")
                
                try:
                    await interaction.followup.send(result[:2000], ephemeral=True)
                except:
                    pass

async def setup(bot):
    await bot.add_cog(ActivityTracker(bot))
