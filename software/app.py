from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import json
import os
import subprocess
import threading
import time
import base64
from datetime import datetime
import multiprocessing as mp
from multiprocessing import shared_memory
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

# Video streaming process (will be set when streaming starts)
video_process = None

# Camera frame storage
current_frame = None
camera_active = False
frame_lock = threading.Lock()
shared_memory_handle = None

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
        
        # Stop video streaming if active
        if video_process:
            try:
                video_process.terminate()
                video_process = None
            except:
                pass
        
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

def read_frame_from_shared_memory():
    """Read frame data from shared memory"""
    global current_frame, camera_active, shared_memory_handle
    
    try:
        # Try to connect to existing shared memory
        if shared_memory_handle is None:
            try:
                shared_memory_handle = shared_memory.SharedMemory(name="camera_frame")
                print("✓ Connected to shared memory 'camera_frame'")
            except FileNotFoundError:
                print("✗ Shared memory 'camera_frame' not found")
                return None
        
        # Read frame data from shared memory
        frame_bytes = bytes(shared_memory_handle.buf)
        
        # Check if we have valid data (not all zeros)
        if len(frame_bytes) == 0 or all(b == 0 for b in frame_bytes[:100]):
            print("⚠ Shared memory contains no data or all zeros")
            return None
        
        # Convert bytes back to numpy array
        frame_array = np.frombuffer(frame_bytes, dtype=np.uint8)
        
        # Calculate the expected size for 640x480x3
        expected_size = 640 * 480 * 3
        
        # Check if we have the right amount of data
        if len(frame_array) != expected_size:
            print(f"⚠ Frame size mismatch: got {len(frame_array)} bytes, expected {expected_size}")
            # Try to handle different sizes by truncating or padding
            if len(frame_array) > expected_size:
                frame_array = frame_array[:expected_size]
                print(f"Truncated to {len(frame_array)} bytes")
            else:
                # Pad with zeros if too small
                padded_array = np.zeros(expected_size, dtype=np.uint8)
                padded_array[:len(frame_array)] = frame_array
                frame_array = padded_array
                print(f"Padded to {len(frame_array)} bytes")
        
        # Reshape to image dimensions
        frame_rgb = frame_array.reshape((480, 640, 3))
        
        # Convert RGB to BGR for OpenCV
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        
        # Encode as JPEG
        _, buffer = cv2.imencode('.jpg', frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 80])
        
        return buffer.tobytes()
        
    except Exception as e:
        print(f"Error reading from shared memory: {e}")
        return None

def read_camera_status():
    """Read camera status from status file"""
    global camera_active
    
    try:
        if os.path.exists("/tmp/camera_status.json"):
            with open("/tmp/camera_status.json", "r") as f:
                status_data = json.load(f)
                camera_active = status_data.get("camera_active", False)
                frame_count = status_data.get("frame_count", 0)
                print(f"📊 Camera status: {'Active' if camera_active else 'Inactive'}, Frames: {frame_count}")
                return True
        else:
            print("📁 Camera status file not found")
    except Exception as e:
        print(f"Error reading camera status: {e}")
    
    return False

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
            # Read camera status
            read_camera_status()
            
            # Try to read frame from shared memory
            frame_data = read_frame_from_shared_memory()
            
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

if __name__ == '__main__':
    # Run on all interfaces so it can be accessed from other devices
    app.run(host='0.0.0.0', port=8000, debug=True)
