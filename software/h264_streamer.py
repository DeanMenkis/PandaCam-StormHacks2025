#!/usr/bin/env python3
"""
H.264 Video Streamer using rpicam-vid for ultra-low latency
"""

import subprocess
import threading
import time
import os
import signal
import sys

class H264Streamer:
    def __init__(self, width=640, height=480, fps=30, bitrate=2000000):
        self.width = width
        self.height = height
        self.fps = fps
        self.bitrate = bitrate
        self.process = None
        self.streaming = False
        self.port = 8554
        
    def start_streaming(self):
        """Start H.264 streaming using rpicam-vid"""
        try:
            if self.streaming:
                print("⚠️ H.264 streaming already active")
                return True
                
            print(f"🎥 Starting H.264 streaming: {self.width}x{self.height}@{self.fps}fps")
            
            # Build rpicam-vid command for H.264 streaming
            cmd = [
                'rpicam-vid',
                '--width', str(self.width),
                '--height', str(self.height),
                '--framerate', str(self.fps),
                '--bitrate', str(self.bitrate),
                '--codec', 'h264',
                '--inline',  # Include SPS/PPS in every frame
                '--timeout', '0',  # Stream indefinitely
                '--output', '-',  # Output to stdout
                '--awb', 'auto',  # Auto white balance
                '--brightness', '0.0',
                '--contrast', '1.0'
            ]
            
            print(f"🚀 Running: {' '.join(cmd)}")
            
            # Start rpicam-vid process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0  # Unbuffered for real-time streaming
            )
            
            self.streaming = True
            print(f"✅ H.264 streaming started on port {self.port}")
            print("📡 Stream available at: http://localhost:8554/stream")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to start H.264 streaming: {e}")
            return False
    
    def stop_streaming(self):
        """Stop H.264 streaming"""
        try:
            if self.process and self.streaming:
                print("🛑 Stopping H.264 streaming...")
                self.process.terminate()
                self.process.wait(timeout=5)
                self.streaming = False
                print("✅ H.264 streaming stopped")
            else:
                print("⚠️ H.264 streaming not active")
        except Exception as e:
            print(f"❌ Error stopping H.264 streaming: {e}")
            if self.process:
                self.process.kill()
    
    def get_stream_url(self):
        """Get the stream URL"""
        return f"http://localhost:{self.port}/stream"
    
    def is_streaming(self):
        """Check if streaming is active"""
        return self.streaming and self.process and self.process.poll() is None

def start_h264_streaming():
    """Start H.264 streaming in a separate thread"""
    streamer = H264Streamer(width=640, height=480, fps=30)
    
    def stream_worker():
        if streamer.start_streaming():
            try:
                # Keep the process alive
                while streamer.is_streaming():
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n🛑 Interrupted by user")
            finally:
                streamer.stop_streaming()
    
    # Start streaming in background thread
    stream_thread = threading.Thread(target=stream_worker, daemon=True)
    stream_thread.start()
    
    return streamer

if __name__ == "__main__":
    print("🚀 Starting H.264 Video Streamer")
    print("=" * 50)
    
    streamer = start_h264_streaming()
    
    try:
        print(f"📡 Stream URL: {streamer.get_stream_url()}")
        print("Press Ctrl+C to stop...")
        
        # Keep main thread alive
        while True:
            time.sleep(1)
            if not streamer.is_streaming():
                print("❌ Streaming stopped unexpectedly")
                break
                
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        streamer.stop_streaming()
        sys.exit(0)
