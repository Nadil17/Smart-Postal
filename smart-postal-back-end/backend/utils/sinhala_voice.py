"""
Sinhala Voice Processing Utilities
Integrates Whisper STT and Gemini LLM with the courier bot
"""
import os
import io
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, Optional
from loguru import logger

# Get ffmpeg path from imageio_ffmpeg
import imageio_ffmpeg
FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
logger.info(f"Using ffmpeg: {FFMPEG_EXE}")

from fastapi import UploadFile

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

try:
    import speech_recognition as sr
    SR_AVAILABLE = True
except ImportError:
    SR_AVAILABLE = False


class SinhalaVoiceProcessor:
    """
    Processes Sinhala voice queries using Whisper STT
    Separate from biometric voice verification
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SinhalaVoiceProcessor, cls).__new__(cls)
            cls._instance.openai_client = None
            cls._instance.whisper_model = None
            cls._instance.recognizer = None
            cls._instance.initialization_error = None
        return cls._instance
    
    def _ensure_models_loaded(self):
        """Load STT models (Whisper or SpeechRecognition)"""
        if self.initialization_error:
            return
        
        if self.openai_client or self.whisper_model or self.recognizer:
            return
        
        try:
            # Try OpenAI Whisper API first
            if OPENAI_AVAILABLE and os.getenv("OPENAI_API_KEY"):
                self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                logger.info("✓ OpenAI Whisper API loaded for Sinhala STT")
                return
            
            # Fallback to local Whisper
            if WHISPER_AVAILABLE:
                logger.info("Loading local Whisper model...")
                self.whisper_model = whisper.load_model("base")
                logger.info("✓ Local Whisper loaded for Sinhala STT")
                return
            
            # Fallback to SpeechRecognition
            if SR_AVAILABLE:
                self.recognizer = sr.Recognizer()
                logger.info("✓ SpeechRecognition loaded for Sinhala STT")
                return
            
            raise ImportError("No STT library available. Install openai-whisper or SpeechRecognition")
            
        except Exception as e:
            error_msg = f"Failed to load Sinhala STT models: {str(e)}"
            logger.error(error_msg)
            self.initialization_error = error_msg
    
    async def transcribe_audio(self, audio_file: UploadFile) -> Dict:
        """
        Transcribe audio file to Sinhala text
        
        Returns:
            {
                "success": bool,
                "text": str,
                "language": str,
                "error": Optional[str]
            }
        """
        self._ensure_models_loaded()
        
        if self.initialization_error:
            return {
                "success": False,
                "text": "",
                "language": "",
                "error": self.initialization_error
            }
        
        try:
            # Save uploaded file temporarily
            audio_bytes = await audio_file.read()
            
            # Try OpenAI Whisper API
            if self.openai_client:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                    temp_file.write(audio_bytes)
                    temp_path = temp_file.name
                
                try:
                    with open(temp_path, "rb") as audio:
                        transcript = self.openai_client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio,
                            language="si"  # Sinhala
                        )
                    
                    return {
                        "success": True,
                        "text": transcript.text,
                        "language": "si",
                        "error": None
                    }
                finally:
                    os.unlink(temp_path)
            
            # Try local Whisper
            if self.whisper_model:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                    temp_file.write(audio_bytes)
                    temp_path = temp_file.name
                
                try:
                    result = self.whisper_model.transcribe(temp_path, language="si")
                    return {
                        "success": True,
                        "text": result["text"],
                        "language": "si",
                        "error": None
                    }
                finally:
                    os.unlink(temp_path)
            
            # Fallback to SpeechRecognition
            if self.recognizer:
                # Convert audio to WAV format using ffmpeg directly
                temp_input_path = None
                temp_output_path = None
                
                try:
                    # Save uploaded audio to temp file
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_input:
                        temp_input.write(audio_bytes)
                        temp_input_path = temp_input.name
                    
                    logger.info(f"Saved audio to: {temp_input_path} ({len(audio_bytes)} bytes)")
                    
                    # Convert to WAV using ffmpeg directly (bypass pydub)
                    temp_output_path = temp_input_path.replace(".webm", ".wav")
                    
                    # FFmpeg command: convert any format to 16kHz mono WAV
                    cmd = [
                        FFMPEG_EXE,
                        '-i', temp_input_path,  # Input file
                        '-acodec', 'pcm_s16le',  # PCM 16-bit
                        '-ar', '16000',          # 16kHz sample rate
                        '-ac', '1',              # Mono
                        '-y',                    # Overwrite output
                        temp_output_path
                    ]
                    
                    logger.info(f"Running ffmpeg conversion...")
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode != 0:
                        logger.error(f"FFmpeg failed: {result.stderr}")
                        raise Exception(f"Audio conversion failed: {result.stderr}")
                    
                    if not os.path.exists(temp_output_path):
                        raise Exception("WAV file was not created")
                    
                    logger.info(f"✓ Converted to WAV: {temp_output_path}")
                    
                    # Load audio file for recognition
                    with sr.AudioFile(temp_output_path) as source:
                        audio_data = self.recognizer.record(source)
                    
                    logger.info(f"✓ Audio loaded for recognition")
                    
                    # Try Google Speech Recognition
                    try:
                        text = self.recognizer.recognize_google(audio_data, language="si-LK")
                        return {
                            "success": True,
                            "text": text,
                            "language": "si",
                            "error": None
                        }
                    except sr.UnknownValueError:
                        # Try English if Sinhala fails
                        try:
                            text = self.recognizer.recognize_google(audio_data, language="en-US")
                            return {
                                "success": True,
                                "text": text,
                                "language": "en",
                                "error": None
                            }
                        except sr.UnknownValueError:
                            return {
                                "success": False,
                                "text": "",
                                "language": "",
                                "error": "Could not understand audio - please speak clearly"
                            }
                    except sr.RequestError as e:
                        return {
                            "success": False,
                            "text": "",
                            "language": "",
                            "error": f"Speech recognition service error: {str(e)}"
                        }
                finally:
                    # Clean up temp files
                    if temp_input_path and os.path.exists(temp_input_path):
                        os.unlink(temp_input_path)
                    if temp_output_path and os.path.exists(temp_output_path) and temp_output_path != temp_input_path:
                        os.unlink(temp_output_path)
            
            return {
                "success": False,
                "text": "",
                "language": "",
                "error": "No STT method available"
            }
            
        except Exception as e:
            logger.error(f"Transcription error: {str(e)}")
            return {
                "success": False,
                "text": "",
                "language": "",
                "error": str(e)
            }


# Global singleton
sinhala_voice_processor = SinhalaVoiceProcessor()
