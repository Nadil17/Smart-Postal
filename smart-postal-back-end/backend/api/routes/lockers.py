# smart-postal-back-end/backend/api/routes/lockers.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Tuple, Optional
from utils.recommender import engine  # Import the engine instance
import random
import string

router = APIRouter()

# In-memory storage for reservations (use database in production)
locker_reservations = {}
unlock_codes = {}

class RecommendationRequest(BaseModel):
    latitude: float
    longitude: float
    courier_route: List[Tuple[float, float]]  # List of [lat, lon] points
    package_size: Optional[str] = "medium"

class ReserveRequest(BaseModel):
    order_id: int
    slot_size: str

class UnlockRequest(BaseModel):
    verification_code: str

@router.post("/recommend")
async def get_locker_recommendation(request: RecommendationRequest):
    """
    Returns Top 3 Smart Lockers based on AI Prediction + Route Optimization
    """
    try:
        route_formatted = [(p[1], p[0]) for p in request.courier_route]
        
        results = engine.get_recommendations(
            request.latitude, 
            request.longitude, 
            route_formatted
        )
        
        return {"success": True, "recommendations": results}
    
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.get("/")
async def get_all_lockers():
    """
    Returns all available lockers in Colombo
    """
    try:
        lockers = []
        for _, locker in engine.lockers.iterrows():
            lockers.append({
                "id": locker['id'],
                "name": locker['name'],
                "latitude": locker['lat'],
                "longitude": locker['lon'],
                "address": locker['address'],
                "small_available": random.randint(3, 8),
                "medium_available": random.randint(5, 12),
                "large_available": random.randint(2, 5),
                "total_slots": 25,
                "operating_hours": "24/7",
                "is_active": True
            })
        return lockers
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{locker_id}")
async def get_locker_by_id(locker_id: str):
    """
    Returns a specific locker by ID
    """
    try:
        locker_row = engine.lockers[engine.lockers['id'] == locker_id]
        if locker_row.empty:
            raise HTTPException(status_code=404, detail="Locker not found")
        
        locker = locker_row.iloc[0]
        return {
            "id": locker['id'],
            "name": locker['name'],
            "latitude": locker['lat'],
            "longitude": locker['lon'],
            "address": locker['address'],
            "small_available": random.randint(3, 8),
            "medium_available": random.randint(5, 12),
            "large_available": random.randint(2, 5),
            "total_slots": 25,
            "operating_hours": "24/7",
            "is_active": True
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{locker_id}/availability")
async def get_locker_availability(locker_id: str):
    """
    Returns availability status for a specific locker
    """
    try:
        locker_row = engine.lockers[engine.lockers['id'] == locker_id]
        if locker_row.empty:
            raise HTTPException(status_code=404, detail="Locker not found")
        
        return {
            "locker_id": locker_id,
            "small_available": random.randint(3, 8),
            "medium_available": random.randint(5, 12),
            "large_available": random.randint(2, 5),
            "last_updated": "2026-01-03T10:00:00Z"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{locker_id}/reserve")
async def reserve_locker_slot(locker_id: str, request: ReserveRequest):
    """
    Reserve a locker slot for an order
    """
    try:
        locker_row = engine.lockers[engine.lockers['id'] == locker_id]
        if locker_row.empty:
            raise HTTPException(status_code=404, detail="Locker not found")
        
        # Generate unlock code
        unlock_code = ''.join(random.choices(string.digits, k=6))
        
        # Store reservation
        reservation_key = f"{locker_id}_{request.order_id}"
        locker_reservations[reservation_key] = {
            "locker_id": locker_id,
            "order_id": request.order_id,
            "slot_size": request.slot_size,
            "unlock_code": unlock_code,
            "status": "reserved"
        }
        unlock_codes[reservation_key] = unlock_code
        
        return {
            "success": True,
            "reservation_id": reservation_key,
            "locker_id": locker_id,
            "order_id": request.order_id,
            "slot_size": request.slot_size,
            "unlock_code": unlock_code,
            "message": f"Slot reserved successfully. Unlock code: {unlock_code}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{locker_id}/unlock")
async def unlock_locker(locker_id: str, request: UnlockRequest):
    """
    Unlock a locker with verification code
    """
    try:
        # Find reservation with this locker and code
        valid_unlock = False
        for key, code in unlock_codes.items():
            if key.startswith(locker_id) and code == request.verification_code:
                valid_unlock = True
                # Update reservation status
                if key in locker_reservations:
                    locker_reservations[key]["status"] = "unlocked"
                break
        
        if not valid_unlock:
            # For demo purposes, accept any 6-digit code
            if len(request.verification_code) == 6 and request.verification_code.isdigit():
                valid_unlock = True
        
        if valid_unlock:
            return {
                "success": True,
                "locker_id": locker_id,
                "message": "Locker unlocked successfully",
                "status": "unlocked"
            }
        else:
            raise HTTPException(status_code=400, detail="Invalid verification code")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))