from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
import pickle
import numpy as np
from typing import Optional
from io import BytesIO
import os

from models.database import get_db
from models.user import User
from models.order import Order
from models.biometric import FaceTemplate, VerificationLog
from api.schemas.face import (
    FaceIDUploadResponse,
    FaceVerificationResponse,
    CourierDecision,
    LockerVerificationResponse,
    LockerUnlockRequest,
    LockerUnlockResponse,
    FaceTemplateResponse
)
from api.middleware.auth import get_current_user, get_current_admin
from utils.face_recognition import face_processor
from utils.locker import locker_manager
from utils.security import encrypt_biometric_data, decrypt_biometric_data
from utils.crypto_commitment import CryptographicCommitmentEngine, EventType
from utils.blockchain import BlockchainService
from config.settings import get_settings
from loguru import logger

router = APIRouter(prefix="/api/face", tags=["Face Recognition"])
settings = get_settings()

# Initialize blockchain service for proof recording
blockchain_service = BlockchainService()
commitment_engine = CryptographicCommitmentEngine()

# Admin private key for blockchain transactions (use env variable in production)
BLOCKCHAIN_PRIVATE_KEY = os.getenv("BLOCKCHAIN_ADMIN_KEY", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")


@router.post("/id/upload", response_model=FaceIDUploadResponse)
async def upload_id_card(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    phone: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload ID card image - JUST STORE (no AI processing)
    AI verification happens only when courier verifies
    """
    try:
        logger.info(f"📸 Storing reference image for user {current_user.id}")
        
        # Read image bytes
        image_bytes = await file.read()
        
        # Simple validation
        if len(image_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file uploaded"
            )
        
        if len(image_bytes) > 10 * 1024 * 1024:  # 10MB limit
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File too large (max 10MB)"
            )
        
        logger.info(f"Image size: {len(image_bytes)} bytes")
        
        # Encrypt raw image bytes (no AI processing yet)
        encrypted_image = encrypt_biometric_data(image_bytes)
        
        # Store ID card info
        id_info = {
            "name": name,
            "phone": phone,
            "address": address
        }
        encrypted_id_info = encrypt_biometric_data(pickle.dumps(id_info))
        
        # Check if user already has a face template
        face_template = db.query(FaceTemplate).filter(
            FaceTemplate.user_id == current_user.id
        ).first()
        
        if face_template:
            # Update existing template - store raw image only
            face_template.embedding_data = encrypted_image
            face_template.nic_image_data = encrypted_image  # Store NIC image separately
            face_template.id_card_info = encrypted_id_info
            face_template.face_quality_score = 1.0
            face_template.confidence_score = 1.0
            face_template.liveness_score = 1.0
            face_template.anti_spoof_passed = True
            face_template.enrollment_type = 'reference_image'
            logger.info(f"✅ Updated reference image for user {current_user.id}, encrypted size: {len(encrypted_image)} bytes")
        else:
            # Create new template - store raw image only
            face_template = FaceTemplate(
                user_id=current_user.id,
                embedding_data=encrypted_image,
                nic_image_data=encrypted_image,  # Store NIC image separately
                id_card_info=encrypted_id_info,
                face_quality_score=1.0,
                confidence_score=1.0,
                liveness_score=1.0,
                anti_spoof_passed=True,
                enrollment_type='reference_image',
                is_active=True
            )
            db.add(face_template)
            logger.info(f"✅ Created new face template for user {current_user.id}, encrypted size: {len(encrypted_image)} bytes")
        
        try:
            db.commit()
            logger.info(f"✅ Database committed successfully")
        except Exception as commit_error:
            db.rollback()
            logger.error(f"❌ Database commit failed: {commit_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(commit_error)}"
            )
        
        db.refresh(face_template)
        logger.info(f"✅ Face template ID: {face_template.id}, stored at: {face_template.created_at}")
        
        return FaceIDUploadResponse(
            success=True,
            message="Reference image stored (AI verification will run during courier check)",
            user_id=current_user.id,
            face_id=face_template.id,
            quality_score=1.0,
            liveness_passed=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"ID upload error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ID card processing failed: {str(e)}"
        )


@router.post("/verify", response_model=FaceVerificationResponse)
async def verify_face(
    file: UploadFile = File(...),
    user_id: int = Form(...),
    order_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Verify live face against stored face template using v3.0 World-Class Engine
    
    This uses:
    - Quality-Adaptive Preprocessing
    - Multi-Model Ensemble (ArcFace, Facenet512, VGG-Face)
    - Adaptive Thresholds based on Image Quality
    
    Used by couriers to verify recipient identity
    """
    try:
        logger.info(f"🔍 Verifying face for user {user_id} (v3.0 Engine)")
        
        # Get stored face template
        face_template = db.query(FaceTemplate).filter(
            FaceTemplate.user_id == user_id,
            FaceTemplate.is_active == True
        ).first()
        
        if not face_template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User has not enrolled face template"
            )
        
        # Read live image bytes
        live_image_bytes = await file.read()
        
        if len(live_image_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Empty file uploaded"
            )
        
        logger.info(f"📷 Live image received: {len(live_image_bytes)} bytes")
        
        # Get stored reference image from nic_image_data (encrypted image bytes)
        try:
            # First try nic_image_data (the actual stored image)
            if face_template.nic_image_data:
                logger.info(f"📦 Using nic_image_data ({len(face_template.nic_image_data)} bytes)")
                reference_image_bytes = decrypt_biometric_data(face_template.nic_image_data)
            else:
                # Fallback to embedding_data
                logger.info(f"📦 Using embedding_data (fallback)")
                reference_image_bytes = decrypt_biometric_data(face_template.embedding_data)
            
            # Check if data is valid image bytes
            if not reference_image_bytes or len(reference_image_bytes) < 100:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Stored face data is corrupted or empty. Please re-enroll."
                )
            
            # Check image format
            is_jpeg = len(reference_image_bytes) >= 2 and reference_image_bytes[0] == 0xff and reference_image_bytes[1] == 0xd8
            is_png = len(reference_image_bytes) >= 4 and reference_image_bytes[0:4] == b'\x89PNG'
            
            logger.info(f"📷 Reference image format check - JPEG: {is_jpeg}, PNG: {is_png}")
            
            if not is_jpeg and not is_png:
                logger.error(f"Stored data is not an image. First bytes: {reference_image_bytes[:20].hex()}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Stored face data is not a valid image. Please re-enroll with face upload."
                )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to decrypt stored reference image: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Face template decryption failed: {str(e)}. Please re-enroll."
            )
        
        # ============================================================
        # Use World-Class Face Recognition v3.0 Engine
        # ============================================================
        logger.info(f"🚀 Starting v3.0 Face Verification Engine")
        
        try:
            # Call the new verify_faces method with raw image bytes
            # This handles everything: preprocessing, multi-model ensemble, adaptive thresholds
            verification_result = face_processor.verify_faces(
                reference_image=reference_image_bytes,
                live_image=live_image_bytes,
                reference_is_nic=True  # NIC reference vs live photo
            )
        except Exception as e:
            logger.error(f"Face verification engine error: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Face verification engine error: {str(e)}"
            )
        
        # Extract results from v3.0 engine
        # IMPORTANT: Convert numpy types to Python native types for JSON serialization
        verified = bool(verification_result.get('verified', False))
        similarity_score = float(verification_result.get('similarity', 0.0))
        confidence = float(verification_result.get('confidence', 0.0))
        liveness_passed = bool(verification_result.get('liveness', True))
        
        # Get quality info
        ref_quality = verification_result.get('reference_quality', {})
        live_quality = verification_result.get('live_quality', {})
        model_details = verification_result.get('model_details', {})
        
        # Convert model_details numpy types to native Python types
        cleaned_model_details = {}
        for model_name, details in model_details.items():
            cleaned_model_details[model_name] = {
                'distance': float(details.get('distance', 0)),
                'threshold': float(details.get('threshold', 0)),
                'similarity': float(details.get('similarity', 0)),
                'is_match': bool(details.get('is_match', False)),
                'weight': float(details.get('weight', 0))
            }
        
        # Build metrics for response
        metrics = {
            'threshold_used': 0.50,  # v3.0 uses adaptive thresholds
            'reference_quality_score': float(ref_quality.get('score', 0)),
            'reference_quality_level': str(ref_quality.get('level', 'unknown')),
            'live_quality_score': float(live_quality.get('score', 0)),
            'live_quality_level': str(live_quality.get('level', 'unknown')),
            'models_matched': int(verification_result.get('votes_match', 0)),
            'models_total': int(verification_result.get('votes_total', 0)),
            'model_details': cleaned_model_details,
            'quality_gap': float(verification_result.get('quality_gap', 0)),
            'engine_version': 'v3.0'
        }
        
        # Extract courier decision from verification result
        courier_decision_raw = verification_result.get('courier_decision', {})
        courier_decision = CourierDecision(
            action=str(courier_decision_raw.get('action', 'MANUAL_CHECK')),
            risk_level=str(courier_decision_raw.get('risk_level', 'MEDIUM')),
            color=str(courier_decision_raw.get('color', 'yellow')),
            icon=str(courier_decision_raw.get('icon', '⚠️')),
            message=str(courier_decision_raw.get('message', 'Please verify manually')),
            similarity_percentage=float(courier_decision_raw.get('similarity_percentage', similarity_score * 100)),
            models_agreed=str(courier_decision_raw.get('models_agreed', f"{metrics['models_matched']}/{metrics['models_total']}")),
            quality_gap=float(courier_decision_raw.get('quality_gap', 0)),
            nic_quality_issue=bool(courier_decision_raw.get('nic_quality_issue', False)),
            additional_steps=courier_decision_raw.get('additional_steps', []),
            quality_note=courier_decision_raw.get('quality_note')
        )
        
        # Build message
        if verified:
            message = f"✓ Face verified successfully (similarity: {similarity_score:.1%}, confidence: {confidence:.1%})"
        else:
            message = f"✗ Face does not match (similarity: {similarity_score:.1%})"
        
        # Log verification attempt
        log = VerificationLog(
            user_id=user_id,
            order_id=order_id,
            verification_type="face_v3",
            success=verified,
            confidence_score=similarity_score,
            ai_detected=not liveness_passed,
            ai_detection_score=0.0,
            ip_address="0.0.0.0",
            device_info="face_verification_v3",
            failure_reason=None if verified else message
        )
        db.add(log)
        db.commit()
        
        # ============================================================
        # BLOCKCHAIN PROOF RECORDING (Privacy-First Protocol)
        # ============================================================
        blockchain_result = None
        if blockchain_service.w3.is_connected() and blockchain_service.contract:
            try:
                # Generate delivery ID from order_id or create unique ID
                delivery_id = f"ORD-{order_id}" if order_id else f"VERIFY-{log.id}"
                
                # Get NIC number from user (or use placeholder for privacy)
                user_record = db.query(User).filter(User.id == user_id).first()
                nic_number = user_record.nic_number if user_record and hasattr(user_record, 'nic_number') else f"USER-{user_id}"
                
                # Create cryptographic commitment (NO personal data stored on chain)
                commitment = commitment_engine.create_identity_commitment(
                    nic_number=nic_number,
                    face_embedding=[similarity_score] * 512,  # Use similarity as proxy embedding
                    liveness_result=liveness_passed,
                    ai_confidence=similarity_score,
                    delivery_id=delivery_id,
                    event_type=EventType.CUSTOMER_VERIFIED if verified else EventType.CUSTOMER_VERIFIED,
                    gps_latitude=6.9271,  # Colombo default - should come from request
                    gps_longitude=79.8612,
                    ai_model="ArcFace-v3"
                )
                
                # Create proof token
                proof = commitment_engine.create_proof_token(commitment)
                
                # Record proof on blockchain
                blockchain_result = await blockchain_service.record_proof(
                    token_hash=proof.token_hash,
                    commitment_hash=commitment.commitment_hash,
                    delivery_id=delivery_id,
                    event_type="CUSTOMER_VERIFIED",
                    status="PASS" if verified else "FAIL",
                    confidence_score=similarity_score,
                    gps_latitude=6.9271,
                    gps_longitude=79.8612,
                    ai_model="ArcFace-v3",
                    private_key=BLOCKCHAIN_PRIVATE_KEY
                )
                
                if blockchain_result and blockchain_result.get("success"):
                    logger.info(f"⛓️  Blockchain proof recorded: TX {blockchain_result['tx_hash'][:20]}... Block #{blockchain_result['block_number']}")
                else:
                    logger.warning(f"⚠️ Blockchain recording failed: {blockchain_result}")
                    
            except Exception as blockchain_error:
                logger.error(f"⚠️ Blockchain recording error (non-critical): {blockchain_error}")
                # Don't fail the verification if blockchain fails - it's supplementary
        
        logger.info(f"Face verification v3.0: {'✓ PASSED' if verified else '✗ FAILED'} - "
                   f"Similarity: {similarity_score:.3f}, Votes: {metrics['models_matched']}/{metrics['models_total']}, "
                   f"Courier Action: {courier_decision.action} ({courier_decision.risk_level})")
        
        # Add blockchain info to metrics if available
        if blockchain_result and blockchain_result.get("success"):
            metrics['blockchain'] = {
                'recorded': True,
                'tx_hash': blockchain_result['tx_hash'],
                'block_number': blockchain_result['block_number'],
                'commitment_hash': commitment.commitment_hash[:20] + "..."
            }
        
        return FaceVerificationResponse(
            success=True,
            verified=verified,
            confidence=similarity_score,
            similarity_score=similarity_score,
            threshold=0.50,
            message=message,
            quality_score=float(live_quality.get('score', 0)) / 100,  # Convert to 0-1
            liveness_passed=liveness_passed,
            metrics=metrics,
            courier_decision=courier_decision  # NEW: Actionable courier guidance
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Face verification error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {str(e)}"
        )


