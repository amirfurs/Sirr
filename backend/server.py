from fastapi import FastAPI, APIRouter, HTTPException
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
import subprocess
import sys
import signal
import psutil
import asyncio

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

# Global variables for bot process management
bot_process = None
bot_status = {"status": "stopped", "pid": None, "started_at": None}

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

# Discord Bot Management Routes
@api_router.get("/bot/status")
async def get_bot_status():
    """Get Discord bot status"""
    global bot_status
    
    # Check if process is actually running
    if bot_status["pid"]:
        try:
            process = psutil.Process(bot_status["pid"])
            if process.is_running():
                bot_status["status"] = "running"
            else:
                bot_status["status"] = "stopped"
                bot_status["pid"] = None
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            bot_status["status"] = "stopped"
            bot_status["pid"] = None
    
    return bot_status

@api_router.post("/bot/start")
async def start_bot():
    """Start the Discord bot"""
    global bot_process, bot_status
    
    if bot_status["status"] == "running":
        return {"message": "Bot is already running", "status": bot_status}
    
    try:
        # Start the Discord bot as a separate process
        bot_process = subprocess.Popen(
            [sys.executable, "discord_bot.py"],
            cwd=ROOT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        bot_status = {
            "status": "starting",
            "pid": bot_process.pid,
            "started_at": datetime.utcnow().isoformat()
        }
        
        return {"message": "Bot started successfully", "status": bot_status}
    
    except Exception as e:
        return {"message": f"Failed to start bot: {str(e)}", "status": "error"}

@api_router.post("/bot/stop")
async def stop_bot():
    """Stop the Discord bot"""
    global bot_process, bot_status
    
    if bot_status["status"] == "stopped":
        return {"message": "Bot is already stopped", "status": bot_status}
    
    try:
        if bot_process and bot_status["pid"]:
            try:
                # Try to terminate gracefully
                process = psutil.Process(bot_status["pid"])
                process.terminate()
                
                # Wait up to 5 seconds for graceful shutdown
                try:
                    process.wait(timeout=5)
                except psutil.TimeoutExpired:
                    # Force kill if it doesn't terminate gracefully
                    process.kill()
                
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass  # Process already dead
        
        bot_status = {
            "status": "stopped",
            "pid": None,
            "started_at": None
        }
        
        return {"message": "Bot stopped successfully", "status": bot_status}
    
    except Exception as e:
        return {"message": f"Failed to stop bot: {str(e)}", "status": "error"}

@api_router.post("/bot/restart")
async def restart_bot():
    """Restart the Discord bot"""
    stop_response = await stop_bot()
    if "error" in stop_response.get("status", ""):
        return stop_response
    
    # Wait a moment before restarting
    await asyncio.sleep(2)
    
    return await start_bot()

@api_router.get("/bot/logs")
async def get_bot_logs():
    """Get recent bot logs"""
    try:
        log_file = ROOT_DIR / "bot.log"
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                recent_lines = lines[-50:]  # Get last 50 lines
                return {"logs": recent_lines}
        else:
            return {"logs": ["No log file found"]}
    except Exception as e:
        return {"logs": [f"Error reading logs: {str(e)}"]}

# Database API Routes for Discord Bot Data
@api_router.get("/bot/moderation-logs")
async def get_moderation_logs(guild_id: Optional[int] = None, limit: int = 50):
    """Get moderation logs"""
    query = {}
    if guild_id:
        query["guild_id"] = guild_id
    
    logs = await db.moderation_logs.find(query).sort("timestamp", -1).limit(limit).to_list(length=limit)
    return {"logs": logs, "total": len(logs)}

@api_router.get("/bot/server-activity")
async def get_server_activity(guild_id: Optional[int] = None, days: int = 7):
    """Get server activity statistics"""
    start_date = datetime.utcnow() - timedelta(days=days)
    
    query = {"timestamp": {"$gte": start_date}}
    if guild_id:
        query["guild_id"] = guild_id
    
    activities = await db.server_activity.find(query).to_list(length=None)
    
    # Count messages per user
    user_activity = {}
    daily_activity = {}
    
    for activity in activities:
        if activity.get("type") == "message":
            user_id = activity["user_id"]
            user_activity[user_id] = user_activity.get(user_id, 0) + 1
            
            # Daily breakdown
            day = activity["timestamp"].strftime("%Y-%m-%d")
            daily_activity[day] = daily_activity.get(day, 0) + 1
    
    # Sort by activity
    sorted_users = sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:10]
    
    return {
        "period_days": days,
        "total_messages": len([a for a in activities if a.get("type") == "message"]),
        "active_users": len(user_activity),
        "top_users": [{"user_id": user_id, "message_count": count} for user_id, count in sorted_users],
        "daily_breakdown": daily_activity
    }

@api_router.get("/bot/reports/daily")
async def get_daily_report(guild_id: Optional[int] = None):
    """Generate daily report"""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    query = {"timestamp": {"$gte": today}}
    if guild_id:
        query["guild_id"] = guild_id
    
    # Get today's moderation actions
    mod_actions = await db.moderation_logs.find(query).to_list(length=None)
    
    # Get today's activity
    activities = await db.server_activity.find(query).to_list(length=None)
    
    # Summarize moderation actions
    mod_summary = {}
    for action in mod_actions:
        action_type = action["action_type"]
        mod_summary[action_type] = mod_summary.get(action_type, 0) + 1
    
    # Count messages
    message_count = len([a for a in activities if a.get("type") == "message"])
    
    return {
        "date": today.isoformat(),
        "guild_id": guild_id,
        "moderation_actions": mod_summary,
        "total_moderation_actions": len(mod_actions),
        "message_count": message_count,
        "total_activities": len(activities)
    }

@api_router.get("/bot/reports/violations")
async def get_violations_report(guild_id: Optional[int] = None):
    """Generate comprehensive violations report"""
    query = {}
    if guild_id:
        query["guild_id"] = guild_id
    
    violations = await db.moderation_logs.find(query).to_list(length=None)
    
    if not violations:
        return {
            "guild_id": guild_id,
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
        "guild_id": guild_id,
        "total_violations": len(violations),
        "violation_types": violation_types,
        "top_violators": [{"user_id": user_id, "count": count} for user_id, count in sorted_violators]
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
    logger.info("FastAPI server starting...")
    logger.info("Discord bot can be started via /api/bot/start endpoint")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global bot_process, bot_status
    
    # Stop bot process if running
    if bot_status["status"] == "running" and bot_status["pid"]:
        try:
            process = psutil.Process(bot_status["pid"])
            process.terminate()
            process.wait(timeout=5)
        except:
            pass
    
    # Close database connection
    client.close()
    logger.info("FastAPI server shutting down...")

# Health check endpoint
@api_router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "bot_status": bot_status["status"]
    }