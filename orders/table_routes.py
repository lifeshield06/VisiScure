import os
from flask import request, jsonify, render_template, send_file, session
from . import orders_bp
from .table_services import TableService, OrderService
from .table_models import Table, TableOrder, Bill, ActiveTable, BillRequest
from database.db import get_db_connection

# Initialize tables
Table.create_tables()

def log_order_activity(activity_type, message, hotel_id=None):
    """Log order-related activity with role='manager'"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO recent_activities (activity_type, message, hotel_id, role) VALUES (%s, %s, %s, %s)",
            (activity_type, message, hotel_id, 'manager')
        )
        conn.commit()
        print(f"[ORDER ACTIVITY LOGGED] type={activity_type}, hotel_id={hotel_id}, role=manager")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[ORDER ACTIVITY ERROR] {e}")

def check_food_module():
    """Check if food module is enabled for this manager's hotel"""
    if not session.get('manager_id'):
        return False
    return session.get('food_enabled', False)

@orders_bp.route('/api/tables', methods=['GET'])
def get_tables():
    """Get all tables for current hotel"""
    try:
        hotel_id = session.get('hotel_id')
        tables = Table.get_all_tables(hotel_id)
        return jsonify({"success": True, "tables": tables})
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/tables', methods=['POST'])
def add_table():
    """Add new table"""
    if not check_food_module():
        return jsonify({"success": False, "message": "Food ordering module not enabled for this hotel"}), 403
    try:
        data = request.get_json()
        table_number = data.get('table_number', '').strip()
        hotel_id = session.get('hotel_id')
        
        if not table_number:
            return jsonify({"success": False, "message": "Table number is required"})
        
        result = TableService.add_new_table(table_number, hotel_id)
        
        # Log activity on success
        if result.get('success'):
            log_order_activity('table', f"Table '{table_number}' was created", hotel_id)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/download-qr/<int:table_id>')
