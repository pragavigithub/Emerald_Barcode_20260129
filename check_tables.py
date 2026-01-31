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
    
    # Check if delivery_documents table exists
    cursor.execute("SHOW TABLES LIKE 'delivery%'")
    tables = cursor.fetchall()
    
    print("Delivery-related tables:")
    if tables:
        for table in tables:
            print(f"  ✅ {table[0]}")
    else:
        print("  ❌ No delivery tables found")
    
    # List all tables
    cursor.execute("SHOW TABLES")
    all_tables = cursor.fetchall()
    print(f"\nTotal tables in database: {len(all_tables)}")
    
    cursor.close()
    connection.close()
    
except Error as e:
    print(f'❌ Error: {e}')
except Exception as e:
    print(f'❌ Unexpected error: {e}')
