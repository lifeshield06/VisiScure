from flask import request, jsonify, session, render_template, redirect, url_for
from . import waiter_bp
from .models import WaiterAuth, WaiterTableAssignment
from orders.table_models import Table
import json

@waiter_bp.route('/login-page')
def login_page():
    """QR-based login page - receives hotel_id from QR code"""
    hotel_id = request.args.get('hotel_id')
    hotel_name = request.args.get('hotel_name', 'Hotel')
    return render_template('waiter_login.html', hotel_id=hotel_id, hotel_name=hotel_name)

@waiter_bp.route('/login', methods=['POST'])
def login():
    """QR-based login - only waiter ID and name required"""
    data = request.json
    hotel_id = data.get('hotel_id')
    waiter_id = data.get('waiter_id')
    name = data.get('name')
    
    print(f"Waiter QR Login attempt - ID: {waiter_id}, Name: {name}, Hotel: {hotel_id}")
    
    result = WaiterAuth.login_qr(waiter_id, name, hotel_id)
    print(f"Waiter Login result: {result}")
    
    # Store session data if login successful
    if result.get('success'):
        session['waiter_id'] = result.get('id')
        session['waiter_name'] = result.get('name')
        session['waiter_hotel_id'] = result.get('hotel_id')
        session['waiter_hotel_name'] = result.get('hotel_name')
        session['is_waiter'] = True
    
    return jsonify(result)

@waiter_bp.route('/logout')
def logout():
    session.pop('waiter_id', None)
    session.pop('waiter_name', None)
    session.pop('waiter_hotel_id', None)
    session.pop('waiter_hotel_name', None)
    session.pop('is_waiter', None)
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@waiter_bp.route('/dashboard')
def dashboard():
    # Check session-based auth
    waiter_id = session.get('waiter_id')
    waiter_name = session.get('waiter_name')
    hotel_id = session.get('waiter_hotel_id')
    hotel_name = session.get('waiter_hotel_name')
    
    if not waiter_id or not waiter_name:
        return "Invalid access. Please login first.", 403
    
    # Get assigned tables
    assigned_tables = WaiterAuth.get_assigned_tables(waiter_id)
    tables_count = len(assigned_tables) if assigned_tables else 0
    
    # Get orders for waiter
    all_orders = WaiterAuth.get_orders_for_waiter(waiter_id)
    active_orders = [o for o in all_orders if o['order_status'] == 'ACTIVE']
    preparing_orders = [o for o in all_orders if o['order_status'] == 'PREPARING']
    completed_orders = [o for o in all_orders if o['order_status'] == 'COMPLETED']
    
    # Debug logging
    print(f"[WAITER DASHBOARD] waiter_id={waiter_id}, hotel_id={hotel_id}")
    print(f"[WAITER DASHBOARD] Assigned tables: {[t.get('table_number') for t in assigned_tables]}")
    print(f"[WAITER DASHBOARD] Active orders: {len(active_orders)}, Preparing: {len(preparing_orders)}, Completed: {len(completed_orders)}")
    
    # Use mobile template
    return render_template('waiter_dashboard_mobile.html',
                         waiter_id=waiter_id,
                         waiter_name=waiter_name,
                         hotel_id=hotel_id,
                         hotel_name=hotel_name,
                         tables=assigned_tables or [],
                         tables_count=tables_count,
                         all_orders=all_orders,
                         active_orders=active_orders,
                         preparing_orders=preparing_orders,
                         completed_orders=completed_orders,
                         active_count=len(active_orders),
                         preparing_count=len(preparing_orders),
                         completed_count=len(completed_orders))

@waiter_bp.route('/api/tables')
def get_tables():
    """Get all tables assigned to the waiter"""
    waiter_id = session.get('waiter_id')
    if not waiter_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    tables = WaiterAuth.get_assigned_tables(waiter_id)
    return jsonify({'success': True, 'tables': tables})

@waiter_bp.route('/api/orders')
def get_orders():
    """Get all orders for waiter's tables"""
    waiter_id = session.get('waiter_id')
    if not waiter_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    status = request.args.get('status')
    orders = WaiterAuth.get_orders_for_waiter(waiter_id, status)
    
    # Parse JSON items for each order
    for order in orders:
        if isinstance(order.get('items'), str):
            try:
                order['items'] = json.loads(order['items'])
            except:
                pass
        # Convert datetime to string for JSON serialization
        if order.get('created_at'):
            order['created_at'] = str(order['created_at'])
    
    return jsonify({'success': True, 'orders': orders})

@waiter_bp.route('/api/orders/<int:order_id>/status', methods=['POST'])
def update_order_status(order_id):
    """Update order status"""
    waiter_id = session.get('waiter_id')
    if not waiter_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    data = request.json
    new_status = data.get('status')
    
    if new_status not in ['ACTIVE', 'PREPARING', 'COMPLETED']:
        return jsonify({'success': False, 'message': 'Invalid status'})
    
    result = WaiterAuth.update_order_status(order_id, new_status, waiter_id)
    return jsonify(result)

@waiter_bp.route('/change-password', methods=['POST'])
def change_password():
    """Change waiter password"""
    waiter_id = session.get('waiter_id')
    if not waiter_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    data = request.json
    result = WaiterAuth.change_password(
        waiter_id,
        data.get('old_password'),
        data.get('new_password')
    )
    return jsonify(result)

@waiter_bp.route('/api/all-tables')
def get_all_tables():
    """Disabled - Waiters should only see their assigned tables"""
    return jsonify({'success': False, 'message': 'Access denied. Only managers can view all tables.'}), 403

@waiter_bp.route('/api/assign-table', methods=['POST'])
def assign_table():
    """Disabled - Only managers can assign tables to waiters"""
    return jsonify({'success': False, 'message': 'Access denied. Only managers can assign tables.'}), 403

@waiter_bp.route('/api/unassign-table', methods=['POST'])
def unassign_table():
    """Disabled - Only managers can unassign tables from waiters"""
    return jsonify({'success': False, 'message': 'Access denied. Only managers can unassign tables.'}), 403
