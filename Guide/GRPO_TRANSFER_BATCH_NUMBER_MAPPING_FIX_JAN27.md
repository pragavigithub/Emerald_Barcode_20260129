# GRPO Transfer - Batch Number Mapping Issue Fixed

## Problem
Batch numbers were being incorrectly mapped to non-batch items in the SAP B1 stock transfer payload. 

**Example Issue:**
- Items 1, 2, 4, 5 are batch items (should have batch numbers)
- Items 3, 6, 7, 8 are non-batch items (should NOT have batch numbers)
- But the JSON payload was including batch numbers for ALL items, including non-batch items

**Incorrect JSON (Before Fix):**
```json
{
  "LineNum": 4,
  "ItemCode": "BOM_Item_3",
  "Quantity": 500.0,
  "BatchNumbers": [
    {
      "BatchNumber": "20251212-BOM_Item_3",
      "Quantity": 500.0
    }
  ]
}
```

**Correct JSON (After Fix):**
```json
{
  "LineNum": 4,
  "ItemCode": "BOM_Item_3",
  "Quantity": 500.0,
  "BatchNumbers": []
}
```

## Root Cause Analysis

### Issue 1: Batch Records Created for Non-Batch Items
In `create_session_view()` endpoint, when fetching batch numbers from SAP:
- SAP returns batch numbers for ALL items in the GRPO (both batch and non-batch)
- The code was creating batch records for every item that had batch numbers
- **It was NOT checking if the item was actually a batch-managed item first**

### Issue 2: SAP Payload Generation Not Validating Item Type
In `post_transfer_to_sap()` endpoint:
- The code checked `if item.is_batch_item and item.batches`
- But if batch records existed (even for non-batch items), they would be included
- The condition didn't validate that batches should only exist for batch items

## Solution Applied

### Fix 1: Validate Item Type Before Creating Batch Records
**File:** `modules/grpo_transfer/routes.py` (lines ~260-280)

Added validation to only create batch records for items that are actually batch-managed:

```python
if item:
    # ✅ CRITICAL FIX: Only create batch records if item is actually a batch item
    # Check if this item is batch-managed (from SAP validation)
    if not item.is_batch_item:
        logger.warning(f"⚠️ Item {item_code} returned batch numbers but is NOT marked as batch item - skipping batch record")
        continue
    
    # Create batch record
    batch = GRPOTransferBatch()
    # ... rest of batch creation
```

**Impact:**
- Non-batch items will NOT have batch records created, even if SAP returns batch numbers
- Only items marked as `is_batch_item = True` will have batch records

### Fix 2: Enhanced Validation in SAP Payload Generation
**File:** `modules/grpo_transfer/routes.py` (lines ~1850-1930 and ~1980-2050)

Updated both approved and rejected transfer sections to validate batch items:

```python
# Handle batch items - ONLY if is_batch_item is True AND batches exist
if item.is_batch_item and item.batches and len(item.batches) > 0:
    # Process batch items with batch numbers
    for batch in item.batches:
        # ... add batch to payload
else:
    # Non-batch items - NO batch numbers
    line = {
        # ... item details
        'BatchNumbers': [],  # ✅ CRITICAL: Empty for non-batch items
        # ... rest of line
    }
```

**Impact:**
- Explicit check for `len(item.batches) > 0` ensures batches actually exist
- Non-batch items always get empty `BatchNumbers` array
- Prevents any batch numbers from being included for non-batch items

## Database Validation

The fix ensures:
1. **Batch Records Table** (`grpo_transfer_batches`):
   - Only contains records for items where `is_batch_item = True`
   - Non-batch items have NO batch records

2. **Item Flags** (`grpo_transfer_items`):
   - `is_batch_item` = True only for batch-managed items
   - `is_batch_item` = False for non-batch items
   - `is_non_managed` = True for non-managed items

## Testing Checklist

After applying this fix, verify:

- [ ] Create a GRPO transfer session with mixed batch and non-batch items
- [ ] Check the grid display - batch items should show batch numbers, non-batch items should show "N/A"
- [ ] Approve items with QC
- [ ] Check the SAP payload JSON:
  - Batch items should have `"BatchNumbers": [{"BatchNumber": "...", "Quantity": ...}]`
  - Non-batch items should have `"BatchNumbers": []`
- [ ] Post transfer to SAP B1 - should succeed without batch number errors
- [ ] Verify in SAP B1 that stock transfer was created correctly

## Files Modified

1. **modules/grpo_transfer/routes.py**
   - Line ~270: Added validation before creating batch records
   - Line ~1850-1930: Enhanced approved transfer payload generation
   - Line ~1980-2050: Enhanced rejected transfer payload generation

## Expected Behavior After Fix

### Grid Display
```
Item Code    | Batch Number | Approved Qty | Rejected Qty
BOM_Item_1   | 20251212-... | 500          | 0
BOM_Item_1   | 20251212-... | 500          | 0
BOM_Item_2   | 20251212-... | 450          | 50
BOM_Item_2   | 20251212-... | 450          | 50
BOM_Item_3   | N/A          | 500          | 0
BOM_Item_1   | N/A          | 500          | 0
BOM_Item_2   | N/A          | 400          | 0
BOM_Item_3   | N/A          | 400          | 0
```

### SAP Payload
- Lines 0-3: Include batch numbers (batch items)
- Lines 4-7: Empty batch numbers array (non-batch items)

## Related Issues Fixed
- Batch number validation during session creation
- Batch number mapping in grid display
- Batch number inclusion in SAP B1 stock transfer payload
- Database consistency for batch vs non-batch items

## Next Steps
1. Test with actual GRPO documents containing mixed item types
2. Verify SAP B1 stock transfer posting succeeds
3. Monitor logs for any batch number validation warnings
4. Confirm grid display shows correct batch numbers
