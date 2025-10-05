#!/usr/bin/env python3
"""
3D Printer Watchdog - Raspberry Pi Desktop Application

This application captures photos of 3D prints using the Raspberry Pi camera
and analyzes them with Google Gemini AI (free tier available) to provide detailed feedback.

Requirements:
- Raspberry Pi OS (Bookworm)
- Camera module enabled
- Google Gemini API key (get free at: https://makersuite.google.com/app/apikey)
- Python libraries: tkinter, Pillow, requests

Usage:
1. Get your FREE Google Gemini API key at: https://makersuite.google.com/app/apikey
2. Paste your API key in GEMINI_API_KEY below
3. Run: python3 watchdog_app.py
4. The live camera preview starts automatically in the UI
5. Use "Take Photo & Analyze" for instant capture with real AI analysis
6. Use "Start Monitoring" for automatic interval-based capture with AI analysis

Note: Live preview is always active and shows directly in the main UI window!
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
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
# CONFIGURATION - EDIT THESE VALUES
# ========================================

# Removed unused Hugging Face token - this app uses Gemini API only

# Camera settings - working configuration
CAPTURE_COMMAND = ["rpicam-jpeg", "--nopreview", "--immediate", "--timeout", "1", "-o", "capture.jpg", "--width", "1280", "--height", "960"]
PREVIEW_COMMAND = ["rpicam-jpeg", "--nopreview", "--output", "-", "--timeout", "1", "--width", "640", "--height", "480"]
CAPTURE_FILENAME = "capture.jpg"
PREVIEW_FILENAME = "preview.jpg"

# Google Gemini API settings (for free AI analysis)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyBHIiKiXJNKW6Ot5ZuFT1S2CiajIyvRP_c")  # Your working API key
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"

# Logging
LOG_FILENAME = "watchdog_log.txt"

# UI Settings
WINDOW_TITLE = "Circuit Breakers StormHacks 2025 - 3D Printer Watchdog"
WINDOW_SIZE = "2000x1400"
DEFAULT_INTERVAL = 30  # seconds
MIN_INTERVAL = 5
MAX_INTERVAL = 60

# ========================================
# MAIN APPLICATION CLASS
# ========================================

class PrinterWatchdogApp:
    def __init__(self, root):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(WINDOW_SIZE)
        self.root.resizable(True, True)
        
        # Initialize logging first
        self.setup_logging()

        # Initialize queues for thread communication
        self.capture_queue = queue.Queue()
        self.ai_queue = queue.Queue()
        self.preview_queue = queue.Queue()
        self.log_queue = queue.Queue()

        # Load AI configuration (after log_queue is initialized)
        self.ai_config = self.load_ai_config()

        # Modern Dark UI styling
        self.style = ttk.Style()
        
        # Dark theme colors
        self.bg_primary = "#1a1a1a"      # Main background
        self.bg_secondary = "#2d2d2d"    # Card backgrounds
        self.bg_tertiary = "#3d3d3d"     # Input backgrounds
        self.text_primary = "#ffffff"     # Main text
        self.text_secondary = "#b0b0b0"   # Secondary text
        self.accent_blue = "#0d7377"      # Primary accent
        self.accent_green = "#14a085"     # Success
        self.accent_orange = "#fa7268"    # Warning
        self.accent_red = "#ff6b6b"       # Danger
        
        # Configure dark theme
        self.style.configure("TFrame", background=self.bg_primary)
        self.style.configure("TLabel", 
                           background=self.bg_primary, 
                           foreground=self.text_primary, 
                           font=("Segoe UI", 10))
        
        self.style.configure("TButton",
                           font=("Segoe UI", 10, "bold"),
                           padding=12,
                           relief="flat",
                           borderwidth=0,
                           background=self.bg_tertiary,
                           foreground=self.text_primary)
        self.style.map("TButton",
                      background=[("active", self.bg_secondary), ("pressed", self.accent_blue)])

        # Custom button styles with dark theme
        self.style.configure("Primary.TButton",
                           background=self.accent_blue,
                           foreground="white")
        self.style.map("Primary.TButton",
                      background=[("active", "#0a5d61"), ("pressed", "#085054")])
        
        self.style.configure("Success.TButton",
                           background=self.accent_green,
                           foreground="white")
        self.style.map("Success.TButton",
                      background=[("active", "#0f7a65"), ("pressed", "#0c6b59")])
        
        self.style.configure("Warning.TButton",
                           background=self.accent_orange,
                           foreground="white")
        self.style.map("Warning.TButton",
                      background=[("active", "#e85a50"), ("pressed", "#d64a40")])
        
        self.style.configure("Danger.TButton",
                           background=self.accent_red,
                           foreground="white")
        self.style.map("Danger.TButton",
                      background=[("active", "#e55555"), ("pressed", "#cc4444")])

        # Dark LabelFrame styling
        self.style.configure("Card.TLabelframe",
                           background=self.bg_secondary,
                           borderwidth=2,
                           relief="solid",
                           lightcolor=self.bg_tertiary,
                           darkcolor=self.bg_tertiary)
        self.style.configure("Card.TLabelframe.Label",
                           background=self.bg_secondary,
                           foreground=self.text_primary,
                           font=("Segoe UI", 12, "bold"))

        # Set root background
        self.root.configure(bg=self.bg_primary)

        # Threading and state management
        self.monitoring_active = False
        self.preview_active = True  # Always active for live preview
        self.capture_thread = None
        self.ai_thread = None
        self.preview_thread = None
        self.timer_thread = None
        self.stop_event = threading.Event()
        self.camera_lock = threading.Lock()  # Prevent camera conflicts
        self.pause_preview_event = threading.Event()  # Signal to pause preview for capture

        # UI state
        self.current_image = None
        self.current_status = "🟢 System Ready - Live Preview Active"
        self.capture_interval = DEFAULT_INTERVAL

        # Build the UI
        self.build_ui()

        # Start UI update loop
        self.update_ui_loop()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_ai_config(self):
        """Load AI configuration from JSON file"""
        config_file = "ai_config.json"
        default_config = {
            "gemini_settings": {
                "prompt": "Look at this image and describe what you see in 2-3 sentences. Focus on any 3D printer, print quality, or technical equipment visible.",
                "temperature": 0.7,
                "max_output_tokens": 100,
                "top_p": 0.8,
                "top_k": 40
            },
            "analysis_settings": {
                "timeout_seconds": 20,
                "retry_attempts": 2,
                "fallback_enabled": False
            },
            "ui_settings": {
                "show_technical_details": True,
                "log_ai_requests": True,
                "display_token_usage": False
            }
        }
        
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                self.log_message(f"✅ Loaded AI configuration from {config_file}")
                return config
            else:
                self.log_message(f"⚠️ Config file {config_file} not found, using defaults")
                return default_config
        except Exception as e:
            self.log_message(f"❌ Error loading AI config: {e}, using defaults", "ERROR")
            return default_config

    def reload_ai_config(self):
        """Reload AI configuration from file"""
        self.ai_config = self.load_ai_config()
        self.log_message("🔄 AI configuration reloaded from file")
        
        # Show confirmation in AI text area
        self.ai_text.config(state=tk.NORMAL)
        self.ai_text.delete(1.0, tk.END)
        self.ai_text.insert(tk.END, "🔄 AI Configuration Reloaded\n")
        self.ai_text.insert(tk.END, "=" * 35 + "\n\n")
        
        # Show current prompt
        current_prompt = self.ai_config.get("gemini_settings", {}).get("prompt", "No prompt loaded")
        self.ai_text.insert(tk.END, "Current AI Prompt:\n")
        self.ai_text.insert(tk.END, f'"{current_prompt}"\n\n')
        
        # Show settings
        gemini_settings = self.ai_config.get("gemini_settings", {})
        self.ai_text.insert(tk.END, "Settings:\n")
        self.ai_text.insert(tk.END, f"• Temperature: {gemini_settings.get('temperature', 0.7)}\n")
        self.ai_text.insert(tk.END, f"• Max Tokens: {gemini_settings.get('max_output_tokens', 100)}\n")
        self.ai_text.insert(tk.END, f"• Top P: {gemini_settings.get('top_p', 0.8)}\n")
        self.ai_text.insert(tk.END, f"• Top K: {gemini_settings.get('top_k', 40)}\n\n")
        
        self.ai_text.insert(tk.END, "💡 Edit ai_config.json to customize the AI prompt and settings!")
        self.ai_text.config(state=tk.DISABLED)

    def setup_logging(self):
        """Initialize logging file"""
        try:
            with open(LOG_FILENAME, 'a') as f:
                f.write(f"\n{'='*50}\n")
                f.write(f"3D Printer Watchdog started at {datetime.now()}\n")
                f.write(f"{'='*50}\n")
        except Exception as e:
            print(f"Warning: Could not initialize log file: {e}")

    def log_message(self, message, level="INFO"):
        """Log a message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"

        # Write to file
        try:
            with open(LOG_FILENAME, 'a') as f:
                f.write(log_entry + "\n")
        except Exception as e:
            print(f"Warning: Could not write to log file: {e}")

        # Add to UI log
        self.log_queue.put(log_entry)

    # ========================================
    # UI CONSTRUCTION
    # ========================================

    def build_ui(self):
        """Build the modern scrollable user interface with vertical layout"""
        # Create main scrollable canvas
        main_canvas = tk.Canvas(self.root, bg=self.bg_primary, highlightthickness=0)
        main_scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        scrollable_frame = ttk.Frame(main_canvas, style="TFrame")

        # Configure scrolling
        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )

        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=main_scrollbar.set)

        # Pack canvas and scrollbar
        main_canvas.pack(side="left", fill="both", expand=True)
        main_scrollbar.pack(side="right", fill="y")

        # Configure grid weights for root
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Main content frame with padding
        main_frame = ttk.Frame(scrollable_frame, padding="20", style="TFrame")
        main_frame.pack(fill="both", expand=True)
        main_frame.columnconfigure(0, weight=1)

        # Modern title with StormHacks branding
        title_frame = ttk.Frame(main_frame, style="TFrame")
        title_frame.pack(fill="x", pady=(0, 25))
        title_frame.columnconfigure(1, weight=1)

        # Title icon (text-based)
        title_icon = ttk.Label(title_frame, text="🔧", font=("Segoe UI", 28), background=self.bg_primary)
        title_icon.grid(row=0, column=0, padx=(0, 15))

        # Main title with StormHacks branding
        title_label = ttk.Label(title_frame, text="Circuit Breakers StormHacks 2025",
                               font=("Segoe UI", 22, "bold"), foreground=self.accent_blue)
        title_label.grid(row=0, column=1, sticky=tk.W)

        subtitle_label = ttk.Label(title_frame, text="3D Printer Watchdog - AI-Powered Print Monitoring",
                                  font=("Segoe UI", 12), foreground=self.text_secondary)
        subtitle_label.grid(row=1, column=1, sticky=tk.W, pady=(5, 0))

        # CONTROLS SECTION - At the top
        control_card = ttk.LabelFrame(main_frame, text="🎮 Controls", padding="15", style="Card.TLabelframe")
        control_card.pack(fill="x", pady=(0, 20))
        control_card.columnconfigure(0, weight=1)
        control_card.columnconfigure(1, weight=1)
        control_card.columnconfigure(2, weight=1)

        # Row 1: Main action buttons
        self.capture_btn = ttk.Button(control_card, text="📸 Take Photo & Analyze Now",
                                     command=self.manual_capture, style="Primary.TButton")
        self.capture_btn.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.reload_config_btn = ttk.Button(control_card, text="🔄 Reload AI Config",
                                           command=self.reload_ai_config, style="Warning.TButton")
        self.reload_config_btn.grid(row=0, column=2, pady=(0, 10), sticky=(tk.W, tk.E), padx=(5, 0))

        # Row 2: Monitoring controls
        monitor_label = ttk.Label(control_card, text="Auto Monitoring:", font=("Segoe UI", 11, "bold"))
        monitor_label.grid(row=1, column=0, sticky=tk.W, pady=(0, 5))

        monitor_buttons = ttk.Frame(control_card, style="TFrame")
        monitor_buttons.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        monitor_buttons.columnconfigure(0, weight=1)
        monitor_buttons.columnconfigure(1, weight=1)

        self.start_btn = ttk.Button(monitor_buttons, text="▶️ Start Monitoring",
                                   command=self.start_monitoring, style="Success.TButton")
        self.start_btn.grid(row=0, column=0, padx=(0, 5), sticky=(tk.W, tk.E))

        self.stop_btn = ttk.Button(monitor_buttons, text="⏹️ Stop Monitoring",
                                  command=self.stop_monitoring, state="disabled", style="Danger.TButton")
        self.stop_btn.grid(row=0, column=1, padx=(5, 0), sticky=(tk.W, tk.E))

        # Row 3: Interval control
        interval_label = ttk.Label(control_card, text="Monitoring Interval:", font=("Segoe UI", 11, "bold"))
        interval_label.grid(row=3, column=0, sticky=tk.W, pady=(10, 5))

        interval_frame = ttk.Frame(control_card, style="TFrame")
        interval_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E))
        interval_frame.columnconfigure(0, weight=1)

        self.interval_var = tk.IntVar(value=DEFAULT_INTERVAL)
        self.interval_scale = ttk.Scale(interval_frame, from_=MIN_INTERVAL, to=MAX_INTERVAL,
                                       orient="horizontal", variable=self.interval_var,
                                       command=self.update_interval)
        self.interval_scale.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))

        self.interval_label = ttk.Label(interval_frame, text=f"{DEFAULT_INTERVAL}s", 
                                       font=("Segoe UI", 12, "bold"), foreground=self.accent_blue)
        self.interval_label.grid(row=0, column=1)

        # CAMERA SECTION - Bigger and in the middle
        image_card = ttk.LabelFrame(main_frame, text="📹 Live Camera Feed", padding="20", style="Card.TLabelframe")
        image_card.pack(fill="both", expand=True, pady=(0, 20))
        image_card.columnconfigure(0, weight=1)
        image_card.rowconfigure(0, weight=1)

        # Camera display frame
        camera_frame = ttk.Frame(image_card, style="TFrame")
        camera_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        camera_frame.columnconfigure(0, weight=1)
        camera_frame.rowconfigure(0, weight=1)

        # HUGE Live preview display - much bigger now with fixed minimum size
        self.image_label = ttk.Label(camera_frame,
                                    text="📹 Live Camera Preview\nInitializing...",
                                    background=self.bg_secondary,
                                    anchor="center",
                                    font=("Segoe UI", 24),
                                    foreground=self.text_secondary)
        self.image_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=20, pady=20)

        # Camera status at bottom
        self.preview_status_label = ttk.Label(image_card,
                                            text="⏳ Starting preview...",
                                            background=self.bg_secondary,
                                            anchor="center",
                                            font=("Segoe UI", 16, "bold"),
                                            foreground=self.accent_blue)
        self.preview_status_label.grid(row=1, column=0, pady=(20, 0))

        # AI ANALYSIS SECTION - Below camera
        ai_card = ttk.LabelFrame(main_frame, text="🤖 AI Analysis Results", padding="15", style="Card.TLabelframe")
        ai_card.pack(fill="both", expand=True, pady=(0, 20))
        ai_card.columnconfigure(0, weight=1)
        ai_card.rowconfigure(0, weight=1)

        # Larger AI text area
        self.ai_text = scrolledtext.ScrolledText(ai_card,
                                               wrap=tk.WORD,
                                               font=("Segoe UI", 12),
                                               bg=self.bg_tertiary,
                                               fg=self.text_primary,
                                               insertbackground=self.accent_blue,
                                               selectbackground=self.accent_blue,
                                               selectforeground="white",
                                               height=12)
        self.ai_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Clean initial message
        self.ai_text.insert(tk.END, "🤖 AI Analysis Ready\n")
        self.ai_text.insert(tk.END, "=" * 50 + "\n\n")
        self.ai_text.insert(tk.END, "Click '📸 Take Photo & Analyze Now' to get AI feedback on your 3D print!\n\n")
        self.ai_text.insert(tk.END, "The AI will analyze:\n")
        self.ai_text.insert(tk.END, "• Print quality and layer adhesion\n")
        self.ai_text.insert(tk.END, "• Visible defects or issues\n")
        self.ai_text.insert(tk.END, "• Bed adhesion and first layer quality\n")
        self.ai_text.insert(tk.END, "• Overall print progress and status\n")
        self.ai_text.insert(tk.END, "• Recommendations for improvement\n")
        self.ai_text.config(state=tk.DISABLED)

        # SYSTEM LOG SECTION - At the bottom
        log_card = ttk.LabelFrame(main_frame, text="📋 System Log", padding="10", style="Card.TLabelframe")
        log_card.pack(fill="both", expand=True, pady=(0, 20))
        log_card.columnconfigure(0, weight=1)
        log_card.rowconfigure(0, weight=1)

        # System log area
        self.log_text = scrolledtext.ScrolledText(log_card,
                                                 wrap=tk.WORD,
                                                 font=("Consolas", 10),
                                                 bg=self.bg_tertiary,
                                                 fg=self.text_primary,
                                                 insertbackground=self.accent_blue,
                                                 selectbackground=self.accent_blue,
                                                 selectforeground="white",
                                                 height=8)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # STATUS BAR - At the very bottom
        status_frame = ttk.Frame(main_frame, style="TFrame")
        status_frame.pack(fill="x", pady=(20, 0))

        status_icon = ttk.Label(status_frame, text="🟢", font=("Segoe UI", 16), background=self.bg_primary)
        status_icon.pack(side="left", padx=(0, 10))

        self.status_var = tk.StringVar(value="🟢 System Ready - Live Preview Active")
        status_label = ttk.Label(status_frame, textvariable=self.status_var,
                               font=("Segoe UI", 14), foreground=self.text_primary, background=self.bg_primary)
        status_label.pack(side="left")

        # Initialize log with welcome message
        self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 System initialized with new scrollable layout\n")
        self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] 📹 Live preview starting...\n")
        self.log_text.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] 🎮 Controls moved to top, camera enlarged, AI log below\n")

        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind mouse wheel to canvas
        main_canvas.bind("<MouseWheel>", _on_mousewheel)  # Windows
        main_canvas.bind("<Button-4>", lambda e: main_canvas.yview_scroll(-1, "units"))  # Linux
        main_canvas.bind("<Button-5>", lambda e: main_canvas.yview_scroll(1, "units"))   # Linux

        # Start live preview automatically
        self.log_message("🚀 Starting 3D Printer Watchdog with live preview...")
        self.update_preview_status("⏳ Initializing camera...")
        self.start_preview()

    def update_interval(self, value):
        """Update interval display when slider changes"""
        interval = int(float(value))
        self.interval_label.config(text=f"{interval}s")
        self.capture_interval = interval

    def update_preview_status(self, status_text):
        """Update the preview status label"""
        if hasattr(self, 'preview_status_label'):
            self.preview_status_label.config(text=status_text)

    def update_ui_loop(self):
        """Main UI update loop - runs in main thread"""
        try:
            # Process log messages
            while not self.log_queue.empty():
                message = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, message + "\n")
                self.log_text.see(tk.END)

            # Process capture results
            if not self.capture_queue.empty():
                result = self.capture_queue.get_nowait()
                if result["success"]:
                    self.display_image(result["image_path"])
                else:
                    self.log_message(f"Camera capture failed: {result['error']}", "ERROR")

            # Process AI results
            if not self.ai_queue.empty():
                result = self.ai_queue.get_nowait()
                self.display_ai_result(result)

            # Process preview results
            if not self.preview_queue.empty():
                result = self.preview_queue.get_nowait()
                if result["success"]:
                    self.display_preview(result["image_path"])

            # Update status (only if not already set by other operations)
            current_status_text = self.status_var.get()
            if not current_status_text.startswith("📸") and not current_status_text.startswith("✅"):
                self.status_var.set(f"{self.current_status}")

        except Exception as e:
            self.log_message(f"UI update error: {e}", "ERROR")

        # Schedule next update
        self.root.after(100, self.update_ui_loop)

    # ========================================
    # CAMERA CAPTURE
    # ========================================

    def manual_capture(self):
        """Manually trigger an instant camera capture"""
        self.current_status = "📸 Taking Photo..."
        self.log_message("📸 Manual capture started")
        
        # Update UI immediately to show we're capturing
        self.status_var.set("📸 Taking Photo...")
        self.root.update_idletasks()
        
        # Signal preview to pause and wait a moment for it to release camera
        self.pause_preview_event.set()
        
        # Capture photo with camera coordination
        self.capture_photo_coordinated()

    def capture_photo_coordinated(self):
        """Capture a photo with proper camera resource coordination"""
        def coordinated_capture_worker():
            try:
                # Wait for preview to pause (give it up to 2 seconds)
                time.sleep(1.0)  # Give preview more time to pause and release camera
                
                # Acquire camera lock
                with self.camera_lock:
                    
                    # Use a different command for manual capture to avoid conflicts
                    capture_cmd = ["rpicam-jpeg", "--nopreview", "--immediate", 
                                 "--timeout", "1000", "-o", CAPTURE_FILENAME, 
                                 "--width", "1920", "--height", "1440"]
                    
                    # Run camera command with shorter timeout for instant capture
                    result = subprocess.run(capture_cmd, capture_output=True, text=True, timeout=8)

                    if result.returncode == 0:
                        self.log_message("📸 Photo captured - analyzing...")
                        
                        # Update preview status to show we're analyzing the captured image
                        self.update_preview_status("📸 Analyzing captured image...")
                        
                        self.capture_queue.put({
                            "success": True,
                            "image_path": CAPTURE_FILENAME
                        })

                        # Start AI analysis
                        self.analyze_image(CAPTURE_FILENAME)

                    else:
                        error_msg = result.stderr.strip() or "Unknown camera error"
                        self.log_message(f"❌ Camera capture failed: {error_msg}", "ERROR")
                        self.capture_queue.put({
                            "success": False,
                            "error": error_msg
                        })

            except subprocess.TimeoutExpired:
                self.log_message("⏰ Camera capture timed out", "ERROR")
                self.capture_queue.put({
                    "success": False,
                    "error": "Camera capture timed out"
                })
            except Exception as e:
                self.log_message(f"❌ Capture error: {e}", "ERROR")
                self.capture_queue.put({
                    "success": False,
                    "error": str(e)
                })
            finally:
                # Resume preview
                self.pause_preview_event.clear()
                if not self.monitoring_active:
                    self.current_status = "🟢 System Ready - Live Preview Active"

        # Run capture in background thread
        thread = threading.Thread(target=coordinated_capture_worker, daemon=True)
        thread.start()

    def capture_photo(self):
        """Capture a photo using rpicam-jpeg (for monitoring mode)"""
        def capture_worker():
            try:
                # Wait a moment for preview to pause
                time.sleep(0.3)
                
                # Acquire camera lock
                with self.camera_lock:
                    # Run camera command with shorter timeout for instant capture
                    result = subprocess.run(CAPTURE_COMMAND, capture_output=True, text=True, timeout=5)

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
                        self.log_message(f"❌ Camera capture failed: {error_msg}", "ERROR")
                        self.capture_queue.put({
                            "success": False,
                            "error": error_msg
                        })

            except subprocess.TimeoutExpired:
                self.log_message("⏰ Camera capture timed out", "ERROR")
                self.capture_queue.put({
                    "success": False,
                    "error": "Camera capture timed out"
                })
            except Exception as e:
                self.log_message(f"❌ Capture error: {e}", "ERROR")
                self.capture_queue.put({
                    "success": False,
                    "error": str(e)
                })
            finally:
                # Resume preview
                self.pause_preview_event.clear()
                if not self.monitoring_active:
                    self.current_status = "🟢 System Ready - Live Preview Active"

        # Run capture in background thread
        thread = threading.Thread(target=capture_worker, daemon=True)
        thread.start()

    def display_image(self, image_path):
        """Display captured image in UI"""
        try:
            # Load image with PIL
            image = Image.open(image_path)

            # Get window dimensions for responsive sizing
            self.root.update_idletasks()
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()
            
            # Calculate available space for image (leave room for controls)
            available_width = int(window_width * 0.8)  # 80% of window width
            available_height = int(window_height * 0.5)  # 50% of window height
            
            # Minimum size to prevent shrinking too much
            min_width, min_height = 640, 480
            display_width = max(available_width, min_width)
            display_height = max(available_height, min_height)

            # Calculate scaling to fit without cropping (maintain aspect ratio)
            img_width, img_height = image.size
            scale_w = display_width / img_width
            scale_h = display_height / img_height
            scale = min(scale_w, scale_h) * 0.9  # 90% to leave some padding

            # Resize image
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Convert to PhotoImage for tkinter
            photo = ImageTk.PhotoImage(image)

            # Update display with indicator that this is a captured image
            self.image_label.config(image=photo, text="")
            self.image_label.image = photo  # Keep reference
            self.current_image = photo
            
            # Update status to show this is the captured image being analyzed
            self.update_preview_status("📸 Captured Image (being analyzed by AI)")

        except Exception as e:
            self.log_message(f"Error displaying image: {e}", "ERROR")
            self.image_label.config(text=f"Error loading image:\n{e}", image="")

    # ========================================
    # AI ANALYSIS
    # ========================================

    def analyze_image(self, image_path):
        """Analyze image with AI or fallback to basic analysis"""
        if not os.path.exists(image_path):
            self.log_message(f"Image file not found: {image_path}", "ERROR")
            return

        def ai_worker():
            try:
                pass  # Removed verbose message

                # Try Google Gemini API first (free tier available)
                if GEMINI_API_KEY and GEMINI_API_KEY != "your_gemini_api_key_here":
                    try:
                        # Read and encode image
                        with open(image_path, "rb") as f:
                            image_data = f.read()
                        image_b64 = base64.b64encode(image_data).decode('utf-8')

                        # Prepare Gemini API request
                        headers = {
                            "Content-Type": "application/json"
                        }

                        # Get settings from config file
                        gemini_settings = self.ai_config.get("gemini_settings", {})
                        prompt_text = gemini_settings.get("prompt", "Look at this image and describe what you see.")
                        
                        payload = {
                            "contents": [{
                                "parts": [
                                    {
                                        "text": prompt_text
                                    },
                                    {
                                        "inline_data": {
                                            "mime_type": "image/jpeg",
                                            "data": image_b64
                                        }
                                    }
                                ]
                            }],
                            "generationConfig": {
                                "temperature": gemini_settings.get("temperature", 0.7),
                                "maxOutputTokens": gemini_settings.get("max_output_tokens", 100),
                                "topP": gemini_settings.get("top_p", 0.8),
                                "topK": gemini_settings.get("top_k", 40)
                            }
                        }

                        # Make API call with configurable timeout
                        api_url = f"{GEMINI_API_URL}?key={GEMINI_API_KEY}"
                        timeout = self.ai_config.get("analysis_settings", {}).get("timeout_seconds", 20)
                        response = requests.post(api_url, headers=headers, json=payload, timeout=timeout)

                        if response.status_code == 200:
                            result = response.json()
                            
                            # Debug logging if enabled
                            if self.ai_config.get("ui_settings", {}).get("log_ai_requests", False):
                                self.log_message(f"🔍 Full Gemini API response: {result}")
                            
                            try:
                                # Check if we have candidates and content
                                if "candidates" in result and len(result["candidates"]) > 0:
                                    candidate = result["candidates"][0]
                                    
                                    # Handle different finish reasons
                                    finish_reason = candidate.get("finishReason", "")
                                    if finish_reason == "MAX_TOKENS":
                                        self.log_message("⚠️ Gemini response was truncated due to token limit", "WARNING")
                                    
                                    # Try to extract content even if truncated
                                    if "content" in candidate:
                                        content = candidate["content"]
                                        if "parts" in content and len(content["parts"]) > 0:
                                            # Look for text in any part
                                            analysis_text = ""
                                            for part in content["parts"]:
                                                if "text" in part:
                                                    analysis_text += part["text"]
                                            
                                            if analysis_text.strip():
                                                # Add note if truncated
                                                if finish_reason == "MAX_TOKENS":
                                                    analysis_text += "\n\n[Note: Response was truncated due to length limits]"
                                                
                                                self.ai_queue.put({
                                                    "success": True,
                                                    "description": analysis_text.strip(),
                                                    "timestamp": datetime.now()
                                                })
                                                return
                                    
                                    # Don't use fallback - if we can't get real content, it's an error
                                    pass

                                # If we get here, the response structure is unexpected
                                self.log_message(f"Unexpected Gemini API response structure: {result}", "WARNING")
                                
                                # Try to provide a helpful fallback message
                                fallback_msg = "⚠️ AI analysis failed due to unexpected response format."
                                if finish_reason == "MAX_TOKENS":
                                    fallback_msg += " The response was truncated - consider increasing max_output_tokens in ai_config.json."
                                
                                self.ai_queue.put({
                                    "success": True,
                                    "description": fallback_msg,
                                    "timestamp": datetime.now()
                                })

                            except Exception as e:
                                self.log_message(f"Gemini API response parsing failed: {e}", "WARNING")
                                pass

                    except Exception as e:
                        # If Gemini API fails, log the error and continue to fallback
                        self.log_message(f"Google Gemini API failed: {e}", "WARNING")
                        pass

                # No fallback - only real AI or error

            except Exception as e:
                self.ai_queue.put({
                    "success": False,
                    "error": f"Analysis error: {e}"
                })

        # Run analysis in background thread
        thread = threading.Thread(target=ai_worker, daemon=True)
        thread.start()

    def display_ai_result(self, result):
        """Display AI analysis result in dedicated AI area"""
        if result["success"]:
            description = result["description"]
            timestamp = result["timestamp"].strftime("%H:%M:%S")
            
            # Clear previous content and add new analysis
            self.ai_text.config(state=tk.NORMAL)
            self.ai_text.delete(1.0, tk.END)
            
            # Add header
            self.ai_text.insert(tk.END, f"🤖 AI Analysis - {timestamp}\n")
            self.ai_text.insert(tk.END, "=" * 35 + "\n\n")
            
            # Add the analysis content
            self.ai_text.insert(tk.END, f"{description}\n\n")
            
            # Add footer
            self.ai_text.insert(tk.END, "─" * 35 + "\n")
            self.ai_text.insert(tk.END, "💡 Click 'Take Photo & Analyze Now' for a new analysis\n")
            
            self.ai_text.see(tk.END)
            self.ai_text.config(state=tk.DISABLED)
            
            # Return to live preview after 3 seconds
            self.root.after(3000, lambda: self.update_preview_status("📹 Live preview resumed"))
            
            # Only log a brief success message to technical log
            self.log_message("✅ AI analysis completed")

            # Update status bar temporarily with analysis
            original_status = self.current_status
            self.current_status = "✅ AI Analysis Complete"
            self.status_var.set(f"✅ AI Analysis Complete")

            # Reset status after 3 seconds
            def reset_status():
                self.current_status = original_status
                self.status_var.set(f"{original_status}")

            self.root.after(3000, reset_status)

        else:
            # Add error to AI area
            self.ai_text.config(state=tk.NORMAL)
            self.ai_text.delete(1.0, tk.END)
            self.ai_text.insert(tk.END, "❌ AI Analysis Error\n")
            self.ai_text.insert(tk.END, "=" * 25 + "\n\n")
            self.ai_text.insert(tk.END, f"Error: {result['error']}\n\n")
            self.ai_text.insert(tk.END, "Please try again or check your API key.\n")
            self.ai_text.see(tk.END)
            self.ai_text.config(state=tk.DISABLED)
            
            self.log_message(f"❌ AI analysis failed: {result['error']}", "ERROR")

    def toggle_preview(self):
        """Start or stop live camera preview"""
        if self.preview_active:
            self.stop_preview()
        else:
            self.start_preview()

    def start_preview(self):
        """Start live camera preview"""
        if self.preview_active and hasattr(self, 'preview_thread') and self.preview_thread and self.preview_thread.is_alive():
            return

        self.preview_active = True
        self.current_status = "👁️ Live Preview Active"

        # Update status label
        self.update_preview_status("🔄 Starting preview thread...")

        # Start preview thread
        self.preview_thread = threading.Thread(target=self.preview_worker, daemon=True)
        self.preview_thread.start()

        self.log_message("👁️ Live camera preview thread started")

    def stop_preview(self):
        """Stop live camera preview (disabled - preview always runs)"""
        # Preview is always active now - don't actually stop it
        # Just update status if needed
        if self.preview_active:
            self.current_status = "🟢 System Ready - Live Preview Active"

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
                        # Capture preview frame with shorter timeout for responsiveness
                        result = subprocess.run(PREVIEW_COMMAND, capture_output=True, timeout=1)
                    finally:
                        self.camera_lock.release()
                else:
                    # Camera is busy, wait a bit
                    time.sleep(0.2)
                    continue

                if result.returncode == 0 and result.stdout:
                    # Save stdout to preview file
                    with open(PREVIEW_FILENAME, "wb") as f:
                        f.write(result.stdout)

                    frame_count += 1
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
                    self.log_message(f"⚠️ Preview capture failed: returncode={result.returncode}, stdout_size={len(result.stdout)}")

                # Wait a bit before next frame (roughly 2-3 FPS)
                time.sleep(0.3)

            except subprocess.TimeoutExpired:
                self.log_message("⚠️ Preview capture timed out")
                continue
            except Exception as e:
                self.log_message(f"⚠️ Preview error: {e}")
                time.sleep(1)

    def display_preview(self, image_path):
        """Display preview frame in UI"""
        try:
            # Load image with PIL
            image = Image.open(image_path)

            # Get window dimensions for responsive sizing - same logic as display_image
            self.root.update_idletasks()
            window_width = self.root.winfo_width()
            window_height = self.root.winfo_height()
            
            # Calculate available space for image (leave room for controls)
            available_width = int(window_width * 0.8)  # 80% of window width
            available_height = int(window_height * 0.5)  # 50% of window height
            
            # Minimum size to prevent shrinking too much
            min_width, min_height = 640, 480
            display_width = max(available_width, min_width)
            display_height = max(available_height, min_height)

            # Calculate scaling to fit without cropping (maintain aspect ratio)
            img_width, img_height = image.size
            scale_w = display_width / img_width
            scale_h = display_height / img_height
            scale = min(scale_w, scale_h) * 0.9  # 90% to leave some padding

            # Resize image
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Convert to PhotoImage for tkinter
            photo = ImageTk.PhotoImage(image)

            # Update display and keep reference for preview
            self.image_label.config(image=photo, text="")
            self.image_label.image = photo  # Keep reference to prevent garbage collection

            # Debug log (only occasionally to avoid spam)
            if hasattr(self, '_preview_display_count'):
                self._preview_display_count += 1
            else:
                self._preview_display_count = 1

            if self._preview_display_count % 100 == 0:  # Log every 100th frame
                self.log_message(f"🖼️ Display: {self._preview_display_count} frames shown")

        except Exception as e:
            # Log preview display errors (but not too frequently)
            if hasattr(self, '_preview_error_count'):
                self._preview_error_count += 1
            else:
                self._preview_error_count = 1

            if self._preview_error_count % 5 == 0:  # Log every 5th error
                self.log_message(f"⚠️ Preview display error: {e}")

    # ========================================
    # MONITORING CONTROL
    # ========================================

    def start_monitoring(self):
        """Start automatic monitoring"""
        if self.monitoring_active:
            return

        # Keep preview running - monitoring works alongside it
        self.monitoring_active = True
        self.stop_event.clear()

        # Update UI
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.current_status = "▶️ AI Monitoring Active - Taking Photos Every " + str(self.capture_interval) + "s"

        # Start timer thread
        self.timer_thread = threading.Thread(target=self.monitoring_timer, daemon=True)
        self.timer_thread.start()

        self.log_message("🤖 AI-powered automatic monitoring started (live preview continues)")

    def stop_monitoring(self):
        """Stop automatic monitoring"""
        if not self.monitoring_active:
            return

        self.monitoring_active = False
        self.stop_event.set()

        # Update UI
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.current_status = "👁️ Live Preview Active"

        self.log_message("⏹️ AI monitoring stopped (live preview continues)")

    def monitoring_timer(self):
        """Timer thread for automatic captures"""
        while not self.stop_event.is_set():
            # Capture photo using coordinated method
            self.current_status = "📸 Auto Capturing..."
            self.log_message("🤖 Automatic capture triggered...")
            
            # Signal preview to pause
            self.pause_preview_event.set()
            
            # Use the regular capture method for monitoring (simpler)
            self.capture_photo()

            # Wait for interval or stop event
            for _ in range(self.capture_interval):
                if self.stop_event.is_set():
                    break
                time.sleep(1)

    def on_closing(self):
        """Handle window close event"""
        self.stop_monitoring()
        self.root.destroy()

