from google import genai
import os
from dotenv import load_dotenv

# Load environment
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
gcp_project = os.getenv("GOOGLE_CLOUD_PROJECT")
gcp_location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

if gcp_project:
    print(f"Initializing Vertex AI client for project: {gcp_project}")
    client = genai.Client(vertexai=True, project=gcp_project, location=gcp_location)
elif api_key:
    print("Initializing AI Studio client...")
    client = genai.Client(api_key=api_key)
else:
    print("Error: No GEMINI_API_KEY or GOOGLE_CLOUD_PROJECT found.")
    exit(1)

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
