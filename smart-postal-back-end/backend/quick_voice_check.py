"""Quick interaction to confirm current Azure voice (male)"""
import requests, base64, uuid, pathlib, subprocess

backend_url = 'http://127.0.0.1:8000/api/assistant/query/text'
text = 'මගේ පැකේජය කොහෙද?'

print('Sending:', text)
r = requests.post(backend_url, json={'text': text}, timeout=30)
print('Status:', r.status_code)
print('Body:', r.text[:200])

r.raise_for_status()
data = r.json()
audio_b64 = data.get('response_audio')
if not audio_b64:
    print('No audio in response')
    raise SystemExit(1)

audio = base64.b64decode(audio_b64)
fname = pathlib.Path('quick_male_test_' + uuid.uuid4().hex[:6] + '.mp3')
fname.write_bytes(audio)
print('Saved', fname, 'size', len(audio))
subprocess.Popen([str(fname)], shell=True)
