#!/usr/bin/env python3
"""
Start the web monitor for the RPG bot
"""
import subprocess
import sys
import os

def main():
    try:
        # Start the web monitor
        print("🖥️ Starting RPG Bot Web Monitor...")
        print("📊 Dashboard will be available at: http://localhost:8002")
        print("🔄 Dashboard auto-refreshes every 30 seconds")
        print("Press Ctrl+C to stop")
        
        subprocess.run([
            sys.executable, "web_monitor.py"
        ], cwd="/app/backend")
        
    except KeyboardInterrupt:
        print("\n👋 Monitor stopped")
    except Exception as e:
        print(f"❌ Error starting monitor: {e}")

if __name__ == "__main__":
    main()