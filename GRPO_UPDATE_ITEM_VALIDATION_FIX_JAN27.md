# GRPO Transfer - Update Item Validation Fix

## Problem
When editing line items, the item type was NOT being validated. Items were being updated without checking if they are batch-managed or not. This caused:
- Batch items to display as "Non-Managed" after editing
- Batch numbers not being fetched or stored
- Incorrect item type in the grid

**Example Issue:**
```
Before Edit:
Row 3: BOM_Item_1 → Type: "Batch" ✅

After Edit (without validation):
Row 3: BOM_Item_1 → Type: "Non-Managed" ❌ (Should still be "Batch")
```

## Root Cause
The `update_item` endpoint was only updating fields without validating the item type or fetching batch numbers. It was missing the validation logic that should happen when warehouses are set.

## Solution
Enhanced the `update_item` endpoint to:
1. Validate item type when warehouse is being set
2. Fetch batch numbers if item is batch-managed
3. Store batch records in database
4. Update item type flags
5. Return updated item data

## Implementation

### Updated Endpoint
```
PUT /api/item/<item_id>
```

### Request Body
```json
{
    "to_warehouse": "7000-QFG",
    "from_warehouse": "7000-FG",
    "approved_quantity": 300,
    "rejected_quantity": 700,
    "qc_status": "approved",
    "qc_notes": "QC approved"
}
```

### Response
```json
{
    "success": true,
    "message": "Item updated successfully",
    "item": {
        "id": 3,
        "item_code": "BOM_Item_1",
        "is_batch_item": true,
        "is_serial_item": false,
        "is_non_managed": false,
        "approved_quantity": 300,
        "rejected_quantity": 700,
        "to_warehouse": "7000-QFG",
        "from_warehouse": "7000-FG"
    }
}
```

## Workflow

```
User clicks "Edit" on line item
    ↓
Edit Modal opens
    ↓
User selects warehouse and quantities
    ↓
User clicks "Save Changes"
    ↓
PUT /api/item/<item_id> called
    ↓
Backend:
├─ Check if warehouse is being set
├─ If yes:
│  ├─ Validate item type via SAP API
│  ├─ Update item type flags
│  ├─ If batch item:
│  │  ├─ Fetch batch numbers via SAP API
│  │  ├─ Delete old batch records
│  │  └─ Create new batch records
│  └─ If non-batch item:
│     └─ Delete any existing batch records
├─ Update item fields (quantities, warehouse, etc.)
├─ Commit to database
└─ Return updated item data
    ↓
Frontend updates grid with new item type
    ↓
Grid displays correct item type and batch status
```

## Code Changes

### Step 1: Validate Item Type
```python
# Call SAP query to validate item type
val_url = f"{sap.base_url}/b1s/v1/SQLQueries('ItemCode_Batch_Serial_Val')/List"
val_payload = {"ParamList": f"itemCode='{item.item_code}'"}

val_response = sap.session.post(val_url, json=val_payload, headers=val_headers, timeout=30)

if val_response.status_code == 200:
    val_data = val_response.json()
    val_items = val_data.get('value', [])
    
    if val_items:
        val_info = val_items[0]
        is_batch = val_info.get('BatchNum') == 'Y'
        is_serial = val_info.get('SerialNum') == 'Y'
        
        # Update item type flags
        item.is_batch_item = is_batch
        item.is_serial_item = is_serial
        item.is_non_managed = not is_batch and not is_serial
```

### Step 2: Fetch Batch Numbers (If Batch Item)
```python
if is_batch:
    # Use the batch details API
    batch_url = f"{sap.base_url}/b1s/v1/SQLQueries('Get_Batch_By_DocEntry_ItemCode')/List"
    
    # Build parameter list with docEntry, itemCode, and lineNum
    param_list = f"docEntry='{item.sap_base_entry}'&itemCode='{item.item_code}'&lineNum='{item.sap_base_line}'"
    batch_payload = {"ParamList": param_list}
    
    batch_response = sap.session.post(batch_url, json=batch_payload, headers=batch_headers, timeout=30)
    
    if batch_response.status_code == 200:
        batch_data = batch_response.json()
        batches = batch_data.get('value', [])
        
        # Delete existing batch records
        GRPOTransferBatch.query.filter_by(item_id=item.id).delete()
        
        # Create new batch records
        for batch_info in batches:
            batch = GRPOTransferBatch()
            batch.item_id = item.id
            batch.batch_number = batch_info.get('BatchNum')
            batch.batch_quantity = float(batch_info.get('Quantity', 0))
            batch.approved_quantity = 0
            batch.rejected_quantity = 0
            batch.qc_status = 'pending'
            # ... parse dates
            db.session.add(batch)
```

### Step 3: Update Item Fields
```python
if 'approved_quantity' in data:
    item.approved_quantity = float(data['approved_quantity'])
if 'rejected_quantity' in data:
    item.rejected_quantity = float(data['rejected_quantity'])
if 'qc_status' in data:
    item.qc_status = data['qc_status']
if 'qc_notes' in data:
    item.qc_notes = data['qc_notes']
if 'to_warehouse' in data:
    item.to_warehouse = data['to_warehouse']
if 'from_warehouse' in data:
    item.from_warehouse = data['from_warehouse']
# ... other fields
```

