import time
import subprocess
import sys
from datetime import datetime

# Interval in seconds (4 hours)
INTERVAL = 60 * 60 * 4

def run_sentinel():
    print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 🕵️ Sentinel Mode: Checking news...")
    
    try:
        # Run main.py in sentinel mode
        # Using sys.executable to ensure we use the same python interpreter
        cmd = [sys.executable, "main.py", "--mode", "sentinel"]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        # Output the stdout/stderr
        print(result.stdout)
        if result.stderr:
            print("⚠️ Errors:", result.stderr)
            
    except Exception as e:
        print(f"❌ Error in sentinel execution: {e}")

def main():
    print("🚀 Marketing Engine: Sentinel Mode Started")
    print(f"⏱️  Interval: {INTERVAL} seconds")
    print("Press Ctrl+C to stop.")
    
    while True:
        run_sentinel()
        
        print(f"zzz Sleeping for {INTERVAL} seconds...")
        time.sleep(INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n🛑 Sentinel Mode stopped by user.")
