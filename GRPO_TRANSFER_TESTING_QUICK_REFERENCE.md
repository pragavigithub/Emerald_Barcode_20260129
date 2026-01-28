# GRPO Transfer Module - Testing Quick Reference
**Date**: January 27, 2026  
**Version**: 3.5.3

---

## Quick Test Scenarios

### Scenario 1: Batch Item with Partial Approval
**Objective**: Test batch item validation, batch fetching, and partial QC approval

**Steps**:
1. Select GRPO document with batch items (e.g., DocEntry: 7840)
2. Verify item validation shows "Batch" type
3. Verify batch numbers are fetched and displayed
4. In QC form:
   - Received Qty: 1000
   - Approved Qty: 600
   - Rejected Qty: 400
   - Status: Partial
5. Select from_warehouse: 7000-FG
6. Select from_bin_code: BIN-001 (verify AbsEntry is captured)
7. Select to_warehouse: 7000-QFG
8. Select to_bin_code: BIN-002 (verify AbsEntry is captured)
9. Submit QC approval
10. Verify transfer preview shows:
    - Batch number (not "N/A")
    - From bin code (not "N/A")
    - To bin code (not "N/A")
    - Quantities: 600 approved, 400 rejected
11. Confirm transfer
12. Verify SAP B1 receives:
    - Batch numbers in payload
    - Bin AbsEntry values (251 for from, 1393 for to)
    - Correct quantities

**Expected Result**: ✅ Transfer posted successfully with batch numbers and bin allocations

---

### Scenario 2: Non-Batch Item
**Objective**: Test non-batch item handling

**Steps**:
1. Select GRPO document with non-batch items
2. Verify item validation shows "Non-Managed" type
3. In QC form:
   - Received Qty: 500
   - Approved Qty: 500
   - Rejected Qty: 0
   - Status: Approved
4. Select warehouses and bins
5. Submit QC approval
6. Verify transfer preview shows correct data
7. Confirm transfer
8. Verify SAP B1 receives transfer without batch numbers

**Expected Result**: ✅ Transfer posted successfully without batch numbers

---

### Scenario 3: Mixed Batch and Non-Batch Items
**Objective**: Test handling of mixed item types

**Steps**:
1. Select GRPO document with both batch and non-batch items
2. Verify item validation shows correct types for each item
3. Perform QC approval for all items
4. Verify transfer preview shows:
    - Batch numbers for batch items
    - No batch numbers for non-batch items
5. Confirm transfer
6. Verify SAP B1 receives correct payload for each item type

**Expected Result**: ✅ Transfer posted successfully with correct handling for each item type

---

### Scenario 4: Multiple Batches per Item
**Objective**: Test handling of items with multiple batches

**Steps**:
1. Select GRPO document with item having multiple batches
2. Verify all batch numbers are fetched
3. In QC form:
   - Received Qty: 2000 (sum of all batches)
   - Approved Qty: 1200
   - Rejected Qty: 800
4. Submit QC approval
5. Verify batch quantities are distributed proportionally
6. Verify transfer preview shows all batches
7. Confirm transfer
8. Verify SAP B1 receives all batch numbers with distributed quantities

**Expected Result**: ✅ Batch quantities distributed proportionally across all batches

---

## Verification Checklist

### Item Validation
- [ ] All items in GRPO are validated (not just last one)
- [ ] Batch items show "Batch" badge
- [ ] Serial items show "Serial" badge
- [ ] Non-batch items show "Non-Managed" badge
- [ ] Item validation uses correct SAP query: `ItemCode_Batch_Serial_Val`

### Batch Fetching
- [ ] Batch numbers are fetched for batch items
- [ ] Batch numbers are NOT fetched for non-batch items
- [ ] Batch numbers use correct SAP field names:
  - `BatchNum` (not `BatchNumber`)
  - `ExpDate` (not `ExpiryDate`)
  - `MnfDate` (not `ManufactureDate`)
- [ ] Date format is parsed correctly (YYYYMMDD → YYYY-MM-DD)
- [ ] Batch data is stored in database

### QC Validation
- [ ] QC form displays all fields:
  - Received Qty
  - Approved Qty
  - Rejected Qty
  - Status
  - From Warehouse
  - From Bin Code
  - To Warehouse
  - To Bin Code
  - QC Notes
