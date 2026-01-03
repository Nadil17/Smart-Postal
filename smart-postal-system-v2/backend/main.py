from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import mysql.connector
from datetime import datetime, timedelta
import json
import os
import requests
from functools import lru_cache

# Import ML models
from postal_ml_webapp import (
    PriorityClassificationModel,
    DynamicRouteOptimizer,
    DynamicRerouter,
    RelocationTracker
)

app = FastAPI(title="Postal Route Optimization API with ML")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Keys - Store these in environment variables in production
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "AIzaSyB_996Uyid5qMajR-4PJY0EcpO6Prp_n4c")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "82307d7563dc58a7c929ee6441cfc1ea")

# Initialize ML models
priority_classifier = PriorityClassificationModel()
route_optimizer = DynamicRouteOptimizer()
dynamic_rerouter = DynamicRerouter(route_optimizer)
relocation_tracker = RelocationTracker()

# Try to load pre-trained model
MODEL_PATH = "priority_classifier_model.pkl"
if os.path.exists(MODEL_PATH):
    try:
        priority_classifier.load_model(MODEL_PATH)
        print("✓ Loaded pre-trained priority classification model")
    except Exception as e:
        print(f"⚠ Could not load model: {e}")

# Database connection
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="postal_optimizations"
    )

# Pydantic Models
class DeliveryInput(BaseModel):
    address: str
    latitude: float
    longitude: float
    mail_type: str
    priority: Optional[str] = None
    parcels: Optional[int] = 1
    urgent: Optional[int] = 0
    time_window: Optional[float] = None

class RouteOptimizationRequest(BaseModel):
    zone_id: int
    deliveries: List[DeliveryInput]
    methods: Optional[List[str]] = None
    traffic_level: Optional[str] = None
    weather_condition: Optional[str] = None

class PriorityClassificationInput(BaseModel):
    mail_type: str
    sender_type: str
    recipient_type: str
    time_received: str
    day_of_week: str

class TrainingDataInput(BaseModel):
    training_data: List[Dict]
    labels: List[str]

class RelocationInput(BaseModel):
    location_id: int
    old_latitude: float
    old_longitude: float
    new_latitude: float
    new_longitude: float
    reason: Optional[str] = "customer_request"

class ReroutingRequest(BaseModel):
    scenario: Dict
    relocations: List[Dict]
    method: Optional[str] = "q_learning"

# Real-time Data Fetching Functions
@lru_cache(maxsize=100)
def get_weather_data(latitude: float, longitude: float) -> Dict:
    """Fetch real-time weather data from OpenWeatherMap API"""
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather"
        params = {
            "lat": latitude,
            "lon": longitude,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric"
        }
        
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # Extract weather conditions
        weather_main = data['weather'][0]['main'].lower()
        rain_volume = data.get('rain', {}).get('1h', 0)
        
        # Determine weather condition
        if 'rain' in weather_main or 'drizzle' in weather_main:
            if rain_volume > 7.5:
                condition = 'flooding'
            elif rain_volume > 2.5:
                condition = 'heavy_rain'
            else:
                condition = 'light_rain'
        elif 'thunderstorm' in weather_main:
            condition = 'flooding'
        else:
            condition = 'clear'
        
        return {
            "condition": condition,
            "temperature": data['main']['temp'],
            "humidity": data['main']['humidity'],
            "description": data['weather'][0]['description'],
            "rain_volume": rain_volume
        }
    except Exception as e:
        print(f"Weather API error: {e}")
        # Return default weather
        return {
            "condition": "clear",
            "temperature": 28,
            "humidity": 70,
            "description": "clear sky",
            "rain_volume": 0
        }

