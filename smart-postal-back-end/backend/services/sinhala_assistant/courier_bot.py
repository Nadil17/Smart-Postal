"""CourierBot: Sinhala voice assistant for Lanka Express courier service."""
from __future__ import annotations

import io
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import google.generativeai as genai
from dotenv import load_dotenv

try:  # pragma: no cover - optional dependency for OpenAI Whisper transcription
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

try:  # pragma: no cover - optional dependency for local Whisper
    import whisper
except ImportError:  # pragma: no cover
    whisper = None

# Optional audio libraries (stubs fall back to console)
try:  # pragma: no cover - optional dependency
    import speech_recognition as sr
except ImportError:  # pragma: no cover
    sr = None

try:  # pragma: no cover - optional dependency
    from gtts import gTTS
except ImportError:  # pragma: no cover
    gTTS = None

try:  # pragma: no cover - optional dependency
    import pygame
except ImportError:  # pragma: no cover
    pygame = None

try:  # pragma: no cover - optional dependency for Azure TTS
    import azure.cognitiveservices.speech as speechsdk
except ImportError:  # pragma: no cover
    speechsdk = None


PROJECT_ROOT = Path(__file__).resolve().parent
MOCK_DB_PATH = PROJECT_ROOT / "mock_db.json"
SYSTEM_PROMPT = (
    "You are a PROFESSIONAL customer support AI for 'Lanka Express' courier service in Sri Lanka. "
    "Always reply in natural, RESPECTFUL spoken Sinhala using FORMAL professional language. "
    "Be CONCISE - customers are in a hurry. Keep responses SHORT and helpful. "
    "Understand Singlish (Sinhala words typed/spoken in English letters) and respond accordingly. "
    "Never reveal driver phone numbers or personal contact info unless explicitly authorized by the data. "
    "\n\nTRACKING ID HANDLING:"
    "\n- Accept various formats: TRK001, TRK 001, TRK01, TRK 1, 'tea ar kay binduwai binduwai eka'"
    "\n- System will normalize to TRK001 format automatically"
    "\n- If tracking ID not found, say ONLY: 'Samawenna, tracking number eka system eke soyaganna bari una. Karunakara nawatath check karanna puluwan da?'"
    "\n- Use professional, polite language at all times"
    "\n\nPROFESSIONAL LANGUAGE RULES - CRITICAL:"
    "\n- Use 'obata' (ඔබට) not 'oyata' (ඔයාට) - more respectful"
    "\n- Use 'obata' (ඔබට) not 'obage' (ඔබගේ) or 'obe' (ඔබේ) when offering services"
    "\n- CORRECT: 'Obata awashya sewawa monawada?' NOT 'Obage awashya sewawa kumakda?'"
    "\n- Use 'karunakara' (කරුණාකර) for 'please' - adds politeness"
    "\n- Use 'subha dawasak' (ශුභ දවසක්) for 'have a good day' - more natural"
    "\n- Use 'awashya sewawa' (අවශ්‍ය සේවාව) for 'service you need'"
    "\n- NEVER use casual phrases like 'Apooo', 'Kohoma hari', 'Mata danna be', 'Eka gena kamak ne'"
    "\n- Keep ALL responses under 2 sentences unless providing tracking details"
    "\n- When customer says they don't need service, respond: 'Sthutyi obata. Subha dawasak wewa!'"
    "\n- When offering help, ask: 'Obata awashya sewawa monawada?' (use OBATA, not obage)"
    "\n- For errors or issues, use: 'Samawenna' (Sorry/Excuse me) to maintain professionalism"
    "\n\nCONTEXT MEMORY - CRITICAL: Remember tracking IDs the customer gives you in this conversation. "
    "If they ask follow-up questions like 'when will I get it?' or 'where is it?' - use the tracking ID from earlier. "
    "Do NOT ask for the tracking ID again unless this is truly the first time in this conversation. "
    "\n\nIMPORTANT: When a user provides a tracking ID (like TRK001, TRK 1, etc.), you MUST immediately call the get_tracking_status function. "
    "Do NOT just say 'I will check' - actually call the function and provide the real status. "
    "If the user asks for rates, IMMEDIATELY call calculate_shipping_rate with the cities and weight. "
    "If they want to reschedule, IMMEDIATELY call reschedule_delivery with the tracking ID and new date. "
    "\n\nWhen providing tracking status, ALWAYS include the estimated delivery date if available. "
    "\n\nExamples of CORRECT PROFESSIONAL responses: "
    "\n- For tracking: 'Parcel eka Kurunegala thiyenawa. Rider Saman athara deliver karanna enawa. December 25 wenakota labaganna puluwan.'"
    "\n- For rates: 'Colombo idan Kandy ta kilo 2k ekata rupiyaal 450 yi.'"
    "\n- For rescheduling: 'December 5 ta reschedule karala thiyenawa.'"
    "\n- When asking for tracking: 'Karunakara tracking number eka danaganna puluwan da?'"
    "\n- Offering more help: 'Obata awashya sewawa monawada?'"
    "\n- When customer is done: 'Sthutyi obata. Subha dawasak wewa!'"
    "\n- If not found: 'Samawenna, tracking number eka system eke soyaganna bari una. Karunakara nawatath check karanna puluwan da?'"
    "\n\nOFF-TOPIC QUESTIONS (weather, politics, recipes, etc.):"
    "\n- Politely redirect to courier services ONLY"
    "\n- Response: 'Samawenna, mata courier service gana witharai udaw karanna puluwan. Parcel ekak gana prashna thiyenawada?'"
    "\n- Keep the tone respectful and professional"
    "\n- Do NOT attempt to answer non-courier questions"
    "\n\nKeep it SHORT, CLEAR, PROFESSIONAL, and HELPFUL."
)
MODEL_FALLBACKS = [
    "gemini-3-pro-preview",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-flash-latest",
    "gemini-pro-latest",
]
REMOTE_CITY_SURCHARGE = {"jaffna", "trincomalee", "mullaitivu", "batticaloa"}
BASE_RATE_LKR = 350
KG_RATE_LKR = 50
REMOTE_SURCHARGE_LKR = 100
DEFAULT_MIN_TRANSCRIPT_CHARS = 2

