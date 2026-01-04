"""
Route Optimization Module
Supports Q-Learning, 2-Opt, Urgent Priority, and Nearest Neighbor algorithms
"""
import random
import numpy as np
from math import radians, sin, cos, sqrt, atan2
from typing import Dict, List


class DynamicRouteOptimizer:
    """Route Optimization with multiple algorithms and fuel consumption tracking"""

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        np.random.seed(random_state)
        
        self.q_table = {}
        self.learning_rate = 0.1
        self.discount_factor = 0.95
        self.exploration_rate = 0.2
        
        self.avg_speed_kmh = 25
        self.service_time_minutes = 5
        
        # Fuel consumption parameters
        self.base_fuel_consumption_per_km = 0.12
        self.idle_fuel_consumption_per_hour = 0.8
        self.fuel_tank_capacity = 50
        self.initial_fuel_level = 45

    def calculate_distance(self, point1: Dict, point2: Dict) -> float:
        """Calculate great circle distance in kilometers"""
        lat1, lon1 = point1['latitude'], point1['longitude']
        lat2, lon2 = point2['latitude'], point2['longitude']

        R = 6371
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)

        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))

        return R * c

    def calculate_travel_time(self, distance_km: float, traffic_factor: float, 
                             weather_factor: float) -> float:
        """Calculate travel time with traffic and weather"""
        base_time_hours = distance_km / self.avg_speed_kmh
        adjusted_time = base_time_hours * traffic_factor * weather_factor
        return adjusted_time

    def calculate_fuel_consumption(self, distance_km: float, traffic_factor: float,
                                   weather_factor: float, service_time_hours: float = 0) -> float:
        """Calculate fuel consumption for a route segment"""
        driving_fuel = distance_km * self.base_fuel_consumption_per_km
        traffic_multiplier = 1 + (traffic_factor - 1) * 0.3
        weather_multiplier = 1 + (weather_factor - 1) * 0.2
        total_driving_fuel = driving_fuel * traffic_multiplier * weather_multiplier
        idling_fuel = service_time_hours * self.idle_fuel_consumption_per_hour
        return total_driving_fuel + idling_fuel

    def calculate_route_fuel_metrics(self, route: List[int], points: List[Dict],
                                     traffic: float, weather: float) -> Dict:
        """Calculate comprehensive fuel metrics for a route"""
        total_fuel = 0
        total_distance = 0
        
        for i in range(len(route) - 1):
            current_point = points[route[i]]
            next_point = points[route[i + 1]]
            
            distance = self.calculate_distance(current_point, next_point)
            total_distance += distance
            service_time = self.service_time_minutes / 60 if i < len(route) - 2 else 0
            fuel = self.calculate_fuel_consumption(distance, traffic, weather, service_time)
            total_fuel += fuel
        
        fuel_efficiency = total_distance / total_fuel if total_fuel > 0 else 0
        remaining_fuel = self.initial_fuel_level - total_fuel
        fuel_percentage = (remaining_fuel / self.fuel_tank_capacity) * 100
        
        return {
            'total_fuel_liters': round(total_fuel, 2),
            'fuel_efficiency_km_per_liter': round(fuel_efficiency, 2),
            'remaining_fuel_liters': round(remaining_fuel, 2),
            'fuel_percentage': round(fuel_percentage, 1),
            'needs_refuel': remaining_fuel < (self.fuel_tank_capacity * 0.2)
        }

    def _count_urgent_on_time(self, route: List[int], points: List[Dict],
                             traffic: float, weather: float) -> int:
        """Count urgent deliveries made within time window"""
        cumulative_time = 0
        urgent_on_time = 0

        for i in range(1, len(route)-1):
            point_id = route[i]
            point = points[point_id]
            prev_point_id = route[i-1]
            dist = self.calculate_distance(points[prev_point_id], point)
            cumulative_time += self.calculate_travel_time(dist, traffic, weather)
            cumulative_time += self.service_time_minutes / 60

            if point.get('urgent', 0) > 0 and point.get('time_window'):
                if cumulative_time <= point['time_window']:
                    urgent_on_time += point['urgent']

        return urgent_on_time

    def nearest_neighbor_route(self, scenario: Dict) -> Dict:
        """Nearest Neighbor algorithm - baseline"""
        points = scenario['delivery_points']
        traffic = scenario['traffic_factor']
        weather = scenario['weather_factor']

        unvisited = set(range(1, len(points)))
        current = 0
        route = [0]
        total_distance = 0
        total_time = 0

        while unvisited:
            nearest = min(unvisited, 
                         key=lambda x: self.calculate_distance(points[current], points[x]))
            distance = self.calculate_distance(points[current], points[nearest])
            travel_time = self.calculate_travel_time(distance, traffic, weather)
            total_distance += distance
            total_time += travel_time + (self.service_time_minutes / 60)
            route.append(nearest)
            unvisited.remove(nearest)
            current = nearest

        distance = self.calculate_distance(points[current], points[0])
        total_distance += distance
        total_time += self.calculate_travel_time(distance, traffic, weather)
        route.append(0)

        urgent_on_time = self._count_urgent_on_time(route, points, traffic, weather)
        fuel_metrics = self.calculate_route_fuel_metrics(route, points, traffic, weather)

        return {
            'route': route,
            'total_distance_km': round(total_distance, 2),
            'total_time_hours': round(total_time, 2),
            'urgent_on_time': urgent_on_time,
            'method': 'Nearest Neighbor',
            **fuel_metrics
        }

    def two_opt_improvement(self, scenario: Dict, initial_route: List[int]) -> Dict:
        """2-Opt local search improvement"""
        points = scenario['delivery_points']
        traffic = scenario['traffic_factor']
        weather = scenario['weather_factor']

        route = initial_route.copy()
        improved = True
        iterations = 0
        max_iterations = 100

        def route_distance(r):
            return sum(self.calculate_distance(points[r[i]], points[r[i+1]]) 
                      for i in range(len(r) - 1))

        while improved and iterations < max_iterations:
            improved = False
            iterations += 1
            for i in range(1, len(route) - 2):
                for j in range(i + 1, len(route) - 1):
                    new_route = route[:i] + route[i:j+1][::-1] + route[j+1:]
                    if route_distance(new_route) < route_distance(route):
                        route = new_route
                        improved = True
                        break
                if improved:
                    break

        total_distance = route_distance(route)
        total_time = sum(
            self.calculate_travel_time(
                self.calculate_distance(points[route[i]], points[route[i+1]]),
                traffic, weather
            ) + (self.service_time_minutes / 60 if i < len(route) - 2 else 0)
            for i in range(len(route) - 1)
        )

        urgent_on_time = self._count_urgent_on_time(route, points, traffic, weather)
        fuel_metrics = self.calculate_route_fuel_metrics(route, points, traffic, weather)

        return {
            'route': route,
            'total_distance_km': round(total_distance, 2),
            'total_time_hours': round(total_time, 2),
            'urgent_on_time': urgent_on_time,
            'iterations': iterations,
            'method': '2-Opt Improved',
            **fuel_metrics
        }

    def urgent_priority_route(self, scenario: Dict) -> Dict:
        """Urgent Priority strategy - deliver urgent items first"""
        points = scenario['delivery_points']
        traffic = scenario['traffic_factor']
        weather = scenario['weather_factor']

        urgent_points = [i for i in range(1, len(points)) if points[i].get('urgent', 0) > 0]
        regular_points = [i for i in range(1, len(points)) if points[i].get('urgent', 0) == 0]
        urgent_points.sort(key=lambda x: points[x].get('time_window', float('inf')))

        route = [0]
        current = 0
        total_distance = 0
        total_time = 0

        for point_id in urgent_points:
            distance = self.calculate_distance(points[current], points[point_id])
            travel_time = self.calculate_travel_time(distance, traffic, weather)
            total_distance += distance
            total_time += travel_time + (self.service_time_minutes / 60)
            route.append(point_id)
            current = point_id

        unvisited = set(regular_points)
        while unvisited:
            nearest = min(unvisited, 
                         key=lambda x: self.calculate_distance(points[current], points[x]))
            distance = self.calculate_distance(points[current], points[nearest])
            travel_time = self.calculate_travel_time(distance, traffic, weather)
            total_distance += distance
            total_time += travel_time + (self.service_time_minutes / 60)
            route.append(nearest)
            unvisited.remove(nearest)
            current = nearest

        distance = self.calculate_distance(points[current], points[0])
        total_distance += distance
        total_time += self.calculate_travel_time(distance, traffic, weather)
        route.append(0)

        urgent_on_time = self._count_urgent_on_time(route, points, traffic, weather)
        fuel_metrics = self.calculate_route_fuel_metrics(route, points, traffic, weather)

        return {
            'route': route,
            'total_distance_km': round(total_distance, 2),
            'total_time_hours': round(total_time, 2),
            'urgent_on_time': urgent_on_time,
            'method': 'Urgent Priority',
            **fuel_metrics
        }

    def q_learning_route(self, scenario: Dict, episodes: int = 500) -> Dict:
        """Q-Learning reinforcement learning algorithm"""
        points = scenario['delivery_points']
        traffic = scenario['traffic_factor']
        weather = scenario['weather_factor']

        def get_state_key(current, unvisited):
            return (current, tuple(sorted(unvisited)))

        def get_reward(current, next_point, cumulative_time):
            distance = self.calculate_distance(points[current], points[next_point])
            reward = -distance

            if points[next_point].get('urgent', 0) > 0 and points[next_point].get('time_window'):
                travel_time = self.calculate_travel_time(distance, traffic, weather)
                arrival_time = cumulative_time + travel_time
                if arrival_time <= points[next_point]['time_window']:
                    reward += 10
                else:
                    reward -= 5

            reward += points[next_point].get('parcels', 0) * 0.1
            return reward

        # Training phase
        for episode in range(episodes):
            current = 0
            unvisited = set(range(1, len(points)))
            cumulative_time = 0

            while unvisited:
                state_key = get_state_key(current, unvisited)

                if random.random() < self.exploration_rate:
                    next_point = random.choice(list(unvisited))
                else:
                    q_values = {
                        candidate: self.q_table.get((state_key, candidate), 0)
                        for candidate in unvisited
                    }
                    next_point = max(q_values, key=q_values.get)

                reward = get_reward(current, next_point, cumulative_time)
                old_q = self.q_table.get((state_key, next_point), 0)

                next_unvisited = unvisited - {next_point}
                next_state_key = get_state_key(next_point, next_unvisited)

                if next_unvisited:
                    max_next_q = max(
                        self.q_table.get((next_state_key, a), 0) 
                        for a in next_unvisited
                    )
                else:
                    max_next_q = 0

                new_q = old_q + self.learning_rate * (reward + self.discount_factor * max_next_q - old_q)
                self.q_table[(state_key, next_point)] = new_q

                distance = self.calculate_distance(points[current], points[next_point])
                cumulative_time += self.calculate_travel_time(distance, traffic, weather)
                cumulative_time += self.service_time_minutes / 60

                current = next_point
                unvisited.remove(next_point)

        # Generate optimal route
        current = 0
        unvisited = set(range(1, len(points)))
        route = [0]
        total_distance = 0
        total_time = 0

        while unvisited:
            state_key = get_state_key(current, unvisited)
            q_values = {
                candidate: self.q_table.get((state_key, candidate), 0)
                for candidate in unvisited
            }
            next_point = max(q_values, key=q_values.get)

            distance = self.calculate_distance(points[current], points[next_point])
            travel_time = self.calculate_travel_time(distance, traffic, weather)
            total_distance += distance
            total_time += travel_time + (self.service_time_minutes / 60)
            route.append(next_point)
            unvisited.remove(next_point)
            current = next_point

        distance = self.calculate_distance(points[current], points[0])
        total_distance += distance
        total_time += self.calculate_travel_time(distance, traffic, weather)
        route.append(0)

        urgent_on_time = self._count_urgent_on_time(route, points, traffic, weather)
        fuel_metrics = self.calculate_route_fuel_metrics(route, points, traffic, weather)

        return {
            'route': route,
            'total_distance_km': round(total_distance, 2),
            'total_time_hours': round(total_time, 2),
            'urgent_on_time': urgent_on_time,
            'method': 'Q-Learning',
            **fuel_metrics
        }

    def optimize_route(self, scenario: Dict, methods: List[str] = None) -> Dict:
        """Optimize route using multiple algorithms"""
        if methods is None:
            methods = ['nearest_neighbor', 'urgent_priority', '2opt', 'q_learning']

        results = {}

        if 'nearest_neighbor' in methods:
            results['nearest_neighbor'] = self.nearest_neighbor_route(scenario)

        if 'urgent_priority' in methods:
            results['urgent_priority'] = self.urgent_priority_route(scenario)

        if '2opt' in methods:
            base_route = results.get('nearest_neighbor', self.nearest_neighbor_route(scenario))
            results['2opt'] = self.two_opt_improvement(scenario, base_route['route'])

        if 'q_learning' in methods:
            results['q_learning'] = self.q_learning_route(scenario, episodes=500)

        best_method = min(results.keys(), 
                         key=lambda m: (results[m]['total_distance_km'] * 0.6 + 
                                       results[m]['total_fuel_liters'] * 0.4))

        baseline_distance = results.get('nearest_neighbor', {}).get('total_distance_km', 0)
        baseline_fuel = results.get('nearest_neighbor', {}).get('total_fuel_liters', 0)

        for method, result in results.items():
            if baseline_distance > 0 and method != 'nearest_neighbor':
                improvement = ((baseline_distance - result['total_distance_km']) / baseline_distance) * 100
                result['improvement_pct'] = round(improvement, 2)
                
                if baseline_fuel > 0:
                    fuel_savings = baseline_fuel - result['total_fuel_liters']
                    fuel_improvement = (fuel_savings / baseline_fuel) * 100
                    result['fuel_savings_liters'] = round(fuel_savings, 2)
                    result['fuel_improvement_pct'] = round(fuel_improvement, 2)
            else:
                result['improvement_pct'] = 0.0
                result['fuel_savings_liters'] = 0.0
                result['fuel_improvement_pct'] = 0.0

        return {
            'scenario': scenario,
            'results': results,
            'best_method': best_method,
            'best_result': results[best_method]
        }