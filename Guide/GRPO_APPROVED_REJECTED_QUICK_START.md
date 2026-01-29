# GRPO Transfer: Approved/Rejected Warehouse - Quick Start Guide

## What Changed?

You can now designate **separate warehouses** for approved and rejected quantities when editing GRPO transfer items.

---

## How to Use

### Step 1: Edit an Item
1. Open GRPO Transfer session
2. Click **Edit** button on any item
3. The edit modal now shows **3 warehouse sections**:
   - **From Warehouse** (source - read-only)
   - **Approved Qty Designation Warehouse** (green section)
   - **Rejected Qty Designation Warehouse** (red section)

### Step 2: Enter Quantities
1. Enter **Approved Qty** (e.g., 100)
2. Enter **Rejected Qty** (e.g., 20)
3. The warehouse fields automatically enable/disable based on quantities

### Step 3: Select Warehouses
- **If Approved Qty > 0**: Select warehouse and bin for approved items
- **If Rejected Qty > 0**: Select warehouse and bin for rejected items
- **If Qty = 0**: Fields stay disabled (grayed out)

### Step 4: Save
Click **Save Changes** - validation ensures:
- ✅ At least one quantity > 0
- ✅ Approved warehouse selected if Approved Qty > 0
- ✅ Rejected warehouse selected if Rejected Qty > 0

### Step 5: Post Transfers
When posting to SAP B1:
- **Approved Transfer**: Uses approved warehouse/bin
- **Rejected Transfer**: Uses rejected warehouse/bin
- Creates **2 separate SAP Stock Transfer documents** (if both quantities > 0)

---

## Field Enabling Rules

| Approved Qty | Rejected Qty | Approved Fields | Rejected Fields |
|-------------|-------------|-----------------|-----------------|
| > 0 | > 0 | ✅ Enabled | ✅ Enabled |
| > 0 | 0 | ✅ Enabled | ❌ Disabled |
| 0 | > 0 | ❌ Disabled | ✅ Enabled |
| 0 | 0 | ❌ Disabled | ❌ Disabled |

---

## Example Workflow

**Scenario**: Received 500 units of Item_A
- 450 units approved → Transfer to QFG warehouse
- 50 units rejected → Transfer to RJT warehouse

**Steps**:
1. Edit Item_A
2. Set Approved Qty = 450
3. Set Rejected Qty = 50
4. Select "7000-QFG" for Approved warehouse
5. Select "7000-RJT" for Rejected warehouse
6. Save
7. Post to SAP B1 → Creates 2 transfers:
   - Transfer 1: 450 units to 7000-QFG
   - Transfer 2: 50 units to 7000-RJT

---

## Validation Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "At least one of Approved or Rejected quantity must be > 0" | Both quantities are 0 | Enter at least one quantity > 0 |
| "Please select a destination warehouse for approved quantity" | Approved Qty > 0 but no warehouse selected | Select warehouse in Approved section |
| "Please select a destination warehouse for rejected quantity" | Rejected Qty > 0 but no warehouse selected | Select warehouse in Rejected section |
| "Approved + Rejected cannot exceed Received" | Sum exceeds received quantity | Reduce quantities |

---

## Backward Compatibility

✅ **Existing sessions still work!**
- Old sessions with single "To Warehouse" continue to work
- New sessions use separate approved/rejected warehouses
- System automatically falls back to legacy warehouse if new fields not set

---

## Database Migration

**Required before using this feature:**

```bash
# Apply migration
mysql -u [user] -p [database] < migrations/mysql/changes/2026-01-28_grpo_transfer_approved_rejected_warehouse.sql
```

**What it does**:
- Adds 6 new columns to `grpo_transfer_items` table
- Creates indexes for performance
- No data loss - existing data preserved

---

## SAP B1 Integration

### Approved Transfer
- **Document Type**: Stock Transfer
- **From Warehouse**: Source warehouse (GRPO)
- **To Warehouse**: Approved warehouse (designated in modal)
- **Quantity**: Approved quantity only

### Rejected Transfer
- **Document Type**: Stock Transfer
- **From Warehouse**: Source warehouse (GRPO)
- **To Warehouse**: Rejected warehouse (designated in modal)
- **Quantity**: Rejected quantity only

---

## Tips & Best Practices

1. **Use Consistent Warehouses**
   - Approved items → QFG (Quality Finished Goods)
   - Rejected items → RJT (Rejected)

2. **Batch Items**
   - Batch numbers automatically included in transfers
   - Each batch gets its own line in SAP

3. **Non-Batch Items**
   - No batch numbers in transfer
   - Quantity transferred as-is

4. **Bin Codes**
   - Optional but recommended
   - Improves warehouse tracking
   - Automatically loaded based on warehouse selection

5. **Audit Trail**
   - All transfers logged in session audit log
   - SAP document numbers recorded
   - User and timestamp tracked

---

## Troubleshooting

**Q: Warehouse dropdown is empty**
- A: Check that warehouses are configured in SAP B1
- A: Verify user has access to warehouses

**Q: Bin codes not loading**
- A: Select warehouse first
- A: Check that bins are configured for warehouse in SAP B1

**Q: Transfer failed in SAP B1**
- A: Check SAP B1 logs for error details
- A: Verify warehouse codes are correct
- A: Ensure item exists in SAP B1

**Q: Can I change warehouse after saving?**
- A: Yes, click Edit again and change warehouse
- A: Changes only affect future transfers

---

## Support

For issues:
1. Check the audit log in session details
2. Review SAP B1 Stock Transfer documents
3. Verify warehouse configuration in SAP B1
4. Check application logs for API errors

---

## Version Info

- **Feature**: Approved/Rejected Warehouse Designation
- **Release Date**: January 28, 2026
- **Status**: Production Ready
- **Backward Compatible**: Yes
