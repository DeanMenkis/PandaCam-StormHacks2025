# Camera Test Script

This folder contains a test script to simulate the Raspberry Pi camera functionality using your laptop's built-in camera.

## Setup

1. **Install dependencies:**
   ```bash
   cd /Users/ilia/Desktop/Projects/CircuitBreakers-StormHacks-2025/software
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Start the Flask server:**
   ```bash
   python app.py
   ```

3. **Start the React frontend (in a new terminal):**
   ```bash
   cd frontend
   npm start
   ```

4. **Run the camera test script (in a new terminal):**
   ```bash
   cd /Users/ilia/Desktop/Projects/CircuitBreakers-StormHacks-2025/software
   source venv/bin/activate
   python test/camera_test.py
   ```

## How it works

- The `camera_test.py` script captures frames from your laptop camera
- It writes frames to **shared memory** for ultra-fast local communication
- The Flask server reads frames from shared memory and serves them via MJPEG stream
- The React frontend displays the live video feed
- **No network overhead** - everything runs locally on the same machine

## Features

- **Real-time streaming**: 10 FPS video feed
- **Shared memory communication**: Ultra-fast local data transfer
- **Error handling**: Graceful handling of camera and memory errors
- **Status updates**: Reports camera status via file system
- **Zero network overhead**: No HTTP requests between local processes

## Communication Method

- **Shared Memory**: Camera frames are written to shared memory (`camera_frame`)
- **Status File**: Camera status is written to `/tmp/camera_status.json`
- **Thread-safe**: Uses locks to prevent data corruption
- **Efficient**: Direct memory access instead of network requests

## Troubleshooting

- **Camera not found**: Make sure no other application is using your camera
- **Shared memory failed**: Ensure proper permissions for shared memory creation
- **Permission denied**: Grant camera permissions to your terminal/IDE
- **Memory errors**: Restart both the Flask server and camera test script

## Future Integration

This test script will be replaced with the actual Raspberry Pi camera code that will:
- Use the Pi Camera module
- Run directly on the Raspberry Pi
- Use the same shared memory communication method
- Include print failure detection logic
