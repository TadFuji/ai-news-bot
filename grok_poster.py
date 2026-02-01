from datetime import timezone, timedelta
import os
import requests
import json
from dotenv import load_dotenv

# Load env
load_dotenv()

XAI_API_KEY = os.environ.get("XAI_API_KEY")

def generate_grok_post(article_title, article_summary, article_url):
    """
    Uses xAI Grok API to generate a high-engagement X post.
    User requested: "Grok 4.1 Flash" (using best available model).
    """
    if not XAI_API_KEY:
        return f"Error: XAI_API_KEY not found.\n{article_title}\n{article_url}"
        
    url = "https://api.x.ai/v1/chat/completions"
    
    # Persona: High-energy, tech-savvy market leader.
    system_prompt = """
    You are a professional AI Tech News influencer on X (Twitter).
    Your goal is to maximize engagement (likes/retweets) and clicks.
    
    Style Guide:
    - Language: Japanese (Natural, Native, Professional yet Exciting)
    - Tone: Urgent, Insightful, "Must Read" vibe.
    - Formatting: short sentences, bullet points if needed.
    - Constraints: No strict character limit. Provide a full and insightful post (X now supports long-form content).
    - Hashtags: #AI #Tech
    - DO NOT include the URL in the text (it will be attached separately).
    - DO NOT use "Intro" or "Outro". Just the tweet body.
    """
    
    user_prompt = f"""
    Write a viral X post about this news:
    Title: {article_title}
    Summary: {article_summary}
    
    Make it sound like a breaking "Scoop" or a "Deep Insight".
    """
    
    payload = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "model": "grok-4-1-fast-non-reasoning", # User requested specific model 
        "stream": False,
        "temperature": 0.7
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {XAI_API_KEY}"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        data = response.json()
        
        if "choices" in data:
            return data['choices'][0]['message']['content'].strip()
        else:
            return f"Error from Grok: {data}"
            
    except Exception as e:
        return f"Exception calling Grok: {e}"

if __name__ == "__main__":
    # Test
    print(generate_grok_post("Test News", "This is a test summary about AI.", "http://example.com"))
