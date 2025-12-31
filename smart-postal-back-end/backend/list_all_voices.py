"""List ALL voices from Google Cloud TTS to find available Sinhala voices"""
import os
from pathlib import Path
from google.cloud import texttospeech

# Set service account
backend_root = Path(__file__).parent
service_account_path = backend_root / "config" / "service-account-key.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(service_account_path)

print(f"✅ Using service account: {service_account_path}\n")

client = texttospeech.TextToSpeechClient()

print("=" * 60)
print("LISTING ALL AVAILABLE VOICES")
print("=" * 60)

try:
    voices = client.list_voices()
    
    # Group by language
    by_language = {}
    for voice in voices.voices:
        for lang in voice.language_codes:
            if lang not in by_language:
                by_language[lang] = []
            by_language[lang].append(voice)
    
    print(f"\nTotal voices: {len(voices.voices)}")
    print(f"Total languages: {len(by_language)}\n")
    
    # Show Sinhala voices
    sinhala_voices = by_language.get('si-LK', [])
    print(f"🇱🇰 Sinhala (si-LK) voices: {len(sinhala_voices)}")
    if sinhala_voices:
        for voice in sinhala_voices:
            print(f"   - {voice.name}")
            print(f"     Gender: {texttospeech.SsmlVoiceGender(voice.ssml_gender).name}")
            print(f"     Languages: {', '.join(voice.language_codes)}")
            print()
    else:
        print("   ❌ NO SINHALA VOICES AVAILABLE!")
        print()
        print("   This could mean:")
        print("   1. Sinhala is not supported in your project's region")
        print("   2. You need to enable additional APIs")
        print("   3. Regional restrictions apply")
        print()
    
    # Show some other languages for comparison
    print("\n📊 Sample of available languages:")
    for lang_code in sorted(by_language.keys())[:10]:
        count = len(by_language[lang_code])
        print(f"   {lang_code}: {count} voices")
    
    if len(by_language) > 10:
        print(f"   ... and {len(by_language) - 10} more languages")
        
except Exception as e:
    print(f"❌ Error listing voices: {e}")
    import traceback
    traceback.print_exc()
