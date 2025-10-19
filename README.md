# PandaCam - 3D Printer Watchdog - Built for Stormhacks 2025

### 🎯 Project Overview -- 
An intelligent 3D printer monitoring system that uses AI-powered image analysis to watch your prints in real-time. Built for StormHacks 2025 by Team Circuit Breakers.

### ✨ Features
- **Live Camera Preview**: Continuous real-time camera feed
- **AI Analysis**: Google Gemini AI analyzes print quality and detects issues
- **Modern Dark UI**: Beautiful, professional interface with StormHacks branding
- **Instant Capture**: Click to immediately capture and analyze photos
- **Automatic Monitoring**: Set intervals for hands-free monitoring
- **Desktop Integration**: Launch from desktop icon or applications menu

### 🚀 Quick Start

#### Option 1: Desktop Icon
- Double-click the "Circuit Breakers StormHacks 2025" icon on your desktop
- Or find it in your applications menu

#### Option 2: Launcher Script
```bash
./launch_watchdog.sh
```

#### Option 3: Direct Launch
```bash
cd rpi_firmware
python3 watchdog_app.py
```

### 📋 Requirements
- Raspberry Pi OS (Bookworm)
- Camera module enabled (`sudo raspi-config`)
- Python 3 with tkinter, PIL, and requests
- Google Gemini API key (free at: https://makersuite.google.com/app/apikey)

### 🔧 Setup
1. Enable camera: `sudo raspi-config` → Interface Options → Camera → Enable
2. Install dependencies: `sudo apt install python3-tk python3-pil python3-requests`
3. Add your Gemini API key to `rpi_firmware/watchdog_app.py` (line 53)
4. Launch the application!

### 🎮 Usage
1. **Live Preview**: Automatically shows camera feed when app starts
2. **Manual Capture**: Click "📸 Take Photo & Analyze Now" for instant analysis
3. **Auto Monitoring**: Use "▶️ Start Monitoring" for periodic captures
4. **Adjust Interval**: Use the slider to set monitoring frequency (5-60 seconds)

