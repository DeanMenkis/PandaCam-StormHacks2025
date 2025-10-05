# 3D Printer Monitoring System - Integrated Version

This is the integrated version of the 3D printer monitoring system that combines the Flask backend, React frontend, and AI-powered monitoring service into a cohesive system.

## System Architecture

The system consists of three main components:

1. **Flask Backend** (`app.py`) - API server that handles requests and manages printer state
2. **React Frontend** (`frontend/`) - Web interface for monitoring and control
3. **Monitoring Service** (`monitoring_service.py`) - Background service that captures images, analyzes them with AI, and communicates with the backend

## Features

- **Real-time Video Streaming**: Live camera feed accessible via web interface
- **AI-Powered Print Analysis**: Uses Google Gemini AI to analyze print quality and detect failures
- **Automatic Monitoring**: Configurable interval-based photo capture and analysis
- **Web Dashboard**: Modern React interface for monitoring and control
- **Print Status Detection**: Automatically determines print status (idle, printing, failed, warning)
- **Failure Reporting**: Immediate alerts when print failures are detected

## Setup Instructions

### 1. Install Dependencies

```bash
# Install Python dependencies
cd /home/admin/Desktop/CircuitBreakers-StormHacks-2025/software
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install Node.js dependencies
cd frontend
npm install
cd ..
```

### 2. Configure AI API Key

Set your Google Gemini API key as an environment variable:

```bash
export GEMINI_API_KEY="your_gemini_api_key_here"
```

Or edit the `monitoring_service.py` file and replace the API key directly.

### 3. Start the System

Open 3 separate terminal windows and run these commands:

**Terminal 1 - Flask Backend:**
```bash
cd /home/admin/Desktop/CircuitBreakers-StormHacks-2025/software
source venv/bin/activate
python app.py
```

**Terminal 2 - Monitoring Service:**
```bash
cd /home/admin/Desktop/CircuitBreakers-StormHacks-2025/software
source venv/bin/activate
python monitoring_service.py
```

**Terminal 3 - React Frontend:**
```bash
cd /home/admin/Desktop/CircuitBreakers-StormHacks-2025/software/frontend
npm start
```

## Usage

### Accessing the System

- **Web Interface**: http://localhost:3000 (or http://192.168.4.32:3000 from other devices)
- **API Endpoints**: http://localhost:8000/api/
- **Video Stream**: http://localhost:8000/video_feed

### Using the Web Interface

1. **Start Monitoring**: Click "Start Monitoring" to begin AI-powered print monitoring
2. **View Video Feed**: The live camera feed is displayed in the web interface
3. **Monitor Status**: Watch the print status updates from AI analysis
4. **View AI Analysis**: See detailed AI analysis results in the interface
5. **Stop Monitoring**: Click "Stop Monitoring" to halt the monitoring service

### API Endpoints

- `GET /api/printer/status` - Get current printer status
- `POST /api/printer/start` - Start monitoring
- `POST /api/printer/stop` - Stop monitoring
- `POST /api/printer/print-status` - Update print status (used by monitoring service)
- `POST /api/printer/failure` - Report print failure
- `GET /video_feed` - MJPEG video stream

## AI Analysis

The system uses Google Gemini AI to analyze captured images and determine:

- **Print Status**: idle, printing, failed, warning, unknown
- **Print Quality**: Assessment of print quality and potential issues
- **Failure Detection**: Automatic detection of print failures like spaghetti, warping, etc.

### AI Response Format

The AI provides responses in a structured format:
- ✅ **PRINT LOOKS GOOD**: [explanation]
- ⚠️ **POTENTIAL ISSUE**: [problem description]
- ❌ **PRINT FAILURE**: [failure details]
- 🤷 **NO PRINTER VISIBLE**: [what's visible instead]

## Configuration

### Monitoring Service Configuration

Edit `monitoring_service.py` to adjust:

- **Capture Interval**: How often to take photos (default: 30 seconds)
- **Camera Settings**: Resolution, quality, etc.
- **AI Settings**: Prompt, temperature, token limits

### AI Configuration

The AI analysis can be customized by modifying the prompt in `monitoring_service.py`:

```python
AI_CONFIG = {
    "gemini_settings": {
        "prompt": "Your custom prompt here...",
        "temperature": 0.3,
        "max_output_tokens": 1024,
        # ... other settings
    }
}
```

## Troubleshooting

### Common Issues

1. **Camera Not Found**: Make sure the camera is connected and not being used by another application
2. **AI Analysis Fails**: Check your Gemini API key and internet connection
3. **Video Stream Not Working**: Ensure the monitoring service is running and camera is active
4. **Port Conflicts**: Make sure ports 3000 and 8000 are not being used by other applications

### Logs

- **Monitoring Service**: Check `monitoring_service.log` for detailed logs
- **Flask Backend**: Check console output for API logs
- **React Frontend**: Check browser console for frontend errors

### Manual Testing

```bash
# Test camera capture
python3 -c "
import subprocess
result = subprocess.run(['rpicam-jpeg', '--nopreview', '--immediate', '--timeout', '1', '-o', 'test.jpg'])
print('Camera test:', 'SUCCESS' if result.returncode == 0 else 'FAILED')
"

# Test AI API
curl -X POST "http://localhost:8000/api/printer/status"
```

## File Structure

```
software/
├── app.py                    # Flask backend server
├── monitoring_service.py     # AI monitoring service
├── start_system.py          # System startup script
├── requirements.txt         # Python dependencies
├── frontend/                # React frontend
│   ├── src/
│   ├── package.json
│   └── ...
└── README_INTEGRATED_SYSTEM.md
```

## Development

### Adding New Features

1. **Backend API**: Add new endpoints in `app.py`
2. **Frontend UI**: Modify React components in `frontend/src/`
3. **AI Analysis**: Customize prompts and analysis logic in `monitoring_service.py`

### Testing

```bash
# Test individual components
python3 app.py                    # Test backend
python3 monitoring_service.py     # Test monitoring service
cd frontend && npm start          # Test frontend
```

## Support

For issues or questions:
1. Check the logs for error messages
2. Verify all dependencies are installed
3. Ensure camera and API key are properly configured
4. Test individual components separately

---

**Circuit Breakers StormHacks 2025** - 3D Printer Monitoring System
