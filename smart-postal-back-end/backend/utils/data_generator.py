"""
Data generation utilities
"""
import random
from datetime import datetime
from typing import Dict, List


def generate_training_data(n_samples: int = 5000) -> List[Dict]:
    """Generate synthetic training data for priority classification"""
    
    MAIL_TYPES = [
        'Court Notice', 'Legal Document', 'Registered Letter', 'Speed Post',
        'Express Mail', 'Tax Document', 'Government Letter', 'Bank Document',
        'Medical Report', 'Insurance Document', 'Certificate', 'Parcel',
        'Standard Letter', 'Magazine', 'Bill', 'Advertisement'
    ]
    
    SENDER_TYPES = [
        'Court', 'Law Firm', 'Government Office', 'Tax Office', 'Bank',
        'Hospital', 'Insurance Company', 'Educational Institute',
        'Business', 'Individual', 'NGO'
    ]
    
    RECIPIENT_TYPES = [
        'Individual', 'Business', 'Government Office', 'Law Firm',
        'Educational Institute', 'Hospital', 'Bank', 'Insurance Company'
    ]
    
    TIME_SLOTS = ['08:00', '09:30', '11:00', '13:00', '14:30', '16:00']
    DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    
    records = []
    
    for i in range(n_samples):
        mail_type = random.choice(MAIL_TYPES)
        sender_type = random.choice(SENDER_TYPES)
        recipient_type = random.choice(RECIPIENT_TYPES)
        time_received = random.choice(TIME_SLOTS)
        day_of_week = random.choice(DAYS_OF_WEEK)
        
        # Urgency scoring
        urgency_score = 0
        
        if mail_type in ['Court Notice', 'Legal Document', 'Registered Letter', 
                        'Speed Post', 'Express Mail', 'Tax Document', 'Certificate']:
            urgency_score += 4
        
        if sender_type in ['Court', 'Law Firm', 'Government Office', 'Tax Office']:
            urgency_score += 3
        
        if time_received in ['08:00', '09:30']:
            urgency_score += 1
        
        if day_of_week in ['Monday', 'Tuesday']:
            urgency_score += 1
        
        is_urgent = urgency_score >= 5
        
        # Add noise
        if random.random() < 0.02:
            is_urgent = not is_urgent
        
        records.append({
            'mail_id': f'MAIL{i+1:06d}',
            'mail_type': mail_type,
            'sender_type': sender_type,
            'recipient_type': recipient_type,
            'time_received': time_received,
            'day_of_week': day_of_week,
            'priority': 'urgent' if is_urgent else 'regular'
        })
    
    return records


def generate_delivery_scenario(n_points: int = 15) -> Dict:
    """Generate realistic delivery scenario"""
    
    base_lat = 6.9271
    base_lon = 79.8612
    
    depot = {
        'id': 0,
        'name': 'Distribution Center',
        'latitude': base_lat,
        'longitude': base_lon,
        'parcels': 0,
        'urgent': 0,
        'time_window': None
    }
    
    delivery_points = [depot]
    
    for i in range(1, n_points + 1):
        lat = base_lat + random.uniform(-0.15, 0.15)
        lon = base_lon + random.uniform(-0.15, 0.15)
        parcels = random.randint(1, 10)
        has_urgent = random.random() < 0.2
        urgent = random.randint(1, 3) if has_urgent else 0
        time_window = random.uniform(2, 4) if urgent > 0 else None
        
        delivery_points.append({
            'id': i,
            'name': f'Location_{i}',
            'latitude': lat,
            'longitude': lon,
            'parcels': parcels,
            'urgent': urgent,
            'time_window': time_window
        })
    
    # Traffic and weather
    current_hour = datetime.now().hour
    
    if 7 <= current_hour <= 9 or 16 <= current_hour <= 18:
        traffic_factor = random.uniform(1.3, 1.5)
        traffic_level = 'heavy'
    elif 12 <= current_hour <= 13:
        traffic_factor = random.uniform(1.1, 1.3)
        traffic_level = 'moderate'
    else:
        traffic_factor = random.uniform(0.9, 1.1)
        traffic_level = 'light'
    
    weather_conditions = ['clear', 'partly_cloudy', 'light_rain', 'heavy_rain']
    weather_weights = [0.45, 0.30, 0.15, 0.10]
    weather_condition = random.choices(weather_conditions, weights=weather_weights)[0]
    
    weather_factors = {
        'clear': 0.95,
        'partly_cloudy': 1.0,
        'light_rain': 1.15,
        'heavy_rain': 1.30
    }
    
    return {
        'delivery_points': delivery_points,
        'traffic_factor': round(traffic_factor, 2),
        'traffic_level': traffic_level,
        'weather_factor': weather_factors[weather_condition],
        'weather_condition': weather_condition,
        'timestamp': datetime.now().isoformat()
    }