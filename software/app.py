from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import os
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Configuration
app.config['JSON_SORT_KEYS'] = False

# Sample data structure - this will be replaced with actual data from your Raspberry Pi app
sample_data = {
    "status": "running",
    "timestamp": datetime.now().isoformat(),
    "sensors": {
        "temperature": 25.5,
        "humidity": 60.2,
        "pressure": 1013.25
    },
    "system_info": {
        "cpu_usage": 45.2,
        "memory_usage": 67.8,
        "disk_usage": 23.1
    }
}

@app.route('/')
def home():
    """Health check endpoint"""
    return jsonify({
        "message": "Flask backend is running",
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/data', methods=['GET'])
def get_data():
    """Get current data from the Raspberry Pi app"""
    try:
        # In the future, this will fetch data from your Raspberry Pi app
        # For now, return sample data
        return jsonify({
            "success": True,
            "data": sample_data,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system status"""
    return jsonify({
        "success": True,
        "status": "online",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/update', methods=['POST'])
def update_data():
    """Update data from external Raspberry Pi app"""
    try:
        data = request.get_json()
        if data:
            # In the future, this will process data from your Raspberry Pi app
            global sample_data
            sample_data.update(data)
            return jsonify({
                "success": True,
                "message": "Data updated successfully",
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
            "error": str(e)
        }), 500

if __name__ == '__main__':
    # Run on all interfaces so it can be accessed from other devices
    app.run(host='0.0.0.0', port=8000, debug=True)