def get_loop_pause() -> float:
    """Return sleep duration after each completed turn."""
    try:
        return max(float(os.getenv("COURIERBOT_LOOP_PAUSE", "1.0")), 0.0)
    except ValueError:
        return 1.0


def should_skip_transcript(text: str) -> bool:
    """Return True when the transcript is too short to send upstream."""
    if not text:
        return True
    stripped = text.strip()
    min_chars = DEFAULT_MIN_TRANSCRIPT_CHARS
    try:
        env_min = int(os.getenv("COURIERBOT_MIN_CHARS", str(min_chars)))
        min_chars = max(env_min, 1)
    except ValueError:
        pass
    return len(stripped) < min_chars
_RESOLVED_MODEL_NAME: Optional[str] = None
_LAST_GEN_CALL_TS = 0.0
OPENAI_CLIENT: Optional["OpenAI"] = None  # For Whisper STT only
WHISPER_MODEL: Optional[Any] = None

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger("courierbot")


def load_env() -> None:
    """Load environment variables for API credentials."""
    # Load from backend/config/.env
    config_env = PROJECT_ROOT.parent.parent / "config" / ".env"
    if config_env.exists():
        load_dotenv(config_env)
    else:
        load_dotenv()  # Fallback to default behavior
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        raise EnvironmentError("GEMINI_API_KEY is not set. Please create a .env file with the key.")
    genai.configure(api_key=gemini_key)
    if not os.getenv("COURIERBOT_MODEL"):
        logger.info("COURIERBOT_MODEL not set. Using automatic Gemini fallback discovery.")
    if not os.getenv("OPENAI_API_KEY"):
        logger.warning("OPENAI_API_KEY is not set. Falling back to SpeechRecognition for STT.")


def _discover_supported_models() -> List[str]:
    """Return models accessible to the API key that support generateContent."""
    try:
        models = genai.list_models()
    except Exception as exc:  # pragma: no cover - depends on network
        logger.warning("Unable to list Gemini models: %s", exc)
        return []
    names: List[str] = []
    for model in models:
        methods = getattr(model, "supported_generation_methods", [])
        if "generateContent" in methods:
            names.append(model.name.split("/", 1)[-1])
    return names


