import os
import time
import datetime
from openai import OpenAI
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Configuration
MODEL_ID = "gemini-2.5-flash-lite-preview-09-2025"
API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

if not API_KEY:
    print("Error: API Key not found.")
    exit(1)

# genai.configure() is for the old google-generativeai, not google-genai
client = genai.Client(api_key=API_KEY)

# 1. Create a large dummy context (>2048 tokens)
# A typical token is ~4 chars. 2500 tokens ~ 10000 chars.
dummy_context = "This is a diagnostic anchor for TinyTruce forensic simulations. " * 200 
print(f"Context size: {len(dummy_context)} characters (~{len(dummy_context)//4} tokens)")

def test_syntax(name, extra_body_structure):
    print(f"\n--- Testing Syntax: {name} ---")
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    
    try:
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Verify if the cache is active. Say 'AFFIRMATIVE' if you received the anchor context."}
            ],
            extra_body=extra_body_structure
        )
        print(f"Result: SUCCESS (200 OK)")
        print(f"Response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"Result: FAILED")
        print(f"Error: {e}")
        return False

# 2. Create the Cache using Native SDK
print("\n[STEP 1] Creating Context Cache using Native SDK...")
try:
    cache = client.caches.create(
        model=MODEL_ID,
        config=types.CreateCachedContentConfig(
            display_name="isolated_syntax_test",
            contents=[dummy_context],
            ttl="900s",
        )
    )
    cache_id = cache.name
    print(f"Cache Created Successfully: {cache_id}")
except Exception as e:
    print(f"Cache Creation Failed: {e}")
    exit(1)

def test_native_bypass(name, messages):
    print(f"\n--- Testing Native Bypass: {name} ---")
    try:
        # Translation Layer
        system_instruction = None
        gemini_messages = []
        
        for m in messages:
            if m["role"] == "system":
                system_instruction = m["content"]
            else:
                role = "model" if m["role"] == "assistant" else "user"
                gemini_messages.append({"role": role, "parts": [{"text": m["content"]}]})
        
        # The SDK expects the cache name, and sometimes it prefers the full path vs just the ID.
        # We already have cache_id as 'cachedContents/ID'
        
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=gemini_messages,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                cached_content=cache_id,
                temperature=0.2
            )
        )
        print(f"Result: SUCCESS")
        print(f"Response: {response.text}")
        return True
    except Exception as e:
        print(f"Result: FAILED -> {e}")
        return False


# 3. Test Syntaxes
# Some Google OpenAI bridges expect the full resource name, others just the ID
short_id = cache_id.split('/')[-1]

syntaxes = [
    ("Flat Snake (cached_content)", {"cached_content": cache_id}),
    ("Flat Snake Short ID", {"cached_content": short_id}),
    ("Nested Google (google -> cached_content)", {"google": {"cached_content": cache_id}}),
    ("Nested Google Short ID", {"google": {"cached_content": short_id}}),
    ("Google JSON (google -> cachedContent)", {"google": {"cachedContent": cache_id}}),
    ("Metadata Structure (metadata -> cached_content)", {"metadata": {"cached_content": cache_id}}),
]

# We should also test if it's a model-level parameter
def test_model_param(name, param_key):
    print(f"\n--- Testing Model Param: {name} ---")
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL)
    try:
        # Some bridges try to parse it from the model name itself
        response = client.chat.completions.create(
            model=f"{MODEL_ID}:{cache_id}", 
            messages=[{"role": "user", "content": "Hi"}],
        )
        print(f"Result: SUCCESS")
        return True
    except Exception as e:
        print(f"Result: FAILED -> {e}")
        return False


successes = []
report_lines = ["--- CACHE SYNTAX DIAGNOSTIC REPORT ---", f"Model: {MODEL_ID}", f"Cache ID: {cache_id}"]

for name, struct in syntaxes:
    res = test_syntax(name, struct)
    status = "SUCCESS" if res else "FAILED"
    report_lines.append(f"Syntax: {name} -> {status}")
    if res:
        successes.append(name)

# 3. Test Native Bypass
sample_messages = [
    {"role": "system", "content": "You are a specialized Antigravity agent."},
    {"role": "user", "content": "Verify if the cache is active. Say 'AFFIRMATIVE' if you received the anchor context."}
]

if test_native_bypass("Native Bypass", sample_messages):
    successes.append("Native Bypass")
else:
    print("Native Bypass also failed. Investigating SDK connectivity...")

report_lines.append("\n--- TEST SUMMARY ---")
if successes:
    report_lines.append(f"Winning Syntaxes: {', '.join(successes)}")
else:
    report_lines.append("All syntaxes failed with 400 Errors.")

with open("cache_syntax_report.txt", "w") as f:
    f.write("\n".join(report_lines))

print("\nReport written to cache_syntax_report.txt")
