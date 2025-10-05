"""
Alert System for Circuit Breakers 3D Printer Monitoring
Handles Discord notifications for print failures
"""

import time
from datetime import datetime, timedelta
import requests
import json
import pytz

try:
    from config import (
        DISCORD_WEBHOOK_URL, SEND_DISCORD_ALERTS, ALERT_COOLDOWN_MINUTES
    )
except ImportError:
    print("⚠️ Warning: config.py not found. Alert system disabled.")
    SEND_DISCORD_ALERTS = False

class AlertSystem:
    def __init__(self):
        self.last_alert_time = None
        self.alert_cooldown = timedelta(minutes=ALERT_COOLDOWN_MINUTES)
        
    def can_send_alert(self):
        """Check if enough time has passed since last alert"""
        if self.last_alert_time is None:
            print("📢 Alert system: No previous alerts, can send alert")
            return True
        
        # Use local time for comparison
        local_tz = pytz.timezone('America/Los_Angeles')
        current_local_time = datetime.now(local_tz).replace(tzinfo=None)
        time_since_last = current_local_time - self.last_alert_time
        can_send = time_since_last >= self.alert_cooldown
        
        if not can_send:
            remaining_time = self.alert_cooldown - time_since_last
            remaining_minutes = remaining_time.total_seconds() / 60
            print(f"⏰ Alert cooldown active: {remaining_minutes:.1f} minutes remaining until next alert")
        else:
            print("📢 Alert system: Cooldown period passed, can send alert")
            
        return can_send
    
    
    def send_discord(self, message, image_data=None, filename="print_failure.jpg"):
        """Send message to Discord webhook with optional image attachment"""
        if not SEND_DISCORD_ALERTS or not DISCORD_WEBHOOK_URL:
            return False
            
        try:
            if image_data:
                # Send message with image attachment
                files = {
                    'file': (filename, image_data, 'image/jpeg')
                }
                
                payload = {
                    "content": message,
                    "username": "3D Printer Monitor",
                    "avatar_url": "https://cdn-icons-png.flaticon.com/512/2103/2103633.png"
                }
                
                # Send to Discord webhook with file
                response = requests.post(DISCORD_WEBHOOK_URL, data=payload, files=files, timeout=15)
            else:
                # Send text-only message
                payload = {
                    "content": message,
                    "username": "3D Printer Monitor",
                    "avatar_url": "https://cdn-icons-png.flaticon.com/512/2103/2103633.png"
                }
                
                # Send to Discord webhook
                response = requests.post(DISCORD_WEBHOOK_URL, json=payload, timeout=10)
            
            if response.status_code in [200, 204]:
                print(f"✅ Discord message sent successfully{' with image' if image_data else ''}")
                return True
            else:
                print(f"❌ Discord webhook error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Discord error: {e}")
            return False
    
    def send_print_failure_alert(self, print_status, confidence, gemini_response, image_data=None, gemini_prompt=None):
        """Send comprehensive alert for print failure with image and full details"""
        print(f"🚨 Attempting to send Discord alert for print failure (Status: {print_status}, Confidence: {confidence:.1%})")
        
        if not self.can_send_alert():
            print("⏰ Alert cooldown active, skipping Discord notification")
            return False
        
        # Get local time (PDT/UTC-7)
        local_tz = pytz.timezone('America/Los_Angeles')
        local_time = datetime.now(local_tz)
        timestamp = local_time.strftime("%Y-%m-%d %H:%M:%S %Z")
        
        # Create concise alert message (Discord has 2000 char limit)
        message = f"""🚨 **3D PRINTER FAILURE ALERT** 🚨

**📊 Status:** {print_status.upper()}
**🎯 Confidence:** {confidence:.1%}
**⏰ Time:** {timestamp}

**📝 AI Analysis:**
{gemini_response[:500]}{'...' if len(gemini_response) > 500 else ''}

**📸 Image:** {'Attached below' if image_data else 'No image available'}

**⚡ Action Required:** Check your printer immediately!

*Circuit Breakers 3D Printer Monitor*"""
        
        # Send Discord alert with image
        filename_timestamp = local_time.strftime("%Y%m%d_%H%M%S")
        discord_success = self.send_discord(message, image_data, f"print_failure_{filename_timestamp}.jpg")
        
        # Update last alert time if alert was sent
        if discord_success:
            self.last_alert_time = local_time.replace(tzinfo=None)  # Store as naive datetime for comparison
            return True
        
        return False

# Global alert system instance
alert_system = AlertSystem()
