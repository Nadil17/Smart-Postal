"""
Smart Postal Service ML System - Production Ready
Web Application Module with Fuel Consumption Tracking

Features:
- Priority Classification (XGBoost)
- Route Optimization (Q-Learning, 2-Opt, etc.)
- Dynamic Rerouting System
- Fuel Consumption Calculation
"""

import pickle
import json
import random
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from math import radians, sin, cos, sqrt, atan2

# ML imports
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.utils.class_weight import compute_class_weight
import xgboost as xgb


class PriorityClassificationModel:
    """
    Priority Classification using XGBoost
    Classifies mail items as urgent or regular
    """

    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        self.model = None
        self.encoders = {}
        self.scaler = StandardScaler()
        self.feature_names = []
        self.is_trained = False

        # Feature spaces for Sri Lankan postal context
        self.MAIL_TYPES = [
            'Court Notice', 'Legal Document', 'Registered Letter', 'Speed Post',
            'Express Mail', 'Tax Document', 'Government Letter', 'Bank Document',
            'Medical Report', 'Insurance Document', 'Certificate', 'Parcel',
            'Standard Letter', 'Magazine', 'Bill', 'Advertisement'
        ]

        self.SENDER_TYPES = [
            'Court', 'Law Firm', 'Government Office', 'Tax Office', 'Bank',
            'Hospital', 'Insurance Company', 'Educational Institute',
            'Business', 'Individual', 'NGO'
        ]

        self.RECIPIENT_TYPES = [
            'Individual', 'Business', 'Government Office', 'Law Firm',
            'Educational Institute', 'Hospital', 'Bank', 'Insurance Company'
        ]

        self.TIME_SLOTS = ['08:00', '09:30', '11:00', '13:00', '14:30', '16:00']
        self.DAYS_OF_WEEK = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

    def preprocess_features(self, df, fit: bool = True) -> np.ndarray:
        """Feature engineering pipeline"""
        df = df.copy()

        # Encode categorical features
        categorical_features = ['mail_type', 'sender_type', 'recipient_type', 
                               'time_received', 'day_of_week']

        for feature in categorical_features:
            if fit:
                self.encoders[feature] = LabelEncoder()
                df[f'{feature}_encoded'] = self.encoders[feature].fit_transform(df[feature])
            else:
                df[f'{feature}_encoded'] = self.encoders[feature].transform(df[feature])

        # Temporal features
        time_to_category = {
            '08:00': 0, '09:30': 0,
            '11:00': 1, '13:00': 1,
            '14:30': 2, '16:00': 2
        }
        df['time_category'] = df['time_received'].map(time_to_category)

        # Binary indicators
        df['is_priority_sender'] = df['sender_type'].isin(
            ['Court', 'Law Firm', 'Government Office', 'Tax Office']
        ).astype(int)

        df['is_priority_mail'] = df['mail_type'].isin(
            ['Court Notice', 'Legal Document', 'Registered Letter', 
             'Speed Post', 'Express Mail', 'Tax Document', 'Certificate']
        ).astype(int)

        df['is_early_week'] = df['day_of_week'].isin(['Monday', 'Tuesday']).astype(int)
        df['is_morning'] = df['time_received'].isin(['08:00', '09:30']).astype(int)

        # Interaction features
        df['priority_sender_mail'] = df['is_priority_sender'] * df['is_priority_mail']
        df['morning_priority'] = df['is_morning'] * df['is_priority_mail']
        df['early_week_priority'] = df['is_early_week'] * df['is_priority_mail']
        df['morning_early_week'] = df['is_morning'] * df['is_early_week']

        # Feature selection
        self.feature_names = [
            'mail_type_encoded', 'sender_type_encoded', 'recipient_type_encoded',
            'time_received_encoded', 'day_of_week_encoded', 'time_category',
            'is_priority_sender', 'is_priority_mail', 'is_early_week', 'is_morning',
            'priority_sender_mail', 'morning_priority', 'early_week_priority',
            'morning_early_week'
        ]

        X = df[self.feature_names].values

        # Scale features
        if fit:
            X = self.scaler.fit_transform(X)
        else:
            X = self.scaler.transform(X)

        return X

    def train(self, training_data, labels):
        """Train the classification model"""
        import pandas as pd
        
        df = pd.DataFrame(training_data)
        X = self.preprocess_features(df, fit=True)

        # Encode target
        le_target = LabelEncoder()
        y = le_target.fit_transform(labels)
        self.encoders['target'] = le_target

        # Calculate class weights
        class_weights = compute_class_weight(
            'balanced', 
            classes=np.unique(y), 
            y=y
        )
        scale_pos_weight = class_weights[1] / class_weights[0]

        # Train model
        self.model = xgb.XGBClassifier(
            n_estimators=300,
            max_depth=8,
            learning_rate=0.1,
            subsample=0.9,
            colsample_bytree=0.9,
            scale_pos_weight=scale_pos_weight,
            random_state=self.random_state,
            eval_metric='logloss',
            use_label_encoder=False
        )

        self.model.fit(X, y)
        self.is_trained = True

        return {"status": "success", "message": "Model trained successfully"}

    def predict(self, mail_data: Dict) -> Dict:
        """
        Predict priority for a single mail item
        
        Args:
            mail_data: dict with keys: mail_type, sender_type, recipient_type, 
                      time_received, day_of_week
        
        Returns:
            dict with priority, confidence, and probabilities
        """
        if not self.is_trained:
            raise ValueError("Model not trained. Load a trained model first.")

        import pandas as pd
        df = pd.DataFrame([mail_data])
        X = self.preprocess_features(df, fit=False)

        prediction = self.model.predict(X)[0]
        probabilities = self.model.predict_proba(X)[0]

        priority_label = self.encoders['target'].inverse_transform([prediction])[0]

        return {
            'priority': priority_label,
            'confidence': float(probabilities.max()),
            'probability_regular': float(probabilities[0]),
            'probability_urgent': float(probabilities[1])
        }

    def save_model(self, filepath: str):
        """Save trained model to disk"""
        model_data = {
            'model': self.model,
            'encoders': self.encoders,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'random_state': self.random_state
        }
        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)

    def load_model(self, filepath: str):
        """Load trained model from disk"""
        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)
        
        self.model = model_data['model']
        self.encoders = model_data['encoders']
        self.scaler = model_data['scaler']
        self.feature_names = model_data['feature_names']
        self.random_state = model_data['random_state']
        self.is_trained = True