def download_qr(table_id):
    """Download QR code"""
    try:
        table = Table.get_table_by_id(table_id)
        if not table or not table['qr_code_path']:
            return jsonify({"success": False, "message": "QR code not found"})
        
        qr_path = table['qr_code_path']
        if os.path.exists(qr_path):
            return send_file(qr_path, as_attachment=True, 
                           download_name=f"Table_{table['table_number']}_QR.png")
        else:
            return jsonify({"success": False, "message": "QR file not found"})
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/regenerate-qr/<int:table_id>', methods=['POST'])
def regenerate_qr(table_id):
    """Regenerate QR code for table"""
    try:
        table = Table.get_table_by_id(table_id)
        if not table:
            return jsonify({"success": False, "message": "Table not found"})
        
        # Remove old QR code file if it exists
        if table['qr_code_path'] and os.path.exists(table['qr_code_path']):
            os.remove(table['qr_code_path'])
        
        # Generate new QR code
        new_qr_path = TableService.create_qr_code(table_id, table['table_number'])
        if not new_qr_path:
            return jsonify({"success": False, "message": "Failed to generate QR code"})
        
        # Update table with new QR path
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("UPDATE tables SET qr_code_path = %s WHERE id = %s", (new_qr_path, table_id))
        connection.commit()
        cursor.close()
        connection.close()
        
        # Log activity
        hotel_id = session.get('hotel_id')
        log_order_activity('table', f"QR code regenerated for Table '{table['table_number']}'", hotel_id)
        
        return jsonify({"success": True, "message": "QR code regenerated successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/menu/<int:table_id>')
def table_menu(table_id):
    """Show menu for table (QR destination)"""
    table = Table.get_table_by_id(table_id)
    if not table:
        return "Table not found", 404
    
    # Check for any open bill with a guest_name to determine initial busy state
    # Bills with NULL/empty guest_name are treated as available (orphaned bills)
    # Note: The actual access logic is handled by check-guest-access API after guest enters name
    open_bill = Bill.get_any_open_bill_for_table(table_id)
    
    # Only show busy if there's an open bill WITH a guest name assigned
    table_busy = False
    if open_bill and open_bill.get('guest_name') and open_bill.get('guest_name').strip():
        table_busy = True
    
    # Fetch hotel logo, name, and UPI payment info
    hotel_id = table.get('hotel_id')
    hotel_name = None
    hotel_logo = None
    upi_id = None
    upi_qr_image = None
    
    if hotel_id:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT hotel_name, logo, upi_id, upi_qr_image FROM hotels WHERE id = %s", (hotel_id,))
            result = cursor.fetchone()
            if result:
                hotel_name = result[0]
                hotel_logo = result[1]
                upi_id = result[2]
                upi_qr_image = result[3]
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error fetching hotel data: {e}")

    return render_template('table_menu.html', 
                         table=table, 
                         table_busy=table_busy,
                         hotel_name=hotel_name,
                         hotel_logo=hotel_logo,
                         upi_id=upi_id,
                         upi_qr_image=upi_qr_image)

@orders_bp.route('/api/check-guest-access', methods=['POST'])
def check_guest_access():
    """Check if a guest can access a table based on existing OPEN bills"""
    try:
        data = request.get_json()
        table_id = data.get('table_id')
        guest_name = data.get('guest_name')
        
        if not table_id:
            return jsonify({"success": False, "message": "Table ID required", "can_order": False})
        
        if not guest_name or not guest_name.strip():
            return jsonify({"success": False, "message": "Guest name is required", "can_order": False})
        
        result = OrderService.check_guest_access(table_id, guest_name)
        return jsonify(result)
    except Exception as e:
        print(f"Error in check_guest_access: {e}")
        return jsonify({"success": False, "message": "Server error", "can_order": False})

@orders_bp.route('/api/create-order', methods=['POST'])
def create_order():
    """Create new ACTIVE order with guest name"""
    try:
        data = request.get_json()
        table_id = data.get('table_id')
        items = data.get('items', [])
        session_id = data.get('session_id')
        guest_name = data.get('guest_name')
        
        if not table_id or not items:
            return jsonify({"success": False, "message": "Table ID and items required"})
        
        if not guest_name or not guest_name.strip():
            return jsonify({"success": False, "message": "Guest name is required"})
        
        result = OrderService.create_order(table_id, items, session_id, guest_name)
        
        # Log activity on success
        if result.get('success'):
            table = Table.get_table_by_id(table_id)
            table_num = table['table_number'] if table else table_id
            hotel_id = table.get('hotel_id') if table else None
            total = sum(item.get('price', 0) * item.get('quantity', 1) for item in items)
            log_order_activity('order', f"New order from Table {table_num} - ₹{total:.0f}", hotel_id)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/orders', methods=['GET'])
def get_orders():
    """Get all orders for current hotel"""
    try:
        hotel_id = session.get('hotel_id')
        orders = TableOrder.get_all_orders(hotel_id)
        return jsonify({"success": True, "orders": orders})
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/session-orders/<int:table_id>/<session_id>', methods=['GET'])
def get_session_orders(table_id, session_id):
    """Get orders for current session"""
    try:
        result = OrderService.get_session_orders(table_id, session_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/complete-payment', methods=['POST'])
def complete_payment():
    """Complete payment and free QR for next customer"""
    try:
        data = request.get_json()
        table_id = data.get('table_id')
        session_id = data.get('session_id')
        
        if not table_id or not session_id:
            return jsonify({"success": False, "message": "Table ID and session ID required"})
        
        result = OrderService.complete_payment(table_id, session_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/complete-order', methods=['POST'])
def complete_order():
    """Complete order and set table AVAILABLE"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        
        if not order_id:
            return jsonify({"success": False, "message": "Order ID required"})
        
        result = OrderService.complete_order(order_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/update-order-status', methods=['POST'])
def update_order_status():
    """Update order status (ACTIVE/PREPARING/COMPLETED) - DEPRECATED, use update-item-status for kitchen"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        status = data.get('status')

        if not order_id or not status:
            return jsonify({"success": False, "message": "Order ID and status required"})

        result = OrderService.update_order_status(order_id, status)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})


@orders_bp.route('/api/update-item-status', methods=['POST'])
def update_item_status():
    """Update individual order item status (for kitchen dashboard)"""
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
                
                # Deduct wallet charge when order is COMPLETED
                cursor.execute("""
                    SELECT o.hotel_id, o.charge_deducted, t.hotel_id as table_hotel_id
                    FROM table_orders o
                    LEFT JOIN tables t ON o.table_id = t.id
                    WHERE o.id = %s
                """, (order_id,))
                order_data = cursor.fetchone()
                
                if order_data:
                    hotel_id = order_data[0] or order_data[2]  # order.hotel_id or table.hotel_id
                    charge_deducted = order_data[1]
                    
                    if hotel_id and not charge_deducted:
                        from wallet.models import HotelWallet
                        
                        # Check balance first
                        balance_check = HotelWallet.check_balance_for_order(hotel_id)
                        if balance_check.get('sufficient', True):
                            deduct_result = HotelWallet.deduct_for_order(hotel_id, order_id)
                            if deduct_result.get('success'):
                                cursor.execute("""
                                    UPDATE table_orders SET charge_deducted = TRUE WHERE id = %s
                                """, (order_id,))
                                connection.commit()
                                print(f"[ITEM_STATUS] Wallet deducted for order {order_id}: ₹{deduct_result.get('deducted', 0)}")
                            else:
                                print(f"[ITEM_STATUS] Wallet deduction failed: {deduct_result.get('message')}")
                        else:
                            print(f"[ITEM_STATUS] Insufficient balance for order {order_id}")
        
        cursor.close()
        connection.close()
        
        print(f"[ITEM_STATUS] Item {item_id} → {status}")
        return jsonify({"success": True, "message": "Item status updated"})
        
    except Exception as e:
        print(f"[ITEM_STATUS ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/tables/<table_number>', methods=['DELETE'])
def delete_table(table_number):
    """Delete table by table number"""
    try:
        hotel_id = session.get('hotel_id')
        if not hotel_id:
            return jsonify({"success": False, "message": "Hotel not found"})
            
        result = TableService.delete_table(table_number, hotel_id)
        
        if result.get('success'):
            log_order_activity('table', f"Table '{table_number}' was deleted", hotel_id)
        
        return jsonify(result)
    except Exception as e:
        print(f"Error in delete_table route: {e}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"})

# ============== Bill & Payment Routes ==============

@orders_bp.route('/api/bill/<int:order_id>', methods=['GET'])
def get_bill_by_order(order_id):
    """Get bill for a specific order"""
    try:
        bill = Bill.get_bill_by_order(order_id)
        if bill:
            return jsonify({"success": True, "bill": bill})
        return jsonify({"success": False, "message": "Bill not found"})
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/session-bill/<int:table_id>/<session_id>', methods=['GET'])
def get_session_bill(table_id, session_id):
    """Get combined bill for entire session"""
    try:
        bill = Bill.get_session_total(table_id, session_id)
        if bill:
            return jsonify({"success": True, "bill": bill})
        return jsonify({"success": False, "message": "No orders found for this session"})
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/guest-bill/<int:table_id>/<guest_name>', methods=['GET'])
def get_guest_bill(table_id, guest_name):
    """Get open bill for a specific guest at a table"""
    try:
        bill = Bill.get_open_bill_by_table_and_guest(table_id, guest_name)
        if bill:
            return jsonify({"success": True, "bill": bill})
        return jsonify({"success": False, "message": "No open bill found for this guest"})
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/complete-bill', methods=['POST'])
def complete_bill():
    """Complete a bill - lock it and free table"""
    try:
        data = request.get_json()
        bill_id = data.get('bill_id')
        
        if not bill_id:
            return jsonify({"success": False, "message": "Bill ID required"})
        
        # Get bill info before completing
        bill_info = Bill.get_bill_details(bill_id) if hasattr(Bill, 'get_bill_details') else None
        
        result = OrderService.complete_bill(bill_id)
        
        # Log activity on success
        if result.get('success') and bill_info:
            table_id = bill_info.get('table_id')
            table = Table.get_table_by_id(table_id) if table_id else None
            table_num = table['table_number'] if table else 'Unknown'
            hotel_id = table.get('hotel_id') if table else None
            total = bill_info.get('total_amount', 0)
            log_order_activity('payment', f"Payment received - Table {table_num} paid ₹{total:.0f}", hotel_id)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/process-payment', methods=['POST'])
def process_payment():
    """Process payment - ALWAYS succeeds if OPEN bill exists"""
    try:
        data = request.get_json()
        table_id = data.get('table_id')
        guest_name = data.get('guest_name')
        payment_method = data.get('payment_method', 'CASH')
        tip_amount = float(data.get('tip_amount', 0.00))  # Get tip amount from request
        
        print(f"[PAYMENT] Processing payment for table_id={table_id}, tip_amount={tip_amount}, method={payment_method}")
        
        if not table_id:
            return jsonify({"success": False, "message": "Table ID is required"})
        
        # Validate tip amount
        if tip_amount < 0:
            return jsonify({"success": False, "message": "Tip amount cannot be negative"})
        
        # Find OPEN bill for this table
        open_bill = Bill.get_any_open_bill_for_table(table_id)
        
        if not open_bill:
            print(f"[PAYMENT ERROR] No open bill found for table_id={table_id}")
            return jsonify({"success": False, "message": "No open bill found. Please place an order first."})
        
        print(f"[PAYMENT] Found open bill: bill_id={open_bill['id']}, bill_number={open_bill.get('bill_number')}")
        
        # Get table info for logging
        table = Table.get_table_by_id(table_id)
        table_num = table['table_number'] if table else table_id
        hotel_id = table.get('hotel_id') if table else None
        bill_total = open_bill.get('total_amount', 0)
        
        # Process payment in atomic transaction with tip
        payment_success = Bill.process_payment_atomic(table_id, open_bill['id'], payment_method, tip_amount)
        
        if payment_success:
            # Calculate final total with tip for logging
            final_total = float(bill_total) + tip_amount
            tip_text = f" (incl. ₹{tip_amount:.0f} tip)" if tip_amount > 0 else ""
            
            # Log activity
            log_order_activity('payment', f"Payment received - Table {table_num} paid ₹{final_total:.0f}{tip_text}", hotel_id)
            print(f"[PAYMENT SUCCESS] Payment completed for table_id={table_id}, total=₹{final_total:.2f}")
            return jsonify({
                "success": True, 
                "message": "Payment successful! Thank you for dining with us."
            })
        
        print(f"[PAYMENT ERROR] process_payment_atomic returned False for table_id={table_id}")
        return jsonify({"success": False, "message": "Failed to process payment"})
    except Exception as e:
        import traceback
        print(f"[PAYMENT ERROR] Exception in process_payment route: {e}")
        print(f"[PAYMENT ERROR] Traceback: {traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/orders-with-bills', methods=['GET'])
def get_orders_with_bills():
    """Get all orders with their bill information for the current hotel"""
    try:
        hotel_id = session.get('hotel_id')
        orders = TableOrder.get_all_orders(hotel_id)
        
        # Add bill info to each order
        for order in orders:
            bill = Bill.get_bill_by_order(order['id'])
            order['bill'] = bill
        
        return jsonify({"success": True, "orders": orders})
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/active-bills', methods=['GET'])
def get_active_bills():
    """Get all OPEN bills for the current hotel - one per table"""
    try:
        hotel_id = session.get('hotel_id')
        bills = Bill.get_all_active_bills(hotel_id)
        return jsonify({"success": True, "bills": bills})
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/all-bills', methods=['GET'])
def get_all_bills():
    """Get all bills for the current hotel with optional status filter"""
    try:
        hotel_id = session.get('hotel_id')
        status = request.args.get('status')  # Optional: 'OPEN' or 'COMPLETED'
        bills = Bill.get_all_bills(hotel_id, status)
        return jsonify({"success": True, "bills": bills})
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/table-bill/<int:table_id>', methods=['GET'])
def get_table_bill(table_id):
    """Get the current OPEN bill for a specific table"""
    try:
        bill = Bill.get_any_open_bill_for_table(table_id)
        if bill:
            return jsonify({"success": True, "bill": bill, "has_open_bill": True})
        return jsonify({"success": True, "bill": None, "has_open_bill": False, "message": "No open bill for this table"})
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/mark-bill-paid', methods=['POST'])
def mark_bill_paid():
    """Mark a bill as PAID and complete it, releasing the table"""
    try:
        data = request.get_json()
        bill_id = data.get('bill_id')
        table_id = data.get('table_id')
        
        print(f"[MARK_BILL_PAID] Request received - bill_id={bill_id}, table_id={table_id}")
        
        if not bill_id:
            print("[MARK_BILL_PAID] Error: Bill ID required")
            return jsonify({"success": False, "message": "Bill ID required"})
        
        # Complete the bill (mark as PAID and COMPLETED, and release table)
        # The complete_bill method handles everything: bill status, payment status, table status, and active_tables
        result = Bill.complete_bill(bill_id)
        
        if not result:
            print(f"[MARK_BILL_PAID] Error: complete_bill returned False for bill_id={bill_id}")
            return jsonify({"success": False, "message": "Failed to complete bill"})
        
        print(f"[MARK_BILL_PAID] Success: Bill {bill_id} marked as paid")
        return jsonify({"success": True, "message": "Bill marked as paid and table released"})
    except Exception as e:
        print(f"[MARK_BILL_PAID] Exception: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/bill-details/<int:bill_id>', methods=['GET'])
def get_bill_details(bill_id):
    """Get detailed bill information including items"""
    try:
        bill = Bill.get_bill_by_id(bill_id)
        if bill:
            return jsonify({"success": True, "bill": bill})
        return jsonify({"success": False, "message": "Bill not found"})
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})

# ============== Active Tables Routes ==============

@orders_bp.route('/api/active-tables', methods=['GET'])
def get_active_tables():
    """Get all active tables (linked to open bills) for the hotel"""
    try:
        hotel_id = session.get('hotel_id')
        active_tables = ActiveTable.get_all_active_tables(hotel_id)
        return jsonify({"success": True, "active_tables": active_tables})
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/active-tables/<int:table_id>', methods=['GET'])
def get_active_table(table_id):
    """Get active entry for a specific table"""
    try:
        entry = ActiveTable.get_active_entry(table_id)
        if entry:
            return jsonify({"success": True, "active_table": entry, "is_active": True})
        return jsonify({"success": True, "active_table": None, "is_active": False})
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/active-tables/sync', methods=['POST'])
def sync_active_tables():
    """Sync active tables with bill status - cleanup stale entries"""
    try:
        ActiveTable.sync_with_bills()
        return jsonify({"success": True, "message": "Active tables synced with bills"})
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})

