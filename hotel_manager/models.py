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

class HotelManager:
    @staticmethod
    def create_account(name, email, username, password):
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Check if username or email already exists
            cursor.execute("SELECT * FROM managers WHERE username = %s OR email = %s", (username, email))
            if cursor.fetchone():
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Username or email already exists!'}
            
            # Insert new manager
            hashed_password = hash_password(password)
            cursor.execute(
                "INSERT INTO managers (name, email, username, password) VALUES (%s, %s, %s, %s)",
                (name, email, username, hashed_password)
            )
            connection.commit()
            cursor.close()
            connection.close()
            
            return {'success': True, 'message': 'Account created successfully!'}
        except Error as exc:
            return {'success': False, 'message': f'Database error: {str(exc)}'}
    
    @staticmethod
    def login(username, password):
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Find manager by username
            cursor.execute("SELECT * FROM managers WHERE username = %s", (username,))
            manager = cursor.fetchone()
            
            if not manager:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Username not found!'}
            
            # Check password
            hashed_password = hash_password(password)
            if manager[4] != hashed_password:  # manager[4] is the password column
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Incorrect password!'}
            
            manager_id = manager[0]
            manager_name = manager[1]
            
            # Fetch hotel assignment and modules for this manager
            cursor.execute("""
                SELECT hma.hotel_id, hm.kyc_enabled, hm.food_enabled, h.hotel_name
                FROM hotel_managers hma
                JOIN hotel_modules hm ON hma.hotel_id = hm.hotel_id
                JOIN hotels h ON hma.hotel_id = h.id
                WHERE hma.manager_id = %s
                LIMIT 1
            """, (manager_id,))
            hotel_data = cursor.fetchone()
            
            cursor.close()
            connection.close()
            
            if hotel_data:
                return {
                    'success': True,
                    'message': 'Login successful!',
                    'name': manager_name,
                    'id': manager_id,
                    'hotel_id': hotel_data[0],
                    'kyc_enabled': bool(hotel_data[1]),
                    'food_enabled': bool(hotel_data[2]),
                    'hotel_name': hotel_data[3]
                }
            else:
                # Manager not assigned to any hotel yet
                return {
                    'success': True,
                    'message': 'Login successful!',
                    'name': manager_name,
                    'id': manager_id,
                    'hotel_id': None,
                    'kyc_enabled': False,
                    'food_enabled': False,
                    'hotel_name': None
                }
        except Error as exc:
            return {'success': False, 'message': f'Database error: {str(exc)}'}
    
    @staticmethod
    def get_all_managers():
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT id, name, email, username, created_at FROM managers")
            managers = cursor.fetchall()
            cursor.close()
            connection.close()
            return managers
        except Error as exc:
            return None

    @staticmethod
    def delete_manager(manager_id):
        try:
            connection = get_db_connection()
            cursor = connection.cursor()

            # Verify manager exists
            cursor.execute("SELECT * FROM managers WHERE id = %s", (manager_id,))
            if not cursor.fetchone():
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Manager not found!'}

            # Delete manager (waiters will cascade)
            cursor.execute("DELETE FROM managers WHERE id = %s", (manager_id,))
            connection.commit()
            cursor.close()
            connection.close()

            return {'success': True, 'message': 'Manager deleted successfully!'}
        except Error as exc:
            return {'success': False, 'message': f'Database error: {str(exc)}'}

    @staticmethod
    def change_password(manager_id, current_password, new_password):
        """Change manager password"""
        connection = None
        cursor = None
        try:
            if not manager_id:
                return {'success': False, 'message': 'Manager ID is required!'}
            
            if not current_password or not new_password:
                return {'success': False, 'message': 'Password fields cannot be empty!'}
            
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Verify manager exists and get current password
            cursor.execute("SELECT password FROM managers WHERE id = %s", (manager_id,))
            manager = cursor.fetchone()
            
            if not manager:
                return {'success': False, 'message': 'Manager not found!'}
            
            stored_password = manager.get('password')
            if not stored_password:
                return {'success': False, 'message': 'No password set for this account!'}
            
            # Verify current password using hash comparison
            hashed_current = hash_password(current_password)
            if stored_password != hashed_current:
                return {'success': False, 'message': 'Current password is incorrect.'}
            
            # Hash and update new password
            hashed_new = hash_password(new_password)
            if not hashed_new:
                return {'success': False, 'message': 'Failed to hash new password!'}
            
            cursor.execute(
                "UPDATE managers SET password = %s WHERE id = %s",
                (hashed_new, manager_id)
            )
            
            connection.commit()
            
            return {'success': True, 'message': 'Password updated successfully.'}
        except Error as db_error:
            print(f"[MANAGER CHANGE PASSWORD] Database error: {db_error}")
            return {'success': False, 'message': f'Database error: {str(db_error)}'}
        except Exception as e:
            print(f"[MANAGER CHANGE PASSWORD] Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'An unexpected error occurred: {str(e)}'}
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

class Waiter:
    @staticmethod
    def validate_email(email):
        """Validate and normalize email: lowercase, trimmed, basic format check"""
        if not email:
            return None, 'Email is required!'
        email = email.strip().lower()
        if '@' not in email or '.' not in email.split('@')[-1]:
            return None, 'Invalid email format!'
        return email, None
    
    @staticmethod
    def validate_phone(phone):
        """Validate phone: exactly 10 digits, numbers only"""
        if not phone:
            return None, 'Phone number is required!'
        phone = phone.strip()
        if not phone.isdigit():
            return None, 'Phone number must contain only digits!'
        if len(phone) != 10:
            return None, 'Phone number must be exactly 10 digits!'
        return phone, None
    
    @staticmethod
    def create_waiter_qr(manager_id, name, email, phone, hotel_id=None, table_ids=None):
        """Create a waiter for QR-based login (no password required)"""
        try:
            # Validate and normalize inputs
            email, email_error = Waiter.validate_email(email)
            if email_error:
                return {'success': False, 'message': email_error}
            
            phone, phone_error = Waiter.validate_phone(phone)
            if phone_error:
                return {'success': False, 'message': phone_error}
            
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Check if email already exists (case-insensitive - email is already lowercase)
            cursor.execute("SELECT * FROM waiters WHERE LOWER(email) = %s", (email,))
            if cursor.fetchone():
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Email already exists!'}
            
            # Insert new waiter without password (QR-based login uses ID + Name)
            cursor.execute(
                """INSERT INTO waiters 
                   (manager_id, name, email, phone, hotel_id, is_active) 
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (manager_id, name, email, phone, hotel_id, True)
            )
            waiter_id = cursor.lastrowid
            
            # Assign tables if provided (many-to-many - don't remove existing assignments)
            if table_ids and len(table_ids) > 0:
                for table_id in table_ids:
                    # Check if assignment already exists
                    cursor.execute(
                        "SELECT * FROM waiter_table_assignments WHERE waiter_id = %s AND table_id = %s",
                        (waiter_id, table_id)
                    )
                    if not cursor.fetchone():
                        cursor.execute(
                            "INSERT INTO waiter_table_assignments (waiter_id, table_id) VALUES (%s, %s)",
                            (waiter_id, table_id)
                        )
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return {
                'success': True, 
                'message': 'Waiter created successfully!',
                'waiter_id': waiter_id,
                'name': name
            }
        except Error as exc:
            return {'success': False, 'message': f'Database error: {str(exc)}'}
    
    @staticmethod
    def create_waiter(manager_id, name, email, phone, username, password, hotel_id=None, table_ids=None):
        try:
            # Validate and normalize inputs
            email, email_error = Waiter.validate_email(email)
            if email_error:
                return {'success': False, 'message': email_error}
            
            phone, phone_error = Waiter.validate_phone(phone)
            if phone_error:
                return {'success': False, 'message': phone_error}
            
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Check if email already exists (case-insensitive)
            cursor.execute("SELECT * FROM waiters WHERE LOWER(email) = %s", (email,))
            if cursor.fetchone():
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Email already exists!'}
            
            # Check if username already exists
            cursor.execute("SELECT * FROM waiters WHERE username = %s", (username,))
            if cursor.fetchone():
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Username already exists!'}
            
            # Hash the password
            hashed_password = hash_password(password)
            
            # Insert new waiter with credentials
            cursor.execute(
                """INSERT INTO waiters 
                   (manager_id, name, email, phone, hotel_id, username, password, is_active) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (manager_id, name, email, phone, hotel_id, username, hashed_password, True)
            )
            waiter_id = cursor.lastrowid
            
            # Assign tables if provided (many-to-many - don't remove existing assignments)
            if table_ids and len(table_ids) > 0:
                for table_id in table_ids:
                    # Check if assignment already exists to avoid duplicate key error
                    cursor.execute(
                        "SELECT * FROM waiter_table_assignments WHERE waiter_id = %s AND table_id = %s",
                        (waiter_id, table_id)
                    )
                    if not cursor.fetchone():
                        cursor.execute(
                            "INSERT INTO waiter_table_assignments (waiter_id, table_id) VALUES (%s, %s)",
                            (waiter_id, table_id)
                        )
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return {
                'success': True, 
                'message': 'Waiter created successfully!',
                'waiter_id': waiter_id,
                'username': username
            }
        except Error as exc:
            return {'success': False, 'message': f'Database error: {str(exc)}'}
    
    @staticmethod
    def get_waiters_by_hotel(hotel_id):
        """Get all waiters for a specific hotel with their assigned tables"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            if hotel_id:
                cursor.execute("""
                    SELECT w.id AS waiter_id, w.name, w.email, w.phone, w.is_active, w.created_at,
                           COALESCE(w.show_waiter_tips, 1) as show_waiter_tips,
                           GROUP_CONCAT(t.table_number ORDER BY t.table_number SEPARATOR ', ') as assigned_tables
                    FROM waiters w
                    LEFT JOIN waiter_table_assignments wta ON w.id = wta.waiter_id
                    LEFT JOIN tables t ON wta.table_id = t.id
                    WHERE w.hotel_id = %s
                    GROUP BY w.id, w.name, w.email, w.phone, w.is_active, w.created_at, w.show_waiter_tips
                    ORDER BY w.id ASC
                """, (hotel_id,))
            else:
                cursor.execute("""
                    SELECT w.id AS waiter_id, w.name, w.email, w.phone, w.is_active, w.created_at,
                           COALESCE(w.show_waiter_tips, 1) as show_waiter_tips,
                           GROUP_CONCAT(t.table_number ORDER BY t.table_number SEPARATOR ', ') as assigned_tables
                    FROM waiters w
                    LEFT JOIN waiter_table_assignments wta ON w.id = wta.waiter_id
                    LEFT JOIN tables t ON wta.table_id = t.id
                    GROUP BY w.id, w.name, w.email, w.phone, w.is_active, w.created_at, w.show_waiter_tips
                    ORDER BY w.id ASC
                """)
            waiters = cursor.fetchall()
            cursor.close()
            connection.close()
            return waiters
        except Error as exc:
            return None
    
    @staticmethod
    def get_waiters_by_manager(manager_id):
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("SELECT id, name, email, phone, created_at FROM waiters WHERE manager_id = %s", (manager_id,))
            waiters = cursor.fetchall()
            cursor.close()
            connection.close()
            return waiters
        except Error as exc:
            return None
    
    @staticmethod
    def delete_waiter(waiter_id, hotel_id=None):
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Verify waiter belongs to this hotel
            if hotel_id:
                cursor.execute("SELECT * FROM waiters WHERE id = %s AND hotel_id = %s", (waiter_id, hotel_id))
            else:
                cursor.execute("SELECT * FROM waiters WHERE id = %s", (waiter_id,))
            if not cursor.fetchone():
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Waiter not found!'}
            
            cursor.execute("DELETE FROM waiters WHERE id = %s", (waiter_id,))
            connection.commit()
            cursor.close()
            connection.close()
            
            return {'success': True, 'message': 'Waiter deleted successfully!'}
        except Error as exc:
            return {'success': False, 'message': f'Database error: {str(exc)}'}
    
    @staticmethod
    def toggle_waiter_status(waiter_id, hotel_id=None):
        """Toggle waiter active/inactive status"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Verify waiter belongs to this hotel
            if hotel_id:
                cursor.execute("SELECT is_active FROM waiters WHERE id = %s AND hotel_id = %s", (waiter_id, hotel_id))
            else:
                cursor.execute("SELECT is_active FROM waiters WHERE id = %s", (waiter_id,))
            
            result = cursor.fetchone()
            if not result:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Waiter not found!'}
            
            current_status = result[0]
            new_status = not current_status
            
            cursor.execute("UPDATE waiters SET is_active = %s WHERE id = %s", (new_status, waiter_id))
            connection.commit()
            cursor.close()
            connection.close()
            
            status_text = 'activated' if new_status else 'deactivated'
            return {'success': True, 'message': f'Waiter {status_text} successfully!', 'is_active': new_status}
        except Error as exc:
            return {'success': False, 'message': f'Database error: {str(exc)}'}
    
    @staticmethod
    def get_waiter_by_id(waiter_id, hotel_id=None):
        """Get waiter details by ID"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            if hotel_id:
                cursor.execute("""
                    SELECT w.id AS waiter_id, w.name, w.email, w.phone, w.is_active, w.created_at, w.hotel_id
                    FROM waiters w
                    WHERE w.id = %s AND w.hotel_id = %s
                """, (waiter_id, hotel_id))
            else:
                cursor.execute("""
                    SELECT w.id AS waiter_id, w.name, w.email, w.phone, w.is_active, w.created_at, w.hotel_id
                    FROM waiters w
                    WHERE w.id = %s
                """, (waiter_id,))
            
            waiter = cursor.fetchone()
            
            if waiter:
                # Get assigned table IDs
                cursor.execute("""
                    SELECT table_id FROM waiter_table_assignments WHERE waiter_id = %s
                """, (waiter_id,))
                table_rows = cursor.fetchall()
                waiter['assigned_table_ids'] = [row['table_id'] for row in table_rows]
            
            cursor.close()
            connection.close()
            return waiter
        except Error as exc:
            return None
    
    @staticmethod
    def update_waiter(waiter_id, name, email, phone, table_ids, hotel_id=None):
        """Update waiter details and table assignments"""
        try:
            # Validate and normalize inputs
            email, email_error = Waiter.validate_email(email)
            if email_error:
                return {'success': False, 'message': email_error}
            
            phone, phone_error = Waiter.validate_phone(phone)
            if phone_error:
                return {'success': False, 'message': phone_error}
            
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Verify waiter belongs to this hotel
            if hotel_id:
                cursor.execute("SELECT * FROM waiters WHERE id = %s AND hotel_id = %s", (waiter_id, hotel_id))
            else:
                cursor.execute("SELECT * FROM waiters WHERE id = %s", (waiter_id,))
            
            if not cursor.fetchone():
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Waiter not found!'}
            
            # Check if email is taken by another waiter (case-insensitive)
            cursor.execute("SELECT id FROM waiters WHERE LOWER(email) = %s AND id != %s", (email, waiter_id))
            if cursor.fetchone():
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Email already in use by another waiter!'}
            
            # Update waiter details
            cursor.execute(
                "UPDATE waiters SET name = %s, email = %s, phone = %s WHERE id = %s",
                (name, email, phone, waiter_id)
            )
            
            # Update table assignments
            # Remove all existing assignments for this waiter
            cursor.execute("DELETE FROM waiter_table_assignments WHERE waiter_id = %s", (waiter_id,))
            
            # Add new assignments (many-to-many, so don't remove other waiters' assignments)
            if table_ids and len(table_ids) > 0:
                for table_id in table_ids:
                    cursor.execute(
                        "INSERT INTO waiter_table_assignments (waiter_id, table_id) VALUES (%s, %s)",
                        (waiter_id, table_id)
                    )
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return {'success': True, 'message': 'Waiter updated successfully!'}
        except Error as exc:
            return {'success': False, 'message': f'Database error: {str(exc)}'}
    
    @staticmethod
    def reset_waiter_password(waiter_id, new_password, hotel_id=None):
        """Reset waiter password to a new manually set password"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Verify waiter belongs to this hotel
            if hotel_id:
                cursor.execute("SELECT * FROM waiters WHERE id = %s AND hotel_id = %s", (waiter_id, hotel_id))
            else:
                cursor.execute("SELECT * FROM waiters WHERE id = %s", (waiter_id,))
            
            if not cursor.fetchone():
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Waiter not found!'}
            
            # Hash the new password
            hashed_password = hash_password(new_password)
            
            cursor.execute("UPDATE waiters SET password = %s WHERE id = %s", (hashed_password, waiter_id))
            connection.commit()
            cursor.close()
            connection.close()
            
            return {
                'success': True, 
                'message': 'Password reset successfully!'
            }
        except Error as exc:
            return {'success': False, 'message': f'Database error: {str(exc)}'}
    
    @staticmethod
    def assign_table_to_waiter(waiter_id, table_id, hotel_id=None):
        """Assign a table to a waiter"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Verify waiter belongs to this hotel
            if hotel_id:
                cursor.execute("SELECT * FROM waiters WHERE id = %s AND hotel_id = %s", (waiter_id, hotel_id))
                if not cursor.fetchone():
                    cursor.close()
                    connection.close()
                    return {'success': False, 'message': 'Waiter not found!'}
            
            # Check if assignment already exists (many-to-many - don't remove other waiters' assignments)
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
    
    @staticmethod
    def update_table_waiters(table_id, waiter_ids, hotel_id=None):
        """Update all waiter assignments for a specific table (many-to-many)"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Verify table belongs to this hotel if hotel_id provided
            if hotel_id:
                cursor.execute("SELECT * FROM tables WHERE id = %s AND hotel_id = %s", (table_id, hotel_id))
                if not cursor.fetchone():
                    cursor.close()
                    connection.close()
                    return {'success': False, 'message': 'Table not found!'}
            
            # Delete existing assignments for this table
            cursor.execute("DELETE FROM waiter_table_assignments WHERE table_id = %s", (table_id,))
            
            # Insert new assignments
            if waiter_ids and len(waiter_ids) > 0:
                for waiter_id in waiter_ids:
                    cursor.execute(
                        "INSERT INTO waiter_table_assignments (waiter_id, table_id) VALUES (%s, %s)",
                        (waiter_id, table_id)
                    )
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return {'success': True, 'message': 'Table assignments updated successfully!'}
        except Error as exc:
            return {'success': False, 'message': f'Database error: {str(exc)}'}


class DashboardStats:
    """Class to fetch real-time dashboard statistics"""
    
    @staticmethod
    def get_table_stats(hotel_id):
        """Get table statistics - busy vs available (today only)"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Get total tables for this hotel
            cursor.execute("""
                SELECT COUNT(*) as total FROM tables WHERE hotel_id = %s
            """, (hotel_id,))
            total_tables = cursor.fetchone()['total']
            
            # Get busy tables (tables with ACTIVE or PREPARING orders TODAY that are not PAID)
            cursor.execute("""
                SELECT COUNT(DISTINCT t.id) as busy 
                FROM tables t
                JOIN table_orders o ON t.id = o.table_id
                WHERE t.hotel_id = %s 
                AND o.order_status IN ('ACTIVE', 'PREPARING')
                AND (o.payment_status IS NULL OR o.payment_status = 'PENDING')
                AND DATE(o.created_at) = CURDATE()
            """, (hotel_id,))
            busy_tables = cursor.fetchone()['busy']
            
            available_tables = total_tables - busy_tables
            
            cursor.close()
            connection.close()
            
            return {
                'total': total_tables,
                'busy': busy_tables,
                'available': available_tables
            }
        except Exception as e:
            print(f"Error getting table stats: {e}")
            return {'total': 0, 'busy': 0, 'available': 0}
    
    @staticmethod
    def get_order_stats(hotel_id):
        """Get order statistics for today"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Get today's orders count
            cursor.execute("""
                SELECT COUNT(*) as total FROM table_orders 
                WHERE hotel_id = %s AND DATE(created_at) = CURDATE()
            """, (hotel_id,))
            today_orders = cursor.fetchone()['total']
            
            # Get active orders (ACTIVE + PREPARING) - today only
            cursor.execute("""
                SELECT COUNT(*) as active FROM table_orders 
                WHERE hotel_id = %s AND order_status IN ('ACTIVE', 'PREPARING')
                AND DATE(created_at) = CURDATE()
            """, (hotel_id,))
            active_orders = cursor.fetchone()['active']
            
            # Get completed orders today
            cursor.execute("""
                SELECT COUNT(*) as completed FROM table_orders 
                WHERE hotel_id = %s AND order_status = 'COMPLETED' AND DATE(created_at) = CURDATE()
            """, (hotel_id,))
            completed_orders = cursor.fetchone()['completed']
            
            cursor.close()
            connection.close()
            
            return {
                'today': today_orders,
                'active': active_orders,
                'completed': completed_orders
            }
        except Exception as e:
            print(f"Error getting order stats: {e}")
            return {'today': 0, 'active': 0, 'completed': 0}
    
    @staticmethod
    def get_revenue_stats(hotel_id):
        """Get revenue statistics"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Get today's revenue (from paid AND completed orders)
            cursor.execute("""
                                SELECT COALESCE(SUM(COALESCE(grand_total, total_amount)), 0) as today_revenue
                                FROM bills
                                WHERE hotel_id = %s
                                    AND payment_status = 'PAID'
                                    AND bill_status = 'COMPLETED'
                                    AND DATE(COALESCE(paid_at, created_at)) = CURDATE()
            """, (hotel_id,))
            today_revenue = float(cursor.fetchone()['today_revenue'])
            
            # Get total revenue (all time from paid AND completed orders)
            cursor.execute("""
                                SELECT COALESCE(SUM(COALESCE(grand_total, total_amount)), 0) as total_revenue
                                FROM bills
                                WHERE hotel_id = %s
                                    AND payment_status = 'PAID'
                                    AND bill_status = 'COMPLETED'
            """, (hotel_id,))
            total_revenue = float(cursor.fetchone()['total_revenue'])
            
            # Get pending revenue (unpaid orders) - today only
            cursor.execute("""
                                SELECT COALESCE(SUM(COALESCE(grand_total, total_amount)), 0) as pending
                                FROM bills
                                WHERE hotel_id = %s
                                    AND (payment_status IS NULL OR payment_status = 'PENDING')
                                    AND bill_status = 'OPEN'
                                    AND DATE(created_at) = CURDATE()
            """, (hotel_id,))
            pending_revenue = float(cursor.fetchone()['pending'])
            
            cursor.close()
            connection.close()
            
            return {
                'today': today_revenue,
                'total': total_revenue,
                'pending': pending_revenue
            }
        except Exception as e:
            print(f"Error getting revenue stats: {e}")
            return {'today': 0.0, 'total': 0.0, 'pending': 0.0}
    
    @staticmethod
    def get_menu_stats(hotel_id):
        """Get menu item statistics"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Get total menu dishes (not deleted) for this hotel
            cursor.execute("""
                SELECT COUNT(*) as total FROM menu_dishes
                WHERE hotel_id = %s AND (is_deleted = 0 OR is_deleted IS NULL)
            """, (hotel_id,))
            total_items = cursor.fetchone()['total']
            
            # Get category count
            cursor.execute("""
                SELECT COUNT(*) as categories FROM menu_categories 
                WHERE hotel_id = %s AND (is_deleted = 0 OR is_deleted IS NULL)
            """, (hotel_id,))
            categories = cursor.fetchone()['categories']
            
            cursor.close()
            connection.close()
            
            return {
                'total_items': total_items,
                'categories': categories
            }
        except Exception as e:
            print(f"Error getting menu stats: {e}")
            return {'total_items': 0, 'categories': 0}
    
    @staticmethod
    def get_verification_stats(hotel_id):
        """Get KYC verification statistics"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Get today's verifications from guest_verifications table
            cursor.execute("""
                SELECT COUNT(*) as today FROM guest_verifications 
                WHERE hotel_id = %s AND DATE(submitted_at) = CURDATE()
            """, (hotel_id,))
            today_verifications = cursor.fetchone()['today']
            
            # Get total verifications from guest_verifications table
            cursor.execute("""
                SELECT COUNT(*) as total FROM guest_verifications 
                WHERE hotel_id = %s
            """, (hotel_id,))
            total_verifications = cursor.fetchone()['total']
            
            cursor.close()
            connection.close()
            
            return {
                'today': today_verifications,
                'total': total_verifications
            }
        except Exception as e:
            print(f"Error getting verification stats: {e}")
            return {'today': 0, 'total': 0}
    
    @staticmethod
    def get_all_stats(hotel_id):
        """Get all dashboard statistics"""
        return {
            'tables': DashboardStats.get_table_stats(hotel_id),
            'orders': DashboardStats.get_order_stats(hotel_id),
            'revenue': DashboardStats.get_revenue_stats(hotel_id),
            'menu': DashboardStats.get_menu_stats(hotel_id),
            'verifications': DashboardStats.get_verification_stats(hotel_id)
        }


class RevenueReports:
    """Class to fetch revenue reporting data"""
    
    @staticmethod
    def get_revenue_summary(hotel_id):
        """Get revenue summary: today, yesterday, last month, total"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Today's Revenue (PAID and COMPLETED orders only)
            cursor.execute("""
                                SELECT COALESCE(SUM(COALESCE(grand_total, total_amount)), 0) as revenue
                                FROM bills
                                WHERE hotel_id = %s
                                    AND DATE(COALESCE(paid_at, created_at)) = CURDATE()
                                    AND payment_status = 'PAID'
                                    AND bill_status = 'COMPLETED'
            """, (hotel_id,))
            today_revenue = float(cursor.fetchone()['revenue'])
            
            # Yesterday's Revenue (PAID and COMPLETED orders only)
            cursor.execute("""
                                SELECT COALESCE(SUM(COALESCE(grand_total, total_amount)), 0) as revenue
                                FROM bills
                                WHERE hotel_id = %s
                                    AND DATE(COALESCE(paid_at, created_at)) = CURDATE() - INTERVAL 1 DAY
                                    AND payment_status = 'PAID'
                                    AND bill_status = 'COMPLETED'
            """, (hotel_id,))
            yesterday_revenue = float(cursor.fetchone()['revenue'])
            
            # Last Month Revenue (PAID and COMPLETED orders only)
            cursor.execute("""
                                SELECT COALESCE(SUM(COALESCE(grand_total, total_amount)), 0) as revenue
                                FROM bills
                WHERE hotel_id = %s 
                                AND MONTH(COALESCE(paid_at, created_at)) = MONTH(CURDATE() - INTERVAL 1 MONTH)
                                AND YEAR(COALESCE(paid_at, created_at)) = YEAR(CURDATE() - INTERVAL 1 MONTH)
                                AND payment_status = 'PAID'
                                AND bill_status = 'COMPLETED'
            """, (hotel_id,))
            last_month_revenue = float(cursor.fetchone()['revenue'])
            
            # Total Revenue (all time, PAID and COMPLETED orders only)
            cursor.execute("""
                                SELECT COALESCE(SUM(COALESCE(grand_total, total_amount)), 0) as revenue
                                FROM bills
                                WHERE hotel_id = %s
                                    AND payment_status = 'PAID'
                                    AND bill_status = 'COMPLETED'
            """, (hotel_id,))
            total_revenue = float(cursor.fetchone()['revenue'])
            
            cursor.close()
            connection.close()
            
            return {
                'today': today_revenue,
                'yesterday': yesterday_revenue,
                'last_month': last_month_revenue,
                'total': total_revenue
            }
        except Exception as e:
            print(f"Error getting revenue summary: {e}")
            return {'today': 0.0, 'yesterday': 0.0, 'last_month': 0.0, 'total': 0.0}
    
    @staticmethod
    def get_daily_revenue(hotel_id, days=30):
        """Get daily revenue data for the last N days"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT 
                    DATE(COALESCE(paid_at, created_at)) as date,
                    COUNT(*) as total_orders,
                    COALESCE(SUM(COALESCE(grand_total, total_amount)), 0) as revenue
                FROM bills
                WHERE hotel_id = %s 
                AND payment_status = 'PAID'
                AND bill_status = 'COMPLETED'
                AND DATE(COALESCE(paid_at, created_at)) >= CURDATE() - INTERVAL %s DAY
                GROUP BY DATE(COALESCE(paid_at, created_at))
                ORDER BY DATE(COALESCE(paid_at, created_at)) DESC
            """, (hotel_id, days))
            
            daily_data = cursor.fetchall()
            
            # Convert date and decimal to serializable format
            for row in daily_data:
                row['date'] = str(row['date'])
                row['revenue'] = float(row['revenue'])
            
            cursor.close()
            connection.close()
            
            return daily_data
        except Exception as e:
            print(f"Error getting daily revenue: {e}")
            return []


