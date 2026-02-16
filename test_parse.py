import os
from openai import OpenAI
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class TestModel(BaseModel):
    answer: str

client = OpenAI(
    api_key=os.getenv("GOOGLE_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

print("Testing beta.chat.completions.parse with Gemini...")
try:
    response = client.beta.chat.completions.parse(
        model="gemini-2.5-flash-lite-preview-09-2025",
        messages=[{"role": "user", "content": "Say hello in JSON format."}],
        response_format=TestModel
    )
    print("Success!")
    print(response.choices[0].message.parsed)
except Exception as e:
    print(f"Failed with error: {e}")
