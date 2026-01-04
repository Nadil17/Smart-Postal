"""
Input validation utilities
"""
from typing import Dict, List


def validate_mail_data(data: Dict) -> tuple[bool, str]:
    """Validate mail priority prediction input"""
    
    required_fields = [
        'mail_type',
        'sender_type',
        'recipient_type',
        'time_received',
        'day_of_week'
    ]
    
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
    
    valid_time_slots = ['08:00', '09:30', '11:00', '13:00', '14:30', '16:00']
    if data['time_received'] not in valid_time_slots:
        return False, f"Invalid time_received. Must be one of {valid_time_slots}"
    
    valid_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    if data['day_of_week'] not in valid_days:
        return False, f"Invalid day_of_week. Must be one of {valid_days}"
    
    return True, "Valid"


def validate_scenario(scenario: Dict) -> tuple[bool, str]:
    """Validate delivery scenario"""
    
    if 'delivery_points' not in scenario:
        return False, "Missing delivery_points"
    
    if not isinstance(scenario['delivery_points'], list):
        return False, "delivery_points must be a list"
    
    if len(scenario['delivery_points']) < 2:
        return False, "Must have at least 2 delivery points (depot + 1 delivery)"
    
    for point in scenario['delivery_points']:
        required = ['id', 'latitude', 'longitude', 'parcels']
        if not all(field in point for field in required):
            return False, f"Delivery point missing required fields: {required}"
    
    if scenario.get('traffic_factor', 1.0) < 0:
        return False, "traffic_factor must be positive"
    
    if scenario.get('weather_factor', 1.0) < 0:
        return False, "weather_factor must be positive"
    
    return True, "Valid"