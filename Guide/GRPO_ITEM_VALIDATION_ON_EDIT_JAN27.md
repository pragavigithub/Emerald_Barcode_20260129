# GRPO Transfer - Item Validation on Edit Feature

## Overview
Implemented a new feature that validates items and fetches batch details **during the edit process**, specifically when the user selects the "To Warehouse". This ensures accurate item type detection and batch number retrieval at the point of warehouse assignment.

## Problem Solved
Previously, item validation happened only during session creation, which could miss items or incorrectly classify them. Now validation happens when the user explicitly edits an item and assigns a warehouse, ensuring real-time accuracy.

## New API Endpoint

### Endpoint
```
POST /api/item/<item_id>/validate-and-fetch-batches
```

### Purpose
Validate item type and fetch batch details when editing an item in the modal.

### Request
```json
{
    "to_warehouse": "7000-QFG"
}
```

### Response (Success)
```json
{
    "success": true,
    "item_code": "BOM_Item_1",
    "is_batch_item": true,
    "is_serial_item": false,
    "is_non_managed": false,
    "batches": [
        {
            "batch_number": "20251212-BOM_Item_1",
            "batch_quantity": 1000.0,
            "expiry_date": "2027-01-08",
            "manufacture_date": "2025-12-12"
        }
    ],
    "message": "Item validated successfully. Found 1 batch numbers."
}
```

### Response (Non-Batch Item)
```json
{
    "success": true,
    "item_code": "BOM_Item_3",
    "is_batch_item": false,
    "is_serial_item": false,
    "is_non_managed": true,
    "batches": [],
    "message": "Item is non-batch managed."
}
```

## Implementation Details

### Step 1: Item Type Validation
**API Used:** `ItemCode_Batch_Serial_Val`

```
Endpoint: /b1s/v1/SQLQueries('ItemCode_Batch_Serial_Val')/List
Method: POST
Request Body: {"ParamList": "itemCode='BOM_Item_1'"}
```

**Returns:**
- `BatchNum`: 'Y' or 'N' (indicates if item is batch-managed)
- `SerialNum`: 'Y' or 'N' (indicates if item is serial-managed)

**Processing:**
```python
is_batch = val_info.get('BatchNum') == 'Y'
is_serial = val_info.get('SerialNum') == 'Y'
is_non_managed = not is_batch and not is_serial

# Update item flags in database
item.is_batch_item = is_batch
item.is_serial_item = is_serial
item.is_non_managed = is_non_managed
```

### Step 2: Batch Details Retrieval (If Batch Item)
**API Used:** `Get_Batch_By_DocEntry_ItemCode`

```
Endpoint: /b1s/v1/SQLQueries('Get_Batch_By_DocEntry_ItemCode')/List
Method: POST
Request Body: {
    "ParamList": "docEntry='7839'&itemCode='BOM_Item_1'&lineNum='0'"
}
```

**Parameters:**
- `docEntry`: GRPO document entry (from `item.sap_base_entry`)
- `itemCode`: Item code (from `item.item_code`)
- `lineNum`: Line number (from `item.sap_base_line`)

**Returns:**
- `BatchNum`: Batch number
- `Quantity`: Batch quantity
- `ExpDate`: Expiry date (format: YYYYMMDD)
- `MnfDate`: Manufacture date (format: YYYYMMDD)

### Step 3: Store Batch Records
```python
# Delete existing batch records (if any)
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
    batch.expiry_date = parse_date(batch_info.get('ExpDate'))
    batch.manufacture_date = parse_date(batch_info.get('MnfDate'))
    
    db.session.add(batch)

db.session.commit()
```

## Workflow

```
User clicks "Edit" on line item
    ↓
Edit Modal opens
    ↓
User selects "To Warehouse"
    ↓
JavaScript calls: POST /api/item/<item_id>/validate-and-fetch-batches
    ↓
Backend validates item type
    ↓
If batch item:
    ├─ Fetch batch details from SAP
    ├─ Delete old batch records
    ├─ Create new batch records
    └─ Return batch list
    ↓
If non-batch item:
    └─ Return empty batch list
    ↓
Frontend displays:
    ├─ Item type badge (Batch/Serial/Non-Managed)
    ├─ Batch numbers (if batch item)
    └─ Batch details (quantity, expiry, manufacture date)
    ↓
User approves/rejects quantities
    ↓
User saves changes
```

