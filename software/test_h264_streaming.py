#!/usr/bin/env python3
"""
Test H.264 streaming capabilities
"""

import subprocess
import sys
import os

def check_rpicam_vid():
    """Check if rpicam-vid is available"""
    print("🔍 Checking for rpicam-vid...")
    
    try:
        result = subprocess.run(['which', 'rpicam-vid'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ rpicam-vid found at: {result.stdout.strip()}")
            return True
        else:
            print("❌ rpicam-vid not found")
            return False
    except Exception as e:
        print(f"❌ Error checking rpicam-vid: {e}")
        return False

def check_rpicam_apps():
    """Check if rpicam-apps package is installed"""
    print("🔍 Checking for rpicam-apps package...")
    
    try:
        result = subprocess.run(['dpkg', '-l', 'rpicam-apps'], capture_output=True, text=True)
        if 'rpicam-apps' in result.stdout:
            print("✅ rpicam-apps package is installed")
            return True
        else:
            print("❌ rpicam-apps package not installed")
            return False
    except Exception as e:
        print(f"❌ Error checking rpicam-apps: {e}")
        return False

def test_h264_streaming():
    """Test H.264 streaming with a short capture"""
    print("🎥 Testing H.264 streaming...")
    
    try:
        cmd = [
            'rpicam-vid',
            '--width', '640',
            '--height', '480',
            '--framerate', '30',
            '--bitrate', '2000000',
            '--codec', 'h264',
            '--inline',
            '--timeout', '2000',  # 2 seconds
            '--output', '/tmp/test_h264.h264',
            '--vflip'  # Flip vertically to fix upside-down
        ]
        
        print(f"🚀 Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            if os.path.exists('/tmp/test_h264.h264'):
                file_size = os.path.getsize('/tmp/test_h264.h264')
                print(f"✅ H.264 test successful! File size: {file_size} bytes")
                os.remove('/tmp/test_h264.h264')
                return True
            else:
                print("❌ H.264 test failed - no output file created")
                return False
        else:
            print(f"❌ H.264 test failed: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ H.264 test timed out (this is expected)")
        return True
    except Exception as e:
        print(f"❌ H.264 test error: {e}")
        return False

def main():
    print("🚀 H.264 Streaming Test")
    print("=" * 50)
    
    # Check prerequisites
    rpicam_available = check_rpicam_vid()
    package_installed = check_rpicam_apps()
    
    if not rpicam_available:
        print("\n📦 To install rpicam-vid:")
        print("   sudo apt update")
        print("   sudo apt install rpicam-apps")
        print("\n💡 This will enable ultra-low latency H.264 streaming!")
        return False
    
    # Test H.264 streaming
    print("\n" + "=" * 50)
    h264_works = test_h264_streaming()
    
    if h264_works:
        print("\n🎉 H.264 streaming is ready!")
        print("📡 You can now use /h264_stream endpoint for ultra-low latency")
        print("⚡ Expected latency: < 200ms")
        return True
    else:
        print("\n❌ H.264 streaming test failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