def resolve_model_name() -> str:
    """Pick the first accessible Gemini model, trying configured value then sensible fallbacks."""
    global _RESOLVED_MODEL_NAME
    if _RESOLVED_MODEL_NAME:
        return _RESOLVED_MODEL_NAME

    configured = os.getenv("COURIERBOT_MODEL")
    extra_fallbacks = os.getenv("COURIERBOT_FALLBACK_MODELS", "")
    candidates: List[str] = []
    if configured:
        candidates.append(configured)
    candidates.extend([name.strip() for name in extra_fallbacks.split(",") if name.strip()])
    candidates.extend(MODEL_FALLBACKS)
    candidates.extend(_discover_supported_models())

    seen: set[str] = set()
    for candidate in candidates:
        model_name = candidate.strip()
        if not model_name or model_name in seen:
            continue
        seen.add(model_name)
        model_path = model_name if model_name.startswith("models/") else f"models/{model_name}"
        try:
            genai.get_model(model_path)
            resolved = model_name.split("models/")[-1]
            logger.info("Using Gemini model %s", resolved)
            _RESOLVED_MODEL_NAME = resolved
            return resolved
        except Exception as exc:
            logger.warning("Model %s unavailable: %s", model_name, exc)
    raise RuntimeError("No accessible Gemini model. Update COURIERBOT_MODEL or ensure API access.")


def read_json_file(path: Path) -> Dict[str, Any]:
    """Read a JSON file safely, returning an empty dict on failure."""
    if not path.exists():
        logger.warning("%s not found. Returning empty dictionary.", path)
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json_file(path: Path, payload: Any) -> None:
    """Persist JSON payload to disk with UTF-8 encoding."""
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def get_tracking_status(tracking_id: str) -> Dict[str, Any]:
    """Return parcel status, location, and rider name for a given tracking ID."""
    database = read_json_file(MOCK_DB_PATH)
    
    # Normalize tracking ID: TRK01 -> TRK001, TRK 1 -> TRK001, etc.
    normalized_id = tracking_id.upper().replace(" ", "")
    if normalized_id.startswith("TRK"):
        # Extract number part after TRK
        num_part = normalized_id[3:]
        if num_part.isdigit():
            # Pad to 3 digits: 1 -> 001, 01 -> 001
            normalized_id = f"TRK{num_part.zfill(3)}"
    
    record = database.get(normalized_id)
    if not record:
        return {"tracking_id": normalized_id, "status": "Not Found"}
    payload = {
        "tracking_id": normalized_id,
        "status": record.get("status", "Unknown"),
        "location": record.get("location", "Unknown"),
        "rider": record.get("rider", "Unknown"),
        "last_update": record.get("last_update", datetime.now(timezone.utc).isoformat()),
    }
    # Include estimated or actual delivery date
    if record.get("estimated_delivery"):
        payload["estimated_delivery"] = record["estimated_delivery"]
    if record.get("delivered_on"):
        payload["delivered_on"] = record["delivered_on"]
    if record.get("rescheduled_for"):
        payload["rescheduled_for"] = record["rescheduled_for"]
    return payload


def calculate_shipping_rate(origin_city: str, destination_city: str, weight_kg: float) -> Dict[str, Any]:
    """Compute shipping cost based on origin/destination and weight rules."""
    try:
        normalized_weight = max(float(weight_kg), 0.1)
    except (ValueError, TypeError):
        raise ValueError("weight_kg must be a numeric value")

    base_cost = BASE_RATE_LKR + KG_RATE_LKR * normalized_weight
    destination_key = destination_city.lower().strip()
    origin_key = origin_city.lower().strip()
    remote_fee = REMOTE_SURCHARGE_LKR if destination_key in REMOTE_CITY_SURCHARGE else 0
    same_city_discount = -50 if origin_key == destination_key else 0
    total = round(base_cost + remote_fee + same_city_discount, 2)
    return {
        "origin_city": origin_city,
        "destination_city": destination_city,
        "weight_kg": normalized_weight,
        "is_remote_destination": bool(remote_fee),
        "same_city_discount_applied": bool(same_city_discount),
        "total_lkr": total,
    }


def reschedule_delivery(tracking_id: str, new_date: str) -> Dict[str, Any]:
    """Update the targeted delivery date for a tracking ID and persist it."""
    database = read_json_file(MOCK_DB_PATH)
    record_key = tracking_id.upper()
    record = database.get(record_key)
    if not record:
        return {"tracking_id": tracking_id, "status": "Not Found"}

    try:
        parsed_date = datetime.fromisoformat(new_date).date().isoformat()
    except ValueError:
        raise ValueError("new_date must be ISO format YYYY-MM-DD")

    record["rescheduled_for"] = parsed_date
    record["last_update"] = datetime.now(timezone.utc).isoformat()
    database[record_key] = record
    write_json_file(MOCK_DB_PATH, database)
    return {
        "tracking_id": tracking_id,
        "status": record.get("status", "Unknown"),
        "rescheduled_for": parsed_date,
    }


