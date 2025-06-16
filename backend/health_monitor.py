#!/usr/bin/env python3
"""
Health Monitor Script for Render Deployment
This script can be run periodically to keep the service alive and monitor its health
"""

import requests
import time
import logging
import os
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - Health Monitor - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def ping_service(base_url):
    """Ping the service to keep it alive"""
    try:
        # Health check endpoint
        health_response = requests.get(f"{base_url}/api/health", timeout=30)
        health_data = health_response.json()
        
        logger.info("✅ Health Check Response:")
        logger.info(f"  - Status: {health_data.get('status')}")
        logger.info(f"  - Bot Status: {health_data.get('bot_status')}")
        logger.info(f"  - Database: {health_data.get('database_status')}")
        
        if health_data.get('system_resources'):
            resources = health_data['system_resources']
            logger.info(f"  - Memory: {resources.get('memory_mb')} MB")
            logger.info(f"  - CPU: {resources.get('cpu_percent')}%")
        
        # Keep-alive ping
        keep_alive_response = requests.get(f"{base_url}/api/keep-alive", timeout=10)
        if keep_alive_response.status_code == 200:
            logger.info("✅ Keep-alive ping successful")
        
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ Service ping failed: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        return False

def monitor_service(base_url, interval_minutes=5):
    """Monitor service health at regular intervals"""
    logger.info(f"🔍 Starting health monitor for {base_url}")
    logger.info(f"📅 Check interval: {interval_minutes} minutes")
    
    consecutive_failures = 0
    max_failures = 3
    
    while True:
        try:
            logger.info(f"⏰ Health check at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            if ping_service(base_url):
                consecutive_failures = 0
                logger.info(f"😴 Sleeping for {interval_minutes} minutes...")
            else:
                consecutive_failures += 1
                logger.warning(f"⚠️ Consecutive failures: {consecutive_failures}/{max_failures}")
                
                if consecutive_failures >= max_failures:
                    logger.error("🚨 Service appears to be down after multiple checks!")
                    # You could add notification logic here (email, webhook, etc.)
            
            time.sleep(interval_minutes * 60)
            
        except KeyboardInterrupt:
            logger.info("⏹️ Health monitor stopped by user")
            break
        except Exception as e:
            logger.error(f"💥 Monitor error: {e}")
            time.sleep(60)  # Wait 1 minute before retrying

if __name__ == "__main__":
    # Default to localhost for testing, but can be overridden
    service_url = os.environ.get('SERVICE_URL', 'http://localhost:10000')
    interval = int(os.environ.get('CHECK_INTERVAL_MINUTES', '5'))
    
    logger.info("🚀 Discord Bot Health Monitor")
    logger.info(f"🎯 Target URL: {service_url}")
    
    monitor_service(service_url, interval)