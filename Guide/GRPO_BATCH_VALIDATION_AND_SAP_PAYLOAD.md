# GRPO Transfer - Complete Implementation with Batch Validation & SAP B1 Payload

**Date**: January 26, 2026  
**Status**: ✅ COMPLETE  
**Version**: 3.4

---

## New API Endpoints Added

### 1. Item Validation Endpoint
**URL**: `GET /grpo-transfer/api/item-validation/<item_code>`

**Purpose**: Validate if item is Batch, Serial, or Non-Batch

**SAP Query Used**: `ItemCode_Batch_Serial_Val`

**Response**:
```json
{
  "success": true,
  "item_code": "BOM_Item_1",
  "item_name": "BOM_Item_Batch_1",
  "item_type": "batch",
  "is_batch": true,
  "is_serial": false,
  "batch_num": "Y",
  "serial_num": "N"
}
```

**Item Types**:
- `batch` - BatchNum = "Y", SerialNum = "N"
- `serial` - BatchNum = "N", SerialNum = "Y"
- `non_batch` - BatchNum = "N", SerialNum = "N"

---

### 2. Get Batches for Item Endpoint
**URL**: `GET /grpo-transfer/api/batches/<doc_entry>/<item_code>`

**Purpose**: Get batch numbers for specific item in GRPO document

**SAP Query Used**: `Get_Batches_By_DocEntry`

**Response**:
```json
{
  "success": true,
  "item_code": "BOM_Item_1",
  "batches": [
    {
      "batch_number": "20251216-BOM_Item_1",
      "quantity": 1000.0,
      "expiry_date": "20270108",
      "manufacture_date": null,
      "line_num": 0
    },
    {
      "batch_number": "20251216-BOM_Item_2",
      "quantity": 1000.0,
      "expiry_date": "20271219",
      "manufacture_date": null,
      "line_num": 1
    }
  ]
}
```

---

### 3. Get Bin Codes with AbsEntry Endpoint
**URL**: `GET /grpo-transfer/api/bin-codes-with-entry/<warehouse_code>`

**Purpose**: Get bin codes with AbsEntry for SAP B1 transfer

**Response**:
```json
{
  "success": true,
  "warehouse_code": "7000-FG",
  "bins": [
    {
      "bin_code": "BIN-001",
      "abs_entry": 251,
      "warehouse_code": "7000-FG"
    },
    {
      "bin_code": "BIN-002",
      "abs_entry": 252,
      "warehouse_code": "7000-FG"
    }
  ]
}
```

---

## QC Validation Workflow

### Step 1: Item Validation
```
User selects item in QC form
    ↓
Call: GET /grpo-transfer/api/item-validation/{item_code}
    ↓
Response: item_type (batch/serial/non_batch)
    ↓
If batch item:
    ├─ Show batch dropdown
    ├─ Load batches from SAP
    └─ Allow batch selection
Else:
    └─ Show quantity fields only
```

### Step 2: Batch Selection (for Batch Items)
```
Item validated as batch item
    ↓
Call: GET /grpo-transfer/api/batches/{doc_entry}/{item_code}
    ↓
Response: List of batches with quantities
    ↓
Display batch dropdown:
    ├─ BATCH_001 (1000 units, Exp: 2027-01-08)
    ├─ BATCH_002 (1000 units, Exp: 2027-12-19)
    └─ ...
```

### Step 3: QC Approval with Split Quantities
```
Example: Item received 1000 units
    ├─ Batch 1: 600 units → OK (Approved)
    ├─ Batch 2: 400 units → NOTOK (Rejected)
    ↓
User enters:
    ├─ Approved Quantity: 600
    ├─ Rejected Quantity: 400
    ├─ Select Batch: BATCH_001
    ├─ From Warehouse: 7000-FG
    ├─ From Bin: BIN-001
    ├─ To Warehouse: 7000-QFG
    └─ To Bin: BIN-002
    ↓
Submit QC Approval
    ↓
System creates splits:
    ├─ Split 1: 600 units, Status=OK, Batch=BATCH_001
    └─ Split 2: 400 units, Status=NOTOK, Batch=BATCH_001
```

---

## SAP B1 Stock Transfer JSON Payload

### Complete Payload Structure

```json
{
  "DocDate": "2025-12-01",
  "Comments": "QC Approved WMS Transfer GRPO-7839 by admin",
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
      "ItemCode": "BOM_Item_2",
      "Quantity": 500.0,
      "WarehouseCode": "7000-QFG",
      "FromWarehouseCode": "7000-FG",
      "BaseEntry": 7840,
      "BaseLine": 1,
      "BaseType": "1250000001",
      "BatchNumbers": [
        {
          "BatchNumber": "20251216-BOM_Item_2",
          "Quantity": 500.0
        }
      ],
      "StockTransferLinesBinAllocations": [
        {
          "BinActionType": "batFromWarehouse",
          "BinAbsEntry": 251,
          "Quantity": 500.0,
          "SerialAndBatchNumbersBaseLine": 0
        },
        {
          "BinActionType": "batToWarehouse",
          "BinAbsEntry": 1393,
          "Quantity": 500.0,
          "SerialAndBatchNumbersBaseLine": 0
        }
      ]
    },
    {
      "LineNum": 2,
      "ItemCode": "BOM_Item_3",
      "Quantity": 1000.0,
      "WarehouseCode": "7000-QFG",
      "FromWarehouseCode": "7000-FG",
      "BaseEntry": 7840,
      "BaseLine": 2,
      "BaseType": "1250000001",
      "BatchNumbers": [],
      "StockTransferLinesBinAllocations": [
        {
          "BinActionType": "batFromWarehouse",
          "BinAbsEntry": 251,
          "Quantity": 1000.0,
          "SerialAndBatchNumbersBaseLine": 0
        },
        {
          "BinActionType": "batToWarehouse",
          "BinAbsEntry": 1393,
          "Quantity": 1000.0,
          "SerialAndBatchNumbersBaseLine": 0
        }
      ]
    }
  ]
}
```

