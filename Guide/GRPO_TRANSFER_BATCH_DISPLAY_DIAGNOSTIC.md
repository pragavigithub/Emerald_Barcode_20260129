# GRPO Transfer - Batch Number Display Diagnostic Guide
**Date**: January 26, 2026

---

## Issue: Batch Numbers Showing "N/A" in Transfer Preview

### Current State
- ✅ From Warehouse: 7000-FG (displaying correctly)
- ✅ From Bin: 7000-FG-A101 (displaying correctly)
- ✅ To Warehouse: 7000-QFG (displaying correctly)
- ✅ To Bin: 7000-QFG-A102 (displaying correctly)
- ❌ Batch Number: N/A (should show actual batch number)

---

## Root Cause Analysis

### Why Batch Numbers Show "N/A"

The transfer preview code checks:
```javascript
if (item.is_batch_item && item.batches && item.batches.length > 0) {
    // Show batch numbers
} else {
    // Show "N/A"
}
```

**Batch numbers show "N/A" when**:
1. `item.is_batch_item === false` (item not marked as batch item)
2. `item.batches === undefined` (batches not included in response)
3. `item.batches.length === 0` (no batches found)

---

## Diagnostic Steps

### Step 1: Check if Batches Were Fetched During Session Creation

**What to Check**:
1. Open browser DevTools (F12)
2. Go to Network tab
3. Create a new GRPO Transfer session
4. Look for API calls to SAP B1
5. Check if `Get_Batches_By_DocEntry` query was called

**Expected**:
- Should see POST request to `/b1s/v1/SQLQueries('Get_Batches_By_DocEntry')/List`
- Response should include batch numbers

**If Not Found**:
- Batches are not being fetched during session creation
- Check server logs for errors

### Step 2: Check if Batches Are in Database

**What to Check**:
1. Open database client (e.g., MySQL Workbench)
2. Query: `SELECT * FROM grpo_transfer_batches WHERE item_id = {item_id}`
3. Check if batches exist for the item

**Expected**:
- Should see rows with batch_number, batch_quantity, etc.

**If Empty**:
- Batches were not saved to database
- Check if batch fetch failed or batches weren't linked to items

### Step 3: Check if is_batch_item is Set

**What to Check**:
1. Query: `SELECT id, item_code, is_batch_item FROM grpo_transfer_items WHERE session_id = {session_id}`
2. Check if `is_batch_item` is 1 (true) for batch items

**Expected**:
- Batch items should have `is_batch_item = 1`
- Non-batch items should have `is_batch_item = 0`

**If All 0**:
- Items are not being marked as batch items
- Check if batch fetch is working

### Step 4: Check if Batches Are in Session Data Response

**What to Check**:
1. Open browser DevTools (F12)
2. Go to Network tab
3. Click "Post to SAP B1" button
4. Look for GET request to `/grpo-transfer/api/session/{session_id}`
5. Check response JSON for `batches` field

**Expected Response**:
```json
{
  "success": true,
  "session": {
    "items": [{
      "item_code": "BOM_Item_1",
      "is_batch_item": true,
      "batches": [{
        "batch_number": "20251216-BOM_Item_1",
        "batch_quantity": 1000,
        "approved_quantity": 600,
        "rejected_quantity": 400
      }]
    }]
  }
}
```

**If Batches Missing**:
- Batches not included in API response
- Check `get_session_data()` function

### Step 5: Check Browser Console for JavaScript Errors

**What to Check**:
1. Open browser DevTools (F12)
2. Go to Console tab
3. Look for any JavaScript errors
4. Check if `buildTransferPreview()` is being called

**Expected**:
- No errors
- `buildTransferPreview()` should be called when modal opens

---

## Common Issues and Solutions

### Issue 1: Batches Not Fetched During Session Creation

**Symptoms**:
- Database has no rows in `grpo_transfer_batches` table
- `is_batch_item` is 0 for all items

**Possible Causes**:
1. SAP B1 API not responding
2. `Get_Batches_By_DocEntry` query not configured in SAP
3. Network connectivity issue

**Solution**:
1. Check server logs for batch fetch errors
2. Verify SAP B1 query exists: `Get_Batches_By_DocEntry`
3. Test SAP B1 API directly using Postman:
   ```
   POST https://192.168.1.4:50000/b1s/v1/SQLQueries('Get_Batches_By_DocEntry')/List
   Body: {"ParamList": "docEntry='7840'"}
   ```

### Issue 2: Batches Fetched But Not Linked to Items

