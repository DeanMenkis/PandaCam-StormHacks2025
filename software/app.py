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
    "timestamp": datetime.now().isoformat()
}

# Camera management
camera = None
camera_active = False
frame_lock = threading.Lock()
current_frame = None
camera_thread = None

def find_available_cameras():
    """Find all available cameras"""
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
                print(f"📹 Camera {i}: {width}x{height} @ {fps}fps")
            cap.release()
    
    return available_cameras

def initialize_camera():
    """Initialize the camera"""
    global camera, camera_active
    
    try:
        # Find available cameras
        available_cameras = find_available_cameras()
        
        if not available_cameras:
            print("❌ No cameras found!")
            return False
        
        # Try to use the first available camera
        camera_index = available_cameras[0]['index']
        print(f"🎥 Initializing camera {camera_index}...")
        
        camera = cv2.VideoCapture(camera_index)
        
        if not camera.isOpened():
            print(f"❌ Failed to open camera {camera_index}")
            return False
        
        # Set camera properties
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        camera.set(cv2.CAP_PROP_FPS, 30)
        
        # Test camera
        ret, test_frame = camera.read()
        if not ret or test_frame is None:
            print("❌ Camera opened but can't read frames")
            camera.release()
            camera = None
            return False
        
        camera_active = True
        print(f"✅ Camera {camera_index} initialized successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error initializing camera: {e}")
        return False

def camera_capture_loop():
    """Background thread to continuously capture frames"""
    global current_frame, camera_active, camera
    
    print("🎬 Starting camera capture loop...")
    
    while camera_active and camera is not None:
        try:
            if camera.isOpened():
                ret, frame = camera.read()
                if ret and frame is not None:
                    # Resize frame for better performance
                    frame = cv2.resize(frame, (640, 480))
                    
                    with frame_lock:
                        current_frame = frame.copy()
                else:
                    print("⚠️ Failed to capture frame")
                    time.sleep(0.1)
            else:
                print("⚠️ Camera not opened")
                time.sleep(0.1)
                
        except Exception as e:
            print(f"❌ Error in camera capture loop: {e}")
            time.sleep(0.1)
    
    print("🛑 Camera capture loop stopped")

def start_camera_stream():
    """Start the camera streaming"""
    global camera_thread, camera_active
    
    if camera_active:
        print("📹 Camera already active")
        return True
    
    if not initialize_camera():
        return False
    
    # Start camera capture thread
    camera_thread = threading.Thread(target=camera_capture_loop, daemon=True)
    camera_thread.start()
    
    # Update printer state
    printer_state["video_stream_active"] = True
    
    print("✅ Camera stream started")
    return True

def stop_camera_stream():
    """Stop the camera streaming"""
    global camera, camera_active, camera_thread, current_frame
    
    print("🛑 Stopping camera stream...")
    
    camera_active = False
    
    if camera_thread and camera_thread.is_alive():
        camera_thread.join(timeout=2)
    
    if camera:
        camera.release()
        camera = None
    
    with frame_lock:
        current_frame = None
    
    # Update printer state
    printer_state["video_stream_active"] = False
    
    print("✅ Camera stream stopped")

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
        return jsonify({
            "success": True,
            "data": printer_state,
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
        
        # Start camera stream
        if start_camera_stream():
            printer_state["video_stream_active"] = True
        else:
            printer_state["video_stream_active"] = False
        
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
        global printer_state
        printer_state["is_running"] = False
        printer_state["is_monitoring"] = False
        printer_state["timestamp"] = datetime.now().isoformat()
        
        # Stop camera stream
        stop_camera_stream()
        
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

def get_current_frame():
    """Get the current frame from camera"""
    global current_frame, camera_active
    
    if not camera_active or current_frame is None:
        return None
    
    try:
        with frame_lock:
            if current_frame is not None:
                # Encode frame as JPEG
                _, buffer = cv2.imencode('.jpg', current_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                return buffer.tobytes()
    except Exception as e:
        print(f"Error encoding frame: {e}")
    
    return None

def create_placeholder_frame():
    """Create a placeholder frame when no camera is active"""
    try:
        # Create a black frame with text
        placeholder = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add text to the placeholder
        cv2.putText(placeholder, "Camera Not Active", (150, 200), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(placeholder, "Waiting for camera...", (120, 250), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
        
        # Encode as JPEG
        _, buffer = cv2.imencode('.jpg', placeholder, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return buffer.tobytes()
    except Exception as e:
        print(f"Error creating placeholder frame: {e}")
        return None

@app.route('/video_feed')
def video_feed():
    """MJPEG video streaming endpoint"""
    def generate_frames():
        global current_frame, camera_active
        
        while True:
            # Get current frame from camera
            frame_data = get_current_frame()
            
            if frame_data and camera_active:
                # Send the actual camera frame
                frame_response = b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + frame_data + b'\r\n'
            else:
                # Send placeholder frame when no camera is active
                placeholder_data = create_placeholder_frame()
                if placeholder_data:
                    frame_response = b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + placeholder_data + b'\r\n'
                else:
                    # Fallback: send a simple black frame
                    black_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    _, buffer = cv2.imencode('.jpg', black_frame)
                    frame_response = b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'
            
            yield frame_response
            time.sleep(0.1)  # 10 FPS
    
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def cleanup_on_exit():
    """Cleanup function to properly close camera on exit"""
    print("🧹 Cleaning up on exit...")
    stop_camera_stream()

if __name__ == '__main__':
    import atexit
    atexit.register(cleanup_on_exit)
    
    print("🚀 Starting 3D Printer Monitoring System...")
    print("📹 Camera will be initialized when monitoring starts")
    print("🌐 Server running on http://0.0.0.0:8000")
    
    # Run on all interfaces so it can be accessed from other devices
    app.run(host='0.0.0.0', port=8000, debug=True)
