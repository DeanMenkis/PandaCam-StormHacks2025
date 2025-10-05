"""
Alert System for Circuit Breakers 3D Printer Monitoring
Handles Discord notifications for print failures
"""

import time
from datetime import datetime, timedelta
import requests
import json

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
            return True
        
        time_since_last = datetime.now() - self.last_alert_time
        return time_since_last >= self.alert_cooldown
    
    
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
        if not self.can_send_alert():
            print("⏰ Alert cooldown active, skipping notification")
            return False
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
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
        discord_success = self.send_discord(message, image_data, f"print_failure_{timestamp.replace(':', '-').replace(' ', '_')}.jpg")
        
        # Update last alert time if alert was sent
        if discord_success:
            self.last_alert_time = datetime.now()
            return True
        
        return False

# Global alert system instance
alert_system = AlertSystem()
