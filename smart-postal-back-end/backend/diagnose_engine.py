"""Test which TTS engine is actually being used"""
import requests
import base64
from pathlib import Path

backend_url = "http://127.0.0.1:8000"

print("=" * 60)
print("CHECKING ACTUAL TTS ENGINE IN USE")
print("=" * 60)

test_text = "හෙලෝ මගේ නම දිනිද"

print(f"\n📝 Test Query: {test_text}")
print("-" * 60)

try:
    response = requests.post(
        f"{backend_url}/api/assistant/query/text",
        json={"text": test_text},
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        
        if data.get("success"):
            print(f"✅ Response: {data['response_text']}\n")
            
            if data.get("response_audio"):
                audio_bytes = base64.b64decode(data["response_audio"])
                size = len(audio_bytes)
                
                print(f"🎵 Audio Analysis:")
                print(f"   Size: {size:,} bytes")
                
                # Determine engine by size
                if size > 25000:
                    engine = "Azure Neural (Premium)"
                    voice_type = "si-LK-SameeraNeural (Male) or si-LK-ThiliniNeural (Female)"
                elif 18000 < size < 25000:
                    engine = "Azure Neural (Standard)"
                    voice_type = "Neural voice"
                elif 10000 < size < 18000:
                    engine = "Azure TTS (Basic)"
                    voice_type = "Standard voice"
                elif 5000 < size < 10000:
                    engine = "gTTS (Free)"
                    voice_type = "Female robotic voice"
                else:
                    engine = "Unknown"
                    voice_type = "Unknown"
                
                print(f"   Engine: {engine}")
                print(f"   Voice: {voice_type}")
                
                # Save and play
                output_file = Path(__file__).parent / "current_engine_test.mp3"
                with open(output_file, "wb") as f:
                    f.write(audio_bytes)
                
                print(f"\n▶️  Saved: {output_file.name}")
                print(f"   Playing now...")
                
                import subprocess
                subprocess.Popen([str(output_file)], shell=True)
                
                print("\n" + "=" * 60)
                print("💡 DIAGNOSIS:")
                print("=" * 60)
                if "gTTS" in engine:
                    print("❌ ISSUE: Using gTTS (old free service)")
                    print("   This is the 'female robotic' voice you're hearing")
                    print("   Azure TTS is NOT being used!")
                    print("\n📋 Possible causes:")
                    print("   1. Azure credentials not loaded properly")
                    print("   2. Azure TTS failed and fell back to gTTS")
                    print("   3. Engine setting is wrong in .env")
                elif "Azure" in engine:
                    print("✅ GOOD: Using Azure Neural TTS")
                    print("   This is premium quality voice")
                    print(f"   If you hear female voice, it's using ThiliniNeural")
                    print(f"   Male voice (SameeraNeural) is configured in code")
            else:
                print("❌ No audio in response")
        else:
            print(f"❌ Failed: {data.get('error')}")
    else:
        print(f"❌ HTTP {response.status_code}")
        print("⚠️  Server might not be running!")
        print("\nPlease check if uvicorn server is running:")
        print("   Look for PowerShell window with server logs")
        
except requests.exceptions.ConnectionError:
    print("❌ Cannot connect to server!")
    print("\n📋 Server is NOT running. Please start it:")
    print("   1. Open PowerShell in: smart-postal-back-end\\backend")
    print("   2. Run: C:/Users/dinid/OneDrive/Desktop/Smart-Postal-Sinhala/Smart-Postal/.venv/Scripts/python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000")
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
