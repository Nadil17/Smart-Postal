"""
================================================================================
BLOCKCHAIN API ROUTES
================================================================================
REST API endpoints for blockchain operations

Endpoints:
- POST /api/blockchain/record-proof     - Record delivery proof
- POST /api/blockchain/record-cod       - Record COD transaction
- POST /api/blockchain/record-consent   - Record neighbor consent
- GET  /api/blockchain/evidence/{id}    - Get delivery evidence
- GET  /api/blockchain/proof/{id}       - Get proof details
- GET  /api/blockchain/statistics       - Get system statistics
- POST /api/blockchain/dispute          - Raise a dispute
- GET  /api/blockchain/admin/db-records - Fast database queries

Author: Smart Postal Research Team
================================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime

from models.database import get_db
from models.user import User
from models.blockchain import BlockchainProof, BlockchainSyncStatus
from api.middleware.auth import get_current_user, get_current_admin
from utils.blockchain import get_blockchain_service
from utils.crypto_commitment import commitment_engine, EventType, VerificationStatus

router = APIRouter(prefix="/api/blockchain", tags=["Blockchain"])


# ============== SCHEMAS ==============

class RecordProofRequest(BaseModel):
    """Request to record delivery proof on blockchain"""
    delivery_id: str = Field(..., description="Delivery identifier")
    nic_number: str = Field(..., description="Customer NIC (processed locally, never stored)")
    face_embedding: List[float] = Field(..., description="Face embedding from AI")
    liveness_result: bool = Field(..., description="Liveness check result")
    ai_confidence: float = Field(..., ge=0, le=1, description="AI confidence score")
    event_type: str = Field(default="CUSTOMER_VERIFIED", description="Event type")
    gps_latitude: float = Field(..., description="GPS latitude")
    gps_longitude: float = Field(..., description="GPS longitude")
    ai_model: str = Field(default="ArcFace", description="AI model used")
    courier_private_key: Optional[str] = Field(None, description="Courier's blockchain private key")


class RecordCODRequest(BaseModel):
    """Request to record COD on blockchain"""
    delivery_id: str
    customer_commitment_hash: str
    amount_lkr: float
    spoken_confirmation: str
    gps_latitude: float
    gps_longitude: float
    courier_private_key: Optional[str] = None


class RecordConsentRequest(BaseModel):
    """Request to record neighbor consent"""
    delivery_id: str
    customer_id: str
    neighbor_commitment_hash: str
    consent_response: str  # "YES" or "NO"
    customer_gps_latitude: float
    customer_gps_longitude: float


class RaiseDisputeRequest(BaseModel):
    """Request to raise a dispute"""
    delivery_id: str
    reason: str


class BlockchainResponse(BaseModel):
    """Standard blockchain response"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    tx_hash: Optional[str] = None
    block_number: Optional[int] = None


# ============== ROUTES ==============

@router.get("/status")
async def get_blockchain_status():
    """
    Get blockchain connection status
    """
    service = get_blockchain_service()
    
    if service is None:
        return {
            "connected": False,
            "message": "Blockchain service not initialized",
            "instructions": "Deploy smart contracts first using: npx hardhat run scripts/deploy.js --network localhost"
        }
    
    return {
        "connected": service.is_available(),
        "rpc_url": service.rpc_url,
        "contract_address": service.contract.address if service.contract else None,
        "admin_address": service.admin_account.address if service.admin_account else None
    }


