from flask import request, jsonify, session, render_template, redirect, url_for
from . import waiter_bp
from .models import WaiterAuth, WaiterTableAssignment
from .notification_service import WaiterNotificationService
from orders.table_models import Table
from waiter_calls.models import WaiterCallService
from database.db import get_db_connection
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
    
    # Fetch hotel logo
    hotel_logo = None
    if hotel_id:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT logo FROM hotels WHERE id = %s", (hotel_id,))
            result = cursor.fetchone()
            if result:
                hotel_logo = result[0]
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error fetching hotel logo: {e}")
    
    # Get assigned tables
    assigned_tables = WaiterAuth.get_assigned_tables(waiter_id)
    tables_count = len(assigned_tables) if assigned_tables else 0
    
    # Get orders for waiter
    active_orders = WaiterAuth.get_orders_for_waiter(waiter_id, 'ACTIVE')
    completed_orders = WaiterAuth.get_orders_for_waiter(waiter_id, 'COMPLETED')
    
    # Debug logging
    print(f"[WAITER DASHBOARD] waiter_id={waiter_id}, hotel_id={hotel_id}")
    print(f"[WAITER DASHBOARD] Assigned tables: {[t.get('table_number') for t in assigned_tables]}")
    print(f"[WAITER DASHBOARD] Active orders: {len(active_orders)}, Completed: {len(completed_orders)}")
    
    # Use mobile template
    return render_template('waiter_dashboard_mobile.html',
                         waiter_id=waiter_id,
                         waiter_name=waiter_name,
                         hotel_id=hotel_id,
                         hotel_name=hotel_name,
                         hotel_logo=hotel_logo,
                         tables=assigned_tables or [],
                         tables_count=tables_count,
                         active_orders=active_orders,
                         completed_orders=completed_orders,
                         active_count=len(active_orders),
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
    
    if new_status != 'COMPLETED':
        return jsonify({'success': False, 'message': 'Invalid status'})
    
    result = WaiterAuth.update_order_status(order_id, new_status, waiter_id)
    return jsonify(result)


@waiter_bp.route('/api/notifications/order-ready', methods=['GET'])
def get_order_ready_notifications():
    """Get pending order-ready notifications for logged-in waiter only."""
    waiter_id = session.get('waiter_id')
    if not waiter_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403

    notifications = WaiterNotificationService.get_pending_order_ready_notifications(waiter_id)
    return jsonify({
        'success': True,
        'notifications': notifications,
        'count': len(notifications)
    })


@waiter_bp.route('/api/notifications/order-ready/<int:notification_id>/acknowledge', methods=['POST'])
def acknowledge_order_ready_notification(notification_id):
    """Mark an order-ready notification as completed by assigned waiter."""
    waiter_id = session.get('waiter_id')
    if not waiter_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403

    result = WaiterNotificationService.acknowledge_order_ready_notification(notification_id, waiter_id)
    status_code = 200 if result.get('success') else 400
    return jsonify(result), status_code

@waiter_bp.route('/api/tip-statistics')
def get_tip_statistics():
    """Get tip statistics for the waiter"""
    waiter_id = session.get('waiter_id')
    hotel_id = session.get('waiter_hotel_id')
    if not waiter_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check per-waiter tips visibility from waiters table
        cursor.execute("""
            SELECT COALESCE(show_waiter_tips, 1) as show_waiter_tips
            FROM waiters
            WHERE id = %s
        """, (waiter_id,))
        visibility_result = cursor.fetchone()
        show_tips = visibility_result['show_waiter_tips'] if visibility_result else True
        
        # If tips are hidden, return zeros with a flag
        if not show_tips:
            cursor.close()
            conn.close()
            return jsonify({
                'success': True,
                'tips_visible': False,
                'today_tips': 0,
                'week_tips': 0,
                'month_tips': 0,
                'total_tips': 0
            })
        
        # Get today's tips
        cursor.execute("""
            SELECT COALESCE(SUM(tip_amount), 0) as today_tips
            FROM waiter_tips
            WHERE waiter_id = %s AND DATE(created_at) = CURDATE()
        """, (waiter_id,))
        today_result = cursor.fetchone()
        
        # Get this week's tips
        cursor.execute("""
            SELECT COALESCE(SUM(tip_amount), 0) as week_tips
            FROM waiter_tips
            WHERE waiter_id = %s AND YEARWEEK(created_at, 1) = YEARWEEK(CURDATE(), 1)
        """, (waiter_id,))
        week_result = cursor.fetchone()
        
        # Get this month's tips
        cursor.execute("""
            SELECT COALESCE(SUM(tip_amount), 0) as month_tips
            FROM waiter_tips
            WHERE waiter_id = %s AND YEAR(created_at) = YEAR(CURDATE()) AND MONTH(created_at) = MONTH(CURDATE())
        """, (waiter_id,))
        month_result = cursor.fetchone()
        
        # Get total tips
        cursor.execute("""
            SELECT COALESCE(SUM(tip_amount), 0) as total_tips
            FROM waiter_tips
            WHERE waiter_id = %s
        """, (waiter_id,))
        total_result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'tips_visible': True,
            'today_tips': float(today_result['today_tips']) if today_result else 0,
            'week_tips': float(week_result['week_tips']) if week_result else 0,
            'month_tips': float(month_result['month_tips']) if month_result else 0,
            'total_tips': float(total_result['total_tips']) if total_result else 0
        })
    except Exception as e:
        print(f"Error fetching tip statistics: {e}")
        return jsonify({
            'success': False,
            'message': 'Error fetching tip statistics',
            'today_tips': 0,
            'week_tips': 0,
            'month_tips': 0,
            'total_tips': 0
        })

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

