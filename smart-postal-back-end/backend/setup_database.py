"""Create delivery_system database and tables"""
import pymysql

try:
    # Connect without database to create it
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='Roshan@823'
    )
    cursor = conn.cursor()
    
    # Create database
    cursor.execute('CREATE DATABASE IF NOT EXISTS delivery_system')
    print('✅ Database "delivery_system" created successfully!')
    
    # Verify
    cursor.execute('SHOW DATABASES LIKE "delivery_system"')
    result = cursor.fetchone()
    if result:
        print(f'✅ Verified: Database exists')
    
    conn.close()
    
    # Now connect to the database and create tables
    print('\n📊 Creating tables...')
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='Roshan@823',
        database='delivery_system'
    )
    cursor = conn.cursor()
    
    # Check existing tables
    cursor.execute('SHOW TABLES')
    tables = cursor.fetchall()
    print(f'   Found {len(tables)} existing tables')
    
    if len(tables) == 0:
        print('   No tables found. Run create_db.py to create tables.')
    else:
        for table in tables:
            cursor.execute(f'SELECT COUNT(*) FROM {table[0]}')
            count = cursor.fetchone()[0]
            print(f'   - {table[0]}: {count} rows')
    
    conn.close()
    print('\n✅ Database setup complete!')
    print('\nNext steps:')
    print('1. Run: python create_db.py (to create all tables)')
    print('2. Restart your FastAPI server')
    
except pymysql.err.OperationalError as e:
    print(f'❌ Error: {e}')
    if '1045' in str(e):
        print('   Wrong password!')
    print('\nCurrent password in .env: Roshan@823')
