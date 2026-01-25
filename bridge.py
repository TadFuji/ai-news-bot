import os
import json
import glob
import re
import datetime

# Paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Assumes AI_TOOL_NEWS is a sibling directory
CLOUD_REPO_DIR = os.path.join(os.path.dirname(CURRENT_DIR), "AI_TOOL_NEWS")
REPORTS_DIR = os.path.join(CLOUD_REPO_DIR, "reports")
OUTPUT_DIR = os.path.join(CURRENT_DIR, "output")

def parse_markdown_report(filepath):
    """Parses a single markdown report from the new system."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Title is usually the first line "# Title"
    title_match = re.search(r'^# (.*)', content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "No Title"

    # Category extraction (from filename or content)
    # The new system writes "# Category - Daily Report" for tool updates
    # And "# Title" for RSS.
    # Let's try to find tool name.
    
    # Tool Name for "Tool Reports" is often "## ToolName"
    tool_match = re.search(r'^## (.*)', content, re.MULTILINE)
    tool_name = tool_match.group(1).strip() if tool_match else ""
    
    if tool_name:
        # It's a tool update, maybe prepend tool name to title
        if title.endswith("Daily Report"):
            title = f"【{tool_name}】Update Detected"
        else:
             title = f"【{tool_name}】{title}"

    # Summary
    summary_match = re.search(r'\*\*Summary\*\*:? (.*)', content)
    summary = ""
    if summary_match:
        summary = summary_match.group(1).strip().replace("**", "")
    else:
        # Fallback to body scan if standard format differs
        # The RSS script writes "## Summary\nContent"
        summary_section = re.split(r'## Summary', content)
        if len(summary_section) > 1:
            summary = summary_section[1].strip()

    # URL
    url_match = re.search(r'\*\*URL\*\*:? (.*)', content)
    url = url_match.group(1).strip() if url_match else ""

    if not summary:
        return None

    return {
        "title_ja": title,
        "summary_ja": summary,
        "url": url,
        "source": "Cloud_Sync"
    }

def main():
    print("=== Bridge System: Syncing Cloud Data to Cockpit ===")
    
    # 1. Determine Today / Yesterday (JST)
    JST = datetime.timezone(datetime.timedelta(hours=9))
    now = datetime.datetime.now(JST)
    today_str = now.strftime("%Y-%m-%d")
    yesterday_str = (now - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    
    print(f"Target Dates: {today_str}, {yesterday_str}")
    print(f"Scanning: {REPORTS_DIR}")

    # 2. Gather Markdown Files
    target_files = []
    
    # Scan Today and Yesterday
    for d in [today_str, yesterday_str]:
        day_path = os.path.join(REPORTS_DIR, d)
        if os.path.exists(day_path):
            # Tool Reports
            target_files.extend(glob.glob(os.path.join(day_path, "*.md")))
            # General News (RSS)
            target_files.extend(glob.glob(os.path.join(day_path, "general_news", "*.md")))

    print(f"Found {len(target_files)} raw reports.")
    
    articles = []
    for fp in target_files:
        try:
            item = parse_markdown_report(fp)
            if item:
                articles.append(item)
        except Exception as e:
            print(f"Skipping {os.path.basename(fp)}: {e}")

    if not articles:
        print("No articles found to sync.")
        return

    # 3. Save as JSON for Cockpit
    # Filename must be sortable by name to be picked up as "latest"
    # app.py sorts by getmtime, but let's make it look standard
    # Using a timestamp ensures it looks new
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    output_filename = f"cloud_synced_{timestamp}.json"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
        
    print(f"✅ Synced {len(articles)} articles to {output_filename}")
    print("Cockpit is ready to launch.")

if __name__ == "__main__":
    main()
