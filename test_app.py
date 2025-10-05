#!/usr/bin/env python3
"""
Test script to verify the 3D Printer Watchdog can start properly
"""

import os
import sys
import subprocess

def test_environment():
    """Test if environment is set up correctly"""
    print("🧪 Testing 3D Printer Watchdog Environment...")
    
    # Test DISPLAY
    display = os.getenv("DISPLAY")
    if not display:
        print("⚠️  DISPLAY not set, setting to :0")
        os.environ["DISPLAY"] = ":0"
    else:
        print(f"✅ DISPLAY set to: {display}")
    
    # Test GEMINI_API_KEY
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("⚠️  GEMINI_API_KEY not set - AI analysis will not work")
    else:
        print(f"✅ GEMINI_API_KEY set (length: {len(api_key)})")
    
    # Test Python imports
    try:
        import tkinter
        print("✅ tkinter available")
    except ImportError:
        print("❌ tkinter not available")
        return False
    
    try:
        import PIL
        print("✅ PIL (Pillow) available")
    except ImportError:
        print("❌ PIL (Pillow) not available")
        return False
    
    try:
        import requests
        print("✅ requests available")
    except ImportError:
        print("❌ requests not available")
        return False
    
    # Test camera command
    try:
        result = subprocess.run(["which", "rpicam-jpeg"], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ rpicam-jpeg command available")
        else:
            print("❌ rpicam-jpeg command not found")
            return False
    except Exception as e:
        print(f"❌ Error checking camera command: {e}")
        return False
    
    print("\n🎉 Environment test completed successfully!")
    print("You can now run the application with:")
    print("   python3 rpi_firmware/watchdog_app.py")
    return True

if __name__ == "__main__":
    success = test_environment()
    sys.exit(0 if success else 1)