### Payload Field Descriptions

| Field | Type | Description |
|-------|------|-------------|
| DocDate | String | Transfer document date (YYYY-MM-DD) |
| Comments | String | Transfer comments/description |
| FromWarehouse | String | Source warehouse code |
| ToWarehouse | String | Destination warehouse code |
| LineNum | Integer | Line number (0-based) |
| ItemCode | String | Item code from SAP |
| Quantity | Float | Total quantity to transfer |
| WarehouseCode | String | Destination warehouse (same as ToWarehouse) |
| FromWarehouseCode | String | Source warehouse (same as FromWarehouse) |
| BaseEntry | Integer | GRPO document entry number |
| BaseLine | Integer | GRPO line number |
| BaseType | String | "1250000001" for GRPO documents |
| BatchNumber | String | Batch number (for batch items) |
| BinActionType | String | "batFromWarehouse" or "batToWarehouse" |
| BinAbsEntry | Integer | Bin absolute entry from SAP |
| SerialAndBatchNumbersBaseLine | Integer | Always 0 for batch allocations |

---

## Complete QC to Transfer Workflow

```
1. Create Session
   ├─ Fetch GRPO from SAP
   ├─ Create items
   └─ Fetch batch numbers

2. QC Validation
   ├─ For each item:
   │  ├─ Validate item type (batch/serial/non-batch)
   │  ├─ If batch: Load batches
   │  ├─ Enter approved/rejected quantities
   │  ├─ Select from/to warehouse & bins
   │  └─ Submit
   └─ System creates splits

3. Generate QR Labels
   ├─ Configure packs
   ├─ Generate labels (one per pack)
   └─ Display with batch info

4. Transfer Preview
   ├─ Show all items
   ├─ Show batch numbers
   ├─ Show warehouse/bin mappings
   └─ Confirm

5. Post to SAP B1
   ├─ Build JSON payload
   ├─ Include batch numbers
   ├─ Include bin allocations
   ├─ Post to /b1s/v1/StockTransfers
   └─ Save DocNum & DocEntry

6. Complete
   └─ Session status = transferred
```

---

## Example Scenario

### Input
```
GRPO Document: 7840
Item 1: BOM_Item_1 (Batch Item)
  - Received: 1000 units
  - Batch: 20251216-BOM_Item_1
  - QC Approval: 600 OK, 400 NOTOK
  - From: 7000-FG (Bin: BIN-001)
  - To: 7000-QFG (Bin: BIN-002)

Item 2: BOM_Item_2 (Batch Item)
  - Received: 1000 units
  - Batch: 20251216-BOM_Item_2
  - QC Approval: 500 OK, 500 NOTOK
  - From: 7000-FG (Bin: BIN-001)
  - To: 7000-QFG (Bin: BIN-002)

Item 3: BOM_Item_3 (Non-Batch)
  - Received: 1000 units
  - QC Approval: 1000 OK
  - From: 7000-FG (Bin: BIN-001)
  - To: 7000-QFG (Bin: BIN-002)
```

### SAP B1 Transfers Created

**Transfer 1: Approved Quantities**
```
From: 7000-FG → To: 7000-QFG
Line 0: BOM_Item_1, 600 units, Batch: 20251216-BOM_Item_1
Line 1: BOM_Item_2, 500 units, Batch: 20251216-BOM_Item_2
Line 2: BOM_Item_3, 1000 units, No batch
```

**Transfer 2: Rejected Quantities**
```
From: 7000-FG → To: 7000-QFG
Line 0: BOM_Item_1, 400 units, Batch: 20251216-BOM_Item_1
Line 1: BOM_Item_2, 500 units, Batch: 20251216-BOM_Item_2
```

---

## Database Updates

### GRPOTransferItem
- `is_batch_item` = True/False (from validation)
- `from_bin_code` = BIN-001 (from QC form)
- `to_bin_code` = BIN-002 (from QC form)
- `approved_quantity` = 600 (for Item 1)
- `rejected_quantity` = 400 (for Item 1)

### GRPOTransferBatch
- `batch_number` = "20251216-BOM_Item_1"
- `batch_quantity` = 1000
- `approved_quantity` = 600
- `rejected_quantity` = 400

### GRPOTransferSplit
- `split_number` = 1
- `quantity` = 600
- `status` = "OK"
- `batch_number` = "20251216-BOM_Item_1"

---

## Verification Checklist

- [x] Item validation API implemented
- [x] Batch fetching API implemented
- [x] Bin codes with AbsEntry API implemented
- [x] QC validation supports batch selection
- [x] QC validation supports split quantities
- [x] SAP B1 payload includes batch numbers
- [x] SAP B1 payload includes bin allocations
- [x] SAP B1 payload includes BaseEntry/BaseLine
- [x] Approved and rejected transfers separate
- [x] SAP response saved (DocNum, DocEntry)

---

**Status**: ✅ COMPLETE  
**Date**: January 26, 2026  
**Version**: 3.4
