#!/usr/bin/env python3
"""
Camera Debug Script
Test camera capture and image quality directly
"""

import subprocess
import os
from PIL import Image
import time

def test_camera_commands():
    """Test different camera commands and settings"""
    
    print("🧪 Testing Camera Commands and Quality")
    print("=" * 50)
    
    # Test commands with different settings
    test_commands = [
        {
            "name": "Basic Preview",
            "cmd": ["rpicam-jpeg", "--nopreview", "--output", "debug_basic.jpg", "--timeout", "1", "--width", "640", "--height", "480"]
        },
        {
            "name": "High Quality Preview", 
            "cmd": ["rpicam-jpeg", "--nopreview", "--output", "debug_hq.jpg", "--timeout", "1", "--width", "960", "--height", "540", "--quality", "95"]
        },
        {
            "name": "Full Resolution",
            "cmd": ["rpicam-jpeg", "--nopreview", "--output", "debug_full.jpg", "--timeout", "1", "--width", "1920", "--height", "1080", "--quality", "95"]
        }
    ]
    
    for test in test_commands:
        print(f"\n📷 Testing: {test['name']}")
        print(f"Command: {' '.join(test['cmd'])}")
        
        try:
            start_time = time.time()
            result = subprocess.run(test['cmd'], capture_output=True, text=True, timeout=10)
            end_time = time.time()
            
            if result.returncode == 0:
                filename = test['cmd'][test['cmd'].index('--output') + 1]
                if os.path.exists(filename):
                    # Get file info
                    file_size = os.path.getsize(filename)
                    
                    # Get image info
                    try:
                        with Image.open(filename) as img:
                            width, height = img.size
                            mode = img.mode
                            
                        print(f"✅ SUCCESS")
                        print(f"   File: {filename} ({file_size:,} bytes)")
                        print(f"   Image: {width}x{height} {mode}")
                        print(f"   Time: {end_time - start_time:.2f}s")
                        
                    except Exception as e:
                        print(f"❌ Image read error: {e}")
                else:
                    print(f"❌ Output file not created")
            else:
                print(f"❌ FAILED (return code: {result.returncode})")
                if result.stderr:
                    print(f"   Error: {result.stderr.strip()}")
                    
        except subprocess.TimeoutExpired:
            print(f"❌ TIMEOUT")
        except Exception as e:
            print(f"❌ ERROR: {e}")
    
    print(f"\n📁 Debug images saved in current directory")
    print(f"🔍 Check these files to see camera output quality")

def test_preview_stream():
    """Test preview stream (stdout output)"""
    print(f"\n🎥 Testing Preview Stream")
    print("=" * 30)
    
    cmd = ["rpicam-jpeg", "--nopreview", "--output", "-", "--timeout", "1", "--width", "640", "--height", "480"]
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=5)
        
        if result.returncode == 0:
            data_size = len(result.stdout)
            print(f"✅ Stream SUCCESS: {data_size:,} bytes received")
            
            # Try to save and analyze the stream data
            with open("debug_stream.jpg", "wb") as f:
                f.write(result.stdout)
                
            try:
                with Image.open("debug_stream.jpg") as img:
                    width, height = img.size
                    mode = img.mode
                print(f"   Stream image: {width}x{height} {mode}")
            except Exception as e:
                print(f"❌ Stream image invalid: {e}")
                
        else:
            print(f"❌ Stream FAILED (return code: {result.returncode})")
            if result.stderr:
                print(f"   Error: {result.stderr.decode()}")
                
    except Exception as e:
        print(f"❌ Stream ERROR: {e}")

if __name__ == "__main__":
    test_camera_commands()
    test_preview_stream()
    print(f"\n🎯 Debug complete! Check the generated debug_*.jpg files")
