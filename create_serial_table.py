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
    
    print("📋 Creating delivery_item_serials table...")
    
    sql = """
    CREATE TABLE IF NOT EXISTS delivery_item_serials (
        id INT AUTO_INCREMENT PRIMARY KEY,
        delivery_item_id INT NOT NULL,
        internal_serial_number VARCHAR(100) NOT NULL,
        system_serial_number INT,
        quantity FLOAT DEFAULT 1.0,
        base_line_number INT NOT NULL,
        allocation_status VARCHAR(20) DEFAULT 'allocated',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        
        FOREIGN KEY (delivery_item_id) REFERENCES delivery_items(id) ON DELETE CASCADE,
        INDEX idx_serial_number (internal_serial_number),
        INDEX idx_delivery_item (delivery_item_id),
        INDEX idx_allocation_status (allocation_status)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """
    
    cursor.execute(sql)
    connection.commit()
    print("✅ Table created successfully!")
    
    # Verify
    cursor.execute("SHOW TABLES LIKE 'delivery_item_serials'")
    result = cursor.fetchone()
    if result:
        print(f"✅ Verified: {result[0]} table exists")
        
        # Show structure
        cursor.execute("DESCRIBE delivery_item_serials")
        columns = cursor.fetchall()
        print("\n✅ Table Structure:")
        for col in columns:
            print(f"   {col[0]:25} {col[1]:20} {col[2]:5} {col[3]:5} {col[4]:20} {col[5]}")
    
    cursor.close()
    connection.close()
    
except Error as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f'❌ Unexpected error: {e}')
    import traceback
    traceback.print_exc()
