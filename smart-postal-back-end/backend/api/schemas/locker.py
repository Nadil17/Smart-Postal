"""
Locker API Schemas
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Tuple
from datetime import datetime
from enum import Enum


class SlotSizeEnum(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class SlotStatusEnum(str, Enum):
    AVAILABLE = "available"
    RESERVED = "reserved"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"


# ============== Station Schemas ==============

class LockerStationBase(BaseModel):
    name: str
    address: str
    city: str = "Colombo"
    latitude: float
    longitude: float
    operating_hours: str = "24/7"
    is_active: bool = True
    contact_phone: Optional[str] = None


class LockerStationCreate(LockerStationBase):
    id: str  # L01, L02, etc.
    small_total: int = 0
    medium_total: int = 0
    large_total: int = 0


class LockerStationUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    operating_hours: Optional[str] = None
    is_active: Optional[bool] = None
    contact_phone: Optional[str] = None


class LockerStationResponse(LockerStationBase):
    id: str
    total_slots: int
    small_total: int
    medium_total: int
    large_total: int
    small_available: int
    medium_available: int
    large_available: int
    total_available: int
    occupancy_rate: float
    created_at: datetime
    
    class Config:
        from_attributes = True


class LockerStationSummary(BaseModel):
    """Lightweight station info for listings"""
    id: str
    name: str
    address: str
    latitude: float
    longitude: float
    total_available: int
    occupancy_rate: float
    is_active: bool


# ============== Slot Schemas ==============

class LockerSlotBase(BaseModel):
    size: SlotSizeEnum
    row: int
    column: int


class LockerSlotCreate(LockerSlotBase):
    id: str  # L01-S-001
    station_id: str


class LockerSlotResponse(BaseModel):
    id: str
    station_id: str
    size: SlotSizeEnum
    status: SlotStatusEnum
    row: int
    column: int
    order_id: Optional[int]
    reserved_at: Optional[datetime]
    expires_at: Optional[datetime]
    package_deposited_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class SlotGridItem(BaseModel):
    """For visual grid display"""
    id: str
    size: str
    status: str
    row: int
    column: int


# ============== Recommendation Schemas ==============

class RecommendationRequest(BaseModel):
    latitude: float = Field(..., description="Customer latitude")
    longitude: float = Field(..., description="Customer longitude")
    courier_route: List[Tuple[float, float]] = Field(..., description="Courier route points")
    package_size: Optional[SlotSizeEnum] = SlotSizeEnum.MEDIUM
    

class LockerRecommendation(BaseModel):
    id: str
    name: str
    address: str
    latitude: float
    longitude: float
    distance_km: float
    route_deviation_km: float
    ai_score: float
    availability: dict  # {small: int, medium: int, large: int}
    predicted_availability: int  # AI predicted slots in 1 hour
    rank: int


class RecommendationResponse(BaseModel):
    success: bool
    customer_location: dict
    recommendations: List[LockerRecommendation]
    processing_time_ms: int
    ai_model: str = "ST-GNN v1.0"


# ============== Reservation Schemas ==============

class ReserveSlotRequest(BaseModel):
    order_id: int
    slot_size: SlotSizeEnum = SlotSizeEnum.MEDIUM
    customer_id: Optional[int] = None


class ReserveSlotResponse(BaseModel):
    success: bool
    station_id: str
    station_name: str
    slot_id: str
    slot_size: str
    row: int
    column: int
    customer_unlock_code: str
    courier_unlock_code: str
    reserved_at: datetime
    expires_at: datetime
    message: str


class UnlockRequest(BaseModel):
    code: str = Field(..., min_length=6, max_length=6)
    actor: str = "customer"  # customer or courier


class UnlockResponse(BaseModel):
    success: bool
    slot_id: str
    action: str  # opened_for_deposit, opened_for_collection
    message: str


# ============== Admin Schemas ==============

class NetworkOverview(BaseModel):
    """Admin dashboard overview"""
    total_stations: int
    total_slots: int
    total_available: int
    total_occupied: int
    total_reserved: int
    total_maintenance: int
    network_occupancy_rate: float
    stations: List[LockerStationSummary]


class StationDetailedView(BaseModel):
    """Detailed station view for admin"""
    station: LockerStationResponse
    slots: List[LockerSlotResponse]
    slot_grid: List[List[SlotGridItem]]
    recent_transactions: List[dict]