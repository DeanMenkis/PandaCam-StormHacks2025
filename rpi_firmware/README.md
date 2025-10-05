# 3D Printer Watchdog

A Raspberry Pi desktop application that monitors 3D prints using AI-powered image analysis to detect potential failures in real-time.

## Features

- **Camera Integration**: Uses Raspberry Pi camera with `rpicam-jpeg`
- **AI-Powered Detection**: Hugging Face API analyzes images for print failures
- **Automatic Monitoring**: Configurable capture intervals (5-60 seconds)
- **Real-time UI**: Live camera feed display with status updates
- **Comprehensive Logging**: All activity logged to file and displayed in UI
- **Threading**: Non-blocking background operations

## Setup

### 1. Hardware Requirements
- Raspberry Pi with camera module
- Raspberry Pi OS (Bookworm)

### 2. Enable Camera
```bash
sudo raspi-config
# Navigate to: Interfacing Options > Camera > Enable
```

### 3. Install Dependencies
```bash
pip3 install -r requirements.txt
```

### 4. Get Hugging Face API Token
1. Go to [Hugging Face](https://huggingface.co/)
2. Create account and get API token from settings
3. Edit `watchdog_app.py` and replace `YOUR_HUGGING_FACE_TOKEN_HERE` with your token

### 5. Run the Application
```bash
python3 watchdog_app.py
```

## Usage

1. **Position Camera**: Point the camera at your 3D printer bed
2. **Manual Capture**: Click "Take Photo" to test camera and AI
3. **Set Interval**: Use the slider to set capture frequency (5-60 seconds)
4. **Start Monitoring**: Click "Start Monitoring" to begin automatic detection
5. **Monitor Results**: Watch the log for AI analysis and status updates

## AI Detection

The app uses `Salesforce/blip-image-captioning-large` model to analyze images. It looks for keywords indicating print failures:
- spaghetti, mess, error, failed, failure
- detached, warped, melted, broken, collapsed
- stringing, blobs, poor quality indicators

## Files

- `watchdog_app.py`: Main application
- `watchdog_log.txt`: Activity log (auto-created)
- `capture.jpg`: Latest camera capture (temporary)
- `requirements.txt`: Python dependencies

## Extending the App

The code is well-commented for easy extension:
- Add Discord webhooks for alerts
- Implement different AI models
- Add email notifications
- Create custom failure detection logic
- Add historical trend analysis

## Troubleshooting

- **Camera not working**: Ensure camera is enabled in raspi-config
- **AI API errors**: Check your Hugging Face token and internet connection
- **Import errors**: Install requirements with `pip3 install -r requirements.txt`
- **Permission errors**: Run with appropriate permissions for camera access