## Database Updates

### grpo_transfer_items
- `is_batch_item` - Updated based on SAP validation
- `is_serial_item` - Updated based on SAP validation
- `is_non_managed` - Updated based on SAP validation
- `to_warehouse` - Set from request
- `from_warehouse` - Set from request
- `approved_quantity` - Set from request
- `rejected_quantity` - Set from request
- `qc_status` - Set from request

### grpo_transfer_batches
- Old records deleted
- New records created for batch items
- Fields: batch_number, batch_quantity, expiry_date, manufacture_date

### grpo_transfer_logs
- New audit entry created
- Action: 'item_updated'
- Includes item type and quantities

## Expected Results

### Before Fix
```
Grid Display:
Row 0: BOM_Item_1 | Batch         | 1000.0 | 0.0   | 0.0
Row 1: BOM_Item_2 | Batch         | 1000.0 | 0.0   | 0.0
Row 2: BOM_Item_3 | Non-Managed   | 1000.0 | 0.0   | 0.0
Row 3: BOM_Item_1 | Non-Managed   | 1000.0 | 300.0 | 700.0  ❌ (Should be Batch)
Row 4: BOM_Item_2 | Non-Managed   | 1000.0 | 0.0   | 0.0    ❌ (Should be Batch)
Row 5: BOM_Item_3 | Non-Managed   | 1000.0 | 0.0   | 0.0
```

### After Fix
```
Grid Display:
Row 0: BOM_Item_1 | Batch         | 1000.0 | 0.0   | 0.0
Row 1: BOM_Item_2 | Batch         | 1000.0 | 0.0   | 0.0
Row 2: BOM_Item_3 | Non-Managed   | 1000.0 | 0.0   | 0.0
Row 3: BOM_Item_1 | Batch         | 1000.0 | 300.0 | 700.0  ✅ (Correct)
Row 4: BOM_Item_2 | Batch         | 1000.0 | 0.0   | 0.0    ✅ (Correct)
Row 5: BOM_Item_3 | Non-Managed   | 1000.0 | 0.0   | 0.0
```

## Logging

### Log Messages
```
✅ Item BOM_Item_1 validated - Batch: True, Serial: False, Non-Managed: False
✅ Retrieved 1 batch numbers for item BOM_Item_1
✅ Added batch 20251212-BOM_Item_1 for item BOM_Item_1 with qty 1000.0
✅ Updated item 3
```

### Audit Trail
```
action: 'item_updated'
description: 'Updated item BOM_Item_1 (line 3): Type=Batch, approved=300, rejected=700, status=approved'
user_id: <current_user_id>
session_id: <session_id>
```

## Error Handling

### Scenarios
1. **Item not found**: Return 404
2. **SAP authentication failed**: Return error
3. **Item not in SAP B1**: Mark as non-managed, continue
4. **Batch fetch failed**: Log warning, continue
5. **Invalid warehouse**: Update still proceeds

### Error Response
```json
{
    "success": false,
    "error": "Error message"
}
```

## Testing Checklist

- [ ] Edit batch item, select warehouse
- [ ] Verify item type updates to "Batch"
- [ ] Verify batch numbers fetched and stored
- [ ] Verify grid displays "Batch" badge
- [ ] Edit non-batch item, select warehouse
- [ ] Verify item type updates to "Non-Managed"
- [ ] Verify no batch numbers appear
- [ ] Edit item, change quantities
- [ ] Verify quantities updated in grid
- [ ] Check database for batch records
- [ ] Check audit logs for validation entry
- [ ] Test error scenarios

## Performance

- **API Calls**: 2 per update (item validation + batch fetch)
- **Database Operations**: Delete + insert batch records
- **Timeout**: 30 seconds per API call
- **Impact**: Minimal (only when warehouse is set)

## Backward Compatibility

✅ Existing sessions: No impact
✅ New sessions: Use new validation on update
✅ Database: No schema changes
✅ API: Enhanced response, backward compatible

## Files Modified

- `modules/grpo_transfer/routes.py` - Enhanced `update_item()` endpoint (lines ~1264-1380)

## Key Improvements

1. **Item Type Validation**: Validates on every update
2. **Batch Number Retrieval**: Fetches fresh batch data
3. **Database Consistency**: Batch records created/updated
4. **User Feedback**: Returns updated item data
5. **Error Handling**: Graceful error handling
6. **Audit Trail**: Logs all validations

## Summary

The `update_item` endpoint now properly validates items and fetches batch numbers when editing line items. This ensures that:
- Item types are correctly identified
- Batch numbers are retrieved and stored
- Grid displays correct item type badges
- Database remains consistent
- All changes are audited

This fix resolves the issue where batch items were incorrectly displayed as "Non-Managed" after editing.
