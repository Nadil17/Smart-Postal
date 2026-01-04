"""
Unit tests for Dynamic Rerouter
"""
import unittest
import sys
sys.path.append('..')

from models.route_optimizer import DynamicRouteOptimizer
from models.rerouter import DynamicRerouter, RelocationTracker


class TestRerouter(unittest.TestCase):
    """Test cases for dynamic rerouting"""
    
    def setUp(self):
        """Set up test fixtures"""
        optimizer = DynamicRouteOptimizer(random_state=42)
        self.rerouter = DynamicRerouter(optimizer)
        
        self.scenario = {
            'delivery_points': [
                {'id': 0, 'latitude': 6.9271, 'longitude': 79.8612, 'parcels': 0, 'urgent': 0, 'time_window': None},
                {'id': 1, 'latitude': 6.9350, 'longitude': 79.8700, 'parcels': 5, 'urgent': 2, 'time_window': 2.5},
                {'id': 2, 'latitude': 6.9200, 'longitude': 79.8500, 'parcels': 3, 'urgent': 0, 'time_window': None},
            ],
            'traffic_factor': 1.2,
            'weather_factor': 1.0,
            'traffic_level': 'moderate',
            'weather_condition': 'clear'
        }
    
    def test_register_relocation(self):
        """Test relocation registration"""
        tracker = RelocationTracker()
        
        relocation = tracker.register_relocation(
            location_id=1,
            old_coords=(6.9350, 79.8700),
            new_coords=(6.9400, 79.8800),
            reason='customer_request'
        )
        
        self.assertIn('relocation_id', relocation)
        self.assertEqual(relocation['location_id'], 1)
        self.assertEqual(relocation['status'], 'pending')
        self.assertGreater(relocation['distance_change_km'], 0)
    
    def test_get_active_relocations(self):
        """Test getting active relocations"""
        tracker = RelocationTracker()
        
        tracker.register_relocation(1, (6.9350, 79.8700), (6.9400, 79.8800))
        tracker.register_relocation(2, (6.9200, 79.8500), (6.9250, 79.8550))
        
        active = tracker.get_active_relocations()
        
        self.assertEqual(len(active), 2)
    
    def test_mark_processed(self):
        """Test marking relocation as processed"""
        tracker = RelocationTracker()
        
        tracker.register_relocation(1, (6.9350, 79.8700), (6.9400, 79.8800))
        tracker.mark_processed(1)
        
        active = tracker.get_active_relocations()
        self.assertEqual(len(active), 0)
    
    def test_analyze_impact(self):
        """Test relocation impact analysis"""
        relocation = {
            'location_id': 1,
            'new_latitude': 6.9400,
            'new_longitude': 79.8800,
            'distance_change_km': 1.5
        }
        
        impact = self.rerouter.analyze_relocation_impact(self.scenario, relocation)
        
        self.assertIn('current_route', impact)
        self.assertIn('new_route', impact)
        self.assertIn('impact', impact)
        self.assertIn('recommendation', impact)
    
    def test_execute_rerouting(self):
        """Test rerouting execution"""
        relocations = [
            {
                'location_id': 1,
                'new_latitude': 6.9400,
                'new_longitude': 79.8800
            }
        ]
        
        result = self.rerouter.execute_rerouting(self.scenario, relocations)
        
        self.assertIn('original_route', result)
        self.assertIn('new_route', result)
        self.assertIn('improvement', result)
        self.assertEqual(result['relocations_processed'], 1)


if __name__ == '__main__':
    unittest.main()