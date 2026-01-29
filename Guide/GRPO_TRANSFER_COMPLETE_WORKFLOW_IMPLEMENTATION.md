# GRPO Transfer - Complete Workflow Implementation
**Date**: January 26, 2026  
**Version**: 3.5  
**Status**: ✅ COMPREHENSIVE IMPLEMENTATION

---

## Complete Workflow Steps

### Step 1: Item Validation (Batch/Serial/Non-Batch)

**API Endpoint**: `POST /b1s/v1/SQLQueries('ItemCode_Batch_Serial_Val')/List`

**Purpose**: Validate if item is Batch, Serial, or Non-Batch

**Request**:
```json
{
  "ParamList": "itemCode='BOM_Item_1'"
}
```

**Response**:
```json
{
  "value": [{
    "ItemCode": "BOM_Item_1",
    "ItemName": "BOM_Item_Batch_1",
    "BatchNum": "Y",        // ← Batch Item
    "SerialNum": "N",
    "NonBatch_NonSerialMethod": "A"
  }]
}
```

**Logic**:
- If `BatchNum = "Y"` → **Batch Item** (fetch batch numbers)
- If `SerialNum = "Y"` → **Serial Item** (fetch serial numbers)
- If both `BatchNum = "N"` and `SerialNum = "N"` → **Non-Batch Item** (no batch/serial)

**Implementation**: Already in `validate_item_type()` endpoint

---

### Step 2: Fetch Batch Numbers (Based on DocEntry)

**API Endpoint**: `POST /b1s/v1/SQLQueries('Get_Batches_By_DocEntry')/List`

**Purpose**: Get all batch numbers for a GRPO document

**Request**:
```json
{
  "ParamList": "docEntry='7840'"
}
```

**Response**:
```json
{
  "value": [
    {
      "DocEntry": 7840,
      "LineNum": 0,
      "ItemCode": "BOM_Item_1",
      "BatchNum": "20251216-BOM_Item_1",
      "Quantity": 1000.0,
      "ExpDate": "20270108",
      "MnfDate": null
    },
    {
      "DocEntry": 7840,
      "LineNum": 1,
      "ItemCode": "BOM_Item_2",
      "BatchNum": "20251216-BOM_Item_2",
      "Quantity": 1000.0,
      "ExpDate": "20271219",
      "MnfDate": null
    }
  ]
}
```

**Implementation**: Already in `create_session_view()` - fetches and saves batches during session creation

---

### Step 3: QC Validation with Splits

**Scenario**: 1000 quantity received
- Approve: 600 (OK)
- Reject: 400 (NOTOK)

**QC Form Input**:
```
Item: BOM_Item_1
Received Qty: 1000
Approved Qty: 600
Rejected Qty: 400
Status: Partial
From Warehouse: 7000-FG
From Bin Code: BIN-001
To Warehouse: 7000-QFG
To Bin Code: BIN-002
```

**Batch Distribution** (Proportional):
- If item has 1 batch with 1000 qty:
  - Batch approved_qty = 600 * (1000/1000) = 600
  - Batch rejected_qty = 400 * (1000/1000) = 400

- If item has 2 batches (500 each):
  - Batch 1 approved_qty = 600 * (500/1000) = 300
  - Batch 1 rejected_qty = 400 * (500/1000) = 200
  - Batch 2 approved_qty = 600 * (500/1000) = 300
  - Batch 2 rejected_qty = 400 * (500/1000) = 200

**API Endpoint**: `POST /grpo-transfer/api/session/{session_id}/qc-approve`

**Request**:
```json
{
  "items": [{
    "item_id": 67,
    "approved_quantity": 600,
    "rejected_quantity": 400,
    "qc_status": "partial",
    "from_warehouse": "7000-FG",
    "from_bin_code": "BIN-001",
    "to_warehouse": "7000-QFG",
    "to_bin_code": "BIN-002",
    "qc_notes": "QC validation complete"
  }]
}
```

**Backend Processing** (`qc_approve_items()`):
1. Update item quantities and warehouse/bin info
2. For batch items: distribute quantities proportionally across batches
3. Set session status to 'completed'
4. Return success

---

### Step 4: Transfer Preview

**API Endpoint**: `GET /grpo-transfer/api/session/{session_id}`

**Response**:
```json
{
  "success": true,
  "session": {
    "items": [{
      "item_code": "BOM_Item_1",
      "is_batch_item": true,
      "approved_quantity": 600,
      "rejected_quantity": 400,
      "from_warehouse": "7000-FG",
      "from_bin_code": "BIN-001",
      "to_warehouse": "7000-QFG",
      "to_bin_code": "BIN-002",
      "batches": [{
        "batch_number": "20251216-BOM_Item_1",
        "batch_quantity": 1000,
        "approved_quantity": 600,
        "rejected_quantity": 400,
        "expiry_date": "2027-01-08"
      }]
    }]
  }
}
```

