"""
Application configuration
"""
import os
from pathlib import Path

class Config:
    """Application configuration"""
    
    # Base directory
    BASE_DIR = Path(__file__).resolve().parent.parent
    
    # Database
    DATABASE_PATH = os.path.join(BASE_DIR, 'delivery_system.db')
    
    # Models
    MODEL_DIR = os.path.join(BASE_DIR, 'models')
    PRETRAINED_DIR = os.path.join(BASE_DIR, 'pretrained_models')
    
    # Logging
    LOG_DIR = os.path.join(BASE_DIR, 'logs')
    LOG_FILE = os.path.join(LOG_DIR, 'postal_ml.log')
    
    # Flask
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 5000
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # ML Parameters
    RANDOM_SEED = 42
    
    # Route Optimization
    DEFAULT_AVG_SPEED_KMH = 25
    DEFAULT_SERVICE_TIME_MIN = 5
    Q_LEARNING_EPISODES = 500
    
    # Fuel Consumption
    BASE_FUEL_CONSUMPTION_PER_KM = 0.12
    IDLE_FUEL_PER_HOUR = 0.8
    FUEL_TANK_CAPACITY = 50
    FUEL_LOW_THRESHOLD = 0.2  # 20%