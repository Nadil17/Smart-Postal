import requests
import time

# Wait for server to be ready
print("Waiting for server...")
time.sleep(2)

try:
    print("\nTesting server connection...")
    response = requests.get("http://127.0.0.1:8000/")
    print(f"Server reachable: {response.status_code}")
except Exception as e:
    print(f"Cannot reach server: {e}")
    exit(1)

# Test the assistant endpoint
print("\nTesting TTS endpoint...")
url = "http://127.0.0.1:8000/api/assistant/query/text"
payload = {"text": "හෙලෝ, මගේ නම අනුර. මම ඔබට උදව්වීමට සතුටුයි."}

try:
    response = requests.post(url, json=payload, timeout=30)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Full response keys: {list(data.keys())}")
        print(f"Response text: {data.get('response_text', 'N/A')[:200] if data.get('response_text') else 'N/A'}")
        
        # Check for response_audio field
        if 'response_audio' in data and data['response_audio']:
            import base64
            audio_bytes = base64.b64decode(data['response_audio'])
            with open("simple_test_output.mp3", "wb") as f:
                f.write(audio_bytes)
            print(f"✅ Audio saved: {len(audio_bytes)} bytes")
            print("🎵 Opening audio file...")
            import subprocess
            subprocess.Popen(["simple_test_output.mp3"], shell=True)
        else:
            print(f"⚠️ No audio in response. Audio field: {data.get('response_audio', 'missing')}")
    else:
        print(f"Error: {response.text[:200]}")
except Exception as e:
    print(f"Request failed: {e}")
