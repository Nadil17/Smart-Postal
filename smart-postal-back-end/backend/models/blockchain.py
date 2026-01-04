"""
Blockchain Proofs Database Model

This model caches blockchain proof records in the database for faster queries.
The source of truth remains the smart contract, but this provides:
- Faster queries without hitting the blockchain
- Full-text search capabilities
- Complex filtering and reporting
- Reduced RPC calls to the blockchain node
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, Index
from sqlalchemy.sql import func
from models.database import Base


class BlockchainProof(Base):
    """
    Database cache for blockchain delivery proofs.
    
    This table mirrors data recorded on the DeliveryProofRegistry smart contract
    for faster database queries while maintaining blockchain as the authoritative source.
    """
    __tablename__ = "blockchain_proofs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Blockchain identifiers
    delivery_id = Column(String(100), unique=True, index=True, nullable=False)
    transaction_hash = Column(String(66), unique=True, index=True, nullable=False)  # 0x + 64 hex chars
    block_number = Column(Integer, index=True, nullable=False)
    block_timestamp = Column(DateTime, index=True, nullable=False)
    
    # Cryptographic data
    proof_hash = Column(String(66), nullable=False)  # SHA3-256 hash
    
    # Verification details
    verification_type = Column(String(50), nullable=False)  # face, voice, fingerprint, cod, neighbor_consent
    verification_status = Column(String(20), nullable=False)  # PASS, FAIL
    confidence_score = Column(Float, nullable=True)
    ai_model_used = Column(String(100), nullable=True)
    
    # Anti-spoofing results
    liveness_passed = Column(Boolean, default=True)
    ai_detection_score = Column(Float, nullable=True)
    
    # Actor information (hashed for privacy)
    recipient_hash = Column(String(66), nullable=True)  # Hashed recipient identifier
    courier_hash = Column(String(66), nullable=True)  # Hashed courier identifier
    
    # Metadata
    gas_used = Column(Integer, nullable=True)
    gas_price = Column(String(50), nullable=True)  # In wei
    
    # Audit timestamps
    created_at = Column(DateTime, server_default=func.now(), index=True)
    synced_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Indexes for common queries
    __table_args__ = (
        Index('ix_blockchain_proofs_type_status', 'verification_type', 'verification_status'),
        Index('ix_blockchain_proofs_created_range', 'created_at', 'verification_type'),
    )
    
    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "delivery_id": self.delivery_id,
            "transaction_hash": self.transaction_hash,
            "block_number": self.block_number,
            "block_timestamp": self.block_timestamp.isoformat() if self.block_timestamp else None,
            "proof_hash": self.proof_hash,
            "verification_type": self.verification_type,
            "verification_status": self.verification_status,
            "confidence_score": self.confidence_score,
            "ai_model_used": self.ai_model_used,
            "liveness_passed": self.liveness_passed,
            "ai_detection_score": self.ai_detection_score,
            "recipient_hash": self.recipient_hash,
            "courier_hash": self.courier_hash,
            "gas_used": self.gas_used,
            "gas_price": self.gas_price,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "synced_at": self.synced_at.isoformat() if self.synced_at else None,
        }


class BlockchainSyncStatus(Base):
    """
    Tracks synchronization status between database and blockchain.
    
    Used to detect if database cache is out of sync and needs refresh.
    """
    __tablename__ = "blockchain_sync_status"
    
    id = Column(Integer, primary_key=True)
    last_synced_block = Column(Integer, default=0)
    last_sync_time = Column(DateTime, server_default=func.now())
    sync_status = Column(String(20), default="idle")  # idle, syncing, error
    error_message = Column(Text, nullable=True)
    total_records_synced = Column(Integer, default=0)
