#!/bin/bash
# Circuit Breakers StormHacks 2025 - 3D Printer Watchdog Launcher
# This script launches the 3D Printer Watchdog application

echo "🚀 Starting Circuit Breakers StormHacks 2025 - 3D Printer Watchdog..."

# Change to the application directory
cd "$(dirname "$0")/rpi_firmware" || {
    echo "❌ Error: Could not find rpi_firmware directory"
    exit 1
}

# Check if Python modules are available
echo "🔍 Checking dependencies..."
python3 -c "import tkinter, PIL, requests" 2>/dev/null || {
    echo "❌ Error: Required Python modules not found"
    echo "   Please install: sudo apt install python3-tk python3-pil python3-requests"
    exit 1
}

echo "✅ Dependencies OK"

# Set display if not set
export DISPLAY=${DISPLAY:-:0}
echo "🖥️ Display set to: $DISPLAY"

# Launch the application
echo "🎯 Launching application..."
python3 watchdog_app.py

echo "👋 Application closed"
