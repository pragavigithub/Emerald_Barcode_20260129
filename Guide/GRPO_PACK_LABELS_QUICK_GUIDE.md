# GRPO Pack-Based Labels - Quick Guide

## How to Generate Labels with Packs

### Step 1: Submit QC Approval
1. Go to **QC Validation** tab
2. Fill in quantities for items
3. Click **Submit QC Approval**

### Step 2: Configure Packs
1. Go to **QR Labels** tab
2. Click **Generate Labels** button
3. **Pack Configuration Modal Opens**
4. For each item:
   - See the **Approved Quantity**
   - Enter **Number of Packs**
   - View **Pack Distribution** preview
5. Click **Generate Labels**

### Step 3: View Labels
- Labels display in grid format
- Each label shows pack number (e.g., "Pack 1 of 5")
- Shows quantity per pack

### Step 4: Print Labels
- Click **Print All Labels** button
- Print window opens
- Click **Print Labels** to print

---

## Pack Distribution Examples

### Example 1: Even Distribution
**Approved Qty**: 1000  
**Packs**: 5

```
Pack 1: 200 units
Pack 2: 200 units
Pack 3: 200 units
Pack 4: 200 units
Pack 5: 200 units
```

### Example 2: Uneven Distribution
**Approved Qty**: 1000  
**Packs**: 3

```
Pack 1: 334 units (gets remainder)
Pack 2: 333 units
Pack 3: 333 units
```

### Example 3: Small Quantity
**Approved Qty**: 11  
**Packs**: 2

```
Pack 1: 6 units (gets remainder)
Pack 2: 5 units
```

---

## Key Features

✅ **Configurable Packs** - Set any number of packs  
✅ **Real-Time Preview** - See distribution before generating  
✅ **Automatic Distribution** - Quantity split evenly  
✅ **Remainder Handling** - First pack gets remainder  
✅ **QR Codes** - One per pack  
✅ **Professional Labels** - Print-ready format  

---

## Distribution Algorithm

```
base_qty = approved_qty ÷ pack_count (integer division)
remainder = approved_qty % pack_count

For each pack:
  if pack == 1 and remainder > 0:
    pack_qty = base_qty + remainder
  else:
    pack_qty = base_qty
```

---

## Tips

1. **Default Packs**: System suggests 1 pack per 1000 units
2. **Minimum**: At least 1 pack required
3. **Preview**: Always check distribution before generating
4. **Print**: Use color printer for best QR code quality
5. **Paper**: Use A4 or Letter size

---

## Troubleshooting

### Modal Not Opening
- Verify QC approval was submitted
- Check if items are approved
- Refresh page

### Distribution Not Showing
- Enter pack count and press Tab/Enter
- Check browser console for errors

### Labels Not Generating
- Verify pack count is valid (≥ 1)
- Check internet connection
- Try again

---

## Questions?

See full documentation: `GRPO_PACK_BASED_LABELS_FEATURE.md`