def build_tools() -> List[genai.types.Tool]:
    """Define Gemini function schemas for tool calling."""
    get_status_fn = genai.types.FunctionDeclaration(
        name="get_tracking_status",
        description="Lookup a Lanka Express tracking ID and return its latest status",
        parameters={
            "type": "object",
            "properties": {
                "tracking_id": {
                    "type": "string",
                    "description": "Tracking number",
                }
            },
            "required": ["tracking_id"],
        },
    )

    calc_rate_fn = genai.types.FunctionDeclaration(
        name="calculate_shipping_rate",
        description="Calculate parcel shipping cost in LKR",
        parameters={
            "type": "object",
            "properties": {
                "origin_city": {
                    "type": "string",
                    "description": "Pickup city",
                },
                "destination_city": {
                    "type": "string",
                    "description": "Drop-off city",
                },
                "weight_kg": {
                    "type": "number",
                    "description": "Weight in kilograms",
                },
            },
            "required": ["origin_city", "destination_city", "weight_kg"],
        },
    )

    reschedule_fn = genai.types.FunctionDeclaration(
        name="reschedule_delivery",
        description="Update a delivery date for an existing tracking ID",
        parameters={
            "type": "object",
            "properties": {
                "tracking_id": {
                    "type": "string",
                    "description": "Tracking number",
                },
                "new_date": {
                    "type": "string",
                    "description": "Preferred delivery date (YYYY-MM-DD)",
                },
            },
            "required": ["tracking_id", "new_date"],
        },
    )

    return [genai.types.Tool(function_declarations=[get_status_fn, calc_rate_fn, reschedule_fn])]


def initialize_model() -> Any:
    """Initialize and return Gemini model."""
    load_env()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY not set in .env file")
    
    logger.info("Using Google Gemini API")
    genai.configure(api_key=api_key)
    tools = build_tools()
    model_name = resolve_model_name()
    
    # Relax safety settings for business conversations
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    return genai.GenerativeModel(
        model_name=model_name,
        system_instruction=SYSTEM_PROMPT,
        tools=tools,
        generation_config={"temperature": 0.3, "max_output_tokens": 512},
        safety_settings=safety_settings,
    )


def get_history_turn_limit() -> int:
    """Return the configured history cap (user+assistant pairs)."""
    try:
        return max(int(os.getenv("COURIERBOT_HISTORY_TURNS", "8")), 1)
    except ValueError:
        return 8


def get_request_cooldown() -> float:
    """Return the minimum seconds between Gemini requests."""
    try:
        return max(float(os.getenv("COURIERBOT_REQUEST_COOLDOWN", "0.75")), 0.0)
    except ValueError:
        return 0.75


def get_openai_client() -> Optional[OpenAI]:
    """Return a memoized OpenAI client if credentials are available."""
    if OpenAI is None:
        return None
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    global OPENAI_CLIENT
    if OPENAI_CLIENT is None:
        OPENAI_CLIENT = OpenAI(api_key=api_key)
    return OPENAI_CLIENT


def get_whisper_model() -> Optional[Any]:
    """Load and cache local Whisper model."""
    if whisper is None:
        return None
    global WHISPER_MODEL
    if WHISPER_MODEL is None:
        model_size = os.getenv("COURIERBOT_LOCAL_WHISPER_MODEL", "base")
        logger.info("Loading local Whisper model '%s' (this may take a moment)...", model_size)
        try:
            WHISPER_MODEL = whisper.load_model(model_size)
        except Exception as exc:
            logger.error("Failed to load Whisper model: %s", exc)
            return None
    return WHISPER_MODEL


def transcribe_with_local_whisper(audio_data: "sr.AudioData") -> Optional[str]:
    """Use local OpenAI Whisper model for Sinhala transcription."""
    model = get_whisper_model()
    if model is None:
        return None
    
    # Save audio temporarily
    import tempfile
    wav_data = audio_data.get_wav_data(convert_rate=16000, convert_width=2)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(wav_data)
        tmp_path = tmp.name
    
    try:
        result = model.transcribe(tmp_path, language="si", fp16=False)
        return result["text"].strip()
    except Exception as exc:
        logger.error("Local Whisper transcription failed: %s", exc)
        return None
    finally:
        import os as os_module
        try:
            os_module.unlink(tmp_path)
        except Exception:
            pass


