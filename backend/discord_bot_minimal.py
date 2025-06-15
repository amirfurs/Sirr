"""
Minimal Discord Bot for Render Deployment
Optimized version with better error handling and logging for cloud deployment
"""

import discord
from discord.ext import commands
import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
from typing import Optional
import logging
import uuid
from pathlib import Path

# Configure logging for cloud deployment
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# MongoDB connection with error handling
try:
    mongo_url = os.environ['MONGO_URL']
    db_name = os.environ['DB_NAME']
    mongo_client = AsyncIOMotorClient(mongo_url)
    db = mongo_client[db_name]
    logger.info("MongoDB connection initialized")
except KeyError as e:
    logger.error(f"Missing environment variable: {e}")
    sys.exit(1)
except Exception as e:
    logger.error(f"Database connection error: {e}")
    sys.exit(1)

# Bot setup with required intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.moderation = True

# Initialize bot
bot = commands.Bot(
    command_prefix='!',
    intents=intents,
    help_command=None
)

# Emoji mapping for polls
POLL_EMOJIS = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

# Database helper functions
async def log_moderation_action(action_type: str, target_user_id: int, moderator_id: int, guild_id: int, reason: str, duration: Optional[int] = None):
    """Log moderation actions to database"""
    try:
        action = {
            "id": str(uuid.uuid4()),
            "action_type": action_type,
            "target_user_id": target_user_id,
            "moderator_id": moderator_id,
            "guild_id": guild_id,
            "reason": reason,
            "duration": duration,
            "timestamp": datetime.utcnow()
        }
        await db.moderation_logs.insert_one(action)
        logger.info(f"Logged moderation action: {action_type} for user {target_user_id}")
    except Exception as e:
        logger.error(f"Failed to log moderation action: {e}")

async def get_user_violations(user_id: int, guild_id: int):
    """Get violations count for a user"""
    try:
        violations = await db.moderation_logs.count_documents({
            "target_user_id": user_id,
            "guild_id": guild_id,
            "action_type": {"$in": ["warn", "mute", "kick", "ban"]}
        })
        return violations
    except Exception as e:
        logger.error(f"Failed to get user violations: {e}")
        return 0

async def save_server_activity(guild_id: int, activity_data: dict):
    """Save server activity data"""
    try:
        activity = {
            "id": str(uuid.uuid4()),
            "guild_id": guild_id,
            "timestamp": datetime.utcnow(),
            **activity_data
        }
        await db.server_activity.insert_one(activity)
    except Exception as e:
        logger.error(f"Failed to save server activity: {e}")

# Bot Events
@bot.event
async def on_ready():
    logger.info(f'{bot.user} قد اتصل بديسكورد!')
    logger.info(f'Bot is in {len(bot.guilds)} servers')
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        logger.info(f'Synced {len(synced)} global command(s)')
        
        for guild in bot.guilds:
            try:
                guild_synced = await bot.tree.sync(guild=guild)
                logger.info(f'Synced {len(guild_synced)} command(s) for guild {guild.name}')
            except Exception as e:
                logger.error(f'Failed to sync commands for guild {guild.name}: {e}')
                
    except Exception as e:
        logger.error(f'Failed to sync global commands: {e}')
        
    logger.info("Bot is ready and all commands are synced!")

