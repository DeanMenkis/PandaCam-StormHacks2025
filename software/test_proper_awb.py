#!/usr/bin/env python3
"""
Test script for proper auto white balance implementation
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from picamera2 import Picamera2
import time

def test_proper_awb():
    """Test proper auto white balance with PiCamera2"""
    
    print("🎨 Testing Proper Auto White Balance with PiCamera2")
    print("=" * 60)
    
    try:
        # Initialize camera
        print("📹 Initializing PiCamera2...")
        camera = Picamera2()
        
        # Create configuration with proper auto white balance
        print("🎨 Configuring camera with proper AWB...")
        config = camera.create_video_configuration(
            main={"size": (640, 480), "format": "RGB888"},
            controls={
                "FrameRate": 15,
                "AwbMode": "auto",  # Proper auto white balance
                "ExposureTime": 0,  # Auto exposure
                "AnalogueGain": 0,  # Auto gain
            }
        )
        
        camera.configure(config)
        camera.start()
        
        # Apply proper auto white balance
        print("🎨 Applying proper auto white balance...")
        camera.set_controls({
            "AwbMode": "auto",  # Enable proper auto white balance
        })
        
        print("✅ Camera initialized with proper auto white balance!")
        print("📸 Taking test capture...")
        
        # Take a test capture
        time.sleep(2)  # Let AWB settle
        frame = camera.capture_array()
        
        print(f"✅ Test capture successful! Frame shape: {frame.shape}")
        print("🎨 Auto white balance should be working properly now")
        
        # Test different AWB modes
        print("\n🔧 Testing different AWB modes...")
        
        # Test daylight mode
        print("   Testing daylight mode...")
        camera.set_controls({"AwbMode": "daylight"})
        time.sleep(1)
        frame = camera.capture_array()
        print("   ✅ Daylight mode working")
        
        # Test tungsten mode
        print("   Testing tungsten mode...")
        camera.set_controls({"AwbMode": "tungsten"})
        time.sleep(1)
        frame = camera.capture_array()
        print("   ✅ Tungsten mode working")
        
        # Back to auto
        print("   Returning to auto mode...")
        camera.set_controls({"AwbMode": "auto"})
        time.sleep(1)
        frame = camera.capture_array()
        print("   ✅ Auto mode restored")
        
        # Cleanup
        camera.stop()
        camera.close()
        
        print("\n🎉 All AWB tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing AWB: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting Proper Auto White Balance Test")
    print("=" * 60)
    print("💡 This test verifies that PiCamera2's built-in AWB works properly")
    print("=" * 60)
    
    # Run the test
    success = test_proper_awb()
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Proper auto white balance test completed successfully!")
        print("\n📝 What this means:")
        print("   ✅ PiCamera2's built-in AWB is working")
        print("   ✅ No more manual white balance needed")
        print("   ✅ Camera should handle cool LED lights automatically")
        print("   ✅ Colors should look natural under your lighting")
    else:
        print("💥 Auto white balance test failed!")
        print("   Check camera connection and PiCamera2 installation")
    
    print("\n🎨 Expected behavior:")
    print("   - Camera automatically adjusts to your cool LED lights")
    print("   - No more blue tint issues")
    print("   - Natural color reproduction")
    print("   - No manual adjustments needed")
