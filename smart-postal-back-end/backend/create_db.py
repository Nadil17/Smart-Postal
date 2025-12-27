import pymysql

try:
    # Connect to MySQL server without specifying a database
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password='Roshan@823',
        port=3306
    )
    
    cursor = connection.cursor()
    
    # Create database if it doesn't exist
    cursor.execute("CREATE DATABASE IF NOT EXISTS delivery_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    
    print("✅ Database 'delivery_system' created successfully!")
    
    cursor.close()
    connection.close()
    
except pymysql.Error as e:
    print(f"❌ MySQL Error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
