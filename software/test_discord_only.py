#!/usr/bin/env python3
"""
Test script for Discord-only alert system
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from alert_system import alert_system
from datetime import datetime

def test_discord_only():
    """Test Discord-only alert system"""
    
    print("🤖 Testing Discord-Only Alert System")
    print("=" * 50)
    
    # Test configuration
    print("📋 Configuration Check:")
    try:
        from config import (
            DISCORD_WEBHOOK_URL, SEND_DISCORD_ALERTS, ALERT_COOLDOWN_MINUTES
        )
        
        print(f"   Discord Webhook: {DISCORD_WEBHOOK_URL[:50]}...")
        print(f"   Send Discord Alerts: {SEND_DISCORD_ALERTS}")
        print(f"   Alert Cooldown: {ALERT_COOLDOWN_MINUTES} minutes")
        
    except ImportError as e:
        print(f"❌ Config import error: {e}")
        return False
    
    print("\n🔍 Alert System Status:")
    print(f"   Last Alert Time: {alert_system.last_alert_time}")
    print(f"   Can Send Alert: {alert_system.can_send_alert()}")
    
    print("\n🤖 Testing Discord Alert...")
    discord_test_message = """🚨 **3D PRINTER ALERT** 🚨

**Print Status:** TEST
**Confidence:** 100%
**Time:** Test Message

**AI Analysis:** This is a test message from the 3D printer monitoring system to verify Discord alerts are working properly.

If you receive this message, the Discord alert system is functioning correctly! ✅

---
*Circuit Breakers 3D Printer Monitoring System - Test Message*"""
    
    discord_success = alert_system.send_discord(discord_test_message)
    
    print("\n🚨 Testing Full Print Failure Alert...")
    failure_alert_success = alert_system.send_print_failure_alert(
        "failed",
        0.85,
        "✅ TEST: Print appears to have failed - this is a test message from the Discord alert system"
    )
    
    print("\n📊 Test Results:")
    print(f"   Discord Test: {'✅ SUCCESS' if discord_success else '❌ FAILED'}")
    print(f"   Failure Alert Test: {'✅ SUCCESS' if failure_alert_success else '❌ FAILED'}")
    
    if discord_success or failure_alert_success:
        print(f"\n✅ Discord alert system is working! Check your Discord channel.")
        print(f"   Last alert time updated to: {alert_system.last_alert_time}")
    else:
        print(f"\n❌ Discord alert system failed all tests. Check configuration and network.")
    
    return discord_success or failure_alert_success

if __name__ == "__main__":
    print("🚀 Starting Discord-Only Alert System Test")
    print("=" * 60)
    
    # Test the alert system
    success = test_discord_only()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Discord alert system test completed successfully!")
    else:
        print("💥 Discord alert system test failed!")
        print("   Check your configuration and network connection.")
    
    print("\n📝 Next steps:")
    print("   1. Check your Discord channel for alert messages")
    print("   2. If no messages received, check:")
    print("      - Discord webhook URL is correct")
    print("      - Network connection is working")
    print("      - Discord webhook permissions are correct")
