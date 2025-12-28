#!/usr/bin/env python3
"""Debug Groq setup."""
import sys
import os

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv

# Load env
load_dotenv()

print("Environment variables:")
print(f"GROQ_API_KEY set: {bool(os.getenv('GROQ_API_KEY'))}")
print(f"GROQ_API_KEY value: {os.getenv('GROQ_API_KEY', 'NOT SET')[:30]}...")
print(f"USE_GROQ: {os.getenv('COURIERBOT_USE_GROQ')}")

# Try importing
try:
    from groq import Groq
    print("\nGroq package imported successfully")
    
    api_key = os.getenv("GROQ_API_KEY")
    if api_key:
        client = Groq(api_key=api_key)
        print(f"✓ Groq client created: {client}")
    else:
        print("✗ GROQ_API_KEY not found in environment")
except Exception as e:
    print(f"✗ Error: {e}")
