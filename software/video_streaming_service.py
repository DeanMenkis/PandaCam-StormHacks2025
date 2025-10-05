#!/usr/bin/env python3
"""
Video Streaming Service for 3D Printer Monitoring System
Based on the camera test script, provides live video streaming to the Flask backend.
"""

import cv2
import time
import json
from datetime import datetime
import threading
import multiprocessing as mp
from multiprocessing import shared_memory
import numpy as np
import logging

class VideoStreamingService:
    def __init__(self):
        self.camera = None
        self.running = False
        self.frame_count = 0
        self.shared_memory = None
        self.frame_lock = None
        self.camera_active = False
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('video_streaming.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_shared_memory(self):
        """Setup shared memory for communication with Flask server"""
        try:
            # Create shared memory for frame data (640x480x3 bytes for RGB image)
            frame_size = 640 * 480 * 3
            self.shared_memory = shared_memory.SharedMemory(create=True, size=frame_size, name="camera_frame")
            
            # Create locks for thread safety
            self.frame_lock = mp.Lock()
            
            self.logger.info(f"Shared memory setup successful - Size: {frame_size} bytes")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting up shared memory: {e}")
            return False
    
    def start_camera(self):
        """Initialize and start the Raspberry Pi camera"""
        try:
            # Test if rpicam-vid works for video streaming
            test_command = ["rpicam-vid", "--nopreview", "--output", "-", "--timeout", "1", "--width", "640", "--height", "480", "--frames", "1"]
            
            import subprocess
            result = subprocess.run(test_command, capture_output=True, timeout=5)
            
            if result.returncode == 0:
                self.camera_active = True
                self.logger.info("Raspberry Pi camera initialized successfully for video streaming")
                return True
            else:
                self.logger.error(f"rpicam-vid test failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error initializing camera: {e}")
            return False
    
    def capture_frame(self):
        """Capture a single frame from the Raspberry Pi camera"""
        try:
            import subprocess
            
            # Use rpicam-vid to capture a single frame
            command = ["rpicam-vid", "--nopreview", "--immediate", "--timeout", "1", "--output", "-", "--width", "640", "--height", "480", "--frames", "1"]
            
            result = subprocess.run(command, capture_output=True, timeout=2)
            
            if result.returncode == 0 and result.stdout:
                # Convert the raw video data to OpenCV frame
                frame_data = np.frombuffer(result.stdout, dtype=np.uint8)
                
                # Try to decode as JPEG first
                try:
                    frame = cv2.imdecode(frame_data, cv2.IMREAD_COLOR)
                    if frame is not None:
                        if self.frame_count == 0:
                            self.logger.info(f"Frame decoded successfully: {frame.shape}")
                        return frame
                except:
                    pass
                
                # If JPEG decoding fails, try to reshape as raw RGB data
                try:
                    expected_size = 640 * 480 * 3
                    if len(frame_data) >= expected_size:
                        frame = frame_data[:expected_size].reshape((480, 640, 3))
                        if self.frame_count == 0:
                            self.logger.info(f"Frame reshaped successfully: {frame.shape}")
                        return frame
                except:
                    pass
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error capturing frame: {e}")
            return None
    
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
                        self.logger.info(f"Frame RGB shape: {frame_rgb.shape}")
                        self.logger.info(f"Frame bytes length: {len(frame_bytes)}")
                        self.logger.info(f"Shared memory size: {self.shared_memory.size}")
                    
                    # Write to shared memory
                    self.shared_memory.buf[:len(frame_bytes)] = frame_bytes
                    
                if self.frame_count % 30 == 0:  # Print every 30th frame
                    self.logger.info(f"Frame {self.frame_count} written to shared memory")
                
        except Exception as e:
            self.logger.error(f"Error writing frame to shared memory: {e}")
    
    def update_camera_status(self, status):
        """Update camera status for the Flask backend"""
        try:
            status_data = {
                "camera_active": status,
                "timestamp": datetime.now().isoformat(),
                "frame_count": self.frame_count
            }
            
            with open("/tmp/camera_status.json", "w") as f:
                json.dump(status_data, f)
                
            self.logger.info(f"Camera status updated: {status}")
                
        except Exception as e:
            self.logger.error(f"Error updating status: {e}")
    
    def run_camera_stream(self):
        """Main camera streaming loop"""
        self.logger.info("Starting camera stream...")
        self.running = True
        self.update_camera_status(True)
        
        try:
            while self.running:
                # Capture frame
                frame = self.capture_frame()
                
                if frame is None:
                    self.logger.warning("Failed to capture frame")
                    time.sleep(0.1)
                    continue
                
                # Write frame to shared memory
                self.write_frame_to_shared_memory(frame)
                
                self.frame_count += 1
                
                # Control frame rate (10 FPS)
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            self.logger.info("\nStopping camera stream...")
        except Exception as e:
            self.logger.error(f"Error in camera stream: {e}")
        finally:
            self.stop_camera()
    
    def stop_camera(self):
        """Stop the camera and cleanup"""
        self.logger.info("Stopping camera...")
        self.running = False
        
        self.camera_active = False
        self.update_camera_status(False)
        
        # Cleanup shared memory
        if self.shared_memory:
            self.shared_memory.close()
            self.shared_memory.unlink()
            
        self.logger.info("Camera stopped")
    
    def start_service(self):
        """Start the video streaming service"""
        self.logger.info("Starting Video Streaming Service...")
        
        # Setup shared memory
        if not self.setup_shared_memory():
            self.logger.error("Failed to setup shared memory")
            return False
        
        # Start camera
        if not self.start_camera():
            self.logger.error("Failed to start camera")
            return False
        
        self.logger.info("Video streaming service started successfully")
        return True

def main():
    """Main function to run the video streaming service"""
    print("=" * 60)
    print("Video Streaming Service")
    print("3D Printer Monitoring System")
    print("=" * 60)
    
    service = VideoStreamingService()
    
    try:
        # Start the service
        if service.start_service():
            print("✅ Video streaming service started successfully!")
            print("📹 Camera: Active")
            print("🌐 Backend API: http://127.0.0.1:8000")
            print("📺 Video Feed: http://127.0.0.1:8000/video_feed")
            print("\nPress Ctrl+C to stop the service")
            print("-" * 60)
            
            # Run the camera stream
            service.run_camera_stream()
        else:
            print("❌ Failed to start video streaming service")
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down video streaming service...")
    finally:
        service.stop_camera()
        print("✅ Video streaming service stopped")

if __name__ == "__main__":
    main()
