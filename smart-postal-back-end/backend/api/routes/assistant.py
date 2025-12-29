"""
Sinhala Voice Assistant API Routes
Conversational AI for package tracking queries
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel
import base64
import requests
import os

# from models.database import get_db
# from models.user import User
# from models.order import Order
# from api.middleware.auth import get_current_user
from utils.sinhala_voice import sinhala_voice_processor
from config.settings import get_settings
from loguru import logger
try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_SDK_AVAILABLE = True
except Exception:
    speechsdk = None
    AZURE_SDK_AVAILABLE = False

try:
    from google.cloud import texttospeech
    GOOGLE_TTS_AVAILABLE = True
except Exception:
    texttospeech = None
    GOOGLE_TTS_AVAILABLE = False

# Import courier bot
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "services" / "sinhala_assistant"))

try:
    from courier_bot import load_env, resolve_model_name, initialize_model, handle_model_turn
    from gtts import gTTS
    import tempfile
    ASSISTANT_AVAILABLE = True
    TTS_AVAILABLE = True
except ImportError as e:
    ASSISTANT_AVAILABLE = False
    TTS_AVAILABLE = False
    logger.warning(f"Sinhala Assistant not available: {e}")

router = APIRouter(prefix="/api/assistant", tags=["Sinhala Assistant"])
settings = get_settings()


def synthesize_gemini_tts(text: str, voice_name: str = "Achernar", prompt: str = "Read aloud in a warm, friendly tone.") -> Optional[bytes]:
    """
    Use Google Cloud TTS v1beta1 API with Gemini 2.5 Pro TTS model for high-quality Sinhala speech.
    This is the BEST quality option for Sinhala pronunciation.
    
    Uses OAuth2 service account authentication for Vertex AI access.
    
    Args:
        text: The Sinhala text to synthesize
        voice_name: One of the Gemini voices (Achernar, Achird, Charon, Fenrir, Kore, Puck, etc.)
        prompt: Style prompt for how to read the text
    
    Returns:
        Audio bytes (MP3 format) or None if failed
    """
    import requests
    import json
    from pathlib import Path
    
    # Try to use service account for OAuth2 authentication (required for Vertex AI / Gemini TTS)
    service_account_path = Path(__file__).parent.parent.parent / "config" / "vertex-service-account.json"
    
    access_token = None
    if service_account_path.exists():
        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request
            
            credentials = service_account.Credentials.from_service_account_file(
                str(service_account_path),
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            credentials.refresh(Request())
            access_token = credentials.token
            logger.info(f"🔑 Using service account OAuth2 for Gemini TTS")
        except Exception as auth_err:
            logger.warning(f"Service account auth failed: {auth_err}")
    
    if not access_token:
        # Fallback to API key (may not work for Gemini model)
        api_key = settings.GOOGLE_CLOUD_TTS_API_KEY or os.getenv("GOOGLE_CLOUD_TTS_API_KEY")
        if not api_key:
            logger.warning("No service account or API key found for Gemini TTS")
            return None
        url = f"https://texttospeech.googleapis.com/v1beta1/text:synthesize?key={api_key}"
        headers = {"Content-Type": "application/json"}
    else:
        # Use OAuth2 token
        url = "https://texttospeech.googleapis.com/v1beta1/text:synthesize"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    
    payload = {
        "audioConfig": {
            "audioEncoding": "MP3",
            "pitch": 0,
            "speakingRate": 1
        },
        "input": {
            "text": text,
            "prompt": prompt
        },
        "voice": {
            "languageCode": "si-LK",
            "modelName": "gemini-2.5-pro-tts",
            "name": voice_name
        }
    }
    
    try:
        logger.info(f"🎯 Calling Gemini 2.5 Pro TTS for Sinhala with voice: {voice_name}")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            audio_content = result.get("audioContent")
            if audio_content:
                audio_bytes = base64.b64decode(audio_content)
                logger.info(f"✅ Gemini TTS success! Audio size: {len(audio_bytes)} bytes")
                return audio_bytes
            else:
                logger.warning("Gemini TTS response missing audioContent")
                return None
        else:
            logger.warning(f"Gemini TTS API error {response.status_code}: {response.text[:500]}")
            return None
            
    except Exception as e:
        logger.error(f"Gemini TTS request failed: {e}")
        return None


# Initialize bot model and chat session
_model_instance = None
_chat_sessions = {}  # Store chat sessions per user

def get_bot_session(user_id: int):
    """Get or create bot model and chat session for user"""
    global _model_instance, _chat_sessions
    
    if not ASSISTANT_AVAILABLE:
        return None, None
    
    # Initialize model once (shared across users)
    if _model_instance is None:
        try:
            _model_instance = initialize_model()
            logger.info("✓ Gemini model initialized")
        except Exception as e:
            logger.error(f"Failed to initialize model: {e}")
            return None, None
    
    # Get or create chat session for this user
    if user_id not in _chat_sessions:
        _chat_sessions[user_id] = _model_instance.start_chat(history=[])
        logger.info(f"✓ New chat session created for user {user_id}")
    
    return _model_instance, _chat_sessions[user_id]


class VoiceQueryRequest(BaseModel):
    """Voice query with optional user context"""
    tracking_id: Optional[str] = None


class TextQueryRequest(BaseModel):
    """Text-based query"""
    text: str
    tracking_id: Optional[str] = None


class QueryResponse(BaseModel):
    """Response from assistant"""
    success: bool
    response_text: str
    response_audio: Optional[str] = None  # Base64 encoded audio
    transcript: Optional[str] = None
    error: Optional[str] = None


@router.post("/query/voice", response_model=QueryResponse)
async def voice_query(
    file: UploadFile = File(...),
    tracking_id: Optional[str] = Form(None)
):
    """
    Process voice query in Sinhala
    User asks about packages, rates, etc.
    """
    if not ASSISTANT_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sinhala Assistant service not available"
        )
    
    try:
        # Test mode - no authentication required
        user_id = 999
        
        # 1. Transcribe audio to text
        logger.info(f"Processing voice query from user {user_id}")
        transcription = await sinhala_voice_processor.transcribe_audio(file)
        
        if not transcription["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Transcription failed: {transcription['error']}"
            )
        
        user_text = transcription["text"]
        logger.info(f"Transcribed: {user_text}")
        
        # 2. Get bot model and chat session
        model, chat = get_bot_session(user_id)
        if not model or not chat:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Assistant not initialized"
            )
        
        # 3. Process query through bot
        response_text, updated_chat = handle_model_turn(model, chat, user_text)
        
        # 4. Generate audio response using TTS
        response_audio = None
        if TTS_AVAILABLE:
            try:
                # Get configured voice settings
                gemini_voice = os.getenv("GEMINI_TTS_VOICE", "Kore")  # Kore = warm yet professional
                azure_voice = os.getenv("AZURE_SPEECH_VOICE", "si-LK-SameeraNeural")
                
                # Professional Sri Lankan customer service agent prompt
                tts_prompt = """Speak as a professional Sri Lankan postal service customer care representative.
