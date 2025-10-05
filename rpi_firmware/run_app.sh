#!/bin/bash
# 3D Printer Watchdog Launcher Script

cd "$(dirname "$0")"

# Set display for GUI
export DISPLAY=:0

# Activate virtual environment
source venv/bin/activate

# Run the modern PyQt5/PySide6 app
python3 watchdog_app_modern.py