**Transfer Preview Display**:
```
┌─────────────────────────────────────────────────────────┐
│ Transfer Line Items                                     │
├─────────────────────────────────────────────────────────┤
│ Item Code │ Batch Number │ Approved │ Rejected │ From Bin│
│ ─────────────────────────────────────────────────────────│
│ BOM_Item_1│20251216-BOM_1│  600.00  │ 400.00   │ BIN-001 │
│ Non_Sr_Bt │     N/A      │  300.00  │ 200.00   │ BIN-001 │
└─────────────────────────────────────────────────────────┘
```

---

### Step 5: Generate QR Labels (Optional)

**For Approved Items Only**:
- One label per pack
- Display: Item Code, Batch Number, Quantities, Warehouse/Bin

**API Endpoint**: `POST /grpo-transfer/api/session/{session_id}/generate-qr-labels`

---

### Step 6: Post Transfer to SAP B1

**API Endpoint**: `POST /b1s/v1/StockTransfers`

**Request Payload**:
```json
{
  "DocDate": "2026-01-23",
  "Comments": "QC Approved WMS Transfer by admin",
  "FromWarehouse": "7000-FG",
  "ToWarehouse": "7000-QFG",
  "StockTransferLines": [
    {
      "LineNum": 0,
      "ItemCode": "BOM_Item_1",
      "Quantity": 600.0,
      "WarehouseCode": "7000-QFG",
      "FromWarehouseCode": "7000-FG",
      "BaseEntry": 7840,
      "BaseLine": 0,
      "BaseType": "1250000001",
      "BatchNumbers": [
        {
          "BatchNumber": "20251216-BOM_Item_1",
          "Quantity": 600.0
        }
      ],
      "StockTransferLinesBinAllocations": [
        {
          "BinActionType": "batFromWarehouse",
          "BinAbsEntry": 251,
          "Quantity": 600.0,
          "SerialAndBatchNumbersBaseLine": 0
        },
        {
          "BinActionType": "batToWarehouse",
          "BinAbsEntry": 1393,
          "Quantity": 600.0,
          "SerialAndBatchNumbersBaseLine": 0
        }
      ]
    },
    {
      "LineNum": 1,
      "ItemCode": "Non_Sr_Bt",
      "Quantity": 300.0,
      "WarehouseCode": "7000-QFG",
      "FromWarehouseCode": "7000-FG",
      "BaseEntry": 7840,
      "BaseLine": 1,
      "BaseType": "1250000001",
      "BatchNumbers": [],
      "StockTransferLinesBinAllocations": [
        {
          "BinActionType": "batFromWarehouse",
          "BinAbsEntry": 251,
          "Quantity": 300.0,
          "SerialAndBatchNumbersBaseLine": 0
        },
        {
          "BinActionType": "batToWarehouse",
          "BinAbsEntry": 1393,
          "Quantity": 300.0,
          "SerialAndBatchNumbersBaseLine": 0
        }
      ]
    }
  ]
}
```

**Key Points**:
- `Quantity`: Approved quantity only (not rejected)
- `BatchNumbers`: Array of batch numbers with quantities (empty for non-batch items)
- `StockTransferLinesBinAllocations`: Bin allocations for both from and to warehouses
- `BaseEntry`, `BaseLine`, `BaseType`: Reference to original GRPO document

**Response**:
```json
{
  "DocEntry": 12345,
  "DocNum": "ST-2026-00001",
  "DocStatus": "O"
}
```

**Backend Processing** (`post_transfer_to_sap()`):
1. Build StockTransfer payload with batch numbers and bin allocations
2. Post to SAP B1
3. Save DocEntry and DocNum to database
4. Return success