class DynamicRouteOptimizer:
    """
    Route Optimization with multiple algorithms and fuel consumption tracking
    Supports Q-Learning, 2-Opt, Urgent Priority, and Nearest Neighbor
    """

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
        self.base_fuel_consumption_per_km = 0.12  # liters per km (average postal vehicle)
        self.idle_fuel_consumption_per_hour = 0.8  # liters per hour (idling during service)
        self.fuel_tank_capacity = 50  # liters
        self.initial_fuel_level = 45  # liters (90% capacity)

    def calculate_distance(self, point1: Dict, point2: Dict) -> float:
        """Calculate great circle distance in kilometers"""
        lat1, lon1 = point1['latitude'], point1['longitude']
        lat2, lon2 = point2['latitude'], point2['longitude']

        R = 6371  # Earth radius in km
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
        """
        Calculate fuel consumption for a route segment
        
        Args:
            distance_km: Distance traveled
            traffic_factor: Traffic impact (>1 = more fuel)
            weather_factor: Weather impact (>1 = more fuel)
            service_time_hours: Time spent at stops
        
        Returns:
            Fuel consumed in liters
        """
        # Base fuel consumption
        driving_fuel = distance_km * self.base_fuel_consumption_per_km
        
        # Traffic increases fuel consumption (stop-and-go)
        traffic_multiplier = 1 + (traffic_factor - 1) * 0.3
        
        # Weather increases fuel consumption (AC, slower speeds)
        weather_multiplier = 1 + (weather_factor - 1) * 0.2
        
        # Calculate driving fuel with conditions
        total_driving_fuel = driving_fuel * traffic_multiplier * weather_multiplier
        
        # Add idling fuel during service stops
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
            
            # Service time only for delivery stops (not depot)
            service_time = self.service_time_minutes / 60 if i < len(route) - 2 else 0
            
            fuel = self.calculate_fuel_consumption(distance, traffic, weather, service_time)
            total_fuel += fuel
        
        # Calculate fuel efficiency and remaining
        fuel_efficiency = total_distance / total_fuel if total_fuel > 0 else 0
        remaining_fuel = self.initial_fuel_level - total_fuel
        fuel_percentage = (remaining_fuel / self.fuel_tank_capacity) * 100
        
        return {
            'total_fuel_liters': round(total_fuel, 2),
            'fuel_efficiency_km_per_liter': round(fuel_efficiency, 2),
            'remaining_fuel_liters': round(remaining_fuel, 2),
            'fuel_percentage': round(fuel_percentage, 1),
            'needs_refuel': remaining_fuel < (self.fuel_tank_capacity * 0.2)  # Alert at 20%
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

        # Return to depot
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

        # Visit urgent points first
        for point_id in urgent_points:
            distance = self.calculate_distance(points[current], points[point_id])
            travel_time = self.calculate_travel_time(distance, traffic, weather)

            total_distance += distance
            total_time += travel_time + (self.service_time_minutes / 60)

            route.append(point_id)
            current = point_id

        # Visit regular points
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

        # Return to depot
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

        # Return to depot
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
        """
        Optimize route using multiple algorithms
        
        Args:
            scenario: delivery scenario with delivery_points, traffic_factor, weather_factor
            methods: list of methods ['nearest_neighbor', 'urgent_priority', '2opt', 'q_learning']
        
        Returns:
            dict with results for each method and best method identified
        """
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

        # Find best method (considering distance, fuel, and urgent delivery success)
        best_method = min(results.keys(), 
                         key=lambda m: (results[m]['total_distance_km'] * 0.6 + 
                                       results[m]['total_fuel_liters'] * 0.4))

        # Calculate improvements
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
    """
    Dynamic Rerouting System
    Handles address changes with impact analysis and recommendations
    """

    def __init__(self, route_optimizer: DynamicRouteOptimizer):
        self.optimizer = route_optimizer
        self.relocation_tracker = RelocationTracker()
        self.rerouting_history = []

    def analyze_relocation_impact(self, scenario: Dict, relocation: Dict) -> Dict:
        """Analyze impact of address change on current route"""
        location_id = relocation['location_id']

        # Update scenario with new coordinates
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

        # Compare routes
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
        # Apply relocations
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

        # Calculate routes
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