def get_traffic_data(latitude: float, longitude: float) -> Dict:
    """Fetch real-time traffic data from Google Maps API"""
    try:
        # Use Google Maps Distance Matrix API to estimate traffic
        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        
        # Create a small radius to check local traffic
        offset = 0.01  # approximately 1km
        origin = f"{latitude},{longitude}"
        destination = f"{latitude + offset},{longitude + offset}"
        
        params = {
            "origins": origin,
            "destinations": destination,
            "departure_time": "now",
            "traffic_model": "best_guess",
            "key": GOOGLE_MAPS_API_KEY
        }
        
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] == 'OK':
            element = data['rows'][0]['elements'][0]
            
            if element['status'] == 'OK':
                # Compare duration vs duration_in_traffic
                normal_duration = element.get('duration', {}).get('value', 0)
                traffic_duration = element.get('duration_in_traffic', {}).get('value', normal_duration)
                
                if traffic_duration > 0 and normal_duration > 0:
                    traffic_ratio = traffic_duration / normal_duration
                    
                    # Determine traffic level based on ratio
                    if traffic_ratio >= 1.5:
                        level = 'severe'
                    elif traffic_ratio >= 1.25:
                        level = 'high'
                    elif traffic_ratio >= 1.1:
                        level = 'moderate'
                    else:
                        level = 'low'
                    
                    return {
                        "level": level,
                        "ratio": round(traffic_ratio, 2),
                        "normal_duration": normal_duration,
                        "traffic_duration": traffic_duration
                    }
        
        # Default if API fails
        return {"level": "moderate", "ratio": 1.0}
        
    except Exception as e:
        print(f"Traffic API error: {e}")
        # Return default traffic
        return {"level": "moderate", "ratio": 1.0}

# Helper Functions
def get_traffic_factor(level: str) -> float:
    """Convert traffic level to factor"""
    factors = {
        'low': 0.9,
        'moderate': 1.0,
        'high': 1.3,
        'severe': 1.6
    }
    return factors.get(level, 1.0)

def get_weather_factor(condition: str) -> float:
    """Convert weather condition to factor"""
    factors = {
        'clear': 1.0,
        'light_rain': 1.1,
        'heavy_rain': 1.3,
        'flooding': 1.8
    }
    return factors.get(condition, 1.0)

def format_route_for_map(route_sequence, deliveries):
    """Format route for frontend map display"""
    return [deliveries[i] for i in route_sequence if i < len(deliveries)]

# API Endpoints
@app.get("/")
def read_root():
    return {
        "message": "Postal Route Optimization API with ML",
        "status": "running",
        "ml_models": {
            "priority_classifier": priority_classifier.is_trained,
            "route_optimizer": "loaded",
            "dynamic_rerouter": "loaded"
        },
        "apis_configured": {
            "google_maps": bool(GOOGLE_MAPS_API_KEY and GOOGLE_MAPS_API_KEY != "AIzaSyB_996Uyid5qMajR-4PJY0EcpO6Prp_n4c"),
            "openweather": bool(OPENWEATHER_API_KEY and OPENWEATHER_API_KEY != "82307d7563dc58a7c929ee6441cfc1ea")
        }
    }

