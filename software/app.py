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
import requests

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
    "print_status": "idle",  # idle, printing, paused, completed, failed, warning, unknown
    "print_progress": 0,  # 0-100
    "print_time_elapsed": 0,  # in minutes
    "print_time_remaining": 0,  # in minutes
    "ai_analysis": None,  # Latest AI analysis result
    "last_ai_analysis_time": None,
    "timestamp": datetime.now().isoformat()
}

# Monitoring service configuration
MONITORING_SERVICE_URL = "http://127.0.0.1:8001"  # If running as separate service

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
        
        # Start the monitoring service
        try:
            # Try to start monitoring service via subprocess
            subprocess.Popen([
                "python3", 
                "/home/admin/Desktop/CircuitBreakers-StormHacks-2025/software/monitoring_service.py"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            # Give it a moment to start
            time.sleep(2)
            
            # Try to communicate with monitoring service to start AI monitoring
            try:
                response = requests.post(f"{MONITORING_SERVICE_URL}/start-ai-monitoring", timeout=5)
                if response.status_code == 200:
                    print("AI monitoring started successfully")
                else:
                    print("Warning: Could not start AI monitoring via API")
            except:
                print("Warning: Monitoring service API not available, but service may still be running")
                
        except Exception as e:
            print(f"Warning: Could not start monitoring service: {e}")
        
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
        
        # Stop the monitoring service
        try:
            # Try to stop AI monitoring via API
            response = requests.post(f"{MONITORING_SERVICE_URL}/stop-ai-monitoring", timeout=5)
            if response.status_code == 200:
                print("AI monitoring stopped successfully")
            else:
                print("Warning: Could not stop AI monitoring via API")
        except:
            print("Warning: Monitoring service API not available")
        
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
            if "ai_analysis" in data:
                printer_state["ai_analysis"] = data["ai_analysis"]
                printer_state["last_ai_analysis_time"] = datetime.now().isoformat()
            
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
    """Read frame data from file (simplified approach)"""
    global current_frame, camera_active
    
    try:
        # Read the latest frame from file
        frame_file = "/tmp/latest_frame.jpg"
        
        if os.path.exists(frame_file):
            with open(frame_file, "rb") as f:
                frame_data = f.read()
            
            if len(frame_data) > 0:
                return frame_data
            else:
                return None
        else:
            return None
        
    except Exception as e:
        print(f"Error reading frame from file: {e}")
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
        cv2.putText(placeholder, "AI Monitoring Active", (120, 200), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(placeholder, "Video streaming not available", (80, 250), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
        cv2.putText(placeholder, "Photos captured every 30s", (100, 300), 
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
