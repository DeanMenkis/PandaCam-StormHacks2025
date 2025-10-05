from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import json
import os
import subprocess
import threading
import time
import base64
from datetime import datetime, timedelta
import pytz
import numpy as np
import cv2
import requests
import re
import shutil

from config import *

from prompt import PROMPT
from alert_system import alert_system

try:
    from picamera import PiCamera
    PICAMERA_AVAILABLE = True
    print("✅ Legacy PiCamera library available")
except (ImportError, OSError):
    PICAMERA_AVAILABLE = False
    # Don't print error - PiCamera2 is preferred anyway

try:
    # Try to import from system packages first
    import sys
    sys.path.insert(0, '/usr/lib/python3/dist-packages')
    from picamera2 import Picamera2
    import libcamera
    PICAMERA2_AVAILABLE = True
    print("✅ PiCamera2 library available")
except (ImportError, OSError) as e:
    PICAMERA2_AVAILABLE = False
    print(f"❌ PiCamera2 library not available: {e}")

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Configuration
app.config['JSON_SORT_KEYS'] = False

# 3D Printer monitoring state
printer_state = {
    "is_running": False,
    "is_monitoring": False,
    "failure_detected": False,
    "last_failure_time": None,
    "video_stream_active": False,
    "print_status": "idle",  # idle, printing, paused, completed, failed
    "print_progress": 0,  # 0-100
    "print_time_elapsed": 0,  # in minutes
    "print_time_remaining": 0,  # in minutes
    "ai_monitoring_active": False,  # AI monitoring status
    "ai_response": "No analysis yet.",  # Latest AI analysis response
    "ai_confidence": 0.0,  # AI confidence level (0.5-1.0)
    "ai_binary_status": 0,  # Binary classification: 1 = good, 0 = bad
    "last_ai_analysis": None,  # Timestamp of last AI analysis
    "ai_countdown": 0,  # Countdown to next AI analysis (seconds)
    "ai_process_status": "idle",  # Current AI process status: idle, capturing, analyzing, processing
    "ai_analysis_count": 0,  # Total number of analyses performed
    "ai_success_rate": 0.0,  # Success rate of AI analyses (0.0-1.0)
    "timestamp": datetime.now().isoformat()
}

# Camera instance
camera = None
camera_active = False
frame_lock = threading.Lock()

# AI Monitoring configuration and state

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
AI_MONITORING_INTERVAL = 10  # seconds - default interval (0.1 Hz)
AI_MAX_RETRIES = 2  # Maximum retries for failed API calls
AI_RETRY_DELAY = 5  # seconds between retries

# AI monitoring thread control
ai_monitoring_thread = None
ai_monitoring_active = False
ai_monitoring_paused = False
ai_monitoring_lock = threading.Lock()

# AI monitoring statistics
ai_stats = {
    "total_analyses": 0,
    "successful_analyses": 0,
    "failed_analyses": 0,
    "last_analysis_time": None,
    "next_analysis_time": None
}

# Global state lock for thread safety
printer_state_lock = threading.Lock()

# History storage configuration
HISTORY_DIR = "ai_history"
HISTORY_IMAGES_DIR = os.path.join(HISTORY_DIR, "images")
HISTORY_MAX_ENTRIES = 100  # Maximum number of history entries to keep

# Create history directories if they don't exist
def ensure_history_directories():
    """Create history storage directories if they don't exist"""
    try:
        os.makedirs(HISTORY_IMAGES_DIR, exist_ok=True)
        print(f"✅ History directories created: {HISTORY_DIR}")
    except Exception as e:
        print(f"❌ Failed to create history directories: {e}")

# Initialize history directories
ensure_history_directories()

