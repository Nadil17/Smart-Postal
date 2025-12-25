# CourierBot (Sinhala Courier Voice Assistant)

This prototype follows the requirements from `funtionspecification.md` to deliver a Sinhala-first voice agent for courier support. It now aligns with the documented tools (tracking lookup, shipping rate calculation, delivery rescheduling) while using Google Gemini for reasoning and OpenAI Whisper-grade speech recognition for audio input.

## Requirements Snapshot
- **LLM**: Google Gemini 3.x via `google-generativeai`. Configure an explicit model through `COURIERBOT_MODEL` when possible to avoid repeated discovery calls.
- **Speech-to-Text**: OpenAI Whisper pipeline through the official `openai` SDK (falls back to `SpeechRecognition`'s Google Web Speech if no key is provided).
- **Text-to-Speech**: `gTTS` placeholder output. Swap with Azure Neural voices when credentials are available.
- **Functions/Tools**: `get_tracking_status`, `calculate_shipping_rate`, `reschedule_delivery` exactly as described in the specification.

## Environment Variables
Create a `.env` file (loaded automatically) with at least:

```
GEMINI_API_KEY=your_gemini_key
OPENAI_API_KEY=your_openai_key
COURIERBOT_MODEL=gemini-2.5-pro
COURIERBOT_WHISPER_MODEL=whisper-1
COURIERBOT_LOCAL_WHISPER_MODEL=base
COURIERBOT_HISTORY_TURNS=8
COURIERBOT_REQUEST_COOLDOWN=0.75
COURIERBOT_LOOP_PAUSE=1.0
COURIERBOT_MIN_CHARS=2
COURIERBOT_MIC_DEVICE=0
```

Notes:
- `COURIERBOT_MODEL` prevents multiple `get_model` calls that would otherwise burn the Gemini quota when the API key lacks access to higher tiers.
- `OPENAI_API_KEY` is optional - if not set, the system will use local Whisper instead (see below).
- `COURIERBOT_LOCAL_WHISPER_MODEL` can be `tiny`, `base`, `small`, `medium`, or `large` (default: `base`). Larger models are more accurate but slower.
- `COURIERBOT_REQUEST_COOLDOWN` (seconds) and `COURIERBOT_HISTORY_TURNS` (conversation turns) are optional guards to keep request volume and token usage within limits.
- `COURIERBOT_LOOP_PAUSE` forces the loop to sleep between turns, and `COURIERBOT_MIN_CHARS` skips transcripts shorter than the threshold so blank inputs never hit Gemini.
- `COURIERBOT_MIC_DEVICE` is optional; set it only if you have multiple microphones and need a specific index.

## Speech Recognition Options
The bot tries these in order:
1. **OpenAI Whisper API** (if `OPENAI_API_KEY` is set) - cloud-based, fastest
2. **Local Whisper** (if `openai-whisper` is installed) - runs on your machine, no API key needed
3. **Google Web Speech** - fallback, less accurate for Sinhala

## Installation & Run
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python courier_bot.py
```

Speak in Sinhala (or Singlish) when prompted. If no microphone is available the program will fall back to console input. Responses are printed and synthesized to `response.mp3` via `gTTS` for manual playback.

## API Usage Tips
- Keep the CLI session focused: every Gemini turn (including tool responses) counts toward the rate limit.
- The built‑in cooldown plus history trimming limit burst traffic, but you can reduce the cooldown further if you have higher quotas.
- Tool functions rely on `mock_db.json`; `reschedule_delivery` persists any date changes back to that file so repeated tests reflect the latest schedule.
