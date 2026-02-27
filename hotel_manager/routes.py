from flask import request, jsonify, session, render_template, send_file
from . import hotel_manager_bp
from .models import HotelManager, Waiter, DashboardStats, DailySpecialMenu
from database.db import get_db_connection
import qrcode
import io
import base64
from urllib.parse import urlencode
from datetime import datetime, timedelta

# Initialize Daily Special Menu table
DailySpecialMenu.create_table()

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
    
    if not manager_id or not manager_name:
        return "Invalid access. Please login first.", 403
    
    # If hotel_id is not in session, fetch it from database
    if not hotel_id and manager_id:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT hotel_id, kyc_enabled, food_enabled FROM hotel_managers WHERE id = %s",
                (manager_id,)
            )
            result = cursor.fetchone()
            if result:
                hotel_id = result[0]
                session['hotel_id'] = hotel_id
                session['kyc_enabled'] = bool(result[1]) if result[1] is not None else False
                session['food_enabled'] = bool(result[2]) if result[2] is not None else False
                
                # Also fetch hotel name
                cursor.execute("SELECT hotel_name FROM hotels WHERE id = %s", (hotel_id,))
                hotel_result = cursor.fetchone()
                if hotel_result:
                    session['hotel_name'] = hotel_result[0]
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error fetching hotel_id: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"[DEBUG] Dashboard loaded - manager_id={manager_id}, hotel_id={hotel_id}")
    
    if not hotel_id:
        return "Hotel not found for this manager. Please contact support.", 403
    
    # Get module flags from session (default to False if not set)
    kyc_enabled = session.get('kyc_enabled', False)
    food_enabled = session.get('food_enabled', False)
    hotel_name = session.get('hotel_name', '')
    
    # Get waiters for this hotel
    waiters = Waiter.get_waiters_by_hotel(hotel_id)
    waiters_count = len(waiters) if waiters else 0
    
    # Get dashboard statistics
    stats = DashboardStats.get_all_stats(hotel_id)
    
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
                         kyc_enabled=kyc_enabled,
                         food_enabled=food_enabled,
                         waiters_count=waiters_count,
                         stats=stats,
                         total_menu_items=total_menu_items)

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
        <title>All Managers - HotelEase</title>
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
            <h1>🏨 HotelEase - Manager Credentials</h1>
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
            <p>&copy; 2026 HotelEase - All Rights Reserved</p>
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

@hotel_manager_bp.route('/api/daily-special', methods=['GET'])
def get_daily_special():
    """Get today's special menu for the manager's hotel"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    special = DailySpecialMenu.get_today_special(hotel_id)
    if special:
        # Convert Decimal to float for JSON serialization
        special['price'] = float(special['price'])
        special['special_date'] = str(special['special_date'])
        return jsonify({'success': True, 'special': special})
    return jsonify({'success': True, 'special': None})


@hotel_manager_bp.route('/api/daily-special', methods=['POST'])
def save_daily_special():
    """Add or update today's special menu"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    # Handle both JSON and form data
    if request.content_type and 'multipart/form-data' in request.content_type:
        menu_name = request.form.get('menu_name', '').strip()
        description = request.form.get('description', '').strip()
        price = request.form.get('price')
        image_file = request.files.get('image')
    else:
        data = request.json or {}
        menu_name = data.get('menu_name', '').strip()
        description = data.get('description', '').strip()
        price = data.get('price')
        image_file = None
    
    # Validation
    if not menu_name:
        return jsonify({'success': False, 'message': 'Menu name is required!'})
    if not price:
        return jsonify({'success': False, 'message': 'Price is required!'})
    
    try:
        price_float = float(price)
        if price_float <= 0:
            return jsonify({'success': False, 'message': 'Price must be greater than zero!'})
    except (ValueError, TypeError):
        return jsonify({'success': False, 'message': 'Invalid price format!'})
    
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
    
    result = DailySpecialMenu.add_or_update_special(hotel_id, menu_name, description, price_float, image_path)
    
    # Log activity on success
    if result.get('success'):
        log_manager_activity('menu', f"Today's Special updated: '{menu_name}' (₹{price_float})", hotel_id)
    
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


@hotel_manager_bp.route('/api/daily-special', methods=['DELETE'])
def delete_daily_special():
    """Delete/deactivate today's special menu"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    result = DailySpecialMenu.delete_today_special(hotel_id)
    
    # Log activity on success
    if result.get('success'):
        log_manager_activity('menu', "Today's Special was removed", hotel_id)
    
    return jsonify(result)


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
    """Create a new kitchen with auto-generated ID and category assignments"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    data = request.json
    section_name = data.get('section_name', '').strip()
    category_ids = data.get('category_ids', [])
    
    # Validation
    if not section_name:
        return jsonify({'success': False, 'message': 'Kitchen name is required!'})
    if not category_ids or len(category_ids) == 0:
        return jsonify({'success': False, 'message': 'At least one category must be selected!'})
    
    result = KitchenAuth.create_kitchen(hotel_id, section_name, category_ids)
    
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
        
        # Get assigned categories
        cursor.execute("""
            SELECT category_id
            FROM kitchen_category_mapping
            WHERE kitchen_section_id = %s
        """, (kitchen_id,))
        
        category_ids = [row['category_id'] for row in cursor.fetchall()]
        kitchen['category_ids'] = category_ids
        
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
    """Update kitchen details and category assignments"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({'success': False, 'message': 'Not authorized'}), 403
    
    data = request.json
    section_name = data.get('section_name', '').strip()
    category_ids = data.get('category_ids', [])
    
    # Validation
    if not section_name:
        return jsonify({'success': False, 'message': 'Kitchen name is required!'})
    if not category_ids or len(category_ids) == 0:
        return jsonify({'success': False, 'message': 'At least one category must be selected!'})
    
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
    
    result = KitchenAuth.update_kitchen(kitchen_id, section_name, category_ids)
    
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
