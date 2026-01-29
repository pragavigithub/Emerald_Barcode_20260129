# Test Guide: Edit Modal Fix Verification

**Feature**: Approved/Rejected Warehouse Designation  
**Bug Fixed**: Edit modal not opening  
**Test Date**: January 28, 2026

---

## Pre-Test Checklist

- [ ] Application restarted
- [ ] Database migration applied
- [ ] No errors in application logs
- [ ] Browser cache cleared
- [ ] Developer tools available (F12)

---

## Test Case 1: Edit Modal Opens

### Steps
1. Navigate to GRPO Transfer module
2. Open any transfer session
3. Click **Edit** button on first item

### Expected Results
- ✅ Modal appears with loading spinner
- ✅ Modal title shows "Edit Item"
- ✅ Loading spinner disappears after 1-2 seconds
- ✅ Item form loads with all fields populated

### Actual Results
- [ ] Modal appears
- [ ] Loading spinner shows
- [ ] Form loads successfully
- [ ] No error messages

### Status
- [ ] PASS
- [ ] FAIL

---

## Test Case 2: Item Data Loads Correctly

### Steps
1. Click Edit on an item
2. Wait for form to load
3. Verify all fields are populated

### Expected Results
- ✅ Item Code field shows correct code
- ✅ Item Name field shows correct name
- ✅ Received Qty shows correct quantity
- ✅ Approved Qty shows current value
- ✅ Rejected Qty shows current value
- ✅ Status dropdown shows current status

### Actual Results
- [ ] Item Code: _______________
- [ ] Item Name: _______________
- [ ] Received Qty: _______________
- [ ] Approved Qty: _______________
- [ ] Rejected Qty: _______________
- [ ] Status: _______________

### Status
- [ ] PASS
- [ ] FAIL

---

## Test Case 3: Warehouse Sections Display

### Steps
1. Click Edit on an item
2. Wait for form to load
3. Scroll down to see warehouse sections

### Expected Results
- ✅ "From Warehouse" section visible (read-only)
- ✅ "Approved Qty Designation Warehouse" section visible (green)
- ✅ "Rejected Qty Designation Warehouse" section visible (red)
- ✅ All warehouse dropdowns present

### Actual Results
- [ ] From Warehouse section visible
- [ ] Approved section visible
- [ ] Rejected section visible
- [ ] All dropdowns present

### Status
- [ ] PASS
- [ ] FAIL

---

## Test Case 4: Warehouse Dropdowns Load

### Steps
1. Click Edit on an item
2. Wait for form to load
3. Click on "Approved To Warehouse" dropdown
4. Verify warehouses load

### Expected Results
- ✅ Dropdown opens
- ✅ Warehouses list appears
- ✅ Warehouses formatted as "CODE - NAME"
- ✅ Can select a warehouse

### Actual Results
- [ ] Dropdown opens
- [ ] Warehouses load
- [ ] Format correct
- [ ] Can select

### Status
- [ ] PASS
- [ ] FAIL

---

## Test Case 5: Batch Information Displays (Batch Items)

### Steps
1. Find a batch-managed item
2. Click Edit
3. Wait for form to load
4. Scroll to see batch information

### Expected Results
- ✅ Batch information table visible
- ✅ Table shows batch numbers
- ✅ Table shows quantities
- ✅ Table shows expiry dates

### Actual Results
- [ ] Batch table visible
- [ ] Batch numbers shown
- [ ] Quantities shown
- [ ] Dates shown

### Status
- [ ] PASS
- [ ] FAIL

---

## Test Case 6: Field Enabling/Disabling Works

### Steps
1. Click Edit on an item
2. Wait for form to load
3. Change Approved Qty to 100
4. Observe warehouse fields

### Expected Results
- ✅ Approved warehouse fields enable
- ✅ Approved warehouse dropdown becomes clickable
- ✅ Approved bin dropdown becomes clickable

### Actual Results
- [ ] Approved warehouse enabled
- [ ] Approved bin enabled
- [ ] Fields are clickable

### Status
- [ ] PASS
- [ ] FAIL

---

## Test Case 7: Quantity Change Disables Fields

### Steps
1. Click Edit on an item
2. Set Approved Qty = 100
3. Set Rejected Qty = 50
4. Change Approved Qty to 0
5. Observe warehouse fields

### Expected Results
- ✅ Approved warehouse fields disable (grayed out)
- ✅ Approved warehouse value clears
- ✅ Approved bin value clears
- ✅ Rejected warehouse fields remain enabled

### Actual Results
- [ ] Approved fields disabled
- [ ] Approved values cleared
- [ ] Rejected fields still enabled

### Status
- [ ] PASS
- [ ] FAIL

---

## Test Case 8: Save Item Changes

### Steps
1. Click Edit on an item
2. Change Approved Qty to 100
3. Select Approved warehouse
4. Select Approved bin
5. Click "Save Changes"