def transcribe_with_openai(audio_data: "sr.AudioData") -> Optional[str]:
    """Use OpenAI Whisper API for Sinhala audio."""
    client = get_openai_client()
    if client is None:
        return None
    wav_data = audio_data.get_wav_data(convert_rate=16000, convert_width=2)
    buffer = io.BytesIO(wav_data)
    buffer.name = "courierbot-input.wav"
    model_name = os.getenv("COURIERBOT_WHISPER_MODEL", "whisper-1")
    try:
        result = client.audio.transcriptions.create(
            model=model_name,
            file=buffer,
            response_format="text",
            language="si",
        )
    except Exception as exc:  # pragma: no cover - depends on network
        logger.error("OpenAI API transcription failed: %s", exc)
        return None
    if isinstance(result, str):
        return result.strip()
    return getattr(result, "text", "").strip()


def transcribe_from_microphone() -> Optional[str]:
    """Capture Sinhala speech via microphone; fallback to keyboard input if unavailable."""
    if sr is None:
        return None
    mic_kwargs: Dict[str, Any] = {}
    mic_device = os.getenv("COURIERBOT_MIC_DEVICE")
    if mic_device:
        try:
            mic_kwargs["device_index"] = int(mic_device)
        except ValueError:
            logger.warning("Invalid COURIERBOT_MIC_DEVICE value '%s'", mic_device)
    try:
        recognizer = sr.Recognizer()
        with sr.Microphone(**mic_kwargs) as source:
            logger.info("🎙️ දැනට ඔබට කතා කළ හැක. Listening...")
            try:
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            except sr.WaitTimeoutError:
                logger.info("No speech detected, continuing...")
                return None
    except (AttributeError, OSError) as exc:
        logger.warning("Microphone input unavailable%s: %s", f" (device {mic_device})" if mic_device else "", exc)
        if hasattr(sr, "Microphone"):
            try:
                devices = sr.Microphone.list_microphone_names()
                if devices:
                    logger.info("Available input devices: %s", ", ".join(devices))
            except Exception:  # pragma: no cover - diagnostic only
                pass
        return None

    # Try OpenAI API first if available
    transcript = transcribe_with_openai(audio)
    if transcript:
        return transcript
    
    # Try local Whisper if available
    transcript = transcribe_with_local_whisper(audio)
    if transcript:
        return transcript

    # Fall back to Google Web Speech
    try:
        return recognizer.recognize_google(audio, language="si-LK")
    except sr.UnknownValueError:
        logger.error("Could not understand audio")
    except sr.RequestError as exc:
        logger.error("Speech recognition error: %s", exc)
    return None


