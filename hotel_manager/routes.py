from flask import request, jsonify, session, render_template, send_file
from . import hotel_manager_bp
from .models import HotelManager, Waiter, DashboardStats, DailySpecialMenu, DailySpecialSettings
from wallet.models import HotelWallet
from database.db import get_db_connection
import qrcode
import io
import base64
from urllib.parse import urlencode
from datetime import datetime, timedelta

# Initialize Daily Special Menu table
DailySpecialMenu.create_table()
DailySpecialSettings.create_table()

# =========================
# ACTIVITY LOGGING FOR MANAGERS
# =========================

def ensure_hotel_id_column():
    """Ensure recent_activities table has hotel_id and role columns"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check and add hotel_id column
        cursor.execute("SHOW COLUMNS FROM recent_activities LIKE 'hotel_id'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE recent_activities ADD COLUMN hotel_id INT DEFAULT NULL")
            cursor.execute("CREATE INDEX idx_hotel_id ON recent_activities (hotel_id)")
            conn.commit()
            print("[MANAGER] Added 'hotel_id' column to recent_activities")
        
        # Check and add role column
        cursor.execute("SHOW COLUMNS FROM recent_activities LIKE 'role'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE recent_activities ADD COLUMN role VARCHAR(20) DEFAULT 'manager'")
            cursor.execute("CREATE INDEX idx_role ON recent_activities (role)")
            conn.commit()
            print("[MANAGER] Added 'role' column to recent_activities")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[MANAGER] Error ensuring columns: {e}")

def log_manager_activity(activity_type, message, hotel_id=None):
    """Log activity for manager dashboard with hotel_id and role='manager'"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert with role='manager'
        cursor.execute(
            "INSERT INTO recent_activities (activity_type, message, hotel_id, role) VALUES (%s, %s, %s, %s)",
            (activity_type, message, hotel_id, 'manager')
        )
        conn.commit()
        
        # Debug: Verify the insert
        cursor.execute("SELECT id, activity_type, hotel_id, role FROM recent_activities ORDER BY id DESC LIMIT 1")
        inserted = cursor.fetchone()
        print(f"[MANAGER ACTIVITY LOGGED] id={inserted[0]}, type={inserted[1]}, hotel_id={inserted[2]}, role={inserted[3]}")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[MANAGER ACTIVITY ERROR] Failed to log activity: {e}")
        import traceback
        traceback.print_exc()

# Ensure hotel_id column exists on module load
ensure_hotel_id_column()

@hotel_manager_bp.route('/login-page')
def login_page():
    return render_template('manager_login.html')

@hotel_manager_bp.route('/signup-page')
def signup_page():
    return render_template('manager_signup.html')

@hotel_manager_bp.route('/signup', methods=['POST'])
def signup():
    data = request.json
    print(f"Signup attempt - Username: {data.get('username')}, Email: {data.get('email')}")
    result = HotelManager.create_account(
        data.get('name'),
        data.get('email'),
        data.get('username'),
        data.get('password')
    )
    print(f"Signup result: {result}")
    return jsonify(result)

@hotel_manager_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    print(f"Login attempt - Username: {data.get('username')}")
    result = HotelManager.login(
        data.get('username'),
        data.get('password')
    )
    print(f"Login result: {result}")
    
    # Store session data if login successful
    if result.get('success'):
        session['manager_id'] = result.get('id')
        session['manager_name'] = result.get('name')
        session['hotel_id'] = result.get('hotel_id')
        session['hotel_name'] = result.get('hotel_name')
        session['kyc_enabled'] = result.get('kyc_enabled', False)
        session['food_enabled'] = result.get('food_enabled', False)
    
    return jsonify(result)

@hotel_manager_bp.route('/change-password', methods=['POST'])
def change_password():
    """Change manager password"""
    manager_id = session.get('manager_id')
    if not manager_id:
        return jsonify({'success': False, 'message': 'Not authorized. Please log in again.'}), 403
    
    data = request.json
    if not data:
        return jsonify({'success': False, 'message': 'No data received!'})
    
    current_password = data.get('current_password', '').strip()
    new_password = data.get('new_password', '').strip()
    confirm_password = data.get('confirm_password', '').strip()
    
    # Validation
    if not current_password or not new_password or not confirm_password:
        return jsonify({'success': False, 'message': 'All fields are required!'})
    
    if new_password != confirm_password:
        return jsonify({'success': False, 'message': 'New passwords do not match.'})
    
    if len(new_password) < 6:
        return jsonify({'success': False, 'message': 'Password must be at least 6 characters!'})
    
    print(f"[MANAGER CHANGE PASSWORD] Attempting password change for manager_id: {manager_id}")
    result = HotelManager.change_password(manager_id, current_password, new_password)
    print(f"[MANAGER CHANGE PASSWORD] Result: {result}")
    return jsonify(result)

