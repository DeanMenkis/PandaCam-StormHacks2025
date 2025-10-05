#!/usr/bin/env python3
"""
Test script for the alert system
Tests SMS and email alerts for 3D printer failures
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from alert_system import alert_system
from datetime import datetime

def test_alert_system():
    """Test the alert system with a simulated print failure"""
    
    print("🧪 Testing Alert System")
    print("=" * 50)
    
    # Test configuration
    print("📋 Configuration Check:")
    try:
        from config import (
            PHONE_NUMBER, EMAIL_ADDRESS, SMS_EMAIL_GATEWAY, EMAIL_PASSWORD,
            SMTP_SERVER, SMTP_PORT, SEND_SMS_ALERTS, SEND_EMAIL_ALERTS, ALERT_COOLDOWN_MINUTES
        )
        
        print(f"   Phone Number: {PHONE_NUMBER}")
        print(f"   Email Address: {EMAIL_ADDRESS}")
        print(f"   SMS Gateway: {SMS_EMAIL_GATEWAY}")
        print(f"   SMTP Server: {SMTP_SERVER}:{SMTP_PORT}")
        print(f"   Send SMS Alerts: {SEND_SMS_ALERTS}")
        print(f"   Send Email Alerts: {SEND_EMAIL_ALERTS}")
        print(f"   Alert Cooldown: {ALERT_COOLDOWN_MINUTES} minutes")
        print(f"   Email Password: {'*' * len(EMAIL_PASSWORD)}")
        
    except ImportError as e:
        print(f"❌ Config import error: {e}")
        return False
    
    print("\n🔍 Alert System Status:")
    print(f"   Last Alert Time: {alert_system.last_alert_time}")
    print(f"   Can Send Alert: {alert_system.can_send_alert()}")
    
    print("\n📱 Testing SMS Alert...")
    sms_test_message = "🧪 TEST MESSAGE - 3D Printer Alert System Test"
    sms_success = alert_system.send_sms(sms_test_message)
    
    print("\n📧 Testing Email Alert...")
    email_success = alert_system.send_email(
        "🧪 TEST - 3D Printer Alert System", 
        sms_test_message
    )
    
    print("\n🚨 Testing Full Print Failure Alert...")
    failure_alert_success = alert_system.send_print_failure_alert(
        "failed",
        0.85,
        "✅ TEST: Print appears to have failed - this is a test message from the alert system"
    )
    
    print("\n📊 Test Results:")
    print(f"   SMS Test: {'✅ SUCCESS' if sms_success else '❌ FAILED'}")
    print(f"   Email Test: {'✅ SUCCESS' if email_success else '❌ FAILED'}")
    print(f"   Failure Alert Test: {'✅ SUCCESS' if failure_alert_success else '❌ FAILED'}")
    
    if sms_success or email_success or failure_alert_success:
        print(f"\n✅ Alert system is working! Check your phone and email.")
        print(f"   Last alert time updated to: {alert_system.last_alert_time}")
    else:
        print(f"\n❌ Alert system failed all tests. Check configuration and network.")
    
    return sms_success or email_success or failure_alert_success

def test_cooldown():
    """Test the alert cooldown mechanism"""
    
    print("\n⏰ Testing Alert Cooldown...")
    print("=" * 30)
    
    print(f"   Current time: {datetime.now()}")
    print(f"   Last alert time: {alert_system.last_alert_time}")
    print(f"   Can send alert: {alert_system.can_send_alert()}")
    
    if alert_system.last_alert_time:
        time_since_last = datetime.now() - alert_system.last_alert_time
        print(f"   Time since last alert: {time_since_last}")
        print(f"   Cooldown period: {alert_system.alert_cooldown}")
        
        if time_since_last < alert_system.alert_cooldown:
            remaining = alert_system.alert_cooldown - time_since_last
            print(f"   ⏰ Cooldown active - {remaining} remaining")
        else:
            print(f"   ✅ Cooldown expired - alerts allowed")

if __name__ == "__main__":
    print("🚀 Starting Alert System Test")
    print("=" * 60)
    
    # Test the alert system
    success = test_alert_system()
    
    # Test cooldown
    test_cooldown()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Alert system test completed successfully!")
    else:
        print("💥 Alert system test failed!")
        print("   Check your configuration and network connection.")
    
    print("\n📝 Next steps:")
    print("   1. Check your phone for SMS messages")
    print("   2. Check your email for alert messages")
    print("   3. If no messages received, check:")
    print("      - Gmail app password is correct")
    print("      - Phone number format is correct")
    print("      - Network connection is working")
    print("      - Gmail SMTP settings are correct")