### Expected Results
- ✅ Save button shows loading state
- ✅ Success message appears
- ✅ Modal closes
- ✅ Page refreshes
- ✅ Changes saved to database

### Actual Results
- [ ] Button shows loading
- [ ] Success message shown
- [ ] Modal closes
- [ ] Page refreshes
- [ ] Changes saved

### Status
- [ ] PASS
- [ ] FAIL

---

## Test Case 9: API Response Includes New Fields

### Steps
1. Open Developer Tools (F12)
2. Go to Network tab
3. Click Edit on an item
4. Find request to `/grpo-transfer/api/item/[id]`
5. Check response

### Expected Results
- ✅ Response status: 200
- ✅ Response includes `approved_to_warehouse`
- ✅ Response includes `approved_to_bin_code`
- ✅ Response includes `rejected_to_warehouse`
- ✅ Response includes `rejected_to_bin_code`

### Actual Results
- [ ] Status: _______________
- [ ] approved_to_warehouse: _______________
- [ ] approved_to_bin_code: _______________
- [ ] rejected_to_warehouse: _______________
- [ ] rejected_to_bin_code: _______________

### Status
- [ ] PASS
- [ ] FAIL

---

## Test Case 10: No Console Errors

### Steps
1. Open Developer Tools (F12)
2. Go to Console tab
3. Click Edit on an item
4. Check for errors

### Expected Results
- ✅ No red error messages
- ✅ No JavaScript exceptions
- ✅ Only info/warning messages (if any)

### Actual Results
- [ ] No errors
- [ ] No exceptions
- [ ] Console clean

### Status
- [ ] PASS
- [ ] FAIL

---

## Test Case 11: Multiple Items Can Be Edited

### Steps
1. Click Edit on Item 1
2. Close modal
3. Click Edit on Item 2
4. Verify Item 2 data loads
5. Close modal
6. Click Edit on Item 3
7. Verify Item 3 data loads

### Expected Results
- ✅ Each item loads correctly
- ✅ No data mixing between items
- ✅ Modal opens/closes smoothly

### Actual Results
- [ ] Item 1 loads correctly
- [ ] Item 2 loads correctly
- [ ] Item 3 loads correctly
- [ ] No data mixing

### Status
- [ ] PASS
- [ ] FAIL

---

## Test Case 12: Backward Compatibility

### Steps
1. Edit an item created before the fix
2. Verify old warehouse data still loads
3. Verify new warehouse fields are empty (NULL)

### Expected Results
- ✅ Old `to_warehouse` field loads
- ✅ Old `to_bin_code` field loads
- ✅ New fields are empty/NULL
- ✅ No errors

### Actual Results
- [ ] Old warehouse loads
- [ ] Old bin loads
- [ ] New fields empty
- [ ] No errors

### Status
- [ ] PASS
- [ ] FAIL

---

## Summary

### Test Results
| Test Case | Status | Notes |
|-----------|--------|-------|
| 1. Modal Opens | [ ] PASS / [ ] FAIL | |
| 2. Data Loads | [ ] PASS / [ ] FAIL | |
| 3. Warehouse Sections | [ ] PASS / [ ] FAIL | |
| 4. Dropdowns Load | [ ] PASS / [ ] FAIL | |
| 5. Batch Info | [ ] PASS / [ ] FAIL | |
| 6. Field Enabling | [ ] PASS / [ ] FAIL | |
| 7. Field Disabling | [ ] PASS / [ ] FAIL | |
| 8. Save Changes | [ ] PASS / [ ] FAIL | |
| 9. API Response | [ ] PASS / [ ] FAIL | |
| 10. No Errors | [ ] PASS / [ ] FAIL | |
| 11. Multiple Items | [ ] PASS / [ ] FAIL | |
| 12. Backward Compat | [ ] PASS / [ ] FAIL | |

### Overall Status
- [ ] ALL TESTS PASSED ✅
- [ ] SOME TESTS FAILED ⚠️
- [ ] CRITICAL FAILURES ❌

---

## Issues Found

```
[Space for documenting any issues found during testing]
```

---

## Sign-Off

**Tested By**: _______________  
**Date**: _______________  
**Status**: [ ] APPROVED / [ ] NEEDS FIXES

**Notes**:
```
[Space for additional notes]
```

---

## Troubleshooting

### Issue: Modal doesn't open
**Solution**: 
1. Clear browser cache (Ctrl+Shift+Delete)
2. Restart application
3. Check browser console for errors

### Issue: Fields not loading
**Solution**:
1. Check API response in Network tab
2. Verify database migration applied
3. Check application logs for errors

### Issue: Warehouse dropdowns empty
**Solution**:
1. Verify warehouses configured in SAP B1
2. Check user permissions
3. Verify API endpoint `/grpo-transfer/api/warehouses` works

### Issue: Save button not working
**Solution**:
1. Check browser console for errors
2. Verify all required fields filled
3. Check application logs

---

**Test Guide Version**: 1.0  
**Last Updated**: January 28, 2026  
**Status**: Ready for Testing
