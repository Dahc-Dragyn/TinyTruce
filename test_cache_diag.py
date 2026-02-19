import os
import google.generativeai as genai
from google.generativeai import caching
import datetime
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def test_cache():
    print("Testing cache creation...")
    try:
        cache = caching.CachedContent.create(
            model="models/gemini-1.5-flash-001",
            display_name="test_cache",
            contents=["This is a test of the emergency caching system."],
            ttl=datetime.timedelta(minutes=5),
        )
        print(f"SUCCESS: Cache created: {cache.name}")
        # Note: We don't need to keep it, so we can delete or let it expire
    except Exception as e:
        print(f"FAILURE: {e}")

if __name__ == "__main__":
    test_cache()
