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
    
    # Read and execute migration
    with open('migrations/mysql/changes/2026-01-31_sales_delivery_serial_allocation.sql', 'r') as f:
        sql_script = f.read()
    
    for statement in sql_script.split(';'):
        if statement.strip():
            cursor.execute(statement)
    
    connection.commit()
    print('✅ Migration completed successfully!')
    print('✅ Table delivery_item_serials created')
    
    # Verify table
    cursor.execute('SHOW TABLES LIKE "delivery_item_serials"')
    result = cursor.fetchone()
    if result:
        print('✅ Table verified in database')
        
        # Check table structure
        cursor.execute('DESCRIBE delivery_item_serials')
        columns = cursor.fetchall()
        print('\n✅ Table Structure:')
        for col in columns:
            print(f'   - {col[0]}: {col[1]}')
    
    cursor.close()
    connection.close()
    
except Error as e:
    print(f'❌ Error: {e}')
except Exception as e:
    print(f'❌ Unexpected error: {e}')