@app.get("/api/postal-zones")
def get_postal_zones():
    """Get all postal zones"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM postal_zones")
        zones = cursor.fetchall()
        
        for zone in zones:
            zone['boundary_coordinates'] = json.loads(zone['boundary_coordinates'])
        
        cursor.close()
        conn.close()
        
        return {"zones": zones}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conditions/{zone_id}")
def get_zone_conditions(zone_id: int):
    """Get real-time traffic and weather conditions for a zone"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM postal_zones WHERE zone_id = %s", (zone_id,))
        zone = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not zone:
            raise HTTPException(status_code=404, detail="Zone not found")
        
        # Get center coordinates of the zone
        boundary = json.loads(zone['boundary_coordinates'])
        center_lat = sum(coord['lat'] for coord in boundary) / len(boundary)
        center_lng = sum(coord['lng'] for coord in boundary) / len(boundary)
        
        # Fetch real-time data
        weather_data = get_weather_data(center_lat, center_lng)
        traffic_data = get_traffic_data(center_lat, center_lng)
        
        return {
            "zone_id": zone_id,
            "zone_name": zone['name'],
            "weather": weather_data,
            "traffic": traffic_data,
            "timestamp": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/deliveries/{zone_id}")
def get_deliveries(zone_id: int):
    """Get all deliveries for a specific zone"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT delivery_id, address, latitude, longitude, 
                   mail_type, priority, deadline, zone_id
            FROM deliveries
            WHERE zone_id = %s
        """, (zone_id,))
        
        deliveries = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return {"deliveries": deliveries, "count": len(deliveries)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ml/classify-priority")
def classify_priority_ml(mail_data: PriorityClassificationInput):
    """Classify mail priority using XGBoost ML model"""
    try:
        if not priority_classifier.is_trained:
            # Fallback to rule-based
            urgent_types = ['Court Notice', 'Legal Document', 'Registered Letter', 
                          'Speed Post', 'Express Mail', 'Tax Document']
            priority = 'urgent' if mail_data.mail_type in urgent_types else 'regular'
            return {
                'priority': priority,
                'confidence': 0.85,
                'probability_regular': 0.15 if priority == 'urgent' else 0.85,
                'probability_urgent': 0.85 if priority == 'urgent' else 0.15,
                'method': 'rule_based'
            }
        
        result = priority_classifier.predict(mail_data.dict())
        result['method'] = 'ml_xgboost'
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ml/train-classifier")
def train_priority_classifier(data: TrainingDataInput):
    """Train the priority classification model"""
    try:
        result = priority_classifier.train(data.training_data, data.labels)
        
        # Save trained model
        priority_classifier.save_model(MODEL_PATH)
        
        return {
            "status": "success",
            "message": "Model trained and saved successfully",
            "model_path": MODEL_PATH
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ml/optimize-route")
def optimize_route_ml(request: RouteOptimizationRequest):
    """Optimize route using ML algorithms with real-time conditions"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get zone information
        cursor.execute("SELECT * FROM postal_zones WHERE zone_id = %s", (request.zone_id,))
        zone = cursor.fetchone()
        
        if not zone:
            raise HTTPException(status_code=404, detail="Zone not found")
        
        # Get real-time conditions
        boundary = json.loads(zone['boundary_coordinates'])
        center_lat = sum(coord['lat'] for coord in boundary) / len(boundary)
        center_lng = sum(coord['lng'] for coord in boundary) / len(boundary)
        
        weather_data = get_weather_data(center_lat, center_lng)
        traffic_data = get_traffic_data(center_lat, center_lng)
        
        traffic_level = request.traffic_level or traffic_data['level']
        weather_condition = request.weather_condition or weather_data['condition']
        
        # Prepare delivery points for ML model
        delivery_points = [
            {
                'id': 0,
                'address': 'Postal Depot',
                'latitude': center_lat,
                'longitude': center_lng,
                'parcels': 0,
                'urgent': 0
            }
        ]
        
        for idx, delivery in enumerate(request.deliveries, start=1):
            point = {
                'id': idx,
                'address': delivery.address,
                'latitude': delivery.latitude,
                'longitude': delivery.longitude,
                'parcels': delivery.parcels or 1,
                'urgent': delivery.urgent or (1 if delivery.priority == 'urgent' else 0),
                'time_window': delivery.time_window or (4.0 if delivery.priority == 'urgent' else 8.0)
            }
            delivery_points.append(point)
        
        # Create scenario
        scenario = {
            'delivery_points': delivery_points,
            'traffic_factor': get_traffic_factor(traffic_level),
            'weather_factor': get_weather_factor(weather_condition),
            'traffic_level': traffic_level,
            'weather_condition': weather_condition
        }
        
        # Optimize using multiple methods
        methods = request.methods or ['nearest_neighbor', 'urgent_priority', '2opt', 'q_learning']
        optimization_result = route_optimizer.optimize_route(scenario, methods)
        
        # Format results for frontend
        formatted_results = {}
        for method, result in optimization_result['results'].items():
            formatted_results[method] = {
                'route_sequence': result['route'],
                'deliveries': format_route_for_map(result['route'], delivery_points),
                'total_distance_km': result['total_distance_km'],
                'total_time_hours': result['total_time_hours'],
                'urgent_on_time': result['urgent_on_time'],
                'improvement_pct': result.get('improvement_pct', 0),
                'method': result['method']
            }
        
        # Save best route to database
        best_result = optimization_result['best_result']
        cursor.execute("""
            INSERT INTO optimized_routes 
            (zone_id, delivery_sequence, total_distance, estimated_time, metrics)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            request.zone_id,
            json.dumps(best_result['route']),
            best_result['total_distance_km'],
            int(best_result['total_time_hours'] * 60),
            json.dumps({
                'urgent_on_time': best_result['urgent_on_time'],
                'method': optimization_result['best_method'],
                'improvement_pct': best_result.get('improvement_pct', 0),
                'traffic_level': traffic_level,
                'weather_condition': weather_condition
            })
        ))
        
        conn.commit()
        route_id = cursor.lastrowid
        
        cursor.close()
        conn.close()
        
        return {
            'route_id': route_id,
            'best_method': optimization_result['best_method'],
            'results': formatted_results,
            'best_result': formatted_results[optimization_result['best_method']],
            'scenario': {
                'traffic_level': traffic_level,
                'weather_condition': weather_condition,
                'traffic_factor': scenario['traffic_factor'],
                'weather_factor': scenario['weather_factor']
            },
            'real_time_data': {
                'weather': weather_data,
                'traffic': traffic_data
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ml/register-relocation")
def register_relocation(relocation: RelocationInput):
    """Register a customer address relocation"""
    try:
        result = relocation_tracker.register_relocation(
            location_id=relocation.location_id,
            old_coords=(relocation.old_latitude, relocation.old_longitude),
            new_coords=(relocation.new_latitude, relocation.new_longitude),
            reason=relocation.reason
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ml/active-relocations")
def get_active_relocations():
    """Get all pending relocations"""
    try:
        relocations = relocation_tracker.get_active_relocations()
        return {"relocations": relocations, "count": len(relocations)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ml/analyze-relocation-impact")
def analyze_relocation_impact(scenario: Dict, relocation: Dict):
    """Analyze impact of address change on route"""
    try:
        impact = dynamic_rerouter.analyze_relocation_impact(scenario, relocation)
        return impact
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ml/execute-rerouting")
def execute_rerouting(request: ReroutingRequest):
    """Execute dynamic rerouting with ML"""
    try:
        result = dynamic_rerouter.execute_rerouting(
            scenario=request.scenario,
            relocations=request.relocations,
            method=request.method
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ml/model-info")
def get_model_info():
    """Get information about loaded ML models"""
    return {
        'priority_classifier': {
            'loaded': priority_classifier.is_trained,
            'model_type': 'XGBoost',
            'features': len(priority_classifier.feature_names) if priority_classifier.is_trained else 0,
            'mail_types': len(priority_classifier.MAIL_TYPES),
            'sender_types': len(priority_classifier.SENDER_TYPES)
        },
        'route_optimizer': {
            'algorithms': ['Nearest Neighbor', 'Urgent Priority', '2-Opt', 'Q-Learning'],
            'q_table_size': len(route_optimizer.q_table),
            'learning_rate': route_optimizer.learning_rate,
            'discount_factor': route_optimizer.discount_factor
        },
        'rerouting_system': {
            'active_relocations': len(relocation_tracker.active_relocations),
            'rerouting_history': len(dynamic_rerouter.rerouting_history)
        }
    }

@app.get("/api/route-statistics")
def get_route_statistics():
    """Get overall route statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total_routes,
                AVG(total_distance) as avg_distance,
                AVG(estimated_time) as avg_time
            FROM optimized_routes
        """)
        
        stats = cursor.fetchone()
        
        cursor.execute("SELECT COUNT(*) as total_deliveries FROM deliveries")
        delivery_stats = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return {
            "total_routes": stats['total_routes'] or 0,
            "total_deliveries": delivery_stats['total_deliveries'] or 0,
            "avg_distance_km": round(stats['avg_distance'] or 0, 2),
            "avg_time_minutes": round(stats['avg_time'] or 0, 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# Pydantic model for real-time condition changes
class ConditionChangeRequest(BaseModel):
    zone_id: int
    deliveries: List[DeliveryInput]
    original_traffic: str = "moderate"
    original_weather: str = "clear"
    new_traffic: str
    new_weather: str
    optimization_method: Optional[str] = "q_learning"

@app.post("/api/ml/change-conditions-realtime")
def change_conditions_realtime(request: ConditionChangeRequest):
    """
    Real-time route comparison when traffic/weather conditions change
    Perfect for Postman testing - shows original vs new routes instantly
    
    Example Postman body:
    {
        "zone_id": 1,
        "deliveries": [...],
        "original_traffic": "moderate",
        "original_weather": "clear",
        "new_traffic": "high",
        "new_weather": "heavy_rain",
        "optimization_method": "q_learning"
    }
    """
    try:
        # Prepare delivery points
        delivery_points = [
            {
                'id': 0,
                'address': 'Postal Depot',
                'latitude': 6.9271,
                'longitude': 79.8612,
                'parcels': 0,
                'urgent': 0
            }
        ]
        
        for idx, delivery in enumerate(request.deliveries, start=1):
            delivery_points.append({
                'id': idx,
                'address': delivery.address,
                'latitude': delivery.latitude,
                'longitude': delivery.longitude,
                'parcels': delivery.parcels or 1,
                'urgent': 1 if delivery.priority == 'urgent' else 0,
                'time_window': 4.0 if delivery.priority == 'urgent' else 8.0
            })
        
        # Calculate ORIGINAL route with original conditions
        original_scenario = {
            'delivery_points': delivery_points,
            'traffic_factor': get_traffic_factor(request.original_traffic),
            'weather_factor': get_weather_factor(request.original_weather),
            'traffic_level': request.original_traffic,
            'weather_condition': request.original_weather
        }
        
        # Calculate NEW route with new conditions
        new_scenario = {
            'delivery_points': delivery_points,
            'traffic_factor': get_traffic_factor(request.new_traffic),
            'weather_factor': get_weather_factor(request.new_weather),
            'traffic_level': request.new_traffic,
            'weather_condition': request.new_weather
        }
        
        # Optimize both scenarios
        method = request.optimization_method
        
        if method == "q_learning":
            original_result = route_optimizer.q_learning_route(original_scenario, episodes=500)
            new_result = route_optimizer.q_learning_route(new_scenario, episodes=500)
        elif method == "2opt":
            base_original = route_optimizer.nearest_neighbor_route(original_scenario)
            original_result = route_optimizer.two_opt_improvement(original_scenario, base_original['route'])
            base_new = route_optimizer.nearest_neighbor_route(new_scenario)
            new_result = route_optimizer.two_opt_improvement(new_scenario, base_new['route'])
        elif method == "urgent_priority":
            original_result = route_optimizer.urgent_priority_route(original_scenario)
            new_result = route_optimizer.urgent_priority_route(new_scenario)
        else:  # nearest_neighbor
            original_result = route_optimizer.nearest_neighbor_route(original_scenario)
            new_result = route_optimizer.nearest_neighbor_route(new_scenario)
        
        # Calculate impacts
        distance_change = new_result['total_distance_km'] - original_result['total_distance_km']
        time_change = new_result['total_time_hours'] - original_result['total_time_hours']
        urgent_change = new_result['urgent_on_time'] - original_result['urgent_on_time']
        
        distance_change_pct = (distance_change / original_result['total_distance_km'] * 100) if original_result['total_distance_km'] > 0 else 0
        time_change_pct = (time_change / original_result['total_time_hours'] * 100) if original_result['total_time_hours'] > 0 else 0
        
        # Determine severity
        def get_severity(dist_pct, time_pct, urgent_change):
            if urgent_change < 0 or time_pct > 50:
                return "CRITICAL"
            elif time_pct > 30 or dist_pct > 30:
                return "HIGH"
            elif time_pct > 15 or dist_pct > 15:
                return "MEDIUM"
            elif time_pct > 5 or dist_pct > 5:
                return "LOW"
            else:
                return "MINIMAL"
        
        severity = get_severity(distance_change_pct, time_change_pct, urgent_change)
        
        # Format response
        return {
            "timestamp": datetime.now().isoformat(),
            "zone_id": request.zone_id,
            "optimization_method": method,
            
            "conditions": {
                "original": {
                    "traffic": request.original_traffic,
                    "weather": request.original_weather,
                    "traffic_factor": original_scenario['traffic_factor'],
                    "weather_factor": original_scenario['weather_factor'],
                    "combined_factor": original_scenario['traffic_factor'] * original_scenario['weather_factor']
                },
                "new": {
                    "traffic": request.new_traffic,
                    "weather": request.new_weather,
                    "traffic_factor": new_scenario['traffic_factor'],
                    "weather_factor": new_scenario['weather_factor'],
                    "combined_factor": new_scenario['traffic_factor'] * new_scenario['weather_factor']
                }
            },
            
            "original_route": {
                "sequence": original_result['route'],
                "deliveries": format_route_for_map(original_result['route'], delivery_points),
                "distance_km": original_result['total_distance_km'],
                "time_hours": original_result['total_time_hours'],
                "time_minutes": round(original_result['total_time_hours'] * 60, 0),
                "urgent_on_time": original_result['urgent_on_time'],
                "total_deliveries": len(delivery_points) - 1
            },
            
            "new_route": {
                "sequence": new_result['route'],
                "deliveries": format_route_for_map(new_result['route'], delivery_points),
                "distance_km": new_result['total_distance_km'],
                "time_hours": new_result['total_time_hours'],
                "time_minutes": round(new_result['total_time_hours'] * 60, 0),
                "urgent_on_time": new_result['urgent_on_time'],
                "total_deliveries": len(delivery_points) - 1
            },
            
            "impact_analysis": {
                "distance_change_km": round(distance_change, 2),
                "distance_change_pct": round(distance_change_pct, 2),
                "time_change_hours": round(time_change, 2),
                "time_change_minutes": round(time_change * 60, 0),
                "time_change_pct": round(time_change_pct, 2),
                "urgent_deliveries_impact": urgent_change,
                "severity": severity,
                "recommendation": get_condition_recommendation(severity, distance_change, time_change)
            },
            
            "route_comparison": {
                "same_sequence": original_result['route'] == new_result['route'],
                "sequence_similarity_pct": calculate_sequence_similarity(
                    original_result['route'], 
                    new_result['route']
                )
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_condition_recommendation(severity: str, distance_change: float, time_change: float) -> str:
    """Generate recommendation based on condition change impact"""
    if severity == "CRITICAL":
        return "⚠️ CRITICAL: Route significantly impacted. Consider delaying non-urgent deliveries or requesting additional vehicles."
    elif severity == "HIGH":
        return "🔴 HIGH IMPACT: Route efficiency reduced significantly. Re-optimize route and notify drivers of delays."
    elif severity == "MEDIUM":
        return "🟡 MODERATE IMPACT: Some delays expected. Update ETAs and monitor progress."
    elif severity == "LOW":
        return "🟢 LOW IMPACT: Minor delays possible. Route remains efficient."
    else:
        return "✅ MINIMAL IMPACT: Conditions have negligible effect on delivery schedule."

def calculate_sequence_similarity(route1: List[int], route2: List[int]) -> float:
    """Calculate how similar two route sequences are (0-100%)"""
    if len(route1) != len(route2):
        return 0.0
    
    matching_positions = sum(1 for i in range(len(route1)) if route1[i] == route2[i])
    return round((matching_positions / len(route1)) * 100, 2)

@app.post("/api/ml/simulate-condition-scenarios")
def simulate_condition_scenarios(request: RouteOptimizationRequest):
    """
    Simulate multiple traffic/weather scenarios at once
    Shows how the same route performs under different conditions
    """
    try:
        # Prepare delivery points
        delivery_points = [{'id': 0, 'address': 'Depot', 'latitude': 6.9271, 
                           'longitude': 79.8612, 'parcels': 0, 'urgent': 0}]
        
        for idx, delivery in enumerate(request.deliveries, start=1):
            delivery_points.append({
                'id': idx,
                'address': delivery.address,
                'latitude': delivery.latitude,
                'longitude': delivery.longitude,
                'parcels': delivery.parcels or 1,
                'urgent': 1 if delivery.priority == 'urgent' else 0,
                'time_window': 4.0 if delivery.priority == 'urgent' else 8.0
            })
        
        # Define scenarios to test
        scenarios = [
            {"traffic": "low", "weather": "clear"},
            {"traffic": "moderate", "weather": "clear"},
            {"traffic": "high", "weather": "clear"},
            {"traffic": "moderate", "weather": "light_rain"},
            {"traffic": "high", "weather": "heavy_rain"},
            {"traffic": "severe", "weather": "flooding"},
        ]
        
        results = []
        
        for scenario_config in scenarios:
            scenario = {
                'delivery_points': delivery_points,
                'traffic_factor': get_traffic_factor(scenario_config['traffic']),
                'weather_factor': get_weather_factor(scenario_config['weather']),
                'traffic_level': scenario_config['traffic'],
                'weather_condition': scenario_config['weather']
            }
            
            route_result = route_optimizer.q_learning_route(scenario, episodes=300)
            
            results.append({
                "scenario": scenario_config,
                "factors": {
                    "traffic_factor": scenario['traffic_factor'],
                    "weather_factor": scenario['weather_factor'],
                    "combined_factor": scenario['traffic_factor'] * scenario['weather_factor']
                },
                "route": {
                    "distance_km": route_result['total_distance_km'],
                    "time_hours": route_result['total_time_hours'],
                    "time_minutes": round(route_result['total_time_hours'] * 60, 0),
                    "urgent_on_time": route_result['urgent_on_time'],
                    "sequence": route_result['route']
                }
            })
        
        # Find best and worst scenarios
        best_scenario = min(results, key=lambda x: x['route']['time_hours'])
        worst_scenario = max(results, key=lambda x: x['route']['time_hours'])
        
        return {
            "zone_id": request.zone_id,
            "total_scenarios": len(scenarios),
            "scenarios": results,
            "best_case": best_scenario,
            "worst_case": worst_scenario,
            "time_range": {
                "min_minutes": round(best_scenario['route']['time_hours'] * 60, 0),
                "max_minutes": round(worst_scenario['route']['time_hours'] * 60, 0),
                "difference_minutes": round((worst_scenario['route']['time_hours'] - best_scenario['route']['time_hours']) * 60, 0)
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)