# ============== Tip Statistics Routes ==============

@orders_bp.route('/api/tip-statistics/hotel', methods=['GET'])
def get_hotel_tip_statistics():
    """Get tip statistics for hotel (Manager Dashboard)"""
    try:
        hotel_id = session.get('hotel_id')
        period = request.args.get('period', 'today')  # today, week, month, all
        
        if not hotel_id:
            return jsonify({"success": False, "message": "Hotel ID required"})
        
        stats = Bill.get_tip_statistics_for_hotel(hotel_id, period)
        return jsonify({"success": True, "statistics": stats})
    except Exception as e:
        print(f"Error getting hotel tip statistics: {e}")
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/tip-statistics/waiter/<int:waiter_id>', methods=['GET'])
def get_waiter_tip_statistics(waiter_id):
    """Get tip statistics for waiter (Waiter Dashboard)"""
    try:
        period = request.args.get('period', 'today')  # today, week, month, all

        # Check per-waiter tips visibility from waiters table
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT COALESCE(show_waiter_tips, 1) as show_waiter_tips
            FROM waiters
            WHERE id = %s
        """, (waiter_id,))
        visibility_result = cursor.fetchone()
        cursor.close()
        connection.close()

        show_tips_raw = visibility_result['show_waiter_tips'] if visibility_result else 1
        show_tips = bool(show_tips_raw) if show_tips_raw is not None else True

        if not show_tips:
            return jsonify({
                "success": True,
                "tips_visible": False,
                "statistics": {"total_tips": 0, "tip_count": 0}
            })

        stats = Bill.get_tip_statistics_for_waiter(waiter_id, period)
        return jsonify({"success": True, "tips_visible": True, "statistics": stats})
    except Exception as e:
        print(f"Error getting waiter tip statistics: {e}")
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/tip-details/waiter/<int:waiter_id>', methods=['GET'])
def get_waiter_tip_details(waiter_id):
    """Get recent tip details for waiter"""
    try:
        limit = int(request.args.get('limit', 10))
        
        tips = Bill.get_waiter_tip_details(waiter_id, limit)
        return jsonify({"success": True, "tips": tips})
    except Exception as e:
        print(f"Error getting waiter tip details: {e}")
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/waiter-wise-tips', methods=['GET'])
def get_waiter_wise_tips():
    """Get waiter-wise tip breakdown for manager dashboard"""
    try:
        hotel_id = session.get('hotel_id')
        period = request.args.get('period', 'all')  # today, week, month, all
        
        print(f"[TIP_API] Request: period={period}, hotel_id={hotel_id}")
        
        if not hotel_id:
            print("[TIP_API] Error: No hotel_id in session")
            return jsonify({"success": False, "message": "Hotel ID required"})
        
        waiters = Bill.get_waiter_wise_tips(hotel_id, period)
        
        print(f"[TIP_API] Result: Found {len(waiters)} waiters with tips")
        for waiter in waiters:
            print(f"[TIP_API] - {waiter['waiter_name']} (ID: {waiter['waiter_id']}): Today ₹{waiter['today_tip']}, Total ₹{waiter['total_tip']}")
        
        return jsonify({"success": True, "waiters": waiters})
    except Exception as e:
        print(f"[TIP_API] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error"})

@orders_bp.route('/api/tip-system-debug', methods=['GET'])
def tip_system_debug():
    """Debug endpoint to check tip system status"""
    try:
        hotel_id = session.get('hotel_id')
        
        if not hotel_id:
            return jsonify({"success": False, "message": "Hotel ID required"})
        
        from database.db import get_db_connection
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        debug_info = {}
        
        # Check waiter_tips table
        cursor.execute("SHOW TABLES LIKE 'waiter_tips'")
        debug_info['waiter_tips_exists'] = cursor.fetchone() is not None
        
        # Check waiters count
        cursor.execute("SELECT COUNT(*) as count FROM waiters WHERE hotel_id = %s", (hotel_id,))
        debug_info['waiters_count'] = cursor.fetchone()['count']
        
        # Check table assignments
        cursor.execute("SELECT COUNT(*) as count FROM waiter_table_assignments wta JOIN tables t ON wta.table_id = t.id WHERE t.hotel_id = %s", (hotel_id,))
        debug_info['assignments_count'] = cursor.fetchone()['count']
        
        # Check bills with tips
        cursor.execute("SELECT COUNT(*) as count FROM bills WHERE hotel_id = %s AND tip_amount > 0", (hotel_id,))
        debug_info['bills_with_tips'] = cursor.fetchone()['count']
        
        # Check waiter_tips records if table exists
        if debug_info['waiter_tips_exists']:
            cursor.execute("SELECT COUNT(*) as count FROM waiter_tips wt JOIN bills b ON wt.bill_id = b.id WHERE b.hotel_id = %s", (hotel_id,))
            debug_info['tip_records'] = cursor.fetchone()['count']
        else:
            debug_info['tip_records'] = 0
        
        cursor.close()
        connection.close()
        
        return jsonify({"success": True, "debug": debug_info})
    except Exception as e:
        print(f"Error in tip system debug: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error"})


@orders_bp.route('/api/clear-completed-orders', methods=['POST'])
def clear_completed_orders():
    """Clear all completed and paid orders safely"""
    try:
        hotel_id = session.get('hotel_id')
        
        if not hotel_id:
            return jsonify({"success": False, "message": "Hotel ID required"})
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Safety check: Only delete orders that are:
        # 1. order_status = 'COMPLETED'
        # 2. payment_status = 'PAID'
        # 3. Related bill (if exists) is also COMPLETED
        
        # First, get count of orders to be deleted
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM table_orders o
            LEFT JOIN bills b ON o.id = b.order_id
            WHERE (o.hotel_id = %s OR (o.hotel_id IS NULL AND EXISTS (
                SELECT 1 FROM tables t WHERE t.id = o.table_id AND t.hotel_id = %s
            )))
            AND o.order_status = 'COMPLETED'
            AND o.payment_status = 'PAID'
            AND (b.id IS NULL OR b.bill_status = 'COMPLETED')
        """, (hotel_id, hotel_id))
        
        count_result = cursor.fetchone()
        orders_to_delete = count_result['count'] if count_result else 0
        
        if orders_to_delete == 0:
            cursor.close()
            connection.close()
            return jsonify({
                "success": True, 
                "message": "No completed orders to clear",
                "deleted_count": 0
            })
        
        # Delete the orders
        cursor.execute("""
            DELETE o FROM table_orders o
            LEFT JOIN bills b ON o.id = b.order_id
            WHERE (o.hotel_id = %s OR (o.hotel_id IS NULL AND EXISTS (
                SELECT 1 FROM tables t WHERE t.id = o.table_id AND t.hotel_id = %s
            )))
            AND o.order_status = 'COMPLETED'
            AND o.payment_status = 'PAID'
            AND (b.id IS NULL OR b.bill_status = 'COMPLETED')
        """, (hotel_id, hotel_id))
        
        deleted_count = cursor.rowcount
        
        connection.commit()
        cursor.close()
        connection.close()
        
        # Log activity
        log_order_activity('order', f"Cleared {deleted_count} completed orders", hotel_id)
        
        print(f"[CLEAR_ORDERS] Deleted {deleted_count} completed orders for hotel {hotel_id}")
        
        return jsonify({
            "success": True,
            "message": f"Successfully cleared {deleted_count} completed order(s)",
            "deleted_count": deleted_count
        })
        
    except Exception as e:
        print(f"[CLEAR_ORDERS ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error"})


