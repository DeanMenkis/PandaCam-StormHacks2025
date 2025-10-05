from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import json
import os
import subprocess
import threading
import time
from datetime import datetime

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
    "timestamp": datetime.now().isoformat()
}

# Video streaming process (will be set when streaming starts)
video_process = None

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

@app.route('/video_feed')
def video_feed():
    """MJPEG video streaming endpoint"""
    def generate_frames():
        global video_process
        
        # For now, we'll create a placeholder video stream
        # In production, this would connect to your camera capture application
        while True:
            # Placeholder: In real implementation, this would read from your camera
            # For now, we'll just send a simple frame
            frame_data = b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + b'placeholder_frame_data' + b'\r\n'
            yield frame_data
            time.sleep(0.1)  # 10 FPS
    
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # Run on all interfaces so it can be accessed from other devices
    app.run(host='0.0.0.0', port=8000, debug=True)
