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

print("Fetching active Context Caches (Cost: $0.00) via google-genai v1.x...")
try:
    # Use the diagnostic list method from the modern SDK
    count = 0
    for c in client.caches.list():
        print(f"Cache Name: {c.name}")
        print(f"Model: {c.model}")
        print(f"Display Name: {c.display_name}")
        print(f"Expire Time (UTC): {c.expire_time}")
        print("-" * 50)
        count += 1
        
    if count == 0:
        print("No active caches found. (They delete themselves after the TTL expires).")
    else:
        print(f"SUCCESS: Found {count} active Context Cache(s) actively saving you billing tokens!")
        
except Exception as e:
    print(f"Error fetching caches: {e}")
