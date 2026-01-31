from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from modules.sales_delivery.models import DeliveryDocument, DeliveryItem, DeliveryItemSerial
from sap_integration import SAPIntegration
from datetime import datetime
from pathlib import Path
import logging

# Use absolute path for template_folder to support PyInstaller .exe builds
sales_delivery_bp = Blueprint('sales_delivery', __name__, 
                              template_folder=str(Path(__file__).resolve().parent / 'templates'),
                              url_prefix='/sales_delivery')


# @sales_delivery_bp.route('/')
# @login_required
# def index():
#     """Main page for Sales Order Against Delivery with filtering, search and pagination"""
#     page = request.args.get('page', 1, type=int)
#     per_page = request.args.get('per_page', 10, type=int)
#     search_term = request.args.get('search', '').strip()
#     from_date = request.args.get('from_date', '').strip()
#     to_date = request.args.get('to_date', '').strip()
#
#     query = DeliveryDocument.query.filter_by(user_id=current_user.id)
#
#     if search_term:
#         query = query.filter(
#             db.or_(
#                 DeliveryDocument.so_doc_num.ilike(f'%{search_term}%'),
#                 DeliveryDocument.card_name.ilike(f'%{search_term}%'),
#                 DeliveryDocument.card_code.ilike(f'%{search_term}%'),
#                 DeliveryDocument.sap_doc_num.ilike(f'%{search_term}%')
#             )
#         )
#
#     if from_date:
#         try:
#             from_dt = datetime.strptime(from_date, '%Y-%m-%d')
#             query = query.filter(DeliveryDocument.created_at >= from_dt)
#         except ValueError:
#             pass
#
#     if to_date:
#         try:
#             to_dt = datetime.strptime(to_date, '%Y-%m-%d')
#             to_dt = to_dt.replace(hour=23, minute=59, second=59)
#             query = query.filter(DeliveryDocument.created_at <= to_dt)
#         except ValueError:
#             pass
#
#     query = query.order_by(DeliveryDocument.created_at.desc())
#
#     pagination = query.paginate(page=page, per_page=per_page, error_out=False)
#     deliveries = pagination.items
#
#     return render_template('sales_delivery/sales_delivery_index.html',
#                          deliveries=deliveries,
#                          per_page=per_page,
#                          search_term=search_term,
#                          from_date=from_date,
#                          to_date=to_date,
#                          pagination=pagination)

from flask import request, jsonify


@sales_delivery_bp.route('/')
@login_required
def index():
    """Main page for Sales Order Against Delivery with filtering, search and pagination"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search_term = request.args.get('search', '').strip()
    from_date = request.args.get('from_date', '').strip()
    to_date = request.args.get('to_date', '').strip()

    query = DeliveryDocument.query.filter_by(user_id=current_user.id)

    if search_term:
        query = query.filter(
            db.or_(
                DeliveryDocument.so_doc_num.ilike(f'%{search_term}%'),
                DeliveryDocument.card_name.ilike(f'%{search_term}%'),
                DeliveryDocument.card_code.ilike(f'%{search_term}%'),
                DeliveryDocument.sap_doc_num.ilike(f'%{search_term}%')
            )
        )

    if from_date:
        try:
            from_dt = datetime.strptime(from_date, '%Y-%m-%d')
            query = query.filter(DeliveryDocument.created_at >= from_dt)
        except ValueError:
            pass

    if to_date:
        try:
            to_dt = datetime.strptime(to_date, '%Y-%m-%d')
            to_dt = to_dt.replace(hour=23, minute=59, second=59)
            query = query.filter(DeliveryDocument.created_at <= to_dt)
        except ValueError:
            pass

    query = query.order_by(DeliveryDocument.created_at.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    deliveries = pagination.items

    # 🔹 JSON response when request expects JSON
    if request.headers.get('Content-Type') == 'application/json' or request.accept_mimetypes.best == 'application/json':
        return jsonify({
            "success": True,
            "data": [
                {
                    "id": d.id,
                    "so_doc_num": d.so_doc_num,
                    "card_code": d.card_code,
                    "card_name": d.card_name,
                    "status": d.status,
                    "delivery_doc_num":d.sap_doc_num,
                    "created_at": d.created_at.isoformat()
                } for d in deliveries
            ],
            "pagination": {
                "page": pagination.page,
                "per_page": pagination.per_page,
                "total": pagination.total,
                "pages": pagination.pages,
                "has_next": pagination.has_next,
                "has_prev": pagination.has_prev
            }
        }), 200

    # 🔹 Default HTML response (unchanged)
    return render_template(
        'sales_delivery/sales_delivery_index.html',
        deliveries=deliveries,
        per_page=per_page,
        search_term=search_term,
        from_date=from_date,
        to_date=to_date,
        pagination=pagination
    )


@sales_delivery_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new delivery note from Sales Order"""
    if request.method == 'POST':
        so_series = request.form.get('so_series')
        print(so_series)
        so_doc_num = request.form.get('so_doc_num')
        print(so_doc_num)
        
        logging.info(f"📋 Creating delivery for SO Series: {so_series}, DocNum: {so_doc_num}")
        
        if not so_series or not so_doc_num:
            flash('Please select a series and enter a document number', 'error')
            return redirect(url_for('sales_delivery.index'))
        
        sap = SAPIntegration()
        
        logging.info(f"🔍 Getting DocEntry for SO Series: {so_series}, DocNum: {so_doc_num}")
        doc_entry = sap.get_so_doc_entry(so_series, so_doc_num)
        print(doc_entry)
        if not doc_entry:
            logging.error(f"❌ DocEntry not found for SO Series: {so_series}, DocNum: {so_doc_num}")
            flash(f'Sales Order {so_doc_num} not found in series {so_series}. Check SAP connection.', 'error')
            return redirect(url_for('sales_delivery.index'))
        
        logging.info(f"📥 Loading SO data for DocEntry: {doc_entry}")
        so_data = sap.get_sales_order_by_doc_entry(doc_entry)
        
        if not so_data:
            logging.error(f"❌ SO data not found for DocEntry: {doc_entry}")
            flash(f'Sales Order {so_doc_num} is not available or has no open lines', 'error')
            return redirect(url_for('sales_delivery.index'))
        
        logging.info(f"✅ SO data loaded: CardCode={so_data.get('CardCode')}, CardName={so_data.get('CardName')}, Lines={len(so_data.get('DocumentLines', []))}")
        
        existing = DeliveryDocument.query.filter_by(
            so_doc_entry=doc_entry,
            user_id=current_user.id,
            status='draft'
        ).first()
        
        if existing:
            return redirect(url_for('sales_delivery.detail', delivery_id=existing.id))
        
        delivery = DeliveryDocument(
            so_doc_entry=doc_entry,
            so_doc_num=so_data.get('DocNum'),
            so_series=so_data.get('Series'),
            card_code=so_data.get('CardCode'),
            card_name=so_data.get('CardName'),
            doc_currency=so_data.get('DocCurrency'),
            doc_date=datetime.now(),
            user_id=current_user.id
        )
        
        db.session.add(delivery)
        db.session.commit()
        
        flash(f'Sales Order {so_doc_num} loaded successfully', 'success')
        return redirect(url_for('sales_delivery.detail', delivery_id=delivery.id))
    
    return redirect(url_for('sales_delivery.index'))


