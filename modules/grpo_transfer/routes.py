"""
GRPO Transfer Module Routes
Handles QC validation and warehouse transfers
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
import logging
import json

from app import db
from models import User
from sap_integration import SAPIntegration
from .models import (
    GRPOTransferSession, GRPOTransferItem, GRPOTransferBatch,
    GRPOTransferSplit, GRPOTransferLog, GRPOTransferQRLabel
)

# Create blueprint
grpo_transfer_bp = Blueprint('grpo_transfer', __name__, url_prefix='/grpo-transfer', template_folder='templates')

logger = logging.getLogger(__name__)

# ============================================================================
# UI ROUTES
# ============================================================================

@grpo_transfer_bp.route('/', methods=['GET'])
@login_required
def index():
    """Main GRPO Transfer dashboard"""
    return render_template('grpo_transfer/index.html')

@grpo_transfer_bp.route('/session/<int:session_id>', methods=['GET'])
@login_required
def session_detail(session_id):
    """View session details"""
    session = GRPOTransferSession.query.get_or_404(session_id)
    
    # Convert items to dictionaries for JSON serialization
    items_data = []
    for item in session.items:
        # Convert batches to dictionaries
        batches_data = []
        if item.batches:
            for batch in item.batches:
                batches_data.append({
                    'id': batch.id,
                    'batch_number': batch.batch_number,
                    'batch_quantity': batch.batch_quantity,
                    'approved_quantity': batch.approved_quantity,
                    'rejected_quantity': batch.rejected_quantity,
                    'expiry_date': batch.expiry_date,
                    'manufacture_date': batch.manufacture_date,
                    'qc_status': batch.qc_status
                })
        
        items_data.append({
            'id': item.id,
            'item_code': item.item_code,
            'item_name': item.item_name,
            'item_description': item.item_description,
            'is_batch_item': item.is_batch_item,
            'is_serial_item': item.is_serial_item,
            'is_non_managed': item.is_non_managed,
            'received_quantity': item.received_quantity,
            'approved_quantity': item.approved_quantity,
            'rejected_quantity': item.rejected_quantity,
            'from_warehouse': item.from_warehouse,
            'from_bin_code': item.from_bin_code,
            'to_warehouse': item.to_warehouse,
            'to_bin_code': item.to_bin_code,
            'unit_of_measure': item.unit_of_measure,
            'price': item.price,
            'line_total': item.line_total,
            'qc_status': item.qc_status,
            'qc_notes': item.qc_notes,
            'sap_base_entry': item.sap_base_entry,
            'sap_base_line': item.sap_base_line,
            'batches': batches_data
        })
    
    return render_template('grpo_transfer/session_detail.html', session=session, items_json=items_data)

@grpo_transfer_bp.route('/session/<int:session_id>/qc', methods=['GET'])
@login_required
def qc_validation(session_id):
    """QC validation screen"""
    session = GRPOTransferSession.query.get_or_404(session_id)
    return render_template('grpo_transfer/qc_validation.html', session=session)

@grpo_transfer_bp.route('/session/create/<int:doc_entry>', methods=['GET', 'POST'])
@login_required
def create_session_view(doc_entry):
    """Create new transfer session - display document details and add items"""
    try:
        sap = SAPIntegration()
        logger.info(f"DocEntry => {doc_entry}")

        if not sap.ensure_logged_in():
            flash('SAP B1 authentication failed', 'error')
            return redirect(url_for('grpo_transfer.index'))

        # =============================
        # 1) FETCH GRPO DOCUMENT
        # =============================
        url = f"{sap.base_url}/b1s/v1/PurchaseDeliveryNotes?$filter=DocEntry eq {doc_entry}"
        headers = {'Prefer': 'odata.maxpagesize=0'}

        logger.debug(f"Fetching GRPO: {url}")
        response = sap.session.get(url, headers=headers, timeout=30)

        if response.status_code != 200:
            logger.error(f"SAP Error: {response.status_code} {response.text}")
            flash("Failed to fetch GRPO from SAP", "error")
            return redirect(url_for('grpo_transfer.index'))

        data = response.json()
        value_list = data.get("value", [])

        if not value_list:
            flash("No GRPO found", "error")
            return redirect(url_for('grpo_transfer.index'))

        doc = value_list[0]  # Only one document

        # =============================
        # 2) HEADER
        # =============================
        doc_details = doc
        line_items = doc.get("DocumentLines", [])

        if not line_items:
            flash("No GRPO lines found", "error")
            return redirect(url_for('grpo_transfer.index'))

        # =============================
        # 3) CREATE SESSION
        # =============================
        session_code = f"GRPO-{doc_entry}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        session = GRPOTransferSession(
            session_code=session_code,
            grpo_doc_entry=doc_entry,
            grpo_doc_num=doc_details.get("DocNum"),
            series_id=doc_details.get("Series"),
            vendor_code=doc_details.get("CardCode"),
            vendor_name=doc_details.get("CardName"),
            doc_date=datetime.strptime(doc_details["DocDate"][:10], "%Y-%m-%d").date(),
            doc_due_date=datetime.strptime(doc_details["DocDueDate"][:10], "%Y-%m-%d").date()
            if doc_details.get("DocDueDate") else None,
            doc_total=float(doc_details.get("DocTotal", 0.0))
        )

        db.session.add(session)
        db.session.flush()

        # =============================
        # 4) LOOP LINES
        # =============================
        for line in line_items:
            item = GRPOTransferItem(
                session_id=session.id,
                line_num=line.get("LineNum"),
                item_code=line.get("ItemCode"),
                item_name=line.get("ItemDescription"),
                item_description=line.get("ItemDescription"),
                received_quantity=float(line.get("Quantity", 0)),
                from_warehouse=line.get("WarehouseCode"),
                unit_of_measure=str(line.get("UnitsOfMeasurment", 1)),
                price=float(line.get("Price", 0)),
                line_total=float(line.get("LineTotal", 0)),
                sap_base_entry=doc_entry,
                sap_base_line=line.get("LineNum")
            )

            # ---------- BIN ----------
            bin_allocs = line.get("DocumentLinesBinAllocations", [])
            if bin_allocs:
                bin_row = bin_allocs[0]
                item.from_bin_abs_entry = bin_row.get("BinAbsEntry")

                bin_info = sap.get_bin_location_details(item.from_bin_abs_entry)
                print("bin_info---->", bin_info)

                if bin_info:
                    if isinstance(bin_info, list) and len(bin_info) > 0:
                        bin_row = bin_info[0]
                    elif isinstance(bin_info, dict):
                        bin_row = bin_info
                    else:
                        bin_row = None

                    if bin_row:
                        item.from_bin_code = bin_row.get("BinCode")
                        item.from_bin_abs_entry = bin_row.get("AbsEntry")
            # ---------- ITEM TYPE ----------
            item_code = item.item_code
            val_url = f"{sap.base_url}/b1s/v1/SQLQueries('ItemCode_Batch_Serial_Val')/List"
            val_payload = {"ParamList": f"itemCode='{item_code}'"}

            val_resp = sap.session.post(val_url, json=val_payload, headers=headers)
            if val_resp.status_code == 200 and val_resp.json().get("value"):
                val = val_resp.json()["value"][0]
                item.is_batch_item = val.get("BatchNum") == "Y"
                item.is_serial_item = val.get("SerialNum") == "Y"
                item.is_non_managed = not item.is_batch_item and not item.is_serial_item
            else:
                item.is_non_managed = True

            db.session.add(item)

        db.session.commit()

        # =============================
        # 5) FETCH BATCHES
        # =============================
        batch_url = f"{sap.base_url}/b1s/v1/SQLQueries('Get_Batch_By_DocEntry_ItemCode')/List"

        session_items = GRPOTransferItem.query.filter_by(session_id=session.id).all()

        for si in session_items:
            if not si.is_batch_item:
                continue

            params = (
                f"docEntry='{si.sap_base_entry}'&"
                f"itemCode='{si.item_code}'&"
                f"lineNum='{si.sap_base_line}'"
            )

            resp = sap.session.post(batch_url, json={"ParamList": params}, headers=headers)
            if resp.status_code != 200:
                continue

            for b in resp.json().get("value", []):
                batch = GRPOTransferBatch(
                    item_id=si.id,
                    batch_number=b.get("BatchNum"),
                    batch_quantity=float(b.get("Quantity", 0)),
                    approved_quantity=0,
                    rejected_quantity=0,
                    qc_status="pending"
                )

                if b.get("ExpDate"):
                    batch.expiry_date = datetime.strptime(b["ExpDate"], "%Y%m%d").date()

                if b.get("MnfDate"):
                    batch.manufacture_date = datetime.strptime(b["MnfDate"], "%Y%m%d").date()

                db.session.add(batch)

        db.session.commit()

        # =============================
        # 6) LOG
        # =============================
        log = GRPOTransferLog(
            session_id=session.id,
            user_id=current_user.id,
            action="session_created",
            description=f"Created transfer session for GRPO {doc_details.get('DocNum')}"
        )
        db.session.add(log)
        db.session.commit()

        logger.info(f"Session {session.id} created")
        return redirect(url_for("grpo_transfer.session_detail", session_id=session.id))

    except Exception as e:
        logger.exception("Create session error")
        db.session.rollback()
        flash(str(e), "error")
        return redirect(url_for("grpo_transfer.index"))

# @grpo_transfer_bp.route('/session/create/<int:doc_entry>', methods=['GET', 'POST'])
# @login_required
# def create_session_view(doc_entry):
#     """Create new transfer session - display document details and add items"""
#     try:
#         sap = SAPIntegration()
#         print("DocValue--1>",doc_entry)
#         # Ensure logged in
#         if not sap.ensure_logged_in():
#             flash('SAP B1 authentication failed', 'error')
#             return redirect(url_for('grpo_transfer.index'))
#
#         # Get GRPO details using $crossjoin to properly join document header with line items
#         #url = f"{sap.base_url}/b1s/v1/$crossjoin(PurchaseDeliveryNotes,PurchaseDeliveryNotes/DocumentLines)?$expand=PurchaseDeliveryNotes($select=CardCode,CardName,DocumentStatus,DocNum,Series,DocDate,DocDueDate,DocTotal,DocEntry),PurchaseDeliveryNotes/DocumentLines($select=LineNum,ItemCode,ItemDescription,WarehouseCode,UnitsOfMeasurment,DocEntry,LineTotal,LineStatus,Quantity,Price,PriceAfterVAT)&$filter=PurchaseDeliveryNotes/DocumentStatus eq PurchaseDeliveryNotes/DocumentLines/LineStatus and PurchaseDeliveryNotes/DocEntry eq PurchaseDeliveryNotes/DocumentLines/DocEntry and PurchaseDeliveryNotes/DocumentLines/DocEntry eq {doc_entry}"
#         url = f"{sap.base_url}/b1s/v1/PurchaseDeliveryNotes?$filter=DocEntry eq {doc_entry}"
#         headers = {'Prefer': 'odata.maxpagesize=0'}
#
#         logger.debug(f"Fetching GRPO details from: {url}")
#         response = sap.session.get(url, headers=headers, timeout=30)
#
#         if response.status_code == 200:
#             data = response.json()
#             value_list = data.get('value', [])
#
#             if not value_list:
#                 logger.warning(f"No data found for GRPO document {doc_entry}")
#                 flash('No data found for this GRPO document', 'error')
#                 return redirect(url_for('grpo_transfer.index'))
#
#         # Extract document details (same for all rows) and line items
#         doc_details = None
#         line_items = []
#         bin_details = []
#         if value_list:
#             for item in value_list:
#                 if 'PurchaseDeliveryNotes' in item and not doc_details:
#                     doc_details = item['PurchaseDeliveryNotes']
#
#                 if 'PurchaseDeliveryNotes/DocumentLines' in item:
#                     line_items.append(item['PurchaseDeliveryNotes/DocumentLines'])
#                     bin_details.append(item['PurchaseDeliveryNotes/DocumentLines/DocumentLinesBinAllocations'])
#             if not doc_details:
#                 logger.error("PurchaseDeliveryNotes details not found in response")
#                 flash('Invalid data format from SAP', 'error')
#                 return redirect(url_for('grpo_transfer.index'))
#
#             logger.info(f"✅ Retrieved GRPO document {doc_entry} with {len(line_items)} line items")
#
#             # Create session
#             session_code = f"GRPO-{doc_entry}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
#
#             session = GRPOTransferSession()
#             session.session_code = session_code
#             session.grpo_doc_entry = doc_entry
#             session.grpo_doc_num = doc_details.get('DocNum')
#             session.series_id = doc_details.get('Series')
#             session.vendor_code = doc_details.get('CardCode')
#             session.vendor_name = doc_details.get('CardName')
#             session.doc_date = datetime.strptime(doc_details.get('DocDate', datetime.now().isoformat()), '%Y-%m-%d').date()
#             session.doc_due_date = datetime.strptime(doc_details.get('DocDueDate', datetime.now().isoformat()), '%Y-%m-%d').date() if doc_details.get('DocDueDate') else None
#             session.doc_total = float(doc_details.get('DocTotal', 0.0))
#
#             db.session.add(session)
#             db.session.flush()  # Flush to get session.id
#
#             # Add line items to session
#             for line in line_items:
#                 item = GRPOTransferItem()
#                 item.session_id = session.id
#                 item.line_num = line.get('LineNum')
#                 item.item_code = line.get('ItemCode')
#                 item.item_name = line.get('ItemDescription')
#                 item.item_description = line.get('ItemDescription')
#                 item.received_quantity = float(line.get('Quantity', 0))
#                 item.from_warehouse = line.get('WarehouseCode')
#                 item.unit_of_measure = str(line.get('UnitsOfMeasurment', '1'))
#                 item.price = float(line.get('Price', 0))
#                 item.line_total = float(line.get('LineTotal', 0))
#                 item.sap_base_entry = doc_entry
#                 item.sap_base_line = line.get('LineNum')
#                 for bin in bin_details:
#                     item.from_bin_abs_entry= bin.get('BinAbsEntry')
#                     bin_details = sap.get_bin_location_details(bin.get('BinAbsEntry'))
#                     # Add warehouse and bin code to the bin allocation
#                     item.from_bin_code = bin_details.get('BinCode')
#
#                 # ✅ NEW: Validate item type (Batch/Serial/Non-Managed) for EACH item
#                 item_code = line.get('ItemCode')
#                 try:
#                     # Call SAP query to validate item
#                     val_url = f"{sap.base_url}/b1s/v1/SQLQueries('ItemCode_Batch_Serial_Val')/List"
#                     val_headers = {'Prefer': 'odata.maxpagesize=0'}
#                     val_payload = {"ParamList": f"itemCode='{item_code}'"}
#                     print("DocValue--2>", doc_entry)
#                     val_response = sap.session.post(val_url, json=val_payload, headers=val_headers, timeout=30)
#
#                     if val_response.status_code == 200:
#                         val_data = val_response.json()
#                         val_items = val_data.get('value', [])
#
#                         if val_items:
#                             val_info = val_items[0]
#                             is_batch = val_info.get('BatchNum') == 'Y'
#                             is_serial = val_info.get('SerialNum') == 'Y'
#
#                             # Set item type flags
#                             item.is_batch_item = is_batch
#                             item.is_serial_item = is_serial
#                             item.is_non_managed = not is_batch and not is_serial
#
#                             logger.info(f"✅ Item {item_code} validated - Batch: {is_batch}, Serial: {is_serial}, Non-Managed: {item.is_non_managed}")
#                         else:
#                             logger.warning(f"⚠️ Item {item_code} not found in SAP B1 - marking as non-managed")
#                             item.is_non_managed = True
#                     else:
#                         logger.warning(f"⚠️ Failed to validate item {item_code}: {val_response.status_code}")
#                         item.is_non_managed = True
#                 except Exception as val_error:
#                     logger.warning(f"⚠️ Error validating item {item_code}: {str(val_error)}")
#                     item.is_non_managed = True
#
#                 db.session.add(item)
#
#             db.session.commit()
#
#             # ============================================================================
#             # FETCH AND SAVE BATCH NUMBERS FOR BATCH ITEMS
#             # ============================================================================
#             # ============================================================================
#             # FETCH AND SAVE BATCH NUMBERS (PER LINE ITEM)
#             # ============================================================================
#             logger.info(f"Fetching batch numbers for GRPO document {doc_entry}")
#
#             batch_url = f"{sap.base_url}/b1s/v1/SQLQueries('Get_Batch_By_DocEntry_ItemCode')/List"
#             batch_headers = {'Prefer': 'odata.maxpagesize=0'}
#
#             # 🔁 LOOP THROUGH SESSION ITEMS
#             session_items = GRPOTransferItem.query.filter_by(session_id=session.id).all()
#
#             for session_item in session_items:
#
#                 # ✅ ONLY batch items
#                 if not session_item.is_batch_item:
#                     logger.info(
#                         f"Skipping batch fetch for non-batch item "
#                         f"{session_item.item_code} (line {session_item.sap_base_line})"
#                     )
#                     continue
#
#                 param_list = (
#                     f"docEntry='{session_item.sap_base_entry}'&"
#                     f"itemCode='{session_item.item_code}'&"
#                     f"lineNum='{session_item.sap_base_line}'"
#                 )
#
#                 logger.info(f"Fetching batch for {session_item.item_code}, line {session_item.sap_base_line}")
#
#                 try:
#                     batch_response = sap.session.post(
#                         batch_url,
#                         json={"ParamList": param_list},
#                         headers=batch_headers,
#                         timeout=30
#                     )
#
#                     if batch_response.status_code != 200:
#                         logger.warning(
#                             f"Batch fetch failed for {session_item.item_code} "
#                             f"(line {session_item.sap_base_line}) "
#                             f"Status: {batch_response.status_code}"
#                         )
#                         continue
#
#                     batch_data = batch_response.json()
#                     batches = batch_data.get('value', [])
#
#                     if not batches:
#                         logger.warning(
#                             f"No batch data found for {session_item.item_code} "
#                             f"(line {session_item.sap_base_line})"
#                         )
#                         continue
#
#                     # 🧹 Clear old batches
#                     GRPOTransferBatch.query.filter_by(
#                         item_id=session_item.id
#                     ).delete()
#
#                     # 💾 Save batches
#                     for batch_info in batches:
#                         batch_number = batch_info.get('BatchNum')
#                         batch_quantity = float(batch_info.get('Quantity', 0))
#
#                         if not batch_number:
#                             continue
#
#                         batch = GRPOTransferBatch(
#                             item_id=session_item.id,
#                             batch_number=batch_number,
#                             batch_quantity=batch_quantity,
#                             approved_quantity=0,
#                             rejected_quantity=0,
#                             qc_status='pending'
#                         )
#
#                         if batch_info.get('ExpDate'):
#                             batch.expiry_date = datetime.strptime(
#                                 batch_info['ExpDate'], '%Y%m%d'
#                             ).date()
#
#                         if batch_info.get('MnfDate'):
#                             batch.manufacture_date = datetime.strptime(
#                                 batch_info['MnfDate'], '%Y%m%d'
#                             ).date()
#
#                         db.session.add(batch)
#
#                     logger.info(
#                         f"✅ Saved {len(batches)} batches for "
#                         f"{session_item.item_code} (line {session_item.sap_base_line})"
#                     )
#
#                 except Exception as e:
#                     logger.error(
#                         f"Batch error for {session_item.item_code} "
#                         f"(line {session_item.sap_base_line}): {str(e)}"
#                     )
#
#             db.session.commit()
#
#             log = GRPOTransferLog()
#             log.session_id = session.id
#             log.user_id = current_user.id
#             log.action = 'session_created'
#             log.description = f'Created transfer session for GRPO {doc_details.get("DocNum")} with {len(line_items)} items'
#             db.session.add(log)
#             db.session.commit()
#
#             logger.info(f"✅ Created session {session.id} with {len(line_items)} items")
#
#             # Redirect to session detail page
#             return redirect(url_for('grpo_transfer.session_detail', session_id=session.id))
#
#         else:
#             logger.error(f"SAP B1 API error: {response.status_code} - {response.text}")
#             flash(f'Failed to load GRPO details: {response.status_code}', 'error')
#             return redirect(url_for('grpo_transfer.index'))
#
#     except Exception as e:
#         logger.error(f"Error creating session view: {str(e)}")
#         db.session.rollback()
#         flash(f'Error: {str(e)}', 'error')
#         return redirect(url_for('grpo_transfer.index'))

# ============================================================================
# API ROUTES - Delete Session
# ============================================================================

@grpo_transfer_bp.route('/api/session/<int:session_id>/delete', methods=['DELETE'])
@login_required
def delete_session(session_id):
    """Delete a GRPO transfer session"""
    try:
        session = GRPOTransferSession.query.get(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        # Check if session can be deleted (only draft or in_progress)
        if session.status not in ['draft', 'in_progress']:
            return jsonify({
                'success': False,
                'error': f'Cannot delete session with status: {session.status}'
            }), 400
        
        # Delete related records
        GRPOTransferQRLabel.query.filter_by(session_id=session_id).delete()
        GRPOTransferLog.query.filter_by(session_id=session_id).delete()
        GRPOTransferBatch.query.filter(
            GRPOTransferBatch.item_id.in_(
                db.session.query(GRPOTransferItem.id).filter_by(session_id=session_id)
            )
        ).delete()
        GRPOTransferSplit.query.filter(
            GRPOTransferSplit.item_id.in_(
                db.session.query(GRPOTransferItem.id).filter_by(session_id=session_id)
            )
        ).delete()
        GRPOTransferItem.query.filter_by(session_id=session_id).delete()
        db.session.delete(session)
        db.session.commit()
        
        logger.info(f"✅ Session {session_id} deleted successfully")
        
        return jsonify({
            'success': True,
            'message': 'Session deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================

@grpo_transfer_bp.route('/api/sessions', methods=['GET'])
@login_required
def get_sessions():
    """Get all active sessions"""
    try:
        sessions = GRPOTransferSession.query.filter(
            GRPOTransferSession.status.in_(['draft', 'in_progress', 'completed','posted'])
        ).order_by(GRPOTransferSession.created_at.desc()).all()
        
        sessions_data = []
        for session in sessions:
            sessions_data.append({
                'id': session.id,
                'session_code': session.session_code,
                'grpo_doc_num': session.grpo_doc_num,
                'vendor_name': session.vendor_name,
                'status': session.status,
                'item_count': len(session.items),
                'created_at': session.created_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'sessions': sessions_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching sessions: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 1: Get Series List
# ============================================================================

@grpo_transfer_bp.route('/api/series-list', methods=['GET'])
@login_required
def get_series_list():
    """Get GRPO series list from SAP B1"""
    try:
        sap = SAPIntegration()
        
        # Ensure logged in
        if not sap.ensure_logged_in():
            return jsonify({
                'success': False,
                'error': 'SAP B1 authentication failed'
            }), 500
        
        # Call SAP B1 OData endpoint to get document series
        # Document Type 1250000001 = Purchase Delivery Note (GRPO)
        url = f"{sap.base_url}/b1s/v1/SQLQueries('GET_GRPO_Series')/List"
        headers = {'Prefer': 'odata.maxpagesize=0'}
        
        logger.debug(f"Fetching GRPO series from: {url}")
        response = sap.session.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            series_data = data.get('value', [])
            
            if series_data:
                series_list = []
                for series in series_data:
                    series_list.append({
                        'SeriesID': series.get('SeriesID'),
                        'SeriesName': series.get('SeriesName'),
                        'NextNumber': series.get('NextNumber')
                    })
                
                logger.info(f"✅ Retrieved {len(series_list)} GRPO series from SAP B1")
                return jsonify({
                    'success': True,
                    'series': series_list
                })
            else:
                logger.warning("No GRPO series found in SAP B1")
                return jsonify({
                    'success': True,
                    'series': [],
                    'message': 'No GRPO series configured in SAP B1'
                })
        else:
            logger.error(f"SAP B1 API error: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'error': f'SAP B1 API error: {response.status_code}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error fetching series list: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 2: Get Document Numbers by Series
# ============================================================================

@grpo_transfer_bp.route('/api/doc-numbers/<int:series_id>', methods=['GET'])
@login_required
def get_doc_numbers(series_id):
    """Get GRPO document numbers for selected series"""
    try:
        sap = SAPIntegration()

        # Ensure logged in
        if not sap.ensure_logged_in():
            return jsonify({
                'success': False,
                'error': 'SAP B1 authentication failed'
            }), 500

        # SAP SQL Query Service Layer endpoint
        url = f"{sap.base_url}/b1s/v1/SQLQueries('GET_GRPO_DocEntry_By_Series')/List"

        headers = {
            'Prefer': 'odata.maxpagesize=0',
            'Content-Type': 'application/json'
        }

        # ✅ Forward series_id to body
        payload = {
            "ParamList": f"seriesID='{series_id}'"
        }

        logger.debug(f"Fetching GRPO documents for series {series_id}")
        response = sap.session.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            doc_data = data.get('value', [])

            doc_list = []
            for doc in doc_data:
                doc_list.append({
                    'DocEntry': doc.get('DocEntry'),
                    'DocNum': doc.get('DocNum'),
                    'CardName': doc.get('CardName'),
                    'DocStatus': doc.get('DocStatus')
                })

            logger.info(f"✅ Retrieved {len(doc_list)} GRPO documents for series {series_id}")

            return jsonify({
                'success': True,
                'documents': doc_list
            })

        else:
            logger.error(f"SAP B1 API error: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'error': response.text
            }), 500

    except Exception as e:
        logger.exception("Error fetching document numbers")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# STEP 3: Get GRPO Document Details
# ============================================================================

@grpo_transfer_bp.route('/api/grpo-details/<int:doc_entry>', methods=['GET'])
@login_required
def get_grpo_details(doc_entry):
    """Get GRPO document details with line items using $crossjoin"""
    try:
        sap = SAPIntegration()
        
        # Ensure logged in
        if not sap.ensure_logged_in():
            return jsonify({
                'success': False,
                'error': 'SAP B1 authentication failed'
            }), 500
        
        # Use $crossjoin to properly join document header with line items
        url = f"{sap.base_url}/b1s/v1/$crossjoin(PurchaseDeliveryNotes,PurchaseDeliveryNotes/DocumentLines)?$expand=PurchaseDeliveryNotes($select=CardCode,CardName,DocumentStatus,DocNum,Series,DocDate,DocDueDate,DocTotal,DocEntry),PurchaseDeliveryNotes/DocumentLines($select=LineNum,ItemCode,ItemDescription,WarehouseCode,UnitsOfMeasurment,DocEntry,LineTotal,LineStatus,Quantity,Price,PriceAfterVAT)&$filter=PurchaseDeliveryNotes/DocumentStatus eq PurchaseDeliveryNotes/DocumentLines/LineStatus and PurchaseDeliveryNotes/DocEntry eq PurchaseDeliveryNotes/DocumentLines/DocEntry and PurchaseDeliveryNotes/DocumentLines/DocEntry eq {doc_entry}"
        headers = {'Prefer': 'odata.maxpagesize=0'}
        
        logger.debug(f"Fetching GRPO details from: {url}")
        response = sap.session.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            value_list = data.get('value', [])
            
            if not value_list:
                logger.warning(f"No data found for GRPO document {doc_entry}")
                return jsonify({
                    'success': True,
                    'document': None,
                    'line_items': [],
                    'message': 'No data found for this document'
                })
            
            # Extract document details (same for all rows) and line items
            doc_details = None
            line_items = []
            
            for item in value_list:
                if 'PurchaseDeliveryNotes' in item and not doc_details:
                    doc_details = item['PurchaseDeliveryNotes']
                
                if 'PurchaseDeliveryNotes/DocumentLines' in item:
                    line_items.append(item['PurchaseDeliveryNotes/DocumentLines'])
            
            logger.info(f"✅ Retrieved GRPO document {doc_entry} with {len(line_items)} line items")
            return jsonify({
                'success': True,
                'document': doc_details,
                'line_items': line_items
            })
        else:
            logger.error(f"SAP B1 API error: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'error': f'SAP B1 API error: {response.status_code}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error fetching GRPO details: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 4: Create Transfer Session
# ============================================================================

@grpo_transfer_bp.route('/api/create-session', methods=['POST'])
@login_required
def create_session():
    """Create a new GRPO transfer session"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['grpo_doc_entry', 'grpo_doc_num', 'series_id', 'vendor_code', 'vendor_name']
        if not all(field in data for field in required_fields):
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400
        
        # Generate session code
        session_code = f"GRPO-{data['grpo_doc_entry']}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create session
        session = GRPOTransferSession()
        session.session_code = session_code
        session.grpo_doc_entry = data['grpo_doc_entry']
        session.grpo_doc_num = data['grpo_doc_num']
        session.series_id = data['series_id']
        session.vendor_code = data['vendor_code']
        session.vendor_name = data['vendor_name']
        session.doc_date = datetime.strptime(data.get('doc_date', datetime.now().isoformat()), '%Y-%m-%d').date()
        session.doc_due_date = datetime.strptime(data.get('doc_due_date', datetime.now().isoformat()), '%Y-%m-%d').date() if data.get('doc_due_date') else None
        session.doc_total = float(data.get('doc_total', 0.0))
        
        db.session.add(session)
        db.session.commit()
        
        # Log activity
        log = GRPOTransferLog()
        log.session_id = session.id
        log.user_id = current_user.id
        log.action = 'session_created'
        log.description = f'Created transfer session for GRPO {data["grpo_doc_num"]}'
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'session_id': session.id,
            'session_code': session_code
        })
        
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 5: Validate Item Type (Batch/Serial/Non-Managed)
# ============================================================================

@grpo_transfer_bp.route('/api/validate-item/<item_code>', methods=['GET'])
@login_required
def validate_item(item_code):
    """Validate item type (batch, serial, or non-managed) using SQL Query"""
    try:
        sap = SAPIntegration()
        
        # Ensure logged in
        if not sap.ensure_logged_in():
            return jsonify({
                'success': False,
                'error': 'SAP B1 authentication failed'
            }), 500
        
        # Use SQL Query to validate item - this is the correct method for SAP B1
        url = f"{sap.base_url}/b1s/v1/SQLQueries('ItemCode_Batch_Serial_Val')/List"
        headers = {'Prefer': 'odata.maxpagesize=0'}
        payload = {"ParamList": f"itemCode='{item_code}'"}
        
        logger.debug(f"Validating item: {item_code}")
        response = sap.session.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('value', [])
            
            if items:
                item_info = items[0]
                
                # Check batch and serial flags
                is_batch = item_info.get('BatchNum') == 'Y'
                is_serial = item_info.get('SerialNum') == 'Y'
                is_non_managed = not is_batch and not is_serial
                
                logger.info(f"✅ Item {item_code} validated - Batch: {is_batch}, Serial: {is_serial}")
                return jsonify({
                    'success': True,
                    'item_code': item_code,
                    'item_name': item_info.get('ItemName'),
                    'is_batch_item': is_batch,
                    'is_serial_item': is_serial,
                    'is_non_managed': is_non_managed,
                    'batch_num': item_info.get('BatchNum'),
                    'serial_num': item_info.get('SerialNum')
                })
            else:
                logger.warning(f"Item {item_code} not found in SAP B1")
                return jsonify({
                    'success': False,
                    'error': 'Item not found in SAP B1'
                }), 404
        else:
            logger.error(f"SAP B1 API error: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'error': f'SAP B1 API error: {response.status_code}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error validating item: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 6: Get Batch Numbers for Item
# ============================================================================

@grpo_transfer_bp.route('/api/batch-numbers/<int:doc_entry>', methods=['GET'])
@login_required
def get_batch_numbers(doc_entry):
    """Get batch numbers for GRPO document using SQL Query"""
    try:
        sap = SAPIntegration()
        
        # Ensure logged in
        if not sap.ensure_logged_in():
            return jsonify({
                'success': False,
                'error': 'SAP B1 authentication failed'
            }), 500
        
        # Use SQL Query to get batch numbers - this is the correct method for SAP B1
        url = f"{sap.base_url}/b1s/v1/SQLQueries('Get_Batches_By_DocEntry')/List"
        headers = {'Prefer': 'odata.maxpagesize=0'}
        payload = {"ParamList": f"docEntry='{doc_entry}'"}
        
        logger.debug(f"Fetching batch numbers for document: {doc_entry}")
        response = sap.session.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            batches = data.get('value', [])
            
            if batches:
                logger.info(f"✅ Retrieved {len(batches)} batch numbers for document {doc_entry}")
                return jsonify({
                    'success': True,
                    'batches': batches
                })
            else:
                logger.warning(f"No batch numbers found for document {doc_entry}")
                return jsonify({
                    'success': True,
                    'batches': [],
                    'message': 'No batch numbers found'
                })
        else:
            logger.error(f"SAP B1 API error: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'error': f'SAP B1 API error: {response.status_code}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error fetching batch numbers: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 7: Get Warehouses
# ============================================================================

@grpo_transfer_bp.route('/api/warehouses', methods=['GET'])
@login_required
def get_warehouses():
    """Get list of warehouses from SAP B1"""
    try:
        sap = SAPIntegration()
        
        # Ensure logged in
        if not sap.ensure_logged_in():
            return jsonify({
                'success': False,
                'error': 'SAP B1 authentication failed'
            }), 500
        
        # Call SAP B1 OData endpoint
        url = f"{sap.base_url}/b1s/v1/Warehouses?$select=WarehouseName,WarehouseCode"
        headers = {'Prefer': 'odata.maxpagesize=0'}
        
        logger.debug(f"Fetching warehouses from: {url}")
        response = sap.session.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            warehouses = data.get('value', [])
            
            logger.info(f"✅ Retrieved {len(warehouses)} warehouses from SAP B1")
            return jsonify({
                'success': True,
                'warehouses': warehouses
            })
        else:
            logger.error(f"SAP B1 API error: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'error': f'SAP B1 API error: {response.status_code}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error fetching warehouses: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 8: Get Bin Codes for Warehouse
# ============================================================================

@grpo_transfer_bp.route('/api/bin-codes/<warehouse_code>', methods=['GET'])
@login_required
def get_bin_codes(warehouse_code):
    """Get bin codes for selected warehouse"""
    try:
        sap = SAPIntegration()
        
        # Ensure logged in
        if not sap.ensure_logged_in():
            return jsonify({
                'success': False,
                'error': 'SAP B1 authentication failed'
            }), 500
        
        # Call SAP B1 OData endpoint
        url = f"{sap.base_url}/b1s/v1/BinLocations?$select=AbsEntry,BinCode,Warehouse&$filter=Warehouse eq '{warehouse_code}'"
        headers = {'Prefer': 'odata.maxpagesize=0'}
        
        logger.debug(f"Fetching bin codes from: {url}")
        response = sap.session.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            bins = data.get('value', [])
            
            logger.info(f"✅ Retrieved {len(bins)} bin codes for warehouse {warehouse_code}")
            return jsonify({
                'success': True,
                'bins': bins
            })
        else:
            logger.warning(f"No bin codes found for warehouse {warehouse_code}")
            return jsonify({
                'success': True,
                'bins': [],
                'message': 'No bin codes found for warehouse'
            })
            
    except Exception as e:
        logger.error(f"Error fetching bin codes: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 8.5: Get Item Details
# ============================================================================

@grpo_transfer_bp.route('/api/session/<int:session_id>', methods=['GET'])
@login_required
def get_session_data(session_id):
    """Get complete session data for preview"""
    try:
        session = GRPOTransferSession.query.get(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        # Build session data with items and batches
        items_data = []
        for item in session.items:
            batches_data = []
            if item.batches:
                for batch in item.batches:
                    batches_data.append({
                        'id': batch.id,
                        'batch_number': batch.batch_number,
                        'batch_quantity': batch.batch_quantity,
                        'approved_quantity': batch.approved_quantity,
                        'rejected_quantity': batch.rejected_quantity,
                        'expiry_date': batch.expiry_date.isoformat() if batch.expiry_date else None,
                        'manufacture_date': batch.manufacture_date.isoformat() if batch.manufacture_date else None
                    })
            
            items_data.append({
                'id': item.id,
                'item_code': item.item_code,
                'item_name': item.item_name,
                'is_batch_item': item.is_batch_item,
                'received_quantity': item.received_quantity,
                'approved_quantity': item.approved_quantity,
                'rejected_quantity': item.rejected_quantity,
                'from_warehouse': item.from_warehouse,
                'from_bin_code': item.from_bin_code,
                'to_warehouse': item.to_warehouse,
                'to_bin_code': item.to_bin_code,
                'qc_status': item.qc_status,
                'batches': batches_data
            })
        
        return jsonify({
            'success': True,
            'session': {
                'id': session.id,
                'session_code': session.session_code,
                'grpo_doc_num': session.grpo_doc_num,
                'grpo_doc_entry': session.grpo_doc_entry,
                'vendor_name': session.vendor_name,
                'doc_date': session.doc_date.isoformat(),
                'doc_total': session.doc_total,
                'status': session.status,
                'items': items_data
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching session data: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 6.4: Validate Item Type (Batch/Serial/Non-Batch)
# ============================================================================

@grpo_transfer_bp.route('/api/item-validation/<item_code>', methods=['GET'])
@login_required
def validate_item_type(item_code):
    """Validate item type: Batch, Serial, or Non-Batch"""
    try:
        sap = SAPIntegration()
        
        if not sap.ensure_logged_in():
            return jsonify({
                'success': False,
                'error': 'SAP B1 authentication failed'
            }), 500
        
        # Call SAP query to validate item type
        url = f"{sap.base_url}/b1s/v1/SQLQueries('ItemCode_Batch_Serial_Val')/List"
        headers = {'Prefer': 'odata.maxpagesize=0'}
        payload = {"ParamList": f"itemCode='{item_code}'"}
        
        logger.debug(f"Validating item type for: {item_code}")
        response = sap.session.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('value', [])
            
            if items:
                item_info = items[0]
                batch_num = item_info.get('BatchNum', 'N')
                serial_num = item_info.get('SerialNum', 'N')
                
                # Determine item type
                if batch_num == 'Y':
                    item_type = 'batch'
                elif serial_num == 'Y':
                    item_type = 'serial'
                else:
                    item_type = 'non_batch'
                
                logger.info(f"✅ Item {item_code} validated as {item_type}")
                
                return jsonify({
                    'success': True,
                    'item_code': item_code,
                    'item_name': item_info.get('ItemName'),
                    'item_type': item_type,
                    'is_batch': batch_num == 'Y',
                    'is_serial': serial_num == 'Y',
                    'batch_num': batch_num,
                    'serial_num': serial_num
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'Item {item_code} not found in SAP B1'
                }), 404
        else:
            logger.error(f"SAP B1 API error: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'error': f'SAP B1 API error: {response.status_code}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error validating item: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 6.5: Get Batch Numbers for Item
# ============================================================================

@grpo_transfer_bp.route('/api/batches/<int:doc_entry>/<item_code>', methods=['GET'])
@login_required
def get_batches_for_item(doc_entry, item_code):
    """Get batch numbers for specific item in GRPO document"""
    try:
        sap = SAPIntegration()
        
        if not sap.ensure_logged_in():
            return jsonify({
                'success': False,
                'error': 'SAP B1 authentication failed'
            }), 500
        
        # Call SAP query to get batches
        url = f"{sap.base_url}/b1s/v1/SQLQueries('Get_Batches_By_DocEntry')/List"
        headers = {'Prefer': 'odata.maxpagesize=0'}
        payload = {"ParamList": f"docEntry='{doc_entry}'"}
        
        logger.debug(f"Fetching batches for doc_entry={doc_entry}, item_code={item_code}")
        response = sap.session.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            all_batches = data.get('value', [])
            
            # Filter batches for this item
            item_batches = [b for b in all_batches if b.get('ItemCode') == item_code]
            
            if item_batches:
                batches_data = []
                for batch in item_batches:
                    batches_data.append({
                        'batch_number': batch.get('BatchNum'),
                        'quantity': float(batch.get('Quantity', 0)),
                        'expiry_date': batch.get('ExpDate'),
                        'manufacture_date': batch.get('MnfDate'),
                        'line_num': batch.get('LineNum')
                    })
                
                logger.info(f"✅ Retrieved {len(batches_data)} batches for item {item_code}")
                
                return jsonify({
                    'success': True,
                    'item_code': item_code,
                    'batches': batches_data
                })
            else:
                return jsonify({
                    'success': True,
                    'item_code': item_code,
                    'batches': []
                })
        else:
            logger.error(f"SAP B1 API error: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'error': f'SAP B1 API error: {response.status_code}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error fetching batches: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 6.6: Get Bin Codes with AbsEntry
# ============================================================================

@grpo_transfer_bp.route('/api/bin-codes-with-entry/<warehouse_code>', methods=['GET'])
@login_required
def get_bin_codes_with_entry(warehouse_code):
    """Get bin codes with AbsEntry for warehouse"""
    try:
        sap = SAPIntegration()
        
        if not sap.ensure_logged_in():
            return jsonify({
                'success': False,
                'error': 'SAP B1 authentication failed'
            }), 500
        
        # Get bin codes from SAP
        url = f"{sap.base_url}/b1s/v1/Warehouses('{warehouse_code}')/BinLocations"
        headers = {'Prefer': 'odata.maxpagesize=0'}
        
        logger.debug(f"Fetching bin codes for warehouse: {warehouse_code}")
        response = sap.session.get(url, headers=headers, timeout=30)

        if response.status_code == 200:
            data = response.json()
            bins = data.get('value', [])

            bins_data = []
            for bin_loc in bins:
                bins_data.append({
                    'bin_code': bin_loc.get('BinCode'),
                    'abs_entry': bin_loc.get('AbsEntry'),
                    'warehouse_code': bin_loc.get('WarehouseCode')
                })

            logger.info(f"✅ Retrieved {len(bins_data)} bin codes for warehouse {warehouse_code}")
            
            return jsonify({
                'success': True,
                'warehouse_code': warehouse_code,
                'bins': bins_data
            })
        else:
            logger.error(f"SAP B1 API error: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'error': f'SAP B1 API error: {response.status_code}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error fetching bin codes: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 8.5: Get Item Details
# ============================================================================
@login_required
def get_item_details(item_id):
    """Get single item details"""
    try:
        item = GRPOTransferItem.query.get(item_id)
        if not item:
            return jsonify({
                'success': False,
                'error': 'Item not found'
            }), 404
        
        # Get batch info if batch item
        batches = []
        for batch in item.batches:
            batches.append({
                'id': batch.id,
                'batch_number': batch.batch_number,
                'batch_quantity': batch.batch_quantity,
                'approved_quantity': batch.approved_quantity,
                'rejected_quantity': batch.rejected_quantity,
                'expiry_date': batch.expiry_date.isoformat() if batch.expiry_date else None,
                'manufacture_date': batch.manufacture_date.isoformat() if batch.manufacture_date else None,
                'qc_status': batch.qc_status
            })
        
        return jsonify({
            'success': True,
            'item': {
                'id': item.id,
                'item_code': item.item_code,
                'item_name': item.item_name,
                'item_description': item.item_description,
                'is_batch_item': item.is_batch_item,
                'is_serial_item': item.is_serial_item,
                'is_non_managed': item.is_non_managed,
                'received_quantity': item.received_quantity,
                'approved_quantity': item.approved_quantity,
                'rejected_quantity': item.rejected_quantity,
                'from_warehouse': item.from_warehouse,
                'from_bin_code': item.from_bin_code,
                'to_warehouse': item.to_warehouse,
                'to_bin_code': item.to_bin_code,
                'unit_of_measure': item.unit_of_measure,
                'price': item.price,
                'line_total': item.line_total,
                'qc_status': item.qc_status,
                'qc_notes': item.qc_notes,
                'sap_base_entry': item.sap_base_entry,
                'sap_base_line': item.sap_base_line,
                'batches': batches
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching item: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 8.5: Get Item Details
# ============================================================================

@grpo_transfer_bp.route('/api/item/<int:item_id>', methods=['GET'])
@login_required
def get_item_details(item_id):
    """Get item details for editing"""
    try:
        item = GRPOTransferItem.query.get(item_id)
        if not item:
            return jsonify({
                'success': False,
                'error': 'Item not found'
            }), 404
        
        # Get batches if batch item
        batches_data = []
        if item.batches:
            for batch in item.batches:
                batches_data.append({
                    'id': batch.id,
                    'batch_number': batch.batch_number,
                    'batch_quantity': batch.batch_quantity,
                    'approved_quantity': batch.approved_quantity,
                    'rejected_quantity': batch.rejected_quantity,
                    'expiry_date': batch.expiry_date.isoformat() if batch.expiry_date else None,
                    'manufacture_date': batch.manufacture_date.isoformat() if batch.manufacture_date else None
                })
        
        return jsonify({
            'success': True,
            'item': {
                'id': item.id,
                'item_code': item.item_code,
                'item_name': item.item_name,
                'item_description': item.item_description,
                'is_batch_item': item.is_batch_item,
                'is_serial_item': item.is_serial_item,
                'is_non_managed': item.is_non_managed,
                'received_quantity': item.received_quantity,
                'approved_quantity': item.approved_quantity,
                'rejected_quantity': item.rejected_quantity,
                'from_warehouse': item.from_warehouse,
                'from_bin_code': item.from_bin_code,
                'to_warehouse': item.to_warehouse,
                'to_bin_code': item.to_bin_code,
                'approved_to_warehouse': item.approved_to_warehouse,
                'approved_to_bin_code': item.approved_to_bin_code,
                'rejected_to_warehouse': item.rejected_to_warehouse,
                'rejected_to_bin_code': item.rejected_to_bin_code,
                'unit_of_measure': item.unit_of_measure,
                'price': item.price,
                'line_total': item.line_total,
                'qc_status': item.qc_status,
                'qc_notes': item.qc_notes,
                'batches': batches_data
            }
        })
        
    except Exception as e:
        logger.error(f"Error fetching item: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 8.6: Update Item
# ============================================================================
@grpo_transfer_bp.route('/api/item/<int:item_id>', methods=['PUT'])
@login_required
def update_item(item_id):
    """Update single item with validation"""
    try:
        # ==============================================================
        # STEP 0: Fetch Item
        # ==============================================================
        item = GRPOTransferItem.query.get(item_id)
        if not item:
            return jsonify({
                'success': False,
                'error': 'Item not found'
            }), 404

        data = request.get_json() or {}
        sap = SAPIntegration()
        # # ==============================================================
        # # STEP 1: Validate Item Type when Warehouse is edited
        # # ==============================================================
        # if 'to_warehouse' in data or 'from_warehouse' in data:
        #     sap = SAPIntegration()
        #
        #     if not sap.ensure_logged_in():
        #         return jsonify({
        #             'success': False,
        #             'error': 'SAP B1 authentication failed'
        #         }), 500
        #
        #     logger.info(
        #         f"Validating item {item.item_code} "
        #         f"(DocEntry {item.sap_base_entry}, Line {item.sap_base_line})"
        #     )
        #
        #     # ---------- Item validation ----------
        #     val_url = f"{sap.base_url}/b1s/v1/SQLQueries('ItemCode_Batch_Serial_Val')/List"
        #     val_payload = {
        #         "ParamList": f"itemCode='{item.item_code}'"
        #     }
        #
        #     val_response = sap.session.post(
        #         val_url,
        #         json=val_payload,
        #         headers={'Prefer': 'odata.maxpagesize=0'},
        #         timeout=30
        #     )
        #
        #     if val_response.status_code == 200:
        #         val_data = val_response.json().get('value', [])
        #
        #         if val_data:
        #             info = val_data[0]
        #             is_batch = info.get('BatchNum') == 'Y'
        #             is_serial = info.get('SerialNum') == 'Y'
        #
        #             item.is_batch_item = is_batch
        #             item.is_serial_item = is_serial
        #             item.is_non_managed = not is_batch and not is_serial
        #
        #             logger.info(
        #                 f"Item {item.item_code} -> "
        #                 f"Batch:{is_batch}, Serial:{is_serial}"
        #             )
        #
        #             # ==================================================
        #             # STEP 2: Fetch Batch Details (if batch-managed)
        #             # ==================================================
        #             if is_batch:
        #                 batch_url = f"{sap.base_url}/b1s/v1/SQLQueries('Get_Batch_By_DocEntry_ItemCode')/List"
        #                 param_list = (
        #                     f"docEntry='{item.sap_base_entry}'&"
        #                     f"itemCode='{item.item_code}'&"
        #                     f"lineNum='{item.sap_base_line}'"
        #                 )
        #
        #                 batch_response = sap.session.post(
        #                     batch_url,
        #                     json={"ParamList": param_list},
        #                     headers={'Prefer': 'odata.maxpagesize=0'},
        #                     timeout=30
        #                 )
        #
        #                 # Clear existing batches
        #                 GRPOTransferBatch.query.filter_by(
        #                     item_id=item.id
        #                 ).delete()
        #
        #                 if batch_response.status_code == 200:
        #                     batches = batch_response.json().get('value', [])
        #
        #                     for b in batches:
        #                         batch_no = b.get('BatchNum')
        #                         if not batch_no:
        #                             continue
        #
        #                         batch = GRPOTransferBatch(
        #                             item_id=item.id,
        #                             batch_number=batch_no,
        #                             batch_quantity=float(b.get('Quantity', 0)),
        #                             approved_quantity=0,
        #                             rejected_quantity=0,
        #                             qc_status='pending'
        #                         )
        #
        #                         if b.get('ExpDate'):
        #                             batch.expiry_date = datetime.strptime(
        #                                 b['ExpDate'], '%Y%m%d'
        #                             ).date()
        #
        #                         if b.get('MnfDate'):
        #                             batch.manufacture_date = datetime.strptime(
        #                                 b['MnfDate'], '%Y%m%d'
        #                             ).date()
        #
        #                         db.session.add(batch)
        #
        #                 logger.info("Batch details refreshed successfully")
        #
        #             else:
        #                 # Non-batch item → clear batches
        #                 GRPOTransferBatch.query.filter_by(
        #                     item_id=item.id
        #                 ).delete()
        #
        #         else:
        #             logger.warning("Item not found in SAP validation query")
        #
        #     else:
        #         logger.warning(
        #             f"SAP validation failed: {val_response.status_code}"
        #         )
        #
        # ==============================================================
        # STEP 3: Update Editable Fields
        # ==============================================================
        if 'approved_quantity' in data:
            item.approved_quantity = float(data['approved_quantity'])

        if 'rejected_quantity' in data:
            item.rejected_quantity = float(data['rejected_quantity'])

        if 'qc_status' in data:
            item.qc_status = data['qc_status']

        if 'qc_notes' in data:
            item.qc_notes = data['qc_notes']

        # if 'from_warehouse' in data:
        #     item.from_warehouse = data['from_warehouse']

        # if 'from_bin_code' in data:
        #     item.from_bin_code = data['from_bin_code']

        # if 'from_bin_abs_entry' in data:
        #     item.from_bin_abs_entry = data['from_bin_abs_entry']

        if 'to_warehouse' in data:
            item.to_warehouse = data['to_warehouse']

        if 'to_bin_code' in data:
            item.to_bin_code = data['to_bin_code']

        if 'to_bin_abs_entry' in data:
            item.to_bin_abs_entry = data['to_bin_abs_entry']

        # ✅ NEW: Handle approved warehouse/bin designation
        if 'approved_to_warehouse' in data:
            item.approved_to_warehouse = data['approved_to_warehouse']

        if 'approved_to_bin_code' in data:
            item.approved_to_bin_code = data['approved_to_bin_code']
            print("item.approved_to_bin_code0--",item.approved_to_bin_code)
            binDetails = sap.get_bins_By_Bincode(item.approved_to_bin_code)
        #if 'approved_to_bin_abs_entry' in data:
        if binDetails and isinstance(binDetails, list):
            bin_row = binDetails[0]  # take first record
            item.approved_to_bin_abs_entry = bin_row.get("AbsEntry")

        # ✅ NEW: Handle rejected warehouse/bin designation
        if 'rejected_to_warehouse' in data:
            item.rejected_to_warehouse = data['rejected_to_warehouse']

        if 'rejected_to_bin_code' in data:
            item.rejected_to_bin_code = data['rejected_to_bin_code']
            binDetails = sap.get_bins_By_Bincode(item.rejected_to_bin_code)
        #if 'rejected_to_bin_abs_entry' in data:
        if binDetails and isinstance(binDetails, list):
                bin_row = binDetails[0]  # take first record
                print("bin_row->",bin_row)
                item.rejected_to_bin_abs_entry = bin_row.get("AbsEntry")
        # ==============================================================
        # STEP 4: Commit
        # ==============================================================
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Item updated successfully'
        })

    except Exception as e:
        db.session.rollback()
        logger.exception("Error updating item")

        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@grpo_transfer_bp.route('/api/item/<int:item_id>/validate-and-fetch-batches', methods=['POST'])
@login_required
def validate_item_and_fetch_batches(item_id):
    """
    Validate item type and fetch batch details when editing item.
    Called when user selects 'To Warehouse' in the edit modal.
    
    Request body:
    {
        "to_warehouse": "7000-QFG"
    }
    """
    try:
        item = GRPOTransferItem.query.get(item_id)
        if not item:
            return jsonify({
                'success': False,
                'error': 'Item not found'
            }), 404
        
        data = request.get_json()
        to_warehouse = data.get('to_warehouse')
        
        if not to_warehouse:
            return jsonify({
                'success': False,
                'error': 'To Warehouse is required'
            }), 400
        
        sap = SAPIntegration()
        
        # Ensure logged in
        if not sap.ensure_logged_in():
            return jsonify({
                'success': False,
                'error': 'SAP B1 authentication failed'
            }), 500
        
        # ============================================================================
        # STEP 1: Validate Item Type (Batch/Serial/Non-Managed)
        # ============================================================================
        logger.info(f"Validating item {item.item_code} (line {item.sap_base_line})")
        
        val_url = f"{sap.base_url}/b1s/v1/SQLQueries('ItemCode_Batch_Serial_Val')/List"
        val_headers = {'Prefer': 'odata.maxpagesize=0'}
        val_payload = {"ParamList": f"itemCode='{item.item_code}'"}
        
        val_response = sap.session.post(val_url, json=val_payload, headers=val_headers, timeout=30)
        
        if val_response.status_code != 200:
            logger.error(f"Failed to validate item: {val_response.status_code}")
            return jsonify({
                'success': False,
                'error': f'Failed to validate item: {val_response.status_code}'
            }), 500
        
        val_data = val_response.json()
        val_items = val_data.get('value', [])
        
        if not val_items:
            logger.warning(f"Item {item.item_code} not found in SAP B1")
            return jsonify({
                'success': False,
                'error': 'Item not found in SAP B1'
            }), 404
        
        val_info = val_items[0]
        is_batch = val_info.get('BatchNum') == 'Y'
        is_serial = val_info.get('SerialNum') == 'Y'
        is_non_managed = not is_batch and not is_serial
        
        # Update item type flags in database
        item.is_batch_item = is_batch
        item.is_serial_item = is_serial
        item.is_non_managed = is_non_managed
        item.to_warehouse = to_warehouse
        
        logger.info(f"✅ Item {item.item_code} validated - Batch: {is_batch}, Serial: {is_serial}, Non-Managed: {is_non_managed}")
        
        # ============================================================================
        # STEP 2: If Batch Item, Fetch Batch Details
        # ============================================================================
        batches_data = []
        
        if is_batch:
            logger.info(f"Fetching batch details for item {item.item_code} (line {item.sap_base_line})")
            
            # Use the new API endpoint that takes docEntry, itemCode, and lineNum
            batch_url = f"{sap.base_url}/b1s/v1/SQLQueries('Get_Batch_By_DocEntry_ItemCode')/List"
            batch_headers = {'Prefer': 'odata.maxpagesize=0'}
            
            # Build parameter list with docEntry, itemCode, and lineNum
            param_list = f"docEntry='{item.sap_base_entry}'&itemCode='{item.item_code}'&lineNum='{item.sap_base_line}'"
            batch_payload = {"ParamList": param_list}
            
            logger.debug(f"Batch query params: {param_list}")
            
            batch_response = sap.session.post(batch_url, json=batch_payload, headers=batch_headers, timeout=30)
            
            if batch_response.status_code == 200:
                batch_data = batch_response.json()
                batches = batch_data.get('value', [])
                
                if batches:
                    logger.info(f"✅ Retrieved {len(batches)} batch numbers for item {item.item_code}")
                    
                    # Delete existing batch records for this item
                    GRPOTransferBatch.query.filter_by(item_id=item.id).delete()
                    
                    # Create new batch records
                    for batch_info in batches:
                        batch_number = batch_info.get('BatchNum')
                        batch_quantity = float(batch_info.get('Quantity', 0))
                        
                        # Validate batch_number is not None or empty
                        if not batch_number or batch_number.strip() == '':
                            logger.warning(f"⚠️ Skipping batch with NULL/empty batch_number")
                            continue
                        
                        # Create batch record
                        batch = GRPOTransferBatch()
                        batch.item_id = item.id
                        batch.batch_number = batch_number
                        batch.batch_quantity = batch_quantity
                        batch.approved_quantity = item.approved_quantity
                        batch.rejected_quantity = item.rejected_quantity
                        batch.qc_status = 'pending'
                        
                        # Parse expiry date
                        if 'ExpDate' in batch_info:
                            try:
                                exp_date_str = batch_info.get('ExpDate')
                                batch.expiry_date = datetime.strptime(exp_date_str, '%Y%m%d').date()
                            except Exception as e:
                                logger.warning(f"Could not parse expiry date: {e}")
                        
                        # Parse manufacture date
                        if 'MnfDate' in batch_info:
                            try:
                                mnf_date_str = batch_info.get('MnfDate')
                                batch.manufacture_date = datetime.strptime(mnf_date_str, '%Y%m%d').date()
                            except Exception as e:
                                logger.warning(f"Could not parse manufacture date: {e}")
                        
                        db.session.add(batch)
                        
                        batches_data.append({
                            'batch_number': batch_number,
                            'batch_quantity': batch_quantity,
                            'expiry_date': batch.expiry_date.isoformat() if batch.expiry_date else None,
                            'manufacture_date': batch.manufacture_date.isoformat() if batch.manufacture_date else None
                        })
                        
                        logger.info(f"✅ Added batch {batch_number} for item {item.item_code} with qty {batch_quantity}")
                    
                    db.session.commit()
                else:
                    logger.warning(f"No batch numbers found for item {item.item_code}")
            else:
                logger.warning(f"Failed to fetch batch details: {batch_response.status_code}")
                logger.debug(f"Response: {batch_response.text}")
        
        # Commit item type updates
        db.session.commit()
        
        # Log activity
        log = GRPOTransferLog(
            session_id=item.session_id,
            user_id=current_user.id,
            action='item_validated_on_edit',
            description=f'Validated item {item.item_code} (line {item.sap_base_line}): Batch={is_batch}, Serial={is_serial}, Non-Managed={is_non_managed}'
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'item_code': item.item_code,
            'is_batch_item': is_batch,
            'is_serial_item': is_serial,
            'is_non_managed': is_non_managed,
            'batches': batches_data,
            'message': f'Item validated successfully. Found {len(batches_data)} batch numbers.' if is_batch else 'Item is non-batch managed.'
        })
        
    except Exception as e:
        logger.error(f"Error validating item and fetching batches: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 9: Add Item to Session
# ============================================================================

@grpo_transfer_bp.route('/api/session/<int:session_id>/add-item', methods=['POST'])
@login_required
def add_item_to_session(session_id):
    """Add item to transfer session"""
    try:
        data = request.get_json()
        session = GRPOTransferSession.query.get(session_id)
        
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        # Create transfer item
        item = GRPOTransferItem(
            session_id=session_id,
            line_num=data.get('line_num'),
            item_code=data.get('item_code'),
            item_name=data.get('item_name'),
            item_description=data.get('item_description'),
            is_batch_item=data.get('is_batch_item', False),
            is_serial_item=data.get('is_serial_item', False),
            is_non_managed=data.get('is_non_managed', False),
            received_quantity=float(data.get('received_quantity', 0)),
            from_warehouse=data.get('from_warehouse'),
            unit_of_measure=data.get('unit_of_measure', '1'),
            price=float(data.get('price', 0)),
            line_total=float(data.get('line_total', 0)),
            sap_base_entry=data.get('sap_base_entry'),
            sap_base_line=data.get('sap_base_line')
        )
        
        db.session.add(item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'item_id': item.id
        })
        
    except Exception as e:
        logger.error(f"Error adding item: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 10: QC Approval - Split and Approve Items
# ============================================================================

@grpo_transfer_bp.route('/api/session/<int:session_id>/qc-approve', methods=['POST'])
@login_required
def qc_approve_items(session_id):
    """QC team approves/rejects items with splits"""
    try:
        data = request.get_json()
        session = GRPOTransferSession.query.get(session_id)
        
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        # Process each item approval
        for item_approval in data.get('items', []):
            item = GRPOTransferItem.query.get(item_approval['item_id'])
            if not item:
                continue
            
            # Update item quantities and warehouse/bin information
            approved_qty = float(item_approval.get('approved_quantity', 0))
            rejected_qty = float(item_approval.get('rejected_quantity', 0))
            
            item.approved_quantity = approved_qty
            item.rejected_quantity = rejected_qty
            item.qc_status = item_approval.get('qc_status', 'pending')
            item.qc_notes = item_approval.get('qc_notes')
            item.to_warehouse = item_approval.get('to_warehouse')
            #item.to_bin_code = item_approval.get('to_bin_code')
            item.to_bin_abs_entry = item_approval.get('to_bin_abs_entry')  # ✅ NEW: Save to_bin AbsEntry
            # ✅ NEW: Update from_warehouse and from_bin_code
            item.from_warehouse = item_approval.get('from_warehouse', item.from_warehouse)
            #item.from_bin_code = item_approval.get('from_bin_code', item.from_bin_code)
            #item.from_bin_abs_entry = item_approval.get('from_bin_abs_entry')  # ✅ NEW: Save from_bin AbsEntry
            
            # ============================================================================
            # UPDATE BATCH QUANTITIES FOR BATCH ITEMS
            # ============================================================================
            if item.is_batch_item and item.batches:
                # Distribute approved and rejected quantities across batches proportionally
                total_batch_qty = sum(batch.batch_quantity for batch in item.batches)
                
                if total_batch_qty > 0:
                    for batch in item.batches:
                        # Calculate proportion of this batch
                        batch_proportion = batch.batch_quantity / total_batch_qty
                        
                        # Distribute quantities proportionally
                        batch.approved_quantity = approved_qty * batch_proportion
                        batch.rejected_quantity = rejected_qty * batch_proportion
                        batch.qc_status = item.qc_status
                        
                        logger.info(f"✅ Updated batch {batch.batch_number}: approved_qty={batch.approved_quantity}, rejected_qty={batch.rejected_quantity}")
            
            # Create splits if needed
            splits = item_approval.get('splits', [])
            for split_data in splits:
                split = GRPOTransferSplit(
                    item_id=item.id,
                    split_number=split_data.get('split_number'),
                    quantity=float(split_data.get('quantity', 0)),
                    status=split_data.get('status'),  # 'OK', 'NOTOK', 'HOLD'
                    from_warehouse=split_data.get('from_warehouse'),
                    from_bin_code=split_data.get('from_bin_code'),
                    to_warehouse=split_data.get('to_warehouse'),
                    to_bin_code=split_data.get('to_bin_code'),
                    batch_number=split_data.get('batch_number'),
                    notes=split_data.get('notes')
                )
                db.session.add(split)
        
        # Set status to 'completed' so transfer button appears
        session.status = 'completed'
        session.qc_approved_by = current_user.id
        db.session.commit()
        
        # Log activity
        log = GRPOTransferLog(
            session_id=session_id,
            user_id=current_user.id,
            action='qc_approved',
            description='QC team approved items'
        )
        db.session.add(log)
        db.session.commit()
        
        logger.info(f"✅ QC approval completed for session {session_id}")
        
        return jsonify({
            'success': True,
            'message': 'Items approved successfully'
        })
        
    except Exception as e:
        logger.error(f"Error approving items: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 11: Get QR Labels for Session
# ============================================================================

@grpo_transfer_bp.route('/api/session/<int:session_id>/labels', methods=['GET'])
@login_required
def get_session_labels(session_id):
    """Get QR labels for session"""
    try:
        session = GRPOTransferSession.query.get(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        labels = GRPOTransferQRLabel.query.filter_by(session_id=session_id).all()
        
        labels_data = []
        for label in labels:
            # Get the item to retrieve the actual item code
            item = GRPOTransferItem.query.get(label.item_id)
            item_code = item.item_code if item else 'Unknown'
            
            labels_data.append({
                'id': label.id,
                'item_code': item_code,
                'label_number': label.label_number,
                'total_labels': label.total_labels,
                'qr_data': label.qr_data,
                'batch_number': label.batch_number,
                'quantity': label.quantity
            })
        
        return jsonify({
            'success': True,
            'labels': labels_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching labels: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 12: Generate QR Labels for Approved Items
# ============================================================================

@grpo_transfer_bp.route('/api/session/<int:session_id>/generate-qr-labels', methods=['POST'])
@login_required
def generate_qr_labels(session_id):
    """Generate QR labels for approved items"""
    try:
        session = GRPOTransferSession.query.get(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        # Check if there are any approved items
        approved_items = [item for item in session.items if item.qc_status == 'approved' and item.approved_quantity > 0]
        
        if not approved_items:
            return jsonify({
                'success': False,
                'error': 'No approved items found. Please submit QC approval first.'
            }), 400
        
        labels = []
        label_count = 0
        
        for item in approved_items:
            # Generate one label per approved quantity unit
            approved_qty = int(item.approved_quantity)
            
            if approved_qty <= 0:
                continue
            
            for label_num in range(1, approved_qty + 1):
                qr_data = {
                    #'session_code': session.session_code,
                    'item_code': item.item_code,
                    'item_name': item.item_name,
                    'quantity': 1,
                    #'label': f'{label_num} of {approved_qty}',
                    'from_warehouse': item.from_warehouse,
                    'to_warehouse': item.to_warehouse,
                    'batch_number': item.batches[0].batch_number if item.batches else None,
                    #'timestamp': datetime.now().isoformat()
                }
                
                label = GRPOTransferQRLabel(
                    session_id=session_id,
                    item_id=item.id,
                    label_number=label_num,
                    total_labels=approved_qty,
                    qr_data=json.dumps(qr_data),
                    batch_number=item.batches[0].batch_number if item.batches else None,
                    quantity=1,
                    from_warehouse=item.from_warehouse,
                    to_warehouse=item.to_warehouse
                )
                db.session.add(label)
                labels.append(qr_data)
                label_count += 1
        
        if label_count == 0:
            return jsonify({
                'success': False,
                'error': 'No labels could be generated. Check approved quantities.'
            }), 400
        
        db.session.commit()
        
        logger.info(f"✅ Generated {label_count} QR labels for session {session_id}")
        
        return jsonify({
            'success': True,
            'labels_generated': label_count,
            'labels': labels
        })
        
    except Exception as e:
        logger.error(f"Error generating QR labels: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Error: {str(e)}'
        }), 500

# ============================================================================
# STEP 11B: Generate QR Labels with Pack Configuration
# ============================================================================

@grpo_transfer_bp.route('/api/session/<int:session_id>/generate-qr-labels-with-packs', methods=['POST'])
@login_required
def generate_qr_labels_with_packs(session_id):
    """Generate QR labels with pack-based distribution (one label per pack)"""
    try:
        data = request.get_json()
        pack_config = data.get('pack_config', {})
        
        session = GRPOTransferSession.query.get(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        # Check if there are any approved items
        approved_items = [item for item in session.items if item.qc_status == 'approved' and item.approved_quantity > 0]
        
        if not approved_items:
            return jsonify({
                'success': False,
                'error': 'No approved items found. Please submit QC approval first.'
            }), 400
        
        # DELETE OLD LABELS FIRST - Clear previous labels
        old_labels = GRPOTransferQRLabel.query.filter_by(session_id=session_id).all()
        for old_label in old_labels:
            db.session.delete(old_label)
        db.session.commit()
        logger.info(f"Deleted {len(old_labels)} old labels for session {session_id}")
        
        labels = []
        label_count = 0
        
        for item in approved_items:
            item_id = item.id
            approved_qty = int(item.approved_quantity)
            rejected_qty = int(item.rejected_quantity) if item.rejected_quantity else 0
            pack_count = int(pack_config.get(str(item_id), 1))
            
            if approved_qty <= 0 or pack_count <= 0:
                continue
            
            # Calculate distribution
            base_qty = approved_qty // pack_count
            remainder = approved_qty % pack_count
            
            logger.info(f"Item {item.item_code}: approved_qty={approved_qty}, rejected_qty={rejected_qty}, pack_count={pack_count}, base_qty={base_qty}, remainder={remainder}")
            
            # Handle batch items - generate labels per batch
            if item.is_batch_item and item.batches:
                # For batch items, generate one label per batch per pack
                for batch in item.batches:
                    batch_approved_qty = int(batch.approved_quantity)
                    if batch_approved_qty <= 0:
                        continue
                    
                    # Calculate packs for this batch
                    batch_base_qty = batch_approved_qty // pack_count
                    batch_remainder = batch_approved_qty % pack_count
                    
                    for pack_num in range(1, pack_count + 1):
                        # First pack gets the remainder
                        if pack_num == 1 and batch_remainder > 0:
                            pack_qty = batch_base_qty + batch_remainder
                        else:
                            pack_qty = batch_base_qty
                        
                        if pack_qty <= 0:
                            continue
                        
                        logger.info(f"Creating batch label: item={item.item_code}, batch={batch.batch_number}, pack_num={pack_num}, pack_qty={pack_qty}")
                        
                        qr_data = {
                            #'session_code': session.session_code,
                            #'grpo_doc_num': session.grpo_doc_num,
                            #'grpo_doc_entry': session.grpo_doc_entry,
                            'item': item.item_code,
                            #'item_name': item.item_name,
                            'batch': batch.batch_number,
                            'id' : f"{item.id}{item.line_num}{pack_num}{pack_count}",
                            #'approved_quantity': pack_qty,
                            #'rejected_quantity': 0,
                            'qty': pack_qty,
                            'pack': f'{pack_num} of {pack_count}',
                            # 'from_warehouse': item.from_warehouse,
                            # 'from_bin_code': item.from_bin_code,
                            # 'to_warehouse': item.to_warehouse,
                            'bin': item.to_bin_code,
                            # 'batch_info': {
                            #     'batch_number': batch.batch_number,
                            #     'item_code': item.item_code,
                            #     'item_name': item.item_name,
                            #     'batch_quantity': batch.batch_quantity,
                            #     'approved_quantity': batch.approved_quantity,
                            #     'rejected_quantity': batch.rejected_quantity,
                            #     #'expiry_date': batch.expiry_date.isoformat() if batch.expiry_date else None,
                            #    # 'manufacture_date': batch.manufacture_date.isoformat() if batch.manufacture_date else None
                            # },
                            #'timestamp': datetime.now().isoformat()
                        }
                        
                        label = GRPOTransferQRLabel(
                            session_id=session_id,
                            item_id=item.id,
                            label_number=pack_num,
                            total_labels=pack_count,
                            qr_data=json.dumps(qr_data),
                            batch_number=batch.batch_number,
                            quantity=pack_qty,
                            from_warehouse=item.from_warehouse,
                            to_warehouse=item.to_warehouse
                        )
                        db.session.add(label)
                        labels.append(qr_data)
                        label_count += 1
            else:
                # For non-batch items, generate labels per pack
                for pack_num in range(1, pack_count + 1):
                    # First pack gets the remainder
                    if pack_num == 1 and remainder > 0:
                        pack_qty = base_qty + remainder
                    else:
                        pack_qty = base_qty
                    
                    if pack_qty <= 0:
                        continue
                    
                    logger.info(f"Creating non-batch label: item={item.item_code}, pack_num={pack_num}, pack_qty={pack_qty}")
                    
                    qr_data = {
                        # 'session_code': session.session_code,
                        # 'grpo_doc_num': session.grpo_doc_num,
                        # 'grpo_doc_entry': session.grpo_doc_entry,
                        'item': item.item_code,
                        #'item_name': item.item_name,
                        'batch': None,
                        # 'approved_quantity': pack_qty,
                        # 'rejected_quantity': 0,
                        'id': f"{item.id}{item.line_num}{pack_num}{pack_count}",
                        'qty': pack_qty,
                        'pack': f'{pack_num} of {pack_count}',
                        # 'from_warehouse': item.from_warehouse,
                        # 'from_bin_code': item.from_bin_code,
                        # 'to_warehouse': item.to_warehouse,
                        'bin': item.to_bin_code,
                        #'batch_info': None,
                        #'timestamp': datetime.now().isoformat()
                    }
                    
                    label = GRPOTransferQRLabel(
                        session_id=session_id,
                        item_id=item.id,
                        label_number=pack_num,
                        total_labels=pack_count,
                        qr_data=json.dumps(qr_data),
                        batch_number=None,
                        quantity=pack_qty,
                        from_warehouse=item.from_warehouse,
                        to_warehouse=item.to_warehouse
                    )
                    db.session.add(label)
                    labels.append(qr_data)
                    label_count += 1
        
        if label_count == 0:
            return jsonify({
                'success': False,
                'error': 'No labels could be generated. Check approved quantities.'
            }), 400
        
        db.session.commit()
        
        logger.info(f"✅ Generated {label_count} QR labels (one per pack) for session {session_id}")
        
        return jsonify({
            'success': True,
            'labels_generated': label_count,
            'labels': labels
        })
        
    except Exception as e:
        logger.error(f"Error generating QR labels with packs: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Error: {str(e)}'
        }), 500

# ============================================================================
# STEP 12: Post Stock Transfer to SAP B1
# ============================================================================

@grpo_transfer_bp.route('/api/session/<int:session_id>/post-transfer', methods=['POST'])
@login_required
def post_transfer_to_sap(session_id):
    """Post stock transfer to SAP B1 - handles approved and rejected quantities separately"""
    try:
        session = GRPOTransferSession.query.get(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        sap = SAPIntegration()
        
        # Ensure logged in
        if not sap.ensure_logged_in():
            return jsonify({
                'success': False,
                'error': 'SAP B1 authentication failed'
            }), 500
        
        # Create separate transfers for approved and rejected quantities
        transfers_posted = []
        
        # ============================================================================
        # TRANSFER 1: APPROVED QUANTITIES
        # ============================================================================
        approved_transfer = {
            'DocDate': session.doc_date.isoformat(),
            'Comments': f'QC Approved WMS Transfer {session.session_code} by {current_user.first_name}',
            'FromWarehouse': session.items[0].from_warehouse if session.items else '',
            'ToWarehouse': session.items[0].to_warehouse if session.items else '',
            'StockTransferLines': []
        }
        
        line_num = 0
        for item in session.items:
            if item.qc_status != 'approved' or item.approved_quantity <= 0:
                continue
            
            # Handle batch items - ONLY if is_batch_item is True AND batches exist
            if item.is_batch_item and item.batches and len(item.batches) > 0:
                for batch in item.batches:
                    if batch.approved_quantity <= 0:
                        continue
                    
                    line = {
                        'LineNum': line_num,
                        'ItemCode': item.item_code,
                        'Quantity': batch.approved_quantity,
                        'WarehouseCode': item.to_warehouse,
                        'FromWarehouseCode': item.from_warehouse,
                        'BaseEntry': item.sap_base_entry,
                        'BaseLine': item.sap_base_line,
                        'BaseType': 'PurchaseDeliveryNotes',  # GRPO document type
                        'BatchNumbers': [
                            {
                                'BatchNumber': batch.batch_number,
                                'Quantity': batch.approved_quantity,
                                'BaseLineNumber':line_num
                            }
                        ],
                        'StockTransferLinesBinAllocations': []
                    }

                    # Add bin allocations if available
                    if item.from_bin_code and item.from_bin_abs_entry:
                        line['StockTransferLinesBinAllocations'].append({
                            'BinActionType': 'batFromWarehouse',
                            'BinAbsEntry': item.from_bin_abs_entry,
                            'Quantity': batch.approved_quantity,
                            'SerialAndBatchNumbersBaseLine': 0
                        })
                    
                    if item.to_bin_code and item.to_bin_abs_entry:
                        line['StockTransferLinesBinAllocations'].append({
                            'BinActionType': 'batToWarehouse',
                            'BinAbsEntry': item.to_bin_abs_entry,
                            'Quantity': batch.approved_quantity,
                            'SerialAndBatchNumbersBaseLine': 0
                        })
                    
                    approved_transfer['StockTransferLines'].append(line)
                    line_num += 1
            else:
                # Non-batch items - NO batch numbers
                line = {
                    'LineNum': line_num,
                    'ItemCode': item.item_code,
                    'Quantity': item.approved_quantity,
                    'WarehouseCode': item.to_warehouse,
                    'FromWarehouseCode': item.from_warehouse,
                    'BaseEntry': item.sap_base_entry,
                    'BaseLine': item.sap_base_line,
                    'BaseType': 'PurchaseDeliveryNotes',
                    'BatchNumbers': [],  # ✅ CRITICAL: Empty for non-batch items
                    'StockTransferLinesBinAllocations': []
                }
                
                # Add bin allocations if available
                if item.from_bin_code and item.from_bin_abs_entry:
                    line['StockTransferLinesBinAllocations'].append({
                        'BinActionType': 'batFromWarehouse',
                        'BinAbsEntry': item.from_bin_abs_entry,
                        'Quantity': item.approved_quantity,
                        'SerialAndBatchNumbersBaseLine': 0
                    })
                
                if item.to_bin_code and item.to_bin_abs_entry:
                    line['StockTransferLinesBinAllocations'].append({
                        'BinActionType': 'batToWarehouse',
                        'BinAbsEntry': item.to_bin_abs_entry,
                        'Quantity': item.approved_quantity,
                        'SerialAndBatchNumbersBaseLine': 0
                    })
                
                approved_transfer['StockTransferLines'].append(line)
                line_num += 1
        
        # Post approved transfer if there are items
        if approved_transfer['StockTransferLines']:
            url = f"{sap.base_url}/b1s/v1/StockTransfers"
            logger.debug(f"Posting approved stock transfer to: {url}")
            logger.debug(f"Approved transfer payload: {json.dumps(approved_transfer, indent=2)}")
            
            response = sap.session.post(url, json=approved_transfer, timeout=30)
            
            if response.status_code in [200, 201]:
                data = response.json()
                session.transfer_doc_entry = data.get('DocEntry')
                session.transfer_doc_num = data.get('DocNum')
                session.status = 'posted'
                transfers_posted.append({
                    'type': 'approved',
                    'doc_entry': data.get('DocEntry'),
                    'doc_num': data.get('DocNum')
                })
                
                logger.info(f"✅ Approved stock transfer posted to SAP B1 - DocEntry: {data.get('DocEntry')}, DocNum: {data.get('DocNum')}")
            else:
                logger.error(f"SAP B1 API error: {response.status_code} - {response.text}")
                session.status = response
                return jsonify({
                    'success': False,
                    'error': f'Failed to post approved transfer: {response.status_code}'
                }), 500
        
        # ============================================================================
        # TRANSFER 2: REJECTED QUANTITIES (if any)
        # ============================================================================
        rejected_transfer = {
            'DocDate': session.doc_date.isoformat(),
            'Comments': f'QC Rejected WMS Transfer {session.session_code} by {current_user.first_name}',
            'FromWarehouse': session.items[0].from_warehouse if session.items else '',
            'ToWarehouse': session.items[0].to_warehouse if session.items else '',  # Rejected warehouse
            'StockTransferLines': []
        }
        
        line_num = 0
        for item in session.items:
            if item.qc_status != 'approved' or item.rejected_quantity <= 0:
                continue
            
            # Handle batch items - ONLY if is_batch_item is True AND batches exist
            if item.is_batch_item and item.batches and len(item.batches) > 0:
                for batch in item.batches:
                    if batch.rejected_quantity <= 0:
                        continue
                    
                    line = {
                        'LineNum': line_num,
                        'ItemCode': item.item_code,
                        'Quantity': batch.rejected_quantity,
                        'WarehouseCode': item.rejected_to_warehouse,  # Rejected warehouse
                        'FromWarehouseCode': item.from_warehouse,
                        'BaseEntry': item.sap_base_entry,
                        'BaseLine': item.sap_base_line,
                        'BaseType': 'PurchaseDeliveryNotes',
                        'BatchNumbers': [
                            {
                                'BatchNumber': batch.batch_number,
                                'Quantity': batch.rejected_quantity
                            }
                        ],
                        'StockTransferLinesBinAllocations': []
                    }
                    
                    # Add bin allocations if available
                    if item.from_bin_code and item.from_bin_abs_entry:
                        line['StockTransferLinesBinAllocations'].append({
                            'BinActionType': 'batFromWarehouse',
                            'BinAbsEntry': item.from_bin_abs_entry,
                            'Quantity': batch.rejected_quantity,
                            'SerialAndBatchNumbersBaseLine': 0
                        })
                    
                    if item.to_bin_code and item.to_bin_abs_entry:
                        line['StockTransferLinesBinAllocations'].append({
                            'BinActionType': 'batToWarehouse',
                            'BinAbsEntry': item.rejected_to_bin_abs_entry,
                            'Quantity': batch.rejected_quantity,
                            'SerialAndBatchNumbersBaseLine': 0
                        })
                    
                    rejected_transfer['StockTransferLines'].append(line)
                    line_num += 1
            else:
                # Non-batch items - NO batch numbers
                line = {
                    'LineNum': line_num,
                    'ItemCode': item.item_code,
                    'Quantity': item.rejected_quantity,
                    'WarehouseCode': item.rejected_to_warehouse,  # Rejected warehouse
                    'FromWarehouseCode': item.from_warehouse,
                    'BaseEntry': item.sap_base_entry,
                    'BaseLine': item.sap_base_line,
                    'BaseType': 'PurchaseDeliveryNotes',
                    'BatchNumbers': [],  # ✅ CRITICAL: Empty for non-batch items
                    'StockTransferLinesBinAllocations': []
                }
                
                # Add bin allocations if available
                if item.from_bin_code and item.from_bin_abs_entry:
                    line['StockTransferLinesBinAllocations'].append({
                        'BinActionType': 'batFromWarehouse',
                        'BinAbsEntry': item.from_bin_abs_entry,
                        'Quantity': item.rejected_quantity,
                        'SerialAndBatchNumbersBaseLine': 0
                    })
                
                if item.to_bin_code and item.to_bin_abs_entry:
                    line['StockTransferLinesBinAllocations'].append({
                        'BinActionType': 'batToWarehouse',
                        'BinAbsEntry': item.rejected_to_bin_abs_entry,
                        'Quantity': item.rejected_quantity,
                        'SerialAndBatchNumbersBaseLine': 0
                    })
                
                rejected_transfer['StockTransferLines'].append(line)
                line_num += 1
        
        # Post rejected transfer if there are items
        if rejected_transfer['StockTransferLines']:
            url = f"{sap.base_url}/b1s/v1/StockTransfers"
            logger.debug(f"Posting rejected stock transfer to: {url}")
            logger.debug(f"Rejected transfer payload: {json.dumps(rejected_transfer, indent=2)}")
            
            response = sap.session.post(url, json=rejected_transfer, timeout=30)
            
            if response.status_code in [200, 201]:
                data = response.json()
                session.rejected_doc_entry = data.get('DocEntry')
                session.rejected_doc_num = data.get('DocNum')
                session.rejected_doc_status = 'posted'
                transfers_posted.append({
                    'type': 'rejected',
                    'doc_entry': data.get('DocEntry'),
                    'doc_num': data.get('DocNum')
                })
                
                logger.info(f"✅ Rejected stock transfer posted to SAP B1 - DocEntry: {data.get('DocEntry')}, DocNum: {data.get('DocNum')}")
            else:
                logger.error(f"SAP B1 API error: {response.status_code} - {response.text}")
                session.rejected_doc_status = response
                return jsonify({
                    'success': False,
                    'error': f'Failed to post rejected transfer: {response.status_code}'
                }), 500
        
        # Update session status
        db.session.commit()
        
        # Log activity
        log = GRPOTransferLog(
            session_id=session_id,
            user_id=current_user.id,
            action='posted',
            description=f'Posted to SAP B1 - Transfers: {json.dumps(transfers_posted)}',
            sap_response=json.dumps(transfers_posted)
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'transfers_posted': transfers_posted,
            'message': f'Successfully posted {len(transfers_posted)} transfer(s) to SAP B1'
        })
        
    except Exception as e:
        logger.error(f"Error posting transfer to SAP: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# ✅ NEW: POST APPROVED TRANSFER ONLY
# ============================================================================
@grpo_transfer_bp.route('/api/session/<int:session_id>/post-approved-transfer', methods=['POST'])
@login_required
def post_approved_transfer_to_sap(session_id):
    """Post ONLY approved quantities to SAP B1 as stock transfer"""
    try:
        session = GRPOTransferSession.query.get(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        sap = SAPIntegration()
        
        # Ensure logged in
        if not sap.ensure_logged_in():
            return jsonify({
                'success': False,
                'error': 'SAP B1 authentication failed'
            }), 500
        
        # Build approved transfer
        approved_transfer = {
            'DocDate': session.doc_date.isoformat(),
            'Comments': f'QC Approved WMS Transfer {session.session_code} by {current_user.first_name}',
            'FromWarehouse': session.items[0].from_warehouse if session.items else '',
            'ToWarehouse': '',  # Will be set per item
            'StockTransferLines': []
        }
        
        line_num = 0
        for item in session.items:
            if item.qc_status != 'approved' or item.approved_quantity <= 0:
                continue
            
            # Use approved_to_warehouse if set, otherwise use to_warehouse
            to_warehouse = item.approved_to_warehouse or item.to_warehouse
            to_bin_code = item.approved_to_bin_code or item.to_bin_code
            to_bin_abs_entry = item.approved_to_bin_abs_entry or item.to_bin_abs_entry
            
            if not to_warehouse:
                return jsonify({
                    'success': False,
                    'error': f'Item {item.item_code}: Approved warehouse not designated'
                }), 400
            
            # Set ToWarehouse from first item
            if line_num == 0:
                approved_transfer['ToWarehouse'] = to_warehouse
            
            # Handle batch items
            if item.is_batch_item and item.batches and len(item.batches) > 0:
                for batch in item.batches:
                    if batch.approved_quantity <= 0:
                        continue
                    
                    line = {
                        'LineNum': line_num,
                        'ItemCode': item.item_code,
                        'Quantity': batch.approved_quantity,
                        'WarehouseCode': to_warehouse,
                        'FromWarehouseCode': item.from_warehouse,
                        'BaseEntry': item.sap_base_entry,
                        'BaseLine': item.sap_base_line,
                        'BaseType': 'PurchaseDeliveryNotes',
                        'BatchNumbers': [
                            {
                                'BatchNumber': batch.batch_number,
                                'Quantity': batch.approved_quantity,
                                'BaseLineNumber': line_num
                            }
                        ],
                        'StockTransferLinesBinAllocations': []
                    }
                    
                    # Add bin allocations
                    if item.from_bin_code and item.from_bin_abs_entry:
                        line['StockTransferLinesBinAllocations'].append({
                            'BinActionType': 'batFromWarehouse',
                            'BinAbsEntry': item.from_bin_abs_entry,
                            'Quantity': batch.approved_quantity,
                            'SerialAndBatchNumbersBaseLine': 0
                        })
                    
                    if to_bin_code and to_bin_abs_entry:
                        line['StockTransferLinesBinAllocations'].append({
                            'BinActionType': 'batToWarehouse',
                            'BinAbsEntry': to_bin_abs_entry,
                            'Quantity': batch.approved_quantity,
                            'SerialAndBatchNumbersBaseLine': 0
                        })
                    
                    approved_transfer['StockTransferLines'].append(line)
                    line_num += 1
            else:
                # Non-batch items
                line = {
                    'LineNum': line_num,
                    'ItemCode': item.item_code,
                    'Quantity': item.approved_quantity,
                    'WarehouseCode': to_warehouse,
                    'FromWarehouseCode': item.from_warehouse,
                    'BaseEntry': item.sap_base_entry,
                    'BaseLine': item.sap_base_line,
                    'BaseType': 'PurchaseDeliveryNotes',
                    'BatchNumbers': [],
                    'StockTransferLinesBinAllocations': []
                }
                
                # Add bin allocations
                if item.from_bin_code and item.from_bin_abs_entry:
                    line['StockTransferLinesBinAllocations'].append({
                        'BinActionType': 'batFromWarehouse',
                        'BinAbsEntry': item.from_bin_abs_entry,
                        'Quantity': item.approved_quantity,
                        'SerialAndBatchNumbersBaseLine': 0
                    })
                
                if to_bin_code and to_bin_abs_entry:
                    line['StockTransferLinesBinAllocations'].append({
                        'BinActionType': 'batToWarehouse',
                        'BinAbsEntry': to_bin_abs_entry,
                        'Quantity': item.approved_quantity,
                        'SerialAndBatchNumbersBaseLine': 0
                    })
                
                approved_transfer['StockTransferLines'].append(line)
                line_num += 1
        
        # Validate that there are items to transfer
        if not approved_transfer['StockTransferLines']:
            return jsonify({
                'success': False,
                'error': 'No approved items to transfer'
            }), 400
        
        # Post to SAP B1
        url = f"{sap.base_url}/b1s/v1/StockTransfers"
        logger.debug(f"Posting approved stock transfer to: {url}")
        logger.debug(f"Approved transfer payload: {json.dumps(approved_transfer, indent=2)}")
        
        response = sap.session.post(url, json=approved_transfer, timeout=30)
        
        if response.status_code in [200, 201]:
            data = response.json()
            session.transfer_doc_entry = data.get('DocEntry')
            session.transfer_doc_num = data.get('DocNum')
            session.status = 'posted'
            db.session.commit()
            
            # Log activity
            log = GRPOTransferLog(
                session_id=session_id,
                user_id=current_user.id,
                action='transferred_approved',
                description=f'Posted approved transfer to SAP B1 - DocEntry: {data.get("DocEntry")}, DocNum: {data.get("DocNum")}',
                sap_response=json.dumps(data)
            )
            db.session.add(log)
            db.session.commit()
            
            logger.info(f"✅ Approved stock transfer posted - DocEntry: {data.get('DocEntry')}, DocNum: {data.get('DocNum')}")
            
            return jsonify({
                'success': True,
                'sap_doc_entry': data.get('DocEntry'),
                'sap_doc_num': data.get('DocNum'),
                'message': 'Approved transfer posted successfully'
            })
        else:
            logger.error(f"SAP B1 API error: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'error': f'Failed to post approved transfer: {response.status_code}'
            }), 500
        
    except Exception as e:
        logger.error(f"Error posting approved transfer: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# ✅ NEW: POST REJECTED TRANSFER ONLY
# ============================================================================
@grpo_transfer_bp.route('/api/session/<int:session_id>/post-rejected-transfer', methods=['POST'])
@login_required
def post_rejected_transfer_to_sap(session_id):
    """Post ONLY rejected quantities to SAP B1 as stock transfer"""
    try:
        session = GRPOTransferSession.query.get(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        sap = SAPIntegration()
        
        # Ensure logged in
        if not sap.ensure_logged_in():
            return jsonify({
                'success': False,
                'error': 'SAP B1 authentication failed'
            }), 500
        
        # Build rejected transfer
        rejected_transfer = {
            'DocDate': session.doc_date.isoformat(),
            'Comments': f'QC Rejected WMS Transfer {session.session_code} by {current_user.first_name}',
            'FromWarehouse': session.items[0].from_warehouse if session.items else '',
            'ToWarehouse': '',  # Will be set per item
            'StockTransferLines': []
        }
        
        line_num = 0
        for item in session.items:
            if item.qc_status != 'approved' or item.rejected_quantity <= 0:
                continue
            
            # Use rejected_to_warehouse if set, otherwise use to_warehouse
            to_warehouse = item.rejected_to_warehouse or item.to_warehouse
            to_bin_code = item.rejected_to_bin_code or item.to_bin_code
            to_bin_abs_entry = item.rejected_to_bin_abs_entry or item.to_bin_abs_entry
            
            if not to_warehouse:
                return jsonify({
                    'success': False,
                    'error': f'Item {item.item_code}: Rejected warehouse not designated'
                }), 400
            
            # Set ToWarehouse from first item
            if line_num == 0:
                rejected_transfer['ToWarehouse'] = to_warehouse
            
            # Handle batch items
            if item.is_batch_item and item.batches and len(item.batches) > 0:
                for batch in item.batches:
                    if batch.rejected_quantity <= 0:
                        continue
                    
                    line = {
                        'LineNum': line_num,
                        'ItemCode': item.item_code,
                        'Quantity': batch.rejected_quantity,
                        'WarehouseCode': to_warehouse,
                        'FromWarehouseCode': item.from_warehouse,
                        'BaseEntry': item.sap_base_entry,
                        'BaseLine': item.sap_base_line,
                        'BaseType': 'PurchaseDeliveryNotes',
                        'BatchNumbers': [
                            {
                                'BatchNumber': batch.batch_number,
                                'Quantity': batch.rejected_quantity
                            }
                        ],
                        'StockTransferLinesBinAllocations': []
                    }
                    
                    # Add bin allocations
                    if item.from_bin_code and item.from_bin_abs_entry:
                        line['StockTransferLinesBinAllocations'].append({
                            'BinActionType': 'batFromWarehouse',
                            'BinAbsEntry': item.from_bin_abs_entry,
                            'Quantity': batch.rejected_quantity,
                            'SerialAndBatchNumbersBaseLine': 0
                        })
                    
                    if to_bin_code and to_bin_abs_entry:
                        line['StockTransferLinesBinAllocations'].append({
                            'BinActionType': 'batToWarehouse',
                            'BinAbsEntry': to_bin_abs_entry,
                            'Quantity': batch.rejected_quantity,
                            'SerialAndBatchNumbersBaseLine': 0
                        })
                    
                    rejected_transfer['StockTransferLines'].append(line)
                    line_num += 1
            else:
                # Non-batch items
                line = {
                    'LineNum': line_num,
                    'ItemCode': item.item_code,
                    'Quantity': item.rejected_quantity,
                    'WarehouseCode': to_warehouse,
                    'FromWarehouseCode': item.from_warehouse,
                    'BaseEntry': item.sap_base_entry,
                    'BaseLine': item.sap_base_line,
                    'BaseType': 'PurchaseDeliveryNotes',
                    'BatchNumbers': [],
                    'StockTransferLinesBinAllocations': []
                }
                
                # Add bin allocations
                if item.from_bin_code and item.from_bin_abs_entry:
                    line['StockTransferLinesBinAllocations'].append({
                        'BinActionType': 'batFromWarehouse',
                        'BinAbsEntry': item.from_bin_abs_entry,
                        'Quantity': item.rejected_quantity,
                        'SerialAndBatchNumbersBaseLine': 0
                    })
                
                if to_bin_code and to_bin_abs_entry:
                    line['StockTransferLinesBinAllocations'].append({
                        'BinActionType': 'batToWarehouse',
                        'BinAbsEntry': to_bin_abs_entry,
                        'Quantity': item.rejected_quantity,
                        'SerialAndBatchNumbersBaseLine': 0
                    })
                
                rejected_transfer['StockTransferLines'].append(line)
                line_num += 1
        
        # Validate that there are items to transfer
        if not rejected_transfer['StockTransferLines']:
            return jsonify({
                'success': False,
                'error': 'No rejected items to transfer'
            }), 400
        
        # Post to SAP B1
        url = f"{sap.base_url}/b1s/v1/StockTransfers"
        logger.debug(f"Posting rejected stock transfer to: {url}")
        logger.debug(f"Rejected transfer payload: {json.dumps(rejected_transfer, indent=2)}")
        
        response = sap.session.post(url, json=rejected_transfer, timeout=30)
        
        if response.status_code in [200, 201]:
            data = response.json()
            db.session.commit()
            
            # Log activity
            log = GRPOTransferLog(
                session_id=session_id,
                user_id=current_user.id,
                action='transferred_rejected',
                description=f'Posted rejected transfer to SAP B1 - DocEntry: {data.get("DocEntry")}, DocNum: {data.get("DocNum")}',
                sap_response=json.dumps(data)
            )
            db.session.add(log)
            db.session.commit()
            
            logger.info(f"✅ Rejected stock transfer posted - DocEntry: {data.get('DocEntry')}, DocNum: {data.get('DocNum')}")
            
            return jsonify({
                'success': True,
                'sap_doc_entry': data.get('DocEntry'),
                'sap_doc_num': data.get('DocNum'),
                'message': 'Rejected transfer posted successfully'
            })
        else:
            logger.error(f"SAP B1 API error: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'error': f'Failed to post rejected transfer: {response.status_code}'
            }), 500
        
    except Exception as e:
        logger.error(f"Error posting rejected transfer: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500