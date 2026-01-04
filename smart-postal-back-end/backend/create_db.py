"""
Database initialization script
"""
import sqlite3
import os
from config import Config

def create_database():
    """Create the delivery system database"""
    
    db_path = Config.DATABASE_PATH
    
    if os.path.exists(db_path):
        print(f"⚠️  Database already exists: {db_path}")
        response = input("Do you want to recreate it? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Aborted")
            return
        os.remove(db_path)
    
    print(f"🔨 Creating database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Routes table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS routes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            route_name TEXT,
            route_data TEXT,
            total_distance REAL,
            total_time REAL,
            total_fuel REAL,
            optimization_method TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Relocations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS relocations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            relocation_id TEXT UNIQUE,
            location_id INTEGER,
            old_latitude REAL,
            old_longitude REAL,
            new_latitude REAL,
            new_longitude REAL,
            distance_change REAL,
            reason TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Priority predictions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS priority_predictions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mail_id TEXT,
            mail_type TEXT,
            sender_type TEXT,
            recipient_type TEXT,
            predicted_priority TEXT,
            confidence REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Delivery scenarios table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS delivery_scenarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scenario_name TEXT,
            num_points INTEGER,
            traffic_level TEXT,
            weather_condition TEXT,
            scenario_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    
    print("✅ Database created successfully!")
    print("\nTables created:")
    print("  • routes")
    print("  • relocations")
    print("  • priority_predictions")
    print("  • delivery_scenarios")

if __name__ == "__main__":
    create_database()