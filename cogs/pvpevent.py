import discord
from discord.ext import commands
import aiohttp
import asyncio
from PIL import Image, ImageEnhance
import io
import re
import logging
from collections import defaultdict
from datetime import datetime, timedelta
import hashlib

# You'll need to install these packages:
# pip install pillow pytesseract opencv-python-headless
try:
    import pytesseract
    import cv2
    import numpy as np
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False

logger = logging.getLogger(__name__)

class PvPEvent(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.target_channel_id = 1237390434041462836
        self.authorized_user_id = 486652069831376943
        self.processed_hashes = set()  # To track duplicate screenshots
        
        if not DEPENDENCIES_AVAILABLE:
            logger.error("Required dependencies not installed. Install: pillow pytesseract opencv-python-headless")

    async def download_image(self, url: str) -> bytes:
        """Download image from URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.read()
        except Exception as e:
            logger.error(f"Failed to download image: {e}")
        return None

    def get_image_hash(self, image_data: bytes) -> str:
        """Generate hash for duplicate detection"""
        return hashlib.md5(image_data).hexdigest()

    def preprocess_image(self, image_data: bytes) -> Image.Image:
        """Preprocess image for better OCR results"""
        try:
            # Open image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if needed
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Convert PIL to OpenCV format
            opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Apply image enhancements for better OCR
            # Convert to grayscale
            gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
            
            # Apply gaussian blur to reduce noise
            blurred = cv2.GaussianBlur(gray, (3, 3), 0)
            
            # Apply threshold to get black and white image
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Convert back to PIL
            processed_image = Image.fromarray(thresh)
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(processed_image)
            processed_image = enhancer.enhance(1.5)
            
            return processed_image
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            return Image.open(io.BytesIO(image_data))

    def extract_text_from_image(self, image: Image.Image) -> str:
        """Extract text using OCR"""
        try:
            # Configure pytesseract for better results
            custom_config = r'--oem 3 --psm 6'
            text = pytesseract.image_to_string(image, config=custom_config)
            return text
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""

    def detect_battle_result(self, text: str) -> dict:
        """Detect if it's a win or loss and extract relevant info"""
        text_lower = text.lower()
        lines = text.split('\n')
        
        # Debug: Log the extracted text
        logger.info(f"OCR Raw text: {text[:300]}...")
        
        # Look for victory/defeat indicators with more patterns
        victory_patterns = [
            'victory', 'victoire', 'won', 'gagné', 'win',
            '🏆', 'trophy', 'winners', 'gagnants'
        ]
        
        defeat_patterns = [
            'defeat', 'défaite', 'lost', 'perdu', 'lose',
            'losers', 'perdants'
        ]
        
        # Check each line for victory/defeat patterns
        is_victory = False
        is_defeat = False
        
        for line in lines:
            line_clean = line.strip().lower()
            if any(pattern in line_clean for pattern in victory_patterns):
                is_victory = True
                logger.info(f"Victory detected in line: {line}")
            if any(pattern in line_clean for pattern in defeat_patterns):
                is_defeat = True
                logger.info(f"Defeat detected in line: {line}")
        
        # If we find "Winners" section, it's likely a victory screen
        # If we only find "Losers" section, it might be a defeat screen
        has_winners_section = any('winner' in line.lower() for line in lines)
        has_losers_section = any('loser' in line.lower() for line in lines)
        
        # Enhanced logic: If we see winners section, assume victory
        if has_winners_section and not is_defeat:
            is_victory = True
            
        # Count defenders by looking for multiple player entries
        defender_count = 0
        player_entries = []
        
        for line in lines:
            line_clean = line.strip()
            # Look for player name patterns (names with levels, etc.)
            if re.match(r'^[A-Za-z][A-Za-z0-9\-_\s]{2,20}\s+\d+', line_clean):
                player_entries.append(line_clean)
            # Also check for names followed by level indicators
            elif re.search(r'[A-Za-z][A-Za-z0-9\-_]{2,15}.*\b(200|1\d\d|\d\d)\b', line_clean):
                player_entries.append(line_clean)
        
        # Count unique defenders (anyone in losers section)
        losers_section = self.extract_section_text(text, 'losers')
        if losers_section:
            potential_defenders = re.findall(r'[A-Za-z][A-Za-z0-9\-_]{2,15}', losers_section)
            defender_count = len([name for name in potential_defenders 
                                if not any(exclude in name.lower() for exclude in 
                                         ['level', 'lvl', 'duration', 'kamas', 'drops', 'gained', 'xp'])])
        
        has_defenders = defender_count > 0
        
        logger.info(f"Victory: {is_victory}, Defeat: {is_defeat}, Defenders: {defender_count}, Has defenders: {has_defenders}")
        
        return {
            'is_victory': is_victory,
            'is_defeat': is_defeat,
            'has_defenders': has_defenders,
            'defender_count': defender_count,
            'has_winners_section': has_winners_section,
            'has_losers_section': has_losers_section,
            'raw_text': text
        }

    def extract_section_text(self, text: str, section: str) -> str:
        """Extract text from specific sections (winners/losers)"""
        lines = text.split('\n')
        section_started = False
        section_text = []
        
        section_keywords = {
            'winners': ['winners', 'gagnants', 'winner'],
            'losers': ['losers', 'perdants', 'loser']
        }
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            
            # Check if this line starts the section we want
            if any(keyword in line_lower for keyword in section_keywords.get(section, [])):
                section_started = True
                continue
            
            if section_started:
                # Stop if we hit another section or empty lines
                if any(keyword in line_lower for other_section in section_keywords.values() 
                       for keyword in other_section if other_section != section_keywords.get(section)):
                    break
                
                if line.strip():
                    section_text.append(line.strip())
                elif len(section_text) > 3:  # Stop after several empty lines
                    break
        
        return '\n'.join(section_text)

    def extract_player_names(self, text: str) -> dict:
        """Extract player names from winners and losers sections"""
        winners_text = self.extract_section_text(text, 'winners')
        losers_text = self.extract_section_text(text, 'losers')
        
        logger.info(f"Winners section: {winners_text[:100]}...")
        logger.info(f"Losers section: {losers_text[:100]}...")
        
        # Pattern to match potential player names with level
        # Looking for: Name followed by level (like "Aspireat 200")
        name_level_pattern = r'([A-Za-z][A-Za-z0-9\-_\s]{2,20})\s+(\d+)'
        
        winners = []
        losers = []
        
        if winners_text:
            matches = re.findall(name_level_pattern, winners_text)
            winners = [match[0].strip() for match in matches]
            # Fallback: simple name pattern
            if not winners:
                simple_names = re.findall(r'[A-Za-z][A-Za-z0-9\-_]{2,15}', winners_text)
                winners = [name for name in simple_names 
                          if not any(exclude in name.lower() for exclude in 
                                   ['level', 'lvl', 'duration', 'kamas', 'drops', 'gained', 'xp', 'winner'])][:4]
        
        if losers_text:
            matches = re.findall(name_level_pattern, losers_text)
            losers = [match[0].strip() for match in matches]
            # Fallback: simple name pattern
            if not losers:
                simple_names = re.findall(r'[A-Za-z][A-Za-z0-9\-_]{2,15}', losers_text)
                losers = [name for name in simple_names 
                         if not any(exclude in name.lower() for exclude in 
                                  ['level', 'lvl', 'duration', 'kamas', 'drops', 'gained', 'xp', 'loser'])][:4]
        
        logger.info(f"Extracted winners: {winners}")
        logger.info(f"Extracted losers: {losers}")
        
        return {
            'winners': winners,
            'losers': losers
        }

    def calculate_points(self, battle_result: dict, player_names: dict) -> dict:
        """Calculate points based on battle outcome"""
        points = 0
        reason = ""
        
        # Determine if this was a victory or defeat
        is_victory = battle_result.get('is_victory', False)
        has_defenders = battle_result.get('has_defenders', False)
        
        # Get the attacking players (winners if victory, losers if defeat)
        if is_victory:
            attacking_players = player_names.get('winners', [])
            defending_players = player_names.get('losers', [])
        else:
            attacking_players = player_names.get('losers', [])  # Attackers lost
            defending_players = player_names.get('winners', [])  # Defenders won
        
        # Calculate points based on outcome
        if is_victory:
            if has_defenders:
                points = 3
                reason = "Won attack with defenders"
            else:
                points = 2
                reason = "Won attack without defenders"
        else:
            if has_defenders:
                points = 1
                reason = "Lost attack with defenders"
            else:
                points = 0
                reason = "Lost attack without defenders"
        
        return {
            'points': points,
            'reason': reason,
            'is_victory': is_victory,
            'has_defenders': has_defenders,
            'attacking_players': attacking_players,
            'defending_players': defending_players
        }

    async def process_screenshot(self, attachment) -> dict:
        """Process a single screenshot and return analysis results"""
        if not DEPENDENCIES_AVAILABLE:
            return {'error': 'OCR dependencies not installed'}
        
        try:
            # Download image
            image_data = await self.download_image(attachment.url)
            if not image_data:
                return {'error': 'Failed to download image'}
            
            # Check for duplicates
            image_hash = self.get_image_hash(image_data)
            if image_hash in self.processed_hashes:
                return {'error': 'Duplicate screenshot detected', 'duplicate': True}
            
            self.processed_hashes.add(image_hash)
            
            # Preprocess image
            processed_image = self.preprocess_image(image_data)
            
            # Extract text
            text = self.extract_text_from_image(processed_image)
            
            if not text.strip():
                return {'error': 'No text extracted from image'}
            
            # Detect battle result
            battle_result = self.detect_battle_result(text)
            
            # Extract player names
            player_names = self.extract_player_names(text)
            
            return {
                'success': True,
                'battle_result': battle_result,
                'player_names': player_names,
                'raw_text': text,
                'image_hash': image_hash
            }
            
        except Exception as e:
            logger.error(f"Error processing screenshot: {e}")
            return {'error': f'Processing failed: {str(e)}'}

    @commands.command(name='calculate_points')
    async def calculate_points_command(self, ctx):
        """Calculate PvP points from screenshots - triggered by '@spectra calculate the points'"""
        # Check if it's the right user and channel
        if ctx.author.id != self.authorized_user_id:
            return
        
        if ctx.channel.id != self.target_channel_id:
            await ctx.send("This command only works in the designated PvP channel.")
            return
        
        if not DEPENDENCIES_AVAILABLE:
            await ctx.send("❌ OCR dependencies are not installed. Please install: `pillow pytesseract opencv-python-headless`")
            return
        
        await ctx.send("🔍 Starting to scan screenshots and calculate points...")
        
        # Clear processed hashes for this calculation
        self.processed_hashes.clear()
        
        player_points = defaultdict(int)
        processed_screenshots = 0
        errors = []
        duplicate_count = 0
        battle_details = []
        
        # Get recent messages (last 200 messages, adjust as needed)
        messages = []
        async for message in ctx.channel.history(limit=200):
            if message.attachments:
                messages.append(message)
        
        progress_msg = await ctx.send(f"Processing {len(messages)} messages with attachments...")
        
        for i, message in enumerate(messages):
            for attachment in message.attachments:
                # Check if it's an image
                if any(attachment.filename.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']):
                    try:
                        result = await self.process_screenshot(attachment)
                        
                        if 'error' in result:
                            if result.get('duplicate'):
                                duplicate_count += 1
                            else:
                                errors.append(f"Screenshot from {message.author.display_name}: {result['error']}")
                            continue
                        
                        processed_screenshots += 1
                        
                        # Calculate points for this battle
                        battle_points = self.calculate_points(
                            result['battle_result'], 
                            result['player_names']
                        )
                        
                        # Add points to each attacking player
                        attacking_players = battle_points.get('attacking_players', [])
                        if attacking_players:
                            for player in attacking_players:
                                player_points[player] += battle_points['points']
                        else:
                            # Fallback: if no players detected, use Discord username
                            fallback_name = message.author.display_name
                            player_points[fallback_name] += battle_points['points']
                            attacking_players = [fallback_name]
                        
                        # Store battle details for debugging
                        battle_details.append({
                            'players': attacking_players,
                            'points': battle_points['points'],
                            'reason': battle_points['reason'],
                            'is_victory': battle_points['is_victory'],
                            'defenders': battle_points.get('defending_players', [])
                        })
                        
                        # Log the analysis
                        logger.info(f"Battle: {attacking_players} -> {battle_points['points']} points - {battle_points['reason']}")
                        
                    except Exception as e:
                        errors.append(f"Error processing screenshot from {message.author.display_name}: {str(e)}")
            
            # Update progress every 20 messages
            if i % 20 == 0:
                try:
                    await progress_msg.edit(content=f"Processed {i}/{len(messages)} messages...")
                except:
                    pass  # Ignore edit errors
        
        try:
            await progress_msg.delete()
        except:
            pass  # Ignore deletion errors
        
        # Create results embed
        embed = discord.Embed(
            title="🏆 PvP Event Points Calculation Results",
            description=f"Processed {processed_screenshots} screenshots",
            color=discord.Color.gold()
        )
        
        # Add player points
        if player_points:
            sorted_players = sorted(player_points.items(), key=lambda x: x[1], reverse=True)
            points_text = ""
            for rank, (player, points) in enumerate(sorted_players, 1):
                points_text += f"{rank}. **{player}**: {points} points\n"
            
            embed.add_field(name="📊 Player Points", value=points_text, inline=False)
        else:
            embed.add_field(name="📊 Player Points", value="No points calculated", inline=False)
        
        # Add statistics
        stats_text = f"✅ Successfully processed: {processed_screenshots}\n"
        stats_text += f"🔄 Duplicates found: {duplicate_count}\n"
        stats_text += f"❌ Errors: {len(errors)}"
        
        embed.add_field(name="📈 Statistics", value=stats_text, inline=False)
        
        # Add point system reminder
        embed.add_field(
            name="🎯 Point System",
            value="3 points: Won attack with defenders\n2 points: Won attack without defenders\n1 point: Lost attack with defenders\n0 points: Lost attack without defenders",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
        # Send errors if any (in smaller chunks)
        if errors:
            error_chunks = [errors[i:i+5] for i in range(0, len(errors), 5)]
            for chunk in error_chunks:
                error_text = "\n".join(chunk)
                if len(error_text) > 1900:  # Discord limit is 2000 chars
                    error_text = error_text[:1900] + "..."
                
                error_embed = discord.Embed(
                    title="⚠️ Processing Errors",
                    description=f"```{error_text}```",
                    color=discord.Color.orange()
                )
                await ctx.send(embed=error_embed)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for the trigger phrase"""
        # Don't respond to bot messages
        if message.author.bot:
            return
            
        # Debug logging
        logger.info(f"Message from {message.author.id} in channel {message.channel.id}: {message.content}")
        
        if message.author.id != self.authorized_user_id:
            logger.info(f"User {message.author.id} not authorized (expected {self.authorized_user_id})")
            return
        
        if message.channel.id != self.target_channel_id:
            logger.info(f"Wrong channel {message.channel.id} (expected {self.target_channel_id})")
            return
        
        # Check if bot is mentioned and message contains "calculate the points"
        bot_mentioned = self.bot.user in message.mentions
        has_trigger = "calculate the points" in message.content.lower()
        
        logger.info(f"Bot mentioned: {bot_mentioned}, Has trigger: {has_trigger}")
        
        if bot_mentioned and has_trigger:
            logger.info("Triggering points calculation...")
            ctx = await self.bot.get_context(message)
            await self.calculate_points_command(ctx)
        else:
            # Let's also try a simple command approach as backup
            if message.content.lower().strip() == "!calculate_points":
                logger.info("Using backup command trigger...")
                ctx = await self.bot.get_context(message)
                await self.calculate_points_command(ctx)

async def setup(bot):
    await bot.add_cog(PvPEvent(bot))
