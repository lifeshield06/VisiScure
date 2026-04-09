"""
Waiter Call Service - Backend logic for Waiter Call System
"""

from database.db import get_db_connection
from mysql.connector import Error
from datetime import datetime


class WaiterCallService:
    """Service layer for managing waiter assistance requests"""

    _schema_checked = False

    @staticmethod
    def _ensure_waiter_calls_schema(cursor):
        """One-time compatibility fix for legacy schemas."""
        if WaiterCallService._schema_checked:
            return
        try:
            cursor.execute(
                """
                SELECT IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME = 'waiter_calls'
                  AND COLUMN_NAME = 'waiter_id'
                LIMIT 1
                """
            )
            row = cursor.fetchone()
            if row:
                is_nullable = row['IS_NULLABLE'] if isinstance(row, dict) else row[0]
                if str(is_nullable).upper() == 'NO':
                    cursor.execute("ALTER TABLE waiter_calls MODIFY COLUMN waiter_id INT NULL")
            WaiterCallService._schema_checked = True
        except Exception as schema_error:
            print(f"[WAITER_CALL SCHEMA WARNING] {schema_error}")

    @staticmethod
    def create_request(table_id, session_id=None, guest_name=None):
        """
        Create waiter assistance requests for waiters assigned to the table.
        Falls back to notifying all hotel waiters if no waiter is assigned to table.
        """
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            WaiterCallService._ensure_waiter_calls_schema(cursor)

            # LEFT JOIN so we always get the table row even with no waiter assigned
            cursor.execute(
                """SELECT t.id, t.hotel_id, wta.waiter_id
                   FROM tables t
                   LEFT JOIN waiter_table_assignments wta ON t.id = wta.table_id
                   WHERE t.id = %s""",
                (table_id,)
            )
            rows = cursor.fetchall()

            if not rows:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Table not found'}

            hotel_id = rows[0]['hotel_id']
            # Only rows that actually have a waiter assigned
            table_waiters = [r for r in rows if r['waiter_id'] is not None]

            # 10-second cooldown — check only PENDING calls to avoid blocking after completion
            cursor.execute(
                """SELECT id, created_at FROM waiter_calls
                   WHERE table_id = %s AND status = 'PENDING'
                   ORDER BY created_at DESC LIMIT 1""",
                (table_id,)
            )
            last_request = cursor.fetchone()

            if last_request and last_request['created_at']:
                time_since_last = (datetime.now() - last_request['created_at']).total_seconds()
                if time_since_last < 10:
                    cursor.close()
                    connection.close()
                    wait_time = int(10 - time_since_last)
                    return {
                        'success': False,
                        'message': f'Please wait {wait_time} seconds before calling again',
                        'cooldown': True,
                        'wait_seconds': wait_time
                    }

            request_ids = []
            notified_waiters = []

            if table_waiters:
                # One record per assigned waiter
                for tw in table_waiters:
                    waiter_id = tw['waiter_id']
                    cursor.execute(
                        """INSERT INTO waiter_calls
                           (hotel_id, table_id, waiter_id, session_id, guest_name, status, created_at)
                           VALUES (%s, %s, %s, %s, %s, 'PENDING', NOW())""",
                        (hotel_id, table_id, waiter_id, session_id, guest_name)
                    )
                    request_ids.append(cursor.lastrowid)
                    notified_waiters.append(waiter_id)
                    print(f"[WAITER_CALL] Created request {cursor.lastrowid} for table {table_id}, waiter {waiter_id}")
            else:
                # No waiter assigned to table — notify all waiters in same hotel.
                cursor.execute(
                    """SELECT id
                       FROM waiters
                       WHERE hotel_id = %s""",
                    (hotel_id,)
                )
                hotel_waiters = cursor.fetchall() or []

                if not hotel_waiters:
                    cursor.close()
                    connection.close()
                    return {
                        'success': False,
                        'message': 'No waiter is available for this hotel. Please contact staff.'
                    }

                for waiter in hotel_waiters:
                    waiter_id = waiter['id']
                    cursor.execute(
                        """INSERT INTO waiter_calls
                           (hotel_id, table_id, waiter_id, session_id, guest_name, status, created_at)
                           VALUES (%s, %s, %s, %s, %s, 'PENDING', NOW())""",
                        (hotel_id, table_id, waiter_id, session_id, guest_name)
                    )
                    request_ids.append(cursor.lastrowid)
                    notified_waiters.append(waiter_id)
                    print(f"[WAITER_CALL] Fallback request {cursor.lastrowid} for table {table_id}, waiter {waiter_id}")

            connection.commit()
            cursor.close()
            connection.close()

            message = 'Waiter notified successfully' if notified_waiters else 'Staff notified successfully'
            return {
                'success': True,
                'message': message,
                'request_ids': request_ids,
                'notified_waiters': notified_waiters,
                'waiter_count': len(notified_waiters)
            }

        except Error as e:
            print(f"[WAITER_CALL ERROR] create_request: {e}")
            return {'success': False, 'message': f'Database error: {str(e)}'}

    @staticmethod
    def get_pending_requests(waiter_id):
        """
        Get pending requests ONLY for tables assigned to this waiter.
        Strictly filters by waiter_id AND waiter_table_assignments — no cross-waiter leakage.
        """
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                """SELECT wc.*, t.table_number, COALESCE(w.name, '') as waiter_name
                   FROM waiter_calls wc
                   JOIN tables t ON wc.table_id = t.id
                   LEFT JOIN waiters w ON wc.waiter_id = w.id
                   WHERE wc.waiter_id = %s
                     AND wc.status = 'PENDING'
                     AND wc.table_id IN (
                         SELECT table_id
                         FROM waiter_table_assignments
                         WHERE waiter_id = %s
                     )
                   ORDER BY wc.created_at ASC""",
                (waiter_id, waiter_id)
            )

            requests = cursor.fetchall()

            for req in requests:
                if req.get('created_at'):
                    req['created_at'] = req['created_at'].isoformat()
                if req.get('acknowledged_at'):
                    req['acknowledged_at'] = req['acknowledged_at'].isoformat()
                if req.get('completed_at'):
                    req['completed_at'] = req['completed_at'].isoformat()

            cursor.close()
            connection.close()

            print(f"[WAITER_CALL] Found {len(requests)} pending requests for waiter {waiter_id}")
            return requests

        except Error as e:
            print(f"[WAITER_CALL ERROR] get_pending_requests: {e}")
            return []

    @staticmethod
    def acknowledge_request(request_id, waiter_id):
        """Mark a request as acknowledged — only by the assigned waiter"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                "SELECT id, status, waiter_id FROM waiter_calls WHERE id = %s",
                (request_id,)
            )
            request = cursor.fetchone()

            if not request:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Request not found'}

            if request['waiter_id'] is not None and request['waiter_id'] != waiter_id:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Unauthorized: Request belongs to another waiter'}

            if request['status'] != 'PENDING':
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Request already acknowledged or completed'}

            cursor.execute(
                "UPDATE waiter_calls SET status = 'ACKNOWLEDGED', acknowledged_at = NOW() WHERE id = %s",
                (request_id,)
            )
            connection.commit()

            cursor.execute("SELECT acknowledged_at FROM waiter_calls WHERE id = %s", (request_id,))
            result = cursor.fetchone()
            acknowledged_at = result['acknowledged_at'].isoformat() if result and result['acknowledged_at'] else None

            cursor.close()
            connection.close()

            print(f"[WAITER_CALL] Request {request_id} acknowledged by waiter {waiter_id}")
            return {'success': True, 'message': 'Request acknowledged', 'acknowledged_at': acknowledged_at}

        except Error as e:
            print(f"[WAITER_CALL ERROR] acknowledge_request: {e}")
            return {'success': False, 'message': f'Database error: {str(e)}'}

    @staticmethod
    def complete_request(request_id, waiter_id):
        """Mark a request as completed — only by the assigned waiter"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                "SELECT id, status, waiter_id FROM waiter_calls WHERE id = %s",
                (request_id,)
            )
            request = cursor.fetchone()

            if not request:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Request not found'}

            if request['waiter_id'] is not None and request['waiter_id'] != waiter_id:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Unauthorized: Request belongs to another waiter'}

            if request['status'] == 'COMPLETED':
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Request already completed'}

            if request['status'] == 'PENDING':
                cursor.execute(
                    "UPDATE waiter_calls SET status = 'COMPLETED', acknowledged_at = NOW(), completed_at = NOW() WHERE id = %s",
                    (request_id,)
                )
            else:
                cursor.execute(
                    "UPDATE waiter_calls SET status = 'COMPLETED', completed_at = NOW() WHERE id = %s",
                    (request_id,)
                )

            connection.commit()

            cursor.execute("SELECT completed_at FROM waiter_calls WHERE id = %s", (request_id,))
            result = cursor.fetchone()
            completed_at = result['completed_at'].isoformat() if result and result['completed_at'] else None

            cursor.close()
            connection.close()

            print(f"[WAITER_CALL] Request {request_id} completed by waiter {waiter_id}")
            return {'success': True, 'message': 'Request completed', 'completed_at': completed_at}

        except Error as e:
            print(f"[WAITER_CALL ERROR] complete_request: {e}")
            return {'success': False, 'message': f'Database error: {str(e)}'}

    @staticmethod
    def check_existing_request(table_id):
        """Check if a table has an existing pending request"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                """SELECT id, created_at, waiter_id FROM waiter_calls
                   WHERE table_id = %s AND status = 'PENDING'
                   ORDER BY created_at DESC LIMIT 1""",
                (table_id,)
            )
            request = cursor.fetchone()
            cursor.close()
            connection.close()

            if not request:
                return {'has_pending': False, 'message': 'No pending request'}

            time_elapsed = int((datetime.now() - request['created_at']).total_seconds()) if request['created_at'] else 0
            return {
                'has_pending': True,
                'request_id': request['id'],
                'created_at': request['created_at'].isoformat() if request['created_at'] else None,
                'time_elapsed_seconds': time_elapsed,
                'message': 'Waiter already notified'
            }

        except Error as e:
            print(f"[WAITER_CALL ERROR] check_existing_request: {e}")
            return {'has_pending': False, 'message': 'Error checking request'}

    @staticmethod
    def get_all_requests(hotel_id=None, status_filter=None, waiter_filter=None):
        """Get all requests for manager dashboard"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            query = """
                SELECT wc.*, t.table_number, COALESCE(w.name, 'Unassigned') as waiter_name
                FROM waiter_calls wc
                JOIN tables t ON wc.table_id = t.id
                LEFT JOIN waiters w ON wc.waiter_id = w.id
                WHERE 1=1
            """
            params = []

            if hotel_id:
                query += " AND wc.hotel_id = %s"
                params.append(hotel_id)
            if status_filter:
                query += " AND wc.status = %s"
                params.append(status_filter)
            if waiter_filter:
                query += " AND wc.waiter_id = %s"
                params.append(waiter_filter)

            query += " ORDER BY wc.created_at DESC"
            cursor.execute(query, tuple(params))
            requests = cursor.fetchall()

            for req in requests:
                if req.get('created_at'):
                    req['created_at'] = req['created_at'].isoformat()
                if req.get('acknowledged_at'):
                    req['acknowledged_at'] = req['acknowledged_at'].isoformat()
                if req.get('completed_at'):
                    req['completed_at'] = req['completed_at'].isoformat()

            cursor.close()
            connection.close()
            return requests

        except Error as e:
            print(f"[WAITER_CALL ERROR] get_all_requests: {e}")
            return []