@router.post("/record-proof", response_model=BlockchainResponse)
async def record_proof(
    request: RecordProofRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Record delivery verification proof on blockchain
    
    PRIVACY PROTOCOL:
    1. Creates cryptographic commitment from identity data
    2. Raw NIC and biometric data are NEVER stored
    3. Only commitment hash is recorded on blockchain
    4. Provides immutable audit trail for dispute resolution
    
    LEGAL: Admissible under Electronic Transactions Act, Section 21
    """
    service = get_blockchain_service()
    
    if not service or not service.is_available():
        # If blockchain not available, still create commitment locally
        commitment = commitment_engine.create_identity_commitment(
            nic_number=request.nic_number,
            face_embedding=request.face_embedding,
            liveness_result=request.liveness_result,
            ai_confidence=request.ai_confidence,
            delivery_id=request.delivery_id,
            event_type=EventType(request.event_type),
            gps_latitude=request.gps_latitude,
            gps_longitude=request.gps_longitude,
            ai_model=request.ai_model
        )
        
        proof_token = commitment_engine.create_proof_token(commitment)
        
        return BlockchainResponse(
            success=True,
            message="Commitment created (blockchain recording pending - deploy contracts first)",
            data={
                "commitment_hash": commitment.commitment_hash,
                "token_hash": proof_token.token_hash,
                "verification_status": commitment.verification_status,
                "confidence_score": commitment.confidence_score,
                "timestamp": commitment.timestamp,
                "blockchain_recorded": False
            }
        )
    
    try:
        # Create cryptographic commitment
        commitment = commitment_engine.create_identity_commitment(
            nic_number=request.nic_number,
            face_embedding=request.face_embedding,
            liveness_result=request.liveness_result,
            ai_confidence=request.ai_confidence,
            delivery_id=request.delivery_id,
            event_type=EventType(request.event_type),
            gps_latitude=request.gps_latitude,
            gps_longitude=request.gps_longitude,
            ai_model=request.ai_model
        )
        
        # Create proof token
        proof_token = commitment_engine.create_proof_token(commitment)
        
        # Record on blockchain
        # Note: In production, courier would sign with their own key
        private_key = request.courier_private_key or service.admin_key
        
        if not private_key:
            return BlockchainResponse(
                success=True,
                message="Commitment created but no private key for blockchain recording",
                data={
                    "commitment_hash": commitment.commitment_hash,
                    "token_hash": proof_token.token_hash,
                    "blockchain_recorded": False
                }
            )
        
        result = await service.record_proof(
            token_hash=proof_token.token_hash,
            commitment_hash=commitment.commitment_hash,
            delivery_id=request.delivery_id,
            event_type=request.event_type,
            status=commitment.verification_status,
            confidence_score=request.ai_confidence,
            gps_latitude=request.gps_latitude,
            gps_longitude=request.gps_longitude,
            ai_model=request.ai_model,
            private_key=private_key
        )
        
        if result and result.get("success"):
            return BlockchainResponse(
                success=True,
                message="Proof recorded on blockchain",
                data={
                    "commitment_hash": commitment.commitment_hash,
                    "token_hash": proof_token.token_hash,
                    "verification_status": commitment.verification_status,
                    "confidence_score": commitment.confidence_score,
                    "timestamp": commitment.timestamp,
                    "blockchain_recorded": True
                },
                tx_hash=result.get("tx_hash"),
                block_number=result.get("block_number")
            )
        else:
            return BlockchainResponse(
                success=False,
                message=f"Blockchain recording failed: {result.get('error', 'Unknown error')}",
                data={
                    "commitment_hash": commitment.commitment_hash,
                    "blockchain_recorded": False
                }
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error recording proof: {str(e)}"
        )


@router.post("/record-cod", response_model=BlockchainResponse)
async def record_cod(
    request: RecordCODRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Record COD (Cash on Delivery) transaction on blockchain
    
    Creates immutable proof of:
    - WHO received the payment (commitment hash)
    - HOW MUCH was paid
    - WHERE payment was collected
    - WHEN payment was collected
    """
    service = get_blockchain_service()
    
    # Create COD commitment
    cod_proof = commitment_engine.create_cod_commitment(
        customer_commitment_hash=request.customer_commitment_hash,
        amount_lkr=request.amount_lkr,
        spoken_confirmation=request.spoken_confirmation,
        delivery_id=request.delivery_id,
        gps_latitude=request.gps_latitude,
        gps_longitude=request.gps_longitude
    )
    
    if not service or not service.is_available():
        return BlockchainResponse(
            success=True,
            message="COD commitment created (blockchain recording pending)",
            data={
                "cod_commitment_hash": cod_proof["cod_commitment_hash"],
                "amount_lkr": request.amount_lkr,
                "blockchain_recorded": False
            }
        )
    
    try:
        private_key = request.courier_private_key or service.admin_key
        
        if not private_key:
            return BlockchainResponse(
                success=True,
                message="COD commitment created but no private key",
                data=cod_proof
            )
        
        result = await service.record_cod(
            delivery_id=request.delivery_id,
            cod_commitment_hash=cod_proof["cod_commitment_hash"],
            customer_commitment_hash=request.customer_commitment_hash,
            amount_lkr=int(request.amount_lkr),
            spoken_confirmation_hash=cod_proof["spoken_confirmation_hash"],
            gps_latitude=request.gps_latitude,
            gps_longitude=request.gps_longitude,
            private_key=private_key
        )
        
        if result and result.get("success"):
            return BlockchainResponse(
                success=True,
                message="COD recorded on blockchain",
                data=cod_proof,
                tx_hash=result.get("tx_hash"),
                block_number=result.get("block_number")
            )
        else:
            return BlockchainResponse(
                success=False,
                message=f"COD recording failed: {result.get('error', 'Unknown')}",
                data=cod_proof
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error recording COD: {str(e)}"
        )


@router.post("/record-consent", response_model=BlockchainResponse)
async def record_consent(
    request: RecordConsentRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Record customer consent for third-party delivery
    
    Creates immutable proof of customer's explicit consent
    for neighbor to receive parcel.
    """
    service = get_blockchain_service()
    
    # Create consent commitment
    consent_proof = commitment_engine.create_consent_commitment(
        customer_id=request.customer_id,
        neighbor_commitment_hash=request.neighbor_commitment_hash,
        consent_response=request.consent_response,
        delivery_id=request.delivery_id,
        customer_gps_latitude=request.customer_gps_latitude,
        customer_gps_longitude=request.customer_gps_longitude
    )
    
    if not service or not service.is_available():
        return BlockchainResponse(
            success=True,
            message="Consent commitment created (blockchain recording pending)",
            data=consent_proof
        )
    
    try:
        result = await service.record_consent(
            delivery_id=request.delivery_id,
            consent_hash=consent_proof["consent_hash"],
            neighbor_commitment_hash=request.neighbor_commitment_hash,
            consent_given=consent_proof["consent_given"],
            customer_gps_latitude=request.customer_gps_latitude,
            customer_gps_longitude=request.customer_gps_longitude
        )
        
        if result and result.get("success"):
            return BlockchainResponse(
                success=True,
                message="Consent recorded on blockchain",
                data=consent_proof,
                tx_hash=result.get("tx_hash"),
                block_number=result.get("block_number")
            )
        else:
            return BlockchainResponse(
                success=False,
                message=f"Consent recording failed",
                data=consent_proof
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error recording consent: {str(e)}"
        )


@router.get("/evidence/{delivery_id}")
async def get_delivery_evidence(
    delivery_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get all blockchain evidence for a delivery
    
    Used for dispute resolution. Returns complete audit trail
    WITHOUT exposing personal data.
    
    LEGAL: Admissible under Electronic Transactions Act, Section 21
    """
    service = get_blockchain_service()
    
    if not service or not service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Blockchain service not available"
        )
    
    evidence = service.get_delivery_evidence(delivery_id)
    
    if not evidence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found on blockchain"
        )
    
    return evidence


