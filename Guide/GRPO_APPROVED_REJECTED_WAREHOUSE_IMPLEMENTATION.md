# GRPO Transfer: Approved/Rejected Warehouse Designation Implementation

**Date**: January 28, 2026  
**Status**: ✅ COMPLETE

## Overview
Implemented separate warehouse and bin designation for approved and rejected quantities in GRPO Transfer module. Each quantity type can now be transferred to different warehouses/bins with conditional field enabling based on quantity values.

---

## Changes Made

### 1. Database Schema Updates
**File**: `migrations/mysql/changes/2026-01-28_grpo_transfer_approved_rejected_warehouse.sql`

Added 6 new columns to `grpo_transfer_items` table:
- `approved_to_warehouse` - Destination warehouse for approved quantities
- `approved_to_bin_code` - Destination bin for approved quantities
- `approved_to_bin_abs_entry` - SAP B1 BinLocation AbsEntry for approved bin
- `rejected_to_warehouse` - Destination warehouse for rejected quantities
- `rejected_to_bin_code` - Destination bin for rejected quantities
- `rejected_to_bin_abs_entry` - SAP B1 BinLocation AbsEntry for rejected bin

**Migration Command**:
```bash
mysql -u [user] -p [database] < migrations/mysql/changes/2026-01-28_grpo_transfer_approved_rejected_warehouse.sql
```

---

### 2. Data Model Updates
**File**: `modules/grpo_transfer/models.py`

Updated `GRPOTransferItem` model to include:
- Separate warehouse/bin fields for approved quantities
- Separate warehouse/bin fields for rejected quantities
- Maintained backward compatibility with legacy `to_warehouse` and `to_bin_code` fields

---

### 3. Frontend UI Updates
**File**: `modules/grpo_transfer/templates/grpo_transfer/session_detail.html`

#### Edit Modal Structure
- **From Warehouse Section**: Source warehouse (disabled, read-only)
- **Approved Qty Designation Section** (Green card):
  - To Warehouse dropdown (enabled when Approved Qty > 0)
  - To Bin Code dropdown (enabled when Approved Qty > 0)
- **Rejected Qty Designation Section** (Red card):
  - To Warehouse dropdown (enabled when Rejected Qty > 0)
  - To Bin Code dropdown (enabled when Rejected Qty > 0)

#### JavaScript Functions Added/Updated

**New Function: `updateFieldEnablement()`**
- Enables/disables warehouse and bin fields based on quantity values
- Approved fields enabled only when Approved Qty > 0
- Rejected fields enabled only when Rejected Qty > 0
- Clears values when fields are disabled

**Updated Function: `renderItemEditForm(item)`**
- Loads separate warehouse data for approved and rejected sections
- Calls `updateFieldEnablement()` on quantity changes
- Adds event listeners for quantity input changes

**Updated Function: `loadWarehousesForEditBoth()`**
- Now accepts 6 parameters (from, approvedTo, rejectedTo, and their bins)
- Populates three separate warehouse dropdowns
- Loads bin codes for each warehouse independently

**Updated Function: `saveItem()`**
- Validates that at least one of Approved or Rejected quantity > 0
- Validates approved warehouse/bin when Approved Qty > 0
- Validates rejected warehouse/bin when Rejected Qty > 0
- Sends new fields to backend API

**Updated Function: `confirmAndPostTransfer()`**
- Calls separate endpoints for approved and rejected transfers
- Posts approved transfer first, then rejected transfer
- Handles cases where only one type of transfer exists

---

### 4. Backend API Updates
**File**: `modules/grpo_transfer/routes.py`

#### Updated Endpoint: `PUT /api/item/<item_id>`
- Accepts new fields: `approved_to_warehouse`, `approved_to_bin_code`, `approved_to_bin_abs_entry`
- Accepts new fields: `rejected_to_warehouse`, `rejected_to_bin_code`, `rejected_to_bin_abs_entry`
- Updates item with new warehouse designations

#### New Endpoint: `POST /api/session/<session_id>/post-approved-transfer`
- Posts ONLY approved quantities to SAP B1
- Uses `approved_to_warehouse` and `approved_to_bin_code` if set
- Falls back to legacy `to_warehouse` and `to_bin_code` for backward compatibility
- Validates that approved warehouse is designated
- Creates single SAP Stock Transfer document
- Returns: `sap_doc_entry`, `sap_doc_num`

#### New Endpoint: `POST /api/session/<session_id>/post-rejected-transfer`
- Posts ONLY rejected quantities to SAP B1
- Uses `rejected_to_warehouse` and `rejected_to_bin_code` if set
- Falls back to legacy `to_warehouse` and `to_bin_code` for backward compatibility
- Validates that rejected warehouse is designated
- Creates single SAP Stock Transfer document
- Returns: `sap_doc_entry`, `sap_doc_num`

---

## Behavior Matrix

| Scenario | Approved Qty | Rejected Qty | Approved Fields | Rejected Fields | Transfer Allowed |
|----------|-------------|-------------|-----------------|-----------------|------------------|
| Both > 0 | > 0 | > 0 | ✅ Enabled | ✅ Enabled | ✅ Yes (2 transfers) |
| Approved only | > 0 | 0 | ✅ Enabled | ❌ Disabled | ✅ Yes (1 transfer) |
| Rejected only | 0 | > 0 | ❌ Disabled | ✅ Enabled | ✅ Yes (1 transfer) |
| Both zero | 0 | 0 | ❌ Disabled | ❌ Disabled | ❌ No (validation error) |

