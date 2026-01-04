"""
Main Application Entry Point
Smart Postal ML System
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from api import create_app
from config import Config

def main():
    """Main application function"""
    print("=" * 80)
    print("🚀 SMART POSTAL ML SYSTEM")
    print("=" * 80)
    print(f"📁 Project root: {project_root}")
    print(f"🗄️  Database: {Config.DATABASE_PATH}")
    print(f"🤖 Models dir: {Config.MODEL_DIR}")
    print(f"🌐 Server: http://{Config.HOST}:{Config.PORT}")
    print("=" * 80)
    
    # Create necessary directories
    os.makedirs(Config.LOG_DIR, exist_ok=True)
    os.makedirs(Config.PRETRAINED_DIR, exist_ok=True)
    
    # Create Flask app
    app = create_app()
    
    # Run server
    print("\n✅ Starting server...")
    print(f"📡 API available at: http://{Config.HOST}:{Config.PORT}/api")
    print("\nPress Ctrl+C to stop\n")
    
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )

if __name__ == "__main__":
    main()