# @sales_delivery_bp.route('/detail/<int:delivery_id>')
# @login_required
# def detail(delivery_id):
#     """Detail page for a delivery note"""
#     delivery = DeliveryDocument.query.get_or_404(delivery_id)
#
#     if delivery.user_id != current_user.id:
#         flash('Access denied', 'error')
#         return redirect(url_for('sales_delivery.index'))
#
#     sap = SAPIntegration()
#     so_data = sap.get_sales_order_by_doc_entry(delivery.so_doc_entry)
#
#     if not so_data:
#         flash('Unable to load Sales Order details from SAP', 'error')
#         return redirect(url_for('sales_delivery.index'))
#
#     return render_template('sales_delivery/sales_delivery_detail.html',
#                          delivery=delivery,
#                          so_data=so_data)

from flask import jsonify, request


@sales_delivery_bp.route('/detail/<int:delivery_id>')
@login_required
def detail(delivery_id):
    """Detail page for a delivery note"""
    delivery = DeliveryDocument.query.get_or_404(delivery_id)

    if delivery.user_id != current_user.id:
        if request.headers.get(
                'Content-Type') == 'application/json' or request.accept_mimetypes.best == 'application/json':
            return jsonify({
                "success": False,
                "message": "Access denied"
            }), 403

        flash('Access denied', 'error')
        return redirect(url_for('sales_delivery.index'))

    sap = SAPIntegration()
    so_data = sap.get_sales_order_by_doc_entry(delivery.so_doc_entry)

    if not so_data:
        if request.headers.get(
                'Content-Type') == 'application/json' or request.accept_mimetypes.best == 'application/json':
            return jsonify({
                "success": False,
                "message": "Unable to load Sales Order details from SAP"
            }), 400

        flash('Unable to load Sales Order details from SAP', 'error')
        return redirect(url_for('sales_delivery.index'))

    # 🔹 JSON response
    if request.headers.get('Content-Type') == 'application/json' or request.accept_mimetypes.best == 'application/json':
        return jsonify({
            "success": True,
            "delivery": {
                "id": delivery.id,
                "so_doc_entry": delivery.so_doc_entry,
                "so_doc_num": delivery.so_doc_num,
                "card_code": delivery.card_code,
                "card_name": delivery.card_name,
                "created_at": delivery.created_at.isoformat()
            },
            "sales_order": so_data
        }), 200

    # 🔹 Existing HTML response (unchanged)
    return render_template(
        'sales_delivery/sales_delivery_detail.html',
        delivery=delivery,
        so_data=so_data
    )


@sales_delivery_bp.route('/api/get_series')
@login_required
def api_get_series():
    """Get Sales Order series from SAP"""
    sap = SAPIntegration()
    series_list = sap.get_so_series()
    return jsonify({'success': True, 'series': series_list})


@sales_delivery_bp.route('/api/get_open_so_docnums')
@login_required
def api_get_open_so_docnums():
    """Get open Sales Order document numbers for a specific series"""
    series = request.args.get('series')
    
    if not series:
        return jsonify({'success': False, 'error': 'Series is required'})
    
    sap = SAPIntegration()
    documents = sap.get_open_so_docnums(series)
    
    return jsonify({'success': True, 'documents': documents})


@sales_delivery_bp.route('/api/validate_item', methods=['POST'])
@login_required
def api_validate_item():
    """Validate item code and get batch/serial requirements"""
    data = request.get_json()
    item_code = data.get('item_code')
    
    if not item_code:
        return jsonify({'success': False, 'error': 'Item code is required'})
    
    sap = SAPIntegration()
    validation = sap.validate_item_code(item_code)
    
    return jsonify(validation)


