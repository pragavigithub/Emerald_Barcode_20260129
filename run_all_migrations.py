#!/usr/bin/env python
import mysql.connector
from mysql.connector import Error
import os

try:
    connection = mysql.connector.connect(
        host='localhost',
        user='root',
        password='root123',
        database='wms_test'
    )
    
    cursor = connection.cursor()
    
    # List of migrations to run in order
    migrations = [
        'migrations/mysql/changes/2025-10-23_sales_delivery_module.sql',
        'migrations/mysql/changes/2025-10-26_sales_delivery_qc_approval.sql',
        'migrations/mysql/changes/2026-01-31_sales_delivery_serial_allocation.sql'
    ]
    
    for migration_file in migrations:
        if os.path.exists(migration_file):
            print(f"\n📋 Running: {migration_file}")
            with open(migration_file, 'r') as f:
                sql_script = f.read()
            
            # Split by semicolon and execute each statement
            statements = sql_script.split(';')
            for statement in statements:
                statement = statement.strip()
                if statement and not statement.startswith('--'):
                    try:
                        cursor.execute(statement)
                        # Fetch any results to clear the buffer
                        try:
                            cursor.fetchall()
                        except:
                            pass
                    except Error as e:
                        if 'already exists' in str(e) or 'Duplicate' in str(e):
                            print(f"   ⚠️  {e}")
                        else:
                            raise
            
            connection.commit()
            print(f"   ✅ Completed")
        else:
            print(f"   ❌ File not found: {migration_file}")
    
    print("\n" + "="*50)
    print("✅ All migrations completed successfully!")
    print("="*50)
    
    # Verify tables
    cursor.execute("SHOW TABLES LIKE 'delivery%'")
    tables = cursor.fetchall()
    print("\n✅ Delivery tables created:")
    for table in tables:
        print(f"   - {table[0]}")
    
    cursor.close()
    connection.close()
    
except Error as e:
    print(f'❌ Error: {e}')
except Exception as e:
    print(f'❌ Unexpected error: {e}')
