import os
import json
import requests
import datetime
import google.genai
from dotenv import load_dotenv

# Load Env
load_dotenv()
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
EXISTING_MODELS_FILE = os.path.join(PROJECT_ROOT, "existing_models.json")

# Keywords for "Cheap/Fast" models
TARGET_KEYWORDS = ["flash", "lite", "fast", "mini", "nano", "haiku"]

def load_known_models():
    if os.path.exists(EXISTING_MODELS_FILE):
        with open(EXISTING_MODELS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"gemini": [], "xai": [], "last_checked": None}

def save_known_models(data):
    data["last_checked"] = datetime.datetime.now().isoformat()
    with open(EXISTING_MODELS_FILE, 'w', encoding='utf-8') as f:
        # Use simple structure
        json.dump(data, f, indent=2)

def fetch_gemini_models():
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return []
    
    client = google.genai.Client(api_key=api_key)
    models = []
    try:
        for m in client.models.list():
            if "gemini" in m.name.lower():
                # Filter for Cost-Effective variants
                if any(k in m.name.lower() for k in TARGET_KEYWORDS) or "exp" in m.name.lower():
                    models.append(m.name) # e.g. models/gemini-1.5-flash
    except Exception as e:
        print(f"Gemini Fetch Error: {e}")
    return sorted(models)

def fetch_xai_models():
    api_key = os.environ.get("XAI_API_KEY")
    if not api_key:
        return []
        
    url = "https://api.x.ai/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    models = []
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json().get('data', [])
            for m in data:
                mid = m['id']
                # Filter for Cost-Effective variants
                if any(k in mid.lower() for k in TARGET_KEYWORDS):
                    models.append(mid)
    except Exception as e:
        print(f"xAI Fetch Error: {e}")
    return sorted(models)

def main():
    print("🔍 Starting Monthly Model Monitor...")
    
    known = load_known_models()
    
    current_gemini = fetch_gemini_models()
    current_xai = fetch_xai_models()
    
    new_gemini = [m for m in current_gemini if m not in known.get("gemini", [])]
    new_xai = [m for m in current_xai if m not in known.get("xai", [])]
    
    if new_gemini or new_xai:
        print("🚨 NEW COST-EFFECTIVE MODELS DETECTED!")
        
        report = f"# 🚀 New AI Model Alert ({datetime.date.today()})\n\n"
        
        if new_gemini:
            report += "## Google Gemini Updates\n"
            for m in new_gemini:
                report += f"- **{m}**\n"
            report += "\n"
            
        if new_xai:
            report += "## xAI (Grok) Updates\n"
            for m in new_xai:
                report += f"- **{m}**\n"
            report += "\n"
            
        report += "Check pricing and update `config.py` if these are cheaper!\n"
        
        # Output Report
        report_path = os.path.join(PROJECT_ROOT, f"model_alert_{datetime.date.today()}.md")
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
            
        print(f"✅ Report saved to: {report_path}")
        print(report)
        
        # Update Knowledge Base
        known["gemini"] = sorted(list(set(known.get("gemini", []) + new_gemini)))
        known["xai"] = sorted(list(set(known.get("xai", []) + new_xai)))
        save_known_models(known)
        
    else:
        print("✅ No new models found this month.")
        # Still process save to update timestamp
        save_known_models(known)

if __name__ == "__main__":
    main()
