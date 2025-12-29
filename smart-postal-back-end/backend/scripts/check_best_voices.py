"""Check ALL available Google TTS voices with quality levels"""
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from dotenv import load_dotenv
env_path = project_root / "config" / ".env"
load_dotenv(env_path)

from google.cloud import texttospeech

api_key = os.getenv("GOOGLE_CLOUD_TTS_API_KEY")
client = texttospeech.TextToSpeechClient(
    client_options={"api_key": api_key}
)

# List ALL voices
response = client.list_voices()

# Group voices by quality
journey_voices = []
neural2_voices = []
wavenet_voices = []
standard_voices = []
news_voices = []
studio_voices = []

print("\n🔍 Scanning ALL available voices...\n")

for voice in response.voices:
    for lang in voice.language_codes:
        if lang.startswith("si"):  # Sinhala
            gender = texttospeech.SsmlVoiceGender(voice.ssml_gender).name
            
            if "Journey" in voice.name:
                journey_voices.append((voice.name, gender, lang))
            elif "Neural2" in voice.name:
                neural2_voices.append((voice.name, gender, lang))
            elif "Wavenet" in voice.name:
                wavenet_voices.append((voice.name, gender, lang))
            elif "News" in voice.name:
                news_voices.append((voice.name, gender, lang))
            elif "Studio" in voice.name:
                studio_voices.append((voice.name, gender, lang))
            elif "Standard" in voice.name:
                standard_voices.append((voice.name, gender, lang))

# Display results
print("=" * 70)
print("SINHALA (si-LK) VOICES BY QUALITY")
print("=" * 70)

if journey_voices:
    print("\n🌟 JOURNEY VOICES (NEWEST - Most Natural, Conversational)")
    print("   💰 Cost: $0.016/1K chars")
    for name, gender, lang in journey_voices:
        print(f"   ✓ {name} ({gender})")
else:
    print("\n❌ Journey voices: NOT AVAILABLE (Requires billing + premium)")

if neural2_voices:
    print("\n🚀 NEURAL2 VOICES (LATEST GENERATION - Very Natural)")
    print("   💰 Cost: $0.016/1K chars")
    for name, gender, lang in neural2_voices:
        print(f"   ✓ {name} ({gender})")
else:
    print("\n❌ Neural2 voices: NOT AVAILABLE (Requires billing)")

if studio_voices:
    print("\n🎙️ STUDIO VOICES (HIGH QUALITY - Professional)")
    print("   💰 Cost: $0.160/1K chars (expensive!)")
    for name, gender, lang in studio_voices:
        print(f"   ✓ {name} ({gender})")
else:
    print("\n❌ Studio voices: NOT AVAILABLE")

if news_voices:
    print("\n📰 NEWS VOICES (NEWS READING STYLE)")
    print("   💰 Cost: $0.016/1K chars")
    for name, gender, lang in news_voices:
        print(f"   ✓ {name} ({gender})")
else:
    print("\n❌ News voices: NOT AVAILABLE")

if wavenet_voices:
    print("\n🎵 WAVENET VOICES (GOOD QUALITY - Natural sounding)")
    print("   💰 Cost: $0.016/1K chars")
    for name, gender, lang in wavenet_voices:
        print(f"   ✓ {name} ({gender})")
else:
    print("\n❌ WaveNet voices: NOT AVAILABLE (Requires billing enabled)")

if standard_voices:
    print("\n🔊 STANDARD VOICES (BASIC - Robotic)")
    print("   ✅ FREE: 4M chars/month")
    for name, gender, lang in standard_voices:
        print(f"   ✓ {name} ({gender})")
else:
    print("\n❌ Standard voices: NOT AVAILABLE")

print("\n" + "=" * 70)
print("RECOMMENDATIONS:")
print("=" * 70)

if journey_voices or neural2_voices:
    print("✅ PREMIUM VOICES AVAILABLE!")
    print("   Use Neural2 or Journey for BEST quality")
elif wavenet_voices:
    print("✅ WAVENET AVAILABLE!")
    print("   Good quality, requires billing")
elif standard_voices:
    print("⚠️  ONLY STANDARD (FREE) VOICES AVAILABLE")
    print("   To unlock premium voices:")
    print("   1. Go to: https://console.cloud.google.com/billing")
    print("   2. Link a billing account (free tier still applies)")
    print("   3. Neural2/Journey voices will unlock automatically")
else:
    print("❌ NO SINHALA VOICES FOUND!")
    print("   Check if TTS API is properly enabled")

print("\n💡 Note: Even with billing enabled, you get 4M FREE chars/month!")
print("   Premium voices only charged after free tier exhausted.\n")