@hotel_manager_bp.route('/dashboard')
def dashboard():
    # Check session-based auth first
    manager_id = session.get('manager_id') or request.args.get('id')
    manager_name = session.get('manager_name') or request.args.get('name')
    hotel_id = session.get('hotel_id')

    # Persist query fallback auth into session for downstream API calls.
    if manager_id and not session.get('manager_id'):
        session['manager_id'] = manager_id
    if manager_name and not session.get('manager_name'):
        session['manager_name'] = manager_name
    
    if not manager_id or not manager_name:
        return "Invalid access. Please login first.", 403
    
    # If hotel_id is not in session, fetch it from database
    if not hotel_id and manager_id:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT hma.hotel_id, hm.kyc_enabled, hm.food_enabled 
                FROM hotel_managers hma
                JOIN hotel_modules hm ON hma.hotel_id = hm.hotel_id
                WHERE hma.manager_id = %s
            """, (manager_id,))
            result = cursor.fetchone()
            if result:
                hotel_id = result[0]
                session['hotel_id'] = hotel_id
                session['kyc_enabled'] = bool(result[1]) if result[1] is not None else False
                session['food_enabled'] = bool(result[2]) if result[2] is not None else False
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error fetching hotel_id: {e}")
            import traceback
            traceback.print_exc()
    
    # Always fetch fresh hotel data (name and logo) on every dashboard load
    if hotel_id:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Fetch hotel name and logo
            cursor.execute("SELECT hotel_name, logo FROM hotels WHERE id = %s", (hotel_id,))
            hotel_result = cursor.fetchone()
            if hotel_result:
                session['hotel_name'] = hotel_result[0]
                session['hotel_logo'] = hotel_result[1]
            
            # Always refresh module flags to ensure they're up-to-date
            cursor.execute("""
                SELECT kyc_enabled, food_enabled 
                FROM hotel_modules 
                WHERE hotel_id = %s
            """, (hotel_id,))
            module_result = cursor.fetchone()
            if module_result:
                session['kyc_enabled'] = bool(module_result[0]) if module_result[0] is not None else False
                session['food_enabled'] = bool(module_result[1]) if module_result[1] is not None else False
            
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error fetching hotel data: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"[DEBUG] Dashboard loaded - manager_id={manager_id}, hotel_id={hotel_id}")
    
    if not hotel_id:
        return "Hotel not found for this manager. Please contact support.", 403
    
    # Get module flags from session (default to False if not set)
    kyc_enabled = session.get('kyc_enabled', False)
    food_enabled = session.get('food_enabled', False)
    hotel_name = session.get('hotel_name', '')
    hotel_logo = session.get('hotel_logo', None)
    
    # Get waiters for this hotel
    waiters = Waiter.get_waiters_by_hotel(hotel_id)
    waiters_count = len(waiters) if waiters else 0
    
    # Get dashboard statistics
    stats = DashboardStats.get_all_stats(hotel_id)

    # Fetch fresh wallet charges so dashboard always reflects latest admin settings
    wallet = HotelWallet.get_or_create_wallet(hotel_id)
    
    # Get total menu items count for this hotel
    total_menu_items = 0
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM menu_dishes WHERE hotel_id = %s",
            (hotel_id,)
        )
        result = cursor.fetchone()
        total_menu_items = result[0] if result else 0
        print(f"[DEBUG] Menu count for hotel_id={hotel_id}: {total_menu_items}")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error fetching menu items count: {e}")
        import traceback
        traceback.print_exc()
    
    return render_template('manager_dashboard.html', 
                         manager_id=manager_id, 
                         manager_name=manager_name,
                         hotel_id=hotel_id,
                         hotel_name=hotel_name,
                         hotel_logo=hotel_logo,
                         kyc_enabled=kyc_enabled,
                         food_enabled=food_enabled,
                         waiters_count=waiters_count,
                         stats=stats,
                         total_menu_items=total_menu_items,
                         wallet=wallet)

@hotel_manager_bp.route('/live-orders')
def live_orders_dashboard():
    """Manager dashboard for live table order tracking"""
    # Check session-based auth
    manager_id = session.get('manager_id')
    if not manager_id:
        return redirect('/hotel-manager/login-page')
    
    manager_name = session.get('manager_name', 'Manager')
    hotel_id = session.get('hotel_id')
    hotel_name = session.get('hotel_name', 'Hotel')
    
    # Check if food module is enabled
    food_enabled = session.get('food_enabled', False)
    if not food_enabled:
        return render_template('404.html', message='Food ordering module is not enabled for this hotel'), 404
    
    return render_template('manager/live_orders_dashboard.html',
                         manager_id=manager_id,
                         manager_name=manager_name,
                         hotel_id=hotel_id,
                         hotel_name=hotel_name)

@hotel_manager_bp.route('/waiters')
def waiters_section():
    """Serve the waiters section page"""
    # Check session-based auth first
    manager_id = session.get('manager_id')
    manager_name = session.get('manager_name')
    hotel_id = session.get('hotel_id')
    
    if not manager_id or not manager_name or not hotel_id:
        return "Invalid access. Please login first.", 403
    
    # Get module flags from session
    kyc_enabled = session.get('kyc_enabled', False)
    food_enabled = session.get('food_enabled', False)
    hotel_name = session.get('hotel_name', '')
    hotel_logo = session.get('hotel_logo', None)
    
    return render_template('manager/waiters_extracted.html',
                         manager_id=manager_id,
                         manager_name=manager_name,
                         hotel_id=hotel_id,
                         hotel_name=hotel_name,
                         hotel_logo=hotel_logo,
                         kyc_enabled=kyc_enabled,
                         food_enabled=food_enabled)

@hotel_manager_bp.route('/generate-waiter-qr')
def generate_waiter_qr():
    """Generate QR code for waiter login"""
    hotel_id = session.get('hotel_id')
    hotel_name = session.get('hotel_name', 'Hotel')
    
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    # Build the login URL with hotel info
    base_url = request.host_url.rstrip('/')
    params = urlencode({'hotel_id': hotel_id, 'hotel_name': hotel_name})
    login_url = f"{base_url}/waiter/login-page?{params}"
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(login_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64 for display
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return jsonify({
        'success': True,
        'qr_code': f"data:image/png;base64,{img_base64}",
        'login_url': login_url
    })

@hotel_manager_bp.route('/download-waiter-qr')
def download_waiter_qr():
    """Download QR code as PNG file"""
    hotel_id = session.get('hotel_id')
    hotel_name = session.get('hotel_name', 'Hotel')
    
    if not hotel_id:
        return "Not authorized", 403
    
    # Build the login URL
    base_url = request.host_url.rstrip('/')
    params = urlencode({'hotel_id': hotel_id, 'hotel_name': hotel_name})
    login_url = f"{base_url}/waiter/login-page?{params}"
    
    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(login_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    
    return send_file(buffer, mimetype='image/png', as_attachment=True, 
                    download_name=f'waiter_login_qr_{hotel_name}.png')

@hotel_manager_bp.route('/add-waiter', methods=['POST'])
def add_waiter():
    """Add a new waiter (QR-based login - no password required)"""
    data = request.json
    hotel_id = session.get('hotel_id')
    manager_id = session.get('manager_id')
    
    result = Waiter.create_waiter_qr(
        manager_id,
        data.get('name'),
        data.get('email'),
        data.get('phone'),
        hotel_id,
        data.get('table_ids', [])
    )
    
    # Log activity on success
    if result.get('success'):
        log_manager_activity('waiter', f"Waiter '{data.get('name')}' was added (ID: {result.get('waiter_id')})", hotel_id)
    
    return jsonify(result)

@hotel_manager_bp.route('/delete-waiter', methods=['POST'])
def delete_waiter():
    data = request.json
    hotel_id = session.get('hotel_id')
    result = Waiter.delete_waiter(
        data.get('waiter_id'),
        hotel_id
    )
    
    # Log activity on success
    if result.get('success'):
        log_manager_activity('waiter', f"Waiter (ID: {data.get('waiter_id')}) was removed", hotel_id)
    
    return jsonify(result)

@hotel_manager_bp.route('/api/waiter/<int:waiter_id>')
def get_waiter_details(waiter_id):
    """Get waiter details for editing"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    waiter = Waiter.get_waiter_by_id(waiter_id, hotel_id)
    if waiter:
        # Convert datetime to string
        if waiter.get('created_at'):
            waiter['created_at'] = str(waiter['created_at'])
        return jsonify({'success': True, 'waiter': waiter})
    return jsonify({'success': False, 'message': 'Waiter not found'})

