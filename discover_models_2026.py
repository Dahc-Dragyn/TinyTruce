import os
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GCP_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
GCP_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

candidates = [
    "gemini-3.1-flash-lite",
    "gemini-3.1-flash-lite-001",
    "gemini-3.1-flash",
    "gemini-3.1-flash-001",
    "gemini-2.5-flash",
    "gemini-2.5-flash-001",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash-lite-001"
]

client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)

print(f"Scanning for 2026 cheapest models in {GCP_LOCATION}...")

for model_id in candidates:
    try:
        response = client.models.generate_content(
            model=model_id,
            contents="test"
        )
        print(f"[SUCCESS] Model '{model_id}' is available.")
    except Exception as e:
        if "404" in str(e):
            print(f"[404] Model '{model_id}' not found.")
        else:
            print(f"[ERROR] Model '{model_id}': {e}")