@orders_bp.route('/api/mark-payment-done', methods=['POST'])
def mark_payment_done():
    """Mark an order as paid (cash payment) and complete the bill"""
    try:
        data = request.get_json()
        order_id = data.get('order_id')
        table_id = data.get('table_id')
        
        if not order_id:
            return jsonify({"success": False, "message": "Order ID required"})
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Get order details including hotel_id and charge_deducted status
        cursor.execute("""
            SELECT o.id, o.order_status, o.payment_status, o.table_id, o.hotel_id, o.charge_deducted,
                   t.hotel_id as table_hotel_id
            FROM table_orders o
            LEFT JOIN tables t ON o.table_id = t.id
            WHERE o.id = %s
        """, (order_id,))
        
        order = cursor.fetchone()
        
        if not order:
            cursor.close()
            connection.close()
            return jsonify({"success": False, "message": "Order not found"})
        
        # Verify order is COMPLETED and payment is PENDING
        if order['order_status'] != 'COMPLETED':
            cursor.close()
            connection.close()
            return jsonify({"success": False, "message": "Order must be COMPLETED first"})
        
        if order['payment_status'] != 'PENDING':
            cursor.close()
            connection.close()
            return jsonify({"success": False, "message": "Payment already processed"})
        
        # Get hotel_id (prefer order.hotel_id, fallback to table.hotel_id)
        hotel_id = order.get('hotel_id') or order.get('table_hotel_id')
        
        if not hotel_id:
            cursor.close()
            connection.close()
            return jsonify({"success": False, "message": "Hotel ID not found"})
        
        # Wallet deduction happens when order is COMPLETED, not when payment is marked
        # No wallet deduction here - settlement happens on order completion
        print(f"[MARK_PAYMENT_DONE] Marking payment for order {order_id} (wallet settlement already done on completion)")
        
        # Update order payment status — freeze final_total at current value + digital fee
        # Fetch digital fee to include in frozen total
        digital_fee_for_freeze = 0.0
        try:
            cursor.execute(
                "SELECT per_order_charge, COALESCE(digital_fee_enabled, 1) as digital_fee_enabled FROM hotel_wallet WHERE hotel_id = %s",
                (hotel_id,)
            )
            fee_row = cursor.fetchone()
            if fee_row and bool(fee_row['digital_fee_enabled']):
                digital_fee_for_freeze = float(fee_row['per_order_charge'] or 0)
        except Exception:
            digital_fee_for_freeze = 0.0

        cursor.execute("""
            UPDATE table_orders
            SET payment_status = 'PAID',
                final_total = ROUND(total_amount + %s, 2)
            WHERE id = %s
        """, (digital_fee_for_freeze, order_id))
        
        print(f"[MARK_PAYMENT_DONE] Updated order {order_id} payment_status to PAID")
        
        # Find related bill
        cursor.execute("""
            SELECT id FROM bills
            WHERE order_id = %s AND bill_status = 'OPEN'
        """, (order_id,))
        
        bill = cursor.fetchone()
        
        if bill:
            bill_id = bill['id']
            
            # Update bill with cash payment
            import datetime
            paid_at = datetime.datetime.now()
            
            cursor.execute("""
                UPDATE bills
                SET bill_status = 'COMPLETED',
                    payment_status = 'PAID',
                    payment_method = 'CASH',
                    paid_at = %s
                WHERE id = %s
            """, (paid_at, bill_id))
            
            print(f"[MARK_PAYMENT_DONE] Updated bill {bill_id} to COMPLETED/PAID with CASH payment")
            
            connection.commit()
            cursor.close()
            connection.close()
            
            # Complete the bill (free table, clear session)
            Bill.complete_bill(bill_id)
            
            # Log activity
            log_order_activity('order', f"Marked order {order_id} as paid (CASH)", hotel_id)
            
            return jsonify({
                "success": True,
                "message": "Payment marked as done. Bill completed and table freed."
            })
        else:
            # No bill found, just update order
            connection.commit()
            cursor.close()
            connection.close()
            
            log_order_activity('order', f"Marked order {order_id} as paid (CASH) - no bill", hotel_id)
            
            return jsonify({
                "success": True,
                "message": "Payment marked as done."
            })
        
    except Exception as e:
        print(f"[MARK_PAYMENT_DONE ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error"})


