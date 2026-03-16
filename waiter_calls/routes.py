"""
Waiter Call API Routes - REST endpoints for Hokitoki-Style Waiter Call System

Provides endpoints for creating, retrieving, and managing waiter assistance requests.
"""

from flask import request, jsonify, session
from . import waiter_calls_bp
from .models import WaiterCallService
from .voice_service import VoiceService


@waiter_calls_bp.route('/create', methods=['POST'])
def create_call():
    """
    Create a new waiter assistance request
    
    POST /api/waiter-calls/create
    Body: {table_id: int, session_id: str, guest_name: str}
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        table_id = data.get('table_id')
        session_id = data.get('session_id')
        guest_name = data.get('guest_name')
        
        # Validate required fields
        if not table_id:
            return jsonify({'success': False, 'message': 'table_id is required'}), 400
        
        # Validate table_id is positive integer
        try:
            table_id = int(table_id)
            if table_id <= 0:
                return jsonify({'success': False, 'message': 'table_id must be positive'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'table_id must be an integer'}), 400
        
        # Validate guest_name length if provided
        if guest_name and len(guest_name) > 100:
            return jsonify({'success': False, 'message': 'guest_name too long (max 100 chars)'}), 400
        
        # Validate session_id length if provided
        if session_id and len(session_id) > 255:
            return jsonify({'success': False, 'message': 'session_id too long (max 255 chars)'}), 400
        
        result = WaiterCallService.create_request(table_id, session_id, guest_name)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        print(f"[WAITER_CALL API ERROR] create_call: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@waiter_calls_bp.route('/pending', methods=['GET'])
def get_pending():
    """
    Get pending assistance requests for logged-in waiter
    
    GET /api/waiter-calls/pending
    Requires: waiter session
    """
    try:
        # Check waiter authentication
        waiter_id = session.get('waiter_id')
        
        if not waiter_id:
            return jsonify({'success': False, 'message': 'Unauthorized: Waiter not logged in'}), 401
        
        requests = WaiterCallService.get_pending_requests(waiter_id)
        
        return jsonify({
            'success': True,
            'requests': requests,
            'count': len(requests)
        }), 200
        
    except Exception as e:
        print(f"[WAITER_CALL API ERROR] get_pending: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@waiter_calls_bp.route('/acknowledge', methods=['POST'])
def acknowledge():
    """
    Acknowledge an assistance request
    
    POST /api/waiter-calls/acknowledge
    Body: {request_id: int}
    Requires: waiter session
    """
    try:
        # Check waiter authentication
        waiter_id = session.get('waiter_id')
        
        if not waiter_id:
            return jsonify({'success': False, 'message': 'Unauthorized: Waiter not logged in'}), 401
        
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
        print(f"[WAITER_CALL API ERROR] acknowledge: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@waiter_calls_bp.route('/complete', methods=['POST'])
def complete():
    """
    Mark an assistance request as completed
    
    POST /api/waiter-calls/complete
    Body: {request_id: int}
    Requires: waiter session
    """
    try:
        # Check waiter authentication
        waiter_id = session.get('waiter_id')
        
        if not waiter_id:
            return jsonify({'success': False, 'message': 'Unauthorized: Waiter not logged in'}), 401
        
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
        print(f"[WAITER_CALL API ERROR] complete: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@waiter_calls_bp.route('/status', methods=['GET'])
def check_status():
    """
    Check if table has pending request
    
    GET /api/waiter-calls/status?table_id=<id>
    """
    try:
        table_id = request.args.get('table_id')
        
        if not table_id:
            return jsonify({'success': False, 'message': 'table_id is required'}), 400
        
        # Validate table_id is positive integer
        try:
            table_id = int(table_id)
            if table_id <= 0:
                return jsonify({'success': False, 'message': 'table_id must be positive'}), 400
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'table_id must be an integer'}), 400
        
        result = WaiterCallService.check_existing_request(table_id)
        
        return jsonify(result), 200
        
    except Exception as e:
        print(f"[WAITER_CALL API ERROR] check_status: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@waiter_calls_bp.route('/all', methods=['GET'])
def get_all():
    """
    Get all assistance requests (for manager dashboard)
    
    GET /api/waiter-calls/all?status=<status>&waiter_id=<id>
    Requires: manager session
    """
    try:
        # Check manager authentication
        manager_id = session.get('manager_id')
        hotel_id = session.get('hotel_id')
        
        if not manager_id:
            return jsonify({'success': False, 'message': 'Unauthorized: Manager not logged in'}), 401
        
        # Get filter parameters
        status_filter = request.args.get('status')
        waiter_filter = request.args.get('waiter_id')
        
        # Validate waiter_id if provided
        if waiter_filter:
            try:
                waiter_filter = int(waiter_filter)
            except (ValueError, TypeError):
                return jsonify({'success': False, 'message': 'waiter_id must be an integer'}), 400
        
        requests = WaiterCallService.get_all_requests(hotel_id, status_filter, waiter_filter)
        
        return jsonify({
            'success': True,
            'requests': requests,
            'count': len(requests)
        }), 200
        
    except Exception as e:
        print(f"[WAITER_CALL API ERROR] get_all: {e}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500



@waiter_calls_bp.route('/generate-voice/<int:request_id>', methods=['GET'])
def generate_voice(request_id):
    """
    Generate voice announcement for a specific waiter call request
    
    GET /api/waiter-calls/generate-voice/<request_id>
    Returns: {success: bool, voice_url: str}
    """
    try:
        # Get the request details to extract table number
        from .models import WaiterCallService
        from database.db import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT wc.id, t.table_number
            FROM waiter_calls wc
            JOIN tables t ON wc.table_id = t.id
            WHERE wc.id = %s
        """, (request_id,))
        
        call_request = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not call_request:
            return jsonify({
                'success': False,
                'message': 'Request not found'
            }), 404
        
        # Generate voice file
        result = VoiceService.generate_voice_file(
            table_number=call_request['table_number'],
            request_id=request_id
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'voice_url': f"/static/{result['filename']}",
                'message': result['message']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 500
            
    except Exception as e:
        print(f"[WAITER_CALL API ERROR] generate_voice: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500


@waiter_calls_bp.route('/voice/<int:table_number>', methods=['GET'])
def get_voice_for_table(table_number):
    """
    Generate voice announcement for a table number (quick generation)
    
    GET /api/waiter-calls/voice/<table_number>
    Returns: {success: bool, voice_url: str}
    """
    try:
        # Validate table_number
        if table_number <= 0:
            return jsonify({
                'success': False,
                'message': 'Invalid table number'
            }), 400
        
        # Generate voice file
        result = VoiceService.generate_voice_file(table_number=table_number)
        
        if result['success']:
            return jsonify({
                'success': True,
                'voice_url': f"/static/{result['filename']}",
                'message': result['message']
            }), 200
        else:
            return jsonify({
                'success': False,
                'message': result['message']
            }), 500
            
    except Exception as e:
        print(f"[WAITER_CALL API ERROR] get_voice_for_table: {e}")
        return jsonify({
            'success': False,
            'message': 'Internal server error'
        }), 500
