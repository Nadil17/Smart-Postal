"""
MySQL Password Finder - Find your MySQL root password
"""
import os
import re
from pathlib import Path

print("=" * 70)
print("🔐 MYSQL PASSWORD FINDER")
print("=" * 70)

password_found = False
possible_passwords = []

# 1. Check common MySQL config locations
print("\n1️⃣  Checking MySQL configuration files...")
print("-" * 50)

config_locations = [
    Path("C:/ProgramData/MySQL/MySQL Server 8.0/my.ini"),
    Path("C:/ProgramData/MySQL/MySQL Server 8.4/my.ini"),
    Path(os.path.expanduser("~/.my.cnf")),
    Path("C:/Windows/my.ini"),
]

for config_path in config_locations:
    if config_path.exists():
        print(f"   Found config: {config_path}")
        try:
            with open(config_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                if 'password' in content.lower():
                    print(f"   ⚠️  Config contains password reference")
        except Exception as e:
            print(f"   ⚠️  Could not read: {e}")
    else:
        print(f"   ❌ Not found: {config_path}")

# 2. Check MySQL Workbench connections
print("\n2️⃣  Checking MySQL Workbench saved connections...")
print("-" * 50)

workbench_path = Path(os.path.expanduser("~/AppData/Roaming/MySQL/Workbench"))
if workbench_path.exists():
    print(f"   ✅ Workbench directory found: {workbench_path}")
    
    # Look for connection files
    connections_file = workbench_path / "connections.xml"
    if connections_file.exists():
        print(f"   📄 Found connections.xml")
        print("   ⚠️  Passwords are encrypted in Workbench")
    
    # Look for server instances
    servers_file = workbench_path / "server_instances.xml"
    if servers_file.exists():
        print(f"   📄 Found server_instances.xml")
else:
    print("   ❌ MySQL Workbench not installed")

# 3. Manual methods
print("\n3️⃣  MANUAL METHODS TO FIND/RESET PASSWORD:")
print("-" * 50)
print("""
   Method 1: Check if you saved it somewhere
   ------------------------------------------
   - Installation notes/documents
   - Password manager
   - Installation wizard screenshots
   
   Method 2: Reset MySQL password (RECOMMENDED)
   ---------------------------------------------
   1. Stop MySQL service:
      net stop MySQL80
   
   2. Start MySQL without password check:
      cd "C:\\Program Files\\MySQL\\MySQL Server 8.0\\bin"
      mysqld --skip-grant-tables --shared-memory
   
   3. Open NEW terminal and connect:
      mysql -u root
   
   4. Reset password:
      FLUSH PRIVILEGES;
      ALTER USER 'root'@'localhost' IDENTIFIED BY 'your_new_password';
      FLUSH PRIVILEGES;
      EXIT;
   
   5. Stop mysqld and restart service normally:
      net start MySQL80
   
   Method 3: Try phpMyAdmin (if installed)
   ----------------------------------------
   Check if you have XAMPP or WAMP installed
   They often have default root password: '' (empty) or 'root'
   
   Method 4: Check your project documentation
   -------------------------------------------
   Look for setup guides, README files in:
   - Smart-Postal project folder
   - Any database setup scripts
""")

print("\n4️⃣  AFTER FINDING PASSWORD:")
print("-" * 50)
print("""
   1. Update .env file:
      📁 smart-postal-back-end/backend/config/.env
      
      Change line:
      DATABASE_URL=mysql+pymysql://root:root@localhost:3306/delivery_system
      
      To:
      DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost:3306/delivery_system
   
   2. Create database if it doesn't exist:
      CREATE DATABASE delivery_system;
   
   3. Run migrations to create tables:
      cd backend
      python create_db.py
   
   4. Restart the FastAPI server
""")

print("\n5️⃣  CURRENT VOICE ASSISTANT STATUS:")
print("-" * 50)
print("""
   ✅ Voice assistant works WITHOUT database
   ✅ Using mock_db.json (5 test tracking numbers)
   ✅ Perfect for testing and demo
   
   To connect voice assistant to MySQL later:
   - I can help you modify courier_bot.py
   - Will query orders table instead of mock_db.json
   - Need database password first
""")

print("\n" + "=" * 70)
print("💡 TIP: For now, voice assistant works perfectly with mock data!")
print("   Test it first, then worry about MySQL connection.")
print("=" * 70)
