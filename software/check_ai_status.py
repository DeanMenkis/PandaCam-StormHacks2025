#!/usr/bin/env python3
"""
Check AI analysis status and history
"""

import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_ai_status():
    """Check the current AI status and recent history"""
    
    print("🤖 AI Analysis Status Check")
    print("=" * 50)
    
    # Check if history file exists
    history_file = "ai_history/history.json"
    if os.path.exists(history_file):
        print(f"📁 History file found: {history_file}")
        
        try:
            with open(history_file, 'r') as f:
                history = json.load(f)
            
            print(f"📊 Total history entries: {len(history)}")
            
            if history:
                # Show last 5 entries
                print(f"\n📋 Last 5 AI Analyses:")
                print("-" * 80)
                
                for i, entry in enumerate(history[-5:]):
                    print(f"\n{i+1}. Entry ID: {entry.get('id', 'N/A')}")
                    print(f"   Timestamp: {entry.get('timestamp', 'N/A')}")
                    print(f"   Success: {entry.get('success', 'N/A')}")
                    print(f"   Print Status: {entry.get('print_status', 'N/A')}")
                    print(f"   Binary Status: {entry.get('binary_status', 'N/A')} ({'✅ GOOD' if entry.get('binary_status') == 1 else '❌ BAD' if entry.get('binary_status') == 0 else '❓ UNKNOWN'})")
                    print(f"   Confidence: {entry.get('confidence', 'N/A')}")
                    print(f"   Gemini Response: {entry.get('gemini_response', 'N/A')[:100]}...")
                    
                    # Check if this would have triggered an alert
                    if entry.get('binary_status') == 0:
                        print(f"   🚨 ALERT TRIGGER: This analysis would have sent an alert!")
                    else:
                        print(f"   ✅ No alert: Binary status = {entry.get('binary_status')}")
                
                # Count alerts that should have been sent
                alert_count = sum(1 for entry in history if entry.get('binary_status') == 0)
                print(f"\n📈 Summary:")
                print(f"   Total analyses: {len(history)}")
                print(f"   Analyses that should have triggered alerts: {alert_count}")
                print(f"   Success rate: {sum(1 for entry in history if entry.get('success')) / len(history) * 100:.1f}%")
                
            else:
                print("📭 No history entries found")
                
        except Exception as e:
            print(f"❌ Error reading history: {e}")
    else:
        print(f"❌ History file not found: {history_file}")
        print("   This means no AI analyses have been performed yet.")
    
    # Check current AI status via API
    print(f"\n🌐 Checking current AI status via API...")
    try:
        import requests
        response = requests.get('http://localhost:8000/api/ai/status', timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                ai_status = data['data']
                print(f"✅ AI Status API Response:")
                print(f"   AI Monitoring Active: {ai_status.get('ai_monitoring_active', 'N/A')}")
                print(f"   AI Monitoring Paused: {ai_status.get('ai_monitoring_paused', 'N/A')}")
                print(f"   Process Status: {ai_status.get('ai_process_status', 'N/A')}")
                print(f"   Last AI Analysis: {ai_status.get('last_ai_analysis', 'N/A')}")
                print(f"   AI Response: {ai_status.get('ai_response', 'N/A')[:100]}...")
                print(f"   Binary Status: {ai_status.get('ai_binary_status', 'N/A')} ({'✅ GOOD' if ai_status.get('ai_binary_status') == 1 else '❌ BAD' if ai_status.get('ai_binary_status') == 0 else '❓ UNKNOWN'})")
                print(f"   Confidence: {ai_status.get('ai_confidence', 'N/A')}")
                print(f"   Analysis Count: {ai_status.get('ai_analysis_count', 'N/A')}")
                print(f"   Success Rate: {ai_status.get('ai_success_rate', 'N/A')}")
                print(f"   Monitoring Interval: {ai_status.get('monitoring_interval', 'N/A')} seconds")
            else:
                print(f"❌ API returned error: {data.get('error', 'Unknown error')}")
        else:
            print(f"❌ API request failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error checking API: {e}")
        print("   Make sure the Flask app is running on localhost:8000")

if __name__ == "__main__":
    check_ai_status()