def speak_sinhala(text: str) -> None:
    """Convert Sinhala text to speech via Azure TTS, gTTS, or fallback to console.
    
    TTS ENGINE SELECTION:
    ====================
    Set COURIERBOT_TTS_ENGINE environment variable:
    - 'azure' = Azure Cognitive Services (BEST Sinhala pronunciation)
    - 'gtts' = Google Text-to-Speech (default, free but robotic)
    
    AZURE TTS SETUP (Recommended for production):
    ============================================
    1. Install: pip install azure-cognitiveservices-speech
    2. Get free Azure account: https://azure.microsoft.com/free/
    3. Create Speech Service resource
    4. Set environment variables:
       AZURE_SPEECH_KEY=your_key_here
       AZURE_SPEECH_REGION=eastus (or your region)
    5. Set COURIERBOT_TTS_ENGINE=azure
    
    Sinhala voices available:
    - si-LK-ThiliniNeural (female, natural)
    - si-LK-SameeraNeural (male, natural)
    
    Cost: $1 per 1M characters (very affordable)
    """
    tts_engine = os.getenv("COURIERBOT_TTS_ENGINE", "gtts").lower()
    
    # Try Azure TTS first if configured
    if tts_engine == "azure" and speechsdk is not None:
        azure_key = os.getenv("AZURE_SPEECH_KEY")
        azure_region = os.getenv("AZURE_SPEECH_REGION")
        
        if azure_key and azure_region:
            try:
                speech_config = speechsdk.SpeechConfig(subscription=azure_key, region=azure_region)
                speech_config.speech_synthesis_voice_name = "si-LK-ThiliniNeural"  # Female Sinhala voice
                
                file_name = PROJECT_ROOT / "response.wav"
                audio_config = speechsdk.audio.AudioOutputConfig(filename=str(file_name))
                
                synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=audio_config)
                result = synthesizer.speak_text_async(text).get()
                
                if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                    logger.info("🔊 Playing Azure TTS audio...")
                    
                    # Play the WAV file with pygame
                    if pygame is not None:
                        pygame.mixer.init()
                        pygame.mixer.music.load(str(file_name))
                        pygame.mixer.music.play()
                        while pygame.mixer.music.get_busy():
                            pygame.time.Clock().tick(10)
                        pygame.mixer.quit()
                        logger.info("✅ Audio playback complete.")
                    else:
                        os.system(f'powershell -c "(New-Object Media.SoundPlayer \"{file_name}\").PlaySync()"')
                    return
                else:
                    logger.warning("Azure TTS failed: %s. Falling back to gTTS.", result.reason)
            except Exception as azure_exc:
                logger.warning("Azure TTS error: %s. Falling back to gTTS.", azure_exc)
        else:
            logger.warning("Azure TTS credentials not set. Falling back to gTTS.")
    
    # Fall back to gTTS
    if gTTS is None:
        logger.info("🔊 %s", text)
        return
    try:
        tts = gTTS(text=text, lang="si", slow=False)
        file_name = PROJECT_ROOT / "response.mp3"
        tts.save(str(file_name))
        logger.info("🔊 Playing audio...")
        
        # Use pygame for non-blocking audio playback
        if pygame is not None:
            try:
                pygame.mixer.init()
                pygame.mixer.music.load(str(file_name))
                pygame.mixer.music.play()
                # Wait for audio to finish playing
                while pygame.mixer.music.get_busy():
                    pygame.time.Clock().tick(10)
                pygame.mixer.quit()
                logger.info("✅ Audio playback complete.")
            except Exception as play_exc:
                logger.warning("pygame playback failed: %s. Using PowerShell fallback.", play_exc)
                os.system(f'powershell -c "(New-Object Media.SoundPlayer \"{file_name}\").PlaySync()"')
        else:
            # pygame not available, use PowerShell SoundPlayer
            logger.info("pygame not available. Using PowerShell SoundPlayer.")
            os.system(f'powershell -c "(New-Object Media.SoundPlayer \"{file_name}\").PlaySync()"')
    except Exception as exc:  # pragma: no cover
        logger.error("gTTS synthesis failed: %s", exc)
        logger.info("🔊 %s", text)


FUNCTION_MAP: Dict[str, Callable[..., Dict[str, Any]]] = {
    "get_tracking_status": get_tracking_status,
    "calculate_shipping_rate": calculate_shipping_rate,
    "reschedule_delivery": reschedule_delivery,
}


def enforce_request_cooldown() -> None:
    """Simple client-side throttling to avoid spiking Gemini quotas."""
    cooldown = get_request_cooldown()
    if cooldown <= 0:
        return
    global _LAST_GEN_CALL_TS
    now = time.monotonic()
    elapsed = now - _LAST_GEN_CALL_TS
    if elapsed < cooldown:
        time.sleep(cooldown - elapsed)
    _LAST_GEN_CALL_TS = time.monotonic()


def trim_chat_history(model: genai.GenerativeModel, chat: genai.ChatSession) -> genai.ChatSession:
    """Ensure we only keep the most recent N turns to limit token growth."""
    history = getattr(chat, "history", [])
    max_messages = get_history_turn_limit() * 2
    if not history or len(history) <= max_messages:
        return chat
    trimmed_history = history[-max_messages:]
    return model.start_chat(history=trimmed_history)


