import os
import json
import time
import datetime
import requests
import re

# Configuration
def load_api_key():
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith("XAI_API_KEY="):
                    return line.strip().split("=")[1]
    return os.environ.get("XAI_API_KEY")

API_KEY = load_api_key()
# Crucial: Use Agent Endpoint and Grok-4 family for server-side x_search
API_URL = "https://api.x.ai/v1/responses"
MODEL = "grok-4-1-fast-non-reasoning" 

TARGETS_FILE = "targets.json"
BASE_REPORT_DIR = "reports"

def setup_report_dir():
    """Creates a directory for today's reports."""
    # TIMEZONE FIX: GitHub Actions runs in UTC. Force JST (UTC+9)
    JST = datetime.timezone(datetime.timedelta(hours=9))
    today = datetime.datetime.now(JST).strftime("%Y-%m-%d")
    path = os.path.join(BASE_REPORT_DIR, today)
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def load_targets():
    """Loads the monitoring targets from JSON."""
    with open(TARGETS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_ai_news(tool_name, accounts):
    """
    Queries xAI Agent API to autonomously search X and report news.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    JST = datetime.timezone(datetime.timedelta(hours=9))
    current_date = datetime.datetime.now(JST).strftime("%Y-%m-%d")
    accounts_str = ", ".join(accounts)
    
    # Prompt optimized for Agentic execution
    prompt = (
        f"Role: Expert AI News Reporter using real-time X data.\n"
        f"Task: Search for the LATEST significant updates from {accounts_str} within the last 3 days.\n"
        f"Current Date: {current_date}\n\n"
        "STEPS:\n"
        "1. USE x_search to find posts from these accounts.\n"
        "2. FILTER for: New Models, Feature Launches, API Updates, or Strategic Partnerships.\n"
        "3. IGNORE: Replies, memes, maintenance, or generic hype.\n"
        "4. OUTPUT: If valid news is found, output in this format:\n"
        "- **Date**: YYYY-MM-DD HH:MM (Important: Include specific time from the post)\n"
        "- **URL**: (The specific tweet URL found via search)\n"
        "- **Summary**: (Detailed Japanese summary covering all key information)\n"
        "- **Why**: (Impact analysis)\n"
        "If NO significant news is found, output exactly: 'No significant news found'."
    )

    # Native Tool Definition for Server-Side Execution
    tools = [{"type": "x_search"}]

    payload = {
        "input": prompt,
        "model": MODEL,
        "stream": False,
        "temperature": 0.0,
        "tools": tools,
        "tool_choice": "auto"
    }

    try:
        # Retry logic for stability
        for attempt in range(3):
            try:
                response = requests.post(API_URL, headers=headers, data=json.dumps(payload), timeout=60)
                if response.status_code == 200:
                    data = response.json()
                    # Parse specific /v1/responses format
                    outputs = data.get('output', [])
                    for item in reversed(outputs): 
                        if item.get('role') == 'assistant' and 'content' in item:
                            content_list = item['content']
                            full_text = ""
                            for part in content_list:
                                if part.get('type') == 'output_text':
                                    full_text += part.get('text', "")
                            
                            # CLEANING: Remove Grok's citation markers [[1]](url) or just [[1]]
                            # Use regex to strip pattern content
                            clean_text = re.sub(r'\[\[\d+\]\](?:\([^)]+\))?', '', full_text)
                            return clean_text.strip()
                    return "Error: No text content in agent response."
                elif response.status_code == 429:
                    time.sleep(5) # Wait for rate limit
                    continue
                else:
                    return f"Error: {response.status_code} - {response.text}"
            except requests.exceptions.Timeout:
                print("Request timed out, retrying...")
                continue
        return "Error: Failed after 3 retries"

    except Exception as e:
        return f"Exception: {str(e)}"


import concurrent.futures
import threading

# Circuit Breaker Globals
FAILURE_COUNTER = 0
FAILURE_THRESHOLD = 5
FAILURE_LOCK = threading.Lock()

def process_tool(category_name, tool, report_dir):
    """Worker function for parallel execution."""
    global FAILURE_COUNTER
    
    # Circuit Breaker Check
    with FAILURE_LOCK:
        if FAILURE_COUNTER >= FAILURE_THRESHOLD:
            return None # Skip silently if breaker is open

    name = tool['name']
    accounts = tool['accounts']
    
    print(f"🔍 Checking {name}...")
    
    try:
        news_content = get_ai_news(name, accounts)
        
        # Success Logic
        if "Error:" in news_content or not news_content.strip():
             print(f"  ❌ {name}: Failed/Empty")
             with FAILURE_LOCK:
                 FAILURE_COUNTER += 1
        elif "No significant news found" in news_content:
             print(f"  ⚪ {name}: No verified updates.")
             # Reset counter on success (even if no news, API worked)
             with FAILURE_LOCK:
                 FAILURE_COUNTER = 0
        else:
             print(f"  ✅ {name}: Update found!")
             # Reset counter
             with FAILURE_LOCK:
                 FAILURE_COUNTER = 0
                 
             # Save Report
             # Clean up markdown
             news_content = news_content.replace("```markdown", "").replace("```", "").strip()
             
             count_str = name.replace(' ', '_').replace('/', '-')
             filename = f"{count_str}.md"
             filepath = os.path.join(report_dir, filename)
             
             with open(filepath, 'w', encoding='utf-8') as f:
                 f.write(f"# {category_name} - Daily Report\n\n")
                 f.write(f"## {name}\n")
                 f.write(news_content + "\n")
                 
    except Exception as e:
        print(f"  🔥 {name}: Critical Failure: {e}")
        with FAILURE_LOCK:
             FAILURE_COUNTER += 1
             
    time.sleep(1) # Jitter for API kindness

# Main Execution Block
if __name__ == "__main__":
    print("=== AI News Collection Start (Parallel Agent Mode) ===")
    
    report_dir = setup_report_dir()
    config = load_targets()
    
    # Flatten task list for parallel execution
    tasks = []
    for category in config:
        for tool in category['tools']:
            tasks.append({
                "category": category['category'],
                "tool": tool,
            })
            
    total_tasks = len(tasks)
    print(f"🚀 Launching {total_tasks} agents with max_workers=3...")

    # Parallel Execution
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(process_tool, t['category'], t['tool'], report_dir): t for t in tasks}
        
        for future in concurrent.futures.as_completed(futures):
            # Just consume the results to ensure exceptions are caught if any
            try:
                future.result()
            except Exception as exc:
                print(f"Thread generated an exception: {exc}")
                
            # Circuit Breaker Final Check
            if FAILURE_COUNTER >= FAILURE_THRESHOLD:
                print("🚨 CIRCUIT BREAKER TRIPPED: Too many errors. Aborting run.")
                executor.shutdown(wait=False)
                break

    print("\n=== Collection Complete ===")
    if FAILURE_COUNTER >= FAILURE_THRESHOLD:
         # Optional: Trigger notify_failure here if needed, or let GitHub Actions fail
         # To make Actions fail, exit with non-zero
         import sys
         sys.exit(1)