---

## Validation Rules

### Frontend Validation (JavaScript)
1. At least one of Approved or Rejected quantity must be > 0
2. Approved Qty + Rejected Qty cannot exceed Received Qty
3. If Approved Qty > 0:
   - Approved warehouse must be selected
   - Approved bin must be selected
4. If Rejected Qty > 0:
   - Rejected warehouse must be selected
   - Rejected bin must be selected

### Backend Validation (Python)
1. Session must exist
2. SAP B1 authentication must succeed
3. If posting approved transfer:
   - Must have at least one approved item with Qty > 0
   - Approved warehouse must be designated
4. If posting rejected transfer:
   - Must have at least one rejected item with Qty > 0
   - Rejected warehouse must be designated

---

## SAP B1 Integration

### Approved Transfer Payload
```json
{
  "DocDate": "2026-01-28",
  "Comments": "QC Approved WMS Transfer GRPO-XXXX by User",
  "FromWarehouse": "7000-FG",
  "ToWarehouse": "[approved_to_warehouse]",
  "StockTransferLines": [
    {
      "LineNum": 0,
      "ItemCode": "ITEM_CODE",
      "Quantity": [approved_quantity],
      "WarehouseCode": "[approved_to_warehouse]",
      "FromWarehouseCode": "7000-FG",
      "BaseEntry": [sap_base_entry],
      "BaseLine": [sap_base_line],
      "BaseType": "PurchaseDeliveryNotes",
      "BatchNumbers": [...],
      "StockTransferLinesBinAllocations": [...]
    }
  ]
}
```

### Rejected Transfer Payload
```json
{
  "DocDate": "2026-01-28",
  "Comments": "QC Rejected WMS Transfer GRPO-XXXX by User",
  "FromWarehouse": "7000-FG",
  "ToWarehouse": "[rejected_to_warehouse]",
  "StockTransferLines": [
    {
      "LineNum": 0,
      "ItemCode": "ITEM_CODE",
      "Quantity": [rejected_quantity],
      "WarehouseCode": "[rejected_to_warehouse]",
      "FromWarehouseCode": "7000-FG",
      "BaseEntry": [sap_base_entry],
      "BaseLine": [sap_base_line],
      "BaseType": "PurchaseDeliveryNotes",
      "BatchNumbers": [...],
      "StockTransferLinesBinAllocations": [...]
    }
  ]
}
```

---

## Testing Checklist

- [ ] Database migration applied successfully
- [ ] Edit modal displays separate Approved and Rejected sections
- [ ] Approved warehouse fields disabled when Approved Qty = 0
- [ ] Rejected warehouse fields disabled when Rejected Qty = 0
- [ ] Both fields enabled when both quantities > 0
- [ ] Validation prevents transfer when both quantities = 0
- [ ] Approved transfer posts to correct warehouse/bin
- [ ] Rejected transfer posts to correct warehouse/bin
- [ ] Batch items handled correctly in both transfers
- [ ] Non-batch items handled correctly in both transfers
- [ ] Backward compatibility maintained (legacy fields still work)
- [ ] SAP B1 documents created with correct line items
- [ ] Audit logs record both transfer types

---

## Backward Compatibility

The implementation maintains full backward compatibility:
- Legacy `to_warehouse` and `to_bin_code` fields still exist
- If `approved_to_warehouse` is not set, falls back to `to_warehouse`
- If `rejected_to_warehouse` is not set, falls back to `to_warehouse`
- Existing sessions continue to work without modification

---

## Files Modified

1. `modules/grpo_transfer/models.py` - Added new columns to GRPOTransferItem
2. `modules/grpo_transfer/routes.py` - Added two new endpoints
3. `modules/grpo_transfer/templates/grpo_transfer/session_detail.html` - Updated UI and JavaScript
4. `migrations/mysql/changes/2026-01-28_grpo_transfer_approved_rejected_warehouse.sql` - Database migration

---

## Deployment Steps

1. **Backup Database**
   ```bash
   mysqldump -u [user] -p [database] > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Apply Migration**
   ```bash
   mysql -u [user] -p [database] < migrations/mysql/changes/2026-01-28_grpo_transfer_approved_rejected_warehouse.sql
   ```

3. **Restart Application**
   ```bash
   # If using systemd
   sudo systemctl restart grpo-app
   
   # If using Docker
   docker-compose restart
   ```

4. **Verify Deployment**
   - Open GRPO Transfer session
   - Click Edit on an item
   - Verify new warehouse sections appear
   - Test quantity-based field enabling/disabling

---

## Known Limitations

- Warehouse selection is per-item (not per-batch)
- Both approved and rejected transfers use same FromWarehouse
- Bin allocations use same AbsEntry for all items in transfer

---

## Future Enhancements

- Per-batch warehouse designation
- Batch-level quantity splitting
- Transfer preview with detailed line items
- Warehouse transfer history tracking
- Automated warehouse suggestion based on item type

---

## Support

For issues or questions:
1. Check audit logs in GRPO Transfer session
2. Review SAP B1 Stock Transfer documents
3. Verify warehouse and bin codes in SAP B1
4. Check application logs for API errors
