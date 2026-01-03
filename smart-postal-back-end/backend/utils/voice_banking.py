import os
import torch
import torchaudio
import numpy as np
from loguru import logger
from config.settings import get_settings
import tempfile
import shutil
from pathlib import Path
from typing import Tuple, Optional, Dict, List
from scipy import signal
from scipy.stats import kurtosis, skew
import librosa
from dataclasses import dataclass, asdict
from fastapi import UploadFile

settings = get_settings()

@dataclass
class AudioQualityMetrics:
    """Audio quality assessment results"""
    snr: float
    duration: float
    is_clipping: bool
    spectral_flatness: float
    zero_crossing_rate: float
    is_acceptable: bool
    rejection_reason: Optional[str] = None


@dataclass
class AntiSpoofingMetrics:
    """Anti-spoofing detection results"""
    is_live: bool
    confidence: float
    spectral_consistency: float
    temporal_consistency: float
    features: Dict[str, float]


@dataclass
class AISyntheticDetectionMetrics:
    """AI-generated/synthetic voice detection results"""
    is_human: bool  # True if human voice, False if AI/synthetic
    confidence: float  # Confidence in detection (0-1)
    ai_probability: float  # Probability that voice is AI-generated (0-1)
    detection_method: str  # Primary detection method used
    flags: List[str]  # List of detection flags/indicators
    features: Dict[str, float]  # Detailed feature analysis
    is_rerecorded: bool  # True if audio appears to be re-recorded (speaker->mic)
    rerecording_confidence: float  # Confidence in re-recording detection


