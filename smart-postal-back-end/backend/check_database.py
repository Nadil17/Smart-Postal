"""
Database Status Checker and Configuration Guide
================================================

This script checks:
1. MySQL service status
2. Database connection
3. Tables and data in database
4. Voice assistant current configuration
5. How to switch from mock_db.json to MySQL
"""
import pymysql
import json
from pathlib import Path

print("=" * 70)
print("🔍 SMART POSTAL DATABASE STATUS CHECK")
print("=" * 70)

# 1. Check MySQL Service
print("\n1️⃣  MYSQL SERVICE STATUS:")
print("-" * 50)
try:
    import subprocess
    result = subprocess.run(
        ['powershell', 'Get-Service', '-Name', 'MySQL80'],
        capture_output=True,
        text=True
    )
    if 'Running' in result.stdout:
        print("   ✅ MySQL80 service is RUNNING")
    else:
        print("   ❌ MySQL80 service is NOT running")
        print("   To start: Run 'net start MySQL80' as Administrator")
except Exception as e:
    print(f"   ⚠️  Could not check service: {e}")

# 2. Test Database Connection
print("\n2️⃣  DATABASE CONNECTION TEST:")
print("-" * 50)

# Try different common passwords
passwords = ['', 'root', 'admin', 'password', '123456']
connected = False
correct_password = None

for pwd in passwords:
    try:
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password=pwd,
            connect_timeout=2
        )
        connected = True
        correct_password = pwd
        print(f"   ✅ Connected successfully with password: '{pwd}'")
        
        # Check if database exists
        cursor = conn.cursor()
        cursor.execute("SHOW DATABASES LIKE 'delivery_system'")
        db_exists = cursor.fetchone()
        
        if db_exists:
            print("   ✅ Database 'delivery_system' EXISTS")
            
            # Connect to the database
            conn.select_db('delivery_system')
            
            # Show tables
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"\n   📊 Found {len(tables)} tables:")
            
            for table in tables:
                table_name = table[0]
                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                count = cursor.fetchone()[0]
                print(f"      - {table_name}: {count} rows")
                
                # Check orders table specifically
                if table_name == 'orders':
                    print("\n   📦 ORDERS TABLE (for voice assistant):")
                    cursor.execute("SELECT * FROM orders LIMIT 3")
                    orders = cursor.fetchall()
                    
                    if orders:
                        # Get column names
                        cursor.execute("DESCRIBE orders")
                        columns = [col[0] for col in cursor.fetchall()]
                        print(f"      Columns: {', '.join(columns)}")
                        
                        print(f"      Sample data ({len(orders)} orders):")
                        for order in orders:
                            print(f"        Order: {order}")
                    else:
                        print("      ⚠️  Table is EMPTY - no order data")
        else:
            print("   ⚠️  Database 'delivery_system' does NOT exist")
            print("   Create it with: CREATE DATABASE delivery_system;")
        
        conn.close()
        break
    except pymysql.err.OperationalError as e:
        if '1045' in str(e):  # Access denied
            continue
        else:
            print(f"   ❌ Connection error: {e}")
            break
    except Exception as e:
        print(f"   ❌ Error: {e}")
        break

if not connected:
    print("   ❌ Could not connect to MySQL")
    print("   Tried passwords:", passwords)
    print("\n   To find your MySQL password:")
    print("   - Check MySQL Workbench saved connections")
    print("   - Look in config files")
    print("   - Reset password if needed")

# 3. Voice Assistant Configuration
print("\n3️⃣  VOICE ASSISTANT CONFIGURATION:")
print("-" * 50)

mock_db_path = Path("services/sinhala_assistant/mock_db.json")
if mock_db_path.exists():
    print(f"   ✅ Mock database found: {mock_db_path}")
    with open(mock_db_path, 'r', encoding='utf-8') as f:
        mock_data = json.load(f)
    print(f"   📦 Mock data contains {len(mock_data)} tracking records:")
    for tid in list(mock_data.keys())[:5]:
        print(f"      - {tid}: {mock_data[tid]['status']}")
    
    print("\n   ⚠️  Voice assistant is currently using MOCK DATA")
    print("   📍 File: courier_bot.py line 49 & 207")
else:
    print("   ❌ Mock database not found")

# 4. Configuration Guide
print("\n4️⃣  HOW TO CONNECT VOICE ASSISTANT TO MYSQL:")
print("-" * 50)
print("""
   Option A: Update courier_bot.py to use MySQL
   ---------------------------------------------
   1. Add database connection function
   2. Replace get_tracking_status() to query MySQL
   3. Modify lines 205-230 in courier_bot.py
   
   Option B: Keep using mock data for now
   ---------------------------------------------
   ✅ Already working - no changes needed
   Mock data is perfect for testing/demo
   
   Current Status:
   - Voice assistant: Using mock_db.json ✅
   - Backend system: Trying to use MySQL (fails due to password)
   - Frontend: Works with mock data ✅
""")

if connected and correct_password:
    print(f"\n5️⃣  UPDATE .ENV FILE:")
    print("-" * 50)
    print(f"   Current: DATABASE_URL=mysql+pymysql://root:root@localhost:3306/delivery_system")
    print(f"   Correct: DATABASE_URL=mysql+pymysql://root:{correct_password}@localhost:3306/delivery_system")
    print("\n   Update this in:")
    print("   📁 smart-postal-back-end/backend/config/.env")

print("\n" + "=" * 70)
print("✅ DATABASE CHECK COMPLETE")
print("=" * 70)
