from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

# Face Enrollment (ID Card Upload)
class FaceIDUploadRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class FaceIDUploadResponse(BaseModel):
    success: bool
    message: str
    user_id: Optional[int] = None
    face_id: Optional[int] = None
    quality_score: Optional[float] = None
    liveness_passed: Optional[bool] = None

# Face Verification
class FaceVerificationRequest(BaseModel):
    user_id: int
    order_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None

# Courier Decision Model for actionable guidance
class CourierDecision(BaseModel):
    action: str  # DELIVER, VERIFY_ID, MANUAL_CHECK, REJECT
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    color: str  # green, yellow, orange, red
    icon: str  # Emoji icon for UI
    message: str  # Human-readable guidance
    similarity_percentage: float
    models_agreed: str  # e.g., "2/3"
    quality_gap: float
    nic_quality_issue: bool
    additional_steps: Optional[List[str]] = None
    quality_note: Optional[str] = None

class FaceVerificationResponse(BaseModel):
    success: bool
    verified: bool
    confidence: float
    similarity_score: float
    threshold: float
    message: str
    quality_score: Optional[float] = None
    liveness_passed: Optional[bool] = None
    metrics: Optional[Dict[str, Any]] = None  # Allow strings and numbers
    courier_decision: Optional[CourierDecision] = None  # NEW: Actionable courier guidance

# Locker Face Verification
class LockerVerificationRequest(BaseModel):
    locker_id: str
    user_id: int
    parcel_id: Optional[str] = None

class LockerVerificationResponse(BaseModel):
    success: bool
    unlock: bool
    token: Optional[str] = None
    message: str
    confidence: float
    expires_in: Optional[int] = None  # Token expiry in seconds

# Locker Unlock
class LockerUnlockRequest(BaseModel):
    token: str
    locker_id: str

class LockerUnlockResponse(BaseModel):
    success: bool
    status: str
    message: str
    locker_id: str
    unlocked_at: Optional[datetime] = None

# Face Template Info
class FaceTemplateResponse(BaseModel):
    id: int
    user_id: int
    enrollment_type: Optional[str]
    quality_score: Optional[float]
    confidence_score: Optional[float]
    liveness_score: Optional[float]
    anti_spoof_passed: bool
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
