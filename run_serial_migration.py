#!/usr/bin/env python
import mysql.connector
from mysql.connector import Error

try:
    connection = mysql.connector.connect(
        host='localhost',
        user='root',
        password='root123',
        database='wms_test'
    )
    
    cursor = connection.cursor()
    
    print("📋 Running: Serial Allocation Migration")
    
    # Read migration file
    with open('migrations/mysql/changes/2026-01-31_sales_delivery_serial_allocation.sql', 'r') as f:
        sql_script = f.read()
    
    # Execute the migration
    for statement in sql_script.split(';'):
        statement = statement.strip()
        if statement and not statement.startswith('--'):
            try:
                cursor.execute(statement)
                try:
                    cursor.fetchall()
                except:
                    pass
            except Error as e:
                if 'already exists' in str(e):
                    print(f"   ⚠️  Table already exists")
                else:
                    raise
    
    connection.commit()
    print("   ✅ Migration completed")
    
    # Verify table
    cursor.execute("SHOW TABLES LIKE 'delivery_item_serials'")
    result = cursor.fetchone()
    if result:
        print("\n✅ Table created successfully: delivery_item_serials")
        
        # Show table structure
        cursor.execute("DESCRIBE delivery_item_serials")
        columns = cursor.fetchall()
        print("\n✅ Table Structure:")
        for col in columns:
            print(f"   - {col[0]}: {col[1]}")
    else:
        print("❌ Table not found")
    
    cursor.close()
    connection.close()
    
except Error as e:
    print(f'❌ Error: {e}')
except Exception as e:
    print(f'❌ Unexpected error: {e}')
