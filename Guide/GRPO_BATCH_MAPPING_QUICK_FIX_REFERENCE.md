# GRPO Transfer - Batch Number Mapping Quick Reference

## What Was Fixed

**Problem:** Non-batch items were getting batch numbers in the SAP B1 payload

**Solution:** Added validation to ensure batch numbers are only assigned to actual batch items

## Key Changes

### 1. Session Creation (Line ~270)
```python
# ✅ CRITICAL FIX: Only create batch records if item is actually a batch item
if not item.is_batch_item:
    logger.warning(f"⚠️ Item {item_code} returned batch numbers but is NOT marked as batch item - skipping batch record")
    continue
```

### 2. Approved Transfer Payload (Line ~1850)
```python
# Handle batch items - ONLY if is_batch_item is True AND batches exist
if item.is_batch_item and item.batches and len(item.batches) > 0:
    # Include batch numbers
else:
    # Non-batch items - NO batch numbers
    'BatchNumbers': []
```

### 3. Rejected Transfer Payload (Line ~1980)
Same validation as approved transfer

## How to Test

1. Create GRPO transfer session with mixed items
2. Check database:
   ```sql
   SELECT item_code, is_batch_item, COUNT(*) as batch_count
   FROM grpo_transfer_items i
   LEFT JOIN grpo_transfer_batches b ON i.id = b.item_id
   GROUP BY i.id;
   ```
   - Batch items should have batch records
   - Non-batch items should have 0 batch records

3. Check SAP payload:
   - Batch items: `"BatchNumbers": [{"BatchNumber": "...", "Quantity": ...}]`
   - Non-batch items: `"BatchNumbers": []`

4. Post to SAP B1 and verify success

## Expected Results

### Before Fix
```json
{
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

### After Fix
```json
{
  "ItemCode": "BOM_Item_3",
  "Quantity": 500.0,
  "BatchNumbers": []
}
```

## Validation Logic

```
Item Type Detection:
├── is_batch_item = True
│   ├── Create batch records ✅
│   └── Include in payload with batch numbers ✅
├── is_serial_item = True
│   ├── No batch records ✅
│   └── Include in payload with empty batch numbers ✅
└── is_non_managed = True
    ├── No batch records ✅
    └── Include in payload with empty batch numbers ✅
```

## Logs to Monitor

Look for these log messages:

**Good (Expected):**
```
✅ Item BOM_Item_1 validated - Batch: True, Serial: False, Non-Managed: False
✅ Added batch 20251212-BOM_Item_1 for item BOM_Item_1 with qty 500.0
```

**Warning (Indicates Issue):**
```
⚠️ Item BOM_Item_3 returned batch numbers but is NOT marked as batch item - skipping batch record
```

## Database Queries

### Check batch items
```sql
SELECT item_code, is_batch_item, COUNT(b.id) as batch_count
FROM grpo_transfer_items i
LEFT JOIN grpo_transfer_batches b ON i.id = b.item_id
WHERE is_batch_item = 1
GROUP BY i.id;
```

### Check non-batch items
```sql
SELECT item_code, is_batch_item, COUNT(b.id) as batch_count
FROM grpo_transfer_items i
LEFT JOIN grpo_transfer_batches b ON i.id = b.item_id
WHERE is_batch_item = 0
GROUP BY i.id;
```

### Verify no orphaned batch records
```sql
SELECT b.* FROM grpo_transfer_batches b
LEFT JOIN grpo_transfer_items i ON b.item_id = i.id
WHERE i.is_batch_item = 0;
```
(Should return 0 rows)

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| Non-batch items have batch numbers in payload | Batch records exist for non-batch items | Check database for orphaned batch records |
| Batch items missing batch numbers | `is_batch_item` flag not set correctly | Re-validate items using SAP query |
| SAP B1 rejects payload | Batch numbers on non-batch items | Apply this fix |
| Grid shows "N/A" for batch items | No batch records in database | Check session creation logs |

## Performance Impact

- Minimal: Added one additional check per batch record
- No database queries added
- Validation happens during session creation (one-time)

## Backward Compatibility

- Existing sessions: No impact
- New sessions: Will use corrected batch mapping
- SAP B1 transfers: Will now succeed for mixed item types