**Symptoms**:
- Database has rows in `grpo_transfer_batches` table
- But `is_batch_item` is still 0

**Possible Causes**:
1. Item code mismatch between GRPO and batch query
2. Batch linking logic not working

**Solution**:
1. Check if item codes match:
   ```sql
   SELECT DISTINCT item_code FROM grpo_transfer_items WHERE session_id = {session_id};
   SELECT DISTINCT ItemCode FROM grpo_transfer_batches WHERE item_id IN (SELECT id FROM grpo_transfer_items WHERE session_id = {session_id});
   ```
2. Verify batch linking code in `create_session_view()`

### Issue 3: Batches in Database But Not in API Response

**Symptoms**:
- Database has batches
- `is_batch_item` is 1
- But API response doesn't include batches

**Possible Causes**:
1. `get_session_data()` not including batches
2. Batches not loaded from database

**Solution**:
1. Check `get_session_data()` function includes batches
2. Verify batches are being loaded: `item.batches`

### Issue 4: Batches in API Response But Not Displaying

**Symptoms**:
- API response includes batches
- But transfer preview shows "N/A"

**Possible Causes**:
1. JavaScript error in `buildTransferPreview()`
2. Condition checking wrong field

**Solution**:
1. Check browser console for errors
2. Add console.log to debug:
   ```javascript
   console.log('item.is_batch_item:', item.is_batch_item);
   console.log('item.batches:', item.batches);
   console.log('item.batches.length:', item.batches ? item.batches.length : 0);
   ```

---

## Debug Queries

### Check Session Items
```sql
SELECT 
  id, 
  item_code, 
  is_batch_item, 
  approved_quantity, 
  rejected_quantity,
  from_warehouse,
  from_bin_code,
  to_warehouse,
  to_bin_code
FROM grpo_transfer_items 
WHERE session_id = {session_id};
```

### Check Batches for Item
```sql
SELECT 
  id,
  batch_number,
  batch_quantity,
  approved_quantity,
  rejected_quantity,
  expiry_date
FROM grpo_transfer_batches 
WHERE item_id = {item_id};
```

### Check All Batches for Session
```sql
SELECT 
  b.id,
  i.item_code,
  b.batch_number,
  b.batch_quantity,
  b.approved_quantity,
  b.rejected_quantity
FROM grpo_transfer_batches b
JOIN grpo_transfer_items i ON b.item_id = i.id
WHERE i.session_id = {session_id};
```

---

## Server Log Analysis

### Look for These Log Messages

**Successful Batch Fetch**:
```
✅ Retrieved X batch numbers for document {doc_entry}
✅ Added batch {batch_number} for item {item_code}
✅ Batch numbers saved for session {session_id}
```

**Batch Fetch Errors**:
```
⚠️ Skipping batch with NULL/empty batch_number for item {item_code}
Failed to fetch batch numbers: {error}
Error fetching batch numbers: {error}
```

**Missing Batches**:
```
No batch numbers found for document {doc_entry}
```

---

## Testing Checklist

- [ ] Verify SAP B1 `Get_Batches_By_DocEntry` query exists
- [ ] Test SAP B1 API directly with Postman
- [ ] Check server logs for batch fetch errors
- [ ] Query database for batches
- [ ] Check if `is_batch_item` is set correctly
- [ ] Check API response includes batches
- [ ] Check browser console for JavaScript errors
- [ ] Verify `buildTransferPreview()` is displaying batches

---

## Quick Fix Checklist

If batch numbers are still showing "N/A":

1. **Check Server Logs**
   - Look for batch fetch errors
   - Verify batches are being saved

2. **Check Database**
   - Verify batches exist in `grpo_transfer_batches` table
   - Verify `is_batch_item` is set to 1

3. **Check API Response**
   - Verify `/grpo-transfer/api/session/{id}` includes batches
   - Check if batches array is populated

4. **Check Frontend**
   - Open browser console
   - Check for JavaScript errors
   - Verify `buildTransferPreview()` is being called

5. **Check Transfer Preview Logic**
   - Verify condition: `if (item.is_batch_item && item.batches && item.batches.length > 0)`
   - Add console.log to debug

---

## Next Steps

1. Run diagnostic steps above
2. Identify which step is failing
3. Fix the issue at that step
4. Verify batch numbers display correctly in transfer preview
5. Test SAP B1 transfer posting with batch numbers

---

**Status**: Diagnostic Guide Ready  
**Last Updated**: January 26, 2026
