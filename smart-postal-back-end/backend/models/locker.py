"""
Smart Locker Database Models
============================
Each station has 50-100 individual locker slots with unique IDs
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from models.database import Base


class SlotSize(str, enum.Enum):
    SMALL = "small"      # 30x30x45 cm - Documents, small packages
    MEDIUM = "medium"    # 45x45x60 cm - Standard parcels
    LARGE = "large"      # 60x60x90 cm - Large boxes


class SlotStatus(str, enum.Enum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"


class LockerStation(Base):
    """
    Locker Station - Physical location with multiple slots
    Example: "Smart Locker - Fort Railway Station" with 75 slots
    """
    __tablename__ = "locker_stations"

    id = Column(String(10), primary_key=True)  # L01, L02, etc.
    name = Column(String(100), nullable=False)
    address = Column(String(255), nullable=False)
    city = Column(String(50), default="Colombo")
    
    # GPS Coordinates
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Operating Info
    operating_hours = Column(String(50), default="24/7")
    is_active = Column(Boolean, default=True)
    
    # Contact
    contact_phone = Column(String(20), nullable=True)
    
    # Capacity Summary (denormalized for fast queries)
    total_slots = Column(Integer, default=0)
    small_total = Column(Integer, default=0)
    medium_total = Column(Integer, default=0)
    large_total = Column(Integer, default=0)
    
    # Real-time availability (updated by triggers/app)
    small_available = Column(Integer, default=0)
    medium_available = Column(Integer, default=0)
    large_available = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    slots = relationship("LockerSlot", back_populates="station", cascade="all, delete-orphan")
    
    @property
    def total_available(self):
        return self.small_available + self.medium_available + self.large_available
    
    @property
    def occupancy_rate(self):
        if self.total_slots == 0:
            return 0
        return ((self.total_slots - self.total_available) / self.total_slots) * 100


class LockerSlot(Base):
    """
    Individual Locker Slot with unique ID
    Example: "L01-S-001" (Station L01, Small, Slot 001)
    """
    __tablename__ = "locker_slots"

    id = Column(String(20), primary_key=True)  # L01-S-001, L01-M-015, etc.
    station_id = Column(String(10), ForeignKey("locker_stations.id"), nullable=False)
    
    # Slot Properties
    size = Column(Enum(SlotSize), nullable=False)
    status = Column(Enum(SlotStatus), default=SlotStatus.AVAILABLE)
    
    # Physical Location within station
    row = Column(Integer, nullable=False)      # Row number (1-10)
    column = Column(Integer, nullable=False)   # Column number (1-10)
    
    # Current Reservation
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    reserved_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    reserved_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    
    # Access Codes
    unlock_code = Column(String(10), nullable=True)  # 6-digit code
    courier_code = Column(String(10), nullable=True)  # Separate code for courier
    
    # Package Info (when occupied)
    package_deposited_at = Column(DateTime, nullable=True)
    package_collected_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    station = relationship("LockerStation", back_populates="slots")
    order = relationship("Order", backref="locker_slot")
    
    def generate_codes(self):
        """Generate random access codes"""
        import random
        import string
        self.unlock_code = ''.join(random.choices(string.digits, k=6))
        self.courier_code = ''.join(random.choices(string.digits, k=6))
        return self.unlock_code, self.courier_code


class LockerTransaction(Base):
    """
    Track all locker activities for audit and analytics
    """
    __tablename__ = "locker_transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slot_id = Column(String(20), ForeignKey("locker_slots.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=True)
    
    # Transaction Type
    action = Column(String(50), nullable=False)  # reserved, deposited, collected, expired, cancelled
    
    # Actor
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    performer_role = Column(String(20), nullable=True)  # customer, courier, admin, system
    
    # Details
    details = Column(Text, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    slot = relationship("LockerSlot")