import os
from google import genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GCP_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
GCP_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

print(f"Testing Vertex AI integration for project: {GCP_PROJECT_ID} in {GCP_LOCATION}")

try:
    # Initialize client in Vertex AI mode
    client = genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)
    
    # Test a simple prompt (using the confirmed cheapest 2026 model ID)
    response = client.models.generate_content(
        model='gemini-2.5-flash-lite', 
        contents='Does the math care about my legacy?'
    )
    
    print("\n--- Response from Vertex AI ---")
    print(response.text)
    print("--- End of Response ---")
    print("\nSUCCESS: Vertex AI connection verified and billing should be active.")

except Exception as e:
    print(f"\nFAILURE: Could not connect to Vertex AI: {e}")
    print("Ensure you have run: gcloud auth application-default login")
