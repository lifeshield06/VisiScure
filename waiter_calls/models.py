"""
Waiter Call Service - Backend logic for Hokitoki-Style Waiter Call System

This module handles assistance request creation, retrieval, and status management
with spam prevention, authorization, and proper error handling.
"""

from database.db import get_db_connection
from mysql.connector import Error
from datetime import datetime


class WaiterCallService:
    """Service layer for managing waiter assistance requests"""
    
    @staticmethod
    def create_request(table_id, session_id=None, guest_name=None):
        """
        Create waiter assistance requests for ALL waiters assigned to the table
        
        Args:
            table_id: ID of the table making the request
            session_id: Guest session identifier (optional)
            guest_name: Name of the guest (optional)
            
        Returns:
            dict: {success: bool, message: str, request_ids: list, notified_waiters: list}
        """
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Get table info and ALL waiter assignments from waiter_table_assignments mapping table
            cursor.execute(
                """SELECT t.id, t.hotel_id, wta.waiter_id
                   FROM tables t
                   INNER JOIN waiter_table_assignments wta ON t.id = wta.table_id
                   WHERE t.id = %s""",
                (table_id,)
            )
            table_waiters = cursor.fetchall()
            
            if not table_waiters or len(table_waiters) == 0:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'No waiter assigned to this table'}
            
            # Check for recent request (10-second cooldown to prevent spam)
            cursor.execute(
                """SELECT id, created_at FROM waiter_calls 
                   WHERE table_id = %s 
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
            
            # Create new request for EACH assigned waiter
            request_ids = []
            notified_waiters = []
            hotel_id = table_waiters[0]['hotel_id']
            
            for table_waiter in table_waiters:
                waiter_id = table_waiter['waiter_id']
                
                cursor.execute(
                    """INSERT INTO waiter_calls 
                       (hotel_id, table_id, waiter_id, session_id, guest_name, status, created_at)
                       VALUES (%s, %s, %s, %s, %s, 'PENDING', NOW())""",
                    (hotel_id, table_id, waiter_id, session_id, guest_name)
                )
                
                request_id = cursor.lastrowid
                request_ids.append(request_id)
                notified_waiters.append(waiter_id)
                
                print(f"[WAITER_CALL] Created request {request_id} for table {table_id}, waiter {waiter_id}")
            
            connection.commit()
            cursor.close()
            connection.close()
            
            waiter_count = len(notified_waiters)
            message = f'Waiter notified successfully' if waiter_count == 1 else f'{waiter_count} waiters notified successfully'
            
            print(f"[WAITER_CALL] Created {len(request_ids)} requests for table {table_id}, notified waiters: {notified_waiters}")
            
            return {
                'success': True,
                'message': message,
                'request_ids': request_ids,
                'notified_waiters': notified_waiters,
                'waiter_count': waiter_count
            }
            
        except Error as e:
            print(f"[WAITER_CALL ERROR] create_request: {e}")
            return {'success': False, 'message': f'Database error: {str(e)}'}
    
    @staticmethod
    def get_pending_requests(waiter_id):
        """
        Get all pending assistance requests for a waiter
        
        Args:
            waiter_id: ID of the waiter
            
        Returns:
            list: Array of pending request dictionaries
        """
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute(
                """SELECT wc.*, t.table_number, w.name as waiter_name
                   FROM waiter_calls wc
                   JOIN tables t ON wc.table_id = t.id
                   JOIN waiters w ON wc.waiter_id = w.id
                   WHERE wc.waiter_id = %s AND wc.status = 'PENDING'
                   ORDER BY wc.created_at ASC""",
                (waiter_id,)
            )
            
            requests = cursor.fetchall()
            
            # Convert datetime objects to ISO format strings for JSON serialization
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
        """
        Mark an assistance request as acknowledged
        
        Args:
            request_id: ID of the request
            waiter_id: ID of the waiter acknowledging
            
        Returns:
            dict: {success: bool, message: str, acknowledged_at: str}
        """
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Verify request exists and belongs to waiter
            cursor.execute(
                "SELECT id, status, waiter_id FROM waiter_calls WHERE id = %s",
                (request_id,)
            )
            request = cursor.fetchone()
            
            if not request:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Request not found'}
            
            if request['waiter_id'] != waiter_id:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Unauthorized: Request belongs to another waiter'}
            
            if request['status'] != 'PENDING':
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Request already acknowledged or completed'}
            
            # Update request status
            cursor.execute(
                "UPDATE waiter_calls SET status = 'ACKNOWLEDGED', acknowledged_at = NOW() WHERE id = %s",
                (request_id,)
            )
            
            connection.commit()
            
            # Get the acknowledged_at timestamp
            cursor.execute("SELECT acknowledged_at FROM waiter_calls WHERE id = %s", (request_id,))
            result = cursor.fetchone()
            acknowledged_at = result['acknowledged_at'].isoformat() if result and result['acknowledged_at'] else None
            
            cursor.close()
            connection.close()
            
            print(f"[WAITER_CALL] Request {request_id} acknowledged by waiter {waiter_id}")
            
            return {
                'success': True,
                'message': 'Request acknowledged',
                'acknowledged_at': acknowledged_at
            }
            
        except Error as e:
            print(f"[WAITER_CALL ERROR] acknowledge_request: {e}")
            return {'success': False, 'message': f'Database error: {str(e)}'}
    
    @staticmethod
    def complete_request(request_id, waiter_id):
        """
        Mark an assistance request as completed
        
        Args:
            request_id: ID of the request
            waiter_id: ID of the waiter completing
            
        Returns:
            dict: {success: bool, message: str, completed_at: str}
        """
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Verify request exists and belongs to waiter
            cursor.execute(
                "SELECT id, status, waiter_id FROM waiter_calls WHERE id = %s",
                (request_id,)
            )
            request = cursor.fetchone()
            
            if not request:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Request not found'}
            
            if request['waiter_id'] != waiter_id:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Unauthorized: Request belongs to another waiter'}
            
            if request['status'] == 'COMPLETED':
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Request already completed'}
            
            # Update request status to COMPLETED
            # If request was never acknowledged, set acknowledged_at as well
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
            
            # Get the completed_at timestamp
            cursor.execute("SELECT completed_at FROM waiter_calls WHERE id = %s", (request_id,))
            result = cursor.fetchone()
            completed_at = result['completed_at'].isoformat() if result and result['completed_at'] else None
            
            cursor.close()
            connection.close()
            
            print(f"[WAITER_CALL] Request {request_id} completed by waiter {waiter_id}")
            
            return {
                'success': True,
                'message': 'Request completed',
                'completed_at': completed_at
            }
            
        except Error as e:
            print(f"[WAITER_CALL ERROR] complete_request: {e}")
            return {'success': False, 'message': f'Database error: {str(e)}'}
    
    @staticmethod
    def check_existing_request(table_id):
        """
        Check if table has an existing pending request
        
        Args:
            table_id: ID of the table
            
        Returns:
            dict: {has_pending: bool, request_id: int, created_at: str}
        """
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
            
            # Calculate time elapsed
            if request['created_at']:
                time_elapsed = (datetime.now() - request['created_at']).total_seconds()
            else:
                time_elapsed = 0
            
            return {
                'has_pending': True,
                'request_id': request['id'],
                'created_at': request['created_at'].isoformat() if request['created_at'] else None,
                'time_elapsed_seconds': int(time_elapsed),
                'message': 'Waiter already notified'
            }
            
        except Error as e:
            print(f"[WAITER_CALL ERROR] check_existing_request: {e}")
            return {'has_pending': False, 'message': 'Error checking request'}
    
    @staticmethod
    def get_all_requests(hotel_id=None, status_filter=None, waiter_filter=None):
        """
        Get all assistance requests (for manager dashboard)
        
        Args:
            hotel_id: Filter by hotel ID (optional)
            status_filter: Filter by status (optional)
            waiter_filter: Filter by waiter ID (optional)
            
        Returns:
            list: Array of request dictionaries
        """
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            query = """
                SELECT wc.*, t.table_number, w.name as waiter_name
                FROM waiter_calls wc
                JOIN tables t ON wc.table_id = t.id
                JOIN waiters w ON wc.waiter_id = w.id
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
            
            # Convert datetime objects to ISO format strings
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
