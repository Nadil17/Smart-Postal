#!/usr/bin/env python3
"""Test Groq with available free models."""
import sys
import os

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from dotenv import load_dotenv
load_dotenv()

from groq import Groq

api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)

print("Testing Groq models...\n")

# Free tier models on Groq
test_models = [
    "gemma-7b-it",
    "gemma2-9b-it", 
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
]

for model in test_models:
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=10,
        )
        print(f"✓ {model} - WORKS")
        print(f"  Response: {response.choices[0].message.content[:50]}")
        break  # Stop at first working model
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "does not exist" in error_msg:
            print(f"✗ {model} - NOT FOUND/DECOMMISSIONED")
        elif "401" in error_msg or "not have access" in error_msg:
            print(f"✗ {model} - NO ACCESS")
        else:
            print(f"? {model} - {error_msg[:60]}")
