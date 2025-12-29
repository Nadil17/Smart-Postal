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
                # Get engine from settings or env, default to azure
                engine = getattr(settings, "COURIERBOT_TTS_ENGINE", None)
                if not engine:
                    engine = os.getenv("COURIERBOT_TTS_ENGINE", "gtts")
                engine = engine.lower()
                
                logger.info(f"TTS Engine configured: {engine}")
                logger.info(f"Google TTS available: {GOOGLE_TTS_AVAILABLE}")
                logger.info(f"Azure SDK available: {AZURE_SDK_AVAILABLE}")
                logger.info(f"Azure Key set: {bool(settings.AZURE_SPEECH_KEY)}")
                logger.info(f"Azure Region set: {bool(settings.AZURE_SPEECH_REGION)}")
                
                # Gemini / Vertex TTS via service account (premium quality!)
                if engine == "gemini" and GOOGLE_TTS_AVAILABLE:
                    logger.info("Using Google Cloud TTS with service account - Premium voice")
                    try:
                        # Set service account credentials if available
                        service_account_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                        if service_account_path:
                            import pathlib
                            abs_path = pathlib.Path(__file__).parent.parent.parent / service_account_path
                            if abs_path.exists():
                                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(abs_path)
                        
                        client = texttospeech.TextToSpeechClient()
                        synthesis_input = texttospeech.SynthesisInput(text=response_text)
                        
                        # Auto-select best voice for Sinhala
                        voice = texttospeech.VoiceSelectionParams(
                            language_code="si-LK",
                            ssml_gender=texttospeech.SsmlVoiceGender.MALE
                        )
                        
                        audio_config = texttospeech.AudioConfig(
                            audio_encoding=texttospeech.AudioEncoding.MP3,
                            speaking_rate=0.95,
                            pitch=-1.0
                        )
                        
                        response_tts = client.synthesize_speech(
                            input=synthesis_input, voice=voice, audio_config=audio_config
                        )
                        
                        audio_bytes = response_tts.audio_content
                        response_audio = base64.b64encode(audio_bytes).decode('utf-8')
                        logger.info(f"✅ Generated Google TTS audio ({len(audio_bytes)} bytes) - Service Account Premium")
                        
                    except Exception as gem_err:
                        logger.warning(f"Gemini TTS error: {gem_err}")
                        engine = "google"

                # Google Cloud TTS - fallback
                if not response_audio and engine == "google" and settings.GOOGLE_CLOUD_TTS_API_KEY and GOOGLE_TTS_AVAILABLE:
                    logger.info("Using Google Cloud TTS - Standard")
                    try:
                        client = texttospeech.TextToSpeechClient(
                            client_options={"api_key": settings.GOOGLE_CLOUD_TTS_API_KEY}
                        )
                        synthesis_input = texttospeech.SynthesisInput(text=response_text)
                        voice = texttospeech.VoiceSelectionParams(
                            language_code="si-LK",
                            ssml_gender=texttospeech.SsmlVoiceGender.MALE
                        )
                        audio_config = texttospeech.AudioConfig(
                            audio_encoding=texttospeech.AudioEncoding.MP3,
                            speaking_rate=0.95,
                            pitch=-1.0
                        )
                        response_tts = client.synthesize_speech(
                            input=synthesis_input, voice=voice, audio_config=audio_config
                        )
                        audio_bytes = response_tts.audio_content
                        response_audio = base64.b64encode(audio_bytes).decode('utf-8')
                        logger.info(f"✅ Generated Google TTS audio ({len(audio_bytes)} bytes) - Standard")
                    except Exception as google_err:
                        logger.warning(f"Google TTS generation failed: {google_err}")
                        engine = "azure"
                
                # Azure TTS if configured and sdk available
                if not response_audio and engine == "azure" and settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION and AZURE_SDK_AVAILABLE:
                    logger.info("Using Azure TTS with si-LK-SameeraNeural (Male)")
                    try:
                        speech_config = speechsdk.SpeechConfig(subscription=settings.AZURE_SPEECH_KEY, region=settings.AZURE_SPEECH_REGION)
                        # Male Sinhala voice (si-LK-SameeraNeural)
                        speech_config.speech_synthesis_voice_name = "si-LK-SameeraNeural"
                        speech_config.set_speech_synthesis_output_format(
                            speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
                        )
                        # Use None for audio_config to get audio data directly from result
                        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
                        
                        # Create SSML for more natural, native-sounding speech
                        # rate: 0.9 = slightly slower (more clear)
                        # pitch: -2% = slightly lower (more natural for male voice)
                        ssml = f'''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="si-LK">
                            <voice name="si-LK-SameeraNeural">
                                <prosody rate="0.9" pitch="-2%">
                                    {response_text}
                                </prosody>
                            </voice>
                        </speak>'''
                        
                        result = synthesizer.speak_ssml_async(ssml).get()
                        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                            # Get audio data directly from result (avoids file locking issues)
                            audio_bytes = result.audio_data
                            response_audio = base64.b64encode(audio_bytes).decode('utf-8')
                            logger.info(f"✅ Generated Azure TTS audio ({len(audio_bytes)} bytes) - Natural Sinhala voice")
                        else:
                            logger.warning(f"Azure TTS failed: {result.reason}")
                    except Exception as azure_err:
                        logger.warning(f"Azure TTS generation failed: {azure_err}")
                        # Fall back to gTTS below if available
                        engine = "gtts"

                # gTTS fallback
                if engine == "gtts":
                    try:
                        tts = gTTS(text=response_text, lang="si", slow=False)
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
                            tts.save(temp_audio.name)
                            temp_audio_path = temp_audio.name
                        with open(temp_audio_path, "rb") as audio_file:
                            audio_bytes = audio_file.read()
                            response_audio = base64.b64encode(audio_bytes).decode('utf-8')
                        os.unlink(temp_audio_path)
                        logger.info(f"Generated gTTS audio ({len(audio_bytes)} bytes)")
                    except Exception as tts_error:
                        logger.warning(f"gTTS generation failed: {tts_error}")
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
                # Get engine from settings or env, default to azure
                engine = getattr(settings, "COURIERBOT_TTS_ENGINE", None)
                if not engine:
                    engine = os.getenv("COURIERBOT_TTS_ENGINE", "gtts")
                engine = engine.lower()
                
                logger.info(f"TTS Engine configured: {engine}")
                logger.info(f"Google TTS available: {GOOGLE_TTS_AVAILABLE}")
                logger.info(f"Azure SDK available: {AZURE_SDK_AVAILABLE}")
                logger.info(f"Azure Key set: {bool(settings.AZURE_SPEECH_KEY)}")
                logger.info(f"Azure Region set: {bool(settings.AZURE_SPEECH_REGION)}")
                
                # Gemini / Vertex TTS via service account (premium quality!)
                if engine == "gemini" and GOOGLE_TTS_AVAILABLE:
                    logger.info("Using Google Cloud TTS with service account - Premium voice")
                    try:
                        # Set service account credentials if available
                        service_account_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
                        if service_account_path:
                            import pathlib
                            abs_path = pathlib.Path(__file__).parent.parent.parent / service_account_path
                            if abs_path.exists():
                                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(abs_path)
                        
                        client = texttospeech.TextToSpeechClient()
                        synthesis_input = texttospeech.SynthesisInput(text=response_text)
                        
                        # Auto-select best voice for Sinhala
                        voice = texttospeech.VoiceSelectionParams(
                            language_code="si-LK",
                            ssml_gender=texttospeech.SsmlVoiceGender.MALE
                        )
                        
                        audio_config = texttospeech.AudioConfig(
                            audio_encoding=texttospeech.AudioEncoding.MP3,
                            speaking_rate=0.95,
                            pitch=-1.0
                        )
                        
                        response_tts = client.synthesize_speech(
                            input=synthesis_input, voice=voice, audio_config=audio_config
                        )
                        
                        audio_bytes = response_tts.audio_content
                        response_audio = base64.b64encode(audio_bytes).decode('utf-8')
                        logger.info(f"✅ Generated Google TTS audio ({len(audio_bytes)} bytes) - Service Account Premium")
                        
                    except Exception as gem_err:
                        logger.warning(f"Gemini TTS error: {gem_err}")
                        engine = "google"

                # Google Cloud TTS - fallback
                if not response_audio and engine == "google" and settings.GOOGLE_CLOUD_TTS_API_KEY and GOOGLE_TTS_AVAILABLE:
                    logger.info("Using Google Cloud TTS - Standard")
                    try:
                        client = texttospeech.TextToSpeechClient(
                            client_options={"api_key": settings.GOOGLE_CLOUD_TTS_API_KEY}
                        )
                        synthesis_input = texttospeech.SynthesisInput(text=response_text)
                        voice = texttospeech.VoiceSelectionParams(
                            language_code="si-LK",
                            ssml_gender=texttospeech.SsmlVoiceGender.MALE
                        )
                        audio_config = texttospeech.AudioConfig(
                            audio_encoding=texttospeech.AudioEncoding.MP3,
                            speaking_rate=0.95,
                            pitch=-1.0
                        )
                        response_tts = client.synthesize_speech(
                            input=synthesis_input, voice=voice, audio_config=audio_config
                        )
                        audio_bytes = response_tts.audio_content
                        response_audio = base64.b64encode(audio_bytes).decode('utf-8')
                        logger.info(f"✅ Generated Google TTS audio ({len(audio_bytes)} bytes) - Standard")
                    except Exception as google_err:
                        logger.warning(f"Google TTS generation failed: {google_err}")
                        engine = "azure"
                
                # Azure TTS if configured and sdk available
                if not response_audio and engine == "azure" and settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION and AZURE_SDK_AVAILABLE:
                    logger.info("Using Azure TTS with si-LK-SameeraNeural (Male)")
                    try:
                        speech_config = speechsdk.SpeechConfig(subscription=settings.AZURE_SPEECH_KEY, region=settings.AZURE_SPEECH_REGION)
                        # Male Sinhala voice (si-LK-SameeraNeural)
                        speech_config.speech_synthesis_voice_name = "si-LK-SameeraNeural"
                        speech_config.set_speech_synthesis_output_format(
                            speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
                        )
                        # Use None for audio_config to get audio data directly from result
                        synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
                        
                        # Create SSML for more natural, native-sounding speech
                        # rate: 0.9 = slightly slower (more clear)
                        # pitch: -2% = slightly lower (more natural for male voice)
                        ssml = f'''<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="si-LK">
                            <voice name="si-LK-SameeraNeural">
                                <prosody rate="0.9" pitch="-2%">
                                    {response_text}
                                </prosody>
                            </voice>
                        </speak>'''
                        
                        result = synthesizer.speak_ssml_async(ssml).get()
                        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                            # Get audio data directly from result (avoids file locking issues)
                            audio_bytes = result.audio_data
                            response_audio = base64.b64encode(audio_bytes).decode('utf-8')
                            logger.info(f"✅ Generated Azure TTS audio ({len(audio_bytes)} bytes) - Natural Sinhala voice")
                        else:
                            logger.warning(f"Azure TTS failed: {result.reason}")
                    except Exception as azure_err:
                        logger.warning(f"Azure TTS generation failed: {azure_err}")
                        # Fall back to gTTS below if available
                        engine = "gtts"

                # gTTS fallback
                if engine == "gtts":
                    try:
                        tts = gTTS(text=response_text, lang="si", slow=False)
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
                            tts.save(temp_audio.name)
                            temp_audio_path = temp_audio.name
                        with open(temp_audio_path, "rb") as audio_file:
                            audio_bytes = audio_file.read()
                            response_audio = base64.b64encode(audio_bytes).decode('utf-8')
                        os.unlink(temp_audio_path)
                        logger.info(f"Generated gTTS audio ({len(audio_bytes)} bytes)")
                    except Exception as tts_error:
                        logger.warning(f"gTTS generation failed: {tts_error}")
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
