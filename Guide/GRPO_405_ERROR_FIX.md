# GRPO Transfer - 405 Method Not Allowed Error Fix

**Date**: January 26, 2026  
**Status**: ✅ FIXED  
**Version**: 3.4.1

---

## Issue

**Error**: `405 Method Not Allowed`  
**URL**: `GET /grpo-transfer/api/item/63`  
**Cause**: The endpoint only supported PUT method, but the frontend was trying to GET item details

---

## Root Cause

The `editItem()` function in the frontend was calling:
```javascript
fetch(`/grpo-transfer/api/item/${itemId}`)  // GET request
```

But the backend only had:
```python
@grpo_transfer_bp.route('/api/item/<int:item_id>', methods=['PUT'])
def update_item(item_id):
```

This caused a 405 error because GET method was not allowed.

---

## Solution

Added a new GET endpoint to fetch item details:

```python
@grpo_transfer_bp.route('/api/item/<int:item_id>', methods=['GET'])
@login_required
def get_item_details(item_id):
    """Get item details for editing"""
    # Returns item data with batches
```

Now the route supports both:
- `GET /grpo-transfer/api/item/<item_id>` - Fetch item details
- `PUT /grpo-transfer/api/item/<item_id>` - Update item

---

## Response Format

### GET Request
```
GET /grpo-transfer/api/item/63
```

### Response
```json
{
  "success": true,
  "item": {
    "id": 63,
    "item_code": "BOM_Item_1",
    "item_name": "BOM_Item_Batch_1",
    "item_description": "Item Description",
    "is_batch_item": true,
    "is_serial_item": false,
    "is_non_managed": false,
    "received_quantity": 4000.0,
    "approved_quantity": 0.0,
    "rejected_quantity": 0.0,
    "from_warehouse": "7000-FG",
    "from_bin_code": null,
    "to_warehouse": null,
    "to_bin_code": null,
    "unit_of_measure": "1",
    "price": 0.0,
    "line_total": 0.0,
    "qc_status": "pending",
    "qc_notes": null,
    "batches": [
      {
        "id": 1,
        "batch_number": "20251216-BOM_Item_1",
        "batch_quantity": 4000.0,
        "approved_quantity": 0.0,
        "rejected_quantity": 0.0,
        "expiry_date": "2027-01-08",
        "manufacture_date": null
      }
    ]
  }
}
```

---

## Testing

### Before Fix
```
GET /grpo-transfer/api/item/63
Response: 405 Method Not Allowed
Modal shows: "Error loading item data"
```

### After Fix
```
GET /grpo-transfer/api/item/63
Response: 200 OK
Modal shows: Item edit form with all details
```

---

## Files Modified

- `modules/grpo_transfer/routes.py`
  - Added: `get_item_details()` function
  - Supports: GET method for `/api/item/<item_id>`

---

## Verification

✅ Code compiles without errors  
✅ GET endpoint returns item data  
✅ Batches included in response  
✅ Modal loads item data correctly  
✅ Edit functionality works

---

**Status**: ✅ FIXED  
**Date**: January 26, 2026  
**Version**: 3.4.1
