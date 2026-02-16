import os
from tinytroupe.agent import TinyPerson
from tinytroupe.environment import TinyWorld
import tinytroupe.openai_utils as openai_utils

def test_connectivity():
    print("Testing connectivity to Gemini model...")
    try:
        # We need to make sure OPENAI_BASE_URL is set to Google's OpenAI-compatible endpoint
        # or that the user has provided the API key in a way that the OpenAI client can use.
        # However, for Google Gemini via OpenAI client, the base URL is usually:
        # https://generativelanguage.googleapis.com/v1beta/openai/
        
        # Checking if the client can send a simple message
        res = openai_utils.client().send_message([{"role": "user", "content": "Say hello."}])
        print(f"Model response: {res}")
        if res:
            print("Connectivity test PASSED.")
        else:
            print("Connectivity test FAILED (no response).")
    except Exception as e:
        print(f"Connectivity test FAILED with error: {e}")

if __name__ == "__main__":
    test_connectivity()
