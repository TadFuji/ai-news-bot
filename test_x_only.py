import os
import json
import glob
from dotenv import load_dotenv
from config import NEWS_BOT_OUTPUT_DIR
from distribute_daily import get_latest_report, post_to_x_single

# Load Env
load_dotenv()

def main():
    print("🧪 Starting X-Only Distribution Test...")
    
    report_path = get_latest_report()
    if not report_path:
        print("❌ No report found to distribute.")
        return

    print(f"📄 Loading report: {report_path}")
    with open(report_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    articles = data.get("articles", [])
    if not articles:
        print("⚠️ No articles in report.")
        return

    # Skip LINE, only X
    print("📡 Distribution to X started (LINE skipped)...")
    try:
        post_to_x_single(articles)
        print("✅ X Distribution Test Complete.")
    except Exception as e:
        print(f"❌ Error sending to X: {e}")

if __name__ == "__main__":
    main()
