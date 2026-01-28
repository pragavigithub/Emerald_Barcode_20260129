# GRPO Edit Modal - Integration Guide

## Overview
This guide explains how to integrate the new item validation endpoint into the Edit Item modal.

## Trigger Point
**When:** User selects "To Warehouse" dropdown
**Action:** Call validation endpoint
**Display:** Item type and batch numbers

## Frontend Implementation

### 1. HTML Structure (Edit Modal)
```html
<div class="modal" id="editItemModal">
    <div class="modal-content">
        <h2>Edit Item</h2>
        
        <!-- Item Code (Read-only) -->
        <div class="form-group">
            <label>Item Code</label>
            <input type="text" id="itemCode" readonly>
        </div>
        
        <!-- Item Name (Read-only) -->
        <div class="form-group">
            <label>Item Name</label>
            <input type="text" id="itemName" readonly>
        </div>
        
        <!-- Item Type Display (NEW) -->
        <div class="form-group">
            <label>Item Type</label>
            <div id="itemTypeDisplay">
                <span id="itemTypeBadge" class="badge"></span>
            </div>
        </div>
        
        <!-- From Warehouse (Read-only) -->
        <div class="form-group">
            <label>From Warehouse</label>
            <input type="text" id="fromWarehouse" readonly>
        </div>
        
        <!-- To Warehouse (Trigger Validation) -->
        <div class="form-group">
            <label>To Warehouse *</label>
            <select id="toWarehouse" onchange="onToWarehouseChange()">
                <option value="">-- Select Warehouse --</option>
                <!-- Options populated from API -->
            </select>
        </div>
        
        <!-- Batch Numbers Display (NEW) -->
        <div class="form-group" id="batchNumbersSection" style="display: none;">
            <label>Batch Numbers</label>
            <div id="batchNumbersList">
                <!-- Batch numbers displayed here -->
            </div>
        </div>
        
        <!-- Quantities -->
        <div class="form-group">
            <label>Received Qty</label>
            <input type="number" id="receivedQty" readonly>
        </div>
        
        <div class="form-group">
            <label>Approved Qty</label>
            <input type="number" id="approvedQty">
        </div>
        
        <div class="form-group">
            <label>Rejected Qty</label>
            <input type="number" id="rejectedQty">
        </div>
        
        <!-- QC Notes -->
        <div class="form-group">
            <label>QC Notes</label>
            <textarea id="qcNotes"></textarea>
        </div>
        
        <!-- Buttons -->
        <div class="modal-buttons">
            <button onclick="closeEditModal()">Close</button>
            <button onclick="saveItemChanges()" class="btn-primary">Save Changes</button>
        </div>
    </div>
</div>
```

### 2. JavaScript Functions

```javascript
// Global variable to store current item ID
let currentEditingItemId = null;

// Open edit modal
function openEditModal(itemId) {
    currentEditingItemId = itemId;
    
    // Fetch item details
    fetch(`/api/item/${itemId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                populateEditModal(data.item);
                document.getElementById('editItemModal').style.display = 'block';
            }
        })
        .catch(error => console.error('Error:', error));
}

// Populate modal with item data
function populateEditModal(item) {
    document.getElementById('itemCode').value = item.item_code;
    document.getElementById('itemName').value = item.item_name;
    document.getElementById('fromWarehouse').value = item.from_warehouse;
    document.getElementById('receivedQty').value = item.received_quantity;
    document.getElementById('approvedQty').value = item.approved_quantity;
    document.getElementById('rejectedQty').value = item.rejected_quantity;
    document.getElementById('qcNotes').value = item.qc_notes || '';
    
    // Load warehouses
    loadWarehouses();
}

// Load warehouses into dropdown
function loadWarehouses() {
    fetch('/api/warehouses')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                const select = document.getElementById('toWarehouse');
                select.innerHTML = '<option value="">-- Select Warehouse --</option>';
                
                data.warehouses.forEach(warehouse => {
                    const option = document.createElement('option');
                    option.value = warehouse.WarehouseCode;
                    option.textContent = warehouse.WarehouseName;
                    select.appendChild(option);
                });
            }
        })
        .catch(error => console.error('Error:', error));
}

// Trigger validation when To Warehouse is selected
function onToWarehouseChange() {
    const toWarehouse = document.getElementById('toWarehouse').value;
    
    if (!toWarehouse) {
        // Clear batch display if no warehouse selected
        document.getElementById('batchNumbersSection').style.display = 'none';
        return;
    }
    
    // Call validation endpoint
    validateItemAndFetchBatches(currentEditingItemId, toWarehouse);
}

// Validate item and fetch batch details
function validateItemAndFetchBatches(itemId, toWarehouse) {
    // Show loading indicator
    showLoadingSpinner();
    
    fetch(`/api/item/${itemId}/validate-and-fetch-batches`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            to_warehouse: toWarehouse
        })
    })
    .then(response => response.json())
    .then(data => {
        hideLoadingSpinner();
        
        if (data.success) {
            // Update item type display
            updateItemTypeDisplay(data.is_batch_item, data.is_serial_item, data.is_non_managed);
            
            // Display batch numbers if batch item
            if (data.is_batch_item && data.batches.length > 0) {
                displayBatchNumbers(data.batches);
            } else {
                document.getElementById('batchNumbersSection').style.display = 'none';
            }
            
            // Show success message
            showSuccessMessage(data.message);
        } else {
            showErrorMessage(data.error);
        }
    })
    .catch(error => {
        hideLoadingSpinner();
        console.error('Error:', error);
        showErrorMessage('Failed to validate item');
    });
}

// Update item type badge display
function updateItemTypeDisplay(isBatch, isSerial, isNonManaged) {
    const badge = document.getElementById('itemTypeBadge');
    
    if (isBatch) {
        badge.className = 'badge badge-batch';
        badge.textContent = 'Batch';
    } else if (isSerial) {
        badge.className = 'badge badge-serial';
        badge.textContent = 'Serial';
    } else if (isNonManaged) {
        badge.className = 'badge badge-non-managed';
        badge.textContent = 'Non-Managed';
    }
}

// Display batch numbers
function displayBatchNumbers(batches) {
    const section = document.getElementById('batchNumbersSection');
    const list = document.getElementById('batchNumbersList');
    
    // Clear previous content
    list.innerHTML = '';
    
    // Create batch table
    const table = document.createElement('table');
    table.className = 'batch-table';
    
    // Header
    const header = table.createTHead();
    const headerRow = header.insertRow();
    headerRow.innerHTML = `
        <th>Batch Number</th>
        <th>Quantity</th>
        <th>Expiry Date</th>
        <th>Manufacture Date</th>
    `;
    
    // Body
    const body = table.createTBody();
    batches.forEach(batch => {
        const row = body.insertRow();
        row.innerHTML = `
            <td>${batch.batch_number}</td>
            <td>${batch.batch_quantity}</td>
            <td>${batch.expiry_date || 'N/A'}</td>
            <td>${batch.manufacture_date || 'N/A'}</td>
        `;
    });
    
    list.appendChild(table);
    section.style.display = 'block';
}

// Save item changes
function saveItemChanges() {
    const itemId = currentEditingItemId;
    const toWarehouse = document.getElementById('toWarehouse').value;
    const approvedQty = parseFloat(document.getElementById('approvedQty').value);
    const rejectedQty = parseFloat(document.getElementById('rejectedQty').value);
    const qcNotes = document.getElementById('qcNotes').value;
    
    if (!toWarehouse) {
        showErrorMessage('Please select To Warehouse');
        return;
    }
    
    // Call update endpoint
    fetch(`/api/item/${itemId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            to_warehouse: toWarehouse,
            approved_quantity: approvedQty,
            rejected_quantity: rejectedQty,
            qc_notes: qcNotes
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showSuccessMessage('Item updated successfully');
            closeEditModal();
            // Refresh grid
            loadSessionItems();
        } else {
            showErrorMessage(data.error);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showErrorMessage('Failed to save changes');
    });
}

// Close modal
function closeEditModal() {
    document.getElementById('editItemModal').style.display = 'none';
    currentEditingItemId = null;
}

// Helper functions
function showLoadingSpinner() {
    // Show loading indicator
    document.getElementById('loadingSpinner').style.display = 'block';
}

function hideLoadingSpinner() {
    document.getElementById('loadingSpinner').style.display = 'none';
}

function showSuccessMessage(message) {
    // Show success toast/alert
    console.log('Success:', message);
}

function showErrorMessage(message) {
    // Show error toast/alert
    console.error('Error:', message);
}
```

### 3. CSS Styling

```css
/* Item Type Badge */
.badge {
    display: inline-block;
    padding: 6px 12px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: bold;
    color: white;
}

.badge-batch {
    background-color: #007bff;
}

.badge-serial {
    background-color: #28a745;
}

.badge-non-managed {
    background-color: #6c757d;
}

/* Batch Table */
.batch-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 10px;
}

.batch-table th,
.batch-table td {
    padding: 10px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}

.batch-table th {
    background-color: #f8f9fa;
    font-weight: bold;
}

.batch-table tr:hover {
    background-color: #f5f5f5;
}

/* Modal */
.modal {
    display: none;
    position: fixed;
    z-index: 1000;
    left: 0;
    top: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.5);
}

.modal-content {
    background-color: white;
    margin: 5% auto;
    padding: 20px;
    border-radius: 8px;
    width: 90%;
    max-width: 600px;
    max-height: 80vh;
    overflow-y: auto;
}

.form-group {
    margin-bottom: 15px;
}

.form-group label {
    display: block;
    margin-bottom: 5px;
    font-weight: bold;
}

.form-group input,
.form-group select,
.form-group textarea {
    width: 100%;
    padding: 8px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;
}

.modal-buttons {
    display: flex;
    gap: 10px;
    justify-content: flex-end;
    margin-top: 20px;
}

.btn-primary {
    background-color: #007bff;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}

.btn-primary:hover {
    background-color: #0056b3;
}
```

## Integration Steps

1. **Add HTML** to edit modal template
2. **Add JavaScript** functions to handle validation
3. **Add CSS** for styling
4. **Test** with batch and non-batch items
5. **Verify** batch numbers display correctly
6. **Check** database for batch records

## Testing Scenarios

### Scenario 1: Batch Item
1. Click Edit on batch item
2. Select To Warehouse
3. Verify item type shows "Batch"
4. Verify batch numbers appear
5. Verify batch details (qty, dates) correct

### Scenario 2: Non-Batch Item
1. Click Edit on non-batch item
2. Select To Warehouse
3. Verify item type shows "Non-Managed"
4. Verify no batch numbers appear

### Scenario 3: Error Handling
1. Select invalid warehouse
2. Verify error message displays
3. Verify modal stays open

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Batch numbers not appearing | Check API response in browser console |
| Item type not updating | Verify validation endpoint called |
| Modal not opening | Check JavaScript errors in console |
| Batch dates showing as null | Check date parsing in backend |

## Performance Tips

1. Debounce warehouse selection (300ms)
2. Cache warehouse list
3. Show loading spinner during validation
4. Disable save button during API call

## Security Considerations

1. Validate item_id belongs to current user's session
2. Validate warehouse code exists
3. Sanitize batch number display
4. Log all validations for audit trail
