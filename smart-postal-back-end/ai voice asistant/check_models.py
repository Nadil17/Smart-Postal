#!/usr/bin/env python3
"""Test available Groq models."""
import sys
import os

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, os.path.dirname(__file__))

from courier_bot import get_groq_client

groq = get_groq_client()

print("Testing Groq models...\n")

test_models = [
    "gemma-7b-it",
    "gemma2-9b-it",
    "llama3-70b-8192",
    "mixtral-8x7b-32768",
]

for model in test_models:
    try:
        response = groq.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Hi"}],
            max_tokens=10,
        )
        print(f"✓ {model} - AVAILABLE")
    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg or "does not exist" in error_msg:
            print(f"✗ {model} - NOT FOUND")
        elif "401" in error_msg or "401" in error_msg:
            print(f"✗ {model} - NO ACCESS")
        else:
            print(f"? {model} - ERROR: {error_msg[:50]}")