@orders_bp.route('/api/kitchen-orders', methods=['GET'])
def get_kitchen_orders():
    """Get orders grouped by category for kitchen dashboard"""
    try:
        hotel_id = session.get('hotel_id')
        status_filter = request.args.get('status', 'all')
        
        if not hotel_id:
            return jsonify({"success": False, "message": "Hotel ID required"})
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Build status filter
        status_condition = ""
        if status_filter != 'all':
            status_condition = f"AND o.order_status = '{status_filter}'"
        
        # Get orders with category information, excluding COMPLETED orders
        cursor.execute(f"""
            SELECT 
                o.id as order_id,
                o.table_id,
                o.order_status,
                o.created_at,
                o.guest_name,
                t.table_number,
                JSON_EXTRACT(o.items, '$[*].name') as item_names,
                JSON_EXTRACT(o.items, '$[*].quantity') as item_quantities,
                JSON_EXTRACT(o.items, '$[*].category_id') as category_ids,
                o.items
            FROM table_orders o
            JOIN tables t ON o.table_id = t.id
            WHERE (o.hotel_id = %s OR t.hotel_id = %s)
            AND o.order_status != 'COMPLETED'
            {status_condition}
            ORDER BY o.created_at ASC
        """, (hotel_id, hotel_id))
        
        orders = cursor.fetchall()
        
        # Get all categories for this hotel
        cursor.execute("""
            SELECT id, name FROM menu_categories
            WHERE hotel_id = %s
            ORDER BY name
        """, (hotel_id,))
        
        categories = {cat['id']: cat['name'] for cat in cursor.fetchall()}
        
        # Get dish details for category mapping
        cursor.execute("""
            SELECT id, name, category_id FROM menu_dishes
            WHERE hotel_id = %s
        """, (hotel_id,))
        
        dishes = {dish['id']: {'name': dish['name'], 'category_id': dish['category_id']} for dish in cursor.fetchall()}
        
        cursor.close()
        connection.close()
        
        # Process orders and group by category
        orders_by_category = {}
        stats = {'active': 0, 'preparing': 0, 'ready': 0}
        
        for order in orders:
            # Parse items JSON
            import json
            items = json.loads(order['items']) if isinstance(order['items'], str) else order['items']
            
            # Count stats
            if order['order_status'] == 'ACTIVE':
                stats['active'] += 1
            elif order['order_status'] == 'PREPARING':
                stats['preparing'] += 1
            elif order['order_status'] == 'READY':
                stats['ready'] += 1
            
            # Process each item in the order
            for item in items:
                dish_id = item.get('id')
                item_name = item.get('name', 'Unknown Item')
                quantity = item.get('quantity', 1)
                
                # Get category from dish
                category_id = None
                category_name = 'Uncategorized'
                
                if dish_id and dish_id in dishes:
                    category_id = dishes[dish_id]['category_id']
                    if category_id and category_id in categories:
                        category_name = categories[category_id]
                
                # Initialize category if not exists
                if category_name not in orders_by_category:
                    orders_by_category[category_name] = []
                
                # Add item to category
                orders_by_category[category_name].append({
                    'order_id': order['order_id'],
                    'table_id': order['table_id'],
                    'table_number': order['table_number'],
                    'guest_name': order.get('guest_name'),
                    'item_name': item_name,
                    'quantity': quantity,
                    'order_status': order['order_status'],
                    'created_at': order['created_at'].strftime('%Y-%m-%d %H:%M:%S') if order['created_at'] else None
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


# ============== Kitchen Section Management Routes ==============

@orders_bp.route('/api/kitchen-sections', methods=['GET'])
def get_kitchen_sections():
    """Get all kitchen sections with their assigned categories"""
    try:
        hotel_id = session.get('hotel_id')
        
        if not hotel_id:
            return jsonify({"success": False, "message": "Hotel ID required"})
        
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Get all kitchen sections for this hotel
        cursor.execute("""
            SELECT id, section_name, created_at
            FROM kitchen_sections
            WHERE hotel_id = %s
            ORDER BY section_name
        """, (hotel_id,))
        
        sections = cursor.fetchall()
        
        # Get all categories for this hotel
        cursor.execute("""
            SELECT id, name
            FROM menu_categories
            WHERE hotel_id = %s
            ORDER BY name
        """, (hotel_id,))
        
        all_categories = cursor.fetchall()
        
        # For each section, get assigned categories
        for section in sections:
            cursor.execute("""
                SELECT c.id, c.name
                FROM menu_categories c
                JOIN kitchen_category_mapping kcm ON c.id = kcm.category_id
                WHERE kcm.kitchen_section_id = %s
                ORDER BY c.name
            """, (section['id'],))
            
            section['categories'] = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({
            "success": True,
            "sections": sections,
            "categories": all_categories
        })
        
    except Exception as e:
        print(f"[KITCHEN_SECTIONS ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error"})


@orders_bp.route('/api/kitchen-sections', methods=['POST'])
def create_kitchen_section():
    """Create a new kitchen section"""
    try:
        hotel_id = session.get('hotel_id')
        data = request.get_json()
        section_name = data.get('section_name', '').strip()
        
        if not hotel_id:
            return jsonify({"success": False, "message": "Hotel ID required"})
        
        if not section_name:
            return jsonify({"success": False, "message": "Section name required"})
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            INSERT INTO kitchen_sections (hotel_id, section_name)
            VALUES (%s, %s)
        """, (hotel_id, section_name))
        
        section_id = cursor.lastrowid
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print(f"[KITCHEN_SECTION] Created section '{section_name}' for hotel {hotel_id}")
        
        return jsonify({
            "success": True,
            "message": "Kitchen section created successfully",
            "section_id": section_id
        })
        
    except Exception as e:
        print(f"[KITCHEN_SECTION ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error"})


@orders_bp.route('/api/kitchen-sections/<int:section_id>', methods=['PUT'])
def update_kitchen_section(section_id):
    """Update kitchen section name"""
    try:
        hotel_id = session.get('hotel_id')
        data = request.get_json()
        section_name = data.get('section_name', '').strip()
        
        if not hotel_id:
            return jsonify({"success": False, "message": "Hotel ID required"})
        
        if not section_name:
            return jsonify({"success": False, "message": "Section name required"})
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            UPDATE kitchen_sections
            SET section_name = %s
            WHERE id = %s AND hotel_id = %s
        """, (section_name, section_id, hotel_id))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print(f"[KITCHEN_SECTION] Updated section {section_id} to '{section_name}'")
        
        return jsonify({
            "success": True,
            "message": "Kitchen section updated successfully"
        })
        
    except Exception as e:
        print(f"[KITCHEN_SECTION ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error"})