- [ ] Warehouse dropdowns populate correctly
- [ ] Bin code dropdowns populate correctly
- [ ] Bin AbsEntry values are captured (check browser console)
- [ ] Partial approval works (e.g., 600 OK, 400 NOTOK)
- [ ] Batch quantities are distributed proportionally

### Transfer Preview
- [ ] Preview modal displays correctly
- [ ] Batch numbers are shown (not "N/A")
- [ ] From bin codes are shown (not "N/A")
- [ ] To bin codes are shown (not "N/A")
- [ ] Warehouse information is displayed
- [ ] Quantities are correct
- [ ] Approved and rejected transfers are separated

### SAP B1 Transfer Posting
- [ ] Transfer is posted to SAP B1 successfully
- [ ] Batch numbers are included in payload
- [ ] Bin AbsEntry values are included (not hardcoded to 1)
- [ ] BaseEntry, BaseLine, BaseType are correct
- [ ] Quantities match approved amounts
- [ ] DocNumber and DocEntry are returned
- [ ] Response is saved to session

### QR Label Generation
- [ ] Labels are generated for approved items
- [ ] One label per pack
- [ ] Labels include:
  - Item code
  - Batch number
  - Quantity
  - Warehouse information
  - Bin information
- [ ] Labels can be printed

---

## Browser Console Checks

### Check 1: Verify AbsEntry Capture
```javascript
// In browser console, after selecting a bin code:
document.querySelector('select[name^="from_bin_"]').options[document.querySelector('select[name^="from_bin_"]').selectedIndex].dataset.absEntry
// Should return a number (e.g., 251), not undefined
```

### Check 2: Verify QC Form Data
```javascript
// In browser console, after filling QC form:
const items = [];
document.querySelectorAll('#qcItemsContainer .card').forEach(card => {
    const approvedQtyInput = card.querySelector('input[name^="approved_qty_"]');
    const fromBinSelect = card.querySelector('select[name^="from_bin_"]');
    const fromBinAbsEntry = fromBinSelect?.options[fromBinSelect.selectedIndex]?.dataset?.absEntry;
    console.log({
        approved_qty: approvedQtyInput.value,
        from_bin_abs_entry: fromBinAbsEntry
    });
});
```

### Check 3: Verify Transfer Payload
```javascript
// In browser console, check network tab:
// Look for POST to /grpo-transfer/api/session/*/post-transfer
// Verify payload includes:
// - BatchNumbers array with batch_number and quantity
// - StockTransferLinesBinAllocations with BinAbsEntry (not 1)
```

---

## Common Issues & Solutions

### Issue 1: Batch Numbers Show "N/A"
**Cause**: Batch data not included in session data or not fetched from SAP B1

**Solution**:
1. Check `session_detail()` route includes batch data
2. Verify batch fetching query uses correct field names
3. Check database has batch records

**Verification**:
```python
# In Python shell:
from modules.grpo_transfer.models import GRPOTransferSession, GRPOTransferBatch
session = GRPOTransferSession.query.get(1)
for item in session.items:
    print(f"Item: {item.item_code}, Batches: {len(item.batches)}")
    for batch in item.batches:
        print(f"  - {batch.batch_number}: {batch.batch_quantity}")
```

---

### Issue 2: From Bin Code Shows "N/A"
**Cause**: from_bin_code not saved in QC approval

**Solution**:
1. Verify QC form includes from_bin_code field
2. Verify submitQCApproval() captures from_bin_code
3. Verify qc_approve_items() saves from_bin_code

**Verification**:
```python
# In Python shell:
from modules.grpo_transfer.models import GRPOTransferItem
item = GRPOTransferItem.query.get(1)
print(f"From Bin: {item.from_bin_code}")
print(f"From Bin AbsEntry: {item.from_bin_abs_entry}")
```

---

### Issue 3: BinAbsEntry is 1 (Hardcoded)
**Cause**: Using old code that hardcodes BinAbsEntry to 1

**Solution**:
1. Verify routes.py uses `item.from_bin_abs_entry` and `item.to_bin_abs_entry`
2. Verify QC approval captures AbsEntry values
3. Verify database has AbsEntry values

