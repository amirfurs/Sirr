#!/usr/bin/env python3
"""
Main entry point for the Discord bot on Render
This file handles environment setup and starts the bot
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment variables from .env file
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

async def main():
    """Main function to start the Discord bot"""
    try:
        logger.info("Starting Discord Bot with Arabic Commands...")
        
        # Check environment variables
        if not check_environment():
            sys.exit(1)
        
        # Import and run the bot
        from discord_bot import run_discord_bot
        
        logger.info("Initializing Discord bot...")
        await run_discord_bot()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)