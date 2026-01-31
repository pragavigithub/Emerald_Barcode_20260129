#!/usr/bin/env python
import mysql.connector

connection = mysql.connector.connect(
    host='localhost',
    user='root',
    password='root123',
    database='wms_test'
)

cursor = connection.cursor()
cursor.execute("SHOW TABLES LIKE 'delivery%'")
tables = cursor.fetchall()

print("✅ Delivery-related tables:")
for table in tables:
    print(f"   - {table[0]}")

cursor.close()
connection.close()