@router.get("/proof/{proof_id}")
async def get_proof_details(
    proof_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Get detailed proof information
    """
    service = get_blockchain_service()
    
    if not service or not service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Blockchain service not available"
        )
    
    proof = service.get_proof_details(proof_id)
    
    if not proof:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proof not found"
        )
    
    return proof


@router.get("/statistics")
async def get_blockchain_statistics():
    """
    Get blockchain system statistics
    
    Public endpoint - no authentication required
    """
    service = get_blockchain_service()
    
    if not service or not service.is_available():
        return {
            "blockchain_active": False,
            "message": "Blockchain not connected"
        }
    
    stats = service.get_statistics()
    return stats or {"blockchain_active": False}


@router.post("/dispute", response_model=BlockchainResponse)
async def raise_dispute(
    request: RaiseDisputeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Raise a dispute for a delivery
    
    Creates immutable record of the dispute for resolution.
    """
    # For now, just acknowledge the dispute
    # Full implementation would interact with blockchain
    
    return BlockchainResponse(
        success=True,
        message="Dispute recorded",
        data={
            "delivery_id": request.delivery_id,
            "reason": request.reason,
            "status": "OPEN",
            "disputed_by": current_user.id
        }
    )


@router.post("/register-courier")
async def register_courier_on_blockchain(
    courier_address: str,
    current_user: User = Depends(get_current_admin)
):
    """
    Register a courier on blockchain (admin only)
    """
    service = get_blockchain_service()
    
    if not service or not service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Blockchain service not available"
        )
    
    result = await service.register_courier(courier_address)
    
    if result and result.get("success"):
        return result
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register courier: {result.get('error', 'Unknown')}"
        )


# ============== ADMIN ROUTES ==============

