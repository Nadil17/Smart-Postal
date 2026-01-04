"""
Unit tests for Route Optimizer
"""
import unittest
import sys
sys.path.append('..')

from models.route_optimizer import DynamicRouteOptimizer


class TestRouteOptimizer(unittest.TestCase):
    """Test cases for route optimization"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.optimizer = DynamicRouteOptimizer(random_state=42)
        
        # Sample scenario
        self.scenario = {
            'delivery_points': [
                {'id': 0, 'latitude': 6.9271, 'longitude': 79.8612, 'parcels': 0, 'urgent': 0, 'time_window': None},
                {'id': 1, 'latitude': 6.9350, 'longitude': 79.8700, 'parcels': 5, 'urgent': 2, 'time_window': 2.5},
                {'id': 2, 'latitude': 6.9200, 'longitude': 79.8500, 'parcels': 3, 'urgent': 0, 'time_window': None},
                {'id': 3, 'latitude': 6.9400, 'longitude': 79.8800, 'parcels': 7, 'urgent': 1, 'time_window': 3.0},
            ],
            'traffic_factor': 1.2,
            'weather_factor': 1.0,
            'traffic_level': 'moderate',
            'weather_condition': 'clear'
        }
    
    def test_distance_calculation(self):
        """Test distance calculation"""
        point1 = {'latitude': 6.9271, 'longitude': 79.8612}
        point2 = {'latitude': 6.9350, 'longitude': 79.8700}
        
        distance = self.optimizer.calculate_distance(point1, point2)
        
        self.assertGreater(distance, 0)
        self.assertIsInstance(distance, float)
    
    def test_nearest_neighbor(self):
        """Test nearest neighbor algorithm"""
        result = self.optimizer.nearest_neighbor_route(self.scenario)
        
        self.assertIn('route', result)
        self.assertIn('total_distance_km', result)
        self.assertIn('total_time_hours', result)
        self.assertEqual(result['method'], 'Nearest Neighbor')
        
        # Check route starts and ends at depot
        self.assertEqual(result['route'][0], 0)
        self.assertEqual(result['route'][-1], 0)
    
    def test_urgent_priority(self):
        """Test urgent priority algorithm"""
        result = self.optimizer.urgent_priority_route(self.scenario)
        
        self.assertIn('route', result)
        self.assertEqual(result['method'], 'Urgent Priority')
        
        # Check urgent deliveries come first
        route = result['route']
        urgent_positions = []
        regular_positions = []
        
        for i, point_id in enumerate(route[1:-1], 1):  # Skip depot
            point = self.scenario['delivery_points'][point_id]
            if point['urgent'] > 0:
                urgent_positions.append(i)
            else:
                regular_positions.append(i)
        
        if urgent_positions and regular_positions:
            self.assertLess(max(urgent_positions), min(regular_positions))
    
    def test_2opt_improvement(self):
        """Test 2-opt improvement"""
        base_result = self.optimizer.nearest_neighbor_route(self.scenario)
        improved_result = self.optimizer.two_opt_improvement(
            self.scenario, 
            base_result['route']
        )
        
        self.assertIn('route', improved_result)
        self.assertIn('iterations', improved_result)
        self.assertEqual(improved_result['method'], '2-Opt Improved')
        
        # 2-opt should not increase distance
        self.assertLessEqual(
            improved_result['total_distance_km'],
            base_result['total_distance_km']
        )
    
    def test_fuel_metrics(self):
        """Test fuel consumption calculation"""
        result = self.optimizer.nearest_neighbor_route(self.scenario)
        
        self.assertIn('total_fuel_liters', result)
        self.assertIn('fuel_efficiency_km_per_liter', result)
        self.assertIn('remaining_fuel_liters', result)
        self.assertIn('fuel_percentage', result)
        self.assertIn('needs_refuel', result)
        
        self.assertGreater(result['total_fuel_liters'], 0)
    
    def test_optimize_all_methods(self):
        """Test optimization with all methods"""
        result = self.optimizer.optimize_route(self.scenario)
        
        self.assertIn('results', result)
        self.assertIn('best_method', result)
        self.assertIn('best_result', result)
        
        # Should have all 4 methods
        self.assertEqual(len(result['results']), 4)


if __name__ == '__main__':
    unittest.main()