@bot.event
async def on_guild_join(guild):
    """Sync commands when bot joins a new guild"""
    try:
        synced = await bot.tree.sync(guild=guild)
        logger.info(f'Synced {len(synced)} command(s) for new guild {guild.name}')
    except Exception as e:
        logger.error(f'Failed to sync commands for new guild {guild.name}: {e}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # Log message activity for statistics
    if message.guild:
        await save_server_activity(message.guild.id, {
            "type": "message",
            "user_id": message.author.id,
            "channel_id": message.channel.id
        })
    
    await bot.process_commands(message)

# ====================
# MODERATION COMMANDS
# ====================

@bot.tree.command(name="مسح", description="مسح رسائل من القناة")
@discord.app_commands.describe(عدد="عدد الرسائل المراد مسحها (افتراضي: 1)")
async def clear_messages(interaction: discord.Interaction, عدد: int = 1):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ ليس لديك صلاحية لمسح الرسائل", ephemeral=True)
        return
    
    if عدد < 1 or عدد > 100:
        await interaction.response.send_message("❌ يجب أن يكون العدد بين 1 و 100", ephemeral=True)
        return
    
    try:
        await interaction.response.defer()
        deleted = await interaction.channel.purge(limit=عدد)
        
        embed = discord.Embed(
            title="🧹 تم مسح الرسائل",
            description=f"تم مسح {len(deleted)} رسالة",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        await log_moderation_action("clear", 0, interaction.user.id, interaction.guild.id, f"مسح {len(deleted)} رسالة")
        
    except discord.Forbidden:
        await interaction.followup.send("❌ ليس لدي صلاحية لمسح الرسائل", ephemeral=True)
    except Exception as e:
        logger.error(f"Error in clear command: {e}")
        await interaction.followup.send("❌ حدث خطأ أثناء مسح الرسائل", ephemeral=True)

@bot.tree.command(name="كتم", description="كتم عضو لفترة محددة")
@discord.app_commands.describe(
    العضو="العضو المراد كتمه",
    دقائق="مدة الكتم بالدقائق",
    سبب="سبب الكتم"
)
async def mute_member(interaction: discord.Interaction, العضو: discord.Member, دقائق: int, سبب: str = "لا يوجد سبب"):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("❌ ليس لديك صلاحية لكتم الأعضاء", ephemeral=True)
        return
    
    if دقائق < 1 or دقائق > 40320:
        await interaction.response.send_message("❌ يجب أن تكون المدة بين 1 دقيقة و 28 يوم", ephemeral=True)
        return
    
    try:
        timeout_duration = discord.utils.utcnow() + timedelta(minutes=دقائق)
        await العضو.timeout(timeout_duration, reason=سبب)
        
        embed = discord.Embed(
            title="🔇 تم كتم العضو",
            color=discord.Color.orange()
        )
        embed.add_field(name="العضو", value=العضو.mention, inline=True)
        embed.add_field(name="المدة", value=f"{دقائق} دقيقة", inline=True)
        embed.add_field(name="السبب", value=سبب, inline=False)
        embed.add_field(name="المشرف", value=interaction.user.mention, inline=True)
        
        await interaction.response.send_message(embed=embed)
        await log_moderation_action("mute", العضو.id, interaction.user.id, interaction.guild.id, سبب, دقائق)
        
        # Try to DM the user
        try:
            dm_embed = discord.Embed(
                title="تم كتمك في الخادم",
                description=f"**الخادم:** {interaction.guild.name}\n**المدة:** {دقائق} دقيقة\n**السبب:** {سبب}",
                color=discord.Color.orange()
            )
            await العضو.send(embed=dm_embed)
        except:
            pass
            
    except discord.Forbidden:
        await interaction.response.send_message("❌ ليس لدي صلاحية لكتم هذا العضو", ephemeral=True)
    except Exception as e:
        logger.error(f"Error in mute command: {e}")
        await interaction.response.send_message("❌ حدث خطأ أثناء كتم العضو", ephemeral=True)

@bot.tree.command(name="اختبار", description="اختبار البوت")
async def test_bot(interaction: discord.Interaction):
    embed = discord.Embed(
        title="✅ البوت يعمل بشكل صحيح!",
        description="جميع الأنظمة تعمل بكفاءة",
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    
    embed.add_field(name="🏓 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="🖥️ الخوادم", value=str(len(bot.guilds)), inline=True)
    embed.add_field(name="👥 المستخدمين", value=str(len(bot.users)), inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="مساعدة", description="عرض قائمة الأوامر المتاحة")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📋 قائمة أوامر البوت",
        description="البوت العربي لإدارة السيرفر",
        color=discord.Color.blue()
    )
    
    commands_text = """
    • `/مسح [عدد]` - مسح رسائل من القناة
    • `/كتم @عضو [دقائق] [سبب]` - كتم عضو لفترة محددة
    • `/اختبار` - اختبار عمل البوت
    • `/مساعدة` - عرض هذه القائمة
    
    **المزيد من الأوامر متاحة! استخدم / لرؤية جميع الأوامر**
    """
    
    embed.add_field(name="🤖 الأوامر المتاحة", value=commands_text, inline=False)
    embed.set_footer(text="استخدم / قبل كل أمر | جميع الأوامر باللغة العربية")
    
    await interaction.response.send_message(embed=embed)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    
    logger.error(f"Command error: {error}")
    
    if hasattr(ctx, 'send'):
        try:
            await ctx.send("❌ حدث خطأ أثناء تنفيذ الأمر")
        except:
            pass

@bot.event
async def on_error(event, *args, **kwargs):
    logger.error(f"Bot error in {event}: {args}")

# Main function to run the bot
async def run_discord_bot():
    """Run the Discord bot with proper error handling"""
    try:
        token = os.environ.get('DISCORD_BOT_TOKEN')
        if not token:
            logger.error("DISCORD_BOT_TOKEN environment variable is not set")
            return
        
        logger.info("Starting Discord bot...")
        await bot.start(token)
        
    except discord.LoginFailure:
        logger.error("Invalid Discord bot token")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
    finally:
        if not bot.is_closed():
            await bot.close()
        if mongo_client:
            mongo_client.close()

if __name__ == "__main__":
    try:
        asyncio.run(run_discord_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")