@hotel_manager_bp.route('/update-waiter', methods=['POST'])
def update_waiter():
    """Update waiter details and table assignments"""
    data = request.json
    hotel_id = session.get('hotel_id')
    
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    waiter_id = data.get('waiter_id')
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    table_ids = data.get('table_ids', [])
    
    if not name or not email or not phone:
        return jsonify({'success': False, 'message': 'Name, email, and phone are required!'})
    
    result = Waiter.update_waiter(waiter_id, name, email, phone, table_ids, hotel_id)
    return jsonify(result)

@hotel_manager_bp.route('/toggle-waiter-status', methods=['POST'])
def toggle_waiter_status():
    data = request.json
    hotel_id = session.get('hotel_id')
    result = Waiter.toggle_waiter_status(
        data.get('waiter_id'),
        hotel_id
    )
    return jsonify(result)

@hotel_manager_bp.route('/reset-waiter-password', methods=['POST'])
def reset_waiter_password():
    data = request.json
    hotel_id = session.get('hotel_id')
    new_password = data.get('new_password')
    
    if not new_password or len(new_password) < 6:
        return jsonify({'success': False, 'message': 'Password must be at least 6 characters!'})
    
    result = Waiter.reset_waiter_password(
        data.get('waiter_id'),
        new_password,
        hotel_id
    )
    return jsonify(result)

@hotel_manager_bp.route('/assign-table', methods=['POST'])
def assign_table():
    data = request.json
    hotel_id = session.get('hotel_id')
    result = Waiter.assign_table_to_waiter(
        data.get('waiter_id'),
        data.get('table_id'),
        hotel_id
    )
    if result.get('success'):
        log_manager_activity('table', f"Table assigned to waiter", hotel_id)
    return jsonify(result)

@hotel_manager_bp.route('/unassign-table', methods=['POST'])
def unassign_table():
    data = request.json
    hotel_id = session.get('hotel_id')
    result = Waiter.unassign_table(data.get('table_id'), data.get('waiter_id'))
    if result.get('success'):
        log_manager_activity('table', f"Table unassigned from waiter", hotel_id)
    return jsonify(result)

@hotel_manager_bp.route('/update-table-waiters', methods=['POST'])
def update_table_waiters():
    """Update all waiter assignments for a specific table (supports multiple waiters)"""
    data = request.json
    hotel_id = session.get('hotel_id')
    
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    table_id = data.get('table_id')
    waiter_ids = data.get('waiter_ids', [])
    
    result = Waiter.update_table_waiters(table_id, waiter_ids, hotel_id)
    if result.get('success'):
        log_manager_activity('table', f"Table assignments updated", hotel_id)
    return jsonify(result)

@hotel_manager_bp.route('/api/tables-with-assignments')
def get_tables_with_assignments():
    hotel_id = session.get('hotel_id')
    
    if not hotel_id:
        return jsonify({'success': False, 'tables': [], 'message': 'No hotel_id in session'})
    
    tables = Waiter.get_tables_with_assignments(hotel_id)
    # Convert datetime objects to strings for JSON
    for table in tables:
        if table.get('created_at'):
            table['created_at'] = str(table['created_at'])
        if table.get('assigned_at'):
            table['assigned_at'] = str(table['assigned_at'])
    return jsonify({'success': True, 'tables': tables})

@hotel_manager_bp.route('/api/waiters')
def get_waiters_api():
    hotel_id = session.get('hotel_id')
    waiters = Waiter.get_waiters_by_hotel(hotel_id)
    waiters_list = []
    if waiters:
        for w in waiters:
            waiters_list.append({
                'waiter_id': w['waiter_id'],
                'name': w['name'],
                'email': w['email'],
                'phone': w['phone'],
                'is_active': bool(w['is_active']) if w['is_active'] is not None else True,
                'show_waiter_tips': bool(w['show_waiter_tips']) if w.get('show_waiter_tips') is not None else True,
                'created_at': str(w['created_at']) if w['created_at'] else None,
                'assigned_tables': w['assigned_tables'] or ''
            })
    return jsonify({'success': True, 'waiters': waiters_list})