**Verification**:
```python
# In Python shell:
from modules.grpo_transfer.models import GRPOTransferItem
item = GRPOTransferItem.query.get(1)
print(f"From Bin AbsEntry: {item.from_bin_abs_entry}")
print(f"To Bin AbsEntry: {item.to_bin_abs_entry}")
# Should be actual numbers, not None or 1
```

---

### Issue 4: Item Validation Only for Last Item
**Cause**: Validation code outside the loop

**Solution**:
1. Verify item validation is inside the loop in `create_session_view()`
2. Check lines 157-210 in routes.py

**Verification**:
```python
# In Python shell:
from modules.grpo_transfer.models import GRPOTransferSession
session = GRPOTransferSession.query.get(1)
for item in session.items:
    print(f"Item: {item.item_code}")
    print(f"  - is_batch_item: {item.is_batch_item}")
    print(f"  - is_serial_item: {item.is_serial_item}")
    print(f"  - is_non_managed: {item.is_non_managed}")
# All items should have correct flags, not just last one
```

---

## Performance Considerations

### Batch Fetching
- Fetches all batches for document at once
- Filters by item_code in memory
- Typical time: < 1 second for 100 batches

### Warehouse/Bin Loading
- Fetches warehouses once
- Fetches bins per warehouse on demand
- Typical time: < 500ms per warehouse

### Transfer Posting
- Posts to SAP B1 synchronously
- Typical time: 2-5 seconds depending on SAP B1 load
- Consider async posting for large transfers

---

## Debugging Tips

### Enable Detailed Logging
```python
# In logging_config.py or app.py:
logging.getLogger('modules.grpo_transfer').setLevel(logging.DEBUG)
```

### Check Server Logs
```bash
# View Flask logs:
tail -f /var/log/grpo-transfer/app.log

# Look for:
# - "✅ Item X validated as batch"
# - "✅ Retrieved X batch numbers"
# - "✅ Updated batch X: approved_qty=Y"
# - "✅ Approved stock transfer posted to SAP B1"
```

### Check Browser Network Tab
1. Open Developer Tools (F12)
2. Go to Network tab
3. Perform QC approval
4. Look for POST to `/grpo-transfer/api/session/*/qc-approve`
5. Check request body includes AbsEntry values
6. Check response is successful (200 OK)

### Check Database
```python
# In Python shell:
from modules.grpo_transfer.models import GRPOTransferItem, GRPOTransferBatch
item = GRPOTransferItem.query.get(1)
print(f"Item: {item.item_code}")
print(f"From Warehouse: {item.from_warehouse}")
print(f"From Bin: {item.from_bin_code}")
print(f"From Bin AbsEntry: {item.from_bin_abs_entry}")
print(f"To Warehouse: {item.to_warehouse}")
print(f"To Bin: {item.to_bin_code}")
print(f"To Bin AbsEntry: {item.to_bin_abs_entry}")
print(f"Batches: {len(item.batches)}")
for batch in item.batches:
    print(f"  - {batch.batch_number}: {batch.batch_quantity}")
```

---

## Test Data Requirements

### SAP B1 Test Data
- GRPO document with batch items (DocEntry: 7840)
- GRPO document with non-batch items
- GRPO document with mixed items
- Warehouses: 7000-FG, 7000-QFG
- Bin codes with AbsEntry values

### Database Setup
```sql
-- Verify tables exist:
SHOW TABLES LIKE 'grpo_transfer%';

-- Verify columns exist:
DESCRIBE grpo_transfer_items;
-- Should include: from_bin_abs_entry, to_bin_abs_entry
```

---

## Success Criteria

✅ All items in GRPO are validated (not just last one)
✅ Batch numbers are fetched with correct SAP field names
✅ Batch numbers display in transfer preview (not "N/A")
✅ From bin codes display in transfer preview (not "N/A")
✅ Bin AbsEntry values are captured and stored
✅ Transfer payload includes batch numbers
✅ Transfer payload includes bin AbsEntry values (not hardcoded)
✅ SAP B1 receives correct payload
✅ QR labels are generated with batch information
✅ Complete workflow works end-to-end

---

**Last Updated**: January 27, 2026  
**Status**: Ready for Testing

