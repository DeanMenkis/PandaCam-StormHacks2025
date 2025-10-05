#!/usr/bin/env python3
"""
Camera Test Script for 3D Printer Monitoring System
Captures images from laptop camera and communicates with Flask server via shared memory
"""

import cv2
import time
import base64
import json
from datetime import datetime
import threading
import sys
import multiprocessing as mp
from multiprocessing import shared_memory
import numpy as np

class CameraTest:
    def __init__(self):
        self.camera = None
        self.running = False
        self.frame_count = 0
        self.shared_memory = None
        self.frame_lock = None
        self.status_lock = None
        
    def setup_shared_memory(self):
        """Setup shared memory for communication with Flask server"""
        try:
            # Create shared memory for frame data (640x480x3 bytes for RGB image)
            frame_size = 640 * 480 * 3
            self.shared_memory = shared_memory.SharedMemory(create=True, size=frame_size, name="camera_frame")
            
            # Create locks for thread safety
            self.frame_lock = mp.Lock()
            self.status_lock = mp.Lock()
            
            print(f"Shared memory setup successful - Size: {frame_size} bytes")
            return True
            
        except Exception as e:
            print(f"Error setting up shared memory: {e}")
            return False
    
    def start_camera(self):
        """Initialize and start the camera"""
        try:
            # Try different camera indices to find the laptop camera
            camera_indices = [0, 1, 2, 3]  # Try common camera indices
            
            for camera_index in camera_indices:
                print(f"Trying camera index {camera_index}...")
                self.camera = cv2.VideoCapture(camera_index)
                
                if self.camera.isOpened():
                    # Test if we can actually read a frame
                    ret, test_frame = self.camera.read()
                    if ret and test_frame is not None:
                        # Get camera properties to identify it
                        width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
                        height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        fps = self.camera.get(cv2.CAP_PROP_FPS)
                        
                        print(f"✓ Camera {camera_index} found: {width}x{height} @ {fps}fps")
                        
                        # Set camera properties for better performance
                        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        self.camera.set(cv2.CAP_PROP_FPS, 30)
                        
                        print(f"Camera {camera_index} initialized successfully")
                        return True
                    else:
                        print(f"✗ Camera {camera_index} opened but can't read frames")
                        self.camera.release()
                else:
                    print(f"✗ Camera {camera_index} not available")
            
            print("Error: No working camera found")
            return False
            
        except Exception as e:
            print(f"Error initializing camera: {e}")
            return False
    
    def capture_frame(self):
        """Capture a single frame from the camera"""
        if not self.camera or not self.camera.isOpened():
            return None
            
        ret, frame = self.camera.read()
        if not ret:
            return None
            
        # Print frame info for debugging
        if self.frame_count == 0:
            print(f"Original frame size: {frame.shape}")
            
        # Resize frame for better performance
        frame = cv2.resize(frame, (640, 480))
        
        if self.frame_count == 0:
            print(f"Resized frame size: {frame.shape}")
            print(f"Frame data size: {frame.nbytes} bytes")
        
        return frame
    
    def write_frame_to_shared_memory(self, frame):
        """Write frame data to shared memory"""
        try:
            if self.shared_memory and self.frame_lock:
                with self.frame_lock:
                    # Convert BGR to RGB and flatten
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    frame_bytes = frame_rgb.flatten().tobytes()
                    
                    # Debug info for first frame
                    if self.frame_count == 0:
                        print(f"Frame RGB shape: {frame_rgb.shape}")
                        print(f"Frame bytes length: {len(frame_bytes)}")
                        print(f"Shared memory size: {self.shared_memory.size}")
                    
                    # Write to shared memory
                    self.shared_memory.buf[:len(frame_bytes)] = frame_bytes
                    
                if self.frame_count % 10 == 0:  # Print every 10th frame
                    print(f"Frame {self.frame_count} written to shared memory")
                
        except Exception as e:
            print(f"Error writing frame to shared memory: {e}")
    
    def update_camera_status(self, status):
        """Update camera status in shared memory"""
        try:
            # Create a simple status file for communication
            status_data = {
                "camera_active": status,
                "timestamp": datetime.now().isoformat(),
                "frame_count": self.frame_count
            }
            
            with open("/tmp/camera_status.json", "w") as f:
                json.dump(status_data, f)
                
            print(f"Camera status updated: {status}")
                
        except Exception as e:
            print(f"Error updating status: {e}")
    
    def run_camera_stream(self):
        """Main camera streaming loop"""
        print("Starting camera stream...")
        self.running = True
        self.update_camera_status(True)
        
        # Create OpenCV window to display camera feed
        cv2.namedWindow('Camera Feed - 3D Printer Monitoring', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Camera Feed - 3D Printer Monitoring', 640, 480)
        
        try:
            while self.running:
                # Capture frame
                frame = self.capture_frame()
                
                if frame is None:
                    print("Failed to capture frame")
                    time.sleep(0.1)
                    continue
                
                # Display frame in OpenCV window
                cv2.imshow('Camera Feed - 3D Printer Monitoring', frame)
                
                # Write frame to shared memory
                self.write_frame_to_shared_memory(frame)
                
                self.frame_count += 1
                
                # Check for window close or ESC key
                key = cv2.waitKey(1) & 0xFF
                if key == 27 or cv2.getWindowProperty('Camera Feed - 3D Printer Monitoring', cv2.WND_PROP_VISIBLE) < 1:
                    print("Camera window closed by user")
                    break
                
                # Control frame rate (send every 100ms = 10 FPS)
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\nStopping camera stream...")
        except Exception as e:
            print(f"Error in camera stream: {e}")
        finally:
            cv2.destroyAllWindows()
            self.stop_camera()
    
    def stop_camera(self):
        """Stop the camera and cleanup"""
        print("Stopping camera...")
        self.running = False
        
        if self.camera:
            self.camera.release()
            self.camera = None
            
        self.update_camera_status(False)
        
        # Cleanup shared memory
        if self.shared_memory:
            self.shared_memory.close()
            self.shared_memory.unlink()
            
        print("Camera stopped")
    
    def test_shared_memory_setup(self):
        """Test if shared memory can be created"""
        try:
            # Try to create a small test shared memory
            test_shm = shared_memory.SharedMemory(create=True, size=1024, name="test_memory")
            test_shm.close()
            test_shm.unlink()
            print("✓ Shared memory setup successful")
            return True
        except Exception as e:
            print(f"✗ Shared memory setup failed: {e}")
            return False
    
    def list_available_cameras(self):
        """List all available cameras and their properties"""
        print("\n🔍 Scanning for available cameras...")
        available_cameras = []
        
        for i in range(10):  # Check up to 10 camera indices
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    
                    camera_info = {
                        'index': i,
                        'width': width,
                        'height': height,
                        'fps': fps,
                        'frame_shape': frame.shape
                    }
                    available_cameras.append(camera_info)
                    
                    print(f"📹 Camera {i}: {width}x{height} @ {fps}fps (Shape: {frame.shape})")
                cap.release()
        
        if not available_cameras:
            print("❌ No cameras found!")
        else:
            print(f"\n✅ Found {len(available_cameras)} camera(s)")
            print("💡 Tip: Your laptop camera is usually the one with higher resolution")
        
        return available_cameras

def main():
    print("=" * 50)
    print("3D Printer Monitoring - Camera Test Script")
    print("=" * 50)
    
    # Initialize camera test
    camera_test = CameraTest()
    
    # List available cameras first
    available_cameras = camera_test.list_available_cameras()
    
    if not available_cameras:
        print("No cameras found. Make sure your camera is connected and not being used by another application.")
        sys.exit(1)
    
    # Test shared memory setup
    if not camera_test.test_shared_memory_setup():
        print("\nShared memory setup failed. Make sure you have proper permissions.")
        sys.exit(1)
    
    # Setup shared memory
    if not camera_test.setup_shared_memory():
        print("Failed to setup shared memory.")
        sys.exit(1)
    
    # Start camera
    if not camera_test.start_camera():
        print("Failed to start camera. Make sure your camera is not being used by another application.")
        sys.exit(1)
    
    print("\nCamera test started!")
    print("Press Ctrl+C or ESC key to stop")
    print("An OpenCV window will open showing the camera feed")
    print("Check your web browser at http://localhost:3000 to see the video feed")
    print("Make sure the Flask server is running to see the video stream")
    print("-" * 50)
    
    try:
        # Run camera stream
        camera_test.run_camera_stream()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        camera_test.stop_camera()
        print("Test completed!")

if __name__ == "__main__":
    main()
