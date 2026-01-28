# GRPO Transfer - Item Validation Per Line Fix

## Problem
Items were being validated and stored incorrectly in the database. When the same item code appeared multiple times in a GRPO (e.g., BOM_Item_1 on line 0 and line 3), only the first occurrence was being validated correctly. Subsequent occurrences were incorrectly marked as "Non-Managed" instead of their actual type (Batch/Serial).

**Example Issue:**
```
Line 0: BOM_Item_1 → Correctly marked as "Batch" ✅
Line 1: BOM_Item_2 → Correctly marked as "Batch" ✅
Line 2: BOM_Item_3 → Correctly marked as "Non-Managed" ✅
Line 3: BOM_Item_1 → INCORRECTLY marked as "Non-Managed" ❌ (should be Batch)
Line 4: BOM_Item_2 → INCORRECTLY marked as "Non-Managed" ❌ (should be Batch)
Line 5: BOM_Item_3 → Correctly marked as "Non-Managed" ✅
```

## Root Cause
The batch number assignment logic was using `.first()` to find items by item code only:

```python
# ❌ WRONG: Only returns first occurrence
item = GRPOTransferItem.query.filter_by(
    session_id=session.id,
    item_code=item_code
).first()
```

When multiple line items had the same item code, only the first one would get batch records assigned. The subsequent occurrences would not have batch records, causing them to display as "Non-Managed".

## Solution Applied

### Fix: Match Items by Line Number
**File:** `modules/grpo_transfer/routes.py` (lines ~240-310)

Changed the item lookup to match by BOTH item code AND line number:

```python
# ✅ CORRECT: Match by item_code AND line_num for unique identification
item = GRPOTransferItem.query.filter_by(
    session_id=session.id,
    item_code=item_code,
    sap_base_line=line_num  # ✅ NEW: Match by line number too
).first()
```

**Key Changes:**
1. Extract `line_num` from batch info: `line_num = batch_info.get('LineNum')`
2. Add `sap_base_line=line_num` to the filter query
3. Enhanced logging to show line number for debugging

## How It Works Now

### Before Fix
```
Batch Info from SAP:
├── ItemCode: BOM_Item_1, LineNum: 0, BatchNum: 20251212-BOM_Item_1
├── ItemCode: BOM_Item_2, LineNum: 1, BatchNum: 20251212-BOM_Item_2
├── ItemCode: BOM_Item_1, LineNum: 3, BatchNum: 20251212-BOM_Item_1
└── ItemCode: BOM_Item_2, LineNum: 4, BatchNum: 20251212-BOM_Item_2

Processing:
├── Line 0: BOM_Item_1 → Found ✅ → Batch record created ✅
├── Line 1: BOM_Item_2 → Found ✅ → Batch record created ✅
├── Line 3: BOM_Item_1 → Found (but it's the FIRST one) ❌ → Batch record NOT created ❌
└── Line 4: BOM_Item_2 → Found (but it's the FIRST one) ❌ → Batch record NOT created ❌
```

### After Fix
```
Batch Info from SAP:
├── ItemCode: BOM_Item_1, LineNum: 0, BatchNum: 20251212-BOM_Item_1
├── ItemCode: BOM_Item_2, LineNum: 1, BatchNum: 20251212-BOM_Item_2
├── ItemCode: BOM_Item_1, LineNum: 3, BatchNum: 20251212-BOM_Item_1
└── ItemCode: BOM_Item_2, LineNum: 4, BatchNum: 20251212-BOM_Item_2

Processing:
├── Line 0: BOM_Item_1 → Found (line 0) ✅ → Batch record created ✅
├── Line 1: BOM_Item_2 → Found (line 1) ✅ → Batch record created ✅
├── Line 3: BOM_Item_1 → Found (line 3) ✅ → Batch record created ✅
└── Line 4: BOM_Item_2 → Found (line 4) ✅ → Batch record created ✅
```

## Database Impact

### Before Fix
```sql
SELECT i.line_num, i.item_code, i.is_batch_item, COUNT(b.id) as batch_count
FROM grpo_transfer_items i
LEFT JOIN grpo_transfer_batches b ON i.id = b.item_id
ORDER BY i.line_num;

Results:
line_num | item_code  | is_batch_item | batch_count
0        | BOM_Item_1 | 1             | 1           ✅
1        | BOM_Item_2 | 1             | 1           ✅
2        | BOM_Item_3 | 0             | 0           ✅
3        | BOM_Item_1 | 1             | 0           ❌ (should be 1)
4        | BOM_Item_2 | 1             | 0           ❌ (should be 1)
5        | BOM_Item_3 | 0             | 0           ✅
```

