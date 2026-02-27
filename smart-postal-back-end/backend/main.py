"""
main.py  –  Smart Postal Route Optimization – FastAPI Backend
────────────────────────────────────────────────────────────
Run:
    pip install -r requirements.txt
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uuid
import json

from ml_models import PriorityClassifier, RouteOptimizer, DynamicRerouter, TRAFFIC_FACTORS, WEATHER_FACTORS
import database as db

# ─── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(title="Smart Postal Route API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # allow Expo / React Native dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Shared ML singletons ─────────────────────────────────────────────────────
classifier = PriorityClassifier()
optimizer  = RouteOptimizer()
rerouter   = DynamicRerouter(optimizer)


# ─── Request / Response schemas ───────────────────────────────────────────────

class DeliveryItem(BaseModel):
    address: str
    latitude: float
    longitude: float
    mail_type: str = "Regular Letter"
    priority: str = "regular"
    sender_type: str = "Individual"
    recipient_type: str = "Individual"
    parcels: int = 1
    urgent: int = 0

class ClassifyRequest(BaseModel):
    mail_type: str
    sender_type: str = "Individual"
    recipient_type: str = "Individual"
    time_received: str = ""
    day_of_week: str = ""

class OptimizeRequest(BaseModel):
    zone_id: int = 1
    deliveries: List[DeliveryItem]
    methods: List[str] = ["nearest_neighbor", "urgent_priority", "2opt", "q_learning"]
    weather_condition: str = "clear"
    traffic_level: str = "moderate"
    session_id: Optional[str] = None

class ChangeConditionsRequest(BaseModel):
    zone_id: int = 1
    deliveries: List[DeliveryItem]
    original_traffic: str
    original_weather: str
    new_traffic: str
    new_weather: str
    optimization_method: str = "q_learning"
    session_id: Optional[str] = None

class SaveDeliveriesRequest(BaseModel):
    session_id: str
    deliveries: List[DeliveryItem]


# ─── Health check ─────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "service": "Smart Postal Route API"}

@app.get("/health")
def health():
    return {"status": "healthy"}


# ─── MODEL 1: Priority Classification ─────────────────────────────────────────

@app.post("/api/ml/classify-priority")
def classify_priority(req: ClassifyRequest):
    result = classifier.classify(
        req.mail_type, req.sender_type,
        req.recipient_type, req.time_received, req.day_of_week
    )
    return result


@app.post("/api/ml/classify-bulk")
def classify_bulk(items: List[ClassifyRequest]):
    return [
        classifier.classify(
            it.mail_type, it.sender_type,
            it.recipient_type, it.time_received, it.day_of_week
        )
        for it in items
    ]


# ─── MODEL 2A: Route Optimization ─────────────────────────────────────────────

@app.post("/api/ml/optimize-route")
def optimize_route(req: OptimizeRequest):
    if not req.deliveries:
        raise HTTPException(400, "No deliveries provided")

    scenario = {
        "delivery_points": [
            {
                "id": i,
                "address": d.address,
                "latitude": d.latitude,
                "longitude": d.longitude,
                "mail_type": d.mail_type,
                "priority": d.priority,
                "urgent": d.urgent or (1 if d.priority == "urgent" else 0),
                "parcels": d.parcels,
            }
            for i, d in enumerate(req.deliveries)
        ],
        "traffic_factor": TRAFFIC_FACTORS.get(req.traffic_level, 1.3),
        "weather_factor": WEATHER_FACTORS.get(req.weather_condition, 1.0),
        "traffic_level": req.traffic_level,
        "weather_condition": req.weather_condition,
    }

    result = optimizer.optimize_all(scenario)

    # Persist to DB
    sid = req.session_id or str(uuid.uuid4())
    result["session_id"] = sid
    try:
        db.save_route_session(sid, result)
    except Exception as e:
        print(f"[DB WARN] save_route_session: {e}")

    return result


# ─── MODEL 2B: Real-time Condition Change & Rerouting ─────────────────────────

@app.post("/api/ml/change-conditions-realtime")
def change_conditions(req: ChangeConditionsRequest):
    if not req.deliveries:
        raise HTTPException(400, "No deliveries provided")

    deliveries = [d.dict() for d in req.deliveries]
    result = rerouter.change_conditions(
        deliveries,
        req.original_traffic, req.original_weather,
        req.new_traffic, req.new_weather,
    )

    # Persist rerouting event
    sid = req.session_id or str(uuid.uuid4())
    result["session_id"] = sid
    try:
        db.save_rerouting_event(sid, result)
    except Exception as e:
        print(f"[DB WARN] save_rerouting_event: {e}")

    return result


# ─── Deliveries CRUD ──────────────────────────────────────────────────────────

@app.post("/api/deliveries/save")
def save_deliveries(req: SaveDeliveriesRequest):
    """Save a batch of deliveries to the DB (called after CSV upload)."""
    deliveries = [d.dict() for d in req.deliveries]
    try:
        db.save_deliveries(req.session_id, deliveries)
        return {"status": "saved", "count": len(deliveries), "session_id": req.session_id}
    except Exception as e:
        raise HTTPException(500, f"DB error: {e}")


@app.get("/api/deliveries/{session_id}")
def get_deliveries(session_id: str):
    try:
        rows = db.get_deliveries(session_id)
        return {"deliveries": rows, "count": len(rows)}
    except Exception as e:
        raise HTTPException(500, f"DB error: {e}")


@app.post("/api/session/new")
def new_session():
    """Generate a fresh session ID."""
    return {"session_id": str(uuid.uuid4())}


# ─── Relocation endpoint ──────────────────────────────────────────────────────

class RelocationRequest(BaseModel):
    session_id: str
    delivery_id: int
    old_address: str
    new_address: str
    old_latitude: float
    old_longitude: float
    new_latitude: float
    new_longitude: float
    distance_change_km: float
    before_route: dict = {}
    after_route: dict = {}

@app.post("/api/relocations/save")
def save_relocation(req: RelocationRequest):
    try:
        db.save_relocation(req.session_id, req.dict())
        return {"status": "saved"}
    except Exception as e:
        raise HTTPException(500, f"DB error: {e}")