def execute_function_call(function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatch Gemini function calls to local Python implementations."""
    handler = FUNCTION_MAP.get(function_name)
    if handler is None:
        raise ValueError(f"Function {function_name} is not implemented")
    return handler(**arguments)


def handle_model_turn(
    model: Any, chat: Any, user_text: str
) -> Tuple[str, Any]:
    """Send user input to Gemini and resolve any tool calls."""
    return handle_gemini_turn(model, chat, user_text)


def handle_gemini_turn(
    model: Any, chat: Any, user_text: str
) -> Tuple[str, Any]:
    """Handle Gemini LLM turn with function calling."""
    enforce_request_cooldown()
    response = chat.send_message(user_text)
    while True:
        function_call = extract_function_call(response)
        if not function_call:
            break
        fn_name, fn_args = function_call
        logger.info("Gemini requested function %s with args %s", fn_name, fn_args)
        try:
            result = execute_function_call(fn_name, fn_args)
        except Exception as exc:
            result = {"error": str(exc)}
        enforce_request_cooldown()
        response = chat.send_message(
            {
                "role": "tool",
                "parts": [
                    {
                        "function_response": {
                            "name": fn_name,
                            "response": result,
                        }
                    }
                ],
            }
        )
    final_text = ""
    # Check for safety or other finish reasons first
    candidates = getattr(response, "candidates", [])
    if candidates:
        candidate = candidates[0]
        finish_reason = getattr(candidate, "finish_reason", None)
        logger.debug("Response finish_reason: %s", finish_reason)
        
        if finish_reason == 2:  # SAFETY
            # Log safety ratings for debugging
            safety_ratings = getattr(candidate, "safety_ratings", [])
            logger.warning("Response blocked by safety filter. Ratings: %s", safety_ratings)
            final_text = "Mata samawenna, tracking ID eka denawada?"
        elif finish_reason == 3:  # RECITATION
            final_text = "මට මේ පිළිතුර දීමට නොහැක. වෙනත් උදව්වක් අවශ්‍යද?"
        elif hasattr(candidate.content, "parts") and candidate.content.parts:
            for part in candidate.content.parts:
                if hasattr(part, "text") and part.text:
                    final_text += part.text
        else:
            final_text = "මට මොකක්ද කියලා තව පැහැදිලි කරන්න."
    else:
        final_text = "මට මොකක්ද කියලා තව පැහැදිලි කරන්න."
    updated_chat = trim_chat_history(model, chat)
    fallback = "මට මොකක්ද කියලා තව පැහැදිලි කරන්න."
    return (final_text or fallback), updated_chat


def extract_function_call(response: Any) -> Optional[tuple[str, Dict[str, Any]]]:
    """Inspect Gemini response for a function call request."""
    candidates = getattr(response, "candidates", [])
    for candidate in candidates:
        for part in candidate.content.parts:
            fn_call = getattr(part, "function_call", None)
            if fn_call:
                args = dict(fn_call.args or {})
                return fn_call.name, args
    return None


def chat_session() -> None:
    """Main console loop simulating the Sinhala voice assistant."""
    model = initialize_model()
    chat = model.start_chat(history=[])  # Gemini only
    
    logger.info("CourierBot සූදානම්. Type your Sinhala query or 'exit' to quit.")

    while True:
        transcript = transcribe_from_microphone()
        if transcript is None:
            transcript = input("ඔබේ ප්‍රශ්නය (type in Sinhala/Singlish): ").strip()
        if should_skip_transcript(transcript):
            logger.info("No speech detected, skipping...")
            logger.info("හොඳයි, දයක දාන්න.")
            continue
        
        # Check for stop/exit commands (English and Sinhala)
        stop_words = {"exit", "quit", "bye", "stop", "nawathanna", "nawathannako", 
                      "ඉවරයි", "ස්තූතියි", "bye bye", "thawa ona ne"}
        if any(word in transcript.lower() for word in stop_words):
            reply = "Sewawa sapayeemata labunata sthutyi. Obata honda dinayak wewa!"
            logger.info("🤖 CourierBot: %s", reply)
            speak_sinhala(reply)
            logger.info("Session ended. 👋")
            break

        logger.info("👤 User: %s", transcript)
        reply, chat = handle_model_turn(model, chat, transcript)
        logger.info("🤖 CourierBot: %s", reply)
        speak_sinhala(reply)
        
        # Auto-exit if bot says goodbye/thank you
        goodbye_phrases = ["sthutyi", "sthuuthi", "honda dinayak", "gihilla", "ayubowan", 
                          "ස්තූතියි", "හොන්ද දිනයක"]
        if any(phrase in reply.lower() for phrase in goodbye_phrases):
            logger.info("Session ended automatically. 👋")
            break
            
        pause = get_loop_pause()
        if pause:
            time.sleep(pause)


def main() -> None:
    """Entry point for running CourierBot via CLI."""
    try:
        chat_session()
    except KeyboardInterrupt:
        logger.info("Session closed by user.")
    except EnvironmentError as env_error:
        logger.error(env_error)
    except Exception as exc:  # pragma: no cover
        logger.exception("Unexpected failure: %s", exc)


if __name__ == "__main__":
    main()
