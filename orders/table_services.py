import os
import qrcode
import uuid
from flask import url_for
from .table_models import Table, TableOrder, Bill, BillRequest

class TableService:
    @staticmethod
    def create_qr_code(table_id, table_number):
        """Generate QR code for table"""
        try:
            # QR code contains URL to menu with table ID - use url_for for correct absolute URL
            qr_data = url_for('orders.table_menu', table_id=table_id, _external=True)
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save QR code
            qr_dir = "static/uploads"
            os.makedirs(qr_dir, exist_ok=True)
            
            filename = f"Table_{table_number}_QR.png"
            filepath = os.path.join(qr_dir, filename)
            img.save(filepath)
            
            return filepath
        except Exception as e:
            print(f"Error creating QR code: {e}")
            return None
    
    @staticmethod
    def add_new_table(table_number, hotel_id=None):
        """Add new table with QR code"""
        try:
            # Check if table number exists for this hotel
            existing_tables = Table.get_all_tables(hotel_id)
            for table in existing_tables:
                if table['table_number'] == table_number:
                    return {"success": False, "message": "Table number already exists"}
            
            # Create table first
            table_id = Table.add_table(table_number, "", hotel_id)
            if not table_id:
                return {"success": False, "message": "Failed to create table"}
            
            # Generate QR code
            qr_path = TableService.create_qr_code(table_id, table_number)
            if not qr_path:
                return {"success": False, "message": "Failed to generate QR code"}
            
            # Update table with QR path
            from database.db import get_db_connection
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE tables SET qr_code_path = %s WHERE id = %s",
                (qr_path, table_id)
            )
            connection.commit()
            cursor.close()
            connection.close()
            
            return {
                "success": True,
                "message": "Table added successfully",
                "table_id": table_id
            }
        except Exception as e:
            print(f"Error adding table: {e}")
            return {"success": False, "message": "Server error"}
    
    @staticmethod
    def delete_table(table_number, hotel_id=None):
        """Delete specific table by table number"""
        try:
            from database.db import get_db_connection
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Get table info first with hotel_id validation if provided
            if hotel_id:
                cursor.execute("SELECT id, qr_code_path FROM tables WHERE table_number = %s AND hotel_id = %s", (table_number, hotel_id))
            else:
                cursor.execute("SELECT id, qr_code_path FROM tables WHERE table_number = %s", (table_number,))
            
            table = cursor.fetchone()
            
            if not table:
                cursor.close()
                connection.close()
                return {"success": False, "message": "Table not found or access denied"}
            
            table_id, qr_path = table
            
            # Delete related records first to avoid foreign key constraints
            try:
                # Delete bills first
                cursor.execute("DELETE FROM bills WHERE table_id = %s", (table_id,))
                
                # Delete orders
                cursor.execute("DELETE FROM table_orders WHERE table_id = %s", (table_id,))
                
                # Delete waiter calls
                cursor.execute("DELETE FROM waiter_calls WHERE table_id = %s", (table_id,))
                
                # Delete active tables entries
                cursor.execute("DELETE FROM active_tables WHERE table_id = %s", (table_id,))
                
                # Delete waiter table assignments
                cursor.execute("DELETE FROM waiter_table_assignments WHERE table_id = %s", (table_id,))
                
                # Finally delete the table
                cursor.execute("DELETE FROM tables WHERE id = %s", (table_id,))
                
                connection.commit()
                
            except Exception as db_error:
                connection.rollback()
                cursor.close()
                connection.close()
                print(f"Database error deleting table {table_number}: {db_error}")
                return {"success": False, "message": f"Database error: {str(db_error)}"}
            
            cursor.close()
            connection.close()
            
            # Delete QR file if exists
            try:
                if qr_path and os.path.exists(qr_path):
                    os.remove(qr_path)
            except Exception as file_error:
                print(f"Warning: Could not delete QR file {qr_path}: {file_error}")
                # Don't fail the whole operation for file deletion issues
            
            return {"success": True, "message": f"Table {table_number} deleted successfully"}
            
        except Exception as e:
            print(f"Error deleting table {table_number}: {e}")
            return {"success": False, "message": f"Server error: {str(e)}"}

