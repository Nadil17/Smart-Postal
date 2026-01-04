# smart-postal-back-end/backend/utils/recommender.py
import torch
import pandas as pd
import numpy as np
from geopy.distance import geodesic
from shapely.geometry import Point, LineString
from models.gnn_predictor import ST_GNN_Predictor
import os

class RecommendationEngine:
    def __init__(self):
        # 1. Path Setup (Dynamic)
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(base_dir, 'pretrained_models', 'st_gnn_colombo_model.pth')
        
        # 2. Real Colombo Smart Locker Locations with Addresses
        self.lockers = pd.DataFrame([
            {
                'id': 'L01', 
                'name': 'Smart Locker - Fort Railway Station', 
                'lat': 6.9344, 
                'lon': 79.8428,
                'address': 'Fort Railway Station, Olcott Mawatha, Colombo 01'
            },
            {
                'id': 'L02', 
                'name': 'Smart Locker - Pettah Central', 
                'lat': 6.9380, 
                'lon': 79.8480,
                'address': 'Main Street, Pettah, Colombo 11'
            },
            {
                'id': 'L03', 
                'name': 'Smart Locker - Havelock City Mall', 
                'lat': 6.8820, 
                'lon': 79.8612,
                'address': 'Havelock City Mall, Havelock Road, Colombo 05'
            },
            {
                'id': 'L04', 
                'name': 'Smart Locker - Nugegoda Super Market', 
                'lat': 6.8649, 
                'lon': 79.8997,
                'address': 'High Level Road, Nugegoda'
            },
            {
                'id': 'L05', 
                'name': 'Smart Locker - Wellawatte Junction', 
                'lat': 6.8744, 
                'lon': 79.8606,
                'address': 'Galle Road, Wellawatte, Colombo 06'
            },
            {
                'id': 'L06', 
                'name': 'Smart Locker - Bambalapitiya Savoy', 
                'lat': 6.8890, 
                'lon': 79.8560,
                'address': 'Galle Road, Bambalapitiya, Colombo 04'
            },
            {
                'id': 'L07', 
                'name': 'Smart Locker - Liberty Plaza', 
                'lat': 6.9120, 
                'lon': 79.8490,
                'address': 'R.A. De Mel Mawatha, Colombo 03'
            },
            {
                'id': 'L08', 
                'name': 'Smart Locker - Majestic City', 
                'lat': 6.8930, 
                'lon': 79.8530,
                'address': 'Station Road, Bambalapitiya, Colombo 04'
            },
        ])

        # 3. Load AI Brain
        self.model = ST_GNN_Predictor(num_nodes=50, in_channels=5)
        try:
            self.model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
            self.model.eval()
            print("✅ ST-GNN Brain Loaded!")
        except Exception as e:
            print(f"⚠️ Warning: Model load failed ({e}). Using dummy predictions.")
            self.model = None

    def get_recommendations(self, cust_lat, cust_lon, courier_route_points):
        candidates = []
        courier_line = LineString(courier_route_points)
        
        for _, locker in self.lockers.iterrows():
            # Distance Checks
            dist_cust = geodesic((cust_lat, cust_lon), (locker['lat'], locker['lon'])).km
            if dist_cust > 5.0: continue

            # AI Prediction (Simulated forward pass for now)
            # In production: prepare tensor inputs -> self.model(inputs)
            small_avail = np.random.randint(2, 8)
            medium_avail = np.random.randint(3, 10)
            large_avail = np.random.randint(1, 5)
            total_avail = small_avail + medium_avail + large_avail

            # Scoring Logic (Novelty 2)
            locker_pt = Point(locker['lon'], locker['lat'])
            dist_route = courier_line.distance(locker_pt) * 111
            
            score = (0.4 * (100 - dist_cust*20)) + \
                    (0.4 * (100 - dist_route*50)) + \
                    (0.2 * (total_avail*10))
            
            candidates.append({
                "id": locker['id'],
                "name": locker['name'],
                "address": locker['address'],
                "latitude": locker['lat'],
                "longitude": locker['lon'],
                "score": round(max(0, score), 1),
                "distance": f"{dist_cust:.2f} km",
                "availability": {
                    "small": small_avail,
                    "medium": medium_avail,
                    "large": large_avail
                },
                "route_deviation": f"{dist_route:.2f} km",
                "predicted_availability": min(95, int(50 + total_avail * 2))
            })
            
        return sorted(candidates, key=lambda x: x['score'], reverse=True)[:3]

# Create a global instance to be used by the API
engine = RecommendationEngine()