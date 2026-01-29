# GRPO Transfer Module - API Reference V3.4

**Date**: January 26, 2026

---

## Item Validation API

### Endpoint
```
GET /grpo-transfer/api/item-validation/<item_code>
```

### Example
```
GET /grpo-transfer/api/item-validation/BOM_Item_1
```

### Response
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

### Item Types
- `batch` - Batch managed item
- `serial` - Serial managed item
- `non_batch` - Non-managed item

---

## Batch Fetching API

### Endpoint
```
GET /grpo-transfer/api/batches/<doc_entry>/<item_code>
```

### Example
```
GET /grpo-transfer/api/batches/7840/BOM_Item_1
```

### Response
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
    }
  ]
}
```

---

## Bin Codes API

### Endpoint
```
GET /grpo-transfer/api/bin-codes-with-entry/<warehouse_code>
```

### Example
```
GET /grpo-transfer/api/bin-codes-with-entry/7000-FG
```

### Response
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

## QC Approval API

### Endpoint
```
POST /grpo-transfer/api/session/<session_id>/qc-approve
```

### Request Body
```json
{
  "items": [
    {
      "item_id": 1,
      "approved_quantity": 600,
      "rejected_quantity": 400,
      "qc_status": "approved",
      "to_warehouse": "7000-QFG",
      "to_bin_code": "BIN-002",
      "qc_notes": "OK"
    }
  ]
}
```

### Response
```json
{
  "success": true,
  "message": "Items approved successfully"
}
```

---

## Generate QR Labels API

### Endpoint
```
POST /grpo-transfer/api/session/<session_id>/generate-qr-labels-with-packs
```

### Request Body
```json
{
  "pack_config": {
    "1": 2,
    "2": 1,
    "3": 3
  }
}
```

### Response
```json
{
  "success": true,
  "labels_generated": 6,
  "labels": [...]
}
```

---

## Get Labels API

### Endpoint
```
GET /grpo-transfer/api/session/<session_id>/labels
```

### Response
```json
{
  "success": true,
  "labels": [
    {
      "id": 1,
      "item_code": "BOM_Item_1",
      "label_number": 1,
      "total_labels": 2,
      "qr_data": "{...}",
      "batch_number": "20251216-BOM_Item_1",
      "quantity": 300
    }
  ]
}
```

---

## Post Transfer API

### Endpoint
```
POST /grpo-transfer/api/session/<session_id>/post-transfer
```

### Response
```json
{
  "success": true,
  "sap_doc_num": "123456",
  "sap_doc_entry": 12345,
  "transfers_posted": [
    {
      "type": "approved",
      "doc_entry": 12345,
      "doc_num": "123456"
    }
  ]
}
```

---

## Get Session Data API

### Endpoint
```
GET /grpo-transfer/api/session/<session_id>
```

### Response
```json
{
  "success": true,
  "session": {
    "id": 20,
    "session_code": "GRPO-7840-20260126120000",
    "grpo_doc_num": "7840",
    "grpo_doc_entry": 7840,
    "vendor_name": "Vendor Name",
    "doc_date": "2026-01-23",
    "doc_total": 900000.00,
    "status": "completed",
    "items": [
      {
        "id": 1,
        "item_code": "BOM_Item_1",
        "item_name": "Item Description",
        "is_batch_item": true,
        "received_quantity": 1000,
        "approved_quantity": 600,
        "rejected_quantity": 400,
        "from_warehouse": "7000-FG",
        "from_bin_code": "BIN-001",
        "to_warehouse": "7000-QFG",
        "to_bin_code": "BIN-002",
        "qc_status": "approved",
        "batches": [
          {
            "id": 1,
            "batch_number": "20251216-BOM_Item_1",
            "batch_quantity": 1000,
            "approved_quantity": 600,
            "rejected_quantity": 400,
            "expiry_date": "2027-01-08",
            "manufacture_date": null
          }
        ]
      }
    ]
  }
}
```

---

## Error Responses

### Item Not Found
```json
{
  "success": false,
  "error": "Item BOM_Item_1 not found in SAP B1"
}
```

### SAP B1 Connection Error
```json
{
  "success": false,
  "error": "SAP B1 authentication failed"
}
```

### Session Not Found
```json
{
  "success": false,
  "error": "Session not found"
}
```

---

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 400 | Bad request |
| 404 | Not found |
| 500 | Server error |

---

## Usage Examples

### Example 1: Validate Item
```bash
curl -X GET "http://localhost:5000/grpo-transfer/api/item-validation/BOM_Item_1" \
  -H "Authorization: Bearer <token>"
```

### Example 2: Get Batches
```bash
curl -X GET "http://localhost:5000/grpo-transfer/api/batches/7840/BOM_Item_1" \
  -H "Authorization: Bearer <token>"
```

### Example 3: Get Bin Codes
```bash
curl -X GET "http://localhost:5000/grpo-transfer/api/bin-codes-with-entry/7000-FG" \
  -H "Authorization: Bearer <token>"
```

### Example 4: Submit QC Approval
```bash
curl -X POST "http://localhost:5000/grpo-transfer/api/session/20/qc-approve" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "item_id": 1,
        "approved_quantity": 600,
        "rejected_quantity": 400,
        "qc_status": "approved",
        "to_warehouse": "7000-QFG",
        "to_bin_code": "BIN-002",
        "qc_notes": "OK"
      }
    ]
  }'
```

### Example 5: Post Transfer
```bash
curl -X POST "http://localhost:5000/grpo-transfer/api/session/20/post-transfer" \
  -H "Authorization: Bearer <token>"
```

---

**Date**: January 26, 2026  
**Version**: 3.4