# ========================================
# MAIN ENTRY POINT
# ========================================

def test_camera():
    """Test camera functionality independently"""
    print("🧪 Testing camera functionality...")
    
    # First check if camera is detected by system
    try:
        result = subprocess.run(["vcgencmd", "get_camera"], capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            output = result.stdout.strip()
            print(f"📋 Camera status: {output}")
            if "detected=0" in output:
                print("❌ No camera detected by system")
                print("   Please check camera connection and enable with: sudo raspi-config")
                return False
        else:
            print("⚠️ Could not check camera status")
    except Exception as e:
        print(f"⚠️ Error checking camera status: {e}")

    # Test camera command
    PREVIEW_COMMAND = ["rpicam-jpeg", "--nopreview", "--output", "-", "--timeout", "500", "--width", "640", "--height", "480"]

    try:
        print("📷 Attempting to capture test frame...")
        result = subprocess.run(PREVIEW_COMMAND, capture_output=True, timeout=3)

        if result.returncode == 0 and result.stdout:
            print(f"✅ Camera working! Captured {len(result.stdout)} bytes of image data")
            return True
        else:
            print(f"❌ Camera failed: returncode={result.returncode}")
            if result.stderr:
                print(f"Error output: {result.stderr.decode()}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ Camera timed out")
        return False
    except FileNotFoundError:
        print("❌ rpicam-jpeg command not found. Is the camera enabled?")
        return False
    except Exception as e:
        print(f"❌ Camera error: {e}")
        return False

def main():
    """Main application entry point"""
    print("🚀 Starting 3D Printer Watchdog...")

    # Check dependencies
    try:
        import requests
        import PIL
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Install with: pip install requests pillow")
        return

    # Create and run application
    print("🖥️  Starting GUI...")
    root = tk.Tk()
    app = PrinterWatchdogApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