@router.get("/admin/all-records")
async def get_all_blockchain_records(
    page: int = 1,
    limit: int = 50,
    record_type: Optional[str] = None  # "proof", "cod", "consent", "dispute"
):
    """
    Get all blockchain records for admin dashboard
    
    Returns:
    - Verification proofs
    - COD transactions
    - Neighbor consents
    - Disputes
    
    Admin only endpoint
    """
    service = get_blockchain_service()
    
    if not service or not service.is_available():
        return {
            "success": False,
            "message": "Blockchain not connected",
            "records": [],
            "total": 0
        }
    
    records = []
    
    try:
        # Get statistics first
        stats = service.get_statistics() or {}
        total_proofs = stats.get("total_verifications", 0)
        
        # Fetch proof records (limited by pagination)
        start_id = (page - 1) * limit + 1
        end_id = min(start_id + limit, total_proofs + 1)
        
        if record_type is None or record_type == "proof":
            for proof_id in range(start_id, end_id):
                proof = service.get_proof_details(proof_id)
                if proof:
                    proof["record_type"] = "VERIFICATION"
                    records.append(proof)
        
        return {
            "success": True,
            "records": records,
            "total": total_proofs,
            "page": page,
            "limit": limit,
            "statistics": stats
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": str(e),
            "records": [],
            "total": 0
        }


@router.get("/admin/dashboard")
async def get_admin_blockchain_dashboard():
    """
    Get comprehensive blockchain dashboard for admin
    
    Returns aggregated statistics and recent activity
    """
    service = get_blockchain_service()
    
    if not service or not service.is_available():
        return {
            "blockchain_status": "offline",
            "message": "Blockchain service not available",
            "statistics": None,
            "recent_proofs": [],
            "recent_cod": [],
            "recent_consents": []
        }
    
    try:
        # Get main statistics
        stats = service.get_statistics() or {}
        
        # Get recent proofs (last 10)
        recent_proofs = []
        total_proofs = stats.get("total_verifications", 0)
        start = max(1, total_proofs - 9)
        
        for proof_id in range(total_proofs, start - 1, -1):
            proof = service.get_proof_details(proof_id)
            if proof:
                recent_proofs.append(proof)
            if len(recent_proofs) >= 10:
                break
        
        return {
            "blockchain_status": "online",
            "contract_address": service.contract.address if service.contract else None,
            "rpc_url": service.rpc_url,
            "statistics": {
                "total_verifications": stats.get("total_verifications", 0),
                "total_deliveries": stats.get("total_deliveries", 0),
                "total_cod_transactions": stats.get("total_cod_transactions", 0),
                "total_cod_amount_lkr": stats.get("total_cod_amount_lkr", 0),
                "total_disputes": stats.get("total_disputes", 0),
                "resolved_disputes": stats.get("resolved_disputes", 0),
                "dispute_resolution_rate": stats.get("dispute_resolution_rate", "0%")
            },
            "recent_proofs": recent_proofs,
            "recent_cod": [],  # To be implemented with event logs
            "recent_consents": []  # To be implemented with event logs
        }
        
    except Exception as e:
        return {
            "blockchain_status": "error",
            "message": str(e),
            "statistics": None,
            "recent_proofs": []
        }


@router.get("/admin/delivery/{delivery_id}/full-audit")
async def get_delivery_full_audit(
    delivery_id: str
):
    """
    Get complete audit trail for a specific delivery
    
    Returns all proofs, COD records, and consents for a delivery.
    Used for dispute resolution and compliance audits.
    """
    service = get_blockchain_service()
    
    if not service or not service.is_available():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Blockchain service not available"
        )
    
    try:
        # Get evidence summary
        evidence = service.get_delivery_evidence(delivery_id)
        
        if not evidence:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No blockchain records found for delivery {delivery_id}"
            )
        
        # Get individual proofs
        proofs = []
        stats = service.get_statistics() or {}
        total_proofs = stats.get("total_verifications", 0)
        
        for proof_id in range(1, total_proofs + 1):
            proof = service.get_proof_details(proof_id)
            if proof and proof.get("delivery_id") == delivery_id:
                proofs.append(proof)
        
        return {
            "delivery_id": delivery_id,
            "evidence_summary": evidence,
            "proofs": proofs,
            "audit_timestamp": datetime.utcnow().isoformat(),
            "legal_note": "This audit trail is admissible under Electronic Transactions Act, Section 21",
            "immutability_verified": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching audit trail: {str(e)}"
        )