class OrderService:
    @staticmethod
    def check_guest_access(table_id, guest_name):
        """Check if a guest can access a table based on existing OPEN bills.
        Returns view_only_mode=True if another guest has an open bill."""
        try:
            table = Table.get_table_by_id(table_id)
            if not table:
                return {"success": False, "message": "Table not found", "can_order": False, "view_only_mode": False}
            
            if not guest_name or not guest_name.strip():
                return {"success": False, "message": "Guest name is required", "can_order": False, "view_only_mode": False}
            
            guest_name = guest_name.strip()
            
            # Check for any OPEN bill on this table
            existing_bill = Bill.get_any_open_bill_for_table(table_id)
            
            if not existing_bill:
                # No open bill - table is available for anyone
                # Signal frontend to clear any stale session data
                return {
                    "success": True, 
                    "can_order": True,
                    "view_only_mode": False,
                    "message": "Table available",
                    "is_returning_guest": False,
                    "existing_bill": None,
                    "clear_session": True  # Tell frontend to clear old session/localStorage
                }
            
            # There's an open bill - check the guest name
            existing_guest = existing_bill.get('guest_name')
            
            # If existing bill has NO guest_name (NULL/empty), treat table as available
            # This handles orphaned bills from before guest name capture was implemented
            if not existing_guest or not existing_guest.strip():
                return {
                    "success": True, 
                    "can_order": True,
                    "view_only_mode": False,
                    "message": "Table available",
                    "is_returning_guest": False,
                    "existing_bill": None,
                    "clear_session": True  # Clear any stale session for new guest
                }
            
            # Existing bill has a guest name - check if it matches
            if existing_guest.lower().strip() == guest_name.lower():
                # Same guest returning - check if their bill is already PAID
                if existing_bill.get('payment_status') == 'PAID' or existing_bill.get('bill_status') == 'COMPLETED':
                    return {
                        "success": True,
                        "can_order": False,
                        "view_only_mode": False,
                        "payment_completed": True,
                        "message": "Payment completed. This table session is now closed.",
                        "is_returning_guest": False,
                        "existing_bill": None
                    }
                # Same guest, bill still open - allow full access
                return {
                    "success": True,
                    "can_order": True,
                    "view_only_mode": False,
                    "message": "Welcome back! Your previous order is still open.",
                    "is_returning_guest": True,
                    "existing_bill": {
                        "bill_id": existing_bill.get('id'),
                        "bill_number": existing_bill.get('bill_number'),
                        "total_amount": existing_bill.get('total_amount'),
                        "items_count": len(existing_bill.get('items', []))
                    },
                    "session_id": existing_bill.get('session_id')
                }
            else:
                # Different guest - VIEW ONLY MODE (can see menu but cannot order)
                return {
                    "success": True,
                    "can_order": False,
                    "view_only_mode": True,
                    "message": f"This table is currently occupied by another guest. You can view the menu, but ordering is disabled until the current guest completes payment.",
                    "is_returning_guest": False,
                    "existing_bill": None,
                    "occupied_by": existing_guest  # Don't show full name for privacy
                }
                
        except Exception as e:
            print(f"Error checking guest access: {e}")
            return {"success": False, "message": "Server error", "can_order": False, "view_only_mode": False}
    
    @staticmethod
    def create_order(table_id, items, session_id=None, guest_name=None):
        """Create new ACTIVE order and set table BUSY - with guest name-based bill grouping"""
        try:
            from orders.table_models import ActiveTable
            
            table = Table.get_table_by_id(table_id)
            if not table:
                return {"success": False, "message": "Table not found"}
            
            hotel_id = table.get('hotel_id')
            
            # Validate guest name is provided
            if not guest_name or not guest_name.strip():
                return {"success": False, "message": "Guest name is required"}
            
            guest_name = guest_name.strip()
            
            # Check for existing OPEN bill on this table
            existing_bill = Bill.get_any_open_bill_for_table(table_id)
            
            if existing_bill:
                existing_guest = existing_bill.get('guest_name', '')
                
                # Block if this guest's bill is already PAID
                if existing_guest and existing_guest.lower() == guest_name.lower():
                    if existing_bill.get('payment_status') == 'PAID' or existing_bill.get('bill_status') == 'COMPLETED':
                        return {
                            "success": False,
                            "message": "Payment already completed. This table session is closed. No new orders can be placed.",
                            "payment_completed": True
                        }
                    # Same guest, bill open - use their existing session
                    session_id = existing_bill.get('session_id')
                    guest_name = existing_guest  # Preserve original case
                else:
                    # Different guest - deny access
                    return {
                        "success": False, 
                        "message": f"Table is currently busy with another guest. Please wait for them to finish."
                    }

            if not session_id:
                session_id = str(uuid.uuid4())
            
            # Calculate total
            total_amount = sum(item['price'] * item['quantity'] for item in items)
            
            # Get assigned waiter_id - check both tables.waiter_id AND waiter_table_assignments
            waiter_id = table.get('waiter_id')
            
            # If no direct waiter_id, check waiter_table_assignments table
            if not waiter_id:
                from database.db import get_db_connection
                try:
                    conn = get_db_connection()
                    cur = conn.cursor(dictionary=True)
                    cur.execute("""
                        SELECT waiter_id FROM waiter_table_assignments 
                        WHERE table_id = %s LIMIT 1
                    """, (table_id,))
                    assignment = cur.fetchone()
                    if assignment:
                        waiter_id = assignment.get('waiter_id')
                    cur.close()
                    conn.close()
                except Exception as e:
                    print(f"Error fetching waiter assignment: {e}")
            
            # Merge into existing active order for same table + same guest/session (if any)
            active_order = TableOrder.get_active_order_for_guest(table_id, session_id=session_id, guest_name=guest_name)

            if active_order:
                order_id = active_order['id']
                order_id, error_message = TableOrder.add_items_to_order(order_id, items)
                if not order_id:
                    if error_message:
                        return {"success": False, "message": f"Failed to update active order: {error_message}"}
                    return {"success": False, "message": "Failed to update active order"}
                order_message = "Items added to existing active order"
            else:
                # Create new ACTIVE order only if no existing active order is found
                order_id, error_message = TableOrder.add_order(table_id, session_id, items, total_amount, hotel_id, guest_name, waiter_id)
                if not order_id:
                    if error_message:
                        return {"success": False, "message": f"Failed to create order: {error_message}"}
                    return {"success": False, "message": "Failed to create order"}
                order_message = "Order created successfully"
            
            # Create or update bill for this guest (same guest + same table = same bill)
            bill_info = Bill.create_bill(order_id, table_id, session_id, items, total_amount, hotel_id, guest_name)

            # New items were added: reopen bill-request flow for this active session.
            BillRequest.reset_for_new_order(table_id, session_id)
            
            # Create or update Active Table entry (links table to open bill)
            if bill_info:
                bill_id = bill_info.get('bill_id')
                ActiveTable.create_or_get_active_entry(table_id, bill_id, guest_name, session_id, hotel_id)
            
            return {
                "success": True,
                "message": order_message,
                "order_id": order_id,
                "session_id": session_id,
                "guest_name": guest_name,
                "bill": bill_info
            }
        except Exception as e:
            print(f"Error creating order: {e}")
            return {"success": False, "message": "Server error"}
    
    @staticmethod
    def complete_order(order_id):
        """Complete order (mark as served). Bill stays OPEN until payment."""
        try:
            if TableOrder.complete_order(order_id):
                return {"success": True, "message": "Order marked as completed (served). Bill stays open until payment."}
            else:
                return {"success": False, "message": "Failed to complete order"}
        except Exception as e:
            print(f"Error completing order: {e}")
            return {"success": False, "message": "Server error"}

    @staticmethod
    def get_session_orders(table_id, session_id):
        """Get orders for current session"""
        try:
            orders = TableOrder.get_orders_by_session(table_id, session_id)
            return {"success": True, "orders": orders}
        except Exception as e:
            print(f"Error getting session orders: {e}")
            return {"success": False, "message": "Server error"}

    @staticmethod
    def complete_payment(table_id, session_id):
        """Complete payment and end table session - This is called AFTER payment is confirmed"""
        try:
            from orders.table_models import ActiveTable
            
            table = Table.get_table_by_id(table_id)
            if not table:
                return {"success": False, "message": "Table not found"}

            # Validate session by checking for OPEN bill instead of table.current_session_id
            open_bill = Bill.get_any_open_bill_for_table(table_id)
            
            if not open_bill:
                return {"success": False, "message": "No open bill found for this table"}
            
            # Use the bill's session_id if the provided one doesn't match
            bill_session_id = open_bill.get('session_id')
            if bill_session_id and bill_session_id != session_id:
                session_id = bill_session_id

            from database.db import get_db_connection
            import datetime
            connection = get_db_connection()
            cursor = connection.cursor()
            
            paid_at = datetime.datetime.now()

            # Mark all orders as COMPLETED (served)
            cursor.execute(
                "UPDATE table_orders SET order_status = 'COMPLETED' WHERE table_id = %s AND session_id = %s",
                (table_id, session_id)
            )

            # Mark bill as COMPLETED and PAID - THIS is where bill closure happens
            cursor.execute(
                "UPDATE bills SET bill_status = 'COMPLETED', payment_status = 'PAID', paid_at = %s WHERE table_id = %s AND session_id = %s AND bill_status = 'OPEN'",
                (paid_at, table_id, session_id)
            )

            # Release the table
            cursor.execute(
                "UPDATE tables SET status = 'AVAILABLE', current_session_id = NULL, current_guest_name = NULL WHERE id = %s",
                (table_id,)
            )
            
            # Close the active table entry (CRITICAL: payment closes active table)
            cursor.execute("""
                UPDATE active_tables 
                SET status = 'CLOSED', closed_at = %s
                WHERE table_id = %s AND status = 'ACTIVE'
            """, (paid_at, table_id))

            connection.commit()
            cursor.close()
            connection.close()

            return {
                "success": True,
                "message": 'Payment completed. Table is now available.'
            }
        except Exception as e:
            print(f"Error completing payment: {e}")
            return {"success": False, "message": "Server error"}

    @staticmethod
    def complete_bill(bill_id):
        """Complete a bill - lock it and free table if needed"""
        try:
            if Bill.complete_bill(bill_id):
                return {"success": True, "message": "Bill completed. Table is now available."}
            else:
                return {"success": False, "message": "Failed to complete bill"}
        except Exception as e:
            print(f"Error completing bill: {e}")
            return {"success": False, "message": "Server error"}

    @staticmethod
    def update_order_status(order_id, status):
        """Update order status (ACTIVE/PREPARING/COMPLETED)."""
        try:
            if status not in {"ACTIVE", "PREPARING", "COMPLETED"}:
                return {"success": False, "message": "Invalid status"}

            if TableOrder.update_order_status(order_id, status):
                return {"success": True, "message": "Order status updated"}

            return {"success": False, "message": "Failed to update order status"}
        except Exception as e:
            print(f"Error updating order status: {e}")
            return {"success": False, "message": "Server error"}