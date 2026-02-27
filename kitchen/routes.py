"""
Kitchen authentication and dashboard routes
"""
from flask import render_template, request, jsonify, session, redirect, url_for
from . import kitchen_bp
from .models import KitchenAuth
from database.db import get_db_connection

@kitchen_bp.route('/login', methods=['GET'])
def login_page():
    """Render kitchen login page"""
    return render_template('kitchen_login.html')

@kitchen_bp.route('/login', methods=['POST'])
def login():
    """Authenticate kitchen user using ID and name"""
    try:
        data = request.get_json()
        kitchen_unique_id = data.get('kitchen_id')
        kitchen_name = data.get('kitchen_name')
        
        if not kitchen_unique_id or not kitchen_name:
            return jsonify({'success': False, 'message': 'Kitchen ID and Kitchen Name required'})
        
        result = KitchenAuth.authenticate(kitchen_unique_id, kitchen_name)
        
        if result['success']:
            # Store kitchen info in session
            kitchen = result['kitchen']
            session['kitchen_id'] = kitchen['id']
            session['kitchen_name'] = kitchen['section_name']
            session['kitchen_unique_id'] = kitchen['kitchen_unique_id']
            session['kitchen_hotel_id'] = kitchen['hotel_id']
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'redirect': url_for('kitchen.dashboard')
            })
        else:
            return jsonify(result)
            
    except Exception as e:
        print(f"[KITCHEN_LOGIN] Error: {e}")
        return jsonify({'success': False, 'message': 'Server error'})

@kitchen_bp.route('/logout')
def logout():
    """Logout kitchen user"""
    session.pop('kitchen_id', None)
    session.pop('kitchen_name', None)
    session.pop('kitchen_unique_id', None)
    session.pop('kitchen_hotel_id', None)
    return redirect(url_for('kitchen.login_page'))

@kitchen_bp.route('/dashboard')
def dashboard():
    """Kitchen dashboard - requires authentication"""
    kitchen_id = session.get('kitchen_id')
    kitchen_name = session.get('kitchen_name')
    
    if not kitchen_id:
        return redirect(url_for('kitchen.login_page'))
    
    return render_template('kitchen_auth_dashboard.html',
                         kitchen_id=kitchen_id,
                         kitchen_name=kitchen_name)

@kitchen_bp.route('/api/orders', methods=['GET'])
def get_kitchen_orders():
    """Get orders for authenticated kitchen"""
    kitchen_id = session.get('kitchen_id')
    
    if not kitchen_id:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Get assigned categories for this kitchen
        cursor.execute("""
            SELECT category_id
            FROM kitchen_category_mapping
            WHERE kitchen_section_id = %s
        """, (kitchen_id,))
        
        assigned_categories = [row['category_id'] for row in cursor.fetchall()]
        
        if not assigned_categories:
            cursor.close()
            connection.close()
            return jsonify({
                "success": True,
                "orders_by_category": {},
                "stats": {"active": 0, "preparing": 0, "ready": 0}
            })
        
        # Get category names
        placeholders = ','.join(['%s'] * len(assigned_categories))
        cursor.execute(f"""
            SELECT id, name FROM menu_categories
            WHERE id IN ({placeholders})
        """, assigned_categories)
        
        categories = {cat['id']: cat['name'] for cat in cursor.fetchall()}
        
        # Get order items for this kitchen ONLY (not COMPLETED)
        cursor.execute("""
            SELECT 
                oi.id as item_id,
                oi.order_id,
                oi.dish_name as item_name,
                oi.quantity,
                oi.item_status,
                oi.category_id,
                oi.created_at,
                o.table_id,
                o.guest_name,
                t.table_number
            FROM order_items oi
            JOIN table_orders o ON oi.order_id = o.id
            JOIN tables t ON o.table_id = t.id
            WHERE oi.kitchen_section_id = %s
              AND oi.item_status != 'COMPLETED'
            ORDER BY oi.created_at ASC
        """, (kitchen_id,))
        
        items = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        # Process items and group by category
        orders_by_category = {}
        stats = {'active': 0, 'preparing': 0, 'ready': 0}
        
        for item in items:
            category_id = item['category_id']
            category_name = categories.get(category_id, 'Uncategorized')
            
            # Count stats
            if item['item_status'] == 'ACTIVE':
                stats['active'] += 1
            elif item['item_status'] == 'PREPARING':
                stats['preparing'] += 1
            elif item['item_status'] == 'READY':
                stats['ready'] += 1
            
            # Initialize category if not exists
            if category_name not in orders_by_category:
                orders_by_category[category_name] = []
            
            # Add item to category
            orders_by_category[category_name].append({
                'item_id': item['item_id'],
                'order_id': item['order_id'],
                'table_id': item['table_id'],
                'table_number': item['table_number'],
                'guest_name': item.get('guest_name'),
                'item_name': item['item_name'],
                'quantity': item['quantity'],
                'order_status': item['item_status'],
                'created_at': item['created_at'].strftime('%Y-%m-%d %H:%M:%S') if item['created_at'] else None
            })
        
        return jsonify({
            "success": True,
            "orders_by_category": orders_by_category,
            "stats": stats
        })
        
    except Exception as e:
        print(f"[KITCHEN_ORDERS ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error"})

@kitchen_bp.route('/api/update-item-status', methods=['POST'])
def update_item_status():
    """Update order item status (authenticated kitchen only)"""
    kitchen_id = session.get('kitchen_id')
    
    if not kitchen_id:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401
    
    try:
        data = request.get_json()
        item_id = data.get('item_id')
        status = data.get('status')
        
        if not item_id or not status:
            return jsonify({"success": False, "message": "Item ID and status required"})
        
        if status not in ['ACTIVE', 'PREPARING', 'READY', 'COMPLETED']:
            return jsonify({"success": False, "message": "Invalid status"})
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Verify item belongs to this kitchen
        cursor.execute("""
            SELECT kitchen_section_id FROM order_items WHERE id = %s
        """, (item_id,))
        
        result = cursor.fetchone()
        if not result or result[0] != kitchen_id:
            cursor.close()
            connection.close()
            return jsonify({"success": False, "message": "Unauthorized"}), 403
        
        # Update item status
        cursor.execute("""
            UPDATE order_items
            SET item_status = %s
            WHERE id = %s
        """, (status, item_id))
        
        connection.commit()
        
        # Check if all items in the order are COMPLETED
        cursor.execute("""
            SELECT order_id FROM order_items WHERE id = %s
        """, (item_id,))
        
        result = cursor.fetchone()
        if result:
            order_id = result[0]
            
            # Check if all items are COMPLETED
            cursor.execute("""
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN item_status = 'COMPLETED' THEN 1 ELSE 0 END) as completed
                FROM order_items
                WHERE order_id = %s
            """, (order_id,))
            
            counts = cursor.fetchone()
            if counts and counts[0] == counts[1]:
                # All items completed, mark order as COMPLETED
                cursor.execute("""
                    UPDATE table_orders
                    SET order_status = 'COMPLETED'
                    WHERE id = %s
                """, (order_id,))
                connection.commit()
        
        cursor.close()
        connection.close()
        
        print(f"[KITCHEN_STATUS] Item {item_id} → {status} by kitchen {kitchen_id}")
        return jsonify({"success": True, "message": "Item status updated"})
        
    except Exception as e:
        print(f"[KITCHEN_STATUS ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error"})