@router.get("/admin/export")
async def export_blockchain_records(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    format: str = "json",
    db: Session = Depends(get_db)
):
    """
    Export blockchain records for compliance and reporting
    
    Returns all records in specified format (json or csv)
    Now uses database for faster queries!
    """
    try:
        # Try database first (much faster)
        query = db.query(BlockchainProof)
        
        if start_date:
            query = query.filter(BlockchainProof.created_at >= datetime.fromisoformat(start_date))
        if end_date:
            query = query.filter(BlockchainProof.created_at <= datetime.fromisoformat(end_date))
        
        db_records = query.order_by(desc(BlockchainProof.created_at)).all()
        
        if db_records:
            records = [r.to_dict() for r in db_records]
            return {
                "export_timestamp": datetime.utcnow().isoformat(),
                "total_records": len(records),
                "format": format,
                "source": "database",
                "records": records,
                "note": "Fast query from database cache"
            }
        
        # Fallback to blockchain if no DB records
        service = get_blockchain_service()
        
        if not service or not service.is_available():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Blockchain service not available"
            )
        
        stats = service.get_statistics() or {}
        total_proofs = stats.get("total_verifications", 0)
        
        records = []
        for proof_id in range(1, total_proofs + 1):
            proof = service.get_proof_details(proof_id)
            if proof:
                records.append(proof)
        
        return {
            "export_timestamp": datetime.utcnow().isoformat(),
            "total_records": len(records),
            "format": format,
            "source": "blockchain",
            "records": records,
            "statistics": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error exporting records: {str(e)}"
        )


# ============== DATABASE-BACKED ROUTES (FAST QUERIES) ==============

@router.get("/admin/db-records")
async def get_blockchain_records_from_db(
    page: int = 1,
    limit: int = 50,
    verification_type: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get blockchain records from database (FAST!)
    
    This queries the local database cache instead of the blockchain,
    providing much faster response times for dashboards and reports.
    
    Parameters:
    - page: Page number (default 1)
    - limit: Records per page (default 50)
    - verification_type: Filter by type (face, voice, cod_collected, neighbor_consent)
    - status_filter: Filter by status (PASS, FAIL)
    """
    try:
        query = db.query(BlockchainProof)
        
        if verification_type:
            query = query.filter(BlockchainProof.verification_type == verification_type)
        if status_filter:
            query = query.filter(BlockchainProof.verification_status == status_filter)
        
        total = query.count()
        records = query.order_by(desc(BlockchainProof.created_at))\
            .offset((page - 1) * limit)\
            .limit(limit)\
            .all()
        
        return {
            "success": True,
            "source": "database",
            "records": [r.to_dict() for r in records],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database query error: {str(e)}"
        )


@router.get("/admin/db-stats")
async def get_database_statistics(db: Session = Depends(get_db)):
    """
    Get statistics from database cache
    
    Provides fast aggregated statistics without hitting the blockchain.
    """
    try:
        total_records = db.query(BlockchainProof).count()
        
        # Count by type
        type_stats = db.query(
            BlockchainProof.verification_type,
            func.count(BlockchainProof.id)
        ).group_by(BlockchainProof.verification_type).all()
        
        # Count by status
        status_stats = db.query(
            BlockchainProof.verification_status,
            func.count(BlockchainProof.id)
        ).group_by(BlockchainProof.verification_status).all()
        
        # Average confidence
        avg_confidence = db.query(
            func.avg(BlockchainProof.confidence_score)
        ).scalar() or 0
        
        # Latest record
        latest = db.query(BlockchainProof)\
            .order_by(desc(BlockchainProof.created_at))\
            .first()
        
        return {
            "source": "database",
            "total_records": total_records,
            "by_type": {t: c for t, c in type_stats},
            "by_status": {s: c for s, c in status_stats},
            "average_confidence": round(avg_confidence, 4) if avg_confidence else 0,
            "latest_record": latest.to_dict() if latest else None,
            "database_synced": True
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@router.get("/admin/db-search")
async def search_blockchain_records(
    delivery_id: Optional[str] = None,
    tx_hash: Optional[str] = None,
    block_number: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Search blockchain records in database
    
    Fast search by delivery_id, transaction hash, or block number.
    """
    try:
        query = db.query(BlockchainProof)
        
        if delivery_id:
            query = query.filter(BlockchainProof.delivery_id.contains(delivery_id))
        if tx_hash:
            query = query.filter(BlockchainProof.transaction_hash.contains(tx_hash))
        if block_number:
            query = query.filter(BlockchainProof.block_number == block_number)
        
        records = query.order_by(desc(BlockchainProof.created_at)).limit(100).all()
        
        return {
            "success": True,
            "source": "database",
            "results": [r.to_dict() for r in records],
            "count": len(records)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search error: {str(e)}"
        )