@orders_bp.route('/api/kitchen-sections/<int:section_id>', methods=['DELETE'])
def delete_kitchen_section(section_id):
    """Delete kitchen section and all its mappings"""
    try:
        hotel_id = session.get('hotel_id')
        
        if not hotel_id:
            return jsonify({"success": False, "message": "Hotel ID required"})
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Delete section (mappings will be deleted automatically due to CASCADE)
        cursor.execute("""
            DELETE FROM kitchen_sections
            WHERE id = %s AND hotel_id = %s
        """, (section_id, hotel_id))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print(f"[KITCHEN_SECTION] Deleted section {section_id}")
        
        return jsonify({
            "success": True,
            "message": "Kitchen section deleted successfully"
        })
        
    except Exception as e:
        print(f"[KITCHEN_SECTION ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error"})


@orders_bp.route('/api/kitchen-category-mapping', methods=['POST'])
def assign_category_to_kitchen():
    """Assign a category to a kitchen section"""
    try:
        data = request.get_json()
        kitchen_section_id = data.get('kitchen_section_id')
        category_id = data.get('category_id')
        
        if not kitchen_section_id or not category_id:
            return jsonify({"success": False, "message": "Kitchen section ID and category ID required"})
        
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            INSERT INTO kitchen_category_mapping (kitchen_section_id, category_id)
            VALUES (%s, %s)
        """, (kitchen_section_id, category_id))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print(f"[KITCHEN_MAPPING] Assigned category {category_id} to section {kitchen_section_id}")
        
        return jsonify({
            "success": True,
            "message": "Category assigned successfully"
        })
        
    except Exception as e:
        print(f"[KITCHEN_MAPPING ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error"})


@orders_bp.route('/api/kitchen-category-mapping/<int:section_id>/<int:category_id>', methods=['DELETE'])
def unassign_category_from_kitchen(section_id, category_id):
    """Remove a category from a kitchen section"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("""
            DELETE FROM kitchen_category_mapping
            WHERE kitchen_section_id = %s AND category_id = %s
        """, (section_id, category_id))
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print(f"[KITCHEN_MAPPING] Unassigned category {category_id} from section {section_id}")
        
        return jsonify({
            "success": True,
            "message": "Category unassigned successfully"
        })
        
    except Exception as e:
        print(f"[KITCHEN_MAPPING ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error"})


@orders_bp.route('/api/kitchen-section-orders/<int:section_id>', methods=['GET'])
def get_kitchen_section_orders(section_id):
    """Get orders for a specific kitchen section (filtered by assigned categories) - ITEM LEVEL"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Get assigned categories for this kitchen section
        cursor.execute("""
            SELECT category_id
            FROM kitchen_category_mapping
            WHERE kitchen_section_id = %s
        """, (section_id,))
        
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
        
        # Get order items for this kitchen section ONLY (not COMPLETED)
        # CRITICAL: Filter by kitchen_section_id to show ONLY items assigned to THIS kitchen
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
        """, (section_id,))
        
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
                'order_status': item['item_status'],  # Use item_status instead of order_status
                'created_at': item['created_at'].strftime('%Y-%m-%d %H:%M:%S') if item['created_at'] else None
            })
        
        return jsonify({
            "success": True,
            "orders_by_category": orders_by_category,
            "stats": stats
        })
        
    except Exception as e:
        print(f"[KITCHEN_SECTION_ORDERS ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error"})


# Kitchen Dashboard Page Route
from flask import render_template

@orders_bp.route('/kitchen/<int:section_id>')
def kitchen_dashboard(section_id):
    """Render kitchen dashboard for a specific section"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Get kitchen section details
        cursor.execute("""
            SELECT section_name, hotel_id
            FROM kitchen_sections
            WHERE id = %s
        """, (section_id,))
        
        section = cursor.fetchone()
        
        if not section:
            cursor.close()
            connection.close()
            return "Kitchen section not found", 404
        
        # Fetch hotel logo and name
        hotel_id = section.get('hotel_id')
        hotel_name = None
        hotel_logo = None
        if hotel_id:
            cursor.execute("SELECT hotel_name, logo FROM hotels WHERE id = %s", (hotel_id,))
            result = cursor.fetchone()
            if result:
                hotel_name = result['hotel_name']
                hotel_logo = result['logo']
        
        cursor.close()
        connection.close()
        
        return render_template('kitchen_dashboard_mobile.html',
                             section_id=section_id,
                             section_name=section['section_name'],
                             hotel_name=hotel_name,
                             hotel_logo=hotel_logo)
        
    except Exception as e:
        print(f"[KITCHEN_DASHBOARD ERROR] {e}")
        import traceback
        traceback.print_exc()
        return "Error loading kitchen dashboard", 500


