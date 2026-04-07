from database.db import get_db_connection
from mysql.connector import Error
import hashlib
import secrets
import string

def hash_password(password):
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_password(length=10):
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def generate_username(name, hotel_id):
    """Generate a unique username from name and hotel ID"""
    base = name.lower().replace(' ', '_')[:10]
    random_suffix = ''.join(secrets.choice(string.digits) for _ in range(4))
    return f"{base}_{hotel_id}_{random_suffix}"

class WaiterAuth:
    @staticmethod
    def login_qr(waiter_id, name, hotel_id):
        """Authenticate waiter via QR-based login (no password)"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Find waiter by ID
            cursor.execute("""
                SELECT w.*, h.hotel_name 
                FROM waiters w
                LEFT JOIN hotels h ON w.hotel_id = h.id
                WHERE w.id = %s AND w.hotel_id = %s
            """, (waiter_id, hotel_id))
            waiter = cursor.fetchone()
            
            if not waiter:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Waiter ID not found!'}
            
            # Verify name matches (case-insensitive)
            if waiter['name'].lower().strip() != name.lower().strip():
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Name does not match our records!'}
            
            # Check if waiter is active
            if not waiter.get('is_active', True):
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Account is deactivated. Contact your manager.'}
            
            cursor.close()
            connection.close()
            
            return {
                'success': True,
                'message': 'Login successful!',
                'id': waiter['id'],
                'name': waiter['name'],
                'email': waiter['email'],
                'hotel_id': waiter['hotel_id'],
                'hotel_name': waiter.get('hotel_name', ''),
                'manager_id': waiter['manager_id']
            }
        except Error as exc:
            return {'success': False, 'message': f'Database error: {str(exc)}'}
    
    @staticmethod
    def login(username, password):
        """Authenticate waiter login (legacy - kept for compatibility)"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Find waiter by username
            cursor.execute("""
                SELECT w.*, h.hotel_name 
                FROM waiters w
                LEFT JOIN hotels h ON w.hotel_id = h.id
                WHERE w.username = %s
            """, (username,))
            waiter = cursor.fetchone()
            
            if not waiter:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Username not found!'}
            
            # Check if waiter is active
            if not waiter.get('is_active', True):
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Account is deactivated. Contact your manager.'}
            
            # Check password
            hashed_password = hash_password(password)
            if waiter['password'] != hashed_password:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Incorrect password!'}
            
            cursor.close()
            connection.close()
            
            return {
                'success': True,
                'message': 'Login successful!',
                'id': waiter['id'],
                'name': waiter['name'],
                'email': waiter['email'],
                'hotel_id': waiter['hotel_id'],
                'hotel_name': waiter.get('hotel_name', ''),
                'manager_id': waiter['manager_id']
            }
        except Error as exc:
            return {'success': False, 'message': f'Database error: {str(exc)}'}
    
    @staticmethod
    def get_waiter_by_id(waiter_id):
        """Get waiter details by ID"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT w.*, h.hotel_name 
                FROM waiters w
                LEFT JOIN hotels h ON w.hotel_id = h.id
                WHERE w.id = %s
            """, (waiter_id,))
            waiter = cursor.fetchone()
            
            cursor.close()
            connection.close()
            return waiter
        except Error as exc:
            return None
    
    @staticmethod
    def get_assigned_tables(waiter_id):
        """Get all tables assigned to a waiter using ONLY waiter_table_assignments mapping table"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Use ONLY waiter_table_assignments table (not tables.waiter_id column)
            cursor.execute("""
                SELECT DISTINCT t.*, 
                       CASE WHEN at.status = 'ACTIVE' THEN 'BUSY' ELSE t.status END as derived_status
                FROM tables t
                INNER JOIN waiter_table_assignments wta ON t.id = wta.table_id
                LEFT JOIN active_tables at ON t.id = at.table_id AND at.status = 'ACTIVE'
                WHERE wta.waiter_id = %s
                ORDER BY t.table_number
            """, (waiter_id,))
            tables = cursor.fetchall()
            
            # Debug logging
            print(f"[WAITER DEBUG] get_assigned_tables for waiter_id={waiter_id}: found {len(tables)} tables")
            for t in tables:
                print(f"  - Table {t.get('table_number')} (id={t.get('id')})")
            
            # Update status to derived status
            for table in tables:
                if table.get('derived_status'):
                    table['status'] = table['derived_status']
            
            cursor.close()
            connection.close()
            return tables
        except Error as exc:
            print(f"[WAITER ERROR] get_assigned_tables error: {exc}")
            return []
    
    @staticmethod
    def get_orders_for_waiter(waiter_id, status=None):
        """Get all orders from tables assigned via waiter_table_assignments mapping table ONLY."""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Filter by waiter_table_assignments junction table ONLY
            query = """
                SELECT DISTINCT
                    o.*, 
                    t.table_number,
                    t.status as table_status
                FROM table_orders o
                JOIN tables t ON o.table_id = t.id
                INNER JOIN waiter_table_assignments wta ON t.id = wta.table_id
                WHERE wta.waiter_id = %s
            """
            params = [waiter_id]
            
            if status:
                query += " AND o.order_status = %s"
                params.append(status)
            
            query += " ORDER BY o.created_at DESC"
            
            cursor.execute(query, tuple(params))
            orders = cursor.fetchall()
            
            # Debug logging
            print(f"[WAITER DEBUG] get_orders_for_waiter for waiter_id={waiter_id}, status={status}: found {len(orders)} orders")
            for o in orders:
                print(f"  - Order {o.get('id')} table={o.get('table_number')} status={o.get('order_status')}")
            
            cursor.close()
            connection.close()
            return orders
        except Error as exc:
            print(f"[WAITER ERROR] get_orders_for_waiter error: {exc}")
            return []
    
    @staticmethod
    def update_order_status(order_id, new_status, waiter_id):
        """Update order status (only if order belongs to waiter via waiter_table_assignments)"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Verify order belongs to waiter - check waiter_table_assignments ONLY
            cursor.execute("""
                SELECT o.*, t.hotel_id as table_hotel_id FROM table_orders o
                JOIN tables t ON o.table_id = t.id
                INNER JOIN waiter_table_assignments wta ON t.id = wta.table_id
                WHERE o.id = %s AND wta.waiter_id = %s
            """, (order_id, waiter_id))
            
            order = cursor.fetchone()
            if not order:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Order not found or not authorized'}
            
            # Update order status
            cursor.execute(
                "UPDATE table_orders SET order_status = %s WHERE id = %s",
                (new_status, order_id)
            )
            
            connection.commit()
            
            cursor.close()
            connection.close()
            
            return {'success': True, 'message': f'Order status updated to {new_status}'}
        except Error as exc:
            return {'success': False, 'message': f'Database error: {str(exc)}'}
    
    @staticmethod
    def change_password(waiter_id, old_password, new_password):
        """Change waiter password"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Verify current password
            cursor.execute("SELECT password FROM waiters WHERE id = %s", (waiter_id,))
            waiter = cursor.fetchone()
            
            if not waiter:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Waiter not found!'}
            
            if waiter['password'] != hash_password(old_password):
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Current password is incorrect!'}
            
            # Update password
            cursor.execute(
                "UPDATE waiters SET password = %s WHERE id = %s",
                (hash_password(new_password), waiter_id)
            )
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return {'success': True, 'message': 'Password changed successfully!'}
        except Error as exc:
            return {'success': False, 'message': f'Database error: {str(exc)}'}


class WaiterTableAssignment:
    @staticmethod
    def assign_table(waiter_id, table_id):
        """Assign a table to a waiter (many-to-many - don't remove other waiters' assignments)"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Check if assignment already exists
            cursor.execute(
                "SELECT * FROM waiter_table_assignments WHERE waiter_id = %s AND table_id = %s",
                (waiter_id, table_id)
            )
            if cursor.fetchone():
                cursor.close()
                connection.close()
                return {'success': True, 'message': 'Table already assigned to this waiter!'}
            
            # Create new assignment (without removing other waiters)
            cursor.execute(
                "INSERT INTO waiter_table_assignments (waiter_id, table_id) VALUES (%s, %s)",
                (waiter_id, table_id)
            )
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return {'success': True, 'message': 'Table assigned successfully!'}
        except Error as exc:
            return {'success': False, 'message': f'Database error: {str(exc)}'}
    
    @staticmethod
    def unassign_table(table_id, waiter_id=None):
        """Remove table assignment - optionally for a specific waiter"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            if waiter_id:
                # Unassign only this waiter from the table
                cursor.execute(
                    "DELETE FROM waiter_table_assignments WHERE table_id = %s AND waiter_id = %s",
                    (table_id, waiter_id)
                )
            else:
                # Unassign all waiters from this table
                cursor.execute("DELETE FROM waiter_table_assignments WHERE table_id = %s", (table_id,))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return {'success': True, 'message': 'Table unassigned successfully!'}
        except Error as exc:
            return {'success': False, 'message': f'Database error: {str(exc)}'}
    
    @staticmethod
    def get_tables_with_assignments(hotel_id):
        """Get all tables with their waiter assignments for a hotel (supports multiple waiters per table)"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Get tables with all assigned waiters (aggregated)
            cursor.execute("""
                SELECT 
                    t.id,
                    t.table_number,
                    t.qr_code_path,
                    t.status,
                    t.hotel_id,
                    t.created_at,
                    GROUP_CONCAT(DISTINCT wta.waiter_id ORDER BY wta.waiter_id SEPARATOR ',') as waiter_ids,
                    GROUP_CONCAT(DISTINCT w.name ORDER BY w.name SEPARATOR ', ') as waiter_names
                FROM tables t
                LEFT JOIN waiter_table_assignments wta ON t.id = wta.table_id
                LEFT JOIN waiters w ON wta.waiter_id = w.id
                WHERE t.hotel_id = %s
                GROUP BY t.id, t.table_number, t.qr_code_path, t.status, t.hotel_id, t.created_at
                ORDER BY t.table_number
            """, (hotel_id,))
            tables = cursor.fetchall()
            
            # Convert waiter_ids string to list of integers
            for table in tables:
                if table['waiter_ids']:
                    table['waiter_id_list'] = [int(wid) for wid in table['waiter_ids'].split(',')]
                else:
                    table['waiter_id_list'] = []
            
            cursor.close()
            connection.close()
            return tables
        except Error as exc:
            return []