class HistoryManager:
    """Manages AI analysis history storage and retrieval"""
    
    def __init__(self, history_dir, images_dir, max_entries=100):
        self.history_dir = history_dir
        self.images_dir = images_dir
        self.max_entries = max_entries
        self.history_file = os.path.join(history_dir, "history.json")
        self.history_lock = threading.Lock()
    
    def save_analysis(self, frame_data, gemini_response, analysis_result):
        """
        Save an AI analysis to history
        
        Args:
            frame_data: JPEG image data as bytes
            gemini_response: Raw response from Gemini
            analysis_result: Parsed analysis result
        """
        try:
            with self.history_lock:
                # Generate unique filename with timestamp
                timestamp = datetime.now()
                filename_base = timestamp.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # Remove last 3 digits of microseconds
                image_filename = f"{filename_base}.jpg"
                image_path = os.path.join(self.images_dir, image_filename)
                
                # Save image
                with open(image_path, 'wb') as f:
                    f.write(frame_data)
                
                # Create history entry
                history_entry = {
                    "id": filename_base,
                    "timestamp": timestamp.isoformat(),
                    "image_filename": image_filename,
                    "image_path": image_path,
                    "gemini_response": gemini_response,
                    "analysis_result": analysis_result,
                    "image_size": len(frame_data),
                    "success": analysis_result.get('success', False),
                    "print_status": analysis_result.get('print_status', 'unknown'),
                    "confidence": analysis_result.get('confidence', 0.0),
                    "binary_status": analysis_result.get('binary_status', 0)
                }
                
                # Load existing history
                history = self._load_history()
                
                # Add new entry
                history.append(history_entry)
                
                # Keep only the most recent entries
                if len(history) > self.max_entries:
                    # Remove oldest entries and their images
                    entries_to_remove = history[:-self.max_entries]
                    for entry in entries_to_remove:
                        try:
                            if os.path.exists(entry['image_path']):
                                os.remove(entry['image_path'])
                        except Exception as e:
                            print(f"⚠️ Failed to remove old image {entry['image_path']}: {e}")
                    history = history[-self.max_entries:]
                
                # Save updated history
                self._save_history(history)
                
                print(f"📸 History entry saved: {filename_base}")
                return history_entry
                
        except Exception as e:
            print(f"❌ Failed to save history entry: {e}")
            return None
    
    def _load_history(self):
        """Load history from JSON file"""
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            print(f"❌ Failed to load history: {e}")
            return []
    
    def _save_history(self, history):
        """Save history to JSON file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
        except Exception as e:
            print(f"❌ Failed to save history: {e}")
    
    def get_history(self, limit=None):
        """Get history entries, optionally limited to recent entries"""
        try:
            with self.history_lock:
                history = self._load_history()
                if limit:
                    return history[-limit:]
                return history
        except Exception as e:
            print(f"❌ Failed to get history: {e}")
            return []
    
    def get_history_entry(self, entry_id):
        """Get a specific history entry by ID"""
        try:
            with self.history_lock:
                history = self._load_history()
                for entry in history:
                    if entry['id'] == entry_id:
                        return entry
                return None
        except Exception as e:
            print(f"❌ Failed to get history entry: {e}")
            return None
    
    def clear_history(self):
        """Clear all history entries and images"""
        try:
            with self.history_lock:
                # Remove all images
                history = self._load_history()
                for entry in history:
                    try:
                        if os.path.exists(entry['image_path']):
                            os.remove(entry['image_path'])
                    except Exception as e:
                        print(f"⚠️ Failed to remove image {entry['image_path']}: {e}")
                
                # Clear history file
                self._save_history([])
                print("🗑️ History cleared")
                return True
        except Exception as e:
            print(f"❌ Failed to clear history: {e}")
            return False

# Initialize history manager
history_manager = HistoryManager(HISTORY_DIR, HISTORY_IMAGES_DIR, HISTORY_MAX_ENTRIES)

class CameraManager:
    def __init__(self):
        self.camera = None
        self.cap = None
        self.is_initialized = False
        self.lock = threading.Lock()
        self.camera_type = None  # 'picamera', 'picamera2', or 'opencv'
    
    def initialize_camera(self):
        """Initialize the Raspberry Pi camera using multiple methods"""
        try:
            with self.lock:
                if self.is_initialized:
                    return True
                
                print("🔍 Initializing Raspberry Pi camera...")
                
                # Method 1: Try PiCamera2 first (newer method, works with modern Pi cameras)
                if PICAMERA2_AVAILABLE and self._try_picamera2():
                    return True
                
                # Method 2: Try legacy PiCamera (fallback for older Pi)
                if PICAMERA_AVAILABLE and self._try_picamera():
                    return True
                
                # Method 3: Try OpenCV (last resort)
                if self._try_opencv():
                    return True
                
                print("❌ Failed to initialize camera with any method")
                print("🔧 Troubleshooting tips:")
                print("   1. Check camera connection")
                print("   2. Ensure camera is enabled in raspi-config")
                print("   3. Try: sudo modprobe bcm2835-v4l2")
                print("   4. Reboot the Pi")
                return False
                    
        except Exception as e:
            print(f"❌ Critical error initializing camera: {e}")
            self.is_initialized = False
            return False
    
    def _try_picamera(self):
        """Try to initialize using legacy PiCamera"""
        try:
            print("📹 Trying legacy PiCamera...")
            self.camera = PiCamera()
            self.camera.resolution = (640, 480)
            self.camera.framerate = 15
            
            # Give camera time to warm up
            time.sleep(2)
            
            # Test capture
            import io
            stream = io.BytesIO()
            self.camera.capture(stream, format='jpeg')
            
            if stream.tell() > 0:
                self.is_initialized = True
                self.camera_type = 'picamera'
                print("✅ Legacy PiCamera initialized successfully!")
                return True
            else:
                self.camera.close()
                self.camera = None
                print("❌ Legacy PiCamera failed to capture test image")
                return False
                
        except Exception as e:
            print(f"❌ Legacy PiCamera error: {e}")
            if self.camera:
                try:
                    self.camera.close()
                except:
                    pass
                self.camera = None
            return False
    
    def _try_picamera2(self):
        """Try to initialize using PiCamera2"""
        try:
            print("📹 Trying PiCamera2...")
            self.camera = Picamera2()
            
            # Use MAXIMUM resolution for ultimate quality!
            print("🚀 Using MAXIMUM resolution: 1456x1088 (1.6MP)!")
            config = self.camera.create_still_configuration(
                main={"size": (1456, 1088), "format": "RGB888"},  # Standard RGB format
                transform=libcamera.Transform(hflip=0, vflip=0),  # No flips
                controls={
                    "FrameRate": 30,  # 30fps for maximum resolution
                    "AwbMode": 2,  # Auto white balance mode 2
                    "ExposureTime": 0,  # Auto exposure
                    "AnalogueGain": 0,  # Auto gain
                }
            )
            
            self.camera.configure(config)
            self.camera.start()
            
            # Set additional controls after starting
            try:
                # Apply auto white balance mode 2
                self.camera.set_controls({
                    "AwbMode": 2,  # Auto white balance mode 2
                })
                print("🎨 Auto white balance enabled (PiCamera2 AWB Mode 2)")
                print("🔄 Transform applied in config: hflip=0, vflip=0 (no flips)")
                    
            except Exception as wb_error:
                print(f"⚠️ White balance control warning: {wb_error}")
                # Continue anyway, basic functionality should still work
            
            # Give camera more time to warm up
            time.sleep(3)
            
            # Test capture with retry
            for attempt in range(3):
                try:
                    frame = self.camera.capture_array()
                    if frame is not None and frame.size > 0:
                        self.is_initialized = True
                        self.camera_type = 'picamera2'
                        print("✅ PiCamera2 initialized successfully!")
                        return True
                    time.sleep(1)
                except Exception as capture_error:
                    print(f"   Capture attempt {attempt + 1} failed: {capture_error}")
                    time.sleep(1)
            
            # If we get here, all capture attempts failed
            self.camera.stop()
            self.camera.close()
            self.camera = None
            print("❌ PiCamera2 failed to capture test frame after 3 attempts")
            return False
                
        except Exception as e:
            print(f"❌ PiCamera2 error: {e}")
            if self.camera:
                try:
                    self.camera.stop()
                    self.camera.close()
                except:
                    pass
                self.camera = None
            return False
    
    def _try_opencv(self):
        """Try to initialize using OpenCV with enhanced compatibility"""
        try:
            print("📹 Trying OpenCV VideoCapture...")
            
            # Try different camera indices and configurations
            camera_configs = [
                {"index": 0, "width": 640, "height": 480, "fps": 30},
                {"index": 0, "width": 320, "height": 240, "fps": 15},
                {"index": 0, "width": 1280, "height": 720, "fps": 30},
                {"index": 1, "width": 640, "height": 480, "fps": 30},
                {"index": 2, "width": 640, "height": 480, "fps": 30},
            ]
            
            for config in camera_configs:
                print(f"   Testing camera index {config['index']} ({config['width']}x{config['height']})...")
                
                # Try different backends
                backends = [cv2.CAP_ANY, cv2.CAP_V4L2]
                
                for backend in backends:
                    try:
                        self.cap = cv2.VideoCapture(config['index'], backend)
                        
                        if self.cap.isOpened():
                            # Set camera properties
                            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config['width'])
                            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config['height'])
                            self.cap.set(cv2.CAP_PROP_FPS, config['fps'])
                            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                            
                            # Wait for camera to initialize
                            time.sleep(3)
                            
                            # Test multiple frame captures
                            success_count = 0
                            for i in range(5):
                                ret, frame = self.cap.read()
                                if ret and frame is not None and frame.size > 0:
                                    success_count += 1
                                time.sleep(0.2)
                            
                            if success_count >= 2:  # At least 2 successful captures
                                self.is_initialized = True
                                self.camera_type = 'opencv'
                                print(f"✅ OpenCV camera initialized on index {config['index']} with {config['width']}x{config['height']}!")
                                return True
                            else:
                                print(f"   ❌ Backend {backend} failed - only {success_count}/5 frames captured")
                                self.cap.release()
                                self.cap = None
                        else:
                            print(f"   ❌ Backend {backend} - camera not available")
                            
                    except Exception as e:
                        print(f"   ❌ Backend {backend} error: {e}")
                        if self.cap:
                            self.cap.release()
                            self.cap = None
            
            print("❌ OpenCV failed on all camera indices and configurations")
            return False
                
        except Exception as e:
            print(f"❌ OpenCV error: {e}")
            if self.cap:
                self.cap.release()
                self.cap = None
            return False
    
    def capture_frame(self):
        """Capture a frame from the camera"""
        try:
            if not self.is_initialized:
                return None
            
            with self.lock:
                if self.camera_type == 'picamera':
                    return self._capture_picamera()
                elif self.camera_type == 'picamera2':
                    return self._capture_picamera2()
                elif self.camera_type == 'opencv':
                    return self._capture_opencv()
                else:
                    return None
                
        except Exception as e:
            print(f"Error capturing frame: {e}")
            return None
    
    def capture_ai_frame(self):
        """Capture a high-resolution frame for AI analysis"""
        try:
            if not self.is_initialized:
                return None
            
            with self.lock:
                if self.camera_type == 'picamera2':
                    return self._capture_picamera2_ai()
                else:
                    # Fallback to regular capture
                    return self.capture_frame()
        except Exception as e:
            print(f"Error capturing AI frame: {e}")
            return None
    
    def _capture_picamera(self):
        """Capture frame using legacy PiCamera"""
        try:
            import io
            stream = io.BytesIO()
            self.camera.capture(stream, format='jpeg')
            stream.seek(0)
            return stream.read()
        except Exception as e:
            print(f"PiCamera capture error: {e}")
            return None
    
    def _capture_picamera2(self):
        """Capture frame using PiCamera2 for streaming (fast, RGB888)"""
        try:
            # Capture RGB frame directly
            frame = self.camera.capture_array()
            
            # PiCamera2 returns RGB, keep as RGB for JPEG encoding
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                frame_rgb = frame
            else:
                frame_rgb = frame
            
            # Compress to JPEG for streaming (high quality for max resolution)
            # Use RGB format directly - no conversion needed
            _, buffer = cv2.imencode('.jpg', frame_rgb, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return buffer.tobytes()
            
        except Exception as e:
            print(f"PiCamera2 streaming capture error: {e}")
            return None
    
    def _capture_picamera2_ai(self):
        """Capture high-resolution frame for AI analysis"""
        try:
            # Capture RGB frame for AI analysis
            frame = self.camera.capture_array()
            
            # PiCamera2 returns RGB, keep as RGB for AI
            if len(frame.shape) == 3 and frame.shape[2] == 3:
                frame_rgb = frame
            else:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Resize to optimal size for AI (keep aspect ratio)
            height, width = frame_rgb.shape[:2]
            target_size = 1280  # Good balance for AI analysis
            
            if width > height:
                new_width = target_size
                new_height = int(height * target_size / width)
            else:
                new_height = target_size
                new_width = int(width * target_size / height)
            
            resized_frame = cv2.resize(frame_rgb, (new_width, new_height))
            
            # High quality JPEG for AI analysis
            _, buffer = cv2.imencode('.jpg', resized_frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
            return buffer.tobytes()
            
        except Exception as e:
            print(f"PiCamera2 AI capture error: {e}")
            return None
    
    def _capture_opencv(self):
        """Capture frame using OpenCV with enhanced error handling"""
        try:
            # Try multiple times to capture a frame
            for attempt in range(3):
                ret, frame = self.cap.read()
                if ret and frame is not None and frame.size > 0:
                    if frame.shape[:2] != (480, 640):
                        frame = cv2.resize(frame, (640, 480))
                    
                    # Resize frame to 720p 16:9 aspect ratio for AI analysis
                    resized_frame = cv2.resize(frame, (1280, 720))  # 720p 16:9 aspect ratio
                    
                    _, buffer = cv2.imencode('.jpg', resized_frame, [cv2.IMWRITE_JPEG_QUALITY, 90])  # High quality for AI
                    return buffer.tobytes()
                else:
                    if attempt < 2:  # Don't sleep on last attempt
                        time.sleep(0.1)
            
            print("⚠️ OpenCV frame capture failed after 3 attempts")
            return None
        except Exception as e:
            print(f"OpenCV capture error: {e}")
            return None
    
    
    def stop_camera(self):
        """Stop and cleanup the camera"""
        try:
            with self.lock:
                if self.camera_type == 'picamera' and self.camera:
                    self.camera.close()
                    self.camera = None
                elif self.camera_type == 'picamera2' and self.camera:
                    self.camera.stop()
                    self.camera.close()
                    self.camera = None
                elif self.camera_type == 'opencv' and self.cap:
                    self.cap.release()
                    self.cap = None
                
                self.is_initialized = False
                self.camera_type = None
                print("✅ Camera stopped and cleaned up")
        except Exception as e:
            print(f"Error stopping camera: {e}")

# Initialize camera manager
camera_manager = CameraManager()

class GeminiAIAnalyzer:
    """AI analyzer using Google Gemini Vision API for 3D print monitoring"""
    
    def __init__(self, api_key, api_url):
        self.api_key = api_key
        self.api_url = api_url
        self.prompt = PROMPT
    
    def analyze_frame(self, frame_data, retry_count=0):
        """
        Analyze a frame using Gemini Vision API with retry logic
        
        Args:
            frame_data: JPEG image data as bytes
            retry_count: Current retry attempt (internal use)
            
        Returns:
            dict: {
                'success': bool,
                'response_text': str,
                'print_status': str,  # 'printing', 'warning', 'failed', 'idle'
                'confidence': float,  # 0.5-1.0
                'error': str or None
            }
        """
        try:
            print(f"🔍 Starting Gemini API analysis at {datetime.now().strftime('%H:%M:%S')}")
            
            if not frame_data:
                print("❌ No frame data provided to Gemini analyzer")
                return {
                    'success': False,
                    'response_text': None,
                    'print_status': 'idle',
                    'confidence': 0.5,
                    'error': 'No frame data provided'
                }
            
            print(f"📷 Frame data size: {len(frame_data)} bytes")
            
            # Encode frame as base64
            frame_b64 = base64.b64encode(frame_data).decode('utf-8')
            print(f"📝 Base64 encoded frame size: {len(frame_b64)} characters")
            
            # Prepare request payload
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": self.prompt},
                            {
                                "inline_data": {
                                    "mime_type": "image/jpeg",
                                    "data": frame_b64
                                }
                            }
                        ]
                    }
                ]
            }
            
            print(f"🌐 Sending request to Gemini API: {self.api_url}")
            print(f"🔑 Using API key: {self.api_key[:20]}...{self.api_key[-10:]}")
            
            # Make API request
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f"{self.api_url}?key={self.api_key}",
                headers=headers,
                json=payload,
                timeout=15  # Reduced from 30 to 15 seconds
            )
            
            print(f"📡 Gemini API response status: {response.status_code}")
            print(f"📡 Response headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Gemini API response received successfully")
                print(f"📄 Raw response: {json.dumps(result, indent=2)}")
                
                # Extract response text
                if 'candidates' in result and len(result['candidates']) > 0:
                    candidate = result['candidates'][0]
                    if 'content' in candidate and 'parts' in candidate['content']:
                        response_text = candidate['content']['parts'][0].get('text', '')
                        
                        # Parse the response
                        parsed = self._parse_response(response_text)
                        
                        # Get binary classification
                        binary_status = self._get_binary_classification(response_text, parsed['print_status'])
                        
                        return {
                            'success': True,
                            'response_text': response_text,
                            'print_status': parsed['print_status'],
                            'confidence': parsed['confidence'],
                            'binary_status': binary_status,  # 1 = good, 0 = bad
                            'error': None
                        }
                
                return {
                    'success': False,
                    'response_text': None,
                    'print_status': 'idle',
                    'confidence': 0.5,
                    'error': 'Invalid response format from Gemini API'
                }
            else:
                error_msg = f"Gemini API error: {response.status_code} - {response.text}"
                print(f"❌ {error_msg}")
                return {
                    'success': False,
                    'response_text': None,
                    'print_status': 'idle',
                    'confidence': 0.5,
                    'error': error_msg
                }
                
        except requests.exceptions.Timeout:
            error_msg = 'Gemini API request timeout'
            print(f"⏰ {error_msg}")
            
            # Retry logic for timeout
            if retry_count < AI_MAX_RETRIES:
                print(f"🔄 Retrying Gemini API call (attempt {retry_count + 1}/{AI_MAX_RETRIES})")
                time.sleep(AI_RETRY_DELAY)
                return self.analyze_frame(frame_data, retry_count + 1)
            
            return {
                'success': False,
                'response_text': None,
                'print_status': 'idle',
                'confidence': 0.5,
                'error': f'{error_msg} (after {AI_MAX_RETRIES} retries)'
            }
        except requests.exceptions.RequestException as e:
            error_msg = f'Gemini API request failed: {str(e)}'
            print(f"🌐 {error_msg}")
            
            # Retry logic for network errors
            if retry_count < AI_MAX_RETRIES and ('timeout' in str(e).lower() or 'connection' in str(e).lower()):
                print(f"🔄 Retrying Gemini API call (attempt {retry_count + 1}/{AI_MAX_RETRIES})")
                time.sleep(AI_RETRY_DELAY)
                return self.analyze_frame(frame_data, retry_count + 1)
            
            return {
                'success': False,
                'response_text': None,
                'print_status': 'idle',
                'confidence': 0.5,
                'error': error_msg
            }
        except Exception as e:
            error_msg = f'Unexpected error: {str(e)}'
            print(f"💥 {error_msg}")
            return {
                'success': False,
                'response_text': None,
                'print_status': 'idle',
                'confidence': 0.5,
                'error': error_msg
            }
    
    def _parse_response(self, response_text):
        """
        Parse Gemini response to extract print status and confidence
        
        Args:
            response_text: Raw response from Gemini
            
        Returns:
            dict: {'print_status': str, 'confidence': float}
        """
        if not response_text:
            return {'print_status': 'idle', 'confidence': 0.5}
        
        # Convert to uppercase for easier matching
        text_upper = response_text.upper()
        
        # Determine print status based on response prefix
        if text_upper.startswith('✅'):
            print_status = 'printing'
            base_confidence = 0.9
        elif text_upper.startswith('⚠️'):
            print_status = 'warning'
            base_confidence = 0.8
        elif text_upper.startswith('❌'):
            print_status = 'failed'
            base_confidence = 0.85
        elif text_upper.startswith('🤷'):
            print_status = 'idle'
            base_confidence = 0.7
        else:
            # Fallback: try to detect keywords
            if any(word in text_upper for word in ['GOOD', 'NORMAL', 'FINE', 'SUCCESSFUL']):
                print_status = 'printing'
                base_confidence = 0.6
            elif any(word in text_upper for word in ['ISSUE', 'PROBLEM', 'WARNING', 'CONCERN']):
                print_status = 'warning'
                base_confidence = 0.6
            elif any(word in text_upper for word in ['FAILURE', 'FAILED', 'ERROR', 'BROKEN']):
                print_status = 'failed'
                base_confidence = 0.6
            else:
                print_status = 'idle'
                base_confidence = 0.5
        
        # Adjust confidence based on response length and specificity
        word_count = len(response_text.split())
        if word_count > 20:  # Detailed response
            confidence = min(base_confidence + 0.05, 1.0)
        elif word_count < 5:  # Very short response
            confidence = max(base_confidence - 0.1, 0.5)
        else:
            confidence = base_confidence
        
        return {
            'print_status': print_status,
            'confidence': round(confidence, 2)
        }
    
    def _get_binary_classification(self, response_text, print_status):
        """
        Convert AI response to binary classification
        
        Args:
            response_text: Raw response from Gemini
            print_status: Parsed print status
            
        Returns:
            int: 1 if print is going well, 0 if not going well
        """
        if not response_text:
            return 0
        
        # Primary classification based on print status
        if print_status == 'printing':
            return 1  # Print is going well
        elif print_status in ['failed', 'warning']:
            return 0  # Print is not going well
        elif print_status == 'idle':
            # For idle status, check if there's actually a printer visible
            text_upper = response_text.upper()
            if 'NO PRINTER' in text_upper or 'NOT VISIBLE' in text_upper:
                return 0  # No printer visible = not going well
            else:
                return 1  # Printer visible but idle = neutral/good
        
        # Fallback: analyze response text for positive/negative indicators
        text_upper = response_text.upper()
        
        # Positive indicators (including bed-related terms that should be considered normal)
        positive_words = ['GOOD', 'FINE', 'NORMAL', 'SUCCESSFUL', 'WELL', 'PERFECT', 'EXCELLENT', 'SMOOTH', 'OKAY', 'ADHERING', 'BUILDING']
        # Negative indicators (actual print problems, not bed cleanliness)
        negative_words = ['WARPED', 'DETACHED', 'CLOGGED', 'FALLEN', 'SPAGHETTI', 'STRINGY', 'DEFORMED', 'CURLED', 'MOVING']
        
        # Don't consider bed-related issues as negative
        bed_words = ['DIRTY', 'MESSY', 'RESIDUE', 'DEBRIS', 'DUST', 'REMNANTS', 'USED', 'WORN']
        # If response mentions bed issues but no actual print problems, lean positive
        has_bed_mentions = any(word in text_upper for word in bed_words)
        has_print_problems = any(word in text_upper for word in negative_words)
        
        positive_count = sum(1 for word in positive_words if word in text_upper)
        negative_count = sum(1 for word in negative_words if word in text_upper)
        
        # Special case: if bed issues mentioned but no actual print problems, consider it good
        if has_bed_mentions and not has_print_problems:
            print(f"🛏️ Bed issues detected but no print problems - classifying as GOOD (1)")
            return 1
        
        if positive_count > negative_count:
            return 1
        elif negative_count > positive_count:
            return 0
        else:
            # Tie or no clear indicators - default based on emoji
            if response_text.startswith('✅'):
                return 1
            elif response_text.startswith(('❌', '⚠️')):
                return 0
            else:
                return 1  # Default to positive for ambiguous cases

# Initialize AI analyzer
ai_analyzer = GeminiAIAnalyzer(GEMINI_API_KEY, GEMINI_API_URL)

def ai_monitoring_worker():
    """
    AI monitoring worker thread that captures frames at configurable intervals
    and analyzes them using Gemini Vision API
    """
    global ai_monitoring_active, ai_monitoring_paused, printer_state, camera_manager, ai_analyzer, ai_stats
    
    print("🤖 AI monitoring thread started")
    
    # Initialize next analysis time
    ai_stats["next_analysis_time"] = datetime.now()
    
    while ai_monitoring_active:
        try:
            # Update countdown and process status
            current_time = datetime.now()
            if ai_stats["next_analysis_time"]:
                time_until_next = (ai_stats["next_analysis_time"] - current_time).total_seconds()
                countdown = max(0, int(time_until_next))
            else:
                countdown = 0
            
            # Update printer state with countdown and process status
            with printer_state_lock:
                printer_state["ai_countdown"] = countdown
                if ai_monitoring_paused:
                    printer_state["ai_process_status"] = "paused"
                else:
                    printer_state["ai_process_status"] = "waiting"
                printer_state["ai_analysis_count"] = ai_stats["total_analyses"]
                if ai_stats["total_analyses"] > 0:
                    printer_state["ai_success_rate"] = ai_stats["successful_analyses"] / ai_stats["total_analyses"]
                else:
                    printer_state["ai_success_rate"] = 0.0
                printer_state["timestamp"] = current_time.isoformat()
            
            # If paused, just wait and continue
            if ai_monitoring_paused:
                time.sleep(1)
                continue
            
            # Wait until it's time for the next analysis
            if countdown > 0:
                time.sleep(1)  # Update countdown every second
                continue
            # Update process status to capturing
            with printer_state_lock:
                printer_state["ai_process_status"] = "capturing"
                printer_state["timestamp"] = current_time.isoformat()
            
            # Check if camera is available, wait for it to be initialized by video stream
            if not camera_manager.is_initialized:
                print("📹 AI monitoring: Waiting for camera to be initialized by video stream...")
                with printer_state_lock:
                    printer_state["ai_process_status"] = "waiting_for_camera"
                    printer_state["timestamp"] = current_time.isoformat()
                # Wait longer for camera to be initialized
                ai_stats["next_analysis_time"] = datetime.now() + timedelta(seconds=5)
                time.sleep(1)
                continue
            
            # Double-check camera is still initialized before capturing
            if not camera_manager.is_initialized:
                print("❌ AI monitoring: Camera not available, skipping analysis")
                with printer_state_lock:
                    printer_state["ai_process_status"] = "camera_unavailable"
                    printer_state["timestamp"] = current_time.isoformat()
                ai_stats["next_analysis_time"] = datetime.now() + timedelta(seconds=AI_MONITORING_INTERVAL)
                time.sleep(1)
                continue
            
            # Capture high-resolution frame for AI analysis
            print(f"📸 AI monitoring: Attempting to capture AI frame at {datetime.now().strftime('%H:%M:%S')}")
            frame_data = camera_manager.capture_ai_frame()
            
            if frame_data and len(frame_data) > 1000:  # Ensure frame has meaningful data
                print(f"✅ Frame captured successfully, size: {len(frame_data)} bytes")
                print(f"🤖 AI monitoring: Analyzing frame at {datetime.now().strftime('%H:%M:%S')}")
                
                # Update process status to analyzing
                with printer_state_lock:
                    printer_state["ai_process_status"] = "analyzing"
                    printer_state["timestamp"] = current_time.isoformat()
                
                # Analyze frame with Gemini
                analysis_result = ai_analyzer.analyze_frame(frame_data)
                
                # Save to history
                if analysis_result['success']:
                    history_manager.save_analysis(
                        frame_data, 
                        analysis_result['response_text'], 
                        analysis_result
                    )
                
                # Update statistics
                ai_stats["total_analyses"] += 1
                if analysis_result['success']:
                    ai_stats["successful_analyses"] += 1
                else:
                    ai_stats["failed_analyses"] += 1
                ai_stats["last_analysis_time"] = current_time
                
                # Update printer state with thread safety
                with printer_state_lock:
                    if analysis_result['success']:
                        # Update state based on AI analysis
                        printer_state["ai_response"] = analysis_result['response_text']
                        printer_state["ai_confidence"] = analysis_result['confidence']
                        printer_state["ai_binary_status"] = analysis_result['binary_status']
                        printer_state["last_ai_analysis"] = datetime.now().isoformat()
                        
                        # Debug logging
                        print(f"🔍 AI Worker: Updated ai_response: {analysis_result['response_text'][:100]}...")
                        print(f"🔍 AI Worker: Updated ai_confidence: {analysis_result['confidence']}")
                        print(f"🔍 AI Worker: Updated ai_binary_status: {analysis_result['binary_status']}")
                        
                        # Update main print status based on binary classification
                        if analysis_result['binary_status'] == 1:
                            # Print is going well
                            if analysis_result['print_status'] == 'idle':
                                printer_state["print_status"] = "idle"
                            else:
                                printer_state["print_status"] = "printing"
                            printer_state["failure_detected"] = False
                        else:
                            # Print is not going well (binary_status == 0)
                            if analysis_result['print_status'] == 'failed':
                                printer_state["print_status"] = "failed"
                            else:
                                printer_state["print_status"] = "warning"
                            printer_state["failure_detected"] = True
                            printer_state["last_failure_time"] = datetime.now().isoformat()
                        
                        # Log AI response with binary classification
                        local_tz = pytz.timezone('America/Los_Angeles')
                        local_time = datetime.now(local_tz)
                        timestamp = local_time.strftime('%Y-%m-%d %H:%M:%S %Z')
                        binary_emoji = "✅" if analysis_result['binary_status'] == 1 else "❌"
                        print(f"🤖 [{timestamp}] AI Analysis: {analysis_result['response_text']}")
                        print(f"   Binary Status: {binary_emoji} {analysis_result['binary_status']} | Print Status: {printer_state['print_status']} | Confidence: {analysis_result['confidence']}")
                        
                        # Alert for failures
                        if analysis_result['binary_status'] == 0:
                            print(f"🚨 AI DETECTED ISSUE: Binary classification = 0 (not going well)")
                            print(f"   📊 Status: {analysis_result['print_status']} | Confidence: {analysis_result['confidence']:.1%}")
                            print(f"   📝 Response: {analysis_result['response_text'][:100]}...")
                            
                            # Send Discord alert with image and full details
                            alert_success = alert_system.send_print_failure_alert(
                                analysis_result['print_status'],
                                analysis_result['confidence'],
                                analysis_result['response_text'],
                                frame_data,  # Include the captured image
                                ai_analyzer.prompt  # Include the Gemini prompt
                            )
                            
                            if alert_success:
                                print("✅ Discord alert sent successfully")
                            else:
                                print("❌ Discord alert failed or was blocked")
                        
                    else:
                        # Handle analysis error
                        printer_state["ai_response"] = f"Analysis error: {analysis_result['error']}"
                        printer_state["ai_confidence"] = 0.5
                        printer_state["last_ai_analysis"] = datetime.now().isoformat()
                        print(f"❌ AI analysis error: {analysis_result['error']}")
                    
                    # Update process status to processing and set next analysis time
                    printer_state["ai_process_status"] = "processing"
                    printer_state["ai_analysis_count"] = ai_stats["total_analyses"]
                    if ai_stats["total_analyses"] > 0:
                        printer_state["ai_success_rate"] = ai_stats["successful_analyses"] / ai_stats["total_analyses"]
                    printer_state["timestamp"] = datetime.now().isoformat()
                    
                    # Schedule next analysis
                    ai_stats["next_analysis_time"] = datetime.now() + timedelta(seconds=AI_MONITORING_INTERVAL)
                    
                    # Reset process status to waiting for next cycle
                    printer_state["ai_process_status"] = "waiting"
            else:
                print("⚠️ AI monitoring: Failed to capture frame")
                with printer_state_lock:
                    # Don't overwrite existing AI response, just update process status
                    printer_state["ai_process_status"] = "capture_failed"
                    printer_state["timestamp"] = datetime.now().isoformat()
                
                # Schedule next analysis
                ai_stats["next_analysis_time"] = datetime.now() + timedelta(seconds=AI_MONITORING_INTERVAL)
                
                # Reset process status to waiting for next cycle
                printer_state["ai_process_status"] = "waiting"
            
            # Wait for next analysis cycle (will be handled by countdown logic)
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ AI monitoring thread error: {e}")
            with printer_state_lock:
                # Don't overwrite existing AI response, just update process status
                printer_state["ai_process_status"] = "error"
                printer_state["timestamp"] = datetime.now().isoformat()
            
            # Schedule next analysis with longer delay on error
            ai_stats["next_analysis_time"] = datetime.now() + timedelta(seconds=AI_MONITORING_INTERVAL * 2)
            time.sleep(1)
    
    print("🤖 AI monitoring thread stopped")

def start_ai_monitoring():
    """Start the AI monitoring thread"""
    global ai_monitoring_thread, ai_monitoring_active, printer_state
    
    with printer_state_lock:
        if ai_monitoring_active:
            return False, "AI monitoring is already active"
        
        try:
            ai_monitoring_active = True
            printer_state["ai_monitoring_active"] = True
            
            # Start the monitoring thread
            ai_monitoring_thread = threading.Thread(target=ai_monitoring_worker, daemon=True)
            ai_monitoring_thread.start()
            
            print("✅ AI monitoring started successfully")
            return True, "AI monitoring started successfully"
            
        except Exception as e:
            ai_monitoring_active = False
            printer_state["ai_monitoring_active"] = False
            error_msg = f"Failed to start AI monitoring: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

def stop_ai_monitoring():
    """Stop the AI monitoring thread"""
    global ai_monitoring_thread, ai_monitoring_active, printer_state
    
    with printer_state_lock:
        if not ai_monitoring_active:
            return False, "AI monitoring is not active"
        
        try:
            ai_monitoring_active = False
            printer_state["ai_monitoring_active"] = False
            
            # Wait for thread to finish (with timeout)
            if ai_monitoring_thread and ai_monitoring_thread.is_alive():
                ai_monitoring_thread.join(timeout=2)
            
            print("✅ AI monitoring stopped successfully")
            return True, "AI monitoring stopped successfully"
            
        except Exception as e:
            error_msg = f"Error stopping AI monitoring: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

@app.route('/')
def home():
    """Health check endpoint"""
    return jsonify({
        "message": "3D Printer Monitoring System",
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/printer/status', methods=['GET'])
def get_printer_status():
    """Get current printer monitoring status"""
    try:
        global printer_state
        
        # Thread-safe access to printer state - minimize lock time
        with printer_state_lock:
            printer_state["timestamp"] = datetime.now().isoformat()
            enhanced_state = printer_state.copy()
        
        # Process AI status outside the lock to reduce lock time
        if enhanced_state.get("ai_monitoring_active", False):
            ai_status_emoji = "🤖"
            if enhanced_state.get("ai_response"):
                if enhanced_state["ai_response"].startswith("✅"):
                    ai_status_emoji = "✅"
                elif enhanced_state["ai_response"].startswith("⚠️"):
                    ai_status_emoji = "⚠️"
                elif enhanced_state["ai_response"].startswith("❌"):
                    ai_status_emoji = "❌"
                elif enhanced_state["ai_response"].startswith("🤷"):
                    ai_status_emoji = "🤷"
            
            enhanced_state["ai_status_summary"] = {
                "active": True,
                "emoji": ai_status_emoji,
                "status": enhanced_state.get("print_status", "idle"),
                "confidence": enhanced_state.get("ai_confidence", 0.0),
                "last_analysis": enhanced_state.get("last_ai_analysis"),
                "response": enhanced_state.get("ai_response", "No analysis yet")
            }
        else:
            enhanced_state["ai_status_summary"] = {
                "active": False,
                "emoji": "🔴",
                "status": "disabled",
                "confidence": 0.0,
                "last_analysis": None,
                "response": "AI monitoring not active"
            }
        
        return jsonify({
            "success": True,
            "data": enhanced_state,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/printer/start', methods=['POST'])
def start_printer():
    """Start 3D printer monitoring"""
    try:
        global printer_state
        
        with printer_state_lock:
            printer_state["is_running"] = True
            printer_state["is_monitoring"] = True
            printer_state["failure_detected"] = False
            printer_state["timestamp"] = datetime.now().isoformat()
            result_state = printer_state.copy()
        
        # Here you would start your actual printer monitoring application
        # For now, we'll just update the state
        
        return jsonify({
            "success": True,
            "message": "Printer monitoring started",
            "data": result_state,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/printer/stop', methods=['POST'])
def stop_printer():
    """Stop 3D printer monitoring"""
    try:
        global printer_state, video_process
        
        with printer_state_lock:
            printer_state["is_running"] = False
            printer_state["is_monitoring"] = False
            printer_state["video_stream_active"] = False
            printer_state["timestamp"] = datetime.now().isoformat()
            result_state = printer_state.copy()
        
        # Stop AI monitoring if active
        if ai_monitoring_active:
            stop_ai_monitoring()
        
        # Stop camera if active
        global camera_manager
        camera_manager.stop_camera()
        global camera_active
        camera_active = False
        
        # Here you would stop your actual printer monitoring application
        
        return jsonify({
            "success": True,
            "message": "Printer monitoring stopped",
            "data": printer_state,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/printer/failure', methods=['POST'])
def report_failure():
    """Report a print failure from external monitoring app"""
    try:
        data = request.get_json()
        global printer_state
        
        if data and "failure_detected" in data:
            printer_state["failure_detected"] = data["failure_detected"]
            if data["failure_detected"]:
                printer_state["last_failure_time"] = datetime.now().isoformat()
                printer_state["print_status"] = "failed"
            printer_state["timestamp"] = datetime.now().isoformat()
            
            return jsonify({
                "success": True,
                "message": "Failure status updated",
                "data": printer_state,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": "Invalid data provided"
            }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/printer/print-status', methods=['POST'])
def update_print_status():
    """Update print status from external monitoring app"""
    try:
        data = request.get_json()
        global printer_state
        
        if data:
            # Update print status fields if provided
            if "print_status" in data:
                printer_state["print_status"] = data["print_status"]
            if "print_progress" in data:
                printer_state["print_progress"] = data["print_progress"]
            if "print_time_elapsed" in data:
                printer_state["print_time_elapsed"] = data["print_time_elapsed"]
            if "print_time_remaining" in data:
                printer_state["print_time_remaining"] = data["print_time_remaining"]
            
            printer_state["timestamp"] = datetime.now().isoformat()
            
            return jsonify({
                "success": True,
                "message": "Print status updated",
                "data": printer_state,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": "No data provided"
            }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/ai/start', methods=['POST'])
def start_ai_monitoring_endpoint():
    """Start AI-based print failure monitoring"""
    try:
        success, message = start_ai_monitoring()
        
        if success:
            return jsonify({
                "success": True,
                "message": message,
                "data": {
                    "ai_monitoring_active": printer_state["ai_monitoring_active"],
                    "monitoring_interval": AI_MONITORING_INTERVAL
                },
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": message,
                "timestamp": datetime.now().isoformat()
            }), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/ai/stop', methods=['POST'])
def stop_ai_monitoring_endpoint():
    """Stop AI-based print failure monitoring"""
    try:
        success, message = stop_ai_monitoring()
        
        if success:
            return jsonify({
                "success": True,
                "message": message,
                "data": {
                    "ai_monitoring_active": printer_state["ai_monitoring_active"]
                },
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": message,
                "timestamp": datetime.now().isoformat()
            }), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/ai/status', methods=['GET'])
def get_ai_status():
    """Get current AI monitoring status and latest analysis results"""
    try:
        with printer_state_lock:
            ai_status = {
                "ai_monitoring_active": printer_state["ai_monitoring_active"],
                "ai_monitoring_paused": ai_monitoring_paused,
                "ai_response": printer_state["ai_response"],
                "ai_confidence": printer_state["ai_confidence"],
                "ai_binary_status": printer_state["ai_binary_status"],
                "print_status": printer_state["print_status"],
                "last_ai_analysis": printer_state["last_ai_analysis"],
                "failure_detected": printer_state["failure_detected"],
                "last_failure_time": printer_state["last_failure_time"],
                "monitoring_interval": AI_MONITORING_INTERVAL,
                "monitoring_frequency_hz": 1.0 / AI_MONITORING_INTERVAL,
                "ai_countdown": printer_state["ai_countdown"],
                "ai_process_status": printer_state["ai_process_status"],
                "ai_analysis_count": printer_state["ai_analysis_count"],
                "ai_success_rate": printer_state["ai_success_rate"],
                "next_analysis_time": ai_stats["next_analysis_time"].isoformat() if ai_stats["next_analysis_time"] else None
            }
            
            # Debug logging for AI response
            if printer_state["ai_response"] and printer_state["ai_response"] != "No analysis yet.":
                print(f"🔍 AI Status API: Sending response to frontend: {printer_state['ai_response'][:100]}...")
        
        return jsonify({
            "success": True,
            "data": ai_status,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    """Get AI analysis history"""
    try:
        limit = request.args.get('limit', type=int)
        history = history_manager.get_history(limit)
        
        return jsonify({
            "success": True,
            "data": {
                "entries": history,
                "total_count": len(history)
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/history/<entry_id>', methods=['GET'])
def get_history_entry(entry_id):
    """Get a specific history entry"""
    try:
        entry = history_manager.get_history_entry(entry_id)
        if entry:
            return jsonify({
                "success": True,
                "data": entry,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": "History entry not found",
                "timestamp": datetime.now().isoformat()
            }), 404
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/history/image/<entry_id>')
def get_history_image(entry_id):
    """Get history image by entry ID"""
    try:
        entry = history_manager.get_history_entry(entry_id)
        if entry and os.path.exists(entry['image_path']):
            with open(entry['image_path'], 'rb') as f:
                image_data = f.read()
            return Response(
                image_data,
                mimetype='image/jpeg',
                headers={'Content-Disposition': f'inline; filename={entry["image_filename"]}'}
            )
        else:
            return jsonify({
                "success": False,
                "error": "Image not found"
            }), 404
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/history/clear', methods=['POST'])
def clear_history():
    """Clear all history entries"""
    try:
        success = history_manager.clear_history()
        if success:
            return jsonify({
                "success": True,
                "message": "History cleared successfully",
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to clear history",
                "timestamp": datetime.now().isoformat()
            }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/ai/interval', methods=['POST'])
def set_ai_interval():
    """Set AI monitoring interval in seconds"""
    try:
        data = request.get_json()
        if not data or 'interval' not in data:
            return jsonify({
                "success": False,
                "error": "Interval value required"
            }), 400
        
        interval_seconds = float(data['interval'])
        if interval_seconds < 5 or interval_seconds > 60:
            return jsonify({
                "success": False,
                "error": "Interval must be between 5 and 60 seconds"
            }), 400
        
        global AI_MONITORING_INTERVAL
        AI_MONITORING_INTERVAL = interval_seconds
        
        return jsonify({
            "success": True,
            "message": f"AI monitoring interval set to {interval_seconds} seconds",
            "data": {
                "interval_seconds": interval_seconds,
                "frequency_hz": 1.0 / interval_seconds
            },
            "timestamp": datetime.now().isoformat()
        })
    except ValueError:
        return jsonify({
            "success": False,
            "error": "Invalid interval value"
        }), 400
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/ai/pause', methods=['POST'])
def pause_ai_monitoring():
    """Pause AI monitoring"""
    try:
        global ai_monitoring_paused
        
        with printer_state_lock:
            ai_monitoring_paused = True
            printer_state["ai_process_status"] = "paused"
            printer_state["timestamp"] = datetime.now().isoformat()
        
        return jsonify({
            "success": True,
            "message": "AI monitoring paused",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/ai/resume', methods=['POST'])
def resume_ai_monitoring():
    """Resume AI monitoring"""
    try:
        global ai_monitoring_paused
        
        with printer_state_lock:
            ai_monitoring_paused = False
            printer_state["ai_process_status"] = "waiting"
            printer_state["timestamp"] = datetime.now().isoformat()
        
        return jsonify({
            "success": True,
            "message": "AI monitoring resumed",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/ai/prompt', methods=['GET'])
def get_ai_prompt():
    """Get the current AI analysis prompt"""
    try:
        return jsonify({
            "success": True,
            "data": {
                "prompt": PROMPT
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500




def create_placeholder_frame(message="Camera Not Active", submessage="Initializing camera..."):
    """Create a placeholder frame when no camera is active"""
    try:
        # Create a black frame with text
        placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add text to the placeholder
        cv2.putText(placeholder, message, (50, 200), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(placeholder, submessage, (50, 250), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
        
        # Add timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        cv2.putText(placeholder, f"Time: {timestamp}", (50, 300), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150, 150, 150), 1)
        
        # Encode as JPEG
        _, buffer = cv2.imencode('.jpg', placeholder, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return buffer.tobytes()
    except Exception as e:
        print(f"Error creating placeholder frame: {e}")
        return None

@app.route('/api/camera/start', methods=['POST'])
def start_camera():
    """Manually start the camera"""
    try:
        global camera_manager, camera_active
        
        if camera_manager.initialize_camera():
            camera_active = True
            return jsonify({
                "success": True,
                "message": "Camera started successfully",
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to initialize camera",
                "timestamp": datetime.now().isoformat()
            }), 500
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/camera/stop', methods=['POST'])
def stop_camera_endpoint():
    """Manually stop the camera"""
    try:
        global camera_manager, camera_active
        camera_manager.stop_camera()
        camera_active = False
        
        return jsonify({
            "success": True,
            "message": "Camera stopped successfully",
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/camera/status', methods=['GET'])
def get_camera_status():
    """Get camera status"""
    try:
        global camera_manager, camera_active
        
        return jsonify({
            "success": True,
            "data": {
                "camera_active": camera_active,
                "is_initialized": camera_manager.is_initialized,
                "camera_available": camera_manager.cap is not None if camera_manager.cap else False
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/camera/test', methods=['POST'])
def test_camera():
    """Test camera capture - returns a single frame as base64"""
    try:
        global camera_manager, camera_active
        
        # Initialize camera if not already done
        if not camera_manager.is_initialized:
            if not camera_manager.initialize_camera():
                return jsonify({
                    "success": False,
                    "error": "Failed to initialize camera",
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        # Capture a test frame
        frame_data = camera_manager.capture_frame()
        
        if frame_data:
            # Convert to base64 for JSON response
            import base64
            frame_b64 = base64.b64encode(frame_data).decode('utf-8')
            
            return jsonify({
                "success": True,
                "message": "Camera test successful",
                "data": {
                    "frame_size": len(frame_data),
                    "frame_base64": frame_b64
                },
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to capture test frame",
                "timestamp": datetime.now().isoformat()
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/video_feed')
def video_feed():
    """MJPEG video streaming endpoint using Raspberry Pi camera"""
    def generate_frames():
        global camera_manager, camera_active
        
        # Initialize camera on first request if not already done
        if not camera_manager.is_initialized:
            print("🎥 Initializing Raspberry Pi camera for video feed...")
            if camera_manager.initialize_camera():
                camera_active = True
                print("✅ Camera initialized successfully for streaming")
            else:
                print("❌ Failed to initialize camera for streaming")
                camera_active = False
        
        frame_count = 0
        while True:
            try:
                frame_count += 1
            
                if camera_active and camera_manager.is_initialized:
                    # Capture frame from Pi camera
                    frame_data = camera_manager.capture_frame()
                    
                    if frame_data:
                        # Send the actual camera frame with Safari-compatible headers
                        frame_response = b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ' + str(len(frame_data)).encode() + b'\r\n\r\n' + frame_data + b'\r\n'
                        if frame_count % 100 == 0:  # Log every 100 frames
                            print(f"📹 Streaming frame {frame_count}")
                    else:
                        # Camera error, send placeholder
                        print("⚠️ Camera capture failed, sending placeholder")
                        placeholder_data = create_placeholder_frame("Camera Error", "Failed to capture frame")
                        if placeholder_data:
                            frame_response = b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ' + str(len(placeholder_data)).encode() + b'\r\n\r\n' + placeholder_data + b'\r\n'
                        else:
                            # Fallback: send a simple black frame
                            black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                            _, buffer = cv2.imencode('.jpg', black_frame)
                            frame_response = b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ' + str(len(buffer)).encode() + b'\r\n\r\n' + buffer.tobytes() + b'\r\n'
                else:
                    # Camera not active, send placeholder
                    placeholder_data = create_placeholder_frame("Camera Inactive", "Use /api/camera/start to activate")
                    if placeholder_data:
                        frame_response = b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ' + str(len(placeholder_data)).encode() + b'\r\n\r\n' + placeholder_data + b'\r\n'
                    else:
                        # Fallback: send a simple black frame
                        black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                        _, buffer = cv2.imencode('.jpg', black_frame)
                        frame_response = b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: ' + str(len(buffer)).encode() + b'\r\n\r\n' + buffer.tobytes() + b'\r\n'
                
                yield frame_response
                time.sleep(0.033)  # ~30 FPS for better Safari compatibility
                
            except Exception as e:
                print(f"❌ Error in video streaming: {e}")
                # Send error placeholder
                placeholder_data = create_placeholder_frame("Streaming Error", f"Error: {str(e)[:50]}...")
                if placeholder_data:
                    frame_response = b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + placeholder_data + b'\r\n'
                    yield frame_response
                time.sleep(1)  # Wait longer on error
    
    return Response(
        generate_frames(), 
        mimetype='multipart/x-mixed-replace; boundary=frame',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'  # Disable nginx buffering
        }
    )

@app.route('/h264_stream')
def h264_stream():
    """H.264 streaming endpoint for ultra-low latency"""
    try:
        # Check if rpicam-vid is available
        import subprocess
        result = subprocess.run(['which', 'rpicam-vid'], capture_output=True, text=True)
        if result.returncode != 0:
            return jsonify({
                "success": False,
                "error": "rpicam-vid not available. Install with: sudo apt install rpicam-apps"
            }), 500
        
        # Start H.264 streaming process at MAXIMUM resolution!
        cmd = [
            'rpicam-vid',
            '--width', '1456',
            '--height', '1088', 
            '--framerate', '30',
            '--bitrate', '8000000',  # Higher bitrate for max resolution
            '--codec', 'h264',
            '--inline',
            '--timeout', '0',
            '--output', '-',
            '--awb', 'auto',
            '--hflip', '--vflip'  # Flip both to rotate 180 degrees
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0
        )
        
        def generate_h264():
            try:
                while True:
                    chunk = process.stdout.read(4096)
                    if not chunk:
                        break
                    yield chunk
            except Exception as e:
                print(f"❌ H.264 streaming error: {e}")
            finally:
                process.terminate()
        
        return Response(
            generate_h264(),
            mimetype='video/mp4',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Content-Type': 'video/mp4'
            }
        )
        
    except Exception as e:
        print(f"❌ H.264 stream error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/camera/wb', methods=['POST'])
def set_white_balance():
    """Set manual white balance gains (live update)"""
    try:
        data = request.get_json()
        red_gain = float(data.get('red', 1.8))
        blue_gain = float(data.get('blue', 1.0))

        if camera_manager.camera and camera_manager.camera_type == 'picamera2':
            camera_manager.camera.set_controls({
                "AwbEnable": False,  # Disable auto white balance
                "ColourGains": (red_gain, blue_gain)
            })

            print(f"🎨 Updated ColourGains → R={red_gain:.2f}, B={blue_gain:.2f}")

            return jsonify({
                "success": True,
                "message": f"White balance updated (R={red_gain}, B={blue_gain})"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Camera not available or not PiCamera2"
            }), 500

    except Exception as e:
        print(f"❌ White balance update error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/camera/wb/reset', methods=['POST'])
def reset_white_balance():
    """Reset to auto white balance"""
    try:
        if camera_manager.camera and camera_manager.camera_type == 'picamera2':
            camera_manager.camera.set_controls({
                "AwbEnable": True,  # Enable auto white balance
                "AwbMode": 2
            })

            print("🎨 Reset to auto white balance")

            return jsonify({
                "success": True,
                "message": "White balance reset to auto"
            })
        else:
            return jsonify({
                "success": False,
                "error": "Camera not available or not PiCamera2"
            }), 500

    except Exception as e:
        print(f"❌ White balance reset error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

# Add a function to print PandaCam message after startup
def print_pandacam_ready():
    import threading
    import time
    
    def delayed_message():
        time.sleep(2)  # Wait for debugger to be active
        print("🐼 PandaCam initialization finished")
    
    threading.Thread(target=delayed_message, daemon=True).start()

if __name__ == '__main__':
    # Only print startup info if we're not in a reloaded process
    import os
    if os.environ.get('WERKZEUG_RUN_MAIN') != 'true':
        print("🚀 Starting 3D Printer Monitoring System with AI-Powered Failure Detection")
        print("📹 Camera will auto-initialize on first video feed request")
        print("🤖 AI monitoring powered by Google Gemini Vision API")
        print("🌐 Server will be available at http://0.0.0.0:8000")
        print("📺 Video feed available at http://0.0.0.0:8000/video_feed")
        print("🔧 Camera controls: /api/camera/start, /api/camera/stop, /api/camera/status")
        print("🧠 AI controls: /api/ai/start, /api/ai/stop, /api/ai/status")
        print("⚡ AI analyzes frames every 15 seconds for print failure detection (0.067 Hz)")
        
        # Schedule PandaCam message after debugger is active
        print_pandacam_ready()
    
    # Run on all interfaces so it can be accessed from other devices
    app.run(host='0.0.0.0', port=8000, debug=True)
