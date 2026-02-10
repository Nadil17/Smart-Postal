from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, LargeBinary, Float, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class VoiceTemplate(Base):
    __tablename__ = "voice_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Voice data (encrypted embeddings)
    embedding_data = Column(LargeBinary, nullable=False)  # Encrypted voice embedding
    sample_count = Column(Integer, default=0)
    
    # Metadata
    audio_quality_score = Column(Float, nullable=True)
    sample_duration_avg = Column(Float, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="voice_templates")

class FingerprintTemplate(Base):
    __tablename__ = "fingerprint_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Fingerprint data (encrypted template)
    template_data = Column(LargeBinary, nullable=False)  # Encrypted fingerprint template
    device_id = Column(String(100), nullable=True)  # Device used for enrollment
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="fingerprint_templates")

class FaceTemplate(Base):
    __tablename__ = "face_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Face data (encrypted embeddings)
    embedding_data = Column(LargeBinary, nullable=False)  # Encrypted 512-dim face embedding
    id_card_info = Column(Text, nullable=True)  # Encrypted ID card metadata
    
    # Quality metrics
    face_quality_score = Column(Float, nullable=True)  # Face quality (0-1)
    confidence_score = Column(Float, nullable=True)  # Detection confidence
    
    # Anti-spoofing
    liveness_score = Column(Float, nullable=True)  # Liveness detection score
    anti_spoof_passed = Column(Boolean, default=True)
    
    # Metadata
    enrollment_type = Column(String(50), nullable=True)  # 'id_card', 'live_capture', 'locker'
    device_id = Column(String(100), nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="face_templates")

class VerificationLog(Base):
    __tablename__ = "verification_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    
    # Verification details
    verification_type = Column(String(50), nullable=False)  # 'voice' or 'fingerprint'
    success = Column(Boolean, nullable=False)
    confidence_score = Column(Float, nullable=True)
    ai_detection_score = Column(Float, nullable=True)  # For voice: AI-generated detection
    ai_detected = Column(Boolean, default=False)
    
    # Additional info
    ip_address = Column(String(50), nullable=True)
    device_info = Column(Text, nullable=True)
    failure_reason = Column(String(255), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="verification_logs")

class Delivery(Base):
    __tablename__ = "deliveries"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    
    # Verification status
    voice_verified = Column(Boolean, default=False)
    fingerprint_verified = Column(Boolean, default=False)
    verification_passed = Column(Boolean, default=False)
    
    # Delivery details
    attempted_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    
    # Location
    delivery_latitude = Column(Float, nullable=True)
    delivery_longitude = Column(Float, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    order = relationship("Order", back_populates="deliveries")