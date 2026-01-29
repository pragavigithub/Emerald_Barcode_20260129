# GRPO Transfer Module - Quick Start Guide

**Version**: 3.3  
**Date**: January 26, 2026

---

## Complete Workflow

### Step 1: Create Session
1. Go to GRPO Transfer Dashboard
2. Click on a GRPO document
3. System automatically:
   - Fetches GRPO details from SAP B1
   - Fetches batch numbers for batch items
   - Creates session with all items

### Step 2: QC Validation
1. Click "QC Validation" tab
2. For each item:
   - Enter **Approved Quantity**
   - Enter **Rejected Quantity**
   - Select **Status** (Approved/Rejected/Partial)
   - Select **To Warehouse** (destination warehouse)
   - Select **To Bin Code** (destination bin)
   - Add QC Notes (optional)
3. Click **"Submit QC Approval"**
4. System automatically:
   - Updates batch quantities proportionally
   - Sets session status to "Completed"
   - Shows "Post to SAP B1" button

### Step 3: Generate QR Labels
1. Click "QR Labels" tab
2. Click **"Generate Labels"** button
3. Configure packs:
   - Enter number of packs for each item
   - See distribution preview
4. Click **"Generate Labels"**
5. Labels appear in grid format showing:
   - Item Code
   - Batch Number (if batch item)
   - Approved Quantity
   - From Warehouse & Bin
   - To Warehouse & Bin
   - QR Code

### Step 4: Review & Print Labels
1. View labels in grid format
2. Click **"Print All Labels"** to print
3. Print layout shows 2 columns per page
4. Each label includes all details

### Step 5: Post to SAP B1
1. Click **"Post to SAP B1"** button
2. **Transfer Preview Modal** appears showing:
   - Approved Transfer details
   - Rejected Transfer details (if any)
   - All items with batch numbers
   - Approved and rejected quantities
   - Warehouse and bin mappings
3. Review all details carefully
4. Click **"Confirm & Post to SAP B1"**
5. System posts to SAP B1:
   - Creates approved quantity transfer
   - Creates rejected quantity transfer (if any)
   - Saves SAP DocNum and DocEntry
   - Updates session status to "Transferred"

### Step 6: Complete
1. Session status shows "Transferred"
2. SAP Transfer Document number displayed
3. Labels available for printing

---

## Key Features

### Batch Item Handling
- **Automatic Batch Fetching**: Batches fetched from SAP during session creation
- **Proportional Distribution**: Batch quantities distributed based on batch size
- **Batch Info in Labels**: Each label shows batch number and details
- **Batch Tracking**: Batch numbers included in SAP transfer

### QR Label Information
Each QR label displays:
```
Item Code: BOM_Item_1
Batch: BATCH_001 (BOM_Item_1)
Quantity: 300
From: 7000-FG (Bin: BIN-001)
To: 7000-QFG (Bin: BIN-002)
Date: 26/1/2026
```

### Transfer Preview
Before posting to SAP B1, review:
- All items to be transferred
- Batch numbers for batch items
- Approved and rejected quantities
- Warehouse and bin mappings
- Separate approved and rejected transfers

### Warehouse & Bin Management
- Select destination warehouse during QC validation
- Select destination bin code
- Automatically included in QR labels
- Included in SAP transfer payload

---

## Important Notes

### Batch Items
- Batch numbers automatically fetched from SAP
- Quantities distributed proportionally across batches
- Each batch gets: `approved_qty * (batch_qty / total_batch_qty)`
- Batch information displayed in QR labels

### Non-Batch Items
- No batch processing
- Quantities transferred as-is
- QR labels show "N/A" for batch

### Approved vs Rejected
- Approved quantities → Approved warehouse
- Rejected quantities → Rejected warehouse
- Separate SAP transfers created for each
- Both included in transfer preview

### QR Labels
- One label per pack (not per unit)
- Configure number of packs during generation
- Quantities distributed across packs
- First pack gets remainder

---

## Troubleshooting

### Batch Numbers Not Showing
1. Check if item is marked as "Batch" type
2. Verify batches were fetched from SAP
3. Check batch quantities in database
4. Regenerate labels

### Warehouse Not Showing in Labels
1. Verify warehouse selected during QC validation
2. Check warehouse exists in SAP B1
3. Verify warehouse code is correct
4. Regenerate labels

### Transfer Preview Not Loading
1. Check session status is "Completed"
2. Verify items have approved quantities
3. Check browser console for errors
4. Try refreshing page

### SAP Transfer Failed
1. Check SAP B1 connection
2. Verify warehouse codes exist in SAP
3. Verify batch numbers are valid
4. Check SAP error message in logs

---

## API Endpoints

### Get Session Data
```
GET /grpo-transfer/api/session/<session_id>
```
Returns complete session data with items and batches for preview.

### QC Approval
```
POST /grpo-transfer/api/session/<session_id>/qc-approve
Body: {
  "items": [
    {
      "item_id": 1,
      "approved_quantity": 300,
      "rejected_quantity": 0,
      "qc_status": "approved",
      "to_warehouse": "7000-QFG",
      "to_bin_code": "BIN-002",
      "qc_notes": "OK"
    }
  ]
}
```

### Generate QR Labels
```
POST /grpo-transfer/api/session/<session_id>/generate-qr-labels-with-packs
Body: {
  "pack_config": {
    "1": 2,  // Item ID 1: 2 packs
    "2": 1   // Item ID 2: 1 pack
  }
}
```

### Get Labels
```
GET /grpo-transfer/api/session/<session_id>/labels
```
Returns all QR labels for session.

### Post Transfer
```
POST /grpo-transfer/api/session/<session_id>/post-transfer
```
Posts approved and rejected transfers to SAP B1.

---

## Database Tables

### GRPOTransferSession
- Session header information
- GRPO document reference
- Transfer status
- SAP transfer document reference

### GRPOTransferItem
- Line items in session
- Quantities (received, approved, rejected)
- Warehouse and bin information
- Batch item flag

### GRPOTransferBatch
- Batch numbers for batch items
- Batch quantities
- Approved and rejected quantities
- Expiry and manufacture dates

### GRPOTransferQRLabel
- Generated QR labels
- QR data (JSON)
- Batch number reference
- Quantity per label

---

## Status Codes

| Status | Meaning | Actions Available |
|--------|---------|-------------------|
| draft | Session created | Edit items, Submit QC |
| in_progress | QC in progress | Submit QC |
| completed | QC approved | Generate labels, Post transfer |
| transferred | Posted to SAP B1 | Print labels |

---

## Best Practices

1. **Review QC Data**: Verify approved/rejected quantities before submission
2. **Check Warehouses**: Ensure destination warehouse is correct
3. **Review Transfer Preview**: Always review before posting to SAP B1
4. **Print Labels**: Print labels immediately after transfer posting
5. **Monitor Logs**: Check audit log for any issues

---

## Support

For issues or questions:
1. Check audit log for error messages
2. Review browser console for JavaScript errors
3. Check application logs for backend errors
4. Verify SAP B1 connection
5. Contact system administrator

---

**Version**: 3.3  
**Last Updated**: January 26, 2026
