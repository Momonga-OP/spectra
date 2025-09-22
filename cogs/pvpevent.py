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
        self.target_channel_id = 1417234772702527703
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
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Apply threshold to get black and white image
            _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Convert back to PIL
            processed_image = Image.fromarray(thresh)
            
            # Enhance contrast
            enhancer = ImageEnhance.Contrast(processed_image)
            processed_image = enhancer.enhance(2.0)
            
            # Enhance sharpness
            enhancer = ImageEnhance.Sharpness(processed_image)
            processed_image = enhancer.enhance(2.0)
            
            return processed_image
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {e}")
            return Image.open(io.BytesIO(image_data))

    def extract_text_from_image(self, image: Image.Image) -> str:
        """Extract text using OCR"""
        try:
            # Configure pytesseract for better results
            custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.'
            text = pytesseract.image_to_string(image, config=custom_config)
            return text
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ""

    def detect_battle_result(self, text: str) -> dict:
        """Detect if it's a win or loss and extract relevant info"""
        text_lower = text.lower()
        
        # Look for victory/defeat indicators
        victory_keywords = ['victory', 'victoire', 'winners', 'gagnants']
        defeat_keywords = ['defeat', 'défaite', 'losers', 'perdants']
        
        is_victory = any(keyword in text_lower for keyword in victory_keywords)
        is_defeat = any(keyword in text_lower for keyword in defeat_keywords)
        
        # Look for defenders (check for multiple players in losers section)
        defender_indicators = ['defenders', 'défenseurs']
        has_defenders = any(keyword in text_lower for keyword in defender_indicators)
        
        # If we can't detect defenders from keywords, try to count names in losers section
        if not has_defenders:
            # Look for patterns that suggest multiple players
            losers_section = self.extract_section_text(text, 'losers')
            if losers_section:
                # Count potential player names (assuming names don't contain numbers)
                potential_names = re.findall(r'[A-Za-z][A-Za-z-_]{2,15}', losers_section)
                has_defenders = len(potential_names) > 1
        
        return {
            'is_victory': is_victory,
            'is_defeat': is_defeat,
            'has_defenders': has_defenders,
            'raw_text': text
        }

    def extract_section_text(self, text: str, section: str) -> str:
        """Extract text from specific sections (winners/losers)"""
        lines = text.split('\n')
        section_started = False
        section_text = []
        
        section_keywords = {
            'winners': ['winners', 'gagnants', 'victory'],
            'losers': ['losers', 'perdants', 'defeat']
        }
        
        for line in lines:
            line_lower = line.lower().strip()
            
            if any(keyword in line_lower for keyword in section_keywords.get(section, [])):
                section_started = True
                continue
            
            if section_started:
                # Stop if we hit another section
                if any(keyword in line_lower for other_section in section_keywords.values() 
                       for keyword in other_section if other_section != section_keywords.get(section)):
                    break
                
                if line.strip():
                    section_text.append(line.strip())
        
        return '\n'.join(section_text)

    def extract_player_names(self, text: str) -> dict:
        """Extract player names from winners and losers sections"""
        winners_text = self.extract_section_text(text, 'winners')
        losers_text = self.extract_section_text(text, 'losers')
        
        # Pattern to match potential player names (adjust based on your server's naming conventions)
        name_pattern = r'[A-Za-z][A-Za-z0-9\-_]{2,15}'
        
        winners = []
        losers = []
        
        if winners_text:
            potential_winners = re.findall(name_pattern, winners_text)
            # Filter out common words/UI elements
            filtered_winners = [name for name in potential_winners 
                              if not any(exclude in name.lower() for exclude in 
                                       ['level', 'lvl', 'duration', 'kamas', 'drops', 'gained', 'xp'])]
            winners = filtered_winners[:4]  # Max 4 players per team usually
        
        if losers_text:
            potential_losers = re.findall(name_pattern, losers_text)
            filtered_losers = [name for name in potential_losers 
                             if not any(exclude in name.lower() for exclude in 
                                      ['level', 'lvl', 'duration', 'kamas', 'drops', 'gained', 'xp'])]
            losers = filtered_losers[:4]  # Max 4 players per team usually
        
        return {
            'winners': winners,
            'losers': losers
        }

    def calculate_points(self, battle_result: dict, player_names: dict, attacking_player: str) -> dict:
        """Calculate points based on battle outcome"""
        points = 0
        reason = ""
        
        # Check if the attacking player won or lost
        player_won = attacking_player.lower() in [name.lower() for name in player_names.get('winners', [])]
        has_defenders = battle_result.get('has_defenders', False) or len(player_names.get('losers', [])) > 0
        
        if player_won:
            if has_defenders:
                points = 3
                reason = "Won attack with defenders"
            else:
                points = 2
                reason = "Won attack with no defenders"
        else:
            if has_defenders:
                points = 1
                reason = "Lost attack with defenders"
            else:
                points = 0
                reason = "Lost attack with no defenders"
        
        return {
            'points': points,
            'reason': reason,
            'player_won': player_won,
            'has_defenders': has_defenders
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
        
        # Get recent messages (last 100 messages, adjust as needed)
        messages = []
        async for message in ctx.channel.history(limit=100):
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
                        
                        # Try to determine the attacking player (could be the message author)
                        attacking_player = message.author.display_name
                        
                        # Calculate points for this battle
                        battle_points = self.calculate_points(
                            result['battle_result'], 
                            result['player_names'], 
                            attacking_player
                        )
                        
                        player_points[attacking_player] += battle_points['points']
                        
                        # Log the analysis for debugging
                        logger.info(f"Processed screenshot from {attacking_player}: {battle_points['points']} points - {battle_points['reason']}")
                        
                    except Exception as e:
                        errors.append(f"Error processing screenshot from {message.author.display_name}: {str(e)}")
            
            # Update progress every 10 messages
            if i % 10 == 0:
                await progress_msg.edit(content=f"Processed {i}/{len(messages)} messages...")
        
        await progress_msg.delete()
        
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
            value="3 points: Won attack with defenders\n2 points: Won attack without defenders\n1 point: Lost attack with defenders",
            inline=False
        )
        
        await ctx.send(embed=embed)
        
        # Send errors if any (in smaller chunks)
        if errors:
            error_chunks = [errors[i:i+10] for i in range(0, len(errors), 10)]
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
        if message.author.id != self.authorized_user_id:
            return
        
        if message.channel.id != self.target_channel_id:
            return
        
        # Check for trigger phrase (case insensitive)
        if "@spectra calculate the points" in message.content.lower():
            ctx = await self.bot.get_context(message)
            await self.calculate_points_command(ctx)

async def setup(bot):
    await bot.add_cog(PvPEvent(bot))
