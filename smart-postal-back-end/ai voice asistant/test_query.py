"""Quick test for safety settings fix."""
from courier_bot import initialize_model, handle_model_turn

model = initialize_model()
chat = model.start_chat(history=[])

# Test the problematic query
test_query = "mage package eka ena dwsa danaganna one"
print(f"Testing: {test_query}")

reply, chat = handle_model_turn(model, chat, test_query)
print(f"Response: {reply}")

# Now provide tracking ID
test_query2 = "Trk002"
print(f"\nTesting: {test_query2}")
reply, chat = handle_model_turn(model, chat, test_query2)
print(f"Response: {reply}")

