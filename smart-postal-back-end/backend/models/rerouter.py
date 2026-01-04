"""
Dynamic Rerouting System
Handles address changes with impact analysis
"""
from datetime import datetime
from typing import Dict, List, Tuple
from math import radians, sin, cos, sqrt, atan2


class RelocationTracker:
    """Track and manage customer address relocations"""

    def __init__(self):
        self.relocation_history = []
        self.active_relocations = {}

    def register_relocation(self, location_id: int, old_coords: Tuple[float, float],
                          new_coords: Tuple[float, float], reason: str = 'customer_request') -> Dict:
        """Register a new address relocation"""
        lat1, lon1 = old_coords
        lat2, lon2 = new_coords

        R = 6371
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance_change_km = R * c

        relocation = {
            'relocation_id': f'REL{len(self.relocation_history)+1:05d}',
            'location_id': location_id,
            'old_latitude': old_coords[0],
            'old_longitude': old_coords[1],
            'new_latitude': new_coords[0],
            'new_longitude': new_coords[1],
            'distance_change_km': round(distance_change_km, 2),
            'reason': reason,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        }

        self.relocation_history.append(relocation)
        self.active_relocations[location_id] = relocation

        return relocation

    def get_active_relocations(self) -> List[Dict]:
        """Get all pending relocations"""
        return list(self.active_relocations.values())

    def mark_processed(self, location_id: int):
        """Mark relocation as processed"""
        if location_id in self.active_relocations:
            self.active_relocations[location_id]['status'] = 'processed'
            del self.active_relocations[location_id]


class DynamicRerouter:
    """Dynamic Rerouting System"""

    def __init__(self, route_optimizer):
        self.optimizer = route_optimizer
        self.relocation_tracker = RelocationTracker()
        self.rerouting_history = []

    def analyze_relocation_impact(self, scenario: Dict, relocation: Dict) -> Dict:
        """Analyze impact of address change on current route"""
        location_id = relocation['location_id']

        updated_scenario = {
            'delivery_points': [p.copy() for p in scenario['delivery_points']],
            'traffic_factor': scenario['traffic_factor'],
            'weather_factor': scenario['weather_factor'],
            'traffic_level': scenario.get('traffic_level', 'moderate'),
            'weather_condition': scenario.get('weather_condition', 'clear')
        }

        for point in updated_scenario['delivery_points']:
            if point['id'] == location_id:
                point['latitude'] = relocation['new_latitude']
                point['longitude'] = relocation['new_longitude']
                break

        current_result = self.optimizer.q_learning_route(scenario, episodes=300)
        new_result = self.optimizer.q_learning_route(updated_scenario, episodes=300)

        distance_impact = new_result['total_distance_km'] - current_result['total_distance_km']
        time_impact = new_result['total_time_hours'] - current_result['total_time_hours']
        urgent_impact = new_result['urgent_on_time'] - current_result['urgent_on_time']
        fuel_impact = new_result['total_fuel_liters'] - current_result['total_fuel_liters']

        impact = {
            'location_id': location_id,
            'relocation_distance_km': relocation['distance_change_km'],
            'current_route': {
                'distance_km': current_result['total_distance_km'],
                'time_hours': current_result['total_time_hours'],
                'urgent_success': current_result['urgent_on_time'],
                'fuel_liters': current_result['total_fuel_liters']
            },
            'new_route': {
                'distance_km': new_result['total_distance_km'],
                'time_hours': new_result['total_time_hours'],
                'urgent_success': new_result['urgent_on_time'],
                'fuel_liters': new_result['total_fuel_liters']
            },
            'impact': {
                'distance_change_km': round(distance_impact, 2),
                'time_change_hours': round(time_impact, 2),
                'urgent_impact': urgent_impact,
                'fuel_change_liters': round(fuel_impact, 2),
                'distance_change_pct': round((distance_impact / current_result['total_distance_km']) * 100, 2) if current_result['total_distance_km'] > 0 else 0
            },
            'recommendation': self._get_recommendation(distance_impact, time_impact, urgent_impact, fuel_impact)
        }

        return impact

    def _get_recommendation(self, distance_impact: float, 
                           time_impact: float, urgent_impact: int, fuel_impact: float) -> str:
        """Determine rerouting recommendation"""
        if urgent_impact < 0:
            return 'CRITICAL - Immediate reroute required'
        if distance_impact > 5 or time_impact > 0.5 or fuel_impact > 2:
            return 'HIGH PRIORITY - Reroute recommended'
        if distance_impact > 2 or time_impact > 0.2 or fuel_impact > 1:
            return 'MEDIUM - Reroute beneficial'
        if distance_impact > 0:
            return 'LOW - Reroute optional'
        return 'IMPROVEMENT - Reroute advantageous'

    def execute_rerouting(self, scenario: Dict, relocations: List[Dict],
                         method: str = 'q_learning') -> Dict:
        """Execute dynamic rerouting for location changes"""
        updated_scenario = {
            'delivery_points': [p.copy() for p in scenario['delivery_points']],
            'traffic_factor': scenario['traffic_factor'],
            'weather_factor': scenario['weather_factor'],
            'traffic_level': scenario.get('traffic_level', 'moderate'),
            'weather_condition': scenario.get('weather_condition', 'clear')
        }

        for relocation in relocations:
            location_id = relocation['location_id']
            for point in updated_scenario['delivery_points']:
                if point['id'] == location_id:
                    point['latitude'] = relocation['new_latitude']
                    point['longitude'] = relocation['new_longitude']
                    break

        original_result = self.optimizer.q_learning_route(scenario, episodes=300)

        if method == 'q_learning':
            new_result = self.optimizer.q_learning_route(updated_scenario, episodes=300)
        elif method == '2opt':
            base = self.optimizer.nearest_neighbor_route(updated_scenario)
            new_result = self.optimizer.two_opt_improvement(updated_scenario, base['route'])
        else:
            new_result = self.optimizer.nearest_neighbor_route(updated_scenario)

        rerouting_result = {
            'timestamp': datetime.now().isoformat(),
            'relocations_processed': len(relocations),
            'original_route': {
                'sequence': original_result['route'],
                'distance_km': original_result['total_distance_km'],
                'time_hours': original_result['total_time_hours'],
                'fuel_liters': original_result['total_fuel_liters']
            },
            'new_route': {
                'sequence': new_result['route'],
                'distance_km': new_result['total_distance_km'],
                'time_hours': new_result['total_time_hours'],
                'fuel_liters': new_result['total_fuel_liters']
            },
            'improvement': {
                'distance_saved_km': round(original_result['total_distance_km'] - new_result['total_distance_km'], 2),
                'time_saved_hours': round(original_result['total_time_hours'] - new_result['total_time_hours'], 2),
                'fuel_saved_liters': round(original_result['total_fuel_liters'] - new_result['total_fuel_liters'], 2)
            }
        }

        self.rerouting_history.append(rerouting_result)

        for relocation in relocations:
            self.relocation_tracker.mark_processed(relocation['location_id'])

        return rerouting_result