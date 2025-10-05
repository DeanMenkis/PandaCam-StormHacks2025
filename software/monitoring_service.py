#!/usr/bin/env python3
"""
3D Printer Monitoring Service
Background service that captures images, analyzes them with AI, and communicates with the Flask backend.

This service integrates:
- Camera capture functionality from rpi_firmware
- AI analysis using Google Gemini API
- Communication with Flask backend API
- Print status detection and reporting
"""

import cv2
import time
import base64
import json
import os
import requests
import subprocess
import threading
import multiprocessing as mp
from multiprocessing import shared_memory
import numpy as np
from datetime import datetime
import logging

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBHIiKiXJNKW6Ot5ZuFT1S2CiajIyvRP_c")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
BACKEND_URL = "http://127.0.0.1:8000"

# Camera settings - optimized for Raspberry Pi
CAPTURE_COMMAND = ["rpicam-jpeg", "--nopreview", "--immediate", "--timeout", "1", "-o", "capture.jpg", "--width", "1280", "--height", "960"]
CAPTURE_FILENAME = "capture.jpg"

# AI Configuration
AI_CONFIG = {
    "gemini_settings": {
        "prompt": "You are an expert 3D printing technician analyzing a camera feed. Look at this image and provide a clear, friendly analysis.\n\n🔍 WHAT TO LOOK FOR:\n• Is there a 3D printer visible in the image?\n• If yes: How does the print quality look? Any issues?\n• If no: What do you actually see instead?\n\n📝 RESPONSE FORMAT:\nWrite a natural, conversational response. Start with one of these:\n• \"✅ PRINT LOOKS GOOD: [explain why]\"\n• \"⚠️ POTENTIAL ISSUE: [describe the problem]\"\n• \"❌ PRINT FAILURE: [explain what went wrong]\"\n• \"🤷 NO PRINTER VISIBLE: [describe what you see instead]\"\n\nBe helpful and specific. If you see a problem, suggest what might be causing it. Keep it under 3 sentences and use a friendly tone.",
        "temperature": 0.3,
        "max_output_tokens": 1024,
        "top_p": 0.8,
        "top_k": 40
    },
    "analysis_settings": {
        "timeout_seconds": 25,
        "retry_attempts": 3,
        "fallback_enabled": True
    }
}

# Shared memory settings for video streaming
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
FRAME_SIZE = FRAME_WIDTH * FRAME_HEIGHT * 3  # RGB