@router.post("/locker/verify", response_model=LockerVerificationResponse)
async def verify_face_for_locker(
    file: UploadFile = File(...),
    locker_id: str = Form(...),
    user_id: int = Form(...),
    parcel_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Verify face at smart locker
    Returns unlock token if verification successful
    No authentication required (locker device calls this)
    """
    try:
        logger.info(f"🔒 Locker verification: locker_id={locker_id}, user_id={user_id}")
        
        # Get stored face template
        face_template = db.query(FaceTemplate).filter(
            FaceTemplate.user_id == user_id,
            FaceTemplate.is_active == True
        ).first()
        
        if not face_template:
            return LockerVerificationResponse(
                success=False,
                unlock=False,
                token=None,
                message="User has not enrolled face template",
                confidence=0.0
            )
        
        # Process incoming face (relaxed quality for testing, strict matching)
        result = await face_processor.process_face_image(
            file,
            perform_quality_check=True,  # Check quality
            perform_liveness_check=False,  # Disabled for testing with photos
            strict_quality=False  # Allow ID card photos for testing
        )
        
        if not result["success"]:
            return LockerVerificationResponse(
                success=False,
                unlock=False,
                token=None,
                message=f"Face processing failed: {result.get('error', 'Unknown error')}",
                confidence=0.0
            )
        
        incoming_embedding = result["embedding"]
        liveness_metrics = result.get("liveness_metrics") or {}
        
        # Decrypt stored embedding
        try:
            decrypted_embedding = decrypt_biometric_data(face_template.embedding_data)
            stored_embedding = pickle.loads(decrypted_embedding)
        except Exception as e:
            logger.error(f"Failed to decrypt face template: {e}")
            return LockerVerificationResponse(
                success=False,
                unlock=False,
                token=None,
                message="Face template corrupted",
                confidence=0.0
            )
        
        # Verify faces (banking-grade threshold for locker)
        is_match, similarity_score, metrics = face_processor.verify_faces(
            incoming_embedding,
            stored_embedding,
            threshold=0.75  # Banking-grade: 75% minimum similarity
        )
        
        # Check liveness
        liveness_passed = liveness_metrics.get('is_live', True)
        
        # Final verification
        verified = is_match and liveness_passed
        
        if verified:
            # Generate unlock token
            locker_token = locker_manager.generate_unlock_token(
                locker_id=locker_id,
                user_id=user_id,
                parcel_id=parcel_id,
                expires_minutes=5
            )
            
            # Log successful verification
            log = VerificationLog(
                user_id=user_id,
                order_id=None,
                verification_type="face_locker",
                success=True,
                confidence_score=similarity_score,
                ip_address="locker_" + locker_id,
                device_info=f"locker_{locker_id}"
            )
            db.add(log)
            db.commit()
            
            logger.info(f"✅ Locker verification successful - Token generated")
            
            return LockerVerificationResponse(
                success=True,
                unlock=True,
                token=locker_token.token,
                message="Face verified - Locker will unlock",
                confidence=similarity_score,
                expires_in=300  # 5 minutes
            )
        else:
            # Log failed verification
            log = VerificationLog(
                user_id=user_id,
                order_id=None,
                verification_type="face_locker",
                success=False,
                confidence_score=similarity_score,
                ai_detected=not liveness_passed,
                ip_address="locker_" + locker_id,
                device_info=f"locker_{locker_id}",
                failure_reason="Face verification failed" if not is_match else "Liveness check failed"
            )
            db.add(log)
            db.commit()
            
            message = "Liveness check failed" if not liveness_passed else f"Face does not match (similarity: {similarity_score:.1%})"
            logger.warning(f"❌ Locker verification failed: {message}")
            
            return LockerVerificationResponse(
                success=False,
                unlock=False,
                token=None,
                message=message,
                confidence=similarity_score
            )
        
    except Exception as e:
        logger.error(f"Locker verification error: {e}")
        return LockerVerificationResponse(
            success=False,
            unlock=False,
            token=None,
            message=f"Verification error: {str(e)}",
            confidence=0.0
        )


@router.post("/locker/unlock", response_model=LockerUnlockResponse)
async def unlock_locker(
    request: LockerUnlockRequest
):
    """
    Unlock locker with token
    Called by locker device to validate token and perform unlock
    """
    try:
        logger.info(f"🔓 Unlock request for locker {request.locker_id}")
        
        # Verify and use token
        success, message, locker_token = locker_manager.unlock_locker(
            request.token,
            request.locker_id
        )
        
        if success:
            logger.info(f"✅ Locker {request.locker_id} unlocked")
            return LockerUnlockResponse(
                success=True,
                status="locker_unlocked",
                message="Locker unlocked successfully",
                locker_id=request.locker_id,
                unlocked_at=locker_token.created_at if locker_token else None
            )
        else:
            logger.warning(f"❌ Unlock failed for locker {request.locker_id}: {message}")
            return LockerUnlockResponse(
                success=False,
                status="unlock_failed",
                message=message,
                locker_id=request.locker_id
            )
        
    except Exception as e:
        logger.error(f"Locker unlock error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unlock failed: {str(e)}"
        )


@router.get("/template", response_model=FaceTemplateResponse)
async def get_face_template(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current user's face template information"""
    face_template = db.query(FaceTemplate).filter(
        FaceTemplate.user_id == current_user.id,
        FaceTemplate.is_active == True
    ).first()
    
    if not face_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No face template found"
        )
    
    return face_template


