#!/usr/bin/env python3
"""
3D Printer Watchdog - Modern UI Version
Circuit Breakers StormHacks 2025

A completely redesigned, modern dark-themed dashboard using CustomTkinter.
All original functionality preserved with a professional, demo-ready interface.

Features:
- Modern dark theme with teal/purple gradients
- Responsive layout with clean typography
- Live camera feed with rounded borders
- Organized control panels
- Expandable AI analysis and system log sections
- Smooth animations and status indicators
- Professional color-coded status badges
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import threading
import time
import subprocess
import requests
import json
import os
import base64
from datetime import datetime
import queue

# ========================================
# CONFIGURATION & CONSTANTS
# ========================================

# Camera settings - optimized for better quality and proper aspect ratio
CAPTURE_COMMAND = ["rpicam-jpeg", "--nopreview", "--immediate", "--timeout", "1", "-o", "capture.jpg", "--width", "1920", "--height", "1080", "--quality", "95"]
PREVIEW_COMMAND = ["rpicam-jpeg", "--nopreview", "--output", "-", "--timeout", "1", "--width", "960", "--height", "540", "--quality", "85"]
CAPTURE_FILENAME = "capture.jpg"
PREVIEW_FILENAME = "preview.jpg"

# Google Gemini API settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBHIiKiXJNKW6Ot5ZuFT1S2CiajIyvRP_c")
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

# Logging
LOG_FILENAME = "watchdog_log.txt"

# UI Settings
WINDOW_TITLE = "⚡ Circuit Breakers StormHacks 2025 — 3D Printer Watchdog"
WINDOW_SIZE = "1600x1000"
DEFAULT_INTERVAL = 30
MIN_INTERVAL = 5
MAX_INTERVAL = 60

# Camera Display Settings - FIXED STATIC DIMENSIONS to prevent shrinking
# These dimensions are used for ALL image scaling to prevent the feedback loop
# that causes images to get smaller over time. DO NOT make these dynamic!
# Using larger dimensions to fill the display area properly
CAMERA_DISPLAY_WIDTH = 900   # Fixed width for camera display
CAMERA_DISPLAY_HEIGHT = 600  # Fixed height for camera display (taller to fill space)

# ========================================
# MODERN THEME CONFIGURATION
# ========================================

class ModernTheme:
    """Professional dark theme with teal/purple accents"""
    
    # Background colors
    BG_PRIMARY = "#121212"      # Main background
    BG_SECONDARY = "#1e1e1e"    # Card backgrounds
    BG_TERTIARY = "#2a2a2a"     # Input backgrounds
    BG_HEADER = "#0d1b2a"       # Header gradient start
    
    # Text colors
    TEXT_PRIMARY = "#e0e0e0"    # Main text
    TEXT_SECONDARY = "#b0b0b0"  # Secondary text
    TEXT_MUTED = "#808080"      # Muted text
    
    # Accent colors
    ACCENT_TEAL = "#00d4ff"     # Primary accent (electric teal)
    ACCENT_PURPLE = "#8b5cf6"   # Secondary accent
    ACCENT_GREEN = "#10b981"    # Success
    ACCENT_ORANGE = "#f59e0b"   # Warning
    ACCENT_RED = "#ef4444"      # Error
    ACCENT_BLUE = "#3b82f6"     # Info
    
    # Status colors
    STATUS_OK = "#10b981"       # Green
    STATUS_FAIL = "#ef4444"     # Red
    STATUS_WARNING = "#f59e0b"  # Orange
    STATUS_UNKNOWN = "#6b7280"  # Gray

# ========================================
# MAIN APPLICATION CLASS
# ========================================

class ModernPrinterWatchdog:
    def __init__(self):
        # Check for existing instances to prevent camera conflicts
        self.check_existing_instances()
        
        # Set CustomTkinter appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Create main window
        self.root = ctk.CTk()
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.configure(fg_color=ModernTheme.BG_PRIMARY)
        
        # Initialize state variables
        self.monitoring_active = False
        self.preview_active = False
        self.capture_interval = DEFAULT_INTERVAL
        self.current_image = None
        self.ai_analysis_expanded = True
        self.system_log_expanded = False
        
        # Initialize threading events
        self.stop_event = threading.Event()
        self.pause_preview_event = threading.Event()
        self.camera_lock = threading.Lock()
        
        # Initialize queues for thread communication
        self.capture_queue = queue.Queue()
        self.ai_queue = queue.Queue()
        self.preview_queue = queue.Queue()
        self.log_queue = queue.Queue()
        
        # Initialize logging
        self.setup_logging()
        
        # Load AI configuration
        self.ai_config = self.load_ai_config()
        
        # Build the modern UI
        self.build_modern_ui()
        
        # Start background processes
        self.start_preview()
        self.start_ui_update_loop()
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.log_message("🚀 Modern 3D Printer Watchdog started successfully!")

    def check_existing_instances(self):
        """Check for existing watchdog instances and warn user"""
        try:
            result = subprocess.run(['pgrep', '-f', 'watchdog_app'], capture_output=True, text=True)
            if result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                if len(pids) > 0:
                    print("⚠️  WARNING: Found existing watchdog processes!")
                    print("   This may cause camera conflicts and poor image quality.")
                    print(f"   PIDs: {', '.join(pids)}")
                    print("   Consider closing other instances first.")
                    print()
        except Exception:
            pass  # Ignore errors in process checking

    def setup_logging(self):
        """Initialize logging system"""
        try:
            with open(LOG_FILENAME, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*50}\n")
        except Exception as e:
            print(f"Logging setup failed: {e}")

    def load_ai_config(self):
        """Load AI configuration from JSON file"""
        config_file = "ai_config.json"
        default_config = {
            "gemini_settings": {
                "prompt": "You are an expert 3D printing technician analyzing a camera feed...",
                "temperature": 0.3,
                "max_output_tokens": 1024,
                "top_p": 0.8,
                "top_k": 40
            },
            "analysis_settings": {
                "timeout_seconds": 25,
                "retry_attempts": 3,
                "fallback_enabled": True
            },
            "ui_settings": {
                "show_technical_details": True,
                "log_ai_requests": True,
                "display_token_usage": True
            }
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.log_message(f"✅ AI configuration loaded from {config_file}")
                    return config
            else:
                self.log_message(f"⚠️ {config_file} not found, using defaults")
                return default_config
        except Exception as e:
            self.log_message(f"❌ Error loading AI config: {e}, using defaults")
            return default_config

    def build_modern_ui(self):
        """Build the complete modern UI layout"""
        
        # ========================================
        # HEADER SECTION
        # ========================================
        self.create_header()
        
        # ========================================
        # MAIN CONTENT AREA
        # ========================================
        self.main_frame = ctk.CTkFrame(
            self.root,
            fg_color=ModernTheme.BG_PRIMARY,
            corner_radius=0
        )
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Configure grid weights for responsive layout
        self.main_frame.grid_columnconfigure(0, weight=2)  # Camera feed (larger)
        self.main_frame.grid_columnconfigure(1, weight=1)  # Controls (smaller)
        self.main_frame.grid_rowconfigure(0, weight=1)     # Main content
        self.main_frame.grid_rowconfigure(1, weight=0)     # Bottom panels
        
        # ========================================
        # LEFT SIDE - CAMERA FEED
        # ========================================
        self.create_camera_section()
        
        # ========================================
        # RIGHT SIDE - CONTROLS
        # ========================================
        self.create_controls_section()
        
        # ========================================
        # BOTTOM - EXPANDABLE PANELS
        # ========================================
        self.create_bottom_panels()

    def create_header(self):
        """Create the modern header with gradient background"""
        header_frame = ctk.CTkFrame(
            self.root,
            height=80,
            fg_color=ModernTheme.BG_HEADER,
            corner_radius=0
        )
        header_frame.pack(fill="x", padx=0, pady=0)
        header_frame.pack_propagate(False)
        
        # Header content
        header_content = ctk.CTkFrame(header_frame, fg_color="transparent")
        header_content.pack(fill="both", expand=True, padx=30, pady=15)
        
        # Left side - Title and subtitle
        title_frame = ctk.CTkFrame(header_content, fg_color="transparent")
        title_frame.pack(side="left", fill="y")
        
        # Main title
        title_label = ctk.CTkLabel(
            title_frame,
            text="⚡ Circuit Breakers StormHacks 2025 — 3D Printer Watchdog",
            font=ctk.CTkFont(family="Roboto", size=24, weight="bold"),
            text_color=ModernTheme.ACCENT_TEAL
        )
        title_label.pack(anchor="w")
        
        # Subtitle
        subtitle_label = ctk.CTkLabel(
            title_frame,
            text="AI-Powered Print Monitoring",
            font=ctk.CTkFont(family="Roboto", size=14),
            text_color=ModernTheme.TEXT_SECONDARY
        )
        subtitle_label.pack(anchor="w", pady=(5, 0))
        
        # Right side - Status indicator
        self.status_frame = ctk.CTkFrame(header_content, fg_color="transparent")
        self.status_frame.pack(side="right", fill="y")
        
        # AI Status indicator
        self.ai_status_label = ctk.CTkLabel(
            self.status_frame,
            text="🟢 System Ready",
            font=ctk.CTkFont(family="Roboto", size=14, weight="bold"),
            text_color=ModernTheme.STATUS_OK
        )
        self.ai_status_label.pack(anchor="e")
        
        # Token usage indicator (placeholder)
        self.token_usage_label = ctk.CTkLabel(
            self.status_frame,
            text="Tokens: 0 / 1000",
            font=ctk.CTkFont(family="Roboto", size=12),
            text_color=ModernTheme.TEXT_MUTED
        )
        self.token_usage_label.pack(anchor="e", pady=(5, 0))

    def create_camera_section(self):
        """Create the camera feed section with rounded borders"""
        camera_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color=ModernTheme.BG_SECONDARY,
            corner_radius=15
        )
        camera_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))
        camera_frame.grid_rowconfigure(1, weight=1)  # Give weight to the image row, not title
        camera_frame.grid_columnconfigure(0, weight=1)
        
        # Camera title
        camera_title = ctk.CTkLabel(
            camera_frame,
            text="📹 Live Camera Feed",
            font=ctk.CTkFont(family="Roboto", size=18, weight="bold"),
            text_color=ModernTheme.TEXT_PRIMARY
        )
        camera_title.grid(row=0, column=0, sticky="ew", pady=(15, 5))  # Less padding, sticky ew
        
        # Camera display area - remove fixed size, let it expand
        self.camera_display_frame = ctk.CTkFrame(
            camera_frame,
            fg_color=ModernTheme.BG_TERTIARY,
            corner_radius=10
        )
        self.camera_display_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=5)
        self.camera_display_frame.grid_rowconfigure(0, weight=1)
        self.camera_display_frame.grid_columnconfigure(0, weight=1)
        # Remove grid_propagate(False) to allow expansion
        
        # Image label
        self.image_label = ctk.CTkLabel(
            self.camera_display_frame,
            text="📹 Initializing Camera...\nPlease wait",
            font=ctk.CTkFont(family="Roboto", size=16),
            text_color=ModernTheme.TEXT_SECONDARY
        )
        self.image_label.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)  # Less padding
        
        # Camera status
        self.camera_status_label = ctk.CTkLabel(
            camera_frame,
            text="⏳ Starting preview...",
            font=ctk.CTkFont(family="Roboto", size=14, weight="bold"),
            text_color=ModernTheme.ACCENT_TEAL
        )
        self.camera_status_label.grid(row=2, column=0, sticky="ew", pady=(5, 15))  # Less padding

    def create_controls_section(self):
        """Create the controls panel with modern buttons"""
        controls_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color=ModernTheme.BG_SECONDARY,
            corner_radius=15
        )
        controls_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=(0, 10))
        
        # Controls title
        controls_title = ctk.CTkLabel(
            controls_frame,
            text="🎛️ Control Panel",
            font=ctk.CTkFont(family="Roboto", size=18, weight="bold"),
            text_color=ModernTheme.TEXT_PRIMARY
        )
        controls_title.pack(pady=(20, 20))
        
        # Button container
        button_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        # Take Photo & Analyze button
        self.capture_btn = ctk.CTkButton(
            button_frame,
            text="📸 Take Photo & Analyze Now",
            font=ctk.CTkFont(family="Roboto", size=14, weight="bold"),
            fg_color=ModernTheme.ACCENT_BLUE,
            hover_color="#2563eb",
            height=45,
            corner_radius=10,
            command=self.capture_and_analyze
        )
        self.capture_btn.pack(fill="x", pady=(0, 10))
        
        # Reload AI Config button
        self.reload_config_btn = ctk.CTkButton(
            button_frame,
            text="♻️ Reload AI Config",
            font=ctk.CTkFont(family="Roboto", size=14, weight="bold"),
            fg_color=ModernTheme.ACCENT_ORANGE,
            hover_color="#d97706",
            height=45,
            corner_radius=10,
            command=self.reload_ai_config
        )
        self.reload_config_btn.pack(fill="x", pady=(0, 10))
        
        # Start Monitoring button
        self.start_btn = ctk.CTkButton(
            button_frame,
            text="▶️ Start Monitoring",
            font=ctk.CTkFont(family="Roboto", size=14, weight="bold"),
            fg_color=ModernTheme.ACCENT_GREEN,
            hover_color="#059669",
            height=45,
            corner_radius=10,
            command=self.start_monitoring
        )
        self.start_btn.pack(fill="x", pady=(0, 10))
        
        # Stop Monitoring button
        self.stop_btn = ctk.CTkButton(
            button_frame,
            text="⏹️ Stop Monitoring",
            font=ctk.CTkFont(family="Roboto", size=14, weight="bold"),
            fg_color=ModernTheme.ACCENT_RED,
            hover_color="#dc2626",
            height=45,
            corner_radius=10,
            command=self.stop_monitoring,
            state="disabled"
        )
        self.stop_btn.pack(fill="x", pady=(0, 10))
        
        # Test Camera button (for debugging camera positioning)
        self.test_camera_btn = ctk.CTkButton(
            button_frame,
            text="🧪 Test Camera Position",
            font=ctk.CTkFont(family="Roboto", size=14, weight="bold"),
            fg_color=ModernTheme.ACCENT_PURPLE,
            hover_color="#7c3aed",
            height=45,
            corner_radius=10,
            command=self.test_camera_position
        )
        self.test_camera_btn.pack(fill="x", pady=(0, 20))
        
        # Monitoring interval section
        interval_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        interval_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        interval_title = ctk.CTkLabel(
            interval_frame,
            text="⏱️ Monitoring Interval",
            font=ctk.CTkFont(family="Roboto", size=16, weight="bold"),
            text_color=ModernTheme.TEXT_PRIMARY
        )
        interval_title.pack(pady=(0, 10))
        
        # Interval display
        self.interval_label = ctk.CTkLabel(
            interval_frame,
            text=f"Every {DEFAULT_INTERVAL} seconds",
            font=ctk.CTkFont(family="Roboto", size=14),
            text_color=ModernTheme.ACCENT_TEAL
        )
        self.interval_label.pack(pady=(0, 10))
        
        # Interval slider
        self.interval_slider = ctk.CTkSlider(
            interval_frame,
            from_=MIN_INTERVAL,
            to=MAX_INTERVAL,
            number_of_steps=MAX_INTERVAL - MIN_INTERVAL,
            command=self.update_interval,
            fg_color=ModernTheme.BG_TERTIARY,
            progress_color=ModernTheme.ACCENT_TEAL,
            button_color=ModernTheme.ACCENT_TEAL,
            button_hover_color="#00b8d4"
        )
        self.interval_slider.set(DEFAULT_INTERVAL)
        self.interval_slider.pack(fill="x", pady=(0, 10))

    def create_bottom_panels(self):
        """Create expandable AI Analysis and System Log panels"""
        bottom_frame = ctk.CTkFrame(
            self.main_frame,
            fg_color=ModernTheme.BG_PRIMARY,
            corner_radius=0
        )
        bottom_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        bottom_frame.grid_columnconfigure(0, weight=1)
        bottom_frame.grid_columnconfigure(1, weight=1)
        
        # AI Analysis Panel
        self.create_ai_panel(bottom_frame)
        
        # System Log Panel
        self.create_log_panel(bottom_frame)

    def create_ai_panel(self, parent):
        """Create the AI Analysis expandable panel"""
        ai_frame = ctk.CTkFrame(
            parent,
            fg_color=ModernTheme.BG_SECONDARY,
            corner_radius=15
        )
        ai_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # AI Panel header
        ai_header = ctk.CTkFrame(ai_frame, fg_color="transparent", height=50)
        ai_header.pack(fill="x", padx=15, pady=(15, 0))
        ai_header.pack_propagate(False)
        
        ai_title = ctk.CTkLabel(
            ai_header,
            text="🤖 AI Analysis Results",
            font=ctk.CTkFont(family="Roboto", size=16, weight="bold"),
            text_color=ModernTheme.TEXT_PRIMARY
        )
        ai_title.pack(side="left", pady=10)
        
        # Status badge
        self.ai_status_badge = ctk.CTkLabel(
            ai_header,
            text="⚪ Ready",
            font=ctk.CTkFont(family="Roboto", size=12, weight="bold"),
            text_color=ModernTheme.STATUS_UNKNOWN,
            fg_color=ModernTheme.BG_TERTIARY,
            corner_radius=15,
            width=80,
            height=30
        )
        self.ai_status_badge.pack(side="right", pady=10)
        
        # AI content area
        self.ai_content_frame = ctk.CTkFrame(ai_frame, fg_color=ModernTheme.BG_TERTIARY, corner_radius=10)
        self.ai_content_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # AI text display
        self.ai_text = ctk.CTkTextbox(
            self.ai_content_frame,
            font=ctk.CTkFont(family="Roboto Mono", size=12),
            fg_color=ModernTheme.BG_TERTIARY,
            text_color=ModernTheme.TEXT_PRIMARY,
            height=200,
            wrap="word"
        )
        self.ai_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.ai_text.insert("1.0", "🤖 AI Analysis will appear here after taking a photo...\n\nClick 'Take Photo & Analyze Now' to get started!")

    def create_log_panel(self, parent):
        """Create the System Log expandable panel"""
        log_frame = ctk.CTkFrame(
            parent,
            fg_color=ModernTheme.BG_SECONDARY,
            corner_radius=15
        )
        log_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        # Log Panel header
        log_header = ctk.CTkFrame(log_frame, fg_color="transparent", height=50)
        log_header.pack(fill="x", padx=15, pady=(15, 0))
        log_header.pack_propagate(False)
        
        log_title = ctk.CTkLabel(
            log_header,
            text="📋 System Log",
            font=ctk.CTkFont(family="Roboto", size=16, weight="bold"),
            text_color=ModernTheme.TEXT_PRIMARY
        )
        log_title.pack(side="left", pady=10)
        
        # Log content area
        log_content_frame = ctk.CTkFrame(log_frame, fg_color=ModernTheme.BG_TERTIARY, corner_radius=10)
        log_content_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        
        # Log text display
        self.log_text = ctk.CTkTextbox(
            log_content_frame,
            font=ctk.CTkFont(family="Roboto Mono", size=11),
            fg_color=ModernTheme.BG_TERTIARY,
            text_color=ModernTheme.TEXT_SECONDARY,
            height=200,
            wrap="word"
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)

    # ========================================
    # CORE FUNCTIONALITY (PRESERVED FROM ORIGINAL)
    # ========================================

    def log_message(self, message, level="INFO"):
        """Add message to log queue for UI display"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        # Add to queue for UI update
        self.log_queue.put(formatted_message)
        
        # Also write to file
        try:
            with open(LOG_FILENAME, 'a', encoding='utf-8') as f:
                f.write(f"{formatted_message}\n")
        except Exception:
            pass  # Fail silently for logging errors

    def update_interval(self, value):
        """Update monitoring interval from slider"""
        interval = int(float(value))
        self.capture_interval = interval
        self.interval_label.configure(text=f"Every {interval} seconds")

    def update_preview_status(self, status_text):
        """Update camera status label"""
        if hasattr(self, 'camera_status_label'):
            self.camera_status_label.configure(text=status_text)

    def test_camera_position(self):
        """Test camera positioning and quality - just capture without AI analysis"""
        self.log_message("🧪 Testing camera position and quality...")
        self.update_ai_status("🟡 Testing Camera...")
        
        def test_worker():
            try:
                # Pause preview briefly
                self.pause_preview_event.set()
                time.sleep(0.5)
                
                # Acquire camera lock
                with self.camera_lock:
                    # Use high-resolution test capture
                    test_cmd = ["rpicam-jpeg", "--nopreview", "--immediate", 
                               "--timeout", "2000", "-o", "test_capture.jpg", 
                               "--width", "1920", "--height", "1080", "--quality", "95"]
                    
                    result = subprocess.run(test_cmd, capture_output=True, text=True, timeout=10)

                    if result.returncode == 0:
                        self.log_message("📸 Test capture successful - check image quality and positioning")
                        self.update_preview_status("📸 Test Image Captured")
                        
                        # Display the test image
                        self.capture_queue.put({
                            "success": True,
                            "image_path": "test_capture.jpg"
                        })
                        
                        # Show analysis in AI panel
                        self.ai_text.delete("1.0", "end")
                        self.ai_text.insert("1.0", "🧪 Camera Position Test\n")
                        self.ai_text.insert("end", "=" * 35 + "\n\n")
                        self.ai_text.insert("end", "✅ Test image captured successfully!\n\n")
                        self.ai_text.insert("end", "📋 Check the image above for:\n")
                        self.ai_text.insert("end", "• Is your 3D printer visible?\n")
                        self.ai_text.insert("end", "• Is the print bed in frame?\n")
                        self.ai_text.insert("end", "• Is the image clear and focused?\n")
                        self.ai_text.insert("end", "• Is the lighting adequate?\n\n")
                        self.ai_text.insert("end", "💡 Adjust camera position if needed, then test again!")
                        
                        self.ai_status_badge.configure(text="🧪 TEST", text_color=ModernTheme.ACCENT_PURPLE)
                        self.update_ai_status("🟢 Test Complete")

                    else:
                        error_msg = result.stderr.strip() or "Unknown camera error"
                        self.log_message(f"❌ Camera test failed: {error_msg}")
                        self.update_ai_status("🔴 Test Failed")

            except subprocess.TimeoutExpired:
                self.log_message("❌ Camera test timed out")
                self.update_ai_status("🔴 Test Timeout")
            except Exception as e:
                self.log_message(f"❌ Test error: {e}")
                self.update_ai_status("🔴 Test Error")
            finally:
                # Resume preview
                self.pause_preview_event.clear()

        # Run in background thread
        thread = threading.Thread(target=test_worker, daemon=True)
        thread.start()

    def capture_and_analyze(self):
        """Capture photo and analyze with AI (manual trigger)"""
        if self.monitoring_active:
            self.log_message("⚠️ Cannot take manual photo while monitoring is active")
            return
            
        self.log_message("📸 Manual photo capture initiated...")
        self.update_ai_status("🟡 Capturing...")
        
        def capture_worker():
            try:
                # Pause preview briefly
                self.pause_preview_event.set()
                time.sleep(0.5)
                
                # Acquire camera lock
                with self.camera_lock:
                    # Use high-resolution capture command
                    capture_cmd = ["rpicam-jpeg", "--nopreview", "--immediate", 
                                 "--timeout", "1000", "-o", CAPTURE_FILENAME, 
                                 "--width", "1920", "--height", "1440"]
                    
                    result = subprocess.run(capture_cmd, capture_output=True, text=True, timeout=8)

                    if result.returncode == 0:
                        self.log_message("📸 Photo captured - analyzing...")
                        self.update_preview_status("📸 Analyzing captured image...")
                        
                        self.capture_queue.put({
                            "success": True,
                            "image_path": CAPTURE_FILENAME
                        })

                        # Start AI analysis
                        self.analyze_image(CAPTURE_FILENAME)

                    else:
                        error_msg = result.stderr.strip() or "Unknown camera error"
                        self.log_message(f"❌ Camera capture failed: {error_msg}")
                        self.capture_queue.put({
                            "success": False,
                            "error": error_msg
                        })
                        self.update_ai_status("🔴 Capture Failed")

            except subprocess.TimeoutExpired:
                self.log_message("❌ Camera capture timed out")
                self.update_ai_status("🔴 Timeout")
            except Exception as e:
                self.log_message(f"❌ Capture error: {e}")
                self.update_ai_status("🔴 Error")
            finally:
                # Resume preview
                self.pause_preview_event.clear()

        # Run in background thread
        thread = threading.Thread(target=capture_worker, daemon=True)
        thread.start()

    def analyze_image(self, image_path):
        """Analyze image with Gemini AI"""
        if not os.path.exists(image_path):
            self.log_message(f"❌ Image file not found: {image_path}")
            return

        self.update_ai_status("🟡 Analyzing...")

        def ai_worker():
            try:
                if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
                    # Encode image
                    with open(image_path, "rb") as image_file:
                        image_data = base64.b64encode(image_file.read()).decode('utf-8')

                    headers = {"Content-Type": "application/json"}

                    # Get settings from config
                    gemini_settings = self.ai_config.get("gemini_settings", {})
                    prompt_text = gemini_settings.get("prompt", "Analyze this 3D printing image.")
                    
                    payload = {
                        "contents": [{
                            "parts": [
                                {"text": prompt_text},
                                {
                                    "inline_data": {
                                        "mime_type": "image/jpeg",
                                        "data": image_data
                                    }
                                }
                            ]
                        }],
                        "generationConfig": {
                            "temperature": gemini_settings.get("temperature", 0.3),
                            "maxOutputTokens": gemini_settings.get("max_output_tokens", 1024),
                            "topP": gemini_settings.get("top_p", 0.8),
                            "topK": gemini_settings.get("top_k", 40)
                        }
                    }

                    # Make API call
                    api_url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
                    timeout = self.ai_config.get("analysis_settings", {}).get("timeout_seconds", 25)
                    response = requests.post(api_url, headers=headers, json=payload, timeout=timeout)

                    if response.status_code == 200:
                        result = response.json()
                        
                        # Debug logging if enabled
                        if self.ai_config.get("ui_settings", {}).get("log_ai_requests", False):
                            self.log_message(f"🔍 Full Gemini API response: {result}")
                        
                        try:
                            if "candidates" in result and len(result["candidates"]) > 0:
                                candidate = result["candidates"][0]
                                
                                # Handle different finish reasons
                                finish_reason = candidate.get("finishReason", "")
                                if finish_reason == "MAX_TOKENS":
                                    self.log_message("⚠️ Gemini response was truncated due to token limit")
                                
                                # Extract content
                                if "content" in candidate:
                                    content = candidate["content"]
                                    if "parts" in content and len(content["parts"]) > 0:
                                        analysis_text = ""
                                        for part in content["parts"]:
                                            if "text" in part:
                                                analysis_text += part["text"]
                                        
                                        if analysis_text.strip():
                                            if finish_reason == "MAX_TOKENS":
                                                analysis_text += "\n\n[Note: Response was truncated due to length limits]"
                                            
                                            self.ai_queue.put({
                                                "success": True,
                                                "description": analysis_text.strip(),
                                                "timestamp": datetime.now()
                                            })
                                            return
                                
                                # Fallback message
                                fallback_msg = "⚠️ AI analysis failed due to unexpected response format."
                                if finish_reason == "MAX_TOKENS":
                                    fallback_msg += " The response was truncated - consider increasing max_output_tokens in ai_config.json."
                                
                                self.ai_queue.put({
                                    "success": True,
                                    "description": fallback_msg,
                                    "timestamp": datetime.now()
                                })

                        except Exception as e:
                            self.log_message(f"Gemini API response parsing failed: {e}")
                            self.ai_queue.put({
                                "success": False,
                                "error": f"Response parsing error: {e}"
                            })

                    else:
                        error_msg = f"API request failed: {response.status_code} - {response.text}"
                        self.log_message(f"❌ Gemini API error: {error_msg}")
                        self.ai_queue.put({
                            "success": False,
                            "error": error_msg
                        })

                else:
                    self.log_message("❌ No Gemini API key configured")
                    self.ai_queue.put({
                        "success": False,
                        "error": "No API key configured"
                    })

            except Exception as e:
                self.log_message(f"❌ AI analysis error: {e}")
                self.ai_queue.put({
                    "success": False,
                    "error": f"Analysis error: {e}"
                })

        # Run analysis in background thread
        thread = threading.Thread(target=ai_worker, daemon=True)
        thread.start()

    def display_image(self, image_path):
        """Display captured image in UI"""
        try:
            # Load image with PIL
            image = Image.open(image_path)

            # Use static dimensions to prevent shrinking feedback loop
            # The UI layout now expands properly to accommodate these dimensions
            display_width = CAMERA_DISPLAY_WIDTH
            display_height = CAMERA_DISPLAY_HEIGHT

            # Calculate scaling to fit without cropping (maintain aspect ratio)
            img_width, img_height = image.size
            scale_w = display_width / img_width
            scale_h = display_height / img_height
            scale = min(scale_w, scale_h)  # Use full scale, no padding reduction

            # Calculate final dimensions
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            # Optional: Enhance image quality BEFORE resizing for better results
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.1)  # Slight sharpening before resize
            
            # Let CTkImage handle the scaling for best quality - don't double-scale!
            ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=(new_width, new_height))

            # Update display with indicator that this is a captured image
            self.image_label.configure(image=ctk_image, text="")
            self.image_label.image = ctk_image  # Keep reference
            self.current_image = ctk_image
            
            # Update status to show this is the captured image being analyzed
            self.update_preview_status("📸 Captured Image (being analyzed by AI)")

        except Exception as e:
            self.log_message(f"Error displaying image: {e}")
            self.image_label.configure(text=f"Error loading image:\n{e}", image="")

    def display_preview(self, image_path):
        """Display preview frame in UI"""
        try:
            # Load image with PIL
            image = Image.open(image_path)

            # Use static dimensions to prevent shrinking feedback loop
            # The UI layout now expands properly to accommodate these dimensions
            display_width = CAMERA_DISPLAY_WIDTH
            display_height = CAMERA_DISPLAY_HEIGHT

            # Calculate scaling to fit without cropping (maintain aspect ratio)
            img_width, img_height = image.size
            scale_w = display_width / img_width
            scale_h = display_height / img_height
            scale = min(scale_w, scale_h)  # Fit within bounds without cropping

            # Calculate final dimensions
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            
            # Optional: Enhance image quality BEFORE resizing for better results
            from PIL import ImageEnhance
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.05)  # Very slight sharpening for preview
            
            # Let CTkImage handle the scaling for best quality - don't double-scale!
            ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=(new_width, new_height))

            # Update display and keep reference for preview
            self.image_label.configure(image=ctk_image, text="")
            self.image_label.image = ctk_image  # Keep reference to prevent garbage collection

        except Exception as e:
            self.log_message(f"⚠️ Preview display error: {e}")

    def start_preview(self):
        """Start live camera preview"""
        if self.preview_active:
            return

        self.log_message("📹 Starting live camera preview...")
        self.preview_active = True
        self.update_preview_status("🔄 Starting preview thread...")

        # Start preview thread
        self.preview_thread = threading.Thread(target=self.preview_worker, daemon=True)
        self.preview_thread.start()

    def preview_worker(self):
        """Continuously capture preview frames"""
        self.log_message("📹 Preview worker started")
        self.update_preview_status("📷 Testing camera...")
        frame_count = 0

        while self.preview_active and not self.stop_event.is_set():
            try:
                # Check if we need to pause for manual capture
                if self.pause_preview_event.is_set():
                    self.update_preview_status("⏸️ Paused for photo capture...")
                    
                    # Wait until pause is cleared
                    while self.pause_preview_event.is_set() and not self.stop_event.is_set():
                        time.sleep(0.1)
                    
                    if self.stop_event.is_set():
                        break
                        
                    self.update_preview_status("📹 Live preview resumed")
                    continue

                # Acquire camera lock for preview (non-blocking)
                if self.camera_lock.acquire(blocking=False):
                    try:
                        # Capture preview frame
                        result = subprocess.run(PREVIEW_COMMAND, capture_output=True, timeout=3)
                        
                        if result.returncode == 0 and len(result.stdout) > 1000:
                            # Save preview frame
                            with open(PREVIEW_FILENAME, 'wb') as f:
                                f.write(result.stdout)
                            
                            frame_count += 1
                            
                            # Queue for UI update
                            self.preview_queue.put({
                                "success": True,
                                "image_path": PREVIEW_FILENAME
                            })

                            # Update status for first few frames
                            if frame_count == 1:
                                self.update_preview_status("✅ Camera working - live preview active")
                            elif frame_count % 20 == 0:
                                self.update_preview_status(f"📹 Live preview active ({frame_count} frames)")

                            # Log every 50 frames to reduce spam
                            if frame_count % 50 == 0:
                                self.log_message(f"📹 Preview: {frame_count} frames captured")
                        else:
                            if frame_count == 0:  # First attempt failed
                                self.update_preview_status("❌ Camera not detected")
                            self.log_message(f"⚠️ Preview capture failed: returncode={result.returncode}")

                    finally:
                        self.camera_lock.release()
                else:
                    # Camera is busy, skip this frame
                    pass

                # Wait before next frame (roughly 2-3 FPS)
                time.sleep(0.4)

            except subprocess.TimeoutExpired:
                self.log_message("⚠️ Preview capture timeout")
                continue
            except Exception as e:
                self.log_message(f"⚠️ Preview error: {e}")
                time.sleep(1)

    def start_monitoring(self):
        """Start automatic monitoring"""
        if self.monitoring_active:
            self.log_message("⚠️ Monitoring is already active")
            return

        self.log_message(f"🚀 Starting automatic monitoring (every {self.capture_interval}s)")
        self.monitoring_active = True
        self.update_ai_status("🟡 Monitoring Active")
        
        # Update button states
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        
        # Start monitoring thread
        self.monitoring_thread = threading.Thread(target=self.monitoring_worker, daemon=True)
        self.monitoring_thread.start()

    def stop_monitoring(self):
        """Stop automatic monitoring"""
        if not self.monitoring_active:
            self.log_message("⚠️ Monitoring is not active")
            return

        self.log_message("⏹️ Stopping automatic monitoring...")
        self.monitoring_active = False
        self.update_ai_status("🟢 System Ready")
        
        # Update button states
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def monitoring_worker(self):
        """Background monitoring loop"""
        while self.monitoring_active and not self.stop_event.is_set():
            try:
                self.log_message("📸 Automatic capture initiated...")
                
                # Pause preview briefly
                self.pause_preview_event.set()
                time.sleep(0.5)
                
                # Acquire camera lock
                with self.camera_lock:
                    result = subprocess.run(CAPTURE_COMMAND, capture_output=True, text=True, timeout=8)

                    if result.returncode == 0:
                        self.log_message("📸 Photo captured successfully - analyzing with AI...")
                        self.capture_queue.put({
                            "success": True,
                            "image_path": CAPTURE_FILENAME
                        })

                        # Start AI analysis
                        self.analyze_image(CAPTURE_FILENAME)

                    else:
                        error_msg = result.stderr.strip() or "Unknown camera error"
                        self.log_message(f"❌ Automatic capture failed: {error_msg}")

                # Resume preview
                self.pause_preview_event.clear()

                # Wait for next capture
                for i in range(self.capture_interval):
                    if not self.monitoring_active or self.stop_event.is_set():
                        break
                    time.sleep(1)

            except Exception as e:
                self.log_message(f"❌ Monitoring error: {e}")
                time.sleep(5)  # Wait before retrying

    def reload_ai_config(self):
        """Reload AI configuration from file"""
        self.ai_config = self.load_ai_config()
        self.log_message("🔄 AI configuration reloaded from file")
        
        # Show confirmation in AI text area
        self.ai_text.delete("1.0", "end")
        self.ai_text.insert("1.0", "🔄 AI Configuration Reloaded\n")
        self.ai_text.insert("end", "=" * 35 + "\n\n")
        
        # Show current prompt
        current_prompt = self.ai_config.get("gemini_settings", {}).get("prompt", "No prompt loaded")
        self.ai_text.insert("end", "Current AI Prompt:\n")
        self.ai_text.insert("end", f'"{current_prompt}"\n\n')
        
        # Show settings
        gemini_settings = self.ai_config.get("gemini_settings", {})
        self.ai_text.insert("end", "Settings:\n")
        self.ai_text.insert("end", f"• Temperature: {gemini_settings.get('temperature', 0.3)}\n")
        self.ai_text.insert("end", f"• Max Tokens: {gemini_settings.get('max_output_tokens', 1024)}\n")
        self.ai_text.insert("end", f"• Top P: {gemini_settings.get('top_p', 0.8)}\n")
        self.ai_text.insert("end", f"• Top K: {gemini_settings.get('top_k', 40)}\n\n")
        
        self.ai_text.insert("end", "💡 Edit ai_config.json to customize the AI prompt and settings!")

    def update_ai_status(self, status):
        """Update AI status indicator"""
        if "🟢" in status:
            color = ModernTheme.STATUS_OK
        elif "🟡" in status:
            color = ModernTheme.STATUS_WARNING
        elif "🔴" in status:
            color = ModernTheme.STATUS_FAIL
        else:
            color = ModernTheme.STATUS_UNKNOWN
            
        self.ai_status_label.configure(text=status, text_color=color)

    def display_ai_result(self, result):
        """Display AI analysis result"""
        if result["success"]:
            description = result["description"]
            timestamp = result["timestamp"].strftime("%H:%M:%S")
            
            # Clear previous content and add new analysis
            self.ai_text.delete("1.0", "end")
            
            # Add header
            self.ai_text.insert("1.0", f"🤖 AI Analysis - {timestamp}\n")
            self.ai_text.insert("end", "=" * 35 + "\n\n")
            
            # Add the analysis content
            self.ai_text.insert("end", f"{description}\n\n")
            
            # Add footer
            self.ai_text.insert("end", "─" * 35 + "\n")
            self.ai_text.insert("end", "💡 Click 'Take Photo & Analyze Now' for a new analysis\n")
            
            # Update status badge based on content
            if "✅" in description or "LOOKS GOOD" in description.upper():
                self.ai_status_badge.configure(text="✅ OK", text_color=ModernTheme.STATUS_OK)
            elif "❌" in description or "FAILURE" in description.upper() or "FAIL" in description.upper():
                self.ai_status_badge.configure(text="❌ FAIL", text_color=ModernTheme.STATUS_FAIL)
            elif "⚠️" in description or "ISSUE" in description.upper():
                self.ai_status_badge.configure(text="⚠️ ISSUE", text_color=ModernTheme.STATUS_WARNING)
            elif "🤷" in description or "NO PRINTER" in description.upper():
                self.ai_status_badge.configure(text="🤷 N/A", text_color=ModernTheme.STATUS_UNKNOWN)
            else:
                self.ai_status_badge.configure(text="✅ OK", text_color=ModernTheme.STATUS_OK)
            
            # Return to live preview after 3 seconds
            self.root.after(3000, lambda: self.update_preview_status("📹 Live preview resumed"))
            
            # Update main status
            self.update_ai_status("🟢 Analysis Complete")
            self.log_message("✅ AI analysis completed")

        else:
            # Handle error case
            error_msg = result.get("error", "Unknown error")
            self.ai_text.delete("1.0", "end")
            self.ai_text.insert("1.0", f"❌ AI Analysis Failed\n")
            self.ai_text.insert("end", "=" * 35 + "\n\n")
            self.ai_text.insert("end", f"Error: {error_msg}\n\n")
            self.ai_text.insert("end", "💡 Check your API key and internet connection")
            
            self.ai_status_badge.configure(text="❌ ERROR", text_color=ModernTheme.STATUS_FAIL)
            self.update_ai_status("🔴 Analysis Failed")

    def start_ui_update_loop(self):
        """Start the main UI update loop"""
        self.update_ui_loop()

    def update_ui_loop(self):
        """Main UI update loop - runs in main thread"""
        try:
            # Process log messages
            while not self.log_queue.empty():
                message = self.log_queue.get_nowait()
                self.log_text.insert("end", message + "\n")
                self.log_text.see("end")

            # Process capture results
            if not self.capture_queue.empty():
                result = self.capture_queue.get_nowait()
                if result["success"]:
                    self.display_image(result["image_path"])
                else:
                    self.log_message(f"Camera capture failed: {result['error']}")

            # Process AI results
            if not self.ai_queue.empty():
                result = self.ai_queue.get_nowait()
                self.display_ai_result(result)

            # Process preview results
            if not self.preview_queue.empty():
                result = self.preview_queue.get_nowait()
                if result["success"]:
                    self.display_preview(result["image_path"])

        except Exception as e:
            print(f"UI update error: {e}")

        # Schedule next update
        self.root.after(100, self.update_ui_loop)

    def on_closing(self):
        """Handle application closing"""
        self.log_message("👋 Shutting down 3D Printer Watchdog...")
        
        # Stop all background processes
        self.stop_event.set()
        self.monitoring_active = False
        self.preview_active = False
        
        # Give threads time to stop
        time.sleep(0.5)
        
        # Close the application
        self.root.destroy()

# ========================================
# APPLICATION ENTRY POINT
# ========================================

def main():
    """Main application entry point"""
    print("🚀 Starting Modern 3D Printer Watchdog...")
    print("🖥️  Initializing modern UI...")
    
    try:
        app = ModernPrinterWatchdog()
        app.root.mainloop()
    except KeyboardInterrupt:
        print("\n👋 Application interrupted by user")
    except Exception as e:
        print(f"❌ Application error: {e}")
        messagebox.showerror("Error", f"Application failed to start:\n{e}")

if __name__ == "__main__":
    main()