@sales_delivery_bp.route('/api/add_item', methods=['POST'])
@login_required
def api_add_item():
    """Add item to delivery document"""
    data = request.get_json()
    
    delivery_id = data.get('delivery_id')
    base_line = data.get('base_line')
    item_code = data.get('item_code')
    quantity = data.get('quantity')
    batch_number = data.get('batch_number')
    serial_number = data.get('serial_number')
    serial_numbers = data.get('serial_numbers', [])
    
    if not all([delivery_id, base_line is not None, item_code, quantity]):
        return jsonify({'success': False, 'error': 'Missing required fields'})
    
    delivery = DeliveryDocument.query.get(delivery_id)
    
    if not delivery or delivery.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Access denied'})
    
    sap = SAPIntegration()
    so_data = sap.get_sales_order_by_doc_entry(delivery.so_doc_entry)
    
    if not so_data:
        return jsonify({'success': False, 'error': 'Sales Order not found'})
    
    so_line = None
    for line in so_data.get('DocumentLines', []):
        if line.get('LineNum') == base_line:
            so_line = line
            break
    
    if not so_line:
        return jsonify({'success': False, 'error': 'Line not found in Sales Order'})
    
    validation = sap.validate_item_code(item_code)
    
    next_line_num = db.session.query(db.func.max(DeliveryItem.line_number)).filter_by(
        delivery_id=delivery_id
    ).scalar() or 0
    
    item = DeliveryItem(
        delivery_id=delivery_id,
        line_number=next_line_num + 1,
        base_line=base_line,
        item_code=item_code,
        item_description=so_line.get('ItemDescription'),
        warehouse_code=so_line.get('WarehouseCode'),
        quantity=float(quantity),
        open_quantity=so_line.get('RemainingOpenQuantity', 0),
        unit_price=so_line.get('UnitPrice', 0),
        uom_code=so_line.get('UoMCode'),
        batch_required=validation.get('batch_required', False),
        serial_required=validation.get('serial_required', False),
        batch_number=batch_number,
        serial_number=serial_number
    )
    
    db.session.add(item)
    db.session.flush()
    
    # If serial numbers are provided, allocate them
    if serial_numbers:
        serial_map = {}
        if 'SerialNumbers' in so_line:
            for serial in so_line['SerialNumbers']:
                serial_map[serial.get('InternalSerialNumber')] = serial
        
        for serial_num in serial_numbers:
            if serial_num in serial_map:
                serial_data = serial_map[serial_num]
                serial_obj = DeliveryItemSerial(
                    delivery_item_id=item.id,
                    internal_serial_number=serial_num,
                    system_serial_number=serial_data.get('SystemSerialNumber'),
                    quantity=serial_data.get('Quantity', 1.0),
                    base_line_number=serial_data.get('BaseLineNumber'),
                    allocation_status='allocated'
                )
                db.session.add(serial_obj)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': 'Item added successfully',
        'item_id': item.id
    })