Use authentic Sri Lankan Sinhala pronunciation with clear, pleasant intonation.
Maintain a courteous, respectful, and helpful tone - professional but approachable.
Speak at a measured, confident pace suitable for customer service.
Be polite and articulate. Avoid being too casual or overly familiar.
Sound competent, reliable, and service-oriented like a trained customer agent."""
                
                # === GEMINI 2.5 PRO TTS - PRIMARY (BEST Sinhala Quality!) ===
                gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
                if gemini_api_key:
                    logger.info(f"🎯 Trying Gemini 2.5 Pro TTS with voice: {gemini_voice}")
                    audio_bytes = synthesize_gemini_tts(
                        text=response_text,
                        voice_name=gemini_voice,
                        prompt=tts_prompt
                    )
                    if audio_bytes:
                        response_audio = base64.b64encode(audio_bytes).decode('utf-8')
                        logger.info(f"✅ Generated Gemini TTS audio ({len(audio_bytes)} bytes) - Premium Sinhala!")
                
                # === AZURE TTS - FALLBACK (Good Quality Neural Voice) ===
                if not response_audio and settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION and AZURE_SDK_AVAILABLE:
                    logger.info(f"Using Azure TTS with {azure_voice} (fallback)")
                    try:
                        speech_config = speechsdk.SpeechConfig(subscription=settings.AZURE_SPEECH_KEY, region=settings.AZURE_SPEECH_REGION)
                        speech_config.speech_synthesis_voice_name = azure_voice
                        speech_config.set_speech_synthesis_output_format(
                            speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
                        )
                        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
                        
                        ssml = f'''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="si-LK">
                            <voice name="{azure_voice}">
                                <prosody rate="0.9" pitch="-2%">
                                    {response_text}
                                </prosody>
                            </voice>
                        </speak>'''
                        
                        result = synthesizer.speak_ssml_async(ssml).get()
                        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                            audio_bytes = result.audio_data
                            response_audio = base64.b64encode(audio_bytes).decode('utf-8')
                            logger.info(f"✅ Generated Azure TTS audio ({len(audio_bytes)} bytes) - {azure_voice}")
                        else:
                            logger.warning(f"Azure TTS failed: {result.reason}")
                    except Exception as azure_err:
                        logger.warning(f"Azure TTS generation failed: {azure_err}")
                
                # NOTE: Gemini 2.5 Pro TTS is now PRIMARY (above), Azure is FALLBACK
                # Legacy Google Cloud TTS Neural2 and Standard engines removed (Gemini is better!)
                
            except Exception as tts_error:
                logger.warning(f"TTS generation failed: {tts_error}")

        
        # 5. Update chat session
        _chat_sessions[user_id] = updated_chat
        
        logger.info(f"Bot response: {response_text}")
        
        return QueryResponse(
            success=True,
            response_text=response_text,
            transcript=user_text,
            response_audio=response_audio,  # Base64 encoded MP3 audio
            error=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice query error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing voice query: {str(e)}"
        )


@router.post("/query/text", response_model=QueryResponse)
async def text_query(
    request: TextQueryRequest
):
    """
    Process text query in Sinhala
    Useful for testing without audio
    """
    print(f"=== TEXT QUERY START ===")
    print(f"AZURE_SDK_AVAILABLE: {AZURE_SDK_AVAILABLE}")
    print(f"TTS_AVAILABLE: {TTS_AVAILABLE}")
    
    if not ASSISTANT_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sinhala Assistant service not available"
        )
    
    try:
        # Test mode - no authentication required
        user_id = 999
        logger.info(f"Processing text query from user {user_id}: {request.text}")
        print(f"Query text: {request.text}")
        
        # Get bot model and chat session
        model, chat = get_bot_session(user_id)
        if not model or not chat:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Assistant not initialized"
            )
        
        # Process query
        response_text, updated_chat = handle_model_turn(model, chat, request.text)
        
        # Generate audio response using TTS
        response_audio = None
        if TTS_AVAILABLE:
            try:
                # Get configured voice settings
                gemini_voice = os.getenv("GEMINI_TTS_VOICE", "Kore")  # Kore = warm yet professional
                azure_voice = os.getenv("AZURE_SPEECH_VOICE", "si-LK-SameeraNeural")
                
                # Professional Sri Lankan customer service agent prompt
                tts_prompt = """Speak as a professional Sri Lankan postal service customer care representative.
