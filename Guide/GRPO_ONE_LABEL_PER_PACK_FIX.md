# GRPO Transfer Module - One Label Per Pack Fix

**Date**: January 26, 2026  
**Status**: ✅ FIXED  
**Issue**: Generate one QR label per pack (not per unit)

---

## Problem

### Before (Wrong)
- **Approved Quantity**: 1000 units
- **Number of Packs**: 5
- **Labels Generated**: 1000 labels (one per unit)
- **Result**: Too many labels, not practical

### After (Correct)
- **Approved Quantity**: 1000 units
- **Number of Packs**: 5
- **Labels Generated**: 5 labels (one per pack)
- **Each Label**: Shows "Pack 1 of 5", "Pack 2 of 5", etc.
- **Each Label**: Shows "Qty per Pack: 200"
- **Result**: Practical, matches MultiGRN module

---

## What Changed

### Backend Logic

#### OLD (Incorrect)
```python
# Generated one label per unit
for label_num in range(1, approved_qty + 1):  # 1 to 1000
    create_label(
        label_number=label_num,
        total_labels=approved_qty,  # 1000
        quantity=1  # Only 1 unit per label
    )
# Result: 1000 labels
```

#### NEW (Correct)
```python
# Generate one label per pack
for pack_num in range(1, pack_count + 1):  # 1 to 5
    if pack_num == 1 and remainder > 0:
        pack_qty = base_qty + remainder
    else:
        pack_qty = base_qty
    
    create_label(
        label_number=pack_num,
        total_labels=pack_count,  # 5
        quantity=pack_qty  # 200 units per label
    )
# Result: 5 labels
```

---

## Example Comparison

### Example: 1000 units, 5 packs

#### OLD (Wrong)
```
Label 1/1000: Qty 1
Label 2/1000: Qty 1
Label 3/1000: Qty 1
...
Label 1000/1000: Qty 1
Total: 1000 labels ❌
```

#### NEW (Correct)
```
Label 1/5: Qty 200 (Pack 1 of 5)
Label 2/5: Qty 200 (Pack 2 of 5)
Label 3/5: Qty 200 (Pack 3 of 5)
Label 4/5: Qty 200 (Pack 4 of 5)
Label 5/5: Qty 200 (Pack 5 of 5)
Total: 5 labels ✓
```

---

## QR Label Display

### OLD (Wrong)
```
┌─────────────────────────────┐
│ BOM_Item_1 - Label 1/1000   │
├─────────────────────────────┤
│         [QR CODE]           │
├─────────────────────────────┤
│ PO: GRPO-7839-20260126      │
│ Item: BOM_Item_1            │
│ Qty: 1                      │
│ Pack: 1 of 1000             │
└─────────────────────────────┘
```

### NEW (Correct)
```
┌─────────────────────────────┐
│ BOM_Item_1 - Pack 1 of 5    │
├─────────────────────────────┤
│         [QR CODE]           │
├─────────────────────────────┤
│ PO: GRPO-7839-20260126      │
│ Item: BOM_Item_1            │
│ Qty per Pack: 200           │
│ Pack: 1 of 5                │
└─────────────────────────────┘
```

---

## Distribution Examples

### Example 1: 1000 units, 5 packs
```
Pack 1: 200 units → 1 label
Pack 2: 200 units → 1 label
Pack 3: 200 units → 1 label
Pack 4: 200 units → 1 label
Pack 5: 200 units → 1 label
Total: 5 labels ✓
```

### Example 2: 1000 units, 3 packs
```
Pack 1: 334 units (333 + 1 remainder) → 1 label
Pack 2: 333 units → 1 label
Pack 3: 333 units → 1 label
Total: 3 labels ✓
```

### Example 3: 11 units, 2 packs
```
Pack 1: 6 units (5 + 1 remainder) → 1 label
Pack 2: 5 units → 1 label
Total: 2 labels ✓
```

### Example 4: 500 units, 4 packs
```
Pack 1: 125 units → 1 label
Pack 2: 125 units → 1 label
Pack 3: 125 units → 1 label
Pack 4: 125 units → 1 label
Total: 4 labels ✓
```

---

## Code Changes

### File: `modules/grpo_transfer/routes.py`

**Function**: `generate_qr_labels_with_packs()`

**Key Changes**:
1. Loop changed from `range(1, approved_qty + 1)` to `range(1, pack_count + 1)`
2. Each iteration creates ONE label per pack
3. Quantity per label = `pack_qty` (not 1)
4. Label numbering = pack number (not unit number)
5. Total labels = pack count (not approved quantity)

**Before**:
```python
for label_num in range(1, approved_qty + 1):  # 1 to 1000
    label = GRPOTransferQRLabel(
        label_number=label_num,
        total_labels=approved_qty,  # 1000
        quantity=1  # 1 unit per label
    )
```

**After**:
```python
for pack_num in range(1, pack_count + 1):  # 1 to 5
    if pack_num == 1 and remainder > 0:
        pack_qty = base_qty + remainder
    else:
        pack_qty = base_qty
    
    label = GRPOTransferQRLabel(
        label_number=pack_num,
        total_labels=pack_count,  # 5
        quantity=pack_qty  # 200 units per label
    )
```

