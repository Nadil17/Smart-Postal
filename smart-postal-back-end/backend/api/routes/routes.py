"""
API Routes for Postal ML System
"""
from flask import Blueprint, request, jsonify
from models import (
    PriorityClassificationModel,
    DynamicRouteOptimizer,
    DynamicRerouter
)
import os

api_bp = Blueprint('api', __name__)

# Initialize models
priority_model = PriorityClassificationModel()
route_optimizer = DynamicRouteOptimizer()
rerouter = DynamicRerouter(route_optimizer)

# Load trained model if exists
model_path = 'pretrained_models/priority_classifier.pkl'
if os.path.exists(model_path):
    priority_model.load_model(model_path)


@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'models': {
            'priority_classifier': priority_model.is_trained,
            'route_optimizer': True,
            'rerouter': True
        }
    })


@api_bp.route('/priority/predict', methods=['POST'])
def predict_priority():
    """Predict mail priority"""
    try:
        data = request.get_json()
        
        required_fields = ['mail_type', 'sender_type', 'recipient_type', 
                          'time_received', 'day_of_week']
        
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400
        
        result = priority_model.predict(data)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/route/optimize', methods=['POST'])
def optimize_route():
    """Optimize delivery route"""
    try:
        data = request.get_json()
        
        if 'delivery_points' not in data:
            return jsonify({'error': 'Missing delivery_points'}), 400
        
        scenario = {
            'delivery_points': data['delivery_points'],
            'traffic_factor': data.get('traffic_factor', 1.0),
            'weather_factor': data.get('weather_factor', 1.0),
            'traffic_level': data.get('traffic_level', 'moderate'),
            'weather_condition': data.get('weather_condition', 'clear')
        }
        
        methods = data.get('methods', ['nearest_neighbor', 'urgent_priority', '2opt', 'q_learning'])
        
        result = route_optimizer.optimize_route(scenario, methods)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/reroute/analyze', methods=['POST'])
def analyze_reroute():
    """Analyze relocation impact"""
    try:
        data = request.get_json()
        
        if 'scenario' not in data or 'relocation' not in data:
            return jsonify({'error': 'Missing required data'}), 400
        
        impact = rerouter.analyze_relocation_impact(
            data['scenario'],
            data['relocation']
        )
        
        return jsonify(impact)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/reroute/execute', methods=['POST'])
def execute_reroute():
    """Execute dynamic rerouting"""
    try:
        data = request.get_json()
        
        if 'scenario' not in data or 'relocations' not in data:
            return jsonify({'error': 'Missing required data'}), 400
        
        result = rerouter.execute_rerouting(
            data['scenario'],
            data['relocations'],
            data.get('method', 'q_learning')
        )
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/relocation/register', methods=['POST'])
def register_relocation():
    """Register new address relocation"""
    try:
        data = request.get_json()
        
        required = ['location_id', 'old_coords', 'new_coords']
        if not all(field in data for field in required):
            return jsonify({'error': 'Missing required fields'}), 400
        
        relocation = rerouter.relocation_tracker.register_relocation(
            data['location_id'],
            tuple(data['old_coords']),
            tuple(data['new_coords']),
            data.get('reason', 'customer_request')
        )
        
        return jsonify(relocation)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api_bp.route('/relocations/active', methods=['GET'])
def get_active_relocations():
    """Get all pending relocations"""
    try:
        relocations = rerouter.relocation_tracker.get_active_relocations()
        return jsonify({'relocations': relocations})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500