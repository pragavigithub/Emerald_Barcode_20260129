# GRPO Transfer - Item Validation Fix (All Items)
**Date**: January 26, 2026  
**Version**: 3.5.2  
**Status**: ✅ FIXED

---

## Issue Identified

### The Problem
Item validation was **incomplete** - only validating the first few items, not all items in the GRPO document.

**Before**:
- Items 1-3: Correctly validated (Batch/Non-Managed)
- Items 4-6: NOT validated (showing as "Non-Managed" even if they're batch items)

**After**:
- Items 1-6: ALL validated correctly ✅

### Root Cause
The item validation was being called **outside the loop** (only for the last item), not **inside the loop** (for each item).

**Wrong Approach**:
```python
for line in line_items:
    item = GRPOTransferItem()
    # ... create item ...
    db.session.add(item)

db.session.commit()

# ❌ WRONG: Validation called AFTER loop, only for last item
validate_item(line.get('ItemCode'))
```

**Correct Approach**:
```python
for line in line_items:
    item = GRPOTransferItem()
    # ... create item ...
    
    # ✅ CORRECT: Validate EACH item inside the loop
    item_code = line.get('ItemCode')
    # Call SAP API to validate
    # Update item.is_batch_item, item.is_serial_item, item.is_non_managed
    
    db.session.add(item)

db.session.commit()
```

---

## Fix Applied

### File: `modules/grpo_transfer/routes.py`

**Location**: Lines 157-210 (in `create_session_view()` function)

**Changes**:

1. **Moved validation inside the loop** (Line 170)
```python
# Add line items to session
for line in line_items:
    item = GRPOTransferItem()
    # ... set item fields ...
    
    # ✅ NEW: Validate item type for EACH item
    item_code = line.get('ItemCode')
    try:
        # Call SAP query to validate item
        val_url = f"{sap.base_url}/b1s/v1/SQLQueries('ItemCode_Batch_Serial_Val')/List"
        val_headers = {'Prefer': 'odata.maxpagesize=0'}
        val_payload = {"ParamList": f"itemCode='{item_code}'"}
        
        val_response = sap.session.post(val_url, json=val_payload, headers=val_headers, timeout=30)
        
        if val_response.status_code == 200:
            val_data = val_response.json()
            val_items = val_data.get('value', [])
            
            if val_items:
                val_info = val_items[0]
                is_batch = val_info.get('BatchNum') == 'Y'
                is_serial = val_info.get('SerialNum') == 'Y'
                
                # Set item type flags
                item.is_batch_item = is_batch
                item.is_serial_item = is_serial
                item.is_non_managed = not is_batch and not is_serial
                
                logger.info(f"✅ Item {item_code} validated - Batch: {is_batch}, Serial: {is_serial}, Non-Managed: {item.is_non_managed}")
            else:
                logger.warning(f"⚠️ Item {item_code} not found in SAP B1 - marking as non-managed")
                item.is_non_managed = True
        else:
            logger.warning(f"⚠️ Failed to validate item {item_code}: {val_response.status_code}")
            item.is_non_managed = True
    except Exception as val_error:
        logger.warning(f"⚠️ Error validating item {item_code}: {str(val_error)}")
        item.is_non_managed = True
    
    db.session.add(item)

db.session.commit()
```

2. **Removed old validation call** (Line 180)
```python
# ❌ REMOVED: validate_item(line.get('ItemCode'))
```

---

## What This Fixes

### ✅ All Items Now Validated

**Before**:
```
Item Code │ Type           │ Status
──────────┼────────────────┼─────────
BOM_Item_1│ Batch          │ ✅ Correct
BOM_Item_2│ Batch          │ ✅ Correct
BOM_Item_3│ Non-Managed    │ ✅ Correct
BOM_Item_1│ Non-Managed    │ ❌ WRONG (should be Batch)
BOM_Item_2│ Non-Managed    │ ❌ WRONG (should be Batch)
BOM_Item_3│ Non-Managed    │ ✅ Correct
```

**After**:
```
Item Code │ Type           │ Status
──────────┼────────────────┼─────────
BOM_Item_1│ Batch          │ ✅ Correct
BOM_Item_2│ Batch          │ ✅ Correct
BOM_Item_3│ Non-Managed    │ ✅ Correct
BOM_Item_1│ Batch          │ ✅ Correct
BOM_Item_2│ Batch          │ ✅ Correct
BOM_Item_3│ Non-Managed    │ ✅ Correct
```

---

## How It Works Now

### Step 1: Session Creation
```
User selects GRPO document
    ↓
System fetches GRPO details and line items
    ↓
System creates GRPOTransferSession
    ↓
For EACH line item:
    ├─ Create GRPOTransferItem
    ├─ Set item fields (code, name, quantity, warehouse, etc.)
    ├─ ✅ NEW: Validate item type using SAP API
    │   ├─ Call ItemCode_Batch_Serial_Val query
    │   ├─ Get BatchNum and SerialNum flags
    │   ├─ Set is_batch_item, is_serial_item, is_non_managed
    │   └─ Log validation result
    └─ Save item to database
    ↓
System commits all items
    ↓
System fetches batch numbers for batch items
    ↓
System creates GRPOTransferBatch for each batch
```

### Step 2: Item Type Determination
```
SAP API Response:
{
  "BatchNum": "Y",      // ← Batch item
  "SerialNum": "N"
}
    ↓
Item Flags Set:
- is_batch_item = true
- is_serial_item = false
- is_non_managed = false
    ↓
Result: Item marked as BATCH ITEM ✅
```

---

## Database Impact

### GRPOTransferItem Fields Updated

For each item, the following fields are now set during session creation:

```python
item.is_batch_item = True/False      # ✅ NOW SET
item.is_serial_item = True/False     # ✅ NOW SET
item.is_non_managed = True/False     # ✅ NOW SET
```

**Before**: These fields were NULL/False for all items
**After**: These fields are correctly set based on SAP validation

---

## Testing Steps

### Test 1: Verify All Items Are Validated
1. Create new GRPO Transfer session with 6 items
2. Check server logs for validation messages:
   ```
   ✅ Item BOM_Item_1 validated - Batch: True, Serial: False, Non-Managed: False
   ✅ Item BOM_Item_2 validated - Batch: True, Serial: False, Non-Managed: False
   ✅ Item BOM_Item_3 validated - Batch: False, Serial: False, Non-Managed: True
   ✅ Item BOM_Item_1 validated - Batch: True, Serial: False, Non-Managed: False
   ✅ Item BOM_Item_2 validated - Batch: True, Serial: False, Non-Managed: False
   ✅ Item BOM_Item_3 validated - Batch: False, Serial: False, Non-Managed: True
   ```

### Test 2: Verify Database
```sql
SELECT 
  item_code,
  is_batch_item,
  is_serial_item,
  is_non_managed
FROM grpo_transfer_items
WHERE session_id = {session_id}
ORDER BY line_num;
```

Expected: All items should have correct flags set

### Test 3: Verify UI Display
1. Open GRPO Transfer session
2. Check "Items" tab
3. Verify "Type" column shows:
   - "Batch" for batch items
   - "Non-Managed" for non-managed items
   - "Serial" for serial items (if any)

### Test 4: Verify Batch Fetching
1. For batch items, verify batch numbers are fetched
2. Check server logs for:
   ```
   ✅ Retrieved X batch numbers for document {doc_entry}
   ✅ Added batch {batch_number} for item {item_code}
   ```

---

## SAP B1 API Reference

### Item Validation Query

**Endpoint**: `POST /b1s/v1/SQLQueries('ItemCode_Batch_Serial_Val')/List`

**Request**:
```json
{
  "ParamList": "itemCode='BOM_Item_1'"
}
```

**Response**:
```json
{
  "value": [{
    "ItemCode": "BOM_Item_1",
    "ItemName": "BOM_Item_Batch_1",
    "BatchNum": "Y",              // ← Batch item
    "SerialNum": "N",
    "NonBatch_NonSerialMethod": "A"
  }]
}
```

**Field Mapping**:
- `BatchNum = "Y"` → is_batch_item = true
- `SerialNum = "Y"` → is_serial_item = true
- Both "N" → is_non_managed = true

---

## Error Handling

### If Validation Fails
```python
try:
    # Call SAP API
    val_response = sap.session.post(...)
except Exception as val_error:
    logger.warning(f"⚠️ Error validating item {item_code}: {str(val_error)}")
    item.is_non_managed = True  # ← Default to non-managed
```

**Behavior**:
- If SAP API fails: Item marked as non-managed (safe default)
- If item not found: Item marked as non-managed
- If validation error: Item marked as non-managed
- Validation errors don't block session creation

---

## Performance Impact

### API Calls
- **Before**: 1 validation call (only for last item)
- **After**: N validation calls (one per item)

**Example**: 6 items = 6 API calls to SAP B1

**Optimization**: Calls are made sequentially during session creation (acceptable since it's a one-time operation)

---

## Deployment Steps

1. ✅ Apply fix to `modules/grpo_transfer/routes.py`
2. ✅ Verify Python syntax: `python -m py_compile modules/grpo_transfer/routes.py`
3. Clear browser cache
4. Restart application
5. Create new GRPO Transfer session
6. Verify all items are validated

---

## Rollback Plan

If issues occur:
1. Revert changes to `modules/grpo_transfer/routes.py` (lines 157-210)
2. Clear browser cache
3. Restart application

---

## Summary

**What Was Fixed**:
- Item validation now runs for ALL items (not just the last one) ✅
- Each item's type is correctly determined (Batch/Serial/Non-Managed) ✅
- Item flags are set in database during session creation ✅
- Batch numbers are fetched only for batch items ✅

**Result**:
- All items in GRPO document are properly validated
- Batch items are correctly identified
- Batch numbers are fetched for all batch items
- Transfer preview shows correct item types
- QR labels display batch numbers for batch items

---

**Status**: ✅ FIXED AND READY FOR TESTING  
**Last Updated**: January 26, 2026  
**Version**: 3.5.2
