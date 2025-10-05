#!/bin/bash
# Camera Setup Script for Raspberry Pi

echo "Setting up Raspberry Pi Camera..."
echo ""

# Check current camera status
echo "Current camera status:"
vcgencmd get_camera
echo ""

# Instructions
echo "To enable the camera:"
echo "1. Run: sudo raspi-config"
echo "2. Navigate: Interfacing Options → Camera → Enable"
echo "3. Reboot: sudo reboot"
echo ""
echo "After reboot, test with:"
echo "rpicam-jpeg -o test.jpg"
echo ""
echo "Then run the watchdog app:"
echo "./run_app.sh"
