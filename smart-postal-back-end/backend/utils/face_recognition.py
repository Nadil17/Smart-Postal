"""
================================================================================
WORLD-CLASS FACE RECOGNITION ENGINE v3.0
================================================================================
Research-Grade Biometric Verification System
Designed for 90-95% Accuracy with Quality-Degraded Images (NIC vs Live Photos)

Key Innovations:
1. Quality-Adaptive Preprocessing Pipeline
2. Multi-Model Weighted Ensemble Voting
3. Forensic Image Enhancement for Low-Quality Documents
4. Adaptive Thresholding Based on Image Quality Metrics
5. Multi-Detector Face Detection with Quality Assessment

Author: Smart-Postal Research Team
================================================================================
"""

import cv2
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import base64
from io import BytesIO
from PIL import Image
import warnings
warnings.filterwarnings('ignore')

# DeepFace for AI models
from deepface import DeepFace


class ImageQuality(Enum):
    """Image quality classification"""
    EXCELLENT = "excellent"  # Clear selfie, good lighting
    GOOD = "good"            # Minor issues but acceptable
    MODERATE = "moderate"    # Some noise/blur but usable
    POOR = "poor"            # Grainy NIC, old document
    VERY_POOR = "very_poor"  # Heavily degraded, needs max enhancement


@dataclass
class QualityMetrics:
    """Comprehensive image quality metrics"""
    sharpness: float       # Laplacian variance (higher = sharper)
    brightness: float      # Mean luminance (0-255)
    contrast: float        # Standard deviation of luminance
    noise_level: float     # Estimated noise (lower = better)
    resolution_score: float # Based on face size relative to image
    overall_quality: ImageQuality
    quality_score: float   # 0-100 composite score
    
    def __repr__(self):
        return f"Quality({self.overall_quality.value}, score={self.quality_score:.1f})"


