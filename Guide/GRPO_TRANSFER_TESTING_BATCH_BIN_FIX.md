# GRPO Transfer - Batch Number and From Bin Fix - Testing Guide
**Date**: January 26, 2026  
**Version**: 3.4.2

---

## Quick Test Steps

### Test 1: QC Form Shows From/To Warehouse and Bin Fields

1. Navigate to a GRPO Transfer session
2. Scroll to the "QC Validation" section
3. Verify you see the following fields for each item:
   - ✅ From Warehouse (dropdown)
   - ✅ From Bin Code (dropdown)
   - ✅ To Warehouse (dropdown)
   - ✅ To Bin Code (dropdown)

**Expected Result**: All 4 warehouse/bin fields should be visible

---

### Test 2: Warehouse Dropdowns Populate Correctly

1. Click on "From Warehouse" dropdown
2. Verify it shows a list of warehouses (e.g., "7000-FG - Finished Goods")
3. Click on "To Warehouse" dropdown
4. Verify it shows the same list of warehouses

**Expected Result**: Both dropdowns should populate with warehouse data from SAP

---

### Test 3: Bin Code Dropdowns Populate After Warehouse Selection

1. Select a warehouse from "From Warehouse" dropdown
2. Verify "From Bin Code" dropdown now shows bin codes for that warehouse
3. Select a warehouse from "To Warehouse" dropdown
4. Verify "To Bin Code" dropdown now shows bin codes for that warehouse

**Expected Result**: Bin dropdowns should populate based on selected warehouse

---

### Test 4: QC Approval Saves From/To Warehouse and Bin

1. Fill in QC form:
   - Approved Qty: 100
   - Rejected Qty: 0
   - Status: Approved
   - From Warehouse: 7000-FG
   - From Bin Code: BIN-001
   - To Warehouse: 7000-QFG
   - To Bin Code: BIN-002
2. Click "Submit QC Approval"
3. Wait for success message

**Expected Result**: Form should submit successfully and page should reload

---

### Test 5: Transfer Preview Shows Batch Numbers (Not "N/A")

1. After QC approval, click "View Transfer Preview" button
2. Look at the "Transfer Line Items" table
3. Check the "Batch Number" column

**Expected Result**: 
- For batch items: Should show actual batch numbers (e.g., "20251216-BOM_Item_1")
- For non-batch items: Should show "N/A"

---

### Test 6: Transfer Preview Shows From Bin (Not "N/A")

1. In the "Transfer Line Items" table
2. Check the "From Bin" column

**Expected Result**: Should show the bin code you selected (e.g., "BIN-001"), not "N/A"

---

### Test 7: Transfer Preview Shows To Bin (Not "N/A")

1. In the "Transfer Line Items" table
2. Check the "To Bin" column

**Expected Result**: Should show the bin code you selected (e.g., "BIN-002"), not "N/A"

---

### Test 8: Transfer Preview Shows Warehouse Information

1. In the "Approved Transfer" card at the top
2. Check "From Warehouse" and "To Warehouse" fields

**Expected Result**: Should show the warehouses you selected (e.g., "7000-FG" and "7000-QFG")

---

### Test 9: Batch Items Show Batch Details in Preview

1. For items marked as batch items
2. In the transfer preview table
3. Each batch should show:
   - ✅ Item Code
   - ✅ Batch Number (actual batch number, not "N/A")
   - ✅ Approved Qty
   - ✅ Rejected Qty
   - ✅ From Bin
   - ✅ To Bin

**Expected Result**: All batch details should be visible and correct

---

### Test 10: Non-Batch Items Show Correctly

1. For items NOT marked as batch items
2. In the transfer preview table
3. Should show:
   - ✅ Item Code
   - ✅ Batch Number: "N/A"
   - ✅ Approved Qty
   - ✅ Rejected Qty
   - ✅ From Bin
   - ✅ To Bin

**Expected Result**: Non-batch items should show "N/A" for batch number but correct bin codes

---

## Troubleshooting

### Issue: Batch Numbers Still Show "N/A"
**Solution**: 
1. Clear browser cache (Ctrl+Shift+Delete)
2. Refresh the page (Ctrl+F5)
3. Verify batches exist in database for the item
4. Check browser console for JavaScript errors

### Issue: From/To Warehouse Dropdowns Empty
**Solution**:
1. Verify warehouses are configured in SAP B1
2. Check API endpoint: GET /grpo-transfer/api/warehouses
3. Verify user has permission to view warehouses

### Issue: From/To Bin Dropdowns Empty After Warehouse Selection
**Solution**:
1. Verify bins are configured in SAP B1 for the selected warehouse
2. Check API endpoint: GET /grpo-transfer/api/bin-codes/{warehouse_code}
3. Verify warehouse code is correct

### Issue: QC Approval Fails
**Solution**:
1. Check browser console for error messages
2. Verify all required fields are filled
3. Check server logs for API errors
4. Verify at least one item is marked as "Approved"

---

## Data Validation

### Before Posting to SAP B1

Verify the following in the transfer preview:

- [ ] All batch items show actual batch numbers (not "N/A")
- [ ] All items show correct From Bin codes (not "N/A")
- [ ] All items show correct To Bin codes (not "N/A")
- [ ] From Warehouse matches the source warehouse
- [ ] To Warehouse matches the destination warehouse
- [ ] Approved quantities are correct
- [ ] Rejected quantities are correct (if any)
- [ ] All required fields are populated

---

## API Testing (Advanced)

### Test QC Approval API

```bash
curl -X POST http://localhost:5000/grpo-transfer/api/session/1/qc-approve \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "item_id": 1,
        "approved_quantity": 100,
        "rejected_quantity": 0,
        "qc_status": "approved",
        "from_warehouse": "7000-FG",
        "from_bin_code": "BIN-001",
        "to_warehouse": "7000-QFG",
        "to_bin_code": "BIN-002",
        "qc_notes": "QC passed"
      }
    ]
  }'
```

**Expected Response**:
```json
{
  "success": true,
  "message": "QC approval submitted successfully"
}
```

### Test Get Session Data API

```bash
curl -X GET http://localhost:5000/grpo-transfer/api/session/1
```

**Expected Response** (includes batches):
```json
{
  "success": true,
  "session": {
    "items": [
      {
        "id": 1,
        "item_code": "BatchItem_01",
        "is_batch_item": true,
        "from_warehouse": "7000-FG",
        "from_bin_code": "BIN-001",
        "to_warehouse": "7000-QFG",
        "to_bin_code": "BIN-002",
        "batches": [
          {
            "batch_number": "20251216-BOM_Item_1",
            "batch_quantity": 1000,
            "approved_quantity": 600,
            "rejected_quantity": 400,
            "expiry_date": "2027-01-08"
          }
        ]
      }
    ]
  }
}
```

---

## Success Criteria

✅ All tests pass  
✅ Batch numbers display correctly in transfer preview  
✅ From/To bin codes display correctly in transfer preview  
✅ QC form collects from_warehouse and from_bin_code  
✅ Data is saved to database correctly  
✅ Transfer preview shows all information before posting to SAP B1  

---

## Next Steps After Testing

1. Post transfer to SAP B1
2. Verify SAP B1 receives correct batch numbers and bin allocations
3. Verify QR labels generate with batch numbers
4. Test with multiple batch items
5. Test with mixed batch and non-batch items
