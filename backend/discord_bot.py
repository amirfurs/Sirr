import discord
from discord.ext import commands
import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timedelta
from typing import Optional
import logging
import uuid
from pathlib import Path

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
mongo_client = AsyncIOMotorClient(mongo_url)
db = mongo_client[os.environ['DB_NAME']]

# Bot setup with required intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.moderation = True

# Initialize bot with Arabic-friendly settings
bot = commands.Bot(
    command_prefix='!',
    intents=intents,
    help_command=None  # We'll create custom help
)

# Emoji mapping for reactions
POLL_EMOJIS = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

# Database helper functions
async def log_moderation_action(action_type: str, target_user_id: int, moderator_id: int, guild_id: int, reason: str, duration: Optional[int] = None):
    """Log moderation actions to database"""
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

async def get_user_violations(user_id: int, guild_id: int):
    """Get violations count for a user"""
    violations = await db.moderation_logs.count_documents({
        "target_user_id": user_id,
        "guild_id": guild_id,
        "action_type": {"$in": ["warn", "mute", "kick", "ban"]}
    })
    return violations

async def save_server_activity(guild_id: int, activity_data: dict):
    """Save server activity data"""
    activity = {
        "id": str(uuid.uuid4()),
        "guild_id": guild_id,
        "timestamp": datetime.utcnow(),
        **activity_data
    }
    await db.server_activity.insert_one(activity)

# Bot Events
@bot.event
async def on_ready():
    logger.info(f'{bot.user} قد اتصل بديسكورد!')
    logger.info(f'Bot is in {len(bot.guilds)} servers')
    
    # Sync slash commands
    try:
        synced = await bot.tree.sync()
        logger.info(f'Synced {len(synced)} command(s)')
    except Exception as e:
        logger.error(f'Failed to sync commands: {e}')

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
@discord.app_commands.describe(
    عدد="عدد الرسائل المراد مسحها (افتراضي: 1)"
)
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
    
    if دقائق < 1 or دقائق > 40320:  # Discord limit: 28 days
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
        
        # Log to database
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
            pass  # User has DMs disabled
            
    except discord.Forbidden:
        await interaction.response.send_message("❌ ليس لدي صلاحية لكتم هذا العضو", ephemeral=True)

@bot.tree.command(name="فك_كتم", description="فك كتم عضو")
@discord.app_commands.describe(
    العضو="العضو المراد فك كتمه"
)
async def unmute_member(interaction: discord.Interaction, العضو: discord.Member):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("❌ ليس لديك صلاحية لفك كتم الأعضاء", ephemeral=True)
        return
    
    try:
        await العضو.timeout(None)
        
        embed = discord.Embed(
            title="🔊 تم فك كتم العضو",
            description=f"**العضو:** {العضو.mention}\n**المشرف:** {interaction.user.mention}",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)
        await log_moderation_action("unmute", العضو.id, interaction.user.id, interaction.guild.id, "فك كتم")
        
    except discord.Forbidden:
        await interaction.response.send_message("❌ ليس لدي صلاحية لفك كتم هذا العضو", ephemeral=True)

@bot.tree.command(name="طرد", description="طرد عضو من الخادم")
@discord.app_commands.describe(
    العضو="العضو المراد طرده",
    سبب="سبب الطرد"
)
async def kick_member(interaction: discord.Interaction, العضو: discord.Member, سبب: str = "لا يوجد سبب"):
    if not interaction.user.guild_permissions.kick_members:
        await interaction.response.send_message("❌ ليس لديك صلاحية لطرد الأعضاء", ephemeral=True)
        return
    
    try:
        # Send DM before kicking
        try:
            dm_embed = discord.Embed(
                title="تم طردك من الخادم",
                description=f"**الخادم:** {interaction.guild.name}\n**السبب:** {سبب}",
                color=discord.Color.red()
            )
            await العضو.send(embed=dm_embed)
        except:
            pass
        
        await العضو.kick(reason=سبب)
        
        embed = discord.Embed(
            title="👢 تم طرد العضو",
            color=discord.Color.red()
        )
        embed.add_field(name="العضو", value=f"{العضو.name}#{العضو.discriminator}", inline=True)
        embed.add_field(name="السبب", value=سبب, inline=False)
        embed.add_field(name="المشرف", value=interaction.user.mention, inline=True)
        
        await interaction.response.send_message(embed=embed)
        await log_moderation_action("kick", العضو.id, interaction.user.id, interaction.guild.id, سبب)
        
    except discord.Forbidden:
        await interaction.response.send_message("❌ ليس لدي صلاحية لطرد هذا العضو", ephemeral=True)

@bot.tree.command(name="حظر", description="حظر عضو من الخادم")
@discord.app_commands.describe(
    العضو="العضو المراد حظره",
    سبب="سبب الحظر"
)
async def ban_member(interaction: discord.Interaction, العضو: discord.Member, سبب: str = "لا يوجد سبب"):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("❌ ليس لديك صلاحية لحظر الأعضاء", ephemeral=True)
        return
    
    try:
        # Send DM before banning
        try:
            dm_embed = discord.Embed(
                title="تم حظرك من الخادم",
                description=f"**الخادم:** {interaction.guild.name}\n**السبب:** {سبب}",
                color=discord.Color.dark_red()
            )
            await العضو.send(embed=dm_embed)
        except:
            pass
        
        await العضو.ban(reason=سبب)
        
        embed = discord.Embed(
            title="🔨 تم حظر العضو",
            color=discord.Color.dark_red()
        )
        embed.add_field(name="العضو", value=f"{العضو.name}#{العضو.discriminator}", inline=True)
        embed.add_field(name="السبب", value=سبب, inline=False)
        embed.add_field(name="المشرف", value=interaction.user.mention, inline=True)
        
        await interaction.response.send_message(embed=embed)
        await log_moderation_action("ban", العضو.id, interaction.user.id, interaction.guild.id, سبب)
        
    except discord.Forbidden:
        await interaction.response.send_message("❌ ليس لدي صلاحية لحظر هذا العضو", ephemeral=True)

@bot.tree.command(name="فك_حظر", description="فك حظر عضو باستخدام معرف المستخدم")
@discord.app_commands.describe(
    معرف_العضو="معرف العضو المراد فك حظره"
)
async def unban_member(interaction: discord.Interaction, معرف_العضو: str):
    if not interaction.user.guild_permissions.ban_members:
        await interaction.response.send_message("❌ ليس لديك صلاحية لفك حظر الأعضاء", ephemeral=True)
        return
    
    try:
        user_id = int(معرف_العضو)
        user = await bot.fetch_user(user_id)
        
        await interaction.guild.unban(user)
        
        embed = discord.Embed(
            title="✅ تم فك حظر العضو",
            description=f"**العضو:** {user.name}#{user.discriminator}\n**المشرف:** {interaction.user.mention}",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)
        await log_moderation_action("unban", user.id, interaction.user.id, interaction.guild.id, "فك حظر")
        
    except ValueError:
        await interaction.response.send_message("❌ معرف المستخدم غير صحيح", ephemeral=True)
    except discord.NotFound:
        await interaction.response.send_message("❌ لم يتم العثور على المستخدم أو أنه غير محظور", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ ليس لدي صلاحية لفك حظر الأعضاء", ephemeral=True)

@bot.tree.command(name="تحذير", description="إعطاء تحذير لعضو")
@discord.app_commands.describe(
    العضو="العضو المراد تحذيره",
    سبب="سبب التحذير"
)
async def warn_member(interaction: discord.Interaction, العضو: discord.Member, سبب: str = "لا يوجد سبب"):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ ليس لديك صلاحية لإعطاء تحذيرات", ephemeral=True)
        return
    
    # Get current warnings count
    warnings_count = await get_user_violations(العضو.id, interaction.guild.id)
    new_warnings = warnings_count + 1
    
    embed = discord.Embed(
        title="⚠️ تم إعطاء تحذير",
        color=discord.Color.yellow()
    )
    embed.add_field(name="العضو", value=العضو.mention, inline=True)
    embed.add_field(name="عدد التحذيرات", value=f"{new_warnings}", inline=True)
    embed.add_field(name="السبب", value=سبب, inline=False)
    embed.add_field(name="المشرف", value=interaction.user.mention, inline=True)
    
    await interaction.response.send_message(embed=embed)
    await log_moderation_action("warn", العضو.id, interaction.user.id, interaction.guild.id, سبب)
    
    # Send DM to user
    try:
        dm_embed = discord.Embed(
            title="تم إعطاؤك تحذير",
            description=f"**الخادم:** {interaction.guild.name}\n**السبب:** {سبب}\n**عدد التحذيرات:** {new_warnings}",
            color=discord.Color.yellow()
        )
        await العضو.send(embed=dm_embed)
    except:
        pass

# ====================
# ANNOUNCEMENT & POLL COMMANDS
# ====================

@bot.tree.command(name="إعلان", description="إنشاء إعلان في القناة")
@discord.app_commands.describe(
    العنوان="عنوان الإعلان",
    المحتوى="محتوى الإعلان"
)
async def create_announcement(interaction: discord.Interaction, العنوان: str, المحتوى: str):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ ليس لديك صلاحية لإنشاء الإعلانات", ephemeral=True)
        return
    
    embed = discord.Embed(
        title=f"📢 {العنوان}",
        description=المحتوى,
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    embed.set_footer(
        text=f"إعلان من {interaction.user.display_name}", 
        icon_url=interaction.user.display_avatar.url
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="استبيان", description="إنشاء استبيان")
@discord.app_commands.describe(
    السؤال="سؤال الاستبيان",
    الخيارات="الخيارات مفصولة بـ | (مثال: نعم|لا|ربما)"
)
async def create_poll(interaction: discord.Interaction, السؤال: str, الخيارات: str):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("❌ ليس لديك صلاحية لإنشاء الاستبيانات", ephemeral=True)
        return
    
    options = [opt.strip() for opt in الخيارات.split('|')]
    
    if len(options) < 2:
        await interaction.response.send_message("❌ يجب تقديم خيارين على الأقل", ephemeral=True)
        return
    
    if len(options) > 10:
        await interaction.response.send_message("❌ الحد الأقصى 10 خيارات", ephemeral=True)
        return
    
    embed = discord.Embed(
        title=f"📊 {السؤال}",
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    
    description = ""
    for i, option in enumerate(options):
        description += f"{POLL_EMOJIS[i]} {option}\n"
    
    embed.description = description
    embed.set_footer(
        text=f"استبيان من {interaction.user.display_name}", 
        icon_url=interaction.user.display_avatar.url
    )
    
    await interaction.response.send_message(embed=embed)
    message = await interaction.original_response()
    
    # Add reactions
    for i in range(len(options)):
        await message.add_reaction(POLL_EMOJIS[i])

@bot.tree.command(name="الأعضاء_النشطين", description="عرض الأعضاء المتصلين حالياً")
async def active_members(interaction: discord.Interaction):
    guild = interaction.guild
    
    # Count members by status
    online_members = [m for m in guild.members if m.status == discord.Status.online and not m.bot]
    idle_members = [m for m in guild.members if m.status == discord.Status.idle and not m.bot]
    dnd_members = [m for m in guild.members if m.status == discord.Status.dnd and not m.bot]
    
    total_active = len(online_members) + len(idle_members) + len(dnd_members)
    
    embed = discord.Embed(
        title="🟢 الأعضاء النشطين",
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    
    embed.add_field(
        name="📊 الإحصائيات",
        value=f"**المتصلين:** {len(online_members)}\n**بعيد:** {len(idle_members)}\n**مشغول:** {len(dnd_members)}\n**المجموع:** {total_active}",
        inline=False
    )
    
    # Show top 10 online members
    if online_members:
        online_list = "\n".join([f"• {member.display_name}" for member in online_members[:10]])
        if len(online_members) > 10:
            online_list += f"\n... و {len(online_members) - 10} آخرين"
        embed.add_field(name="🟢 المتصلين", value=online_list, inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="المخالفات", description="عرض مخالفات عضو")
@discord.app_commands.describe(
    العضو="العضو المراد عرض مخالفاته"
)
async def member_violations(interaction: discord.Interaction, العضو: discord.Member):
    if not interaction.user.guild_permissions.view_audit_log:
        await interaction.response.send_message("❌ ليس لديك صلاحية لعرض المخالفات", ephemeral=True)
        return
    
    # Get recent violations from database
    violations = await db.moderation_logs.find({
        "target_user_id": العضو.id,
        "guild_id": interaction.guild.id
    }).sort("timestamp", -1).limit(10).to_list(length=10)
    
    embed = discord.Embed(
        title=f"📋 مخالفات {العضو.display_name}",
        color=discord.Color.orange()
    )
    
    if not violations:
        embed.description = "✅ لا توجد مخالفات مسجلة"
    else:
        violations_text = ""
        for violation in violations:
            action_emoji = {
                "warn": "⚠️",
                "mute": "🔇",
                "kick": "👢",
                "ban": "🔨",
                "unmute": "🔊",
                "unban": "✅"
            }.get(violation["action_type"], "📝")
            
            date = violation["timestamp"].strftime("%Y-%m-%d %H:%M")
            violations_text += f"{action_emoji} **{violation['action_type']}** - {violation['reason']}\n📅 {date}\n\n"
        
        embed.description = violations_text
        embed.add_field(
            name="📊 الإجمالي", 
            value=f"**عدد المخالفات:** {len(violations)}", 
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

# ====================
# STATISTICS & REPORTS
# ====================

@bot.tree.command(name="الإحصائيات", description="عرض إحصائيات الخادم الأساسية")
async def server_stats(interaction: discord.Interaction):
    guild = interaction.guild
    
    # Count members by status
    online = len([m for m in guild.members if m.status == discord.Status.online])
    idle = len([m for m in guild.members if m.status == discord.Status.idle])
    dnd = len([m for m in guild.members if m.status == discord.Status.dnd])
    offline = len([m for m in guild.members if m.status == discord.Status.offline])
    
    # Count bots vs humans
    bots = len([m for m in guild.members if m.bot])
    humans = len([m for m in guild.members if not m.bot])
    
    embed = discord.Embed(
        title=f"📊 إحصائيات {guild.name}",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    
    embed.add_field(
        name="👥 الأعضاء",
        value=f"**المجموع:** {guild.member_count}\n**البشر:** {humans}\n**البوتات:** {bots}",
        inline=True
    )
    
    embed.add_field(
        name="🟢 الحالة",
        value=f"**متصل:** {online}\n**بعيد:** {idle}\n**مشغول:** {dnd}\n**غير متصل:** {offline}",
        inline=True
    )
    
    embed.add_field(
        name="📝 القنوات",
        value=f"**نصية:** {len(guild.text_channels)}\n**صوتية:** {len(guild.voice_channels)}\n**الفئات:** {len(guild.categories)}",
        inline=True
    )
    
    embed.add_field(
        name="🎭 الأدوار",
        value=f"**المجموع:** {len(guild.roles)}",
        inline=True
    )
    
    embed.add_field(
        name="📅 معلومات الخادم",
        value=f"**تاريخ الإنشاء:** {guild.created_at.strftime('%Y-%m-%d')}\n**المالك:** {guild.owner.mention if guild.owner else 'غير محدد'}",
        inline=True
    )
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="تقرير_يومي", description="تقرير يومي شامل للخادم")
async def daily_report(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ مطلوب صلاحية المدير", ephemeral=True)
        return
    
    guild = interaction.guild
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Get today's moderation actions
    mod_actions = await db.moderation_logs.find({
        "guild_id": guild.id,
        "timestamp": {"$gte": today}
    }).to_list(length=None)
    
    # Get today's activity
    activities = await db.server_activity.find({
        "guild_id": guild.id,
        "timestamp": {"$gte": today}
    }).to_list(length=None)
    
    embed = discord.Embed(
        title="📊 التقرير اليومي",
        description=f"تقرير لتاريخ {today.strftime('%Y-%m-%d')}",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    
    # Moderation summary
    mod_summary = {}
    for action in mod_actions:
        action_type = action["action_type"]
        mod_summary[action_type] = mod_summary.get(action_type, 0) + 1
    
    if mod_summary:
        mod_text = "\n".join([f"**{action}:** {count}" for action, count in mod_summary.items()])
        embed.add_field(name="🛡️ إجراءات الإشراف", value=mod_text, inline=True)
    else:
        embed.add_field(name="🛡️ إجراءات الإشراف", value="✅ لا توجد إجراءات", inline=True)
    
    # Activity summary
    message_count = len([a for a in activities if a.get("type") == "message"])
    embed.add_field(name="💬 الرسائل", value=str(message_count), inline=True)
    
    # Current stats
    embed.add_field(
        name="👥 الأعضاء الحاليين",
        value=f"**المجموع:** {guild.member_count}\n**متصل:** {len([m for m in guild.members if m.status == discord.Status.online])}",
        inline=True
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="أكثر_نشاط", description="عرض أكثر الأعضاء نشاطاً")
@discord.app_commands.describe(
    الفترة="فترة التقييم (أسبوع أو شهر)"
)
@discord.app_commands.choices(الفترة=[
    discord.app_commands.Choice(name="أسبوع", value="week"),
    discord.app_commands.Choice(name="شهر", value="month")
])
async def most_active(interaction: discord.Interaction, الفترة: str):
    days = 7 if الفترة == "week" else 30
    start_date = datetime.utcnow() - timedelta(days=days)
    
    # Get activities from database
    activities = await db.server_activity.find({
        "guild_id": interaction.guild.id,
        "timestamp": {"$gte": start_date},
        "type": "message"
    }).to_list(length=None)
    
    # Count messages per user
    user_activity = {}
    for activity in activities:
        user_id = activity["user_id"]
        user_activity[user_id] = user_activity.get(user_id, 0) + 1
    
    # Sort by activity
    sorted_users = sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:10]
    
    embed = discord.Embed(
        title=f"🏆 أكثر الأعضاء نشاطاً - آخر {الفترة}",
        color=discord.Color.gold(),
        timestamp=discord.utils.utcnow()
    )
    
    if sorted_users:
        description = ""
        for i, (user_id, count) in enumerate(sorted_users, 1):
            try:
                user = interaction.guild.get_member(user_id)
                if user:
                    medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                    description += f"{medal} {user.display_name} - {count} رسالة\n"
            except:
                continue
        
        embed.description = description if description else "لا توجد بيانات نشاط"
    else:
        embed.description = "لا توجد بيانات نشاط لهذه الفترة"
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="إحصائيات_عضو", description="إحصائيات مفصلة لعضو")
@discord.app_commands.describe(
    العضو="العضو المراد عرض إحصائياته"
)
async def member_stats(interaction: discord.Interaction, العضو: discord.Member):
    # Get member's activity
    week_ago = datetime.utcnow() - timedelta(days=7)
    month_ago = datetime.utcnow() - timedelta(days=30)
    
    week_messages = await db.server_activity.count_documents({
        "guild_id": interaction.guild.id,
        "user_id": العضو.id,
        "type": "message",
        "timestamp": {"$gte": week_ago}
    })
    
    month_messages = await db.server_activity.count_documents({
        "guild_id": interaction.guild.id,
        "user_id": العضو.id,
        "type": "message",
        "timestamp": {"$gte": month_ago}
    })
    
    violations = await get_user_violations(العضو.id, interaction.guild.id)
    
    embed = discord.Embed(
        title=f"📊 إحصائيات {العضو.display_name}",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )
    
    embed.set_thumbnail(url=العضو.display_avatar.url)
    
    embed.add_field(name="💬 الرسائل - الأسبوع", value=str(week_messages), inline=True)
    embed.add_field(name="💬 الرسائل - الشهر", value=str(month_messages), inline=True)
    embed.add_field(name="⚠️ المخالفات", value=str(violations), inline=True)
    
    embed.add_field(
        name="📅 معلومات العضوية",
        value=f"**انضم في:** {العضو.joined_at.strftime('%Y-%m-%d') if العضو.joined_at else 'غير محدد'}\n**تاريخ الإنشاء:** {العضو.created_at.strftime('%Y-%m-%d')}",
        inline=False
    )
    
    if العضو.roles[1:]:  # Exclude @everyone
        roles = ", ".join([role.name for role in العضو.roles[1:][:5]])
        if len(العضو.roles) > 6:
            roles += f" و {len(العضو.roles) - 6} آخرين"
        embed.add_field(name="🎭 الأدوار", value=roles, inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="نمو_الخادم", description="إحصائيات نمو الخادم")
async def server_growth(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.view_audit_log:
        await interaction.response.send_message("❌ ليس لديك صلاحية لعرض إحصائيات النمو", ephemeral=True)
        return
    
    guild = interaction.guild
    
    # Calculate growth periods
    now = datetime.utcnow()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)
    
    # Count new members (approximation based on join dates)
    week_joins = len([m for m in guild.members if m.joined_at and m.joined_at >= week_ago])
    month_joins = len([m for m in guild.members if m.joined_at and m.joined_at >= month_ago])
    
    embed = discord.Embed(
        title="📈 نمو الخادم",
        color=discord.Color.green(),
        timestamp=discord.utils.utcnow()
    )
    
    embed.add_field(name="👥 الأعضاء الحاليين", value=str(guild.member_count), inline=True)
    embed.add_field(name="📅 الأسبوع الماضي", value=f"+{week_joins} عضو", inline=True)
    embed.add_field(name="📅 الشهر الماضي", value=f"+{month_joins} عضو", inline=True)
    
    # Server age
    server_age = (now - guild.created_at).days
    embed.add_field(
        name="📊 معدل النمو",
        value=f"**عمر الخادم:** {server_age} يوم\n**المعدل اليومي:** {guild.member_count / max(server_age, 1):.1f} عضو/يوم",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="تقرير_مخالفات", description="تقرير شامل للمخالفات")
async def violations_report(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ مطلوب صلاحية المدير", ephemeral=True)
        return
    
    # Get all violations for this guild
    violations = await db.moderation_logs.find({
        "guild_id": interaction.guild.id
    }).to_list(length=None)
    
    if not violations:
        embed = discord.Embed(
            title="📋 تقرير المخالفات",
            description="✅ لا توجد مخالفات مسجلة",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
        return
    
    # Analyze violations
    total_violations = len(violations)
    violation_types = {}
    top_violators = {}
    
    for violation in violations:
        # Count by type
        v_type = violation["action_type"]
        violation_types[v_type] = violation_types.get(v_type, 0) + 1
        
        # Count by user
        user_id = violation["target_user_id"]
        top_violators[user_id] = top_violators.get(user_id, 0) + 1
    
    embed = discord.Embed(
        title="📋 تقرير المخالفات الشامل",
        color=discord.Color.orange(),
        timestamp=discord.utils.utcnow()
    )
    
    embed.add_field(name="📊 إجمالي المخالفات", value=str(total_violations), inline=True)
    
    # Types breakdown
    types_text = "\n".join([f"**{v_type}:** {count}" for v_type, count in sorted(violation_types.items(), key=lambda x: x[1], reverse=True)])
    embed.add_field(name="📈 أنواع المخالفات", value=types_text, inline=True)
    
    # Top violators
    sorted_violators = sorted(top_violators.items(), key=lambda x: x[1], reverse=True)[:5]
    violators_text = ""
    for user_id, count in sorted_violators:
        try:
            user = interaction.guild.get_member(user_id)
            name = user.display_name if user else f"مستخدم محذوف ({user_id})"
            violators_text += f"**{name}:** {count}\n"
        except:
            violators_text += f"**مستخدم محذوف:** {count}\n"
    
    if violators_text:
        embed.add_field(name="🔝 أكثر المخالفين", value=violators_text, inline=True)
    
    await interaction.response.send_message(embed=embed)

# ====================
# GENERAL COMMANDS
# ====================

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

@bot.tree.command(name="مساعدة", description="عرض قائمة الأوامر")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📋 قائمة أوامر البوت",
        description="جميع الأوامر المتاحة للبوت",
        color=discord.Color.blue()
    )
    
    # Moderation commands
    mod_commands = """
    • `/مسح [عدد]` - مسح رسائل
    • `/كتم @عضو [دقائق] [سبب]` - كتم عضو
    • `/فك_كتم @عضو` - فك كتم
    • `/طرد @عضو [سبب]` - طرد عضو
    • `/حظر @عضو [سبب]` - حظر عضو
    • `/فك_حظر [معرف_العضو]` - فك حظر عضو
    • `/تحذير @عضو [سبب]` - إعطاء تحذير
    """
    embed.add_field(name="🛡️ أوامر الإدارة", value=mod_commands, inline=False)
    
    # Announcement commands
    announce_commands = """
    • `/إعلان [عنوان] [محتوى]` - إنشاء إعلان
    • `/استبيان [سؤال] [خيارات]` - إنشاء استبيان
    • `/الأعضاء_النشطين` - عرض الأعضاء المتصلين
    • `/المخالفات @عضو` - عرض مخالفات عضو
    """
    embed.add_field(name="📢 أوامر الإعلانات", value=announce_commands, inline=False)
    
    # Reports commands
    report_commands = """
    • `/تقرير_يومي` - تقرير يومي شامل
    • `/أكثر_نشاط [فترة]` - أكثر الأعضاء نشاطاً
    • `/إحصائيات_عضو @عضو` - إحصائيات مفصلة لعضو
    • `/نمو_الخادم` - إحصائيات نمو الخادم
    • `/تقرير_مخالفات` - تقرير شامل للمخالفات
    """
    embed.add_field(name="📊 أوامر التقارير المتقدمة", value=report_commands, inline=False)
    
    # General commands
    general_commands = """
    • `/اختبار` - اختبار البوت
    • `/مساعدة` - هذه القائمة
    • `/الإحصائيات` - إحصائيات الخادم الأساسية
    """
    embed.add_field(name="ℹ️ أوامر عامة", value=general_commands, inline=False)
    
    embed.set_footer(text="استخدم / قبل كل أمر | جميع الأوامر باللغة العربية")
    
    await interaction.response.send_message(embed=embed)

# Error handling
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    
    logger.error(f"Command error: {error}")
    
    if hasattr(ctx, 'send'):
        await ctx.send("❌ حدث خطأ أثناء تنفيذ الأمر")

# Run the bot
async def run_discord_bot():
    try:
        await bot.start(os.environ['DISCORD_BOT_TOKEN'])
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")

if __name__ == "__main__":
    asyncio.run(run_discord_bot())