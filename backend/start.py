#!/usr/bin/env python3
"""
Start script for Discord Bot Web Service on Render
This is the main entry point that Render will execute
"""

import os
import sys
import asyncio
import threading
import logging
from pathlib import Path
from dotenv import load_dotenv
import uvicorn

# Add the current directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# Load environment variables
load_dotenv()

# Configure logging for Render
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

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
    
    logger.info("All required environment variables are set")
    return True

def start_discord_bot():
    """Start Discord bot in a separate thread"""
    def run_bot():
        try:
            logger.info("Starting Discord bot in background thread...")
            from discord_bot import run_discord_bot
            asyncio.run(run_discord_bot())
        except Exception as e:
            logger.error(f"Discord bot error: {e}")
    
    # Start bot in daemon thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    logger.info("Discord bot thread started")

def main():
    """Main function to start both web server and Discord bot"""
    try:
        logger.info("=" * 50)
        logger.info("🚀 Starting Discord Bot Web Service on Render")
        logger.info("=" * 50)
        
        # Check environment variables
        if not check_environment():
            logger.error("❌ Environment check failed")
            sys.exit(1)
        
        # Start Discord bot in background
        logger.info("🤖 Starting Discord bot...")
        start_discord_bot()
        
        # Get port from environment (Render sets this automatically)
        port = int(os.environ.get('PORT', 10000))
        
        logger.info(f"🌐 Starting FastAPI web server on port {port}...")
        
        # Import and run FastAPI server
        from server import app
        
        # Run FastAPI server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("⏹️ Service stopped by user")
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        logger.exception("Full error details:")
        sys.exit(1)

if __name__ == "__main__":
    main()