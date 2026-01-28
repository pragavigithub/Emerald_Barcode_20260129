# GRPO Transfer Module - Quick Test Guide

**Date**: January 26, 2026  
**Status**: ✅ FIXED & READY TO TEST

---

## Quick Test (5 minutes)

### Step 1: Create a Test Session
1. Go to GRPO Transfer module
2. Select a GRPO document
3. Create a new session

### Step 2: Submit QC Approval
1. Go to "QC Validation" tab
2. Approve items with quantities (e.g., 500 units)
3. Click "Submit QC Approval"

### Step 3: Generate Labels with Packs
1. Go to "QR Labels" tab
2. Click "Generate Labels" button
3. Pack Configuration Modal opens
4. Enter number of packs (e.g., 2)
5. View distribution preview:
   - Pack 1: 250 units
   - Pack 2: 250 units
6. Click "Generate Labels"

### Step 4: Verify Labels Display
✅ **Check these things**:
- [ ] 2 labels displayed (not 500)
- [ ] Label header shows: "BOM_Item_1 - Label 1/2" (item code, not ID)
- [ ] Each label shows:
  - Item Code: "BOM_Item_1"
  - Quantity: 250
  - Pack: "1 of 2" or "2 of 2"
  - QR Code image
- [ ] Print button works

### Step 5: Print Labels
1. Click "Print All Labels"
2. Print window opens
3. Verify 2 labels in print preview (not 500)
4. Print or close

---

## What Was Fixed

### The Bug
The API was returning `item_id` (database ID like "42") instead of `item_code` (like "BOM_Item_1") in the labels list.

### The Fix
Updated `get_session_labels()` function to:
1. Look up the actual item using `item_id`
2. Return the `item_code` field
3. Fallback to 'Unknown' if item not found

### Result
Labels now display with correct item code in the grid header.

---

## Test Scenarios

### Scenario 1: Basic Test (2 packs)
```
Approved Qty: 500
Packs: 2

Expected:
✅ 2 labels generated
✅ Label 1: Pack 1 of 2, Qty 250
✅ Label 2: Pack 2 of 2, Qty 250
✅ Item code displays correctly
```

### Scenario 2: Multiple Packs (5 packs)
```
Approved Qty: 1000
Packs: 5

Expected:
✅ 5 labels generated
✅ Each label: Qty 200
✅ Item code displays correctly
```

### Scenario 3: With Remainder (3 packs)
```
Approved Qty: 1000
Packs: 3

Expected:
✅ 3 labels generated
✅ Label 1: Qty 334 (333 + 1 remainder)
✅ Label 2: Qty 333
✅ Label 3: Qty 333
✅ Total: 1000
✅ Item code displays correctly
```

### Scenario 4: Multiple Items
```
Item 1: Qty 500, 2 packs
Item 2: Qty 1000, 5 packs

Expected:
✅ 7 labels total
✅ Item 1 labels show "Item_Code_1"
✅ Item 2 labels show "Item_Code_2"
✅ Each shows correct item code
```

---

## Verification Checklist

### ✅ Frontend Display
- [ ] Labels display in grid
- [ ] Item code shows in header (not item ID)
- [ ] Correct number of labels
- [ ] Correct pack numbering
- [ ] Correct quantities
- [ ] QR codes display
- [ ] Print button works

### ✅ Database
- [ ] Correct number of labels in database
- [ ] Correct quantities per pack
- [ ] Correct pack numbering
- [ ] Old labels deleted before generation

### ✅ API Response
- [ ] Returns item_code (not item_id)
- [ ] All fields present
- [ ] Valid JSON format
- [ ] Success flag is true

### ✅ Complete Workflow
- [ ] QC approval works
- [ ] Pack configuration works
- [ ] Label generation works
- [ ] Label display works
- [ ] Print works

---

## Browser Console Check

Open browser console (F12) and check for:
- ✅ No JavaScript errors
- ✅ No 404 errors
- ✅ No CORS errors
- ✅ API calls return 200 status

---

## Database Check

Run these queries to verify:

```sql
-- Count labels for a session
SELECT COUNT(*) as total_labels FROM grpo_transfer_qr_labels WHERE session_id = 15;

-- View label details
SELECT id, item_id, label_number, total_labels, quantity 
FROM grpo_transfer_qr_labels 
WHERE session_id = 15
ORDER BY label_number;

-- Verify quantities sum correctly
SELECT SUM(quantity) as total_quantity 
FROM grpo_transfer_qr_labels 
WHERE session_id = 15;
```

Expected results:
- total_labels: 2 (not 500)
- Each label has correct quantity
- Sum equals approved quantity

---

## Troubleshooting

### Issue: Still showing 500 labels
**Solution**: 
1. Clear browser cache (Ctrl+Shift+Delete)
2. Refresh page (Ctrl+F5)
3. Check database to verify only 2 labels exist
4. Check application logs for errors

### Issue: Item code shows as number (e.g., "42")
**Solution**:
1. Verify code fix was deployed
2. Restart application
3. Clear browser cache
4. Refresh page

### Issue: Print shows 500 labels
**Solution**:
1. Check database - should only have 2 labels
2. If database has 500 labels, old labels weren't deleted
3. Check application logs for deletion errors
4. Manually delete old labels and regenerate

### Issue: QR codes not displaying
**Solution**:
1. Check browser console for errors
2. Verify QR Server API is accessible
3. Check network tab for failed requests
4. Try different browser

---

## Logs to Check

### Application Logs
```
Look for:
✅ "Deleted X old labels for session Y"
✅ "Item BOM_Item_1: approved_qty=500, pack_count=2"
✅ "Creating label: pack_num=1, pack_count=2, pack_qty=250"
✅ "Generated 2 QR labels (one per pack) for session Y"
```

### Browser Console
```
Look for:
✅ No errors
✅ API calls returning 200
✅ Labels array with correct item_code
```

---

## Success Criteria

### ✅ All of these must be true:
1. [ ] 2 labels generated (not 500)
2. [ ] Item code displays correctly in header
3. [ ] Each label shows correct pack number
4. [ ] Each label shows correct quantity
5. [ ] QR codes display correctly
6. [ ] Print functionality works
7. [ ] Database has correct data
8. [ ] No errors in logs or console

---

## Next Steps

### If Test Passes ✅
1. Test with multiple items
2. Test with different pack counts
3. Test print functionality
4. Deploy to production

### If Test Fails ❌
1. Check browser console for errors
2. Check application logs
3. Check database
4. Review code changes
5. Contact support

---

## Files Modified

**File**: `modules/grpo_transfer/routes.py`

**Function**: `get_session_labels()`

**Change**: Fixed item_code retrieval from database

---

## Support

If you encounter any issues:
1. Check the troubleshooting section above
2. Review the application logs
3. Check the browser console
4. Verify database data
5. Contact the development team

---

**Status**: ✅ READY FOR TESTING  
**Date**: January 26, 2026  
**Version**: 1.9