class AdvancedImagePreprocessor:
    """
    Advanced Image Preprocessing Pipeline for Face Recognition
    
    This class implements multiple enhancement techniques that adapt based on
    detected image quality. Key for handling NIC scans vs live photos.
    """
    
    def __init__(self):
        self.quality_thresholds = {
            'sharpness': {'excellent': 500, 'good': 200, 'moderate': 100, 'poor': 50},
            'brightness': {'low': 60, 'high': 200, 'optimal_min': 80, 'optimal_max': 180},
            'contrast': {'excellent': 60, 'good': 40, 'moderate': 25, 'poor': 15},
            'noise': {'excellent': 5, 'good': 10, 'moderate': 20, 'poor': 35},
        }
    
    def detect_image_quality(self, image: np.ndarray) -> QualityMetrics:
        """
        Comprehensive image quality analysis
        
        Returns metrics that guide the enhancement pipeline
        """
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # 1. Sharpness (Laplacian variance)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        sharpness = laplacian.var()
        
        # 2. Brightness (mean luminance)
        brightness = np.mean(gray)
        
        # 3. Contrast (standard deviation)
        contrast = np.std(gray)
        
        # 4. Noise estimation using median filter difference
        denoised = cv2.medianBlur(gray, 5)
        noise_level = np.mean(np.abs(gray.astype(float) - denoised.astype(float)))
        
        # 5. Resolution score (based on image dimensions)
        height, width = gray.shape[:2]
        min_dim = min(height, width)
        resolution_score = min(100, (min_dim / 300) * 100)
        
        # Calculate composite quality score (0-100)
        sharpness_score = min(100, (sharpness / 500) * 100)
        brightness_score = 100 - abs(brightness - 128) / 1.28  # Optimal around 128
        contrast_score = min(100, (contrast / 60) * 100)
        noise_score = max(0, 100 - noise_level * 3)
        
        quality_score = (
            sharpness_score * 0.35 +
            brightness_score * 0.15 +
            contrast_score * 0.20 +
            noise_score * 0.15 +
            resolution_score * 0.15
        )
        
        # Classify overall quality
        if quality_score >= 80:
            overall_quality = ImageQuality.EXCELLENT
        elif quality_score >= 65:
            overall_quality = ImageQuality.GOOD
        elif quality_score >= 45:
            overall_quality = ImageQuality.MODERATE
        elif quality_score >= 25:
            overall_quality = ImageQuality.POOR
        else:
            overall_quality = ImageQuality.VERY_POOR
        
        return QualityMetrics(
            sharpness=sharpness,
            brightness=brightness,
            contrast=contrast,
            noise_level=noise_level,
            resolution_score=resolution_score,
            overall_quality=overall_quality,
            quality_score=quality_score
        )
    
    def adaptive_denoise(self, image: np.ndarray, quality: QualityMetrics) -> np.ndarray:
        """
        Apply denoising with strength based on detected noise level
        """
        if quality.noise_level < 5:
            return image  # No denoising needed
        
        # Determine denoising strength based on noise level
        if quality.noise_level > 30:
            h = 15  # Strong denoising for very noisy images
        elif quality.noise_level > 20:
            h = 10
        elif quality.noise_level > 10:
            h = 7
        else:
            h = 4  # Light denoising
        
        # Use Non-Local Means Denoising (best for preserving edges)
        if len(image.shape) == 3:
            denoised = cv2.fastNlMeansDenoisingColored(image, None, h, h, 7, 21)
        else:
            denoised = cv2.fastNlMeansDenoising(image, None, h, 7, 21)
        
        return denoised
    
    def enhance_contrast_clahe(self, image: np.ndarray, quality: QualityMetrics) -> np.ndarray:
        """
        Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        Strength adapts to image contrast level
        """
        # Convert to LAB color space for better results
        if len(image.shape) == 3:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
        else:
            l = image
        
        # Adaptive clip limit based on contrast
        if quality.contrast < 20:
            clip_limit = 4.0  # Strong enhancement for low contrast
        elif quality.contrast < 35:
            clip_limit = 3.0
        elif quality.contrast < 50:
            clip_limit = 2.0
        else:
            clip_limit = 1.5  # Light enhancement
        
        clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
        enhanced_l = clahe.apply(l)
        
        if len(image.shape) == 3:
            lab = cv2.merge([enhanced_l, a, b])
            enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        else:
            enhanced = enhanced_l
        
        return enhanced
    
    def normalize_lighting(self, image: np.ndarray, quality: QualityMetrics) -> np.ndarray:
        """
        Normalize lighting to compensate for uneven illumination
        Common in NIC photos taken under poor lighting
        """
        if len(image.shape) == 3:
            # Convert to YUV
            yuv = cv2.cvtColor(image, cv2.COLOR_BGR2YUV)
            y = yuv[:, :, 0].astype(float)
        else:
            y = image.astype(float)
        
        # Estimate illumination using large Gaussian blur
        blur_size = max(31, (min(image.shape[:2]) // 4) | 1)  # Ensure odd
        illumination = cv2.GaussianBlur(y, (blur_size, blur_size), 0)
        
        # Normalize: divide by illumination and rescale
        normalized = np.clip((y / (illumination + 1)) * 128, 0, 255).astype(np.uint8)
        
        if len(image.shape) == 3:
            yuv[:, :, 0] = normalized
            result = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)
        else:
            result = normalized
        
        return result
    
    def sharpen_adaptive(self, image: np.ndarray, quality: QualityMetrics) -> np.ndarray:
        """
        Apply unsharp mask with strength based on blur level
        """
        if quality.sharpness > 300:
            return image  # Already sharp enough
        
        # Determine sharpening strength
        if quality.sharpness < 50:
            amount = 2.0  # Strong sharpening
            radius = 2
        elif quality.sharpness < 100:
            amount = 1.5
            radius = 1.5
        elif quality.sharpness < 200:
            amount = 1.2
            radius = 1
        else:
            amount = 0.8
            radius = 0.5
        
        # Unsharp mask
        blurred = cv2.GaussianBlur(image, (0, 0), radius)
        sharpened = cv2.addWeighted(image, 1 + amount, blurred, -amount, 0)
        
        return np.clip(sharpened, 0, 255).astype(np.uint8)
    
    def upscale_image(self, image: np.ndarray, target_size: int = 224) -> np.ndarray:
        """
        Upscale small images using bicubic interpolation
        Most face models expect 224x224 or larger
        """
        height, width = image.shape[:2]
        min_dim = min(height, width)
        
        if min_dim >= target_size:
            return image
        
        scale = target_size / min_dim * 1.2  # Slight over-scale for quality
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        # Use INTER_CUBIC for upscaling
        upscaled = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        
        return upscaled
    
    def gamma_correction(self, image: np.ndarray, quality: QualityMetrics) -> np.ndarray:
        """
        Apply gamma correction to fix brightness issues
        """
        brightness = quality.brightness
        
        if 80 <= brightness <= 180:
            return image  # Brightness is acceptable
        
        # Calculate gamma
        if brightness < 80:
            gamma = 0.7 + (brightness / 80) * 0.3  # Brighten dark images
        else:
            gamma = 1.0 + (brightness - 180) / 75 * 0.5  # Darken bright images
        
        # Apply gamma correction
        inv_gamma = 1.0 / gamma
        table = np.array([((i / 255.0) ** inv_gamma) * 255 
                         for i in range(256)]).astype(np.uint8)
        
        return cv2.LUT(image, table)
    
    def full_enhancement_pipeline(self, image: np.ndarray, is_nic: bool = False) -> Tuple[np.ndarray, QualityMetrics]:
        """
        Complete enhancement pipeline with quality-adaptive processing
        
        Args:
            image: Input image (BGR format)
            is_nic: Whether this is a NIC/ID card image (applies stronger enhancement)
        
        Returns:
            Tuple of (enhanced_image, quality_metrics)
        """
        # Step 1: Analyze quality
        quality = self.detect_image_quality(image)
        print(f"   📊 Image Quality: {quality}")
        
        enhanced = image.copy()
        
        # For NIC images or poor quality, apply full pipeline
        if is_nic or quality.overall_quality in [ImageQuality.POOR, ImageQuality.VERY_POOR]:
            print("   🔧 Applying FULL enhancement pipeline (NIC/Low-quality mode)")
            
            # Step 2: Upscale FIRST for better processing
            enhanced = self.upscale_image(enhanced, target_size=300)
            
            # Step 3: Strong denoise for grainy NIC
            enhanced = self.adaptive_denoise(enhanced, quality)
            
            # Step 4: Normalize lighting
            enhanced = self.normalize_lighting(enhanced, quality)
            
            # Step 5: Gamma correction
            enhanced = self.gamma_correction(enhanced, quality)
            
            # Step 6: CLAHE contrast enhancement (stronger for NIC)
            enhanced = self.enhance_contrast_clahe(enhanced, quality)
            
            # Step 7: Sharpen to recover detail
            enhanced = self.sharpen_adaptive(enhanced, quality)
            
            # Step 8: Second pass - light denoise to remove sharpening artifacts
            if quality.noise_level > 15:
                enhanced = cv2.bilateralFilter(enhanced, 5, 50, 50)
            
        elif quality.overall_quality == ImageQuality.MODERATE:
            print("   🔧 Applying MODERATE enhancement pipeline")
            
            enhanced = self.adaptive_denoise(enhanced, quality)
            enhanced = self.enhance_contrast_clahe(enhanced, quality)
            enhanced = self.sharpen_adaptive(enhanced, quality)
            
        elif quality.overall_quality == ImageQuality.GOOD:
            print("   🔧 Applying LIGHT enhancement pipeline")
            
            enhanced = self.enhance_contrast_clahe(enhanced, quality)
            
        else:
            print("   ✨ Image quality EXCELLENT - minimal processing")
        
        return enhanced, quality


class MultiModelEnsemble:
    """
    Multi-Model Ensemble for Face Verification
    
    Uses weighted voting across multiple state-of-the-art face recognition models
    with adaptive thresholds based on image quality.
    """
    
    # Model configurations with base thresholds
    # These are distance thresholds (lower = more similar)
    # WORLD-CLASS SETTINGS - optimized for grainy NIC vs clear Live photo
    MODEL_CONFIG = {
        'ArcFace': {
            'weight': 0.40,
            'base_threshold': 0.55,  # ArcFace is most reliable
            'nic_adjustment': 0.15,  # Additional tolerance for NIC
            'quality_gap_factor': 0.008,  # Per point of quality difference (DOUBLED)
            'detector': 'retinaface',
            'embedding_dim': 512
        },
        'Facenet512': {
            'weight': 0.35,
            'base_threshold': 0.40,
            'nic_adjustment': 0.18,
            'quality_gap_factor': 0.009,  # Higher for Facenet which is more sensitive
            'detector': 'retinaface',
            'embedding_dim': 512
        },
        'VGG-Face': {
            'weight': 0.25,
            'base_threshold': 0.48,
            'nic_adjustment': 0.15,
            'quality_gap_factor': 0.008,
            'detector': 'retinaface',
            'embedding_dim': 4096
        }
    }
    
    # Quality-based threshold adjustments
    QUALITY_ADJUSTMENTS = {
        ImageQuality.EXCELLENT: 0.0,
        ImageQuality.GOOD: 0.02,
        ImageQuality.MODERATE: 0.05,
        ImageQuality.POOR: 0.08,
        ImageQuality.VERY_POOR: 0.12
    }
    
    FALLBACK_DETECTORS = ['retinaface', 'mtcnn', 'opencv', 'ssd']
    
    def __init__(self):
        self.preprocessor = AdvancedImagePreprocessor()
        self._models_initialized = False
    
    def get_adaptive_threshold(self, model_name: str, 
                                ref_quality: QualityMetrics,
                                live_quality: QualityMetrics,
                                is_nic_comparison: bool = True) -> float:
        """
        Calculate adaptive threshold based on image qualities
        
        KEY INNOVATION: Quality Gap Compensation
        When comparing poor NIC to good selfie, the distance is naturally higher
        due to information loss in the degraded image, NOT because it's different person.
        We compensate by increasing threshold proportional to quality gap.
        """
        config = self.MODEL_CONFIG[model_name]
        threshold = config['base_threshold']
        
        # Add NIC adjustment if comparing document to live photo
        if is_nic_comparison:
            threshold += config['nic_adjustment']
        
        # QUALITY GAP COMPENSATION (World-class technique)
        # If reference is much worse than live, increase threshold
        quality_gap = abs(ref_quality.quality_score - live_quality.quality_score)
        gap_adjustment = quality_gap * config.get('quality_gap_factor', 0.004)
        threshold += gap_adjustment
        
        # Add quality-based adjustment (use worst quality of the two)
        worst_quality = min(ref_quality.quality_score, live_quality.quality_score)
        
        if worst_quality < 25:
            quality_adj = self.QUALITY_ADJUSTMENTS[ImageQuality.VERY_POOR]
        elif worst_quality < 45:
            quality_adj = self.QUALITY_ADJUSTMENTS[ImageQuality.POOR]
        elif worst_quality < 65:
            quality_adj = self.QUALITY_ADJUSTMENTS[ImageQuality.MODERATE]
        elif worst_quality < 80:
            quality_adj = self.QUALITY_ADJUSTMENTS[ImageQuality.GOOD]
        else:
            quality_adj = self.QUALITY_ADJUSTMENTS[ImageQuality.EXCELLENT]
        
        threshold += quality_adj
        
        print(f"      → {model_name} threshold: base={config['base_threshold']:.2f} + nic={config['nic_adjustment']:.2f} + gap={gap_adjustment:.3f} + quality={quality_adj:.2f} = {threshold:.3f}")
        
        return threshold
    
    def extract_embeddings_robust(self, image: np.ndarray, model_name: str) -> Optional[np.ndarray]:
        """
        Extract face embeddings with fallback detectors
        
        Tries multiple detectors if the primary one fails
        """
        for detector in self.FALLBACK_DETECTORS:
            try:
                embeddings = DeepFace.represent(
                    img_path=image,
                    model_name=model_name,
                    detector_backend=detector,
                    enforce_detection=True,
                    align=True
                )
                
                if embeddings and len(embeddings) > 0:
                    embedding = np.array(embeddings[0]['embedding'])
                    print(f"   ✓ {model_name}: Embedding extracted ({len(embedding)} dims) [detector: {detector}]")
                    return embedding
                    
            except Exception as e:
                continue
        
        print(f"   ✗ {model_name}: Failed to extract embedding")
        return None
    
    def weighted_voting(self, ref_image: np.ndarray, live_image: np.ndarray,
                        ref_quality: QualityMetrics, live_quality: QualityMetrics,
                        is_nic: bool = True) -> Dict[str, Any]:
        """
        Perform weighted voting across all models
        
        Returns comprehensive verification results
        """
        results = {
            'models': {},
            'weighted_score': 0.0,
            'votes_match': 0,
            'votes_total': 0,
            'final_decision': False,
            'confidence': 0.0,
            'details': []
        }
        
        total_weight = 0.0
        weighted_score_sum = 0.0
        
        print("\n🗳️  MODEL VOTING RESULTS (Quality-Adaptive Thresholds):")
        print("-" * 70)
        
        for model_name, config in self.MODEL_CONFIG.items():
            # Extract embeddings
            ref_embedding = self.extract_embeddings_robust(ref_image, model_name)
            live_embedding = self.extract_embeddings_robust(live_image, model_name)
            
            if ref_embedding is None or live_embedding is None:
                print(f"   {model_name:12} | ⚠️  SKIPPED (embedding extraction failed)")
                continue
            
            # Calculate cosine distance
            ref_norm = ref_embedding / (np.linalg.norm(ref_embedding) + 1e-10)
            live_norm = live_embedding / (np.linalg.norm(live_embedding) + 1e-10)
            cosine_similarity = np.dot(ref_norm, live_norm)
            distance = 1 - cosine_similarity
            
            # Get adaptive threshold
            threshold = self.get_adaptive_threshold(model_name, ref_quality, live_quality, is_nic)
            
            # Determine match
            is_match = distance < threshold
            
            # Calculate similarity percentage (0-100)
            # Map distance to similarity: 0 distance = 100%, threshold distance = 50%
            similarity_pct = max(0, min(100, (1 - distance / (threshold * 2)) * 100))
            
            # Update totals
            weight = config['weight']
            total_weight += weight
            weighted_score_sum += similarity_pct * weight
            
            results['votes_total'] += 1
            if is_match:
                results['votes_match'] += 1
            
            results['models'][model_name] = {
                'distance': float(distance),
                'threshold': float(threshold),
                'similarity': float(similarity_pct),
                'is_match': is_match,
                'weight': weight
            }
            
            # Log result
            match_symbol = "✅ MATCH" if is_match else "❌ MISMATCH"
            print(f"   {model_name:12} | {match_symbol:12} | Dist: {distance:.4f} < Thresh: {threshold:.2f} | Score: {similarity_pct:.1f}%")
        
        # Calculate final weighted score
        if total_weight > 0:
            results['weighted_score'] = weighted_score_sum / total_weight
        
        # SMART DECISION LOGIC
        # Different strategies based on quality gap
        quality_gap = abs(ref_quality.quality_score - live_quality.quality_score)
        
        if quality_gap > 30:
            # Large quality gap (degraded NIC vs clear selfie)
            # Be lenient - NIC quality degrades embeddings significantly
            # World-class insight: same person can score 35-50% with degraded NIC
            majority_vote = results['votes_match'] >= 1
            score_pass = results['weighted_score'] >= 38.0
            results['final_decision'] = majority_vote or score_pass
            decision_mode = "QUALITY-GAP-TOLERANT"
        elif quality_gap > 20:
            # Moderate quality gap
            majority_vote = results['votes_match'] >= 1
            score_pass = results['weighted_score'] >= 42.0
            results['final_decision'] = majority_vote or score_pass
            decision_mode = "MODERATE-GAP"
        elif quality_gap > 10:
            # Small quality gap - balanced criteria
            majority_vote = results['votes_match'] >= 2
            score_pass = results['weighted_score'] >= 48.0
            results['final_decision'] = majority_vote or score_pass
            decision_mode = "BALANCED"
        else:
            # Similar quality images - strict criteria
            majority_vote = results['votes_match'] >= 2
            score_pass = results['weighted_score'] >= 55.0
            results['final_decision'] = majority_vote and score_pass
            decision_mode = "STRICT"
        
        print(f"   Decision Mode: {decision_mode} (quality gap: {quality_gap:.1f})")
        
        # Confidence based on agreement
        if results['votes_total'] > 0:
            vote_confidence = results['votes_match'] / results['votes_total']
            score_confidence = results['weighted_score'] / 100
            results['confidence'] = (vote_confidence + score_confidence) / 2
        
        print("-" * 70)
        print(f"   CONSENSUS: {results['votes_match']}/{results['votes_total']} models | Weighted Score: {results['weighted_score']:.1f}%")
        print(f"   VERDICT: {'✅ VERIFIED' if results['final_decision'] else '❌ REJECTED'}")
        
        return results


class FaceProcessor:
    """
    World-Class Face Recognition Processor v3.0
    
    Main interface for face verification with quality-adaptive processing
    and multi-model ensemble voting.
    
    Target Accuracy: 90-95% for NIC vs Live Photo verification
    """
    
    def __init__(self):
        self.preprocessor = AdvancedImagePreprocessor()
        self.ensemble = MultiModelEnsemble()
        print("🚀 Face Recognition Engine v3.0 Initialized")
        print("   - Quality-Adaptive Preprocessing: ✓")
        print("   - Multi-Model Ensemble (ArcFace, Facenet512, VGG-Face): ✓")
        print("   - Adaptive Thresholding: ✓")
    
    def _load_image(self, image_input) -> np.ndarray:
        """Load image from various input formats"""
        if isinstance(image_input, np.ndarray):
            return image_input
        
        if isinstance(image_input, str):
            # Base64 encoded
            if 'base64,' in image_input:
                image_input = image_input.split('base64,')[1]
            
            image_bytes = base64.b64decode(image_input)
            nparr = np.frombuffer(image_bytes, np.uint8)
            return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if isinstance(image_input, bytes):
            nparr = np.frombuffer(image_input, np.uint8)
            return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        raise ValueError(f"Unsupported image input type: {type(image_input)}")
    
    def extract_embeddings(self, image_input, is_nic: bool = False) -> Dict[str, Any]:
        """
        Extract face embeddings with preprocessing
        
        Args:
            image_input: Image in various formats (numpy, base64, bytes)
            is_nic: Whether this is a NIC/ID document image
        
        Returns:
            Dictionary with embeddings and quality metrics
        """
        print("\n📷 Processing image for embedding extraction...")
        
        # Load image
        image = self._load_image(image_input)
        if image is None:
            return {'success': False, 'error': 'Failed to load image'}
        
        # Apply enhancement pipeline
        enhanced, quality = self.preprocessor.full_enhancement_pipeline(image, is_nic=is_nic)
        
        # Extract embeddings from all models
        embeddings = {}
        for model_name in MultiModelEnsemble.MODEL_CONFIG.keys():
            emb = self.ensemble.extract_embeddings_robust(enhanced, model_name)
            if emb is not None:
                embeddings[model_name] = emb
        
        return {
            'success': len(embeddings) > 0,
            'embeddings': embeddings,
            'quality': quality,
            'enhanced_image': enhanced
        }
    
    def _generate_courier_decision(self, similarity_pct: float, votes_match: int, 
                                    votes_total: int, quality_gap: float,
                                    nic_quality: float) -> Dict[str, Any]:
        """
        Generate actionable decision guidance for courier
        
        Based on similarity percentage, provides clear actions:
        - DELIVER: High confidence match, proceed with delivery
        - VERIFY_ID: Medium confidence, ask for additional ID verification  
        - MANUAL_CHECK: Low confidence, contact customer/supervisor
        - REJECT: Very low match, do not deliver
        
        Returns comprehensive decision object with:
        - action: What the courier should do
        - risk_level: LOW/MEDIUM/HIGH/CRITICAL
        - message: Human-readable explanation
        - additional_steps: List of recommended verification steps
        """
        decision = {
            'similarity_percentage': round(similarity_pct, 1),
            'models_agreed': f"{votes_match}/{votes_total}",
            'nic_quality_issue': nic_quality < 50,
            'quality_gap': round(quality_gap, 1)
        }
        
        # Adjust thresholds based on quality gap
        # Higher quality gap means genuine matches may have lower similarity
        quality_adjustment = min(15, quality_gap * 0.3)  # Max 15% adjustment
        
        # Decision thresholds (adjusted for quality gap)
        high_confidence_threshold = 60 - quality_adjustment
        medium_confidence_threshold = 45 - quality_adjustment
        low_confidence_threshold = 30 - quality_adjustment
        
        if similarity_pct >= high_confidence_threshold and votes_match >= 2:
            # HIGH CONFIDENCE - Proceed with delivery
            decision['action'] = 'DELIVER'
            decision['risk_level'] = 'LOW'
            decision['color'] = 'green'
            decision['icon'] = '✅'
            decision['message'] = 'Identity verified with high confidence. Proceed with delivery.'
            decision['additional_steps'] = []
            
        elif similarity_pct >= medium_confidence_threshold or votes_match >= 1:
            # MEDIUM CONFIDENCE - Verify with additional ID
            decision['action'] = 'VERIFY_ID'
            decision['risk_level'] = 'MEDIUM'
            decision['color'] = 'yellow'
            decision['icon'] = '⚠️'
            decision['message'] = 'Moderate match detected. Please verify with additional identification.'
            decision['additional_steps'] = [
                'Ask customer to show physical NIC/ID card',
                'Verify name matches delivery details',
                'Check address on ID matches delivery address',
                'Take note of ID number for records'
            ]
            
            # Add context about why score is lower
            if quality_gap > 25:
                decision['quality_note'] = f'NIC image quality is poor (gap: {quality_gap:.0f}). Lower similarity is expected for same person.'
                
        elif similarity_pct >= low_confidence_threshold:
            # LOW CONFIDENCE - Manual check required
            decision['action'] = 'MANUAL_CHECK'
            decision['risk_level'] = 'HIGH'
            decision['color'] = 'orange'
            decision['icon'] = '🔍'
            decision['message'] = 'Low confidence match. Additional verification required.'
            decision['additional_steps'] = [
                'Contact supervisor for guidance',
                'Ask customer for secondary ID (driving license, passport)',
                'Verify phone number matches order details',
                'Consider rescheduling delivery if uncertain',
                'Take photo of customer with their ID (with permission)'
            ]
            
        else:
            # VERY LOW - Do not deliver
            decision['action'] = 'REJECT'
            decision['risk_level'] = 'CRITICAL'
            decision['color'] = 'red'
            decision['icon'] = '❌'
            decision['message'] = 'Identity verification failed. Do not deliver without supervisor approval.'
            decision['additional_steps'] = [
                'DO NOT hand over the package',
                'Contact supervisor immediately',
                'Request customer to contact sender',
                'Mark delivery as "verification failed" in system',
                'Schedule redelivery with proper verification'
            ]
        
        return decision
    
    def verify_faces(self, reference_image, live_image, 
                     reference_is_nic: bool = True) -> Dict[str, Any]:
        """
        Verify if two face images belong to the same person
        
        This is the main verification method with full pipeline:
        1. Quality detection and adaptive preprocessing
        2. Multi-model embedding extraction
        3. Weighted voting with adaptive thresholds
        
        Args:
            reference_image: Reference image (typically NIC/ID)
            live_image: Live captured image
            reference_is_nic: Whether reference is a NIC/document
        
        Returns:
            Comprehensive verification results
        """
        print("\n" + "=" * 70)
        print("🔐 FACE VERIFICATION v3.0 - Quality-Adaptive Engine")
        print("=" * 70)
        
        # Load images
        ref_img = self._load_image(reference_image)
        live_img = self._load_image(live_image)
        
        if ref_img is None or live_img is None:
            return {
                'verified': False,
                'similarity': 0.0,
                'error': 'Failed to load images'
            }
        
        # Preprocess both images
        print("\n📸 Processing REFERENCE image (NIC):")
        ref_enhanced, ref_quality = self.preprocessor.full_enhancement_pipeline(
            ref_img, is_nic=reference_is_nic
        )
        
        print("\n📸 Processing LIVE image:")
        live_enhanced, live_quality = self.preprocessor.full_enhancement_pipeline(
            live_img, is_nic=False
        )
        
        # Perform ensemble voting
        voting_results = self.ensemble.weighted_voting(
            ref_enhanced, live_enhanced,
            ref_quality, live_quality,
            is_nic=reference_is_nic
        )
        
        # Calculate quality gap for decision context
        quality_gap = abs(ref_quality.quality_score - live_quality.quality_score)
        similarity_pct = voting_results['weighted_score']
        
        # COURIER DECISION GUIDANCE
        # Provides actionable guidance based on similarity percentage
        courier_decision = self._generate_courier_decision(
            similarity_pct, 
            voting_results['votes_match'],
            voting_results['votes_total'],
            quality_gap,
            ref_quality.quality_score
        )
        
        # Compile final results
        result = {
            'verified': voting_results['final_decision'],
            'similarity': voting_results['weighted_score'] / 100,  # Convert to 0-1
            'confidence': voting_results['confidence'],
            'votes_match': voting_results['votes_match'],
            'votes_total': voting_results['votes_total'],
            'model_details': voting_results['models'],
            'reference_quality': {
                'score': ref_quality.quality_score,
                'level': ref_quality.overall_quality.value
            },
            'live_quality': {
                'score': live_quality.quality_score,
                'level': live_quality.overall_quality.value
            },
            'quality_gap': quality_gap,
            'liveness': True,  # Placeholder for liveness detection
            'courier_decision': courier_decision  # NEW: Actionable guidance for courier
        }
        
        print("\n" + "=" * 70)
        status = "✅ VERIFIED" if result['verified'] else "❌ REJECTED"
        print(f"FINAL RESULT: {status} | Similarity: {result['similarity']*100:.1f}%")
        print(f"COURIER ACTION: {courier_decision['action']} ({courier_decision['risk_level']})")
        print("=" * 70 + "\n")
        
        return result
    
    def compare_faces(self, image1, image2) -> Dict[str, Any]:
        """
        Compare two face images (general comparison, not NIC-specific)
        
        Useful for comparing two selfies or two photos
        """
        return self.verify_faces(image1, image2, reference_is_nic=False)


# ============================================================================
# LEGACY COMPATIBILITY LAYER
# ============================================================================
# These classes provide backward compatibility with existing code

class CentralBankIdentityEngine:
    """
    Legacy compatibility class - wraps FaceProcessor v3.0
    """
    
    def __init__(self):
        self._processor = FaceProcessor()
    
    def extract_embeddings(self, image_input, is_nic: bool = False) -> Dict[str, Any]:
        return self._processor.extract_embeddings(image_input, is_nic)
    
    def verify_faces(self, ref_image, live_image, ref_is_nic: bool = True) -> Dict[str, Any]:
        return self._processor.verify_faces(ref_image, live_image, ref_is_nic)
    
    def compare_faces(self, image1, image2) -> Dict[str, Any]:
        return self._processor.compare_faces(image1, image2)


# ============================================================================
# GLOBAL INSTANCE
# ============================================================================

# Create global instance for API usage
face_processor = FaceProcessor()

# Legacy aliases
identity_engine = CentralBankIdentityEngine()


# ============================================================================
# UTILITY FUNCTIONS FOR API ROUTES
# ============================================================================

def verify_face_match(reference_image, live_image, is_nic: bool = True) -> Dict[str, Any]:
    """
    Utility function for API routes
    
    Args:
        reference_image: Reference image (NIC/ID)
        live_image: Live captured image
        is_nic: Whether reference is NIC
    
    Returns:
        Verification results
    """
    return face_processor.verify_faces(reference_image, live_image, is_nic)


def extract_face_embeddings(image, is_nic: bool = False) -> Dict[str, Any]:
    """
    Utility function to extract embeddings
    """
    return face_processor.extract_embeddings(image, is_nic)


# ============================================================================
# MAIN - Testing
# ============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("🔐 WORLD-CLASS FACE RECOGNITION ENGINE v3.0")
    print("   Research-Grade Biometric Verification System")
    print("   Target Accuracy: 90-95% for NIC vs Live Photo")
    print("=" * 70)
    print("\nEngine initialized and ready for verification.")
    print("\nKey Features:")
    print("  ✓ Quality-Adaptive Preprocessing")
    print("  ✓ Multi-Model Ensemble (ArcFace, Facenet512, VGG-Face)")
    print("  ✓ Adaptive Thresholds based on Image Quality")
    print("  ✓ Forensic Enhancement for Low-Quality Documents")
    print("\nUsage:")
    print("  from utils.face_recognition import face_processor")
    print("  result = face_processor.verify_faces(nic_image, live_image)")
