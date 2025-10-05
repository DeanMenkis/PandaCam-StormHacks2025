from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import json
import os
import subprocess
import threading
import time
import base64
from datetime import datetime
import numpy as np
import cv2
import requests
import re
try:
    from picamera import PiCamera
    PICAMERA_AVAILABLE = True
    print("✅ Legacy PiCamera library available")
except (ImportError, OSError) as e:
    PICAMERA_AVAILABLE = False
    print(f"❌ Legacy PiCamera library not available: {e}")

try:
    # Try to import from system packages first
    import sys
    sys.path.insert(0, '/usr/lib/python3/dist-packages')
    from picamera2 import Picamera2
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
    "ai_response": None,  # Latest AI analysis response
    "ai_confidence": 0.0,  # AI confidence level (0.5-1.0)
    "last_ai_analysis": None,  # Timestamp of last AI analysis
    "timestamp": datetime.now().isoformat()
}

# Camera instance
camera = None
camera_active = False
frame_lock = threading.Lock()

# AI Monitoring configuration and state
GEMINI_API_KEY = "AIzaSyBHIiKiXJNKW6Ot5ZuFT1S2CiajIyvRP_c"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
AI_MONITORING_INTERVAL = 10  # seconds

# AI monitoring thread control
ai_monitoring_thread = None
ai_monitoring_active = False
ai_monitoring_lock = threading.Lock()

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
            
            # Create a more compatible configuration
            config = self.camera.create_video_configuration(
                main={"size": (640, 480), "format": "RGB888"},
                controls={"FrameRate": 15}
            )
            self.camera.configure(config)
            self.camera.start()
            
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
        """Try to initialize using OpenCV"""
        try:
            print("📹 Trying OpenCV VideoCapture...")
            
            for camera_index in [0, 1, 2]:
                print(f"   Testing camera index {camera_index}...")
                self.cap = cv2.VideoCapture(camera_index)
                
                if self.cap.isOpened():
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                    self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    
                    time.sleep(2)
                    
                    # Test capture
                    ret, frame = self.cap.read()
                    if ret and frame is not None and frame.size > 0:
                        self.is_initialized = True
                        self.camera_type = 'opencv'
                        print(f"✅ OpenCV camera initialized on index {camera_index}!")
                        return True
                    
                    self.cap.release()
                    self.cap = None
            
            print("❌ OpenCV failed on all camera indices")
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
        """Capture frame using PiCamera2"""
        try:
            frame = self.camera.capture_array()
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            _, buffer = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return buffer.tobytes()
        except Exception as e:
            print(f"PiCamera2 capture error: {e}")
            return None
    
    def _capture_opencv(self):
        """Capture frame using OpenCV"""
        try:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                if frame.shape[:2] != (480, 640):
                    frame = cv2.resize(frame, (640, 480))
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                return buffer.tobytes()
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
        self.prompt = """You are an expert 3D printing technician analyzing a camera feed. Look at this image and provide a clear, friendly analysis.

🔍 WHAT TO LOOK FOR:
• Is there a 3D printer visible in the image?
• If yes: How does the print quality look? Any issues?
• If no: What do you actually see instead?

📝 RESPONSE FORMAT:
Write a natural, conversational response. Start with one of these:
• '✅ PRINT LOOKS GOOD: [explain why]'
• '⚠️ POTENTIAL ISSUE: [describe the problem]'
• '❌ PRINT FAILURE: [explain what went wrong]'
• '🤷 NO PRINTER VISIBLE: [describe what you see instead]'

Be helpful and specific. If you see a problem, suggest what might be causing it. Keep it under 3 sentences and use a friendly tone."""
    
    def analyze_frame(self, frame_data):
        """
        Analyze a frame using Gemini Vision API
        
        Args:
            frame_data: JPEG image data as bytes
            
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
                timeout=30
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
                        
                        return {
                            'success': True,
                            'response_text': response_text,
                            'print_status': parsed['print_status'],
                            'confidence': parsed['confidence'],
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
            return {
                'success': False,
                'response_text': None,
                'print_status': 'idle',
                'confidence': 0.5,
                'error': error_msg
            }
        except requests.exceptions.RequestException as e:
            error_msg = f'Gemini API request failed: {str(e)}'
            print(f"🌐 {error_msg}")
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

# Initialize AI analyzer
ai_analyzer = GeminiAIAnalyzer(GEMINI_API_KEY, GEMINI_API_URL)

def ai_monitoring_worker():
    """
    AI monitoring worker thread that captures frames every 10 seconds
    and analyzes them using Gemini Vision API
    """
    global ai_monitoring_active, printer_state, camera_manager, ai_analyzer
    
    print("🤖 AI monitoring thread started")
    
    while ai_monitoring_active:
        try:
            # Ensure camera is initialized
            if not camera_manager.is_initialized:
                print("📹 AI monitoring: Initializing camera...")
                if not camera_manager.initialize_camera():
                    print("❌ AI monitoring: Failed to initialize camera, retrying in 10 seconds")
                    time.sleep(AI_MONITORING_INTERVAL)
                    continue
            
            # Capture frame
            print(f"📸 AI monitoring: Attempting to capture frame at {datetime.now().strftime('%H:%M:%S')}")
            frame_data = camera_manager.capture_frame()
            
            if frame_data:
                print(f"✅ Frame captured successfully, size: {len(frame_data)} bytes")
                print(f"🤖 AI monitoring: Analyzing frame at {datetime.now().strftime('%H:%M:%S')}")
                
                # Analyze frame with Gemini
                analysis_result = ai_analyzer.analyze_frame(frame_data)
                
                # Update printer state with thread safety
                with ai_monitoring_lock:
                    if analysis_result['success']:
                        # Update state based on AI analysis
                        printer_state["ai_response"] = analysis_result['response_text']
                        printer_state["ai_confidence"] = analysis_result['confidence']
                        printer_state["print_status"] = analysis_result['print_status']
                        printer_state["last_ai_analysis"] = datetime.now().isoformat()
                        
                        # Handle failure detection
                        if analysis_result['print_status'] == 'failed':
                            printer_state["failure_detected"] = True
                            printer_state["last_failure_time"] = datetime.now().isoformat()
                            print(f"🚨 AI DETECTED PRINT FAILURE: {analysis_result['response_text']}")
                        else:
                            # Reset failure if status is good
                            if analysis_result['print_status'] == 'printing':
                                printer_state["failure_detected"] = False
                        
                        # Log AI response
                        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        print(f"🤖 [{timestamp}] AI Analysis: {analysis_result['response_text']}")
                        print(f"   Status: {analysis_result['print_status']} | Confidence: {analysis_result['confidence']}")
                        
                    else:
                        # Handle analysis error
                        printer_state["ai_response"] = f"Analysis error: {analysis_result['error']}"
                        printer_state["ai_confidence"] = 0.5
                        printer_state["last_ai_analysis"] = datetime.now().isoformat()
                        print(f"❌ AI analysis error: {analysis_result['error']}")
                    
                    printer_state["timestamp"] = datetime.now().isoformat()
            else:
                print("⚠️ AI monitoring: Failed to capture frame")
                with ai_monitoring_lock:
                    printer_state["ai_response"] = "Failed to capture camera frame"
                    printer_state["ai_confidence"] = 0.5
                    printer_state["last_ai_analysis"] = datetime.now().isoformat()
                    printer_state["timestamp"] = datetime.now().isoformat()
            
            # Wait for next analysis cycle
            time.sleep(AI_MONITORING_INTERVAL)
            
        except Exception as e:
            print(f"❌ AI monitoring thread error: {e}")
            with ai_monitoring_lock:
                printer_state["ai_response"] = f"Monitoring error: {str(e)}"
                printer_state["ai_confidence"] = 0.5
                printer_state["last_ai_analysis"] = datetime.now().isoformat()
                printer_state["timestamp"] = datetime.now().isoformat()
            time.sleep(AI_MONITORING_INTERVAL)
    
    print("🤖 AI monitoring thread stopped")

def start_ai_monitoring():
    """Start the AI monitoring thread"""
    global ai_monitoring_thread, ai_monitoring_active, printer_state
    
    with ai_monitoring_lock:
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
    
    with ai_monitoring_lock:
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
        printer_state["timestamp"] = datetime.now().isoformat()
        
        # Enhanced status with AI insights prominently displayed
        enhanced_state = printer_state.copy()
        
        # Add AI status summary for easy frontend consumption
        if printer_state.get("ai_monitoring_active", False):
            ai_status_emoji = "🤖"
            if printer_state.get("ai_response"):
                if printer_state["ai_response"].startswith("✅"):
                    ai_status_emoji = "✅"
                elif printer_state["ai_response"].startswith("⚠️"):
                    ai_status_emoji = "⚠️"
                elif printer_state["ai_response"].startswith("❌"):
                    ai_status_emoji = "❌"
                elif printer_state["ai_response"].startswith("🤷"):
                    ai_status_emoji = "🤷"
            
            enhanced_state["ai_status_summary"] = {
                "active": True,
                "emoji": ai_status_emoji,
                "status": printer_state.get("print_status", "idle"),
                "confidence": printer_state.get("ai_confidence", 0.0),
                "last_analysis": printer_state.get("last_ai_analysis"),
                "response": printer_state.get("ai_response", "No analysis yet")
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
        printer_state["is_running"] = True
        printer_state["is_monitoring"] = True
        printer_state["failure_detected"] = False
        printer_state["timestamp"] = datetime.now().isoformat()
        
        # Here you would start your actual printer monitoring application
        # For now, we'll just update the state
        
        return jsonify({
            "success": True,
            "message": "Printer monitoring started",
            "data": printer_state,
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
        printer_state["is_running"] = False
        printer_state["is_monitoring"] = False
        printer_state["video_stream_active"] = False
        printer_state["timestamp"] = datetime.now().isoformat()
        
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
        with ai_monitoring_lock:
            ai_status = {
                "ai_monitoring_active": printer_state["ai_monitoring_active"],
                "ai_response": printer_state["ai_response"],
                "ai_confidence": printer_state["ai_confidence"],
                "print_status": printer_state["print_status"],
                "last_ai_analysis": printer_state["last_ai_analysis"],
                "failure_detected": printer_state["failure_detected"],
                "last_failure_time": printer_state["last_failure_time"],
                "monitoring_interval": AI_MONITORING_INTERVAL
            }
        
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
                        # Send the actual camera frame
                        frame_response = b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n'
                        if frame_count % 100 == 0:  # Log every 100 frames
                            print(f"📹 Streaming frame {frame_count}")
                    else:
                        # Camera error, send placeholder
                        print("⚠️ Camera capture failed, sending placeholder")
                        placeholder_data = create_placeholder_frame("Camera Error", "Failed to capture frame")
                        if placeholder_data:
                            frame_response = b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + placeholder_data + b'\r\n'
                        else:
                            # Fallback: send a simple black frame
                            black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                            _, buffer = cv2.imencode('.jpg', black_frame)
                            frame_response = b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'
                else:
                    # Camera not active, send placeholder
                    placeholder_data = create_placeholder_frame("Camera Inactive", "Use /api/camera/start to activate")
                    if placeholder_data:
                        frame_response = b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + placeholder_data + b'\r\n'
                    else:
                        # Fallback: send a simple black frame
                        black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                        _, buffer = cv2.imencode('.jpg', black_frame)
                        frame_response = b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'
                
                yield frame_response
                time.sleep(0.033)  # ~30 FPS for smoother video
                
            except Exception as e:
                print(f"❌ Error in video streaming: {e}")
                # Send error placeholder
                placeholder_data = create_placeholder_frame("Streaming Error", f"Error: {str(e)[:50]}...")
                if placeholder_data:
                    frame_response = b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + placeholder_data + b'\r\n'
                    yield frame_response
                time.sleep(1)  # Wait longer on error
    
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    print("🚀 Starting 3D Printer Monitoring System with AI-Powered Failure Detection")
    print("📹 Camera will auto-initialize on first video feed request")
    print("🤖 AI monitoring powered by Google Gemini Vision API")
    print("🌐 Server will be available at http://0.0.0.0:8000")
    print("📺 Video feed available at http://0.0.0.0:8000/video_feed")
    print("🔧 Camera controls: /api/camera/start, /api/camera/stop, /api/camera/status")
    print("🧠 AI controls: /api/ai/start, /api/ai/stop, /api/ai/status")
    print("⚡ AI analyzes frames every 10 seconds for print failure detection")
    
    # Run on all interfaces so it can be accessed from other devices
    app.run(host='0.0.0.0', port=8000, debug=True)
