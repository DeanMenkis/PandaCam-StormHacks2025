#!/usr/bin/env python3
"""
Simple Video Streaming Service
Captures frames using rpicam-jpeg and serves them via shared memory to Flask backend.
"""

import subprocess
import time
import json
import threading
import multiprocessing as mp
from multiprocessing import shared_memory
import numpy as np
import cv2
import logging
from datetime import datetime

class SimpleVideoStream:
    def __init__(self):
        self.running = False
        self.frame_count = 0
        self.shared_memory = None
        self.frame_lock = None
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('simple_video_stream.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_shared_memory(self):
        """Setup shared memory for communication with Flask backend"""
        try:
            # Create shared memory for frame data (640x480x3 bytes for RGB image)
            frame_size = 640 * 480 * 3
            self.shared_memory = shared_memory.SharedMemory(create=True, size=frame_size, name="camera_frame")
            
            # Create lock for thread safety
            self.frame_lock = mp.Lock()
            
            self.logger.info(f"Shared memory setup successful - Size: {frame_size} bytes")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting up shared memory: {e}")
            return False
    
    def capture_and_write_frame(self):
        """Capture a frame using rpicam-jpeg and write to shared memory"""
        try:
            # Use rpicam-jpeg to capture a frame
            command = ["rpicam-jpeg", "--nopreview", "--immediate", "--timeout", "1", "--output", "-", "--width", "640", "--height", "480", "--quality", "80"]
            
            result = subprocess.run(command, capture_output=True, timeout=3)
            
            if result.returncode == 0 and result.stdout:
                # Decode the JPEG data
                frame_data = np.frombuffer(result.stdout, dtype=np.uint8)
                frame = cv2.imdecode(frame_data, cv2.IMREAD_COLOR)
                
                if frame is not None:
                    # Resize to ensure correct dimensions
                    frame = cv2.resize(frame, (640, 480))
                    
                    # Convert BGR to RGB
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    
                    # Write to shared memory
                    if self.shared_memory and self.frame_lock:
                        with self.frame_lock:
                            frame_bytes = frame_rgb.flatten().tobytes()
                            self.shared_memory.buf[:len(frame_bytes)] = frame_bytes
                    
                    self.frame_count += 1
                    
                    if self.frame_count % 30 == 0:  # Log every 30 frames
                        self.logger.info(f"Frame {self.frame_count} captured and written to shared memory")
                    
                    return True
                else:
                    self.logger.warning("Failed to decode JPEG frame")
                    return False
            else:
                self.logger.warning("rpicam-jpeg command failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Error capturing frame: {e}")
            return False
    
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
                
        except Exception as e:
            self.logger.error(f"Error updating camera status: {e}")
    
    def run_stream(self):
        """Main streaming loop"""
        self.logger.info("Starting simple video stream...")
        self.running = True
        self.update_camera_status(True)
        
        try:
            while self.running:
                # Capture and write frame
                self.capture_and_write_frame()
                
                # Control frame rate (5 FPS)
                time.sleep(0.2)
                
        except KeyboardInterrupt:
            self.logger.info("\nStopping video stream...")
        except Exception as e:
            self.logger.error(f"Error in video stream: {e}")
        finally:
            self.stop_stream()
    
    def stop_stream(self):
        """Stop the video stream and cleanup"""
        self.logger.info("Stopping video stream...")
        self.running = False
        
        self.update_camera_status(False)
        
        # Cleanup shared memory
        if self.shared_memory:
            self.shared_memory.close()
            self.shared_memory.unlink()
            
        self.logger.info("Video stream stopped")
    
    def start_service(self):
        """Start the video streaming service"""
        self.logger.info("Starting Simple Video Streaming Service...")
        
        # Setup shared memory
        if not self.setup_shared_memory():
            self.logger.error("Failed to setup shared memory")
            return False
        
        self.logger.info("Simple video streaming service started successfully")
        return True

def main():
    """Main function to run the simple video streaming service"""
    print("=" * 60)
    print("Simple Video Streaming Service")
    print("3D Printer Monitoring System")
    print("=" * 60)
    
    service = SimpleVideoStream()
    
    try:
        # Start the service
        if service.start_service():
            print("✅ Simple video streaming service started successfully!")
            print("📹 Camera: Active")
            print("🌐 Backend API: http://127.0.0.1:8000")
            print("📺 Video Feed: http://127.0.0.1:8000/video_feed")
            print("\nPress Ctrl+C to stop the service")
            print("-" * 60)
            
            # Run the video stream
            service.run_stream()
        else:
            print("❌ Failed to start simple video streaming service")
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down simple video streaming service...")
    finally:
        service.stop_stream()
        print("✅ Simple video streaming service stopped")

if __name__ == "__main__":
    main()
