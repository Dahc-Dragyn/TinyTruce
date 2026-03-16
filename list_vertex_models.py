import os
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GCP_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
GCP_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

print(f"Listing available models for project: {GCP_PROJECT_ID} in {GCP_LOCATION}")

try:
    # Initialize client in Vertex AI mode
    client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)
    
    print("\n--- Available Models ---")
    for model in client.models.list():
        print(f"ID: {model.name}")
    print("--- End of List ---")

except Exception as e:
    print(f"\nFAILURE: Could not list models: {e}")
