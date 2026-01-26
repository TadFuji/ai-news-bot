import os
import google.genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("GOOGLE_API_KEY")
if not api_key:
    print("Error: GOOGLE_API_KEY not found.")
    exit()

client = google.genai.Client(api_key=api_key)

print("Fetching available models...")
try:
    # Attempt to list models. The SDK structure might vary, 
    # but client.models.list() is standard for the verifiable SDK versions.
    # We will try to iterate and print.
    for m in client.models.list():
        if "gemini" in m.name:
            print(f"- {m.name} ({m.display_name})")
except Exception as e:
    print(f"Error fetching models: {e}")