## Database Changes

### grpo_transfer_items Table
Updated fields:
- `is_batch_item` - Set during validation
- `is_serial_item` - Set during validation
- `is_non_managed` - Set during validation
- `to_warehouse` - Set when user selects warehouse

### grpo_transfer_batches Table
Records created/updated:
- `batch_number` - From SAP batch query
- `batch_quantity` - From SAP batch query
- `expiry_date` - Parsed from SAP response
- `manufacture_date` - Parsed from SAP response
- `qc_status` - Set to 'pending'

## Frontend Integration

### JavaScript Call
```javascript
// When user selects "To Warehouse"
async function validateItemAndFetchBatches(itemId, toWarehouse) {
    const response = await fetch(`/api/item/${itemId}/validate-and-fetch-batches`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            to_warehouse: toWarehouse
        })
    });
    
    const data = await response.json();
    
    if (data.success) {
        // Update UI with item type
        updateItemTypeDisplay(data.is_batch_item, data.is_serial_item, data.is_non_managed);
        
        // Display batch numbers if batch item
        if (data.is_batch_item && data.batches.length > 0) {
            displayBatchNumbers(data.batches);
        }
    } else {
        showError(data.error);
    }
}
```

## Error Handling

### Possible Errors
1. **Item not found**: Item doesn't exist in database
2. **SAP authentication failed**: Session expired
3. **Item not in SAP B1**: Item code doesn't exist in SAP
4. **Batch fetch failed**: SAP API error

### Error Responses
```json
{
    "success": false,
    "error": "Item not found"
}
```

## Logging

### Log Messages
```
✅ Item BOM_Item_1 validated - Batch: True, Serial: False, Non-Managed: False
✅ Retrieved 1 batch numbers for item BOM_Item_1
✅ Added batch 20251212-BOM_Item_1 for item BOM_Item_1 with qty 1000.0
```

### Audit Trail
Each validation is logged in `grpo_transfer_logs`:
- `action`: 'item_validated_on_edit'
- `description`: Item validation details
- `user_id`: User who performed validation
- `session_id`: Transfer session ID

## Benefits

1. **Real-time Validation**: Item type validated when user edits
2. **Accurate Batch Retrieval**: Batches fetched for specific line item
3. **Database Consistency**: Batch records created/updated during edit
4. **User Feedback**: Immediate display of item type and batch numbers
5. **Error Prevention**: Validation happens before QC approval

## Testing Checklist

- [ ] Create GRPO transfer session
- [ ] Click "Edit" on a batch item
- [ ] Select "To Warehouse"
- [ ] Verify item type displays correctly
- [ ] Verify batch numbers appear
- [ ] Verify batch details (quantity, dates) are correct
- [ ] Click "Edit" on a non-batch item
- [ ] Verify "Non-Managed" badge displays
- [ ] Verify no batch numbers appear
- [ ] Save changes
- [ ] Verify database updated correctly
- [ ] Check audit logs for validation entry

## Performance Considerations

- **API Calls**: 2 calls per item validation (item type + batch details)
- **Database Operations**: Delete old batches + insert new batches
- **Caching**: None (always fetch fresh data)
- **Timeout**: 30 seconds per API call

## Backward Compatibility

- ✅ Existing sessions: No impact
- ✅ New sessions: Use new validation on edit
- ✅ Database: No schema changes
- ✅ API: New endpoint, no changes to existing endpoints

## Related Features

- Item type validation during session creation (still works)
- Batch number mapping in SAP payload (uses validated data)
- QC approval workflow (uses validated item types)

## Future Enhancements

1. Cache item type validation results
2. Batch number caching with TTL
3. Bulk item validation
4. Validation on item code change
5. Serial number validation and retrieval

## Support

For issues:
1. Check application logs for validation messages
2. Verify SAP B1 connectivity
3. Verify item exists in SAP B1
4. Check batch query parameters in logs
5. Verify database batch records created

## Files Modified

- `modules/grpo_transfer/routes.py` - Added new endpoint (lines ~1380-1520)

## Code Location

```python
@grpo_transfer_bp.route('/api/item/<int:item_id>/validate-and-fetch-batches', methods=['POST'])
@login_required
def validate_item_and_fetch_batches(item_id):
    """Validate item type and fetch batch details when editing item."""
```