class DailySpecialMenu:
    """Model for managing daily special menu items - supports multiple specials per day"""
    
    @staticmethod
    def create_table():
        """Create the today_specials table if it doesn't exist"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Create new today_specials table (supports multiple specials per day)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS today_specials (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    hotel_id INT NOT NULL,
                    dish_name VARCHAR(255) NOT NULL,
                    description TEXT,
                    price DECIMAL(10, 2) NOT NULL,
                    image_path VARCHAR(500) DEFAULT NULL,
                    special_date DATE NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    display_order INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_hotel_date_active (hotel_id, special_date, is_active)
                )
            """)
            connection.commit()
            
            # Also ensure old table exists for backwards compatibility
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_special_menu (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    hotel_id INT NOT NULL,
                    menu_name VARCHAR(255) NOT NULL,
                    description TEXT,
                    price DECIMAL(10, 2) NOT NULL,
                    image_path VARCHAR(500) DEFAULT NULL,
                    special_date DATE NOT NULL,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_hotel_date (hotel_id, special_date),
                    INDEX idx_hotel_date_active (hotel_id, special_date, is_active)
                )
            """)
            connection.commit()
            
            cursor.close()
            connection.close()
            return True
        except Error as e:
            print(f"Error creating today_specials table: {e}")
            return False
    
    @staticmethod
    def get_today_specials(hotel_id):
        """Get all today's specials for a hotel"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, hotel_id, dish_name, description, price, image_path, special_date, is_active, display_order
                FROM today_specials 
                WHERE hotel_id = %s AND special_date = CURDATE() AND is_active = TRUE
                ORDER BY display_order ASC, created_at ASC
            """, (hotel_id,))
            specials = cursor.fetchall()
            cursor.close()
            connection.close()
            return specials
        except Error as e:
            print(f"Error getting today's specials: {e}")
            return []
    
    @staticmethod
    def get_today_special(hotel_id):
        """Get first today's special for backward compatibility"""
        specials = DailySpecialMenu.get_today_specials(hotel_id)
        if specials:
            # Convert dish_name to menu_name for backward compatibility
            special = specials[0]
            special['menu_name'] = special.get('dish_name', '')
            return special
        return None
    
    @staticmethod
    def get_special_by_id(special_id, hotel_id):
        """Get a specific special by ID"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, hotel_id, dish_name, description, price, image_path, special_date, is_active
                FROM today_specials 
                WHERE id = %s AND hotel_id = %s
            """, (special_id, hotel_id))
            special = cursor.fetchone()
            cursor.close()
            connection.close()
            return special
        except Error as e:
            print(f"Error getting special by id: {e}")
            return None
    
    @staticmethod
    def add_special(hotel_id, dish_name, description, price, image_path=None):
        """Add a new today's special"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Get next display order
            cursor.execute("""
                SELECT COALESCE(MAX(display_order), 0) + 1 as next_order 
                FROM today_specials 
                WHERE hotel_id = %s AND special_date = CURDATE()
            """, (hotel_id,))
            result = cursor.fetchone()
            next_order = result[0] if result else 1
            
            cursor.execute("""
                INSERT INTO today_specials 
                (hotel_id, dish_name, description, price, image_path, special_date, is_active, display_order)
                VALUES (%s, %s, %s, %s, %s, CURDATE(), TRUE, %s)
            """, (hotel_id, dish_name, description, price, image_path, next_order))
            
            special_id = cursor.lastrowid
            connection.commit()
            cursor.close()
            connection.close()
            
            return {'success': True, 'message': "Special dish added successfully!", 'id': special_id}
        except Error as e:
            print(f"Error adding special: {e}")
            return {'success': False, 'message': f'Database error: {str(e)}'}
    
    @staticmethod
    def update_special(special_id, hotel_id, dish_name, description, price, image_path=None):
        """Update an existing special"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            if image_path:
                cursor.execute("""
                    UPDATE today_specials 
                    SET dish_name = %s, description = %s, price = %s, image_path = %s, 
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND hotel_id = %s
                """, (dish_name, description, price, image_path, special_id, hotel_id))
            else:
                cursor.execute("""
                    UPDATE today_specials 
                    SET dish_name = %s, description = %s, price = %s, 
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s AND hotel_id = %s
                """, (dish_name, description, price, special_id, hotel_id))
            
            connection.commit()
            affected = cursor.rowcount
            cursor.close()
            connection.close()
            
            if affected > 0:
                return {'success': True, 'message': "Special dish updated successfully!"}
            return {'success': False, 'message': 'Special not found'}
        except Error as e:
            print(f"Error updating special: {e}")
            return {'success': False, 'message': f'Database error: {str(e)}'}
    
    @staticmethod
    def add_or_update_special(hotel_id, menu_name, description, price, image_path=None):
        """Add or update - for backward compatibility, adds a new special"""
        return DailySpecialMenu.add_special(hotel_id, menu_name, description, price, image_path)
    
    @staticmethod
    def update_special_image(hotel_id, image_path):
        """Update image for the most recent special - backward compatibility"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("""
                UPDATE today_specials 
                SET image_path = %s, updated_at = CURRENT_TIMESTAMP
                WHERE hotel_id = %s AND special_date = CURDATE() AND is_active = TRUE
                ORDER BY created_at DESC LIMIT 1
            """, (image_path, hotel_id))
            connection.commit()
            affected = cursor.rowcount
            cursor.close()
            connection.close()
            
            if affected > 0:
                return {'success': True, 'message': 'Image updated successfully!'}
            return {'success': False, 'message': 'No special found for today'}
        except Error as e:
            print(f"Error updating special image: {e}")
            return {'success': False, 'message': f'Database error: {str(e)}'}
    
    @staticmethod
    def delete_special(special_id, hotel_id):
        """Delete a specific special by ID"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("""
                UPDATE today_specials 
                SET is_active = FALSE 
                WHERE id = %s AND hotel_id = %s
            """, (special_id, hotel_id))
            connection.commit()
            affected = cursor.rowcount
            cursor.close()
            connection.close()
            
            if affected > 0:
                return {'success': True, 'message': "Special dish removed!"}
            return {'success': False, 'message': 'Special not found'}
        except Error as e:
            print(f"Error deleting special: {e}")
            return {'success': False, 'message': f'Database error: {str(e)}'}
    
    @staticmethod
    def delete_today_special(hotel_id):
        """Delete/deactivate all today's specials - backward compatibility"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("""
                UPDATE today_specials 
                SET is_active = FALSE 
                WHERE hotel_id = %s AND special_date = CURDATE()
            """, (hotel_id,))
            connection.commit()
            cursor.close()
            connection.close()
            return {'success': True, 'message': "All today's specials removed!"}
        except Error as e:
            print(f"Error deleting specials: {e}")
            return {'success': False, 'message': f'Database error: {str(e)}'}