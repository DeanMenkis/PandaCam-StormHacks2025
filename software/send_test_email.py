#!/usr/bin/env python3
"""
Send a test email with subject "3D Printer Failure"
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from alert_system import alert_system

def send_test_email():
    """Send a test email with the specified subject"""
    
    print("📧 Sending Test Email")
    print("=" * 30)
    
    # Test message
    test_message = """🧪 TEST EMAIL - 3D Printer Alert System

This is a test email to verify the alert system is working correctly.

Print Status: TEST
Confidence: 100%
Time: Test Message

AI Analysis: This is a test message from the 3D printer monitoring system to verify email alerts are working properly.

If you receive this email, the alert system is functioning correctly! ✅

---
Circuit Breakers 3D Printer Monitoring System
Test Message"""
    
    print("📤 Sending email with subject: '3D Printer Failure'")
    print(f"📧 To: brennan.pinette@gmail.com")
    print(f"📝 Message length: {len(test_message)} characters")
    
    # Send the email
    success = alert_system.send_email("3D Printer Failure", test_message)
    
    if success:
        print("✅ Test email sent successfully!")
        print("📬 Check your email inbox for the message.")
    else:
        print("❌ Failed to send test email.")
        print("🔍 Check your Gmail app password and network connection.")
    
    return success

if __name__ == "__main__":
    send_test_email()
