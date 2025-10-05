#!/bin/bash
# Launch script for Modern 3D Printer Watchdog
# Circuit Breakers StormHacks 2025

echo "🚀 Starting Modern 3D Printer Watchdog..."
echo "✨ Professional Dark Theme UI with CustomTkinter"
echo ""

# Change to the application directory
cd "$(dirname "$0")" || {
    echo "❌ Error: Could not find application directory"
    exit 1
}

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Error: Virtual environment not found"
    echo "   Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if CustomTkinter is installed
echo "🔍 Checking dependencies..."
source venv/bin/activate
python3 -c "import customtkinter, PIL, requests" 2>/dev/null || {
    echo "❌ Error: Required modules not found"
    echo "   Installing CustomTkinter..."
    pip install customtkinter
}

echo "✅ Dependencies OK"

# Set display if not set
export DISPLAY=${DISPLAY:-:0}
echo "🖥️ Display set to: $DISPLAY"

# Set API key if not set
if [ -z "$GEMINI_API_KEY" ]; then
    export GEMINI_API_KEY="AIzaSyBHIiKiXJNKW6Ot5ZuFT1S2CiajIyvRP_c"
    echo "🔑 Using default API key"
fi

# Launch the modern application
echo "🎯 Launching Modern UI..."
echo ""
python3 watchdog_app_modern.py

echo ""
echo "👋 Modern 3D Printer Watchdog closed"
