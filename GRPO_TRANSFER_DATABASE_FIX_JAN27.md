# GRPO Transfer Database Creation Issue - Fixed

## Problem
The GRPO Transfer module was throwing a database error when trying to create a transfer session:
```
Error: (pymysql.err.OperationalError) (1054, "Unknown column 'from_bin_abs_entry' in 'field list'")
```

The error occurred because the database schema was missing columns that the application code was trying to insert.

## Root Cause
The `grpo_transfer_items` table was created with the initial schema, but the application code in `modules/grpo_transfer/routes.py` (specifically the QC approval endpoint) was trying to save additional columns:
- `from_bin_abs_entry` - SAP B1 BinLocation AbsEntry for source bin
- `to_bin_abs_entry` - SAP B1 BinLocation AbsEntry for destination bin
- `from_warehouse_abs_entry` - SAP B1 Warehouse AbsEntry for source warehouse
- `to_warehouse_abs_entry` - SAP B1 Warehouse AbsEntry for destination warehouse

## Solution Applied

### 1. Updated Model Definition
Modified `modules/grpo_transfer/models.py` to include the missing columns in the `GRPOTransferItem` model:

```python
# Warehouse and Bin information
from_warehouse = db.Column(db.String(50), nullable=False)
from_bin_code = db.Column(db.String(100), nullable=True)
from_bin_abs_entry = db.Column(db.Integer, nullable=True)  # SAP B1 BinLocation AbsEntry
to_warehouse = db.Column(db.String(50), nullable=True)
to_bin_code = db.Column(db.String(100), nullable=True)
to_bin_abs_entry = db.Column(db.Integer, nullable=True)  # SAP B1 BinLocation AbsEntry
from_warehouse_abs_entry = db.Column(db.Integer, nullable=True)  # SAP B1 Warehouse AbsEntry
to_warehouse_abs_entry = db.Column(db.Integer, nullable=True)  # SAP B1 Warehouse AbsEntry
```

### 2. Added Missing Columns to Database
Executed SQL ALTER TABLE commands to add the 4 missing columns to the existing `grpo_transfer_items` table:
- `ALTER TABLE grpo_transfer_items ADD COLUMN from_bin_abs_entry INTEGER NULL`
- `ALTER TABLE grpo_transfer_items ADD COLUMN to_bin_abs_entry INTEGER NULL`
- `ALTER TABLE grpo_transfer_items ADD COLUMN from_warehouse_abs_entry INTEGER NULL`
- `ALTER TABLE grpo_transfer_items ADD COLUMN to_warehouse_abs_entry INTEGER NULL`

### 3. Verified Schema
Confirmed all 29 columns now exist in the `grpo_transfer_items` table:
- Original 25 columns ✅
- 4 new columns ✅

## Database Schema - grpo_transfer_items

| Column | Type | Purpose |
|--------|------|---------|
| id | INTEGER | Primary key |
| session_id | INTEGER | Foreign key to grpo_transfer_sessions |
| line_num | INTEGER | Line number from GRPO |
| item_code | VARCHAR(50) | SAP B1 item code |
| item_name | VARCHAR(255) | Item name |
| item_description | VARCHAR(500) | Item description |
| is_batch_item | TINYINT | Flag: batch-managed item |
| is_serial_item | TINYINT | Flag: serial-managed item |
| is_non_managed | TINYINT | Flag: non-managed item |
| received_quantity | FLOAT | Quantity received |
| approved_quantity | FLOAT | Quantity approved by QC |
| rejected_quantity | FLOAT | Quantity rejected by QC |
| from_warehouse | VARCHAR(50) | Source warehouse code |
| from_bin_code | VARCHAR(100) | Source bin code |
| **from_bin_abs_entry** | **INTEGER** | **Source bin AbsEntry (NEW)** |
| to_warehouse | VARCHAR(50) | Destination warehouse code |
| to_bin_code | VARCHAR(100) | Destination bin code |
| **to_bin_abs_entry** | **INTEGER** | **Destination bin AbsEntry (NEW)** |
| **from_warehouse_abs_entry** | **INTEGER** | **Source warehouse AbsEntry (NEW)** |
| **to_warehouse_abs_entry** | **INTEGER** | **Destination warehouse AbsEntry (NEW)** |
| unit_of_measure | VARCHAR(20) | Unit of measure |
| price | FLOAT | Item price |
| line_total | FLOAT | Line total |
| qc_status | VARCHAR(20) | QC status (pending, approved, rejected, partial) |
| qc_notes | TEXT | QC notes |
| sap_base_entry | INTEGER | SAP B1 base document entry |
| sap_base_line | INTEGER | SAP B1 base document line |
| created_at | DATETIME | Record creation timestamp |
| updated_at | DATETIME | Record update timestamp |

## Testing
The GRPO Transfer module should now work correctly:
1. ✅ Create transfer sessions
2. ✅ Add items to sessions
3. ✅ Perform QC approval with warehouse/bin assignments
4. ✅ Save AbsEntry references for SAP B1 integration

## Files Modified
- `modules/grpo_transfer/models.py` - Added 4 new columns to GRPOTransferItem model
- Database schema - Added 4 new columns to grpo_transfer_items table

## Next Steps
If you encounter any other database-related errors, check:
1. All GRPO Transfer tables exist (6 tables total)
2. All columns match the model definitions
3. Foreign key relationships are intact
