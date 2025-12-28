"""
Full Voice Functionality Test for Sinhala Voice Assistant
Tests microphone input, speech recognition, and audio output
"""
import sys
from pathlib import Path
import os

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_audio_libraries():
    """Test if all audio libraries are available"""
    print("=" * 60)
    print("TEST 1: Checking Audio Libraries")
    print("=" * 60)
    
    results = {}
    
    # Test SpeechRecognition
    try:
        import speech_recognition as sr
        results['SpeechRecognition'] = True
        print("✓ SpeechRecognition: INSTALLED")
    except ImportError:
        results['SpeechRecognition'] = False
        print("✗ SpeechRecognition: NOT INSTALLED")
    
    # Test gTTS
    try:
        from gtts import gTTS
        results['gTTS'] = True
        print("✓ gTTS: INSTALLED")
    except ImportError:
        results['gTTS'] = False
        print("✗ gTTS: NOT INSTALLED")
    
    # Test pygame
    try:
        import pygame
        results['pygame'] = True
        print("✓ pygame: INSTALLED")
    except ImportError:
        results['pygame'] = False
        print("✗ pygame: NOT INSTALLED")
    
    # Test pydub
    try:
        import pydub
        results['pydub'] = True
        print("✓ pydub: INSTALLED")
    except ImportError:
        results['pydub'] = False
        print("✗ pydub: NOT INSTALLED")
    
    return all(results.values())


def test_microphone_availability():
    """Test if microphone is available"""
    print("\n" + "=" * 60)
    print("TEST 2: Checking Microphone Availability")
    print("=" * 60)
    
    try:
        import speech_recognition as sr
        
        # List available microphones
        mic_list = sr.Microphone.list_microphone_names()
        if mic_list:
            print(f"✓ Found {len(mic_list)} microphone(s):")
            for idx, name in enumerate(mic_list):
                print(f"   [{idx}] {name}")
            return True
        else:
            print("✗ No microphones detected")
            return False
    except Exception as e:
        print(f"✗ Error checking microphones: {e}")
        return False


def test_text_to_speech():
    """Test gTTS and audio playback"""
    print("\n" + "=" * 60)
    print("TEST 3: Testing Text-to-Speech (gTTS)")
    print("=" * 60)
    
    try:
        from gtts import gTTS
        import pygame
        
        test_text = "හලෝ, මම සිංහල හඬ සහායකයා"  # Hello, I am Sinhala voice assistant
        print(f"Test text: {test_text}")
        
        # Generate TTS
        tts = gTTS(text=test_text, lang='si', slow=False)
        audio_file = Path(__file__).parent / "test_voice_output.mp3"
        tts.save(str(audio_file))
        print(f"✓ Audio file generated: {audio_file.name}")
        
        # Test playback
        print("🔊 Playing audio... (this will take a few seconds)")
        pygame.mixer.init()
        pygame.mixer.music.load(str(audio_file))
        pygame.mixer.music.play()
        
        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
        
        pygame.mixer.quit()
        print("✓ Audio playback completed successfully")
        
        # Cleanup
        if audio_file.exists():
            audio_file.unlink()
        
        return True
    except Exception as e:
        print(f"✗ TTS test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_speech_recognition_manual():
    """Test speech recognition with user input"""
    print("\n" + "=" * 60)
    print("TEST 4: Testing Speech Recognition")
    print("=" * 60)
    
    try:
        import speech_recognition as sr
        
        recognizer = sr.Recognizer()
        
        print("\n📝 Manual test - Please speak when prompted")
        print("   (Speak in Sinhala or English)")
        print("   Waiting 5 seconds after prompt...")
        
        response = input("\nDo you want to test microphone input? (y/n): ").strip().lower()
        
        if response != 'y':
            print("⊘ Skipping microphone test")
            return None
        
        with sr.Microphone() as source:
            print("\n🎙️ Adjusting for ambient noise... (wait 2 seconds)")
            recognizer.adjust_for_ambient_noise(source, duration=2)
            
            print("🎙️ Listening... Speak now!")
            try:
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=10)
                print("✓ Audio captured, processing...")
                
                # Try Google Speech Recognition
                text = recognizer.recognize_google(audio, language="si-LK")
                print(f"✓ Recognized text: {text}")
                return True
                
            except sr.WaitTimeoutError:
                print("⊘ No speech detected within timeout")
                return None
            except sr.UnknownValueError:
                print("⊘ Could not understand audio")
                return None
            except sr.RequestError as e:
                print(f"✗ Recognition service error: {e}")
                return False
                
    except Exception as e:
        print(f"✗ Speech recognition test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_courier_bot_integration():
    """Test integration with courier bot functions"""
    print("\n" + "=" * 60)
    print("TEST 5: Testing Courier Bot Voice Integration")
    print("=" * 60)
    
    try:
        from courier_bot import speak_sinhala, transcribe_from_microphone
        
        # Test speak function
        print("\nTesting speak_sinhala() function...")
        test_text = "පැකේජය කුරුණෑගල තිබේ"  # Package is in Kurunegala
        print(f"Speaking: {test_text}")
        print("🔊 Playing audio...")
        
        speak_sinhala(test_text)
        print("✓ speak_sinhala() function works!")
        
        return True
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_conversation_flow():
    """Test a complete conversation flow"""
    print("\n" + "=" * 60)
    print("TEST 6: Full Voice Conversation Flow")
    print("=" * 60)
    
    try:
        from courier_bot import initialize_model, handle_model_turn, speak_sinhala
        
        print("Initializing bot...")
        model = initialize_model()
        chat = model.start_chat(history=[])
        print("✓ Bot initialized")
        
        # Test conversation with text input (simulating voice)
        test_queries = [
            "හලෝ",  # Hello
            "TRK001 එකේ status එක දෙන්නද?",  # Give status of TRK001
        ]
        
        for query in test_queries:
            print(f"\n👤 User (simulated): {query}")
            reply, chat = handle_model_turn(model, chat, query)
            print(f"🤖 Bot: {reply}")
            
            # Speak the response
            print("🔊 Speaking response...")
            speak_sinhala(reply)
        
        print("\n✓ Full conversation flow test completed!")
        return True
        
    except Exception as e:
        print(f"✗ Conversation flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all voice functionality tests"""
    print("\n" + "=" * 60)
    print(" SINHALA VOICE ASSISTANT - FULL VOICE TEST")
    print("=" * 60 + "\n")
    
    results = []
    
    # Test 1: Audio Libraries
    results.append(("Audio Libraries", test_audio_libraries()))
    
    # Test 2: Microphone
    results.append(("Microphone Detection", test_microphone_availability()))
    
    # Test 3: Text-to-Speech
    results.append(("Text-to-Speech", test_text_to_speech()))
    
    # Test 4: Speech Recognition (optional)
    mic_result = test_speech_recognition_manual()
    if mic_result is not None:
        results.append(("Speech Recognition", mic_result))
    
    # Test 5: Courier Bot Integration
    results.append(("Bot Voice Integration", test_courier_bot_integration()))
    
    # Test 6: Full Conversation
    results.append(("Full Conversation Flow", test_full_conversation_flow()))
    
    # Summary
    print("\n" + "=" * 60)
    print(" TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        if passed:
            status = "✓ PASS"
        else:
            status = "✗ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All voice features are working!")
        print("\n📝 To use full voice mode, run:")
        print("   python courier_bot.py")
    else:
        print("\n⚠️ Some tests failed. Check errors above.")
        print("\n💡 Text-only mode is still available in courier_bot.py")


if __name__ == "__main__":
    main()