# ============== Payment Info Routes ==============

@orders_bp.route('/api/get-payment-info', methods=['GET'])
def get_payment_info():
    """Get hotel UPI payment information for payment display"""
    try:
        hotel_id = request.args.get('hotel_id', type=int)
        
        if not hotel_id:
            return jsonify({
                "success": False,
                "message": "Hotel ID is required"
            })
        
        # Fetch hotel payment info
        payment_info = get_hotel_payment_info(hotel_id)
        
        if not payment_info:
            return jsonify({
                "success": False,
                "message": "Hotel not found"
            })
        
        return jsonify(payment_info)
        
    except Exception as e:
        print(f"[PAYMENT_INFO ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": "Server error"
        })


def get_hotel_payment_info(hotel_id: int) -> dict:
    """
    Fetch hotel UPI configuration for payment display.
    
    Args:
        hotel_id: ID of the hotel
        
    Returns:
        Dictionary with keys: upi_id, upi_qr_image, hotel_name, success
        Returns empty dict with success=False on error
    """
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT upi_id, upi_qr_image, hotel_name
            FROM hotels
            WHERE id = %s
        """, (hotel_id,))
        
        result = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if not result:
            return {
                "success": False,
                "message": "Hotel not found"
            }
        
        return {
            "success": True,
            "upi_id": result.get('upi_id'),
            "upi_qr_image": result.get('upi_qr_image'),
            "hotel_name": result.get('hotel_name')
        }
        
    except Exception as e:
        print(f"[GET_HOTEL_PAYMENT_INFO ERROR] {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": "Server error"
        }

@orders_bp.route('/api/digital-fee-settings', methods=['GET'])
def get_digital_fee_settings():
    """Get digital convenience fee toggle state for current hotel"""
    try:
        hotel_id = session.get('hotel_id')
        if not hotel_id:
            return jsonify({"success": False, "message": "Not authenticated"})
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT per_order_charge, COALESCE(digital_fee_enabled, 1) as digital_fee_enabled FROM hotel_wallet WHERE hotel_id = %s",
            (hotel_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if row:
            return jsonify({
                "success": True,
                "digital_fee_enabled": bool(row['digital_fee_enabled']),
                "per_order_charge": float(row['per_order_charge'] or 0)
            })
        return jsonify({"success": True, "digital_fee_enabled": True, "per_order_charge": 0})
    except Exception as e:
        print(f"[DIGITAL_FEE_SETTINGS ERROR] {e}")
        return jsonify({"success": False, "message": "Server error"})


@orders_bp.route('/api/digital-fee-settings', methods=['POST'])
def update_digital_fee_settings():
    """Toggle digital convenience fee on/off for current hotel"""
    try:
        hotel_id = session.get('hotel_id')
        if not hotel_id:
            return jsonify({"success": False, "message": "Not authenticated"})
        
        data = request.get_json()
        enabled = data.get('digital_fee_enabled', True)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE hotel_wallet SET digital_fee_enabled = %s WHERE hotel_id = %s",
            (1 if enabled else 0, hotel_id)
        )
        conn.commit()
        cursor.close()
        conn.close()
        
        status = "enabled" if enabled else "disabled"
        log_order_activity('settings', f"Digital Convenience Fee {status}", hotel_id)
        return jsonify({"success": True, "digital_fee_enabled": enabled, "message": f"Digital Convenience Fee {status}"})
    except Exception as e:
        print(f"[DIGITAL_FEE_UPDATE ERROR] {e}")
        return jsonify({"success": False, "message": "Server error"})


# ============== Bill Request Routes ==============

@orders_bp.route('/api/bill-request', methods=['POST'])
def create_bill_request():
    """Guest requests to see their bill"""
    try:
        data = request.get_json()
        table_id = data.get('table_id')
        session_id = data.get('session_id')
        guest_name = data.get('guest_name')

        if not table_id or not session_id:
            return jsonify({"success": False, "message": "Table ID and session ID required"})

        # Get hotel_id from table
        table = Table.get_table_by_id(table_id)
        hotel_id = table.get('hotel_id') if table else None

        request_id = BillRequest.create_request(table_id, session_id, guest_name, hotel_id)
        if request_id:
            log_order_activity('bill_request', f"Bill requested by {guest_name} at Table {table.get('table_number', table_id)}", hotel_id)
            return jsonify({"success": True, "request_id": request_id, "status": "PENDING"})
        return jsonify({"success": False, "message": "Failed to create request"})
    except Exception as e:
        print(f"[BILL_REQUEST ERROR] {e}")
        return jsonify({"success": False, "message": "Server error"})


@orders_bp.route('/api/bill-request/status', methods=['GET'])
def get_bill_request_status():
    """Check bill request status for a guest"""
    try:
        table_id = request.args.get('table_id')
        session_id = request.args.get('session_id')

        if not table_id or not session_id:
            return jsonify({"success": False, "message": "Table ID and session ID required"})

        status = BillRequest.get_request_status(int(table_id), session_id)
        return jsonify({"success": True, "status": status})
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})


@orders_bp.route('/api/bill-requests/pending', methods=['GET'])
def get_pending_bill_requests():
    """Get all pending bill requests for manager"""
    try:
        hotel_id = session.get('hotel_id')
        if not hotel_id:
            return jsonify({"success": False, "message": "Not authenticated"})
        requests_list = BillRequest.get_pending_requests(hotel_id)
        return jsonify({"success": True, "requests": requests_list})
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})


@orders_bp.route('/api/bill-request/<int:request_id>/approve', methods=['POST'])
def approve_bill_request(request_id):
    """Manager approves a bill request"""
    try:
        hotel_id = session.get('hotel_id')
        if not hotel_id:
            return jsonify({"success": False, "message": "Not authenticated"})
        BillRequest.update_status(request_id, 'APPROVED')
        log_order_activity('bill_request', f"Bill request #{request_id} approved", hotel_id)
        return jsonify({"success": True, "message": "Bill request approved"})
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})


@orders_bp.route('/api/bill-request/<int:request_id>/reject', methods=['POST'])
def reject_bill_request(request_id):
    """Manager rejects a bill request"""
    try:
        hotel_id = session.get('hotel_id')
        if not hotel_id:
            return jsonify({"success": False, "message": "Not authenticated"})
        BillRequest.update_status(request_id, 'REJECTED')
        log_order_activity('bill_request', f"Bill request #{request_id} rejected", hotel_id)
        return jsonify({"success": True, "message": "Bill request rejected"})
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})


@orders_bp.route('/api/order/<int:order_id>/request-bill', methods=['POST'])
def request_bill_for_order(order_id):
    """Guest marks bill as requested on their order"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE table_orders SET bill_requested = 1 WHERE id = %s",
            (order_id,)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": "Server error"})