---

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. USER SELECTS GRPO DOCUMENT                                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. SYSTEM CREATES SESSION & FETCHES ITEMS                       │
│    - Fetches GRPO details from SAP                              │
│    - Creates GRPOTransferSession                                │
│    - Creates GRPOTransferItem for each line                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. SYSTEM VALIDATES ITEMS & FETCHES BATCHES                     │
│    - Validates each item (Batch/Serial/Non-Batch)              │
│    - For batch items: Fetches batch numbers from SAP            │
│    - Creates GRPOTransferBatch for each batch                   │
│    - Sets is_batch_item = true for batch items                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. USER PERFORMS QC VALIDATION                                  │
│    - Opens QC Form                                              │
│    - Enters approved/rejected quantities                        │
│    - Selects from_warehouse, from_bin_code                      │
│    - Selects to_warehouse, to_bin_code                          │
│    - Submits QC Approval                                        │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. SYSTEM PROCESSES QC APPROVAL                                 │
│    - Updates item quantities                                    │
│    - Updates warehouse/bin information                          │
│    - For batch items: Distributes quantities proportionally     │
│    - Sets session status to 'completed'                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. USER REVIEWS TRANSFER PREVIEW                                │
│    - Clicks "Post to SAP B1"                                    │
│    - System fetches session data with batches                   │
│    - Displays transfer preview with:                            │
│      - From Warehouse, From Bin                                 │
│      - To Warehouse, To Bin                                     │
│      - Batch Numbers (for batch items)                          │
│      - Approved/Rejected Quantities                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 7. USER CONFIRMS & POSTS TO SAP B1                              │
│    - Clicks "Confirm & Post to SAP B1"                          │
│    - System builds StockTransfer payload with:                  │
│      - Batch numbers and quantities                             │
│      - Bin allocations (from and to)                            │
│      - Warehouse information                                    │
│    - Posts to SAP B1                                            │
│    - Saves DocEntry and DocNum to database                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ 8. TRANSFER COMPLETE                                            │
│    - SAP B1 creates StockTransfer document                      │
│    - WMS application saves transfer reference                   │
│    - QR labels generated (optional)                             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Checklist

### Backend (routes.py)
- [x] `validate_item_type()` - Validate Batch/Serial/Non-Batch
- [x] `create_session_view()` - Fetch and save batches
- [x] `qc_approve_items()` - Distribute batch quantities
- [x] `get_session_data()` - Return session with batches
- [x] `post_transfer_to_sap()` - Build and post StockTransfer payload

### Frontend (session_detail.html)
- [x] Edit modal - Editable warehouse/bin dropdowns
- [x] QC form - Pre-populated warehouse/bin dropdowns
- [x] Transfer preview - Display batch numbers
- [x] Transfer preview - Display warehouse/bin information

### Database (models.py)
- [x] GRPOTransferItem - from_warehouse, from_bin_code fields
- [x] GRPOTransferBatch - batch_number, quantities, dates
- [x] GRPOTransferSplit - split tracking (optional)

---

## Testing Scenarios

### Scenario 1: Batch Item with Single Batch
- Item: BOM_Item_1 (Batch Item)
- Received: 1000
- Batch: 20251216-BOM_Item_1 (1000 qty)
- Approve: 600, Reject: 400
- Expected: Batch shows 600 approved, 400 rejected in preview

### Scenario 2: Batch Item with Multiple Batches
- Item: BOM_Item_1 (Batch Item)
- Received: 1000
- Batches: 
  - 20251216-BOM_Item_1 (500 qty)
  - 20251216-BOM_Item_2 (500 qty)
- Approve: 600, Reject: 400
- Expected: Each batch shows 300 approved, 200 rejected

### Scenario 3: Non-Batch Item
- Item: Non_Sr_Bt (Non-Batch Item)
- Received: 500
- Approve: 300, Reject: 200
- Expected: Batch Number shows "N/A" in preview

### Scenario 4: Mixed Items
- Item 1: BOM_Item_1 (Batch Item)
- Item 2: Non_Sr_Bt (Non-Batch Item)
- Expected: Batch item shows batch number, non-batch shows "N/A"

---

## Troubleshooting

### Issue: Batch Numbers Show "N/A"
**Possible Causes**:
1. `is_batch_item` not set to true
2. Batches not fetched during session creation
3. Batches not included in session data

**Solution**:
1. Check if item validation is working
2. Verify batch fetch API is called during session creation
3. Verify batches are included in get_session_data() response

### Issue: Warehouse/Bin Shows "N/A"
**Possible Causes**:
1. Values not saved during QC approval
2. Values not included in session data

**Solution**:
1. Verify QC form is sending warehouse/bin values
2. Verify API is saving values to database
3. Verify get_session_data() includes warehouse/bin fields

### Issue: Transfer Preview Not Displaying
**Possible Causes**:
1. Session data API returning error
2. JavaScript error in buildTransferPreview()

**Solution**:
1. Check browser console for errors
2. Check server logs for API errors
3. Verify session data is being returned correctly

---

## Version History

- **v3.5** (Jan 26, 2026): Complete workflow implementation
- **v3.4.3** (Jan 26, 2026): Fixed from_warehouse, from_bin_code, batch number display
- **v3.4** (Jan 2026): Initial GRPO Transfer implementation

---

**Status**: ✅ READY FOR TESTING  
**Last Updated**: January 26, 2026
