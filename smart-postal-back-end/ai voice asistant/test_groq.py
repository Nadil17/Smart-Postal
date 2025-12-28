#!/usr/bin/env python3
"""Quick test script for Groq integration."""
import sys
import os

# Fix encoding for Windows console
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Add the project directory to path
sys.path.insert(0, os.path.dirname(__file__))

from courier_bot import (
    initialize_model,
    handle_model_turn,
    get_groq_client,
    GroqClient,
)

# Initialize model
model = initialize_model()
is_groq = isinstance(model, type(get_groq_client())) if GroqClient else False

print(f"✓ Model initialized: {'Groq' if is_groq else 'Gemini'}")

# Initialize chat
if is_groq:
    chat = []
else:
    chat = model.start_chat(history=[])

print(f"✓ Chat session started")

# Test query
test_queries = [
    "mage trk001 eke status kiyanna",
    "colombo hadak kandy hadak shipping cost kettha",
]

for query in test_queries:
    print(f"\n📝 Query: {query}")
    try:
        reply, chat = handle_model_turn(model, chat, query)
        print(f"✓ Reply: {reply}")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

print("\n✓ Test completed successfully!")
