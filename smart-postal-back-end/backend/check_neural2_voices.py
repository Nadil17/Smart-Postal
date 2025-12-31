import os
from pathlib import Path
import sys

# Set up path
backend_path = Path(__file__).parent
sys.path.insert(0, str(backend_path))

# Load .env
from dotenv import load_dotenv
env_path = backend_path / "config" / ".env"
load_dotenv(env_path)

# Set credentials
service_account_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
if service_account_path:
    abs_path = backend_path / service_account_path
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(abs_path)
    print(f"✅ Using service account: {abs_path}")

from google.cloud import texttospeech

client = texttospeech.TextToSpeechClient()

print("\n" + "=" * 60)
print("LISTING ALL AVAILABLE SINHALA VOICES")
print("=" * 60)

voices = client.list_voices(language_code="si-LK")

print(f"\nFound {len(voices.voices)} Sinhala voices:\n")

for voice in voices.voices:
    quality = "UNKNOWN"
    if "Neural2" in voice.name:
        quality = "🌟 NEURAL2 (Premium)"
    elif "Wavenet" in voice.name:
        quality = "💎 WAVENET (Premium)"
    elif "Standard" in voice.name:
        quality = "📢 STANDARD (Free)"
    else:
        quality = "❓ Unknown"
    
    gender = "Male" if voice.ssml_gender == 1 else "Female" if voice.ssml_gender == 2 else "Neutral"
    
    print(f"{quality}")
    print(f"  Name: {voice.name}")
    print(f"  Gender: {gender}")
    print(f"  Language: {', '.join(voice.language_codes)}")
    print()

print("=" * 60)
print("Testing si-LK-Neural2-A specifically...")
print("=" * 60)

try:
    synthesis_input = texttospeech.SynthesisInput(text="හෙලෝ")
    voice = texttospeech.VoiceSelectionParams(
        language_code="si-LK",
        name="si-LK-Neural2-A"
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )
    
    print(f"✅ Neural2-A works!")
    print(f"   Audio size: {len(response.audio_content)} bytes")
    
    with open("test_neural2_direct.mp3", "wb") as f:
        f.write(response.audio_content)
    print(f"   Saved to: test_neural2_direct.mp3")
    
except Exception as e:
    print(f"❌ Error with Neural2-A: {e}")
    import traceback
    traceback.print_exc()
