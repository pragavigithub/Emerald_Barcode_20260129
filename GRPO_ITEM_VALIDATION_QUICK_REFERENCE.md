# GRPO Item Validation - Quick Reference

## The Issue
Same item code appearing multiple times → Only first occurrence validated correctly → Subsequent occurrences marked as "Non-Managed"

## The Fix
Match items by **item_code + line_number** instead of just **item_code**

## Code Change
```python
# ❌ BEFORE: Only first occurrence matched
item = GRPOTransferItem.query.filter_by(
    session_id=session.id,
    item_code=item_code
).first()

# ✅ AFTER: Each line item matched uniquely
item = GRPOTransferItem.query.filter_by(
    session_id=session.id,
    item_code=item_code,
    sap_base_line=line_num  # ← NEW
).first()
```

## Expected Results

### Grid Display
```
Line 0: BOM_Item_1 → Batch ✅
Line 1: BOM_Item_2 → Batch ✅
Line 2: BOM_Item_3 → Non-Managed ✅
Line 3: BOM_Item_1 → Batch ✅ (was Non-Managed ❌)
Line 4: BOM_Item_2 → Batch ✅ (was Non-Managed ❌)
Line 5: BOM_Item_3 → Non-Managed ✅
```

### Database
```sql
-- Each line item should have correct type and batch records
SELECT line_num, item_code, is_batch_item, 
       (SELECT COUNT(*) FROM grpo_transfer_batches WHERE item_id = i.id) as batch_count
FROM grpo_transfer_items i
ORDER BY line_num;

-- Expected:
-- 0, BOM_Item_1, 1, 1 ✅
-- 1, BOM_Item_2, 1, 1 ✅
-- 2, BOM_Item_3, 0, 0 ✅
-- 3, BOM_Item_1, 1, 1 ✅ (was 0 ❌)
-- 4, BOM_Item_2, 1, 1 ✅ (was 0 ❌)
-- 5, BOM_Item_3, 0, 0 ✅
```

## Validation Flow

```
Session Creation:
├── For each line item:
│   ├── Validate item type (Batch/Serial/Non-Managed)
│   └── Store in database with line_num
│
Batch Assignment:
├── For each batch from SAP:
│   ├── Get ItemCode and LineNum
│   ├── Find item by: session_id + item_code + line_num ← KEY FIX
│   ├── Check if is_batch_item = True
│   └── Create batch record if True
```

## Key Points

1. **Line Number is Critical**: Each line item must be uniquely identified
2. **Per-Line Validation**: Each occurrence of same item code is validated separately
3. **Batch Records**: Only created for items marked as batch items
4. **Database Consistency**: Each line item has correct type and batch records

## Testing

```bash
# 1. Create GRPO with duplicate item codes
# 2. Check grid display - all items should show correct type
# 3. Check database:
SELECT * FROM grpo_transfer_items WHERE session_id = 29 ORDER BY line_num;
SELECT * FROM grpo_transfer_batches WHERE item_id IN (SELECT id FROM grpo_transfer_items WHERE session_id = 29);

# 4. Post transfer to SAP B1 - should succeed
# 5. Verify in SAP B1 - correct batch numbers
```

## Logs

**Look for:**
```
✅ Item BOM_Item_1 (line 0) validated - Batch: True
✅ Item BOM_Item_1 (line 3) validated - Batch: True
✅ Added batch 20251212-BOM_Item_1 for item BOM_Item_1 (line 0)
✅ Added batch 20251212-BOM_Item_1 for item BOM_Item_1 (line 3)
```

**Avoid:**
```
⚠️ Could not find item BOM_Item_1 at line 3
```

## Files Modified
- `modules/grpo_transfer/routes.py` (lines ~240-310)

## Impact
- ✅ Correct item type validation for all line items
- ✅ Correct batch number assignment
- ✅ Correct grid display
- ✅ Correct SAP B1 payload
- ✅ No database schema changes
- ✅ No performance impact