@hotel_manager_bp.route('/api/recent-activities')
def get_recent_activities():
    """Get recent activities for the manager's hotel (last 3 days, max 5)"""
    hotel_id = session.get('hotel_id')
    
    if not hotel_id:
        print("[RECENT ACTIVITIES] No hotel_id in session")
        return jsonify([])
    
    # Ensure hotel_id is an integer for DB query
    hotel_id = int(hotel_id)
    print(f"[RECENT ACTIVITIES] Fetching for hotel_id={hotel_id}, role='manager'")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Clean old activities (older than 3 days)
        cursor.execute("DELETE FROM recent_activities WHERE created_at < NOW() - INTERVAL 3 DAY")
        conn.commit()
        
        # Debug: Check what activities exist for this hotel
        cursor.execute("""
            SELECT id, activity_type, message, hotel_id, role, created_at
            FROM recent_activities
            WHERE hotel_id = %s
            ORDER BY created_at DESC
            LIMIT 10
        """, (hotel_id,))
        debug_activities = cursor.fetchall()
        print(f"[RECENT ACTIVITIES DEBUG] Found {len(debug_activities)} activities for hotel_id={hotel_id}:")
        for act in debug_activities:
            print(f"  - id={act['id']}, type={act['activity_type']}, role={act.get('role')}, hotel_id={act['hotel_id']}")
        
        # Fetch activities for this hotel with role='manager' (last 3 days, limit 5)
        cursor.execute("""
            SELECT activity_type, message, created_at
            FROM recent_activities
            WHERE hotel_id = %s AND role = 'manager' AND created_at >= NOW() - INTERVAL 3 DAY
            ORDER BY created_at DESC
            LIMIT 5
        """, (hotel_id,))
        activities = cursor.fetchall()
        
        print(f"[RECENT ACTIVITIES] Returning {len(activities)} activities")
        
        # Format activities for JSON response
        formatted_activities = []
        for act in activities:
            formatted_activities.append({
                'activity_type': act['activity_type'],
                'message': act['message'],
                'created_at': act['created_at'].strftime("%Y-%m-%d %H:%M:%S") if act['created_at'] else None
            })
        
        cursor.close()
        conn.close()
        
        return jsonify(formatted_activities)
    except Exception as e:
        print(f"[RECENT ACTIVITIES ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify([])

@hotel_manager_bp.route('/api/all-activities')
def get_all_activities():
    """Get all activities for the manager's hotel (last 3 days, max 50)"""
    hotel_id = session.get('hotel_id')
    
    if not hotel_id:
        return jsonify([])
    
    # Ensure hotel_id is an integer for proper database matching
    hotel_id = int(hotel_id)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Clean old activities (older than 3 days)
        cursor.execute("DELETE FROM recent_activities WHERE created_at < NOW() - INTERVAL 3 DAY")
        conn.commit()
        
        # Fetch all activities for this hotel with role='manager' (last 3 days, limit 50)
        cursor.execute("""
            SELECT activity_type, message, created_at
            FROM recent_activities
            WHERE hotel_id = %s AND role = 'manager' AND created_at >= NOW() - INTERVAL 3 DAY
            ORDER BY created_at DESC
            LIMIT 50
        """, (hotel_id,))
        activities = cursor.fetchall()
        
        # Format activities for JSON response
        formatted_activities = []
        for act in activities:
            formatted_activities.append({
                'activity_type': act['activity_type'],
                'message': act['message'],
                'created_at': act['created_at'].strftime("%Y-%m-%d %H:%M:%S") if act['created_at'] else None
            })
        
        cursor.close()
        conn.close()
        
        return jsonify(formatted_activities)
    except Exception as e:
        return jsonify([])

@hotel_manager_bp.route('/all-managers')
def all_managers():
    managers = HotelManager.get_all_managers()
    
    managers_html = ""
    if managers:
        managers_html = "<table class='managers-table'>"
        managers_html += "<thead><tr><th>ID</th><th>Name</th><th>Email</th><th>Username</th><th>Created At</th></tr></thead>"
        managers_html += "<tbody>"
        for manager in managers:
            managers_html += f"<tr><td>{manager[0]}</td><td>{manager[1]}</td><td>{manager[2]}</td><td>{manager[3]}</td><td>{manager[4]}</td></tr>"
        managers_html += "</tbody></table>"
    else:
        managers_html = "<p class='no-data'>No managers found</p>"
    
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>All Managers - VisiScure Order</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f8fafc; min-height: 100vh; display: flex; flex-direction: column; }}
            
            .navbar {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1.5rem; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
            .navbar h1 {{ font-size: 1.8rem; }}
            
            .container {{ max-width: 1200px; margin: 2rem auto; padding: 0 2rem; width: 100%; flex: 1; }}
            
            .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem; }}
            .header h2 {{ color: #2d3748; font-size: 1.8rem; }}
            .back-btn {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 0.7rem 1.5rem; border-radius: 8px; cursor: pointer; font-weight: 600; transition: all 0.3s ease; text-decoration: none; display: inline-block; }}
            .back-btn:hover {{ transform: translateY(-2px); box-shadow: 0 6px 20px rgba(102, 126, 234, 0.3); }}
            
            .card {{ background: white; border-radius: 12px; padding: 2rem; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
            
            .managers-table {{ width: 100%; border-collapse: collapse; }}
            .managers-table thead {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
            .managers-table th {{ color: white; padding: 1.2rem; text-align: left; font-weight: 600; }}
            .managers-table td {{ padding: 1rem 1.2rem; border-bottom: 1px solid #e2e8f0; }}
            .managers-table tbody tr:hover {{ background: #f7fafc; }}
            .managers-table tbody tr:last-child td {{ border-bottom: none; }}
            
            .no-data {{ text-align: center; color: #718096; font-size: 1.1rem; padding: 2rem; }}
            
            .footer {{ background: linear-gradient(135deg, #2d3748 0%, #4a5568 100%); color: white; text-align: center; padding: 1.5rem; margin-top: auto; }}
            
            @media (max-width: 768px) {{
                .container {{ padding: 0 1rem; }}
                .header {{ flex-direction: column; gap: 1rem; }}
                .managers-table {{ font-size: 0.9rem; }}
                .managers-table th, .managers-table td {{ padding: 0.8rem 0.5rem; }}
            }}
        </style>
    </head>
    <body>
        <nav class="navbar">
            <h1>🍽️ VisiScure Order - Manager Credentials</h1>
        </nav>
        
        <div class="container">
            <div class="header">
                <h2>All Registered Managers</h2>
                <a href="/" class="back-btn">← Back to Home</a>
            </div>
            
            <div class="card">
                {managers_html}
            </div>
        </div>
        
        <footer class="footer">
            <p>&copy; 2026 VisiScure Order - All Rights Reserved</p>
        </footer>
    </body>
    </html>
    """


# ============== Daily Special Menu Routes ==============

import os
from werkzeug.utils import secure_filename

# Allowed image extensions
ALLOWED_SPECIAL_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

def allowed_special_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_SPECIAL_EXTENSIONS


def _parse_offer_datetime(value):
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace(' ', 'T'))
    except ValueError:
        return None


def _parse_special_offer_payload(payload_get, base_price):
    offer_type = (payload_get('offer_type') or '').strip().lower()
    offer_value_raw = (payload_get('offer_value') or '').strip()

    if not offer_type or offer_type == 'none':
        return {
            'is_offer_active': False,
            'offer_type': None,
            'offer_value': None,
            'offer_price': None,
            'discount_percent': None
        }, None

    if offer_type not in ('percentage', 'flat'):
        return None, 'Offer type must be Percentage or Flat Price'

    try:
        offer_value = float(offer_value_raw)
    except (TypeError, ValueError):
        return None, 'Offer value must be a valid number'

    if offer_value <= 0:
        return None, 'Offer value must be greater than 0'

    if offer_type == 'percentage':
        if offer_value > 100:
            return None, 'Percentage offer cannot exceed 100'
        return {
            'is_offer_active': True,
            'offer_type': 'percentage',
            'offer_value': offer_value,
            'offer_price': None,
            'discount_percent': offer_value
        }, None

    # Flat amount off
    if offer_value >= float(base_price):
        return None, 'Flat offer must be less than base price'

    return {
        'is_offer_active': True,
        'offer_type': 'flat',
        'offer_value': offer_value,
        'offer_price': float(base_price) - offer_value,
        'discount_percent': None
    }, None


def _apply_menu_offer_sync(hotel_id, specials):
    """If special has no own offer, inherit active menu-dish offer by matching name."""
    if not specials:
        return specials

    names = sorted({str((s.get('dish_name') or s.get('menu_name') or '')).strip().lower() for s in specials if (s.get('dish_name') or s.get('menu_name'))})
    if not names:
        return specials

    conn = None
    cursor = None
    menu_offer_map = {}
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        placeholders = ','.join(['%s'] * len(names))
        query = f"""
            SELECT name, COALESCE(is_offer_active, 0) AS is_offer_active,
                   offer_price, discount_percent, offer_start, offer_end
            FROM menu_dishes
            WHERE hotel_id = %s
              AND COALESCE(is_active, 1) = 1
              AND LOWER(name) IN ({placeholders})
        """
        cursor.execute(query, [hotel_id] + names)
        rows = cursor.fetchall() or []

        now = datetime.now()
        for row in rows:
            if not int(row.get('is_offer_active') or 0):
                continue
            start_dt = _parse_offer_datetime(row.get('offer_start'))
            end_dt = _parse_offer_datetime(row.get('offer_end'))
            if not start_dt or not end_dt or not (start_dt <= now <= end_dt):
                continue

            key = str(row.get('name') or '').strip().lower()
            if not key:
                continue

            menu_offer_map[key] = {
                'is_offer_active': 1,
                'offer_price': float(row['offer_price']) if row.get('offer_price') is not None else None,
                'discount_percent': float(row['discount_percent']) if row.get('discount_percent') is not None else None,
                'offer_type': 'percentage' if row.get('discount_percent') is not None else ('flat' if row.get('offer_price') is not None else None),
                'offer_source': 'menu'
            }
    except Exception as exc:
        print(f"[DAILY SPECIAL] menu offer sync error: {exc}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

    for special in specials:
        # Prefer explicit special-level offer if configured
        if int(special.get('is_offer_active') or 0):
            special['offer_source'] = 'special'
            continue

        key = str(special.get('dish_name') or special.get('menu_name') or '').strip().lower()
        synced = menu_offer_map.get(key)
        if not synced:
            continue

        special['is_offer_active'] = synced['is_offer_active']
        special['offer_price'] = synced['offer_price']
        special['discount_percent'] = synced['discount_percent']
        special['offer_type'] = synced['offer_type']
        if synced['offer_type'] == 'percentage':
            special['offer_value'] = synced['discount_percent']
        elif synced['offer_type'] == 'flat' and special.get('price') is not None and synced['offer_price'] is not None:
            special['offer_value'] = max(0.0, float(special['price']) - float(synced['offer_price']))
        else:
            special['offer_value'] = None
        special['offer_source'] = 'menu'

    return specials

@hotel_manager_bp.route('/api/daily-special', methods=['GET'])
def get_daily_special():
    """Get all today's specials for the manager's hotel"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    specials = DailySpecialMenu.get_today_specials(hotel_id)
    specials = _apply_menu_offer_sync(hotel_id, specials)
    # Convert Decimal to float for JSON serialization
    for special in specials:
        special['price'] = float(special['price'])
        special['special_date'] = str(special['special_date'])
        special['is_offer_active'] = int(special.get('is_offer_active') or 0)
        special['offer_type'] = (special.get('offer_type') or '').strip().lower()
        special['offer_value'] = float(special['offer_value']) if special.get('offer_value') is not None else None
        special['offer_price'] = float(special['offer_price']) if special.get('offer_price') is not None else None
        special['discount_percent'] = float(special['discount_percent']) if special.get('discount_percent') is not None else None
        # Add menu_name for backward compatibility
        special['menu_name'] = special.get('dish_name', '')
    
    # Also return single 'special' for backward compatibility
    single_special = specials[0] if specials else None
    
    return jsonify({'success': True, 'specials': specials, 'special': single_special})


@hotel_manager_bp.route('/api/daily-special', methods=['POST'])
def save_daily_special():
    """Add a new today's special or update existing one"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    # Handle both JSON and form data
    if request.content_type and 'multipart/form-data' in request.content_type:
        special_id = request.form.get('id')  # For updates
        menu_name = request.form.get('menu_name', '').strip() or request.form.get('dish_name', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price')
        image_file = request.files.get('image')
    else:
        data = request.json or {}
        special_id = data.get('id')  # For updates
        menu_name = data.get('menu_name', '').strip() or data.get('dish_name', '').strip()
        description = data.get('description', '').strip()
        price = data.get('price')
        image_file = None
    
    # Validation
    if not menu_name:
        return jsonify({'success': False, 'message': 'Dish name is required!'})
    if not price:
        return jsonify({'success': False, 'message': 'Price is required!'})
    
    try:
        price_float = float(price)
        if price_float <= 0:
            return jsonify({'success': False, 'message': 'Price must be greater than zero!'})
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid price format!'})

    if request.content_type and 'multipart/form-data' in request.content_type:
        offer_payload, offer_error = _parse_special_offer_payload(lambda key: request.form.get(key), price_float)
    else:
        offer_payload, offer_error = _parse_special_offer_payload(lambda key: data.get(key), price_float)

    if offer_error:
        return jsonify({'success': False, 'message': offer_error})
    
    # Handle image upload
    image_path = None
    if image_file and image_file.filename:
        if allowed_special_file(image_file.filename):
            # Create uploads directory if it doesn't exist
            upload_folder = os.path.join('static', 'uploads', 'specials')
            os.makedirs(upload_folder, exist_ok=True)
            
            # Generate unique filename
            import time
            timestamp = int(time.time())
            filename = secure_filename(image_file.filename)
            unique_filename = f"special_{hotel_id}_{timestamp}_{filename}"
            filepath = os.path.join(upload_folder, unique_filename)
            
            # Save the file
            image_file.save(filepath)
            image_path = f"/static/uploads/specials/{unique_filename}"
        else:
            return jsonify({'success': False, 'message': 'Invalid image format. Allowed: jpg, png, webp, gif'})
    
    # Update existing or add new
    if special_id:
        result = DailySpecialMenu.update_special(
            int(special_id), hotel_id, menu_name, description, price_float, image_path,
            offer_payload['is_offer_active'], offer_payload['offer_type'], offer_payload['offer_value'],
            offer_payload['offer_price'], offer_payload['discount_percent']
        )
        action = "updated"
    else:
        result = DailySpecialMenu.add_special(
            hotel_id, menu_name, description, price_float, image_path,
            offer_payload['is_offer_active'], offer_payload['offer_type'], offer_payload['offer_value'],
            offer_payload['offer_price'], offer_payload['discount_percent']
        )
        action = "added"
    
    # Log activity on success
    if result.get('success'):
        log_manager_activity('menu', f"Today's Special {action}: '{menu_name}' (₹{price_float})", hotel_id)
    
    return jsonify(result)


@hotel_manager_bp.route('/api/daily-special/upload-image', methods=['POST'])
def upload_special_image():
    """Upload image for today's special menu"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    if 'image' not in request.files:
        return jsonify({'success': False, 'message': 'No image file provided'})
    
    image_file = request.files['image']
    if not image_file.filename:
        return jsonify({'success': False, 'message': 'No image selected'})
    
    if not allowed_special_file(image_file.filename):
        return jsonify({'success': False, 'message': 'Invalid image format. Allowed: jpg, png, webp, gif'})
    
    # Create uploads directory if it doesn't exist
    upload_folder = os.path.join('static', 'uploads', 'specials')
    os.makedirs(upload_folder, exist_ok=True)
    
    # Generate unique filename
    import time
    timestamp = int(time.time())
    filename = secure_filename(image_file.filename)
    unique_filename = f"special_{hotel_id}_{timestamp}_{filename}"
    filepath = os.path.join(upload_folder, unique_filename)
    
    # Save the file
    image_file.save(filepath)
    image_path = f"/static/uploads/specials/{unique_filename}"
    
    # Update database
    result = DailySpecialMenu.update_special_image(hotel_id, image_path)
    if result['success']:
        result['image_path'] = image_path
    return jsonify(result)


@hotel_manager_bp.route('/api/daily-special/<int:special_id>', methods=['DELETE'])
def delete_specific_special(special_id):
    """Delete a specific today's special by ID"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    result = DailySpecialMenu.delete_special(special_id, hotel_id)
    
    # Log activity on success
    if result.get('success'):
        log_manager_activity('menu', f"Today's Special (ID: {special_id}) was removed", hotel_id)
    
    return jsonify(result)


@hotel_manager_bp.route('/api/daily-special', methods=['DELETE'])
def delete_daily_special():
    """Delete/deactivate all today's specials"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    result = DailySpecialMenu.delete_today_special(hotel_id)
    
    # Log activity on success
    if result.get('success'):
        log_manager_activity('menu', "All Today's Specials were removed", hotel_id)
    
    return jsonify(result)


@hotel_manager_bp.route('/api/daily-special-settings', methods=['GET'])
def get_daily_special_settings():
    """Get persisted daily special popup settings for current hotel."""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403

    settings = DailySpecialSettings.get_settings(hotel_id)
    return jsonify({'success': True, 'settings': settings})


@hotel_manager_bp.route('/api/daily-special-settings', methods=['POST'])
def save_daily_special_settings():
    """Persist daily special popup settings for current hotel."""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403

    payload = request.json or {}
    result = DailySpecialSettings.upsert_settings(hotel_id, payload)

    if result.get('success'):
        settings = result.get('settings', {})
        log_manager_activity(
            'menu',
            (
                "Today's Special settings updated: "
                f"popup={'on' if settings.get('popup_enabled') else 'off'}, "
                f"reopen={settings.get('reopen_timer_seconds', 5)}s, "
                f"auto_slide={'on' if settings.get('auto_slide_enabled') else 'off'}, "
                f"slide_interval={settings.get('slide_interval_seconds', 3)}s, "
                f"initial_delay={settings.get('initial_delay_seconds', 2)}s"
            ),
            hotel_id
        )
        return jsonify({'success': True, 'message': 'Settings saved successfully', 'settings': settings})

    return jsonify(result), 400


# ============== Revenue Reports Routes ==============

@hotel_manager_bp.route('/api/revenue-reports', methods=['GET'])
def get_revenue_reports():
    """Get revenue reports data for the dashboard"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    from hotel_manager.models import RevenueReports
    
    summary = RevenueReports.get_revenue_summary(hotel_id)
    daily_data = RevenueReports.get_daily_revenue(hotel_id, days=30)
    
    return jsonify({
        'success': True,
        'summary': summary,
        'daily_revenue': daily_data
    })


# ============== GST Settings Routes ==============

@hotel_manager_bp.route('/api/gst-settings', methods=['GET'])
def get_gst_settings():
    """Get GST percentage for the manager's hotel"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT gst_percentage FROM hotels WHERE id = %s", (hotel_id,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if result:
            gst_percentage = float(result.get('gst_percentage', 5.0))
            return jsonify({'success': True, 'gst_percentage': gst_percentage})
        
        return jsonify({'success': True, 'gst_percentage': 5.0})  # Default
    except Exception as e:
        print(f"Error getting GST settings: {e}")
        return jsonify({'success': False, 'message': 'Server error'})


@hotel_manager_bp.route('/api/gst-settings', methods=['POST'])
def update_gst_settings():
    """Update GST percentage for the manager's hotel"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    data = request.json
    gst_percentage = data.get('gst_percentage')
    
    # Validation
    if gst_percentage is None:
        return jsonify({'success': False, 'message': 'GST percentage is required!'})
    
    try:
        gst_float = float(gst_percentage)
        
        if gst_float < 0:
            return jsonify({'success': False, 'message': 'GST percentage cannot be negative!'})
        
        if gst_float > 28:
            return jsonify({'success': False, 'message': 'GST percentage cannot exceed 28%!'})
        
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid GST percentage format!'})
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update GST percentage for this hotel
        cursor.execute(
            "UPDATE hotels SET gst_percentage = %s WHERE id = %s",
            (gst_float, hotel_id)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Log activity
        log_manager_activity('settings', f"GST percentage updated to {gst_float}%", hotel_id)
        
        return jsonify({
            'success': True, 
            'message': f'GST percentage updated to {gst_float}%',
            'gst_percentage': gst_float
        })
    except Exception as e:
        print(f"Error updating GST settings: {e}")
        return jsonify({'success': False, 'message': 'Server error'})


# ============== Category Tax Settings (CGST/SGST) ==============

@hotel_manager_bp.route('/api/category-tax-settings', methods=['GET'])
def get_category_tax_settings():
    """Get all categories with their CGST and SGST percentages"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, name, 
                   COALESCE(cgst_percentage, 2.50) as cgst_percentage, 
                   COALESCE(sgst_percentage, 2.50) as sgst_percentage
            FROM menu_categories 
            WHERE hotel_id = %s 
            ORDER BY name
        """, (hotel_id,))
        
        categories = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert Decimal to float for JSON
        for cat in categories:
            cat['cgst_percentage'] = float(cat['cgst_percentage'])
            cat['sgst_percentage'] = float(cat['sgst_percentage'])
        
        return jsonify({'success': True, 'categories': categories})
    except Exception as e:
        print(f"Error getting category tax settings: {e}")
        return jsonify({'success': False, 'message': 'Server error'})


@hotel_manager_bp.route('/api/category-tax-settings', methods=['POST'])
def update_category_tax_settings():
    """Update CGST and SGST percentages for a category"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    data = request.json
    category_id = data.get('category_id')
    cgst_percentage = data.get('cgst_percentage')
    sgst_percentage = data.get('sgst_percentage')
    
    # Validation
    if not category_id:
        return jsonify({'success': False, 'message': 'Category ID is required!'})
    
    try:
        cgst_float = float(cgst_percentage) if cgst_percentage is not None else 2.50
        sgst_float = float(sgst_percentage) if sgst_percentage is not None else 2.50
        
        if cgst_float < 0 or sgst_float < 0:
            return jsonify({'success': False, 'message': 'Tax percentage cannot be negative!'})
        
        if cgst_float > 14 or sgst_float > 14:
            return jsonify({'success': False, 'message': 'Individual tax percentage cannot exceed 14%!'})
        
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid tax percentage format!'})
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verify category belongs to this hotel
        cursor.execute("SELECT id, name FROM menu_categories WHERE id = %s AND hotel_id = %s", (category_id, hotel_id))
        category = cursor.fetchone()
        
        if not category:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Category not found!'})
        
        # Update tax percentages
        cursor.execute(
            "UPDATE menu_categories SET cgst_percentage = %s, sgst_percentage = %s WHERE id = %s AND hotel_id = %s",
            (cgst_float, sgst_float, category_id, hotel_id)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Log activity
        log_manager_activity('settings', f"Tax rates updated for category '{category[1]}': CGST {cgst_float}%, SGST {sgst_float}%", hotel_id)
        
        return jsonify({
            'success': True, 
            'message': f'Tax rates updated successfully',
            'cgst_percentage': cgst_float,
            'sgst_percentage': sgst_float
        })
    except Exception as e:
        print(f"Error updating category tax settings: {e}")
        return jsonify({'success': False, 'message': 'Server error'})


# ============== Waiter Call Voice Message Settings ==============

@hotel_manager_bp.route('/api/waiter-call-voice', methods=['GET'])
def get_waiter_call_voice():
    """Get waiter call voice message for the manager's hotel"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT waiter_call_voice FROM hotels WHERE id = %s", (hotel_id,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if result:
            voice_message = result.get('waiter_call_voice', 'Table {table} is calling waiter')
            return jsonify({'success': True, 'voice_message': voice_message})
        
        return jsonify({'success': True, 'voice_message': 'Table {table} is calling waiter'})  # Default
    except Exception as e:
        print(f"Error getting waiter call voice: {e}")
        return jsonify({'success': False, 'message': 'Server error'})


@hotel_manager_bp.route('/api/waiter-call-voice', methods=['POST'])
def update_waiter_call_voice():
    """Update waiter call voice message for the manager's hotel"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    data = request.json
    voice_message = data.get('voice_message', '').strip()
    
    # Validation
    if not voice_message:
        return jsonify({'success': False, 'message': 'Voice message is required!'})
    
    if len(voice_message) > 500:
        return jsonify({'success': False, 'message': 'Voice message is too long (max 500 characters)!'})
    
    if '{table}' not in voice_message:
        return jsonify({'success': False, 'message': 'Voice message must contain {table} placeholder!'})
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update voice message for this hotel
        cursor.execute(
            "UPDATE hotels SET waiter_call_voice = %s WHERE id = %s",
            (voice_message, hotel_id)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Log activity
        log_manager_activity('settings', f"Waiter call voice message updated", hotel_id)
        
        return jsonify({
            'success': True, 
            'message': 'Voice message updated successfully',
            'voice_message': voice_message
        })
    except Exception as e:
        print(f"Error updating waiter call voice: {e}")
        return jsonify({'success': False, 'message': 'Server error'})


# ============== Kitchen Management Routes ==============

from kitchen.models import KitchenAuth

@hotel_manager_bp.route('/api/kitchens', methods=['GET'])
def get_kitchens():
    """Get all kitchens for the manager's hotel"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    kitchens = KitchenAuth.get_all_kitchens(hotel_id)
    
    # Convert datetime to string for JSON
    for kitchen in kitchens:
        if kitchen.get('created_at'):
            kitchen['created_at'] = str(kitchen['created_at'])
    
    return jsonify({'success': True, 'kitchens': kitchens})


@hotel_manager_bp.route('/api/create-kitchen', methods=['POST'])
def create_kitchen():
    """Create a new kitchen with auto-generated ID"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    data = request.json
    section_name = data.get('section_name', '').strip()
    
    # Validation
    if not section_name:
        return jsonify({'success': False, 'message': 'Kitchen name is required!'})
    
    result = KitchenAuth.create_kitchen(hotel_id, section_name)
    
    # Log activity on success
    if result.get('success'):
        log_manager_activity('kitchen', f"Kitchen '{section_name}' was created (ID: {result.get('kitchen_unique_id')})", hotel_id)
    
    return jsonify(result)


@hotel_manager_bp.route('/api/kitchen/<int:kitchen_id>', methods=['GET'])
def get_kitchen_details(kitchen_id):
    """Get kitchen details for editing"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        # Get kitchen details
        cursor.execute("""
            SELECT id, section_name, username, is_active, created_at
            FROM kitchen_sections
            WHERE id = %s AND hotel_id = %s
        """, (kitchen_id, hotel_id))
        
        kitchen = cursor.fetchone()
        
        if not kitchen:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'message': 'Kitchen not found'})
        
        # Convert datetime to string
        if kitchen.get('created_at'):
            kitchen['created_at'] = str(kitchen['created_at'])
        
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'kitchen': kitchen})
        
    except Exception as e:
        print(f"[KITCHEN_DETAILS ERROR] {e}")
        return jsonify({'success': False, 'message': 'Server error'})


@hotel_manager_bp.route('/api/kitchen/<int:kitchen_id>', methods=['PUT'])
def update_kitchen(kitchen_id):
    """Update kitchen details"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    data = request.json
    section_name = data.get('section_name', '').strip()
    
    # Validation
    if not section_name:
        return jsonify({'success': False, 'message': 'Kitchen name is required!'})
    
    # Verify kitchen belongs to this hotel
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("SELECT hotel_id FROM kitchen_sections WHERE id = %s", (kitchen_id,))
        result = cursor.fetchone()
        
        if not result or result[0] != hotel_id:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'message': 'Kitchen not found'}), 404
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"[UPDATE_KITCHEN ERROR] {e}")
        return jsonify({'success': False, 'message': 'Server error'})
    
    result = KitchenAuth.update_kitchen(kitchen_id, section_name)
    
    # Log activity on success
    if result.get('success'):
        log_manager_activity('kitchen', f"Kitchen '{section_name}' was updated", hotel_id)
    
    return jsonify(result)


@hotel_manager_bp.route('/api/kitchen/<int:kitchen_id>/toggle', methods=['POST'])
def toggle_kitchen_status(kitchen_id):
    """Toggle kitchen active status"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    # Verify kitchen belongs to this hotel
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("SELECT hotel_id FROM kitchen_sections WHERE id = %s", (kitchen_id,))
        result = cursor.fetchone()
        
        if not result or result[0] != hotel_id:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'message': 'Kitchen not found'}), 404
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"[TOGGLE_KITCHEN ERROR] {e}")
        return jsonify({'success': False, 'message': 'Server error'})
    
    result = KitchenAuth.toggle_active(kitchen_id)
    
    # Log activity on success
    if result.get('success'):
        log_manager_activity('kitchen', f"Kitchen status was toggled", hotel_id)
    
    return jsonify(result)


@hotel_manager_bp.route('/api/kitchen/<int:kitchen_id>', methods=['DELETE'])
def delete_kitchen(kitchen_id):
    """Delete kitchen"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    # Verify kitchen belongs to this hotel
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        cursor.execute("SELECT hotel_id, section_name FROM kitchen_sections WHERE id = %s", (kitchen_id,))
        result = cursor.fetchone()
        
        if not result or result[0] != hotel_id:
            cursor.close()
            connection.close()
            return jsonify({'success': False, 'message': 'Kitchen not found'}), 404
        
        kitchen_name = result[1]
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"[DELETE_KITCHEN ERROR] {e}")
        return jsonify({'success': False, 'message': 'Server error'})
    
    result = KitchenAuth.delete_kitchen(kitchen_id)
    
    # Log activity on success
    if result.get('success'):
        log_manager_activity('kitchen', f"Kitchen '{kitchen_name}' was deleted", hotel_id)
    
    return jsonify(result)


@hotel_manager_bp.route('/api/categories', methods=['GET'])
def get_categories():
    """Get all categories for the manager's hotel"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, name
            FROM menu_categories
            WHERE hotel_id = %s
            ORDER BY name ASC
        """, (hotel_id,))
        
        categories = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return jsonify({'success': True, 'categories': categories})
        
    except Exception as e:
        print(f"[GET_CATEGORIES ERROR] {e}")
        return jsonify({'success': False, 'message': 'Server error'})


# =========================
# TIP VISIBILITY SETTINGS
# =========================

@hotel_manager_bp.route('/api/tip-visibility', methods=['GET'])
def get_tip_visibility():
    """Get current tip visibility setting for the hotel"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT COALESCE(show_waiter_tips, TRUE) as show_waiter_tips
            FROM hotel_modules
            WHERE hotel_id = %s
        """, (hotel_id,))
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        # Default to True if no setting found
        show_tips = result['show_waiter_tips'] if result else True
        
        return jsonify({
            'success': True,
            'show_waiter_tips': bool(show_tips)
        })
        
    except Exception as e:
        print(f"[TIP_VISIBILITY ERROR] {e}")
        return jsonify({'success': False, 'message': 'Server error', 'show_waiter_tips': True})


@hotel_manager_bp.route('/api/toggle-tip-visibility', methods=['POST'])
def toggle_tip_visibility():
    """Toggle tip visibility setting for waiters"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    try:
        data = request.get_json()
        show_tips = data.get('show_waiter_tips', True)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update the setting
        cursor.execute("""
            UPDATE hotel_modules
            SET show_waiter_tips = %s
            WHERE hotel_id = %s
        """, (show_tips, hotel_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Log the activity
        status = "enabled" if show_tips else "disabled"
        log_manager_activity('settings', f'Waiter tip visibility {status}', hotel_id)
        
        return jsonify({
            'success': True,
            'message': f'Tip visibility {status} for waiters',
            'show_waiter_tips': show_tips
        })
        
    except Exception as e:
        print(f"[TOGGLE_TIP_VISIBILITY ERROR] {e}")
        return jsonify({'success': False, 'message': 'Failed to update setting'})


@hotel_manager_bp.route('/api/toggle-waiter-tips/<int:waiter_id>', methods=['POST'])
def toggle_waiter_tips(waiter_id):
    """Toggle per-waiter tip visibility"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403

    try:
        data = request.get_json()
        show_tips = bool(data.get('show_waiter_tips', True))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE waiters SET show_waiter_tips = %s WHERE id = %s AND hotel_id = %s",
            (show_tips, waiter_id, hotel_id)
        )
        conn.commit()
        cursor.close()
        conn.close()

        status = "enabled" if show_tips else "disabled"
        log_manager_activity('settings', f'Tips {status} for waiter ID {waiter_id}', hotel_id)
        return jsonify({'success': True, 'show_waiter_tips': show_tips, 'message': f'Tips {status}'})

    except Exception as e:
        print(f"[TOGGLE_WAITER_TIPS ERROR] {e}")
        return jsonify({'success': False, 'message': 'Failed to update setting'})


@hotel_manager_bp.route('/api/waiter-tip-details/<int:waiter_id>')
def get_waiter_tip_details(waiter_id):
    """Get full tip history and summary for a specific waiter"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Verify waiter belongs to this hotel
        cursor.execute("SELECT id, name FROM waiters WHERE id = %s AND hotel_id = %s", (waiter_id, hotel_id))
        waiter = cursor.fetchone()
        if not waiter:
            cursor.close()
            conn.close()
            return jsonify({'success': False, 'message': 'Waiter not found'}), 404

        period = request.args.get('period', 'all')

        period_filter = ""
        if period == 'today':
            period_filter = "AND DATE(wt.created_at) = CURDATE()"
        elif period == 'week':
            period_filter = "AND YEARWEEK(wt.created_at, 1) = YEARWEEK(CURDATE(), 1)"
        elif period == 'month':
            period_filter = "AND YEAR(wt.created_at) = YEAR(CURDATE()) AND MONTH(wt.created_at) = MONTH(CURDATE())"

        # Tip history with table number
        cursor.execute(f"""
            SELECT wt.id, wt.tip_amount, wt.created_at,
                   b.table_number, b.guest_name, b.bill_number
            FROM waiter_tips wt
            LEFT JOIN bills b ON wt.bill_id = b.id
            WHERE wt.waiter_id = %s {period_filter}
            ORDER BY wt.created_at DESC
        """, (waiter_id,))
        tips = cursor.fetchall()

        # Summary totals
        cursor.execute("""
            SELECT
                COALESCE(SUM(tip_amount), 0) as total_tips,
                COALESCE(SUM(CASE WHEN DATE(created_at) = CURDATE() THEN tip_amount ELSE 0 END), 0) as today_tips,
                COALESCE(SUM(CASE WHEN YEARWEEK(created_at,1) = YEARWEEK(CURDATE(),1) THEN tip_amount ELSE 0 END), 0) as week_tips,
                COALESCE(SUM(CASE WHEN YEAR(created_at) = YEAR(CURDATE()) AND MONTH(created_at) = MONTH(CURDATE()) THEN tip_amount ELSE 0 END), 0) as month_tips,
                COUNT(*) as tip_count
            FROM waiter_tips WHERE waiter_id = %s
        """, (waiter_id,))
        summary = cursor.fetchone()

        cursor.close()
        conn.close()

        # Serialize datetimes
        for t in tips:
            if t.get('created_at'):
                t['created_at'] = t['created_at'].strftime('%Y-%m-%d %H:%M')
            t['tip_amount'] = float(t['tip_amount'])

        return jsonify({
            'success': True,
            'waiter': {'id': waiter_id, 'name': waiter['name']},
            'summary': {
                'total_tips': float(summary['total_tips']),
                'today_tips': float(summary['today_tips']),
                'week_tips': float(summary['week_tips']),
                'month_tips': float(summary['month_tips']),
                'tip_count': int(summary['tip_count'])
            },
            'tips': tips
        })

    except Exception as e:
        print(f"[WAITER_TIP_DETAILS ERROR] {e}")
        return jsonify({'success': False, 'message': str(e)}), 500