class BankingGradeVoiceProcessor:
    """
    Enterprise-grade voice verification for banking applications
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BankingGradeVoiceProcessor, cls).__new__(cls)
            cls._instance.resemblyzer_model = None
            cls._instance.initialization_error = None
            cls._instance.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        return cls._instance
    
    def _ensure_models_loaded(self):
        """Load voice verification models"""
        if self.resemblyzer_model is not None or self.initialization_error is not None:
            return
            
        try:
            logger.info("🔐 Loading banking-grade voice verification models...")
            
            from resemblyzer import VoiceEncoder
            self.resemblyzer_model = VoiceEncoder(device=self.device)
            
            logger.info(f"✓ Models loaded on {self.device}")
            
        except Exception as e:
            error_msg = f"Failed to load models: {str(e)}"
            logger.error(error_msg)
            self.initialization_error = error_msg
            self.resemblyzer_model = None

    def assess_audio_quality(self, audio_path: str, sample_rate: int = 16000) -> AudioQualityMetrics:
        """Comprehensive audio quality assessment"""
        try:
            y, sr = librosa.load(audio_path, sr=sample_rate)
            duration = librosa.get_duration(y=y, sr=sr)
            
            if duration < 1.0:
                return AudioQualityMetrics(
                    snr=0.0, duration=duration, is_clipping=False,
                    spectral_flatness=0.0, zero_crossing_rate=0.0,
                    is_acceptable=False,
                    rejection_reason="Audio too short (minimum 1 second)"
                )
            
            if duration > 30.0:
                return AudioQualityMetrics(
                    snr=0.0, duration=duration, is_clipping=False,
                    spectral_flatness=0.0, zero_crossing_rate=0.0,
                    is_acceptable=False,
                    rejection_reason="Audio too long (maximum 30 seconds)"
                )
            
            energy = np.sum(y ** 2) / len(y)
            if energy < 0.0001:
                return AudioQualityMetrics(
                    snr=0.0, duration=duration, is_clipping=False,
                    spectral_flatness=0.0, zero_crossing_rate=0.0,
                    is_acceptable=False,
                    rejection_reason="Insufficient energy (possible silence)"
                )
            
            clipping_threshold = 0.95
            is_clipping = np.max(np.abs(y)) > clipping_threshold
            
            frame_energy = librosa.feature.rms(y=y)[0]
            noise_threshold = np.percentile(frame_energy, 10)
            signal_frames = frame_energy > noise_threshold
            
            if np.sum(signal_frames) > 0:
                signal_power = np.mean(frame_energy[signal_frames] ** 2)
                noise_power = np.mean(frame_energy[~signal_frames] ** 2) if np.sum(~signal_frames) > 0 else 0.001
                snr_db = 10 * np.log10(signal_power / (noise_power + 1e-10))
            else:
                snr_db = 0.0
            
            spectral_flatness = np.mean(librosa.feature.spectral_flatness(y=y))
            zcr = np.mean(librosa.feature.zero_crossing_rate(y))
            
            # Relaxed thresholds for real-world environments
            MIN_SNR_DB = 3.0  # Very lenient - only reject extremely noisy
            MAX_SPECTRAL_FLATNESS = 0.95  # Only reject complete silence
            
            is_acceptable = True
            rejection_reason = None
            
            # Only reject truly unusable audio
            if duration < 0.5:
                is_acceptable = False
                rejection_reason = f"Audio too short: {duration:.2f}s (minimum: 0.5s)"
            elif snr_db < MIN_SNR_DB:
                is_acceptable = False
                rejection_reason = f"Extremely noisy: {snr_db:.1f}dB. Try again."
            elif spectral_flatness > MAX_SPECTRAL_FLATNESS:
                is_acceptable = False
                rejection_reason = "No voice detected. Please speak into microphone."
            
            logger.info(f"📊 Quality: SNR={snr_db:.1f}dB, Duration={duration:.2f}s, OK={is_acceptable}")
            
            return AudioQualityMetrics(
                snr=float(snr_db),
                duration=float(duration),
                is_clipping=is_clipping,
                spectral_flatness=float(spectral_flatness),
                zero_crossing_rate=float(zcr),
                is_acceptable=is_acceptable,
                rejection_reason=rejection_reason
            )
            
        except Exception as e:
            logger.error(f"Quality assessment error: {str(e)}")
            return AudioQualityMetrics(
                snr=0.0, duration=0.0, is_clipping=False,
                spectral_flatness=0.0, zero_crossing_rate=0.0,
                is_acceptable=False,
                rejection_reason=f"Assessment failed: {str(e)}"
            )

    def enhance_audio(self, audio_path: str, sample_rate: int = 16000) -> np.ndarray:
        """
        Advanced audio enhancement for robustness in noisy environments
        - Noise reduction using spectral gating
        - Normalization
        - Voice activity detection
        """
        try:
            import noisereduce as nr
            
            y, sr = librosa.load(audio_path, sr=sample_rate)
            
            # Apply noise reduction
            y_denoised = nr.reduce_noise(y=y, sr=sr, stationary=True, prop_decrease=0.8)
            
            # Normalize
            y_normalized = librosa.util.normalize(y_denoised)
            
            return y_normalized
            
        except ImportError:
            # Fallback if noisereduce not available
            y, sr = librosa.load(audio_path, sr=sample_rate)
            return librosa.util.normalize(y)
        except Exception as e:
            logger.warning(f"Audio enhancement failed: {e}, using original")
            y, sr = librosa.load(audio_path, sr=sample_rate)
            return y

    def detect_ai_synthetic_voice(self, audio_path: str, sample_rate: int = 16000, 
                                   strict_mode: bool = True) -> AISyntheticDetectionMetrics:
        """
        Advanced AI-generated/synthetic voice detection with re-recording detection.
        
        Detects:
        1. Direct AI-generated voices (TTS, voice cloning)
        2. Re-recorded AI voices (speaker -> microphone)
        3. Acoustic replay attacks
        4. Voice conversion artifacts
        
        Args:
            audio_path: Path to audio file
            sample_rate: Target sample rate
            strict_mode: If True, use stricter thresholds
        
        Returns:
            AISyntheticDetectionMetrics with detection results
        """
        logger.info(f"🔍 Starting AI detection on: {audio_path} (strict_mode={strict_mode})")
        try:
            y, sr = librosa.load(audio_path, sr=sample_rate)
            duration = librosa.get_duration(y=y, sr=sr)
            
            flags = []
            features = {}
            
            # =================================================================
            # 1. SPECTRAL ANALYSIS - Detects unnatural frequency patterns
            # =================================================================
            
            # Extract mel-frequency cepstral coefficients (MFCC)
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
            mfcc_mean = np.mean(mfcc, axis=1)
            mfcc_std = np.std(mfcc, axis=1)
            mfcc_delta = librosa.feature.delta(mfcc)
            
            # AI voices often have unnatural MFCC patterns
            mfcc_variance = np.mean(mfcc_std)
            features['mfcc_variance'] = float(mfcc_variance)
            
            # Low variance suggests synthetic generation (relaxed threshold)
            if mfcc_variance < 10.0:
                flags.append("LOW_MFCC_VARIANCE")
            
            # Spectral centroid - center of mass of spectrum
            spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
            spectral_centroid_mean = np.mean(spectral_centroid)
            spectral_centroid_std = np.std(spectral_centroid)
            
            features['spectral_centroid_mean'] = float(spectral_centroid_mean)
            features['spectral_centroid_std'] = float(spectral_centroid_std)
            
            # AI voices tend to have more stable spectral centroid (relaxed threshold)
            if spectral_centroid_std < 150:
                flags.append("STABLE_SPECTRAL_CENTROID")
            
            # =================================================================
            # 2. TEMPORAL ANALYSIS - Detects unnatural timing patterns
            # =================================================================
            
            # Energy envelope analysis
            frame_energy = librosa.feature.rms(y=y)[0]
            energy_variance = np.var(frame_energy)
            energy_kurtosis_val = kurtosis(frame_energy)
            energy_skew_val = skew(frame_energy)
            
            features['energy_variance'] = float(energy_variance)
            features['energy_kurtosis'] = float(energy_kurtosis_val)
            features['energy_skew'] = float(energy_skew_val)
            
            # AI voices often have unnaturally consistent energy (relaxed threshold)
            if energy_variance < 0.0003:
                flags.append("LOW_ENERGY_VARIANCE")
            
            # Unnatural kurtosis suggests synthetic generation
            if abs(energy_kurtosis_val) < 1.5 or abs(energy_kurtosis_val) > 8.0:
                flags.append("ABNORMAL_ENERGY_KURTOSIS")
            
            # =================================================================
            # 3. PHASE ANALYSIS - Detects replay/re-recording artifacts
            # =================================================================
            
            # Compute STFT for phase analysis
            stft = librosa.stft(y)
            phase = np.angle(stft)
            
            # Phase coherence - measures phase consistency
            phase_diff = np.diff(phase, axis=1)
            phase_coherence = np.mean(np.abs(np.cos(phase_diff)))
            
            features['phase_coherence'] = float(phase_coherence)
            
            # Re-recorded audio has different phase characteristics (relaxed threshold)
            if phase_coherence > 0.90:
                flags.append("HIGH_PHASE_COHERENCE")
            
            # =================================================================
            # 4. HIGH-FREQUENCY ANALYSIS - Detects TTS and re-recording
            # =================================================================
            
            # Human voice has rich high-frequency content
            # Re-recorded or TTS audio loses high frequencies
            
            # Split spectrum into low (<2kHz) and high (>4kHz) bands
            fft = np.fft.rfft(y)
            freqs = np.fft.rfftfreq(len(y), 1/sr)
            
            low_freq_mask = freqs < 2000
            high_freq_mask = freqs > 4000
            
            low_freq_power = np.mean(np.abs(fft[low_freq_mask])**2)
            high_freq_power = np.mean(np.abs(fft[high_freq_mask])**2)
            
            high_low_ratio = high_freq_power / (low_freq_power + 1e-10)
            features['high_low_freq_ratio'] = float(high_low_ratio)
            
            # Low ratio suggests re-recording or speaker playback (focus on clear cases)
            if high_low_ratio < 0.008:
                flags.append("LOW_HIGH_FREQ_CONTENT")
            
            # =================================================================
            # 5. HARMONICITY ANALYSIS - Detects synthetic pitch
            # =================================================================
            
            # Extract pitch and harmonicity
            try:
                pitches, magnitudes = librosa.piptrack(y=y, sr=sr)
                pitch_values = []
                
                for t in range(pitches.shape[1]):
                    index = magnitudes[:, t].argmax()
                    pitch = pitches[index, t]
                    if pitch > 0:
                        pitch_values.append(pitch)
                
                if len(pitch_values) > 0:
                    pitch_std = np.std(pitch_values)
                    features['pitch_std'] = float(pitch_std)
                    
                    # AI voices often have unnaturally stable pitch
                    if pitch_std < 10.0:
                        flags.append("STABLE_PITCH")
            except:
                features['pitch_std'] = 0.0
            
            # =================================================================
            # 6. FORMANT ANALYSIS - Detects unnatural vocal tract simulation
            # =================================================================
            
            # Extract formants using LPC (Linear Predictive Coding)
            # AI/TTS often has unnatural formant transitions
            try:
                # Pre-emphasis filter
                pre_emphasis = 0.97
                y_emphasized = np.append(y[0], y[1:] - pre_emphasis * y[:-1])
                
                # Frame the signal
                frame_length = int(0.025 * sr)  # 25ms frames
                hop_length = int(0.010 * sr)    # 10ms hop
                
                frames = librosa.util.frame(y_emphasized, 
                                            frame_length=frame_length, 
                                            hop_length=hop_length)
                
                formant_variance_list = []
                for frame in frames.T[:50]:  # Sample first 50 frames
                    if np.sum(frame**2) > 0.01:  # Skip silent frames
                        # Simple formant estimation using peak picking
                        spectrum = np.abs(np.fft.rfft(frame))
                        formant_variance_list.append(np.std(spectrum))
                
                if len(formant_variance_list) > 0:
                    formant_consistency = np.mean(formant_variance_list)
                    features['formant_consistency'] = float(formant_consistency)
                    
                    # Too consistent formants suggest TTS
                    if formant_consistency < 0.05:
                        flags.append("CONSISTENT_FORMANTS")
            except:
                features['formant_consistency'] = 0.0
            
            # =================================================================
            # 7. RE-RECORDING DETECTION - Detects speaker->microphone path
            # =================================================================
            
            is_rerecorded = False
            rerecording_confidence = 0.0
            
            # Room reverb/echo detection (indicates speaker playback)
            try:
                # Autocorrelation for echo detection
                autocorr = np.correlate(y, y, mode='full')
                autocorr = autocorr[len(autocorr)//2:]
                
                # Normalize
                if autocorr[0] > 0:
                    autocorr = autocorr / autocorr[0]
                
                # Look for secondary peaks (echoes)
                # Skip first 100ms to avoid pitch harmonics
                search_start = int(0.1 * sr)
                search_end = int(0.5 * sr)
                
                if search_end < len(autocorr):
                    echo_region = autocorr[search_start:search_end]
                    max_echo = np.max(echo_region) if len(echo_region) > 0 else 0
                    
                    features['echo_strength'] = float(max_echo)
                    
                    # Strong echo suggests speaker playback
                    if max_echo > 0.3:
                        flags.append("ECHO_DETECTED")
                        is_rerecorded = True
                        rerecording_confidence = min(max_echo, 1.0)
            except:
                features['echo_strength'] = 0.0
            
            # Bandlimited signal detection (speaker frequency response)
            # Re-recorded audio through phone speakers has characteristic limits
            magnitude_spectrum = np.abs(fft)
            
            # Check for unnatural frequency cutoffs (typical of phone speakers)
            very_high_freq_mask = freqs > 8000
            very_high_power = np.mean(magnitude_spectrum[very_high_freq_mask])
            
            features['very_high_freq_power'] = float(very_high_power)
            
            if very_high_power < 0.001:
                flags.append("BANDLIMITED_SIGNAL")
                is_rerecorded = True
                rerecording_confidence = max(rerecording_confidence, 0.6)
            
            # =================================================================
            # 8. PROSODY ANALYSIS - Detects unnatural speech rhythm
            # =================================================================
            
            # Zero-crossing rate variability
            zcr = librosa.feature.zero_crossing_rate(y)[0]
            zcr_std = np.std(zcr)
            
            features['zcr_std'] = float(zcr_std)
            
            # AI voices often have more consistent zero-crossing rates
            if zcr_std < 0.02:
                flags.append("CONSISTENT_ZCR")
            
            # =================================================================
            # 9. MODULATION SPECTRUM ANALYSIS - Detects AI generation patterns
            # =================================================================
            
            # Compute modulation spectrum (spectrum of the envelope)
            envelope = np.abs(librosa.feature.rms(y=y)[0])
            mod_spectrum = np.abs(np.fft.rfft(envelope))
            mod_spectrum_peak = np.max(mod_spectrum[1:]) if len(mod_spectrum) > 1 else 0  # Skip DC
            
            features['modulation_spectrum_peak'] = float(mod_spectrum_peak)
            
            # Unnatural modulation suggests TTS
            if mod_spectrum_peak > 50.0:
                flags.append("ABNORMAL_MODULATION")
            
            # =================================================================
            # 10. LFCC ANALYSIS - Advanced anti-spoofing feature
            # =================================================================
            
            try:
                from utils.anti_spoof import lfcc_extractor
                
                # Extract LFCC features
                lfcc = lfcc_extractor.extract(y)
                lfcc_stats = lfcc_extractor.compute_statistics(lfcc)
                
                # Add LFCC statistics to features
                features.update(lfcc_stats)
                
                # LFCC-based spoofing indicators
                if lfcc_stats.get('lfcc_range', 100) < 15.0:
                    flags.append("LOW_LFCC_RANGE")
                
                if abs(lfcc_stats.get('lfcc_kurtosis', 0)) < 1.0:
                    flags.append("ABNORMAL_LFCC_KURTOSIS")
                
                logger.debug(f"LFCC features extracted: range={lfcc_stats.get('lfcc_range', 0):.2f}")
                
            except Exception as e:
                logger.warning(f"LFCC extraction failed: {e}")
            
            # =================================================================
            # 11. AGGREGATE SCORING - Combine all indicators
            # =================================================================
            
            # Count red flags
            red_flag_count = len(flags)
            features['red_flag_count'] = red_flag_count
            
            # Calculate AI probability based on multiple factors
            ai_score = 0.0
            
            # Weighted scoring based on detection strength (reduced weights to avoid false positives)
            if "LOW_MFCC_VARIANCE" in flags:
                ai_score += 0.10
            if "STABLE_SPECTRAL_CENTROID" in flags:
                ai_score += 0.08
            if "LOW_ENERGY_VARIANCE" in flags:
                ai_score += 0.12
            if "ABNORMAL_ENERGY_KURTOSIS" in flags:
                ai_score += 0.08
            if "HIGH_PHASE_COHERENCE" in flags:
                ai_score += 0.06
            if "LOW_HIGH_FREQ_CONTENT" in flags:
                ai_score += 0.18  # Strong indicator for re-recorded/speaker playback
            if "STABLE_PITCH" in flags:
                ai_score += 0.08
            if "CONSISTENT_FORMANTS" in flags:
                ai_score += 0.10
            if "ECHO_DETECTED" in flags:
                ai_score += 0.22  # Strong indicator of re-recording
            if "BANDLIMITED_SIGNAL" in flags:
                ai_score += 0.20  # Strong indicator of speaker playback
            if "CONSISTENT_ZCR" in flags:
                ai_score += 0.07
            if "ABNORMAL_MODULATION" in flags:
                ai_score += 0.06
            
            # LFCC-based flags (new)
            if "LOW_LFCC_RANGE" in flags:
                ai_score += 0.09
            if "ABNORMAL_LFCC_KURTOSIS" in flags:
                ai_score += 0.08
            
            # Normalize to 0-1 range
            ai_probability = min(ai_score, 1.0)
            
            # Determine detection thresholds (balanced to reduce false positives)
            if strict_mode:
                # Strict mode: Sensitive but not overly aggressive
                AI_THRESHOLD = 0.45  # Reject if 45%+ AI probability
            else:
                # Standard mode: Balanced
                AI_THRESHOLD = 0.60  # Reject if 60%+ AI probability
            
            is_human = ai_probability < AI_THRESHOLD
            confidence = abs(ai_probability - 0.5) * 2  # Distance from decision boundary
            
            # Determine primary detection method
            if not is_human:
                if "ECHO_DETECTED" in flags or "BANDLIMITED_SIGNAL" in flags:
                    detection_method = "RE_RECORDED_DETECTION"
                elif "LOW_HIGH_FREQ_CONTENT" in flags:
                    detection_method = "SPECTRAL_ANALYSIS"
                elif "LOW_ENERGY_VARIANCE" in flags or "STABLE_PITCH" in flags:
                    detection_method = "TEMPORAL_ANALYSIS"
                else:
                    detection_method = "MULTI_FACTOR_ANALYSIS"
            else:
                detection_method = "HUMAN_VOICE_CONFIRMED"
            
            logger.info(f"🤖 AI Detection: Human={is_human}, AI_Prob={ai_probability:.3f}, "
                       f"Flags={red_flag_count}, Method={detection_method}, "
                       f"ReRecorded={is_rerecorded}, Threshold={AI_THRESHOLD}, Strict={strict_mode}")
            
            if flags:
                logger.info(f"   Detection flags: {', '.join(flags)}")
            else:
                logger.info(f"   No detection flags raised - appears to be human voice")
            
            return AISyntheticDetectionMetrics(
                is_human=is_human,
                confidence=float(confidence),
                ai_probability=float(ai_probability),
                detection_method=detection_method,
                flags=flags,
                features=features,
                is_rerecorded=is_rerecorded,
                rerecording_confidence=float(rerecording_confidence)
            )
            
        except Exception as e:
            logger.error(f"AI detection error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Fail secure: reject on error in strict mode
            if strict_mode:
                return AISyntheticDetectionMetrics(
                    is_human=False,
                    confidence=0.0,
                    ai_probability=1.0,
                    detection_method="ERROR_FAIL_SECURE",
                    flags=["DETECTION_ERROR"],
                    features={"error": str(e)},
                    is_rerecorded=False,
                    rerecording_confidence=0.0
                )
            else:
                # Fail open in non-strict mode
                return AISyntheticDetectionMetrics(
                    is_human=True,
                    confidence=0.0,
                    ai_probability=0.0,
                    detection_method="ERROR_FAIL_OPEN",
                    flags=["DETECTION_ERROR"],
                    features={"error": str(e)},
                    is_rerecorded=False,
                    rerecording_confidence=0.0
                )

    def detect_replay_attack(self, audio_path: str, sample_rate: int = 16000) -> AntiSpoofingMetrics:
        """
        Legacy anti-spoofing method - now supplemented by detect_ai_synthetic_voice.
        Kept for backward compatibility.
        """
        try:
            y, sr = librosa.load(audio_path, sr=sample_rate)
            
            # Simple checks for obvious spoofing
            frame_energy = librosa.feature.rms(y=y)[0]
            energy_variance = np.var(frame_energy)
            
            # Very basic liveness: just check if audio has natural variation
            # Real voice has energy variance, synthetic/replayed might be too flat
            has_variation = energy_variance > 0.0001
            
            # Always pass unless obviously synthetic (extremely low variation)
            liveness_score = 0.9 if has_variation else 0.1
            is_live = True  # Default to accepting
            
            features = {
                "energy_variance": float(energy_variance),
                "has_variation": has_variation
            }
            
            logger.info(f"🛡️ Legacy anti-spoofing: Score={liveness_score:.3f}, Live={is_live}")
            
            return AntiSpoofingMetrics(
                is_live=is_live,
                confidence=float(liveness_score),
                spectral_consistency=1.0,
                temporal_consistency=1.0,
                features=features
            )
            
        except Exception as e:
            logger.error(f"Anti-spoofing error: {str(e)}")
            # Fail open for liveness (accept by default)
            return AntiSpoofingMetrics(
                is_live=True,
                confidence=0.5,
                spectral_consistency=0.0,
                temporal_consistency=0.0,
                features={"error": str(e)}
            )

    async def process_audio(self, file: UploadFile, perform_quality_check: bool = True,
                          perform_liveness_check: bool = True,
                          perform_ai_detection: bool = True,
                          ai_detection_strict_mode: bool = True) -> Dict:
        """Process audio file with quality checks, AI detection, and embedding extraction"""
        self._ensure_models_loaded()
        
        if self.initialization_error:
            return {
                "success": False,
                "error": f"Models not available: {self.initialization_error}",
                "embedding": None
            }
        
        temp_path = None
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                temp_path = temp_file.name
                content = await file.read()
                temp_file.write(content)
            
            # Quality assessment
            quality_metrics = None
            if perform_quality_check:
                quality_metrics = self.assess_audio_quality(temp_path)
                # Only reject for extreme low or duration issues
                if quality_metrics.duration < 0.5:
                    return {
                        "success": False,
                        "error": "Audio too short (minimum 0.5 seconds)",
                        "error_code": "AUDIO_TOO_SHORT",
                        "quality_metrics": asdict(quality_metrics),
                        "embedding": None
                    }
                # Accept even noisy audio - we'll clean it
                logger.info(f"📊 Quality: SNR={quality_metrics.snr:.1f}dB, Duration={quality_metrics.duration:.2f}s")
            
            # AI/Synthetic voice detection (PRIMARY SECURITY CHECK)
            ai_detection_metrics = None
            if perform_ai_detection:
                ai_detection_metrics = self.detect_ai_synthetic_voice(
                    temp_path, 
                    strict_mode=ai_detection_strict_mode
                )
                
                if not ai_detection_metrics.is_human:
                    # Determine specific rejection reason
                    if ai_detection_metrics.is_rerecorded:
                        rejection_reason = (
                            f"AI-generated voice detected (re-recorded). "
                            f"This appears to be synthetic speech played through a speaker "
                            f"and recorded (AI probability: {ai_detection_metrics.ai_probability:.1%}). "
                            f"Please use your natural voice directly into the microphone."
                        )
                    else:
                        rejection_reason = (
                            f"AI-generated or synthetic voice detected. "
                            f"The audio exhibits characteristics of computer-generated speech "
                            f"(AI probability: {ai_detection_metrics.ai_probability:.1%}). "
                            f"Please use your natural voice for authentication."
                        )
                    
                    logger.warning(
                        f"🚫 AI/Synthetic voice REJECTED: AI_Prob={ai_detection_metrics.ai_probability:.3f}, "
                        f"Method={ai_detection_metrics.detection_method}, "
                        f"Flags={ai_detection_metrics.flags}"
                    )
                    
                    return {
                        "success": False,
                        "error": rejection_reason,
                        "error_code": "AI_SYNTHETIC_VOICE_DETECTED",
                        "quality_metrics": asdict(quality_metrics) if quality_metrics else None,
                        "ai_detection_metrics": asdict(ai_detection_metrics),
                        "embedding": None
                    }
            
            # Legacy liveness check (supplementary)
            liveness_metrics = None
            if perform_liveness_check:
                liveness_metrics = self.detect_replay_attack(temp_path)
                # Only reject if obviously synthetic
                if not liveness_metrics.is_live:
                    logger.warning(f"⚠️ Legacy liveness check flagged audio")
            
            # Enhanced audio preprocessing
            from resemblyzer import preprocess_wav
            
            try:
                # Try with noise reduction first
                enhanced_audio = self.enhance_audio(temp_path)
                
                # Save enhanced audio temporarily
                enhanced_path = temp_path.replace('.wav', '_enhanced.wav')
                import soundfile as sf
                sf.write(enhanced_path, enhanced_audio, 16000)
                
                # Process enhanced audio
                wav = preprocess_wav(enhanced_path)
                embedding = self.resemblyzer_model.embed_utterance(wav)
                
                # Cleanup enhanced file
                if os.path.exists(enhanced_path):
                    os.remove(enhanced_path)
                    
                logger.info(f"✓ Enhanced embedding extracted: shape={embedding.shape}")
                
            except Exception as e:
                # Fallback to original audio if enhancement fails
                logger.warning(f"Enhancement failed, using original: {e}")
                wav = preprocess_wav(temp_path)
                embedding = self.resemblyzer_model.embed_utterance(wav)
                logger.info(f"✓ Original embedding extracted: shape={embedding.shape}")
            
            # Normalize embedding for better comparison
            embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
            
            return {
                "success": True,
                "embedding": embedding,
                "quality_metrics": asdict(quality_metrics) if quality_metrics else None,
                "liveness_metrics": asdict(liveness_metrics) if liveness_metrics else None,
                "ai_detection_metrics": asdict(ai_detection_metrics) if ai_detection_metrics else None,
                "error": None,
                "error_code": None
            }
            
        except Exception as e:
            logger.error(f"Processing error: {str(e)}")
            raise e
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def verify_voice_ensemble(self, embedding1: np.ndarray, embedding2: np.ndarray,
                            use_strict_threshold: bool = False) -> Tuple[bool, float, Dict]:
        """Multi-metric ensemble verification"""
        try:
            if not isinstance(embedding1, np.ndarray):
                embedding1 = np.array(embedding1)
            if not isinstance(embedding2, np.ndarray):
                embedding2 = np.array(embedding2)
            
            cosine_sim = np.dot(embedding1, embedding2) / (
                np.linalg.norm(embedding1) * np.linalg.norm(embedding2) + 1e-10
            )
            cosine_score = float(np.clip(cosine_sim, 0, 1))
            
            euclidean_dist = np.linalg.norm(embedding1 - embedding2)
            euclidean_score = float(np.clip(1 - (euclidean_dist / 2.0), 0, 1))
            
            correlation = np.corrcoef(embedding1, embedding2)[0, 1]
            correlation_score = float(np.clip((correlation + 1) / 2, 0, 1))
            
            ensemble_score = (
                cosine_score * 0.70 +
                euclidean_score * 0.20 +
                correlation_score * 0.10
            )
            
            # Get fresh settings
            current_settings = get_settings()
            threshold = current_settings.VOICE_SIMILARITY_THRESHOLD
            
            is_verified = ensemble_score >= threshold
            fail_reason = None
            
            if not is_verified:
                fail_reason = f"Ensemble score {ensemble_score:.3f} < Threshold {threshold:.3f}"
            
            # Minimum cosine similarity threshold
            MIN_COSINE_THRESHOLD = 0.65  # Balanced for real-world use
            if cosine_score < MIN_COSINE_THRESHOLD:
                is_verified = False
                fail_reason = f"Cosine similarity {cosine_score:.3f} < Min {MIN_COSINE_THRESHOLD:.3f}"
                logger.warning(f"⚠️ Cosine too low ({cosine_score:.3f} < {MIN_COSINE_THRESHOLD})")
            
            metrics = {
                "ensemble_score": round(ensemble_score, 4),
                "cosine_similarity": round(cosine_score, 4),
                "euclidean_score": round(euclidean_score, 4),
                "correlation_score": round(correlation_score, 4),
                "threshold_used": round(threshold, 4),
                "min_cosine_threshold": MIN_COSINE_THRESHOLD,
                "fail_reason": fail_reason
            }
            
            logger.info(f"🔍 Verification: Ensemble={ensemble_score:.4f}, "
                       f"Cosine={cosine_score:.4f}, "
                       f"Threshold={threshold:.4f}, "
                       f"Verified={is_verified}")
            
            return is_verified, ensemble_score, metrics
            
        except Exception as e:
            logger.error(f"Verification error: {str(e)}")
            return False, 0.0, {"error": str(e)}

    def validate_enrollment_template(self, embeddings: List[np.ndarray]) -> Tuple[bool, float, str]:
        """Validate enrollment template consistency"""
        if len(embeddings) < 2:
            return True, 1.0, "Single sample"
        
        try:
            similarities = []
            for i in range(len(embeddings)):
                for j in range(i + 1, len(embeddings)):
                    sim = np.dot(embeddings[i], embeddings[j]) / (
                        np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j]) + 1e-10
                    )
                    similarities.append(sim)
            
            avg_consistency = np.mean(similarities)
            min_consistency = np.min(similarities)
            
            MIN_AVERAGE_CONSISTENCY = 0.75
            MIN_SINGLE_CONSISTENCY = 0.65
            
            is_valid = (avg_consistency >= MIN_AVERAGE_CONSISTENCY and 
                       min_consistency >= MIN_SINGLE_CONSISTENCY)
            
            reason = ""
            if not is_valid:
                if avg_consistency < MIN_AVERAGE_CONSISTENCY:
                    reason = f"Inconsistent samples (avg: {avg_consistency:.3f})"
                elif min_consistency < MIN_SINGLE_CONSISTENCY:
                    reason = f"Sample differs significantly (min: {min_consistency:.3f})"
            else:
                reason = "Template valid"
            
            logger.info(f"📋 Template: Avg={avg_consistency:.3f}, Min={min_consistency:.3f}, Valid={is_valid}")
            
            return is_valid, float(avg_consistency), reason
            
        except Exception as e:
            logger.error(f"Template validation error: {str(e)}")
            return False, 0.0, f"Validation error: {str(e)}"


voice_processor = BankingGradeVoiceProcessor()