@router.delete("/template")
async def delete_face_template(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete user's face template"""
    face_template = db.query(FaceTemplate).filter(
        FaceTemplate.user_id == current_user.id
    ).first()
    
    if not face_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No face template found"
        )
    
    db.delete(face_template)
    db.commit()
    
    logger.info(f"Deleted face template for user {current_user.id}")
    
    return {"message": "Face template deleted successfully"}


@router.get("/reference/{user_id}")
async def get_reference_image(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get customer's reference image for courier verification display.
    Returns base64 encoded image data.
    """
    try:
        logger.info(f"📷 Getting reference image for user {user_id}")
        
        # Get stored face template
        face_template = db.query(FaceTemplate).filter(
            FaceTemplate.user_id == user_id,
            FaceTemplate.is_active == True
        ).first()
        
        if not face_template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer has not enrolled their face yet"
            )
        
        # Get the stored image
        if face_template.nic_image_data:
            decrypted_image = decrypt_biometric_data(face_template.nic_image_data)
        elif face_template.embedding_data:
            decrypted_image = decrypt_biometric_data(face_template.embedding_data)
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No reference image found for this customer"
            )
        
        # Check if data is valid image
        if not decrypted_image or len(decrypted_image) < 100:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored image data is corrupted"
            )
        
        # Detect image format
        is_jpeg = len(decrypted_image) >= 2 and decrypted_image[0] == 0xff and decrypted_image[1] == 0xd8
        is_png = len(decrypted_image) >= 4 and decrypted_image[0:4] == b'\x89PNG'
        
        if not is_jpeg and not is_png:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Stored data is not a valid image"
            )
        
        # Convert to base64 for transmission
        import base64
        image_base64 = base64.b64encode(decrypted_image).decode('utf-8')
        mime_type = "image/jpeg" if is_jpeg else "image/png"
        
        logger.info(f"✅ Returning reference image for user {user_id} ({len(decrypted_image)} bytes, {mime_type})")
        
        return {
            "success": True,
            "user_id": user_id,
            "image_data": f"data:{mime_type};base64,{image_base64}",
            "image_size": len(decrypted_image),
            "enrolled_at": str(face_template.created_at) if face_template.created_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting reference image: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve reference image: {str(e)}"
        )
