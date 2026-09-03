import os
import requests
from dotenv import load_dotenv
from google import genai
from google.genai.errors import APIError

load_dotenv()

print("Gemini API Key defined:", bool(os.getenv("GEMINI_API_KEY")))
print("Groq API Key defined:", bool(os.getenv("GROQ_API_KEY")))

print("\n--- Testing Groq ---")
groq_key = os.getenv("GROQ_API_KEY")
if groq_key:
    headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [{"role": "user", "content": "Hello, this is a test."}],
        "max_tokens": 10
    }
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=5)
        print(f"Groq status: {r.status_code}")
        if r.status_code != 200:
            print("Groq error:", r.text)
        else:
            print("Groq success!")
    except Exception as e:
        print("Groq Exception:", repr(e))
else:
    print("No GROQ_API_KEY")

print("\n--- Testing Gemini ---")
gemini_key = os.getenv("GEMINI_API_KEY")
if gemini_key:
    try:
        client = genai.Client(api_key=gemini_key)
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents='Hello'
        )
        print("Gemini 2.5 success.")
    except Exception as e:
        print("Gemini 2.5 Exception:", repr(e))
        
    try:
        client = genai.Client(api_key=gemini_key)
        response = client.models.generate_content(
            model='gemini-3.5-flash',
            contents='Hello'
        )
        print("Gemini 3.5 success.")
    except Exception as e:
        print("Gemini 3.5 Exception:", repr(e))
else:
    print("No GEMINI_API_KEY")