# ============================================================================
# WAITER CALL SYSTEM - Integrated into existing waiter dashboard
# ============================================================================

@waiter_bp.route('/api/waiter-calls/pending')
def get_pending_calls():
    """Get pending waiter call requests for logged-in waiter"""
    waiter_id = session.get('waiter_id')
    
    if not waiter_id:
        return jsonify({'success': False, 'message': 'Unauthorized: Waiter not logged in'}), 401
    
    try:
        requests = WaiterCallService.get_pending_requests(waiter_id)
        return jsonify({
            'success': True,
            'requests': requests,
            'count': len(requests)
        }), 200
    except Exception as e:
        print(f"[WAITER_CALL API ERROR] get_pending_calls: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@waiter_bp.route('/api/waiter-calls/acknowledge', methods=['POST'])
def acknowledge_call():
    """Acknowledge a waiter call request"""
    waiter_id = session.get('waiter_id')
    
    if not waiter_id:
        return jsonify({'success': False, 'message': 'Unauthorized: Waiter not logged in'}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        request_id = data.get('request_id')
        if not request_id:
            return jsonify({'success': False, 'message': 'request_id is required'}), 400
        
        # Validate request_id is positive integer
        try:
            request_id = int(request_id)
            if request_id <= 0:
                return jsonify({'success': False, 'message': 'request_id must be positive'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'request_id must be an integer'}), 400
        
        result = WaiterCallService.acknowledge_request(request_id, waiter_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f"[WAITER_CALL API ERROR] acknowledge_call: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@waiter_bp.route('/api/waiter-calls/complete', methods=['POST'])
def complete_call():
    """Mark a waiter call request as completed"""
    waiter_id = session.get('waiter_id')
    
    if not waiter_id:
        return jsonify({'success': False, 'message': 'Unauthorized: Waiter not logged in'}), 401
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        request_id = data.get('request_id')
        if not request_id:
            return jsonify({'success': False, 'message': 'request_id is required'}), 400
        
        # Validate request_id is positive integer
        try:
            request_id = int(request_id)
            if request_id <= 0:
                return jsonify({'success': False, 'message': 'request_id must be positive'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'request_id must be an integer'}), 400
        
        result = WaiterCallService.complete_request(request_id, waiter_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    except Exception as e:
        print(f"[WAITER_CALL API ERROR] complete_call: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

@waiter_bp.route('/api/waiter-calls/voice-message')
def get_voice_message():
    """Get the configured voice message for waiter calls"""
    waiter_id = session.get('waiter_id')
    hotel_id = session.get('waiter_hotel_id')
    
    if not waiter_id or not hotel_id:
        return jsonify({'success': False, 'message': 'Unauthorized: Waiter not logged in'}), 401
    
    try:
        from database.db import get_db_connection
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT waiter_call_voice FROM hotels WHERE id = %s", (hotel_id,))
        result = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if result:
            voice_message = result.get('waiter_call_voice', 'Table {table} is calling waiter')
            return jsonify({'success': True, 'voice_message': voice_message}), 200
        
        return jsonify({'success': True, 'voice_message': 'Table {table} is calling waiter'}), 200
    except Exception as e:
        print(f"[WAITER_CALL API ERROR] get_voice_message: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500

