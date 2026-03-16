from flask import request, jsonify, session
from . import wallet_bp
from .models import HotelWallet
from database.db import get_db_connection

# Import Razorpay client from payment module
try:
    from payment.razorpay_client import get_razorpay_client
    razorpay_service = get_razorpay_client()
    RAZORPAY_ENABLED = razorpay_service.is_enabled
    RAZORPAY_KEY_ID = razorpay_service.key_id if RAZORPAY_ENABLED else ""
except ImportError as e:
    print(f"[WALLET] Could not import Razorpay client: {e}")
    razorpay_service = None
    RAZORPAY_ENABLED = False
    RAZORPAY_KEY_ID = ""
except Exception as e:
    print(f"[WALLET] Razorpay initialization error: {e}")
    razorpay_service = None
    RAZORPAY_ENABLED = False
    RAZORPAY_KEY_ID = ""

# Initialize tables on import
HotelWallet.create_tables()


def log_wallet_activity(activity_type, message, hotel_id=None, role='manager'):
    """Log wallet-related activity with role and hotel_id"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Ensure role column exists
        try:
            cursor.execute("SHOW COLUMNS FROM recent_activities LIKE 'role'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE recent_activities ADD COLUMN role VARCHAR(20) DEFAULT 'manager'")
                conn.commit()
                print("[WALLET] Added 'role' column to recent_activities")
        except Exception as col_err:
            print(f"[WALLET] Column check error: {col_err}")
        
        cursor.execute(
            "INSERT INTO recent_activities (activity_type, message, hotel_id, role) VALUES (%s, %s, %s, %s)",
            (activity_type, message, hotel_id, role)
        )
        conn.commit()
        
        # Debug: Verify the insert
        cursor.execute("SELECT id, activity_type, message, hotel_id, role FROM recent_activities ORDER BY id DESC LIMIT 1")
        inserted = cursor.fetchone()
        print(f"[WALLET ACTIVITY LOGGED] id={inserted[0]}, type={inserted[1]}, hotel_id={inserted[3]}, role={inserted[4]}")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[WALLET ACTIVITY ERROR] Failed to log activity: {e}")
        import traceback
        traceback.print_exc()


@wallet_bp.route('/api/balance/<int:hotel_id>', methods=['GET'])
def get_balance(hotel_id):
    """Get wallet balance and details for a hotel"""
    # Check if admin or manager of this hotel
    admin_id = session.get('admin_id')
    manager_hotel_id = session.get('hotel_id')
    
    if not admin_id and int(manager_hotel_id or 0) != hotel_id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    # Use get_or_create_wallet to auto-create if not exists
    wallet = HotelWallet.get_or_create_wallet(hotel_id)
    if wallet:
        return jsonify({'success': True, 'wallet': wallet})
    return jsonify({'success': False, 'message': 'Could not retrieve or create wallet'})


@wallet_bp.route('/api/add-balance', methods=['POST'])
def add_balance():
    """Add balance to hotel wallet (Admin or Manager) - requires UTR number"""
    try:
        data = request.json
        hotel_id = int(data.get('hotel_id', 0))
        amount = float(data.get('amount', 0))
        utr_number = data.get('utr_number', '').strip()
        
        if not hotel_id:
            return jsonify({'success': False, 'message': 'Hotel ID is required'})
        
        if amount <= 0:
            return jsonify({'success': False, 'message': 'Amount must be greater than 0'})
        
        if not utr_number:
            return jsonify({'success': False, 'message': 'UTR Number is required'})
        
        # Determine who is adding balance
        admin_id = session.get('admin_id')
        manager_id = session.get('manager_id')
        manager_hotel_id = session.get('hotel_id')
        
        if admin_id:
            created_by_type = 'ADMIN'
            created_by_id = admin_id
        elif manager_id and int(manager_hotel_id or 0) == hotel_id:
            created_by_type = 'MANAGER'
            created_by_id = manager_id
        else:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
        result = HotelWallet.add_balance(hotel_id, amount, utr_number, created_by_type, created_by_id)
        
        # Log activity on success
        if result.get('success'):
            if admin_id:
                # Admin action - log without hotel_id for admin dashboard
                log_wallet_activity('wallet', f"Balance ₹{amount:.0f} added to hotel wallet (UTR: {utr_number})", None, role='admin')
            else:
                # Manager action - log with hotel_id for manager dashboard
                # Ensure hotel_id is an integer for proper DB storage
                log_hotel_id = int(manager_hotel_id) if manager_hotel_id else hotel_id
                print(f"[WALLET DEBUG] Logging manager activity - hotel_id={log_hotel_id}, role=manager")
                log_wallet_activity('wallet', f"Wallet balance increased by ₹{amount:.0f} (UTR: {utr_number})", log_hotel_id, role='manager')
        
        return jsonify(result)
    except Exception as e:
        print(f"Error in add_balance route: {e}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'})


@wallet_bp.route('/api/all-wallets', methods=['GET'])
def get_all_wallets():
    """Get all hotel wallets (Admin only)"""
    if 'admin_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    wallets = HotelWallet.get_all_wallets()
    return jsonify({'success': True, 'wallets': wallets})


@wallet_bp.route('/api/transactions/<int:hotel_id>', methods=['GET'])
def get_transactions(hotel_id):
    """Get transaction history for a hotel"""
    # Check authorization
    admin_id = session.get('admin_id')
    manager_hotel_id = session.get('hotel_id')
    
    if not admin_id and int(manager_hotel_id or 0) != hotel_id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    limit = request.args.get('limit', 50, type=int)
    transactions = HotelWallet.get_transactions(hotel_id, limit)
    return jsonify({'success': True, 'transactions': transactions})


@wallet_bp.route('/api/update-charges', methods=['POST'])
def update_charges():
    """Update hotel charges (Admin only)"""
    if 'admin_id' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    try:
        data = request.json
        hotel_id = int(data.get('hotel_id', 0))
        per_verification_charge = float(data.get('per_verification_charge', 0))
        per_order_charge = float(data.get('per_order_charge', 0))
        
        if not hotel_id:
            return jsonify({'success': False, 'message': 'Hotel ID is required'})
        
        result = HotelWallet.update_charges(hotel_id, per_verification_charge, per_order_charge)
        
        # Log admin activity on success
        if result.get('success'):
            log_wallet_activity('wallet', f"Hotel charges updated (₹{per_verification_charge}/verify, ₹{per_order_charge}/order)", None)
        
        return jsonify(result)
    except Exception as e:
        print(f"Error in update_charges route: {e}")
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'})


@wallet_bp.route('/api/check-verification-balance/<int:hotel_id>', methods=['GET'])
def check_verification_balance(hotel_id):
    """Check if hotel has sufficient balance for verification"""
    result = HotelWallet.check_balance_for_verification(hotel_id)
    return jsonify(result)


@wallet_bp.route('/api/check-order-balance/<int:hotel_id>', methods=['GET'])
def check_order_balance(hotel_id):
    """Check if hotel has sufficient balance for order"""
    result = HotelWallet.check_balance_for_order(hotel_id)
    return jsonify(result)


# ================================
# RAZORPAY PAYMENT INTEGRATION
# ================================

@wallet_bp.route('/api/razorpay/config', methods=['GET'])
def get_razorpay_config():
    """Get Razorpay configuration for frontend"""
    config = razorpay_service.get_config()
    return jsonify({
        'success': True,
        'enabled': config['enabled'],
        'key_id': config['key_id']
    })


@wallet_bp.route('/api/razorpay/create-order', methods=['POST'])
def create_razorpay_order():
    """Create a Razorpay order for wallet recharge"""
    if not RAZORPAY_ENABLED:
        return jsonify({'success': False, 'message': 'Razorpay is not configured'}), 400
    
    try:
        data = request.json
        hotel_id = int(data.get('hotel_id', 0))
        amount = float(data.get('amount', 0))
        
        if not hotel_id:
            return jsonify({'success': False, 'message': 'Hotel ID is required'})
        
        if amount <= 0:
            return jsonify({'success': False, 'message': 'Amount must be greater than 0'})
        
        # Check authorization
        admin_id = session.get('admin_id')
        manager_id = session.get('manager_id')
        manager_hotel_id = session.get('hotel_id')
        
        if not admin_id and not (manager_id and int(manager_hotel_id or 0) == hotel_id):
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
        # Get hotel name for order notes
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT hotel_name FROM hotels WHERE id = %s", (hotel_id,))
        hotel = cursor.fetchone()
        cursor.close()
        conn.close()
        
        hotel_name = hotel['hotel_name'] if hotel else f"Hotel {hotel_id}"
        
        # Create Razorpay order using service
        notes = {
            'hotel_id': str(hotel_id),
            'hotel_name': hotel_name,
            'purpose': 'Wallet Recharge'
        }
        
        result = razorpay_service.create_order(amount, notes=notes)
        
        if not result['success']:
            return jsonify(result)
        
        return jsonify({
            'success': True,
            'order_id': result['order_id'],
            'amount': amount,
            'currency': 'INR',
            'key_id': result['key_id']
        })
        
    except Exception as e:
        print(f"Error creating Razorpay order: {e}")
        return jsonify({'success': False, 'message': f'Error creating order: {str(e)}'})


@wallet_bp.route('/api/razorpay/verify-payment', methods=['POST'])
def verify_razorpay_payment():
    """Verify Razorpay payment and credit wallet"""
    if not RAZORPAY_ENABLED:
        return jsonify({'success': False, 'message': 'Razorpay is not configured'}), 400
    
    try:
        data = request.json
        hotel_id = int(data.get('hotel_id', 0))
        amount = float(data.get('amount', 0))
        razorpay_payment_id = data.get('razorpay_payment_id', '')
        razorpay_order_id = data.get('razorpay_order_id', '')
        razorpay_signature = data.get('razorpay_signature', '')
        
        if not all([hotel_id, amount, razorpay_payment_id, razorpay_order_id, razorpay_signature]):
            return jsonify({'success': False, 'message': 'Missing required payment details'})
        
        # Verify signature using service
        is_valid = razorpay_service.verify_payment_signature(
            razorpay_order_id, razorpay_payment_id, razorpay_signature
        )
        
        if not is_valid:
            print(f"[RAZORPAY] Signature verification failed for order {razorpay_order_id}")
            return jsonify({'success': False, 'message': 'Payment verification failed - invalid signature'})
        
        # Check authorization
        admin_id = session.get('admin_id')
        manager_id = session.get('manager_id')
        manager_hotel_id = session.get('hotel_id')
        
        if admin_id:
            created_by_type = 'ADMIN'
            created_by_id = admin_id
        elif manager_id and int(manager_hotel_id or 0) == hotel_id:
            created_by_type = 'MANAGER'
            created_by_id = manager_id
        else:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 401
        
        # Add balance via Razorpay
        result = HotelWallet.add_balance_razorpay(
            hotel_id, amount, razorpay_payment_id, razorpay_order_id,
            created_by_type, created_by_id
        )
        
        # Log activity on success
        if result.get('success'):
            if admin_id:
                log_wallet_activity('wallet', f"Balance ₹{amount:.0f} added via Razorpay (Pay ID: {razorpay_payment_id[:12]}...)", None, role='admin')
            else:
                log_hotel_id = int(manager_hotel_id) if manager_hotel_id else hotel_id
                log_wallet_activity('wallet', f"Wallet recharged ₹{amount:.0f} via Razorpay", log_hotel_id, role='manager')
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error verifying Razorpay payment: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error verifying payment: {str(e)}'})

