# Modern 3D Printer Watchdog - PyQt5/PySide6 Edition

⚡ **Circuit Breakers StormHacks 2025 — 3D Printer Watchdog (AI Print Monitor)**

A complete redesign of the 3D Printer Watchdog application featuring a modern, professional dark-themed dashboard UI built with PyQt5/PySide6.

## ✨ Features

### 🎨 Modern UI Design
- **Dark-themed dashboard** with professional StormHacks branding
- **Gradient accent header** with teal/purple neon glow effect
- **Rounded, bordered containers** with glowing dividers
- **Color-coded gradient buttons** with hover animations and subtle shadows
- **Console-style AI analysis area** with timestamped, colored status lines
- **Animated status indicator light** (green/yellow/red) beside AI Analysis label
- **Smooth fade-in transitions** when images update

### 📱 Dashboard Layout
- **Left Panel**: Live camera preview in a rounded, bordered frame
- **Right Panel**: Vertical control panel with buttons, AI logs, and status indicators
- **Top Banner**: Professional header with StormHacks branding and lightning icon
- **Bottom Bar**: Real-time status updates with icons

### 🤖 AI Integration
- **Google Gemini AI** analysis with configurable prompts
- **Real-time feedback** displayed in console format
- **Status indicators**: 🟢 Success, 🔴 Error, 🟡 Analyzing
- **Configurable settings** via `ai_config.json`

### 📷 Camera Features
- **Live preview** with smooth 3 FPS updates
- **High-quality capture** (1920x1440) for analysis
- **Automatic monitoring** with configurable intervals (5-60 seconds)
- **Coordinated camera access** to prevent conflicts

## 🚀 Quick Start

### Prerequisites
```bash
# Install PyQt5 (recommended) or PySide6
pip install PyQt5 Pillow requests

# Or PySide6 alternative
pip install PySide6 Pillow requests

# Enable camera on Raspberry Pi
sudo raspi-config  # Enable camera interface
```

### Setup
1. **Get your FREE Gemini API key**: Visit [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)
2. **Update the API key** in `watchdog_app_modern.py`:
   ```python
   GEMINI_API_KEY = "your_api_key_here"
   ```
3. **Customize AI prompts** (optional): Edit `ai_config.json`
4. **Run the application**:
   ```bash
   # Direct execution
   python3 watchdog_app_modern.py

   # Or use the updated launcher script
   ./run_app.sh
   ```

## 🎯 Usage Guide

### Live Preview
- Camera feed starts automatically on launch
- Shows real-time preview at ~3 FPS
- Displays in the left panel with smooth updates

### Manual Analysis
1. Click **"📷 Take Photo & Analyze"** (blue gradient button)
2. Camera captures high-quality image
3. AI analyzes the image using Gemini
4. Results display in console format with timestamps

### Automatic Monitoring
1. Click **"▶️ Start Monitoring"** (green gradient button)
2. Adjust interval slider (5-60 seconds)
3. AI automatically captures and analyzes at intervals
4. Click **"⏹️ Stop"** (red gradient button) to end monitoring

### Configuration
- **"🔄 Reload AI Config"** (orange button): Reload `ai_config.json` without restarting
- Edit `ai_config.json` to customize AI prompts, temperature, and settings

## 🎨 UI Customization

### Color Scheme
- **Primary Background**: `#1a1a1a` (Dark matte)
- **Secondary Panels**: `#2a2a2a` (Card backgrounds)
- **Accent Color**: `#00d4ff` (Teal/cyan glow)
- **Success**: `#14a085` (Green gradients)
- **Warning**: `#fa7268` (Orange gradients)
- **Error**: `#ff6b6b` (Red gradients)

### Typography
- **Primary Font**: Segoe UI, Roboto, or system sans-serif
- **Headers**: Bold, 18-24px
- **Body Text**: Regular, 11-14px
- **Console**: Consolas/Monaco monospace

### Button Styling
- **Gradient backgrounds** with hover effects
- **Rounded corners** (8px radius)
- **Subtle shadows** and borders
- **Color coding**: Blue (analyze), Green (start), Red (stop), Orange (config)

## 🔧 Technical Details

### Architecture
- **PyQt5/PySide6** for modern cross-platform GUI
- **QSS (Qt Style Sheets)** for advanced styling
- **Threading** for camera and AI operations
- **Queue-based communication** between threads
- **Fade animations** using QPropertyAnimation

### File Structure
```
watchdog_app_modern.py    # Main application
ai_config.json            # AI configuration
README_MODERN.md          # This documentation
watchdog_log.txt          # Application logs
capture.jpg              # Latest capture
preview.jpg              # Preview frames
```

### Key Classes
- `ModernPrinterWatchdog`: Main application window
- `CameraCaptureWorker`: Camera capture thread
- `AIAnalysisWorker`: AI analysis thread
- `PreviewWorker`: Live preview thread

### Thread Safety
- Camera operations use coordinated locking
- UI updates happen on main thread
- Queue-based communication prevents race conditions

## 🔄 Migration from Tkinter Version

The modern version maintains **100% functional compatibility** with the original tkinter app:

- ✅ Same camera commands and settings
- ✅ Identical AI integration and API calls
- ✅ Same configuration file format
- ✅ All monitoring and capture logic preserved
- ✅ Same logging and error handling

**Only the UI layer changed** - all backend functionality works identically.

## 🎯 StormHacks Ready

This modern interface is designed specifically for hackathon presentations:

- **Professional appearance** suitable for demos
- **Clear visual hierarchy** with branded elements
- **Real-time feedback** with animated indicators
- **Responsive design** that scales well
- **Modern aesthetics** that impress judges

## 🐛 Troubleshooting

### Camera Issues
```bash
# Test camera independently
python3 -c "
import subprocess
result = subprocess.run(['rpicam-jpeg', '--nopreview', '--output', '-', '--timeout', '500', '--width', '640', '--height', '480'], capture_output=True, timeout=5)
print('Camera OK' if result.returncode == 0 else 'Camera failed')
"
```

### Import Errors
```bash
# Install dependencies
pip install PyQt5 Pillow requests

# Alternative PySide6
pip install PySide6 Pillow requests
```

### API Issues
- Verify `GEMINI_API_KEY` is correct
- Check internet connectivity
- Ensure `ai_config.json` exists and is valid JSON

## 📝 API Configuration

Example `ai_config.json`:
```json
{
  "gemini_settings": {
    "prompt": "Analyze this 3D printer image. Describe print quality, any issues, and provide recommendations.",
    "temperature": 0.7,
    "max_output_tokens": 150,
    "top_p": 0.8,
    "top_k": 40
  },
  "analysis_settings": {
    "timeout_seconds": 20,
    "retry_attempts": 2
  }
}
```

## 🤝 Contributing

This modern version serves as a foundation for further enhancements:
- Additional camera filters/effects
- Multiple AI model support
- Advanced analytics dashboard
- Print progress tracking
- Historical analysis storage

---

**Built for Circuit Breakers StormHacks 2025** ⚡