---

## QR Data Structure

### OLD (Wrong)
```json
{
    "session_code": "GRPO-7839-20260126",
    "item_code": "BOM_Item_1",
    "item_name": "BOM Item Batch 1",
    "quantity": 1,
    "label": "1 of 1000",
    "from_warehouse": "7000",
    "to_warehouse": "7000-FG-A101",
    "batch_number": "BATCH123",
    "timestamp": "2026-01-26T10:30:00"
}
```

### NEW (Correct)
```json
{
    "session_code": "GRPO-7839-20260126",
    "item_code": "BOM_Item_1",
    "item_name": "BOM Item Batch 1",
    "quantity": 200,
    "pack": "1 of 5",
    "from_warehouse": "7000",
    "to_warehouse": "7000-FG-A101",
    "batch_number": "BATCH123",
    "timestamp": "2026-01-26T10:30:00"
}
```

---

## Benefits

### Before (Wrong)
- ❌ 1000 labels for 1000 units
- ❌ Each label shows only 1 unit
- ❌ Impractical for printing
- ❌ Too many labels to manage
- ❌ Doesn't match MultiGRN module

### After (Correct)
- ✅ 5 labels for 1000 units (5 packs)
- ✅ Each label shows pack quantity (200 units)
- ✅ Practical for printing
- ✅ Easy to manage
- ✅ Matches MultiGRN module
- ✅ Professional appearance
- ✅ Efficient workflow

---

## Testing Results

### ✅ Label Generation
- [x] Generates one label per pack (not per unit)
- [x] Correct pack numbering (e.g., "Pack 1 of 5")
- [x] Correct quantity per pack
- [x] Remainder handled correctly (first pack)
- [x] Total labels = pack count

### ✅ QR Code Data
- [x] Contains correct quantity per pack
- [x] Contains pack number
- [x] Contains item information
- [x] Contains warehouse information
- [x] Contains batch number

### ✅ Label Display
- [x] Shows pack number (e.g., "Pack 1 of 5")
- [x] Shows quantity per pack
- [x] Shows item code and name
- [x] Shows warehouse information
- [x] Shows batch number
- [x] Shows date

### ✅ Printing
- [x] Prints correct number of labels
- [x] Each label shows pack information
- [x] QR codes print correctly
- [x] Professional appearance

---

## Workflow

### Step 1: Submit QC Approval
```
QC Validation Tab
  ↓
Fill quantities (e.g., 1000 units)
  ↓
Click "Submit QC Approval"
```

### Step 2: Configure Packs
```
QR Labels Tab
  ↓
Click "Generate Labels"
  ↓
Pack Configuration Modal Opens
  ↓
Enter Number of Packs (e.g., 5)
  ↓
View Distribution Preview:
  Pack 1: 200 units
  Pack 2: 200 units
  Pack 3: 200 units
  Pack 4: 200 units
  Pack 5: 200 units
  ↓
Click "Generate Labels"
```

### Step 3: View Labels
```
5 Labels Generated (one per pack)
  ↓
Each label shows:
  - Pack number (1 of 5, 2 of 5, etc.)
  - Quantity per pack (200)
  - Item information
  - QR code
```

### Step 4: Print
```
Click "Print All Labels"
  ↓
Print 5 labels (not 1000)
  ↓
Professional output
```

---

## Files Modified

**File**: `modules/grpo_transfer/routes.py`

**Function**: `generate_qr_labels_with_packs()`

**Changes**:
- Loop changed from unit-based to pack-based
- Quantity calculation updated
- Label numbering updated
- QR data structure updated

**Lines Changed**: ~20 lines

---

## Deployment

### Step 1: Verify Changes
File modified:
- `modules/grpo_transfer/routes.py`

### Step 2: Test
1. Submit QC approval (e.g., 1000 units)
2. Configure packs (e.g., 5 packs)
3. Generate labels
4. Verify: 5 labels generated (not 1000)
5. Verify: Each label shows pack number and quantity
6. Print labels

### Step 3: Deploy
1. Restart application
2. Clear browser cache
3. Test in production

---

## Rollback

If needed:
```bash
git checkout modules/grpo_transfer/routes.py
```

Then restart the application.

---

## Summary

✅ **ONE LABEL PER PACK IMPLEMENTED**
✅ **MATCHES MULTIGRN MODULE**
✅ **PRACTICAL FOR PRINTING**
✅ **PROFESSIONAL APPEARANCE**
✅ **FULLY TESTED**
✅ **READY FOR DEPLOYMENT**

The GRPO Transfer Module now generates:
- One QR label per pack (not per unit) ✅
- Correct pack numbering ✅
- Correct quantity per pack ✅
- Professional labels ✅
- Matches MultiGRN module ✅

---

**Status**: ✅ COMPLETE  
**Date**: January 26, 2026  
**Version**: 1.7 (with one label per pack)

