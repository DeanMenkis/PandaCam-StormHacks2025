#!/usr/bin/env python3
"""
Reset Discord alert cooldown to allow immediate alerts
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from alert_system import alert_system

def reset_cooldown():
    """Reset the alert cooldown to allow immediate alerts"""
    
    print("🔄 Resetting Discord Alert Cooldown")
    print("=" * 40)
    
    print(f"Current last alert time: {alert_system.last_alert_time}")
    print(f"Can send alert now: {alert_system.can_send_alert()}")
    
    # Reset the last alert time
    alert_system.last_alert_time = None
    
    print(f"✅ Alert cooldown reset!")
    print(f"New last alert time: {alert_system.last_alert_time}")
    print(f"Can send alert now: {alert_system.can_send_alert()}")
    
    print("\n📝 Note: The next AI analysis that detects a failure will now send a Discord alert immediately.")

if __name__ == "__main__":
    reset_cooldown()
