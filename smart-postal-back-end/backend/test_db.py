"""Test MySQL database connection and check tables"""
import pymysql
import sys

try:
    # Connect to database
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='root',
        database='delivery_system'
    )
    print('✅ Database connection successful!')
    
    # Get cursor
    cursor = conn.cursor()
    
    # Show tables
    cursor.execute('SHOW TABLES;')
    tables = cursor.fetchall()
    print(f'\n📊 Tables found: {len(tables)}')
    for table in tables:
        print(f'  - {table[0]}')
        
        # Count rows in each table
        cursor.execute(f'SELECT COUNT(*) FROM {table[0]}')
        count = cursor.fetchone()[0]
        print(f'    Rows: {count}')
    
    # Check orders table specifically
    print('\n📦 Checking orders table (for voice assistant):')
    cursor.execute('SELECT * FROM orders LIMIT 5')
    orders = cursor.fetchall()
    
    if orders:
        print(f'  Found {len(orders)} sample orders:')
        cursor.execute('DESCRIBE orders')
        columns = cursor.fetchall()
        col_names = [col[0] for col in columns]
        print(f'  Columns: {", ".join(col_names)}')
        
        for order in orders:
            print(f'  - Order ID: {order[0]}')
    else:
        print('  ⚠️  No orders found in database')
    
    conn.close()
    print('\n✅ Database test completed successfully!')
    
except pymysql.err.OperationalError as e:
    print(f'❌ Database connection failed: {e}')
    print('\nPossible issues:')
    print('  1. MySQL service not running')
    print('  2. Wrong password (currently using: root)')
    print('  3. Database "delivery_system" does not exist')
    sys.exit(1)
except Exception as e:
    print(f'❌ Error: {e}')
    sys.exit(1)