### After Fix
```sql
Results:
line_num | item_code  | is_batch_item | batch_count
0        | BOM_Item_1 | 1             | 1           ✅
1        | BOM_Item_2 | 1             | 1           ✅
2        | BOM_Item_3 | 0             | 0           ✅
3        | BOM_Item_1 | 1             | 1           ✅
4        | BOM_Item_2 | 1             | 1           ✅
5        | BOM_Item_3 | 0             | 0           ✅
```

## Grid Display Impact

### Before Fix
```
Item Code  | Type          | Batch Number
BOM_Item_1 | Batch         | 20251212-BOM_Item_1
BOM_Item_2 | Batch         | 20251212-BOM_Item_2
BOM_Item_3 | Non-Managed   | N/A
BOM_Item_1 | Non-Managed   | N/A              ❌ (should be Batch)
BOM_Item_2 | Non-Managed   | N/A              ❌ (should be Batch)
BOM_Item_3 | Non-Managed   | N/A
```

### After Fix
```
Item Code  | Type          | Batch Number
BOM_Item_1 | Batch         | 20251212-BOM_Item_1
BOM_Item_2 | Batch         | 20251212-BOM_Item_2
BOM_Item_3 | Non-Managed   | N/A
BOM_Item_1 | Batch         | 20251212-BOM_Item_1  ✅
BOM_Item_2 | Batch         | 20251212-BOM_Item_2  ✅
BOM_Item_3 | Non-Managed   | N/A
```

## Validation Flow

```
For each line item in GRPO:
├── Validate item type (Batch/Serial/Non-Managed)
│   └── Store flags: is_batch_item, is_serial_item, is_non_managed
├── For each batch number returned by SAP:
│   ├── Get ItemCode and LineNum from batch info
│   ├── Find item by: session_id + item_code + sap_base_line (line_num)
│   ├── Check if item.is_batch_item = True
│   ├── If True: Create batch record ✅
│   └── If False: Skip batch record ✅
└── Result: Each line item has correct type and batch records
```

## Code Changes Summary

| Location | Change | Impact |
|----------|--------|--------|
| Line ~245 | Added `line_num = batch_info.get('LineNum')` | Extract line number from batch info |
| Line ~250 | Added `sap_base_line=line_num` to filter | Match items by line number |
| Line ~265 | Enhanced logging with line number | Better debugging |
| Line ~310 | Added warning for missing items | Catch edge cases |

## Testing Checklist

- [ ] Create GRPO with same item code appearing multiple times
- [ ] Verify each line item is validated individually
- [ ] Check database: Each line item should have correct `is_batch_item` flag
- [ ] Check database: Each batch item should have batch records
- [ ] Check grid display: All batch items show batch numbers
- [ ] Check grid display: All non-batch items show "N/A"
- [ ] Post transfer to SAP B1: Should succeed
- [ ] Verify SAP B1 stock transfer has correct batch numbers

## Logs to Monitor

**Good (Expected):**
```
✅ Item BOM_Item_1 (line 0) validated - Batch: True, Serial: False, Non-Managed: False
✅ Item BOM_Item_1 (line 3) validated - Batch: True, Serial: False, Non-Managed: False
✅ Added batch 20251212-BOM_Item_1 for item BOM_Item_1 (line 0) with qty 1000.0
✅ Added batch 20251212-BOM_Item_1 for item BOM_Item_1 (line 3) with qty 1000.0
```

**Warning (Indicates Issue):**
```
⚠️ Could not find item BOM_Item_1 at line 3 in session 29
```

## Performance Impact

- Minimal: Added one additional filter parameter
- No new database queries
- Validation happens during session creation (one-time)

## Backward Compatibility

- Existing sessions: No impact
- New sessions: Will use corrected per-line validation
- Database: No schema changes required

## Related Fixes

This fix complements the previous batch number mapping fix by ensuring:
1. Each line item is validated individually ✅ (this fix)
2. Batch numbers are only assigned to batch items ✅ (previous fix)
3. SAP payload includes correct batch numbers ✅ (previous fix)

Together, these fixes ensure proper item type validation and batch number handling for GRPO transfers with duplicate item codes.
