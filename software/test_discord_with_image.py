#!/usr/bin/env python3
"""
Test script for Discord alerts with image attachments
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from alert_system import alert_system
from datetime import datetime
import numpy as np
import cv2

def create_test_image():
    """Create a test image that looks like a failed 3D print"""
    
    # Create a test image (640x480)
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Add some background color (dark gray)
    img[:] = (40, 40, 40)
    
    # Add text to simulate a failed print
    cv2.putText(img, "TEST: FAILED 3D PRINT", (50, 100), 
               cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 255), 3)
    
    cv2.putText(img, "Spaghetti mess detected", (50, 150), 
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    cv2.putText(img, "Print detached from bed", (50, 200), 
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    # Add some random "spaghetti" lines
    for i in range(20):
        x1 = np.random.randint(0, 640)
        y1 = np.random.randint(0, 480)
        x2 = np.random.randint(0, 640)
        y2 = np.random.randint(0, 480)
        cv2.line(img, (x1, y1), (x2, y2), (255, 0, 0), 2)
    
    # Add timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(img, f"Test Image - {timestamp}", (50, 450), 
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (128, 128, 128), 2)
    
    # Convert to JPEG bytes
    _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return buffer.tobytes()

def test_discord_with_image():
    """Test Discord alert with image attachment"""
    
    print("🤖 Testing Discord Alert with Image")
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
    
    # Create test image
    print("\n🖼️ Creating test image...")
    test_image = create_test_image()
    print(f"   Test image size: {len(test_image)} bytes")
    
    # Test Gemini prompt
    test_prompt = """You are an expert 3D printing technician analyzing a camera feed. Your job is to determine if the CURRENT PRINT is successful or failing.

🔍 CRITICAL ANALYSIS GUIDELINES:

ONLY report failures for ACTUAL PRINT PROBLEMS:
• Print is warped, curled, or deformed
• Print has detached from the bed and is moving
• Extruder is clogged or not extruding
• Print has completely failed or fallen over
• Spaghetti/stringy mess instead of proper layers

ALWAYS CONSIDER THESE AS SUCCESSFUL PRINTS:
• Dirty or messy print bed (this is NORMAL and OKAY)
• Old filament residue on the bed (this is NORMAL and OKAY)
• Dust, debris, or previous print remnants on bed (this is NORMAL and OKAY)
• Slightly imperfect bed surface (this is NORMAL and OKAY)
• Tools or objects near the printer (this is NORMAL and OKAY)
• Print bed that looks used or worn (this is NORMAL and OKAY)

FOCUS ONLY ON THE CURRENT PRINT OBJECT:
• Is the current print adhering properly to the bed?
• Are the layers building correctly?
• Is the print maintaining its intended shape?

🎯 KEY RULE: A dirty bed does NOT equal a failed print! Beds get messy during normal use.

📝 RESPONSE FORMAT:
Write a natural, conversational response. Start with one of these:
• '✅ PRINT LOOKS GOOD: [explain why the current print is successful]'
• '❌ PRINT FAILURE: [explain what went wrong with the current print]'
• '🤷 NO PRINTER VISIBLE: [describe what you see instead]'

REMEMBER: Dirty beds are normal! Only flag actual print failures, not cosmetic bed issues."""
    
    print("\n🚨 Testing Full Print Failure Alert with Image...")
    failure_alert_success = alert_system.send_print_failure_alert(
        "failed",
        0.95,
        "❌ PRINT FAILURE: The current print is clearly failing. Instead of building proper layers, the extruder is creating a spaghetti mess with random stringy filament scattered across the bed. The print has completely detached from the bed and is no longer adhering properly. This is a classic print failure that requires immediate attention.",
        test_image,  # Include the test image
        test_prompt  # Include the Gemini prompt
    )
    
    print("\n📊 Test Results:")
    print(f"   Failure Alert with Image: {'✅ SUCCESS' if failure_alert_success else '❌ FAILED'}")
    
    if failure_alert_success:
        print(f"\n✅ Discord alert with image sent successfully! Check your Discord channel.")
        print(f"   Last alert time updated to: {alert_system.last_alert_time}")
    else:
        print(f"\n❌ Discord alert with image failed. Check configuration and network.")
    
    return failure_alert_success

if __name__ == "__main__":
    print("🚀 Starting Discord Alert with Image Test")
    print("=" * 60)
    
    # Test the alert system
    success = test_discord_with_image()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Discord alert with image test completed successfully!")
        print("📸 Check your Discord channel for the alert message with image attachment!")
    else:
        print("💥 Discord alert with image test failed!")
        print("   Check your configuration and network connection.")
    
    print("\n📝 What to expect in Discord:")
    print("   - Alert message with all details (status, confidence, time)")
    print("   - AI analysis response")
    print("   - Gemini prompt used")
    print("   - Image attachment showing the failed print")
    print("   - Professional formatting with emojis and markdown")
