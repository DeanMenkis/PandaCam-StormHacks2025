#!/usr/bin/env python3
"""
Minimal test version - GUI only, no camera
"""

import tkinter as tk
from tkinter import ttk
import threading
import time

class TestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Test - Circuit Breakers StormHacks 2025")
        self.root.geometry("800x600")
        
        # Simple UI
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        title_label = ttk.Label(main_frame, text="🎯 3D Printer Watchdog - Test Mode", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, pady=20)
        
        status_label = ttk.Label(main_frame, text="✅ GUI is working! Camera disabled for testing.", 
                                font=("Arial", 12))
        status_label.grid(row=1, column=0, pady=10)
        
        test_button = ttk.Button(main_frame, text="Test Button", 
                                command=lambda: print("Button clicked!"))
        test_button.grid(row=2, column=0, pady=10)
        
        close_button = ttk.Button(main_frame, text="Close", 
                                 command=self.root.destroy)
        close_button.grid(row=3, column=0, pady=10)
        
        print("✅ Test GUI created successfully")

def main():
    print("🧪 Starting GUI-only test...")
    root = tk.Tk()
    app = TestApp(root)
    print("🚀 Starting mainloop...")
    root.mainloop()
    print("👋 GUI closed")

if __name__ == "__main__":
    main()

