import requests
import json
import time
import unittest
import os
from datetime import datetime, timedelta

# Get the backend URL from environment variables
BACKEND_URL = "https://9c30fc51-e4c0-4eec-b50d-c874183f13e8.preview.emergentagent.com/api"

class DiscordBotAPITest(unittest.TestCase):
    
    def setUp(self):
        # Ensure the bot is stopped before each test
        self.stop_bot()
        time.sleep(1)  # Give it time to stop
    
    def tearDown(self):
        # Clean up after tests by stopping the bot
        self.stop_bot()
    
    def stop_bot(self):
        """Helper method to stop the bot"""
        response = requests.post(f"{BACKEND_URL}/bot/stop")
        return response.json()
    
    def test_api_root(self):
        """Test the API root endpoint"""
        response = requests.get(f"{BACKEND_URL}/")
        data = response.json()
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data["message"], "Discord Bot Management API")
        self.assertEqual(data["status"], "running")
        
    def test_status_endpoint(self):
        """Test the status endpoint"""
        response = requests.get(f"{BACKEND_URL}/status")
        data = response.json()
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(isinstance(data, list))
        # This endpoint returns a list of status checks
    
    def test_bot_status(self):
        """Test the bot status endpoint"""
        response = requests.get(f"{BACKEND_URL}/bot/status")
        data = response.json()
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("status", data)
        # Bot should be stopped at this point
        self.assertEqual(data["status"], "stopped")
        self.assertIsNone(data["pid"])
    
    def test_bot_start_stop(self):
        """Test starting and stopping the bot"""
        # Start the bot
        start_response = requests.post(f"{BACKEND_URL}/bot/start")
        start_data = start_response.json()
        
        self.assertEqual(start_response.status_code, 200)
        self.assertIn("message", start_data)
        self.assertIn("Bot started successfully", start_data["message"])
        self.assertIn("status", start_data)
        self.assertIn("pid", start_data["status"])
        self.assertIsNotNone(start_data["status"]["pid"])
        
        # Check status after starting
        time.sleep(2)  # Give it time to start
        status_response = requests.get(f"{BACKEND_URL}/bot/status")
        status_data = status_response.json()
        
        self.assertEqual(status_response.status_code, 200)
        self.assertIn("status", status_data)
        # Bot should be either starting or running
        self.assertIn(status_data["status"], ["starting", "running"])
        
        # Stop the bot
        stop_response = requests.post(f"{BACKEND_URL}/bot/stop")
        stop_data = stop_response.json()
        
        self.assertEqual(stop_response.status_code, 200)
        self.assertIn("message", stop_data)
        self.assertIn("Bot stopped successfully", stop_data["message"])
        
        # Check status after stopping
        time.sleep(2)  # Give it time to stop
        status_response = requests.get(f"{BACKEND_URL}/bot/status")
        status_data = status_response.json()
        
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_data["status"], "stopped")
        self.assertIsNone(status_data["pid"])
    
    def test_bot_restart(self):
        """Test restarting the bot"""
        # Start the bot first
        requests.post(f"{BACKEND_URL}/bot/start")
        time.sleep(2)  # Give it time to start
        
        # Restart the bot
        restart_response = requests.post(f"{BACKEND_URL}/bot/restart")
        restart_data = restart_response.json()
        
        self.assertEqual(restart_response.status_code, 200)
        self.assertIn("message", restart_data)
        self.assertIn("Bot started successfully", restart_data["message"])
        
        # Check status after restarting
        time.sleep(2)  # Give it time to restart
        status_response = requests.get(f"{BACKEND_URL}/bot/status")
        status_data = status_response.json()
        
        self.assertEqual(status_response.status_code, 200)
        self.assertIn(status_data["status"], ["starting", "running"])
    
    def test_bot_logs(self):
        """Test retrieving bot logs"""
        # Start the bot to generate some logs
        requests.post(f"{BACKEND_URL}/bot/start")
        time.sleep(3)  # Give it time to generate logs
        
        # Get logs
        logs_response = requests.get(f"{BACKEND_URL}/bot/logs")
        logs_data = logs_response.json()
        
        self.assertEqual(logs_response.status_code, 200)
        self.assertIn("logs", logs_data)
        # Either we have logs or a message saying no logs found
        self.assertTrue(isinstance(logs_data["logs"], list))
    
    def test_moderation_logs(self):
        """Test retrieving moderation logs"""
        response = requests.get(f"{BACKEND_URL}/bot/moderation-logs")
        data = response.json()
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("logs", data)
        self.assertIn("total", data)
        self.assertTrue(isinstance(data["logs"], list))
        self.assertTrue(isinstance(data["total"], int))
    
    def test_server_activity(self):
        """Test retrieving server activity"""
        response = requests.get(f"{BACKEND_URL}/bot/server-activity")
        data = response.json()
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("period_days", data)
        self.assertIn("total_messages", data)
        self.assertIn("active_users", data)
        self.assertIn("top_users", data)
        self.assertIn("daily_breakdown", data)
    
    def test_daily_report(self):
        """Test retrieving daily report"""
        response = requests.get(f"{BACKEND_URL}/bot/reports/daily")
        data = response.json()
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("date", data)
        self.assertIn("moderation_actions", data)
        self.assertIn("total_moderation_actions", data)
        self.assertIn("message_count", data)
        self.assertIn("total_activities", data)
    
    def test_violations_report(self):
        """Test retrieving violations report"""
        response = requests.get(f"{BACKEND_URL}/bot/reports/violations")
        data = response.json()
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("guild_id", data)
        self.assertIn("total_violations", data)
        self.assertIn("violation_types", data)
        self.assertIn("top_violators", data)

if __name__ == "__main__":
    unittest.main(argv=['first-arg-is-ignored'], exit=False)