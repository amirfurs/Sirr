from fastapi import FastAPI, APIRouter, HTTPException, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import asyncio
import threading
from discord_bot import bot, run_discord_bot

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Discord Bot Management API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

class ModerationLog(BaseModel):
    id: str
    action_type: str
    target_user_id: int
    moderator_id: int
    guild_id: int
    reason: str
    duration: Optional[int] = None
    timestamp: datetime

class ServerStats(BaseModel):
    guild_id: int
    guild_name: str
    member_count: int
    online_count: int
    channel_count: int
    role_count: int
    timestamp: datetime

class AnnouncementRequest(BaseModel):
    channel_id: int
    title: str
    content: str

# Original API routes
@api_router.get("/")
async def root():
    return {"message": "Discord Bot Management API", "status": "running"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Discord Bot API Routes
@api_router.get("/bot/status")
async def get_bot_status():
    """Get Discord bot status"""
    if bot.is_ready():
        return {
            "status": "online",
            "latency": round(bot.latency * 1000),
            "guilds": len(bot.guilds),
            "users": len(bot.users)
        }
    else:
        return {"status": "offline"}

@api_router.get("/bot/guilds")
async def get_bot_guilds():
    """Get list of guilds the bot is in"""
    if not bot.is_ready():
        raise HTTPException(status_code=503, detail="Bot is not ready")
    
    guilds = []
    for guild in bot.guilds:
        guilds.append({
            "id": guild.id,
            "name": guild.name,
            "member_count": guild.member_count,
            "icon": str(guild.icon.url) if guild.icon else None,
            "owner_id": guild.owner_id
        })
    return {"guilds": guilds}

@api_router.get("/bot/guilds/{guild_id}/stats")
async def get_guild_stats(guild_id: int):
    """Get statistics for a specific guild"""
    if not bot.is_ready():
        raise HTTPException(status_code=503, detail="Bot is not ready")
    
    guild = bot.get_guild(guild_id)
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
    
    # Calculate stats
    online = len([m for m in guild.members if m.status.name == "online"])
    idle = len([m for m in guild.members if m.status.name == "idle"])
    dnd = len([m for m in guild.members if m.status.name == "dnd"])
    offline = len([m for m in guild.members if m.status.name == "offline"])
    
    bots = len([m for m in guild.members if m.bot])
    humans = len([m for m in guild.members if not m.bot])
    
    stats = {
        "guild_id": guild_id,
        "guild_name": guild.name,
        "member_count": guild.member_count,
        "online_count": online,
        "idle_count": idle,
        "dnd_count": dnd,
        "offline_count": offline,
        "bot_count": bots,
        "human_count": humans,
        "channel_count": len(guild.channels),
        "text_channel_count": len(guild.text_channels),
        "voice_channel_count": len(guild.voice_channels),
        "role_count": len(guild.roles),
        "created_at": guild.created_at.isoformat(),
        "owner_id": guild.owner_id
    }
    
    return stats

@api_router.get("/bot/guilds/{guild_id}/moderation-logs")
async def get_guild_moderation_logs(guild_id: int, limit: int = 50):
    """Get moderation logs for a guild"""
    logs = await db.moderation_logs.find({
        "guild_id": guild_id
    }).sort("timestamp", -1).limit(limit).to_list(length=limit)
    
    return {"logs": logs, "total": len(logs)}

@api_router.get("/bot/guilds/{guild_id}/members")
async def get_guild_members(guild_id: int, limit: int = 100):
    """Get list of guild members"""
    if not bot.is_ready():
        raise HTTPException(status_code=503, detail="Bot is not ready")
    
    guild = bot.get_guild(guild_id)
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
    
    members = []
    for member in guild.members[:limit]:
        members.append({
            "id": member.id,
            "name": member.display_name,
            "username": member.name,
            "discriminator": member.discriminator,
            "avatar": str(member.display_avatar.url),
            "status": str(member.status),
            "joined_at": member.joined_at.isoformat() if member.joined_at else None,
            "created_at": member.created_at.isoformat(),
            "roles": [role.name for role in member.roles if role.name != "@everyone"],
            "is_bot": member.bot
        })
    
    return {"members": members, "total": len(members)}

@api_router.get("/bot/guilds/{guild_id}/channels")
async def get_guild_channels(guild_id: int):
    """Get list of guild channels"""
    if not bot.is_ready():
        raise HTTPException(status_code=503, detail="Bot is not ready")
    
    guild = bot.get_guild(guild_id)
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
    
    channels = []
    for channel in guild.channels:
        channels.append({
            "id": channel.id,
            "name": channel.name,
            "type": str(channel.type),
            "category": channel.category.name if channel.category else None,
            "position": channel.position
        })
    
    return {"channels": channels}

@api_router.post("/bot/guilds/{guild_id}/announce")
async def create_guild_announcement(guild_id: int, announcement: AnnouncementRequest):
    """Create an announcement in a specific channel"""
    if not bot.is_ready():
        raise HTTPException(status_code=503, detail="Bot is not ready")
    
    guild = bot.get_guild(guild_id)
    if not guild:
        raise HTTPException(status_code=404, detail="Guild not found")
    
    channel = guild.get_channel(announcement.channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    try:
        import discord
        embed = discord.Embed(
            title=f"📢 {announcement.title}",
            description=announcement.content,
            color=discord.Color.blue(),
            timestamp=datetime.utcnow()
        )
        
        await channel.send(embed=embed)
        return {"success": True, "message": "Announcement sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send announcement: {str(e)}")

@api_router.get("/bot/guilds/{guild_id}/reports/daily")
async def get_daily_report(guild_id: int):
    """Generate daily report for a guild"""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Get today's moderation actions
    mod_actions = await db.moderation_logs.find({
        "guild_id": guild_id,
        "timestamp": {"$gte": today}
    }).to_list(length=None)
    
    # Get today's activity
    activities = await db.server_activity.find({
        "guild_id": guild_id,
        "timestamp": {"$gte": today}
    }).to_list(length=None)
    
    # Summarize moderation actions
    mod_summary = {}
    for action in mod_actions:
        action_type = action["action_type"]
        mod_summary[action_type] = mod_summary.get(action_type, 0) + 1
    
    # Count messages
    message_count = len([a for a in activities if a.get("type") == "message"])
    
    return {
        "date": today.isoformat(),
        "moderation_actions": mod_summary,
        "total_moderation_actions": len(mod_actions),
        "message_count": message_count,
        "total_activities": len(activities)
    }

@api_router.get("/bot/guilds/{guild_id}/reports/violations")
async def get_violations_report(guild_id: int):
    """Generate comprehensive violations report"""
    violations = await db.moderation_logs.find({
        "guild_id": guild_id
    }).to_list(length=None)
    
    if not violations:
        return {
            "total_violations": 0,
            "violation_types": {},
            "top_violators": []
        }
    
    # Analyze violations
    violation_types = {}
    top_violators = {}
    
    for violation in violations:
        # Count by type
        v_type = violation["action_type"]
        violation_types[v_type] = violation_types.get(v_type, 0) + 1
        
        # Count by user
        user_id = violation["target_user_id"]
        top_violators[user_id] = top_violators.get(user_id, 0) + 1
    
    # Sort top violators
    sorted_violators = sorted(top_violators.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        "total_violations": len(violations),
        "violation_types": violation_types,
        "top_violators": [{"user_id": user_id, "count": count} for user_id, count in sorted_violators]
    }

@api_router.get("/bot/guilds/{guild_id}/activity/stats")
async def get_activity_stats(guild_id: int, days: int = 7):
    """Get activity statistics for a period"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    activities = await db.server_activity.find({
        "guild_id": guild_id,
        "timestamp": {"$gte": start_date},
        "type": "message"
    }).to_list(length=None)
    
    # Count messages per user
    user_activity = {}
    daily_activity = {}
    
    for activity in activities:
        user_id = activity["user_id"]
        user_activity[user_id] = user_activity.get(user_id, 0) + 1
        
        # Daily breakdown
        day = activity["timestamp"].strftime("%Y-%m-%d")
        daily_activity[day] = daily_activity.get(day, 0) + 1
    
    # Sort by activity
    sorted_users = sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        "period_days": days,
        "total_messages": len(activities),
        "active_users": len(user_activity),
        "top_users": [{"user_id": user_id, "message_count": count} for user_id, count in sorted_users],
        "daily_breakdown": daily_activity
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """Start the Discord bot when FastAPI starts"""
    logger.info("Starting Discord bot...")
    
    # Start Discord bot in a separate thread
    def start_bot():
        asyncio.run(run_discord_bot())
    
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    
    logger.info("Discord bot started in background")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
    logger.info("Database connection closed")

# Health check endpoint
@api_router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "bot_status": "online" if bot.is_ready() else "offline"
    }