@sales_delivery_bp.route('/api/get_available_serials', methods=['POST'])
@login_required
def api_get_available_serials():
    """Get available serial numbers for a specific SO line from SAP"""
    try:
        data = request.get_json()
        delivery_id = data.get('delivery_id')
        base_line = data.get('base_line')
        
        if not delivery_id or base_line is None:
            return jsonify({'success': False, 'error': 'Delivery ID and base line are required'})
        
        delivery = DeliveryDocument.query.get(delivery_id)
        if not delivery or delivery.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Access denied'})
        
        sap = SAPIntegration()
        so_data = sap.get_sales_order_by_doc_entry(delivery.so_doc_entry)
        
        if not so_data:
            return jsonify({'success': False, 'error': 'Sales Order not found'})
        
        # Find the line in SO
        so_line = None
        for line in so_data.get('DocumentLines', []):
            if line.get('LineNum') == base_line:
                so_line = line
                break
        
        if not so_line:
            return jsonify({'success': False, 'error': 'Line not found in Sales Order'})
        
        # Get serial numbers from the SO line
        available_serials = []
        if 'SerialNumbers' in so_line:
            for serial in so_line['SerialNumbers']:
                available_serials.append({
                    'internal_serial_number': serial.get('InternalSerialNumber'),
                    'system_serial_number': serial.get('SystemSerialNumber'),
                    'quantity': serial.get('Quantity', 1.0),
                    'base_line_number': serial.get('BaseLineNumber'),
                    'item_code': serial.get('ItemCode')
                })
        
        # Get already allocated serials for this line
        allocated_serials = db.session.query(DeliveryItemSerial.internal_serial_number).join(
            DeliveryItem, DeliveryItemSerial.delivery_item_id == DeliveryItem.id
        ).filter(
            DeliveryItem.delivery_id == delivery_id,
            DeliveryItem.base_line == base_line
        ).all()
        
        allocated_set = {s[0] for s in allocated_serials}
        
        # Filter out already allocated serials
        unallocated_serials = [s for s in available_serials if s['internal_serial_number'] not in allocated_set]
        
        return jsonify({
            'success': True,
            'available_serials': unallocated_serials,
            'total_available': len(unallocated_serials),
            'already_allocated': len(allocated_set)
        })
        
    except Exception as e:
        logging.error(f"Error getting available serials: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@sales_delivery_bp.route('/api/validate_serial_allocation', methods=['POST'])
@login_required
def api_validate_serial_allocation():
    """Validate if serial numbers can be allocated to a delivery line"""
    try:
        data = request.get_json()
        delivery_id = data.get('delivery_id')
        base_line = data.get('base_line')
        serial_numbers = data.get('serial_numbers', [])
        quantity = data.get('quantity', 0)
        
        if not delivery_id or base_line is None:
            return jsonify({'success': False, 'error': 'Delivery ID and base line are required'})
        
        delivery = DeliveryDocument.query.get(delivery_id)
        if not delivery or delivery.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Access denied'})
        
        sap = SAPIntegration()
        so_data = sap.get_sales_order_by_doc_entry(delivery.so_doc_entry)
        
        if not so_data:
            return jsonify({'success': False, 'error': 'Sales Order not found'})
        
        # Find the line in SO
        so_line = None
        for line in so_data.get('DocumentLines', []):
            if line.get('LineNum') == base_line:
                so_line = line
                break
        
        if not so_line:
            return jsonify({'success': False, 'error': 'Line not found in Sales Order'})
        
        # Get available serials from SO
        available_serials_map = {}
        if 'SerialNumbers' in so_line:
            for serial in so_line['SerialNumbers']:
                available_serials_map[serial.get('InternalSerialNumber')] = serial
        
        # Validate each serial number
        validation_results = []
        not_available = []
        
        for serial_num in serial_numbers:
            if serial_num in available_serials_map:
                validation_results.append({
                    'serial_number': serial_num,
                    'status': 'available',
                    'allocated': True
                })
            else:
                not_available.append(serial_num)
                validation_results.append({
                    'serial_number': serial_num,
                    'status': 'not_available',
                    'allocated': False
                })
        
        # Check if quantity matches number of serials
        if len(serial_numbers) != int(quantity):
            return jsonify({
                'success': False,
                'error': f'Quantity ({quantity}) does not match number of serial numbers ({len(serial_numbers)})',
                'validation_results': validation_results
            })
        
        if not_available:
            return jsonify({
                'success': False,
                'error': f'Serial numbers not available: {", ".join(not_available)}',
                'validation_results': validation_results,
                'not_available_serials': not_available
            })
        
        return jsonify({
            'success': True,
            'message': 'All serial numbers are available and allocated',
            'validation_results': validation_results
        })
        
    except Exception as e:
        logging.error(f"Error validating serial allocation: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@sales_delivery_bp.route('/api/allocate_serials', methods=['POST'])
@login_required
def api_allocate_serials():
    """Allocate serial numbers to a delivery line item"""
    try:
        data = request.get_json()
        delivery_item_id = data.get('delivery_item_id')
        serial_numbers = data.get('serial_numbers', [])
        
        if not delivery_item_id or not serial_numbers:
            return jsonify({'success': False, 'error': 'Delivery item ID and serial numbers are required'})
        
        item = DeliveryItem.query.get(delivery_item_id)
        if not item or item.delivery.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Access denied'})
        
        # Clear existing serials for this item
        DeliveryItemSerial.query.filter_by(delivery_item_id=delivery_item_id).delete()
        
        # Get SO data to fetch serial details
        sap = SAPIntegration()
        so_data = sap.get_sales_order_by_doc_entry(item.delivery.so_doc_entry)
        
        if not so_data:
            return jsonify({'success': False, 'error': 'Sales Order not found'})
        
        # Find the SO line
        so_line = None
        for line in so_data.get('DocumentLines', []):
            if line.get('LineNum') == item.base_line:
                so_line = line
                break
        
        if not so_line:
            return jsonify({'success': False, 'error': 'Line not found in Sales Order'})
        
        # Create serial mapping from SO
        serial_map = {}
        if 'SerialNumbers' in so_line:
            for serial in so_line['SerialNumbers']:
                serial_map[serial.get('InternalSerialNumber')] = serial
        
        # Allocate each serial number
        allocated_count = 0
        for serial_num in serial_numbers:
            if serial_num in serial_map:
                serial_data = serial_map[serial_num]
                serial_obj = DeliveryItemSerial(
                    delivery_item_id=delivery_item_id,
                    internal_serial_number=serial_num,
                    system_serial_number=serial_data.get('SystemSerialNumber'),
                    quantity=serial_data.get('Quantity', 1.0),
                    base_line_number=serial_data.get('BaseLineNumber'),
                    allocation_status='allocated'
                )
                db.session.add(serial_obj)
                allocated_count += 1
            else:
                db.session.rollback()
                return jsonify({
                    'success': False,
                    'error': f'Serial number {serial_num} not found in Sales Order'
                })
        
        db.session.commit()
        
        logging.info(f"✅ Allocated {allocated_count} serial numbers to delivery item {delivery_item_id}")
        
        return jsonify({
            'success': True,
            'message': f'Successfully allocated {allocated_count} serial numbers',
            'allocated_count': allocated_count
        })
        
    except Exception as e:
        logging.error(f"Error allocating serials: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@sales_delivery_bp.route('/api/submit_delivery', methods=['POST'])
@login_required
def api_submit_delivery():
    """Submit delivery note for QC approval (does not post to SAP yet)"""
    data = request.get_json()
    delivery_id = data.get('delivery_id')
    
    if not delivery_id:
        return jsonify({'success': False, 'error': 'Delivery ID is required'})
    
    delivery = DeliveryDocument.query.get(delivery_id)
    
    if not delivery or delivery.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Access denied'})
    
    if delivery.status != 'draft':
        return jsonify({'success': False, 'error': 'Delivery already submitted'})
    
    items = DeliveryItem.query.filter_by(delivery_id=delivery_id).all()
    
    if not items:
        return jsonify({'success': False, 'error': 'No items to deliver'})
    
    sap = SAPIntegration()
    
    # Validate we have all required data from SAP (but don't post yet)
    card_code = delivery.card_code
    doc_currency = delivery.doc_currency
    
    if not card_code:
        # Fetch from SAP if missing from delivery record
        logging.info(f"CardCode missing, fetching from SAP for DocEntry: {delivery.so_doc_entry}")
        so_data = sap.get_sales_order_by_doc_entry(delivery.so_doc_entry)
        if so_data:
            card_code = so_data.get('CardCode')
            if not doc_currency:
                doc_currency = so_data.get('DocCurrency', 'INR')
            # Update delivery record with missing data
            delivery.card_code = card_code
            delivery.card_name = so_data.get('CardName')
            delivery.doc_currency = doc_currency
            db.session.commit()
        else:
            return jsonify({'success': False, 'error': 'Unable to fetch Sales Order details from SAP'})
    
    # Submit for QC approval without posting to SAP
    delivery.status = 'submitted'
    delivery.submitted_at = datetime.utcnow()
    db.session.commit()
    
    logging.info(f"✅ Sales Delivery {delivery_id} submitted for QC approval by {current_user.username}")
    
    return jsonify({
        'success': True,
        'message': f'Delivery against SO {delivery.so_doc_num} submitted for QC approval'
    })


@sales_delivery_bp.route('/api/approve_delivery', methods=['POST'])
@login_required
def api_approve_delivery():
    """QC approve delivery and post to SAP B1"""
    try:
        data = request.get_json()
        delivery_id = data.get('delivery_id')
        
        if not delivery_id:
            return jsonify({'success': False, 'error': 'Delivery ID is required'})
        
        delivery = DeliveryDocument.query.get(delivery_id)
        
        if not delivery:
            return jsonify({'success': False, 'error': 'Delivery not found'})
        
        if not current_user.has_permission('qc_dashboard') and current_user.role not in ['admin', 'manager']:
            return jsonify({'success': False, 'error': 'QC permissions required'}), 403
        
        if delivery.status != 'submitted':
            return jsonify({'success': False, 'error': 'Only submitted deliveries can be approved'})
        
        qc_notes = data.get('qc_notes', '')
        
        delivery.status = 'qc_approved'
        delivery.qc_approver_id = current_user.id
        delivery.qc_approved_at = datetime.utcnow()
        delivery.qc_notes = qc_notes
        
        for item in delivery.items:
            item.qc_status = 'approved'
        
        sap = SAPIntegration()
        
        if not sap.ensure_logged_in():
            db.session.rollback()
            return jsonify({'success': False, 'error': 'SAP B1 authentication failed'}), 500
        
        document_lines = []
        for item in delivery.items:
            doc_line = {
                'BaseType': 17,
                'BaseEntry': delivery.so_doc_entry,
                'BaseLine': item.base_line,
                'ItemCode': item.item_code,
                'Quantity': item.quantity,
                'WarehouseCode': item.warehouse_code
            }
            
            if item.batch_required and item.batch_number:
                doc_line['BatchNumbers'] = [{
                    'BatchNumber': item.batch_number,
                    'Quantity': item.quantity
                }]
            
            # Add serial numbers if allocated
            if item.serial_numbers:
                serial_numbers_list = []
                for serial in item.serial_numbers:
                    serial_numbers_list.append({
                        'InternalSerialNumber': serial.internal_serial_number,
                        'Quantity': serial.quantity,
                        'SystemSerialNumber': serial.system_serial_number,
                        'BaseLineNumber': serial.base_line_number
                    })
                doc_line['SerialNumbers'] = serial_numbers_list
            elif item.serial_required and item.serial_number:
                doc_line['SerialNumbers'] = [{
                    'InternalSerialNumber': item.serial_number,
                    'Quantity': 1.0
                }]
            
            document_lines.append(doc_line)
        
        delivery_data = {
            'CardCode': delivery.card_code,
            'DocDate': datetime.now().strftime('%Y-%m-%d'),
            'DocCurrency': delivery.doc_currency or 'INR',
            'Comments': f'QC Approved - SO {delivery.so_doc_num}',
            'DocumentLines': document_lines
        }
        
        result = sap.post_sales_delivery(delivery_data)
        
        if not result.get('success'):
            db.session.rollback()
            error_msg = result.get('error', 'Unknown SAP error')
            logging.error(f"❌ SAP B1 posting failed for delivery {delivery_id}: {error_msg}")
            return jsonify({'success': False, 'error': f'SAP B1 posting failed: {error_msg}'}), 500
        
        delivery.sap_doc_entry = result.get('doc_entry')
        delivery.sap_doc_num = result.get('doc_num')
        delivery.status = 'posted'
        
        db.session.commit()
        
        logging.info(f"✅ Sales Delivery {delivery_id} approved and posted to SAP B1 as {delivery.sap_doc_num}")
        return jsonify({
            'success': True,
            'message': f'Delivery approved and posted to SAP B1 as {delivery.sap_doc_num}',
            'sap_doc_num': delivery.sap_doc_num
        })
        
    except Exception as e:
        logging.error(f"Error approving delivery: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@sales_delivery_bp.route('/api/reject_delivery', methods=['POST'])
@login_required
def api_reject_delivery():
    """QC reject delivery"""
    try:
        data = request.get_json()
        delivery_id = data.get('delivery_id')
        
        if not delivery_id:
            return jsonify({'success': False, 'error': 'Delivery ID is required'})
        
        delivery = DeliveryDocument.query.get(delivery_id)
        
        if not delivery:
            return jsonify({'success': False, 'error': 'Delivery not found'})
        
        if not current_user.has_permission('qc_dashboard') and current_user.role not in ['admin', 'manager']:
            return jsonify({'success': False, 'error': 'QC permissions required'}), 403
        
        if delivery.status != 'submitted':
            return jsonify({'success': False, 'error': 'Only submitted deliveries can be rejected'})
        
        qc_notes = data.get('qc_notes', '')
        
        if not qc_notes:
            return jsonify({'success': False, 'error': 'Rejection reason is required'}), 400
        
        delivery.status = 'rejected'
        delivery.qc_approver_id = current_user.id
        delivery.qc_approved_at = datetime.utcnow()
        delivery.qc_notes = qc_notes
        
        for item in delivery.items:
            item.qc_status = 'rejected'
        
        db.session.commit()
        
        logging.info(f"❌ Sales Delivery {delivery_id} rejected by {current_user.username}")
        return jsonify({'success': True, 'message': 'Delivery rejected by QC'})
        
    except Exception as e:
        logging.error(f"Error rejecting delivery: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@sales_delivery_bp.route('/api/delete_item/<int:item_id>', methods=['DELETE'])
@login_required
def api_delete_item(item_id):
    """Delete item from delivery"""
    item = DeliveryItem.query.get_or_404(item_id)
    
    if item.delivery.user_id != current_user.id:
        return jsonify({'success': False, 'error': 'Access denied'})
    
    if item.delivery.status != 'draft':
        return jsonify({'success': False, 'error': 'Cannot delete from submitted delivery'})
    
    db.session.delete(item)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Item deleted successfully'})


@sales_delivery_bp.route('/api/validate_serial_availability', methods=['POST'])
@login_required
def api_validate_serial_availability():
    """Validate if a serial number is available in the Sales Order DocumentLines"""
    try:
        data = request.get_json()
        print("datavalidate_serial_availability--->",data)
        base_line=data.get('base_line')
        serial_number = data.get('serial_number', '').strip()
        item_code = data.get('item_code', '').strip()
        warehouse_code = data.get('warehouse_code', '').strip()
        doc_entry = data.get('doc_entry')
        
        if not serial_number or not item_code or not warehouse_code:
            return jsonify({
                'success': False,
                'available': False,
                'error': 'Serial number, item code, and warehouse code are required'
            })
        
        if not doc_entry:
            return jsonify({
                'success': False,
                'available': False,
                'error': 'DocEntry is required for validation'
            })
        
        sap = SAPIntegration()
        so_data = sap.get_sales_order_by_doc_entry_I(doc_entry)
        
        if not so_data:
            return jsonify({
                'success': False,
                'available': False,
                'error': f'Sales Order with DocEntry {doc_entry} not found in SAP'
            })
        
        for line in so_data.get('DocumentLines', []):
            if line.get('ItemCode') == item_code and line.get('WarehouseCode') == warehouse_code and line.get('LineNum') == base_line:
                serial_numbers_in_line = line.get('SerialNumbers', [])
                for sn in serial_numbers_in_line:
                    if sn.get('InternalSerialNumber') == serial_number:
                        return jsonify({
                            'success': True,
                            'available': True,
                            'serial_number': serial_number,
                            'item_code': item_code,
                            'warehouse_code': warehouse_code,
                            'system_serial_number': sn.get('SystemSerialNumber'),
                            'base_line_number': sn.get('BaseLineNumber'),
                            'quantity': sn.get('Quantity', 1.0),
                            'message': f'Serial {serial_number} found in Sales Order for {item_code}'
                        })
        
        return jsonify({
            'success': True,
            'available': False,
            'serial_number': serial_number,
            'error': f'Serial {serial_number} not found in Sales Order for item {item_code} in warehouse {warehouse_code}'
        })
        
    except Exception as e:
        logging.error(f"Error validating serial availability: {str(e)}")
        return jsonify({'success': False, 'available': False, 'error': str(e)}), 500


@sales_delivery_bp.route('/api/get_inventory_serials', methods=['POST'])
@login_required
def api_get_inventory_serials():
    """Get available serial numbers from SAP inventory for an item/warehouse"""
    try:
        data = request.get_json()
        item_code = data.get('item_code', '').strip()
        warehouse_code = data.get('warehouse_code', '').strip()
        
        if not item_code or not warehouse_code:
            return jsonify({
                'success': False,
                'error': 'Item code and warehouse code are required'
            })
        
        sap = SAPIntegration()
        result = sap.get_available_serials_from_inventory(item_code, warehouse_code)
        
        return jsonify(result)
        
    except Exception as e:
        logging.error(f"Error getting inventory serials: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@sales_delivery_bp.route('/api/save_line_serials', methods=['POST'])
@login_required
def api_save_line_serials():
    """
    Validate and save serial numbers for a specific SO line.
    Validates: serial count <= open qty, serial availability in SAP inventory.
    Stores validated serials to DeliveryItemSerial table.
    """
    try:
        data = request.get_json()
        delivery_id = data.get('delivery_id')
        base_line = data.get('base_line')
        item_code = data.get('item_code', '').strip()
        warehouse_code = data.get('warehouse_code', '').strip()
        serial_numbers = data.get('serial_numbers', [])
        open_quantity = data.get('open_quantity', 0)
        
        if not delivery_id or base_line is None or not item_code:
            return jsonify({'success': False, 'error': 'Missing required fields'})
        
        delivery = DeliveryDocument.query.get(delivery_id)
        if not delivery or delivery.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Access denied'})
        
        if delivery.status != 'draft':
            return jsonify({'success': False, 'error': 'Cannot modify submitted delivery'})
        
        if len(serial_numbers) > open_quantity:
            return jsonify({
                'success': False,
                'error': f'Number of serial numbers ({len(serial_numbers)}) exceeds open quantity ({open_quantity})'
            })
        
        if not serial_numbers:
            return jsonify({'success': False, 'error': 'At least one serial number is required'})
        
        sap = SAPIntegration()
        validated_serials = []
        invalid_serials = []
        
        for serial_num in serial_numbers:
            serial_num = serial_num.strip()
            if not serial_num:
                continue
                
            validation = sap.validate_serial_in_inventory(serial_num, item_code, warehouse_code)
            
            if validation.get('available'):
                validated_serials.append({
                    'internal_serial_number': serial_num,
                    'system_serial_number': validation.get('system_serial_number', 0),
                    'quantity': 1
                })
            else:
                invalid_serials.append({
                    'serial_number': serial_num,
                    'reason': validation.get('error', 'Not available')
                })
        
        if invalid_serials:
            invalid_list = [s['serial_number'] for s in invalid_serials]
            return jsonify({
                'success': False,
                'error': f'Invalid or unavailable serial numbers: {", ".join(invalid_list)}',
                'invalid_serials': invalid_serials,
                'validated_count': len(validated_serials)
            })
        
        existing_item = DeliveryItem.query.filter_by(
            delivery_id=delivery_id,
            base_line=base_line
        ).first()
        
        if existing_item:
            DeliveryItemSerial.query.filter_by(delivery_item_id=existing_item.id).delete()
            existing_item.quantity = len(validated_serials)
        else:
            so_data = sap.get_sales_order_by_doc_entry(delivery.so_doc_entry)
            so_line = None
            if so_data:
                for line in so_data.get('DocumentLines', []):
                    if line.get('LineNum') == base_line:
                        so_line = line
                        break
            
            next_line_num = db.session.query(db.func.max(DeliveryItem.line_number)).filter_by(
                delivery_id=delivery_id
            ).scalar() or 0
            
            existing_item = DeliveryItem(
                delivery_id=delivery_id,
                line_number=next_line_num + 1,
                base_line=base_line,
                item_code=item_code,
                item_description=so_line.get('ItemDescription') if so_line else '',
                warehouse_code=warehouse_code,
                quantity=len(validated_serials),
                open_quantity=open_quantity,
                unit_price=so_line.get('UnitPrice', 0) if so_line else 0,
                uom_code=so_line.get('UoMCode') if so_line else None,
                serial_required=True
            )
            db.session.add(existing_item)
            db.session.flush()
        
        system_serial_counter = 1
        for serial_data in validated_serials:
            serial_obj = DeliveryItemSerial(
                delivery_item_id=existing_item.id,
                internal_serial_number=serial_data['internal_serial_number'],
                system_serial_number=serial_data.get('system_serial_number') or system_serial_counter,
                quantity=1.0,
                base_line_number=base_line,
                allocation_status='allocated'
            )
            db.session.add(serial_obj)
            system_serial_counter += 1
        
        db.session.commit()
        
        logging.info(f"✅ Saved {len(validated_serials)} serial numbers for delivery {delivery_id}, line {base_line}")
        
        return jsonify({
            'success': True,
            'message': f'Successfully validated and saved {len(validated_serials)} serial numbers',
            'validated_count': len(validated_serials),
            'item_id': existing_item.id
        })
        
    except Exception as e:
        logging.error(f"Error saving line serials: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@sales_delivery_bp.route('/api/post_delivery_to_sap', methods=['POST'])
@login_required
def api_post_delivery_to_sap():
    """
    Post delivery note to SAP B1 with serial numbers.
    Creates the delivery note in SAP with the format expected by SAP Service Layer.
    """
    try:
        data = request.get_json()
        delivery_id = data.get('delivery_id')
        
        if not delivery_id:
            return jsonify({'success': False, 'error': 'Delivery ID is required'})
        
        delivery = DeliveryDocument.query.get(delivery_id)
        
        if not delivery or delivery.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Access denied'})
        
        if delivery.status not in ['draft', 'submitted']:
            return jsonify({'success': False, 'error': 'Delivery already posted or not ready'})
        
        items = DeliveryItem.query.filter_by(delivery_id=delivery_id).all()
        
        if not items:
            return jsonify({'success': False, 'error': 'No items to deliver'})
        
        sap = SAPIntegration()
        
        if not sap.ensure_logged_in():
            return jsonify({'success': False, 'error': 'SAP B1 authentication failed'}), 500
        
        so_data = sap.get_sales_order_by_doc_entry(delivery.so_doc_entry)
        if not so_data:
            return jsonify({'success': False, 'error': 'Sales Order not found in SAP'})
        
        document_lines = []
        for item in items:
            doc_line = {
                'LineNum': item.base_line,
                'BaseType': 17,
                'BaseEntry': delivery.so_doc_entry,
                'BaseLine': item.base_line,
                'ItemCode': item.item_code,
                'Quantity': item.quantity,
                'WarehouseCode': item.warehouse_code,
                'UnitPrice': item.unit_price or 0
            }
            
            if item.serial_numbers:
                serial_numbers_list = []
                for idx, serial in enumerate(item.serial_numbers):
                    serial_numbers_list.append({
                        'InternalSerialNumber': serial.internal_serial_number,
                        'Quantity': 1,
                        'SystemSerialNumber': serial.system_serial_number or (idx + 1),
                        'BaseLineNumber': item.base_line
                    })
                doc_line['SerialNumbers'] = serial_numbers_list
            
            if item.batch_required and item.batch_number:
                doc_line['BatchNumbers'] = [{
                    'BatchNumber': item.batch_number,
                    'Quantity': item.quantity
                }]
            
            document_lines.append(doc_line)
        
        delivery_payload = {
            'CardCode': delivery.card_code or so_data.get('CardCode'),
            'DocDate': datetime.now().strftime('%Y-%m-%d'),
            'Comments': f'Delivery against SO {delivery.so_doc_num}',
            'BPL_IDAssignedToInvoice': so_data.get('BPL_IDAssignedToInvoice'),
            'DocumentLines': document_lines
        }
        
        logging.info(f"📤 Posting delivery to SAP: {delivery_payload}")
        
        result = sap.create_delivery_note(delivery_payload)
        
        if result.get('success'):
            delivery.sap_doc_entry = result.get('doc_entry')
            delivery.sap_doc_num = result.get('doc_num')
            delivery.status = 'posted'
            delivery.submitted_at = datetime.utcnow()
            db.session.commit()
            
            logging.info(f"✅ Delivery {delivery_id} posted to SAP as DocNum: {result.get('doc_num')}")
            
            return jsonify({
                'success': True,
                'message': f'Delivery Note {result.get("doc_num")} created successfully in SAP',
                'sap_doc_entry': result.get('doc_entry'),
                'sap_doc_num': result.get('doc_num')
            })
        else:
            error_msg = result.get('error', 'Unknown SAP error')
            logging.error(f"❌ SAP posting failed: {error_msg}")
            return jsonify({
                'success': False,
                'error': f'SAP B1 Error: {error_msg}'
            })
        
    except Exception as e:
        logging.error(f"Error posting delivery to SAP: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@sales_delivery_bp.route('/api/get_line_serials', methods=['POST'])
@login_required
def api_get_line_serials():
    """Get allocated serial numbers for a specific line item"""
    try:
        data = request.get_json()
        delivery_id = data.get('delivery_id')
        base_line = data.get('base_line')
        
        if not delivery_id or base_line is None:
            return jsonify({'success': False, 'error': 'Delivery ID and base line are required'})
        
        delivery = DeliveryDocument.query.get(delivery_id)
        if not delivery or delivery.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Access denied'})
        
        item = DeliveryItem.query.filter_by(
            delivery_id=delivery_id,
            base_line=base_line
        ).first()
        
        if not item:
            return jsonify({
                'success': True,
                'serial_numbers': [],
                'count': 0
            })
        
        serials = DeliveryItemSerial.query.filter_by(delivery_item_id=item.id).all()
        
        serial_list = []
        for serial in serials:
            serial_list.append({
                'id': serial.id,
                'internal_serial_number': serial.internal_serial_number,
                'system_serial_number': serial.system_serial_number,
                'quantity': serial.quantity,
                'allocation_status': serial.allocation_status
            })
        
        return jsonify({
            'success': True,
            'serial_numbers': serial_list,
            'count': len(serial_list),
            'item_id': item.id
        })
        
    except Exception as e:
        logging.error(f"Error getting line serials: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@sales_delivery_bp.route('/api/validate_serials_against_so', methods=['POST'])
@login_required
def api_validate_serials_against_so():
    """
    Validate entered serials against SAP Sales Order data.
    Checks:
    1. Serial exists in SO DocumentLines.SerialNumbers for the given ItemCode
    2. Serial matches the warehouse code
    3. Serial hasn't been allocated to another delivery item
    
    Returns validation results and adds validated serials to picked items grid.
    """
    try:
        data = request.get_json()
        print("Datat----->Vaidate JSON",data)
        delivery_id = data.get('delivery_id')
        doc_entry = data.get('doc_entry')
        base_line = data.get('base_line')
        item_code = data.get('item_code', '').strip()
        warehouse_code = data.get('warehouse_code', '').strip()
        serial_numbers = data.get('serial_numbers', [])
        
        if not delivery_id or not doc_entry or not item_code or not warehouse_code:
            return jsonify({
                'success': False,
                'error': 'Delivery ID, DocEntry, ItemCode, and WarehouseCode are required'
            })
        
        if not serial_numbers:
            return jsonify({
                'success': False,
                'error': 'At least one serial number is required'
            })
        
        delivery = DeliveryDocument.query.get(delivery_id)
        if not delivery or delivery.user_id != current_user.id:
            return jsonify({'success': False, 'error': 'Access denied'})
        
        # Fetch SO data from SAP
        sap = SAPIntegration()
        so_data = sap.get_sales_order_by_doc_entry_I(doc_entry)
        
        if not so_data:
            return jsonify({
                'success': False,
                'error': f'Sales Order with DocEntry {doc_entry} not found in SAP'
            })
        
        # Find the line with matching ItemCode and WarehouseCode
        so_line = None
        for line in so_data.get('DocumentLines', []):
            if line.get('ItemCode') == item_code and line.get('WarehouseCode') == warehouse_code and line.get('LineNum') == base_line:
                so_line = line
                break
        
        if not so_line:
            return jsonify({
                'success': False,
                'error': f'Line not found for ItemCode {item_code} in warehouse {warehouse_code}'
            })
        
        # Build map of available serials from SO
        available_serials_map = {}
        if 'SerialNumbers' in so_line:
            for serial in so_line['SerialNumbers']:
                internal_sn = serial.get('InternalSerialNumber')
                available_serials_map[internal_sn] = {
                    'system_serial_number': serial.get('SystemSerialNumber'),
                    'quantity': serial.get('Quantity', 1.0),
                    'base_line_number': serial.get('BaseLineNumber'),
                    'item_code': serial.get('ItemCode')
                }
        
        # Get already allocated serials for this SO line
        allocated_serials = db.session.query(DeliveryItemSerial.internal_serial_number).join(
            DeliveryItem, DeliveryItemSerial.delivery_item_id == DeliveryItem.id
        ).filter(
            DeliveryItem.delivery_id == delivery_id,
            DeliveryItem.base_line == so_line.get('LineNum')
        ).all()
        
        allocated_set = {s[0] for s in allocated_serials}
        
        # Validate each entered serial
        validation_results = []
        valid_serials = []
        invalid_serials = []
        
        for serial_num in serial_numbers:
            serial_num = serial_num.strip()
            if not serial_num:
                continue
            
            result = {
                'serial_number': serial_num,
                'status': 'unknown',
                'message': ''
            }
            
            if serial_num not in available_serials_map:
                result['status'] = 'not_found'
                result['message'] = f'Serial {serial_num} not found in Sales Order for {item_code}'
                invalid_serials.append(result)
            elif serial_num in allocated_set:
                result['status'] = 'already_allocated'
                result['message'] = f'Serial {serial_num} already allocated to another delivery item'
                invalid_serials.append(result)
            else:
                result['status'] = 'valid'
                result['message'] = 'Serial validated successfully'
                result['system_serial_number'] = available_serials_map[serial_num]['system_serial_number']
                result['quantity'] = available_serials_map[serial_num]['quantity']
                result['base_line_number'] = available_serials_map[serial_num]['base_line_number']
                valid_serials.append(result)
            
            validation_results.append(result)
        
        # If there are invalid serials, return error with details
        if invalid_serials:
            return jsonify({
                'success': False,
                'error': f'Validation failed for {len(invalid_serials)} serial(s)',
                'validation_results': validation_results,
                'valid_count': len(valid_serials),
                'invalid_count': len(invalid_serials),
                'invalid_serials': invalid_serials
            })
        
        if not valid_serials:
            return jsonify({
                'success': False,
                'error': 'No valid serial numbers to add'
            })
        
        # All serials are valid - add to delivery
        base_line = so_line.get('LineNum')
        
        # Check if item already exists for this line
        existing_item = DeliveryItem.query.filter_by(
            delivery_id=delivery_id,
            base_line=base_line
        ).first()
        
        if existing_item:
            # Update existing item quantity
            existing_item.quantity = len(valid_serials)
            delivery_item = existing_item
        else:
            # Create new delivery item
            next_line_num = db.session.query(db.func.max(DeliveryItem.line_number)).filter_by(
                delivery_id=delivery_id
            ).scalar() or 0
            
            delivery_item = DeliveryItem(
                delivery_id=delivery_id,
                line_number=next_line_num + 1,
                base_line=base_line,
                item_code=item_code,
                item_description=so_line.get('ItemDescription', ''),
                warehouse_code=warehouse_code,
                quantity=len(valid_serials),
                open_quantity=so_line.get('RemainingOpenQuantity', 0),
                unit_price=so_line.get('UnitPrice', 0),
                uom_code=so_line.get('UoMCode'),
                serial_required=True
            )
            db.session.add(delivery_item)
            db.session.flush()
        
        # Clear existing serials if updating
        if existing_item:
            DeliveryItemSerial.query.filter_by(delivery_item_id=delivery_item.id).delete()
        
        # Add validated serials
        for serial_data in valid_serials:
            serial_obj = DeliveryItemSerial(
                delivery_item_id=delivery_item.id,
                internal_serial_number=serial_data['serial_number'],
                system_serial_number=serial_data.get('system_serial_number', 0),
                quantity=serial_data.get('quantity', 1.0),
                base_line_number=serial_data.get('base_line_number', base_line),
                allocation_status='allocated'
            )
            db.session.add(serial_obj)
        
        db.session.commit()
        
        logging.info(f"✅ Validated and added {len(valid_serials)} serials to delivery {delivery_id}, line {base_line}")
        
        return jsonify({
            'success': True,
            'message': f'Successfully validated and added {len(valid_serials)} serial number(s)',
            'validation_results': validation_results,
            'valid_count': len(valid_serials),
            'item_id': delivery_item.id,
            'line_number': delivery_item.line_number,
            'picked_item': {
                'id': delivery_item.id,
                'line_number': delivery_item.line_number,
                'item_code': delivery_item.item_code,
                'item_description': delivery_item.item_description,
                'quantity': delivery_item.quantity,
                'warehouse_code': delivery_item.warehouse_code,
                'unit_price': delivery_item.unit_price,
                'serial_numbers': [s['serial_number'] for s in valid_serials]
            }
        })
        
    except Exception as e:
        logging.error(f"Error validating serials against SO: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500
