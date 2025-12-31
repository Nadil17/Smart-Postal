"""Check available Azure Sinhala voices and test them"""
import os
from pathlib import Path
from dotenv import load_dotenv
import azure.cognitiveservices.speech as speechsdk

# Load environment
backend_root = Path(__file__).parent
load_dotenv(backend_root / "config" / ".env")

key = os.getenv("AZURE_SPEECH_KEY")
region = os.getenv("AZURE_SPEECH_REGION")

print("=" * 60)
print("AZURE SINHALA VOICES - COMPLETE LIST")
print("=" * 60)

speech_config = speechsdk.SpeechConfig(subscription=key, region=region)
synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)

# Get list of voices
result = synthesizer.get_voices_async().get()

print(f"\n🔍 Searching for Sinhala (si-LK) voices...\n")

sinhala_voices = []
for voice in result.voices:
    if voice.locale.startswith("si-LK"):
        sinhala_voices.append(voice)
        print(f"{'='*60}")
        print(f"✅ Found: {voice.short_name}")
        print(f"   Gender: {voice.gender.name}")
        print(f"   Locale: {voice.locale}")
        print(f"   Display Name: {voice.local_name}")
        print(f"   Voice Type: {voice.voice_type.name}")

if not sinhala_voices:
    print("❌ No Sinhala voices found!")
else:
    print(f"\n{'='*60}")
    print(f"Total Sinhala voices found: {len(sinhala_voices)}")
    print(f"{'='*60}")
    
    # Test each voice
    test_text = "හෙලෝ, මගේ නම සමීර. මම ඔබට උදව් කරන්න සතුටුයි."
    
    for i, voice in enumerate(sinhala_voices, 1):
        print(f"\n🎤 Testing Voice {i}: {voice.short_name}")
        print(f"   Gender: {voice.gender.name}")
        print("-" * 60)
        
        try:
            # Configure this specific voice
            speech_config_test = speechsdk.SpeechConfig(subscription=key, region=region)
            speech_config_test.speech_synthesis_voice_name = voice.short_name
            speech_config_test.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
            )
            
            synthesizer_test = speechsdk.SpeechSynthesizer(speech_config=speech_config_test, audio_config=None)
            
            # Test with SSML
            ssml = f'''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="si-LK">
                <voice name="{voice.short_name}">
                    <prosody rate="0.9" pitch="-2%">
                        {test_text}
                    </prosody>
                </voice>
            </speak>'''
            
            result = synthesizer_test.speak_ssml_async(ssml).get()
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                audio_data = result.audio_data
                
                # Save to file
                output_file = backend_root / f"azure_voice_test_{voice.short_name}.mp3"
                with open(output_file, "wb") as f:
                    f.write(audio_data)
                
                print(f"   ✅ Success!")
                print(f"   Audio size: {len(audio_data):,} bytes")
                print(f"   Saved: {output_file.name}")
                
                # Play it
                import subprocess
                subprocess.Popen([str(output_file)], shell=True)
                
                import time
                time.sleep(3)  # Wait between samples
            else:
                print(f"   ❌ Failed: {result.reason}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

print("\n" + "=" * 60)
print("VOICE COMPARISON COMPLETE")
print("=" * 60)
print("\nListen to the samples to choose your preferred voice!")
print("Then we'll update the configuration.")
print("=" * 60)