class PrinterMonitoringService:
    def __init__(self):
        self.running = False
        self.monitoring_active = False
        self.capture_interval = 30  # seconds
        self.shared_memory = None
        self.frame_lock = None
        self.camera = None
        self.camera_active = False
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('monitoring_service.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def setup_shared_memory(self):
        """Setup for video streaming (simplified - no shared memory needed)"""
        try:
            # We don't actually need shared memory anymore since we're using files
            # Just create a simple lock for thread safety
            self.frame_lock = mp.Lock()
            self.logger.info("Video streaming setup successful (file-based)")
            return True
        except Exception as e:
            self.logger.error(f"Error setting up video streaming: {e}")
            return False
    
    def start_camera(self):
        """Initialize camera for both photo capture and video streaming"""
        try:
            # Test if rpicam-jpeg works for photo capture
            test_command = ["rpicam-jpeg", "--nopreview", "--immediate", "--timeout", "1", "-o", "test_camera.jpg", "--width", "640", "--height", "480"]
            
            result = subprocess.run(test_command, capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                self.camera_active = True
                self.logger.info("Raspberry Pi camera initialized successfully for photo capture and video streaming")
                return True
            else:
                self.logger.error(f"rpicam-jpeg test failed: {result.stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error initializing camera: {e}")
            return False
    
    def capture_frame(self):
        """Capture a single frame from the camera for video streaming"""
        try:
            # Use rpicam-jpeg to capture a frame for video streaming
            command = ["rpicam-jpeg", "--nopreview", "--immediate", "--timeout", "1", "--output", "-", "--width", "640", "--height", "480", "--quality", "80"]
            
            result = subprocess.run(command, capture_output=True, timeout=2)
            
            if result.returncode == 0 and result.stdout:
                # Return the JPEG data directly
                return result.stdout
            else:
                return None
                
        except Exception as e:
            self.logger.error(f"Error capturing frame for video: {e}")
            return None
    
    def write_frame_to_shared_memory(self, frame_data):
        """Write frame data to file for video streaming"""
        try:
            if self.frame_lock:
                with self.frame_lock:
                    # frame_data is already JPEG bytes from rpicam-jpeg
                    # Store it as a file that the Flask backend can read
                    with open("/tmp/latest_frame.jpg", "wb") as f:
                        f.write(frame_data)
                    
        except Exception as e:
            self.logger.error(f"Error writing frame to file: {e}")
    
    def update_camera_status(self, status):
        """Update camera status for the Flask backend"""
        try:
            status_data = {
                "camera_active": status,
                "timestamp": datetime.now().isoformat()
            }
            
            with open("/tmp/camera_status.json", "w") as f:
                json.dump(status_data, f)
                
        except Exception as e:
            self.logger.error(f"Error updating camera status: {e}")
    
    def capture_photo_for_analysis(self):
        """Capture a high-quality photo for AI analysis using rpicam-jpeg"""
        try:
            # Use rpicam-jpeg for high-quality capture
            result = subprocess.run(CAPTURE_COMMAND, capture_output=True, text=True, timeout=8)
            
            if result.returncode == 0 and os.path.exists(CAPTURE_FILENAME):
                self.logger.info("Photo captured successfully for AI analysis")
                return CAPTURE_FILENAME
            else:
                error_msg = result.stderr.strip() or "Unknown camera error"
                self.logger.error(f"Photo capture failed: {error_msg}")
                return None
                
        except subprocess.TimeoutExpired:
            self.logger.error("Photo capture timed out")
            return None
        except Exception as e:
            self.logger.error(f"Photo capture error: {e}")
            return None
    
    def analyze_image_with_ai(self, image_path):
        """Analyze image using Google Gemini AI"""
        try:
            if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
                self.logger.warning("Gemini API key not configured")
                return None
            
            # Read and encode image
            with open(image_path, "rb") as f:
                image_data = f.read()
            image_b64 = base64.b64encode(image_data).decode('utf-8')
            
            # Prepare Gemini API request
            headers = {"Content-Type": "application/json"}
            
            gemini_settings = AI_CONFIG.get("gemini_settings", {})
            prompt_text = gemini_settings.get("prompt", "Look at this image and describe what you see.")
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt_text},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": image_b64
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "temperature": gemini_settings.get("temperature", 0.3),
                    "maxOutputTokens": gemini_settings.get("max_output_tokens", 1024),
                    "topP": gemini_settings.get("top_p", 0.8),
                    "topK": gemini_settings.get("top_k", 40)
                }
            }
            
            # Make API call
            api_url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
            timeout = AI_CONFIG.get("analysis_settings", {}).get("timeout_seconds", 25)
            
            self.logger.info("Sending image to Gemini AI for analysis...")
            response = requests.post(api_url, headers=headers, json=payload, timeout=timeout)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    ai_response = result['candidates'][0]['content']['parts'][0]['text']
                    self.logger.info(f"AI Analysis: {ai_response}")
                    return ai_response
                else:
                    self.logger.error("No AI response received")
                    return None
            else:
                self.logger.error(f"AI API error: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            self.logger.error(f"AI analysis error: {e}")
            return None
    
    def determine_print_status(self, ai_response):
        """Determine print status based on AI response"""
        if not ai_response:
            return "unknown", 0
        
        ai_response_lower = ai_response.lower()
        
        # Check for failure indicators
        if any(keyword in ai_response_lower for keyword in ["print failure", "❌", "failed", "failure", "spaghetti", "detached", "warped", "melted", "broken", "collapsed"]):
            return "failed", 0
        
        # Check for potential issues
        elif any(keyword in ai_response_lower for keyword in ["potential issue", "⚠️", "problem", "issue", "concern", "warning"]):
            return "warning", 50
        
        # Check for good status
        elif any(keyword in ai_response_lower for keyword in ["print looks good", "✅", "good", "excellent", "perfect", "normal"]):
            return "printing", 100
        
        # Check if no printer visible
        elif any(keyword in ai_response_lower for keyword in ["no printer visible", "🤷", "no printer", "not visible"]):
            return "idle", 0
        
        # Default to unknown
        else:
            return "unknown", 50
    
    def send_status_to_backend(self, print_status, print_progress, ai_response):
        """Send print status update to Flask backend"""
        try:
            data = {
                "print_status": print_status,
                "print_progress": print_progress,
                "ai_analysis": ai_response,
                "timestamp": datetime.now().isoformat()
            }
            
            response = requests.post(f"{BACKEND_URL}/api/printer/print-status", json=data, timeout=10)
            
            if response.status_code == 200:
                self.logger.info(f"Status sent to backend: {print_status} ({print_progress}%)")
                return True
            else:
                self.logger.error(f"Failed to send status to backend: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error sending status to backend: {e}")
            return False
    
    def report_failure_to_backend(self):
        """Report print failure to Flask backend"""
        try:
            data = {
                "failure_detected": True,
                "failure_time": datetime.now().isoformat(),
                "ai_analysis": "Print failure detected by AI monitoring"
            }
            
            response = requests.post(f"{BACKEND_URL}/api/printer/failure", json=data, timeout=10)
            
            if response.status_code == 200:
                self.logger.info("Print failure reported to backend")
                return True
            else:
                self.logger.error(f"Failed to report failure to backend: {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.error(f"Error reporting failure to backend: {e}")
            return False
    
    def video_streaming_worker(self):
        """Background worker for video streaming"""
        self.logger.info("Starting video streaming worker...")
        
        while self.running and self.camera_active:
            try:
                # Capture a frame
                frame_data = self.capture_frame()
                
                if frame_data:
                    # Write frame to shared memory for the Flask backend
                    self.write_frame_to_shared_memory(frame_data)
                
                # Control frame rate (5 FPS for video streaming)
                time.sleep(0.2)
                
            except Exception as e:
                self.logger.error(f"Video streaming error: {e}")
                time.sleep(1)
    
    def monitoring_worker(self):
        """Background worker for AI monitoring"""
        self.logger.info("Starting AI monitoring worker...")
        
        while self.running and self.monitoring_active:
            try:
                self.logger.info("📸 Capturing photo for AI analysis...")
                
                # Capture photo
                image_path = self.capture_photo_for_analysis()
                
                if image_path:
                    # Analyze with AI
                    ai_response = self.analyze_image_with_ai(image_path)
                    
                    if ai_response:
                        # Determine print status
                        print_status, print_progress = self.determine_print_status(ai_response)
                        
                        # Send status to backend
                        self.send_status_to_backend(print_status, print_progress, ai_response)
                        
                        # Report failure if detected
                        if print_status == "failed":
                            self.report_failure_to_backend()
                
                # Wait for next capture
                for i in range(self.capture_interval):
                    if not self.running or not self.monitoring_active:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
                time.sleep(5)  # Wait before retrying
    
    def start_monitoring(self, interval=30):
        """Start the monitoring service"""
        self.logger.info("Starting 3D Printer Monitoring Service...")
        
        # Setup shared memory
        if not self.setup_shared_memory():
            self.logger.error("Failed to setup shared memory")
            return False
        
        # Start camera
        if not self.start_camera():
            self.logger.error("Failed to start camera")
            return False
        
        self.running = True
        self.capture_interval = interval
        self.update_camera_status(True)
        
        # Start both video streaming and AI monitoring workers
        video_thread = threading.Thread(target=self.video_streaming_worker, daemon=True)
        monitoring_thread = threading.Thread(target=self.monitoring_worker, daemon=True)
        
        video_thread.start()
        monitoring_thread.start()
        
        self.logger.info("Monitoring service started successfully (video streaming + AI monitoring)")
        return True
    
    def start_ai_monitoring(self):
        """Start AI monitoring (separate from video streaming)"""
        self.monitoring_active = True
        self.logger.info("AI monitoring started")
    
    def stop_ai_monitoring(self):
        """Stop AI monitoring"""
        self.monitoring_active = False
        self.logger.info("AI monitoring stopped")
    
    def stop_service(self):
        """Stop the monitoring service"""
        self.logger.info("Stopping monitoring service...")
        
        self.running = False
        self.monitoring_active = False
        
        # Stop camera
        if self.camera:
            self.camera.release()
            self.camera = None
        
        self.camera_active = False
        self.update_camera_status(False)
        
        # Cleanup temporary files
        try:
            if os.path.exists("/tmp/latest_frame.jpg"):
                os.remove("/tmp/latest_frame.jpg")
        except:
            pass
        
        self.logger.info("Monitoring service stopped")

def main():
    """Main function to run the monitoring service"""
    print("=" * 60)
    print("3D Printer Monitoring Service")
    print("Circuit Breakers StormHacks 2025")
    print("=" * 60)
    
    service = PrinterMonitoringService()
    
    try:
        # Start the service
        if service.start_monitoring(interval=30):
            print("✅ Monitoring service started successfully!")
            print("📹 Video streaming: Active")
            print("🤖 AI monitoring: Ready (use API to start/stop)")
            print("🌐 Backend API: http://127.0.0.1:8000")
            print("\nPress Ctrl+C to stop the service")
            print("-" * 60)
            
            # Keep the service running
            while True:
                time.sleep(1)
        else:
            print("❌ Failed to start monitoring service")
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down monitoring service...")
    finally:
        service.stop_service()
        print("✅ Monitoring service stopped")

if __name__ == "__main__":
    main()
