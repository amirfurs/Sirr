#!/usr/bin/env python3
"""
Robust start script for Discord Bot Web Service on Render
This is the main entry point that Render will execute
"""

import os
import sys
import asyncio
import threading
import logging
import time
import signal
from pathlib import Path
from dotenv import load_dotenv
import uvicorn
import psutil

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Load environment variables
load_dotenv()

# Configure logging for Render with better formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Global variables for bot management
bot_thread = None
bot_running = False
app_shutdown = False

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = ['DISCORD_BOT_TOKEN', 'MONGO_URL', 'DB_NAME']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please set these variables in your Render dashboard:")
        for var in missing_vars:
            logger.error(f"  - {var}")
        return False
    
    logger.info("✅ All required environment variables are set")
    
    # Log some debug info (without sensitive data)
    logger.info(f"DB_NAME: {os.environ.get('DB_NAME')}")
    logger.info(f"PORT: {os.environ.get('PORT', '10000')}")
    logger.info(f"DISCORD_BOT_TOKEN: {'*' * 20}...{os.environ.get('DISCORD_BOT_TOKEN', '')[-6:]}")
    
    return True

def log_system_resources():
    """Log system resource usage"""
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        cpu_percent = process.cpu_percent()
        
        logger.info(f"📊 System Resources:")
        logger.info(f"  - Memory: {memory_info.rss / 1024 / 1024:.2f} MB")
        logger.info(f"  - CPU: {cpu_percent:.2f}%")
        
        # System resources
        system_memory = psutil.virtual_memory()
        logger.info(f"  - System Memory: {system_memory.percent:.1f}% used")
        
    except Exception as e:
        logger.warning(f"Could not log system resources: {e}")

def run_bot_with_recovery():
    """Run Discord bot with automatic recovery"""
    global bot_running, app_shutdown
    
    retry_count = 0
    max_retries = 5
    
    while not app_shutdown and retry_count < max_retries:
        try:
            logger.info(f"🤖 Starting Discord bot (attempt {retry_count + 1}/{max_retries})")
            bot_running = True
            
            from discord_bot import run_discord_bot
            asyncio.run(run_discord_bot())
            
        except Exception as e:
            bot_running = False
            retry_count += 1
            logger.error(f"❌ Discord bot crashed: {e}")
            
            if retry_count < max_retries and not app_shutdown:
                wait_time = min(30 * retry_count, 300)  # Max 5 minutes
                logger.info(f"🔄 Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                logger.error(f"💥 Bot failed after {max_retries} attempts")
                break
    
    bot_running = False
    logger.info("🛑 Bot thread terminated")

def start_discord_bot():
    """Start Discord bot in a separate thread with recovery"""
    global bot_thread
    
    # Start bot in a non-daemon thread so it can be properly managed
    bot_thread = threading.Thread(target=run_bot_with_recovery, daemon=False)
    bot_thread.start()
    logger.info("✅ Discord bot thread started with recovery mechanism")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    global app_shutdown
    logger.info(f"🛑 Received signal {signum}, shutting down gracefully...")
    app_shutdown = True

def health_check_loop():
    """Periodic health check to keep service alive"""
    ping_count = 0
    while not app_shutdown:
        try:
            time.sleep(300)  # Check every 5 minutes (reduced from 1 minute)
            ping_count += 1
            
            if not app_shutdown:
                # Self-ping to keep alive on Render free tier
                try:
                    import requests
                    port = os.environ.get('PORT', '10000')
                    response = requests.get(f'http://localhost:{port}/api/keep-alive', timeout=5)
                    if response.status_code == 200:
                        logger.info(f"💓 Self-ping #{ping_count} successful - Service staying alive")
                    else:
                        logger.warning(f"⚠️ Self-ping returned status {response.status_code}")
                except Exception as ping_error:
                    logger.warning(f"⚠️ Self-ping failed: {ping_error}")
                
                # Log system resources every 30 minutes only
                if ping_count % 6 == 0:  # Every 6th ping (30 minutes)
                    log_system_resources()
                    logger.info(f"📊 Health check #{ping_count} - Detailed resources logged")
                
                # Check bot status
                if bot_thread and bot_thread.is_alive():
                    logger.info("✅ Discord bot thread is running")
                else:
                    logger.warning("⚠️ Discord bot thread is not running")
                    
        except Exception as e:
            logger.error(f"Health check error: {e}")

def main():
    """Main function to start both web server and Discord bot"""
    global app_shutdown
    
    try:
        logger.info("=" * 60)
        logger.info("🚀 Starting Discord Bot Web Service on Render")
        logger.info("=" * 60)
        
        # Set up signal handlers
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        # Check environment variables
        if not check_environment():
            logger.error("❌ Environment check failed")
            sys.exit(1)
        
        # Log initial system resources
        log_system_resources()
        
        # Start Discord bot in background
        logger.info("🤖 Starting Discord bot with recovery mechanism...")
        start_discord_bot()
        
        # Start health check in background
        health_thread = threading.Thread(target=health_check_loop, daemon=True)
        health_thread.start()
        logger.info("✅ Health check thread started")
        
        # Get port from environment (Render sets this automatically)
        port = int(os.environ.get('PORT', 10000))
        
        logger.info(f"🌐 Starting FastAPI web server on port {port}...")
        
        # Import and run FastAPI server
        from server import app
        
        # Run FastAPI server with optimized configuration for Render
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="warning" if os.environ.get('RENDER') else "info",  # Less logging in production
            access_log=False if os.environ.get('RENDER') else True,      # Disable access log in production
            timeout_keep_alive=30,
            timeout_graceful_shutdown=30,
            loop="asyncio"  # Use asyncio loop
        )
        
    except KeyboardInterrupt:
        logger.info("⏹️ Service stopped by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        logger.exception("Full error details:")
        sys.exit(1)
    finally:
        app_shutdown = True
        logger.info("🧹 Cleanup completed")

if __name__ == "__main__":
    main()