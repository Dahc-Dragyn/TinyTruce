from google import genai
import os
from dotenv import load_dotenv

# Load API keys
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("Error: GEMINI_API_KEY or GOOGLE_API_KEY not found in environment.")
    exit(1)

client = genai.Client(api_key=api_key)

print("Searching for active Context Caches to purge...")
try:
    count = 0
    # Use the diagnostic list method from the modern SDK
    for c in client.caches.list():
        print(f"Deleting Cache: {c.name} (Display Name: {c.display_name})...")
        client.caches.delete(name=c.name)
        count += 1
        
    if count == 0:
        print("No active caches found. Nothing to purge.")
    else:
        print(f"\nSUCCESS: Purged {count} active Context Cache(s). Your billing baseline has been reset.")
        
except Exception as e:
    print(f"Error purging caches: {e}")
