"""List all available Sinhala voices from Google Cloud TTS"""
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

# List all voices
response = client.list_voices()

# Filter Sinhala voices
print("\n🎤 Available Sinhala (si-LK) voices:\n")
for voice in response.voices:
    for lang in voice.language_codes:
        if lang.startswith("si"):
            gender = texttospeech.SsmlVoiceGender(voice.ssml_gender).name
            print(f"  • {voice.name}")
            print(f"    Gender: {gender}")
            print(f"    Languages: {', '.join(voice.language_codes)}")
            print()