Use authentic Sri Lankan Sinhala pronunciation with clear, pleasant intonation.
Maintain a courteous, respectful, and helpful tone - professional but approachable.
Speak at a measured, confident pace suitable for customer service.
Be polite and articulate. Avoid being too casual or overly familiar.
Sound competent, reliable, and service-oriented like a trained customer agent."""
                
                # === GEMINI 2.5 PRO TTS - PRIMARY (BEST Sinhala Quality!) ===
                gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
                if gemini_api_key:
                    logger.info(f"🎯 Trying Gemini 2.5 Pro TTS with voice: {gemini_voice}")
                    audio_bytes = synthesize_gemini_tts(
                        text=response_text,
                        voice_name=gemini_voice,
                        prompt=tts_prompt
                    )
                    if audio_bytes:
                        response_audio = base64.b64encode(audio_bytes).decode('utf-8')
                        logger.info(f"✅ Generated Gemini TTS audio ({len(audio_bytes)} bytes) - Premium Sinhala!")
                
                # === AZURE TTS - FALLBACK (Good Quality Neural Voice) ===
                if not response_audio and settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION and AZURE_SDK_AVAILABLE:
                    logger.info(f"Using Azure TTS with {azure_voice} (fallback)")
                    try:
                        speech_config = speechsdk.SpeechConfig(subscription=settings.AZURE_SPEECH_KEY, region=settings.AZURE_SPEECH_REGION)
                        speech_config.speech_synthesis_voice_name = azure_voice
                        speech_config.set_speech_synthesis_output_format(
                            speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
                        )
                        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
                        
                        ssml = f'''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="si-LK">
                            <voice name="{azure_voice}">
                                <prosody rate="0.9" pitch="-2%">
                                    {response_text}
                                </prosody>
                            </voice>
                        </speak>'''
                        
                        result = synthesizer.speak_ssml_async(ssml).get()
                        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                            audio_bytes = result.audio_data
                            response_audio = base64.b64encode(audio_bytes).decode('utf-8')
                            logger.info(f"✅ Generated Azure TTS audio ({len(audio_bytes)} bytes) - {azure_voice}")
                        else:
                            logger.warning(f"Azure TTS failed: {result.reason}")
                    except Exception as azure_err:
                        logger.warning(f"Azure TTS generation failed: {azure_err}")
                
                # NOTE: Gemini 2.5 Pro TTS is now PRIMARY (above), Azure is FALLBACK
                # Legacy Google Cloud TTS Neural2 and Standard engines removed (Gemini is better!)
                
            except Exception as tts_error:
                logger.warning(f"TTS generation failed: {tts_error}")
        
        # Update chat session
        _chat_sessions[user_id] = updated_chat
        
        logger.info(f"Bot response: {response_text}")
        
        return QueryResponse(
            success=True,
            response_text=response_text,
            transcript=request.text,
            response_audio=response_audio,
            error=None
        )
        
    except Exception as e:
        logger.error(f"Text query error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing text query: {str(e)}"
        )


# @router.get("/packages")
# async def get_packages(
#     db: Session = Depends(get_db),
#     current_user: User = Depends(get_current_user)
# ):
#     """
#     Get user's packages for assistant context
#     Connects mock data with real database
#     """
#     try:
#         # Get real orders from database
#         orders = db.query(Order).filter(
#             Order.customer_id == current_user.id
#         ).all()
#         
#         packages = []
#         for order in orders:
#             packages.append({
#                 "tracking_id": order.tracking_id,
#                 "status": order.status,
#                 "created_at": str(order.created_at),
#                 "delivery_address": order.delivery_address
#             })
#         
#         return {
#             "success": True,
#             "packages": packages,
#             "count": len(packages)
#         }
#         
#     except Exception as e:
#         logger.error(f"Error fetching packages: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=str(e)
#         )


@router.post("/reset-conversation")
async def reset_conversation():
    """Reset bot conversation history"""
    if not ASSISTANT_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Sinhala Assistant service not available"
        )
    
    try:
        global _chat_sessions, _model_instance
        
        # Test mode - no authentication required
        user_id = 999
        
        # Reset chat session for this user
        if user_id in _chat_sessions:
            del _chat_sessions[user_id]
            logger.info(f"Conversation reset for user {user_id}")
        
        # Recreate session
        if _model_instance:
            _chat_sessions[user_id] = _model_instance.start_chat(history=[])
        
        return {"success": True, "message": "Conversation reset"}
        
    except Exception as e:
        logger.error(f"Reset error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
