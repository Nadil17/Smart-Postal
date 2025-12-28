"""
Quick test script for Sinhala Voice Assistant
Tests basic functionality without audio I/O
"""
import sys
from pathlib import Path
import os

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_basic_import():
    """Test if we can import the courier bot"""
    print("=" * 60)
    print("TEST 1: Importing courier_bot modules...")
    print("=" * 60)
    try:
        import courier_bot
        from courier_bot import load_env, resolve_model_name, initialize_model, handle_model_turn
        print("✓ Successfully imported courier_bot modules")
        return True
    except ImportError as e:
        print(f"✗ Failed to import: {e}")
        return False

def test_env_setup():
    """Test environment configuration"""
    print("\n" + "=" * 60)
    print("TEST 2: Checking Environment Configuration...")
    print("=" * 60)
    try:
        from courier_bot import load_env
        load_env()
        
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            print(f"✓ GEMINI_API_KEY found: {api_key[:10]}...{api_key[-4:]}")
        else:
            print("✗ GEMINI_API_KEY not found")
            return False
            
        model = os.getenv("COURIERBOT_MODEL", "gemini-2.0-flash-exp")
        print(f"✓ Model: {model}")
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_bot_initialization():
    """Test bot initialization"""
    print("\n" + "=" * 60)
    print("TEST 3: Initializing Gemini Model...")
    print("=" * 60)
    try:
        from courier_bot import load_env, resolve_model_name, initialize_model
        
        load_env()
        model_name = resolve_model_name()
        print(f"Using model: {model_name}")
        
        model = initialize_model()
        print("✓ Gemini model initialized successfully")
        
        # Start a chat session
        chat = model.start_chat(history=[])
        return (model, chat)
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_text_query(session):
    """Test a simple text query"""
    print("\n" + "=" * 60)
    print("TEST 4: Testing Text Query...")
    print("=" * 60)
    if not session:
        print("✗ Model not initialized, skipping test")
        return False
    
    model, chat = session
        
    try:
        from courier_bot import handle_model_turn
        
        # Test with a simple Sinhala query
        test_query = "හලෝ"  # "Hello"
        print(f"Query: {test_query}")
        
        reply, updated_chat = handle_model_turn(model, chat, test_query)
        print(f"\n✓ Response received:")
        print(f"  Text: {reply[:200]}...")
        
        return True
    except Exception as e:
        print(f"✗ Query failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_function_calling(session):
    """Test function calling capability"""
    print("\n" + "=" * 60)
    print("TEST 5: Testing Function Calling...")
    print("=" * 60)
    if not session:
        print("✗ Model not initialized, skipping test")
        return False
    
    model, chat = session
        
    try:
        from courier_bot import handle_model_turn
        
        # Test tracking query with a known tracking number from mock_db
        test_query = "TRK001 එකේ status එක check කරන්නද?"
        print(f"Query: {test_query}")
        
        reply, updated_chat = handle_model_turn(model, chat, test_query)
        print(f"\n✓ Response received:")
        print(f"  Text: {reply[:200]}...")
        
        return True
    except Exception as e:
        print(f"✗ Function calling failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print(" SINHALA VOICE ASSISTANT - SYSTEM TEST")
    print("=" * 60 + "\n")
    
    results = []
    
    # Test 1: Import
    results.append(("Import", test_basic_import()))
    
    # Test 2: Environment
    results.append(("Environment", test_env_setup()))
    
    # Test 3: Initialization
    session = test_bot_initialization()
    results.append(("Initialization", session is not None))
    
    # Test 4: Text Query
    results.append(("Text Query", test_text_query(session)))
    
    # Test 5: Function Calling
    results.append(("Function Calling", test_function_calling(session)))
    
    # Summary
    print("\n" + "=" * 60)
    print(" TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! The Sinhala Voice Assistant is working!")
    else:
        print("\n⚠️ Some tests failed. Check the errors above.")

if __name__ == "__main__":
    main()
