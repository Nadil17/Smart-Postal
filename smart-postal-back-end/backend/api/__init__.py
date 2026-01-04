"""
API package - REST endpoints
"""
from flask import Flask
from flask_cors import CORS

def create_app():
    """Application factory"""
    app = Flask(__name__)
    CORS(app)
    
    from .routes import api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    return app