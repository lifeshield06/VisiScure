from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from admin.models import Admin, Manager
from database.db import get_db_connection
from datetime import datetime
from werkzeug.utils import secure_filename
from payment.upi_utils import validate_upi_id
import os

admin_bp = Blueprint("admin", __name__)

# Logo upload configuration
UPLOAD_FOLDER = 'static/uploads/hotel_logos'
UPI_QR_UPLOAD_FOLDER = 'static/uploads/hotel_qr'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'svg'}
ALLOWED_QR_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def allowed_qr_file(filename):
    """Check if QR file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_QR_EXTENSIONS

# =========================
# REUSABLE ACTIVITY LOGGER
# =========================

def log_activity(activity_type, message):
    """Reusable function to log admin activities safely with role='admin'"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Ensure role column exists
        try:
            cursor.execute("SHOW COLUMNS FROM recent_activities LIKE 'role'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE recent_activities ADD COLUMN role VARCHAR(20) DEFAULT 'admin'")
                conn.commit()
        except Exception:
            pass
        
        cursor.execute(
            "INSERT INTO recent_activities (activity_type, message, role) VALUES (%s, %s, %s)",
            (activity_type, message, 'admin')
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception:
        pass  # Fail silently to not break main operations

# =========================
# AUTH
# =========================

@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        admin = Admin.authenticate(username, password)
        if admin:
            session["admin_id"] = admin.id
            session["admin_name"] = admin.name
            session["admin_username"] = admin.username
            return redirect(url_for("admin.dashboard"))
        else:
            flash("Invalid username or password", "error")

    return render_template("admin_login.html")


@admin_bp.route("/dashboard")
def dashboard():
    if "admin_id" not in session:
        return redirect(url_for("admin.login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Ensure recent_activities table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recent_activities (
            id INT AUTO_INCREMENT PRIMARY KEY,
            activity_type VARCHAR(50) NOT NULL,
            message TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_created_at (created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)

    # Clean old activities (older than 3 days)
    cursor.execute("DELETE FROM recent_activities WHERE created_at < NOW() - INTERVAL 3 DAY")
    conn.commit()

    # TOTAL HOTELS
    cursor.execute("SELECT COUNT(*) FROM hotels")
    total_hotels = cursor.fetchone()[0]

    # TOTAL MANAGERS
    cursor.execute("SELECT COUNT(*) FROM managers")
    total_managers = cursor.fetchone()[0]

    # TOTAL KYC VERIFICATIONS
    cursor.execute("SELECT COUNT(*) FROM kyc_verifications")
    total_kyc = cursor.fetchone()[0]

    # TODAY'S KYC VERIFICATIONS
    cursor.execute("""
        SELECT COUNT(*) FROM kyc_verifications
        WHERE DATE(created_at) = CURDATE()
    """)
    today_kyc = cursor.fetchone()[0]

    # FETCH RECENT ACTIVITIES (latest 5)
    cursor.execute("""
        SELECT activity_type, message, created_at
        FROM recent_activities
        ORDER BY created_at DESC
        LIMIT 5
    """)
    recent_activities = cursor.fetchall()

    conn.close()

    return render_template(
        "admin/admin_dashboard.html",
        total_hotels=total_hotels,
        total_managers=total_managers,
        total_kyc=total_kyc,
        today_kyc=today_kyc,
        recent_activities=recent_activities
    )



@admin_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("admin.login"))


# =========================
# RESTAURANT MANAGEMENT
# =========================

@admin_bp.route("/create-hotel", methods=["GET", "POST"])
def create_hotel():
    if "admin_id" not in session:
        return redirect(url_for("admin.login"))

    if request.method == "POST":
        hotel_name = request.form.get("hotel_name")
        address = request.form.get("address")
        city = request.form.get("city")

        kyc_enabled = request.form.get("kyc") == "on"
        food_enabled = request.form.get("food") == "on"
        
        # Get pricing charges
        per_verification_charge = float(request.form.get("per_verification_charge", 0) or 0)
        per_order_charge = float(request.form.get("per_order_charge", 0) or 0)
        
        # Get UPI payment details
        upi_id = request.form.get("upi_id", "").strip() or None
        
        # Validate UPI ID if provided
        if upi_id and not validate_upi_id(upi_id):
            flash("Invalid UPI ID format. Use format: identifier@bank (e.g., 9876543210@paytm)", "error")
            return redirect(url_for("admin.create_hotel"))
        
        # Handle logo upload
        logo_filename = None
        logo_file = request.files.get('hotel_logo')
        
        if logo_file and logo_file.filename:
            if allowed_file(logo_file.filename):
                # Temporarily save with original name
                filename = secure_filename(logo_file.filename)
                temp_path = os.path.join(UPLOAD_FOLDER, filename)
                logo_file.save(temp_path)
                logo_filename = filename
            else:
                flash("Invalid file type. Allowed: png, jpg, jpeg, gif, svg", "error")
                return redirect(url_for("admin.create_hotel"))
        
        # Handle UPI QR upload
        upi_qr_filename = None
        upi_qr_file = request.files.get('upi_qr_image')
        
        if upi_qr_file and upi_qr_file.filename:
            if allowed_qr_file(upi_qr_file.filename):
                # Temporarily save with original name
                filename = secure_filename(upi_qr_file.filename)
                temp_path = os.path.join(UPI_QR_UPLOAD_FOLDER, filename)
                upi_qr_file.save(temp_path)
                upi_qr_filename = filename
            else:
                flash("Invalid QR file type. Allowed: png, jpg, jpeg", "error")
                return redirect(url_for("admin.create_hotel"))

        if not (kyc_enabled or food_enabled):
            flash("Please select at least one module", "error")
            return redirect(url_for("admin.create_hotel"))

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Insert hotel with logo and UPI details
            cursor.execute(
                "INSERT INTO hotels (hotel_name, address, city, logo, upi_id, upi_qr_image) VALUES (%s, %s, %s, %s, %s, %s)",
                (hotel_name, address, city, logo_filename, upi_id, upi_qr_filename)
            )
            hotel_id = cursor.lastrowid
            
            # Rename logo file to include hotel_id
            if logo_filename:
                old_path = os.path.join(UPLOAD_FOLDER, logo_filename)
                extension = logo_filename.rsplit('.', 1)[1].lower()
                new_filename = f"hotel_{hotel_id}.{extension}"
                new_path = os.path.join(UPLOAD_FOLDER, new_filename)
                os.rename(old_path, new_path)
                
                # Update database with new filename
                cursor.execute("UPDATE hotels SET logo = %s WHERE id = %s", (new_filename, hotel_id))
            
            # Rename UPI QR file to include hotel_id
            if upi_qr_filename:
                old_path = os.path.join(UPI_QR_UPLOAD_FOLDER, upi_qr_filename)
                extension = upi_qr_filename.rsplit('.', 1)[1].lower()
                new_qr_filename = f"qr_hotel_{hotel_id}.{extension}"
                new_path = os.path.join(UPI_QR_UPLOAD_FOLDER, new_qr_filename)
                os.rename(old_path, new_path)
                
                # Update database with new filename
                cursor.execute("UPDATE hotels SET upi_qr_image = %s WHERE id = %s", (new_qr_filename, hotel_id))

            # Insert module permissions
            cursor.execute(
                """
                INSERT INTO hotel_modules (hotel_id, kyc_enabled, food_enabled)
                VALUES (%s, %s, %s)
                """,
                (hotel_id, kyc_enabled, food_enabled)
            )

            # Log activity
            log_activity('hotel', f"Hotel '{hotel_name}' was created")

            conn.commit()
            cursor.close()
            conn.close()
            
            # Create wallet for the hotel with charges
            from wallet.models import HotelWallet
            HotelWallet.create_wallet(hotel_id, per_verification_charge, per_order_charge)

            flash("Hotel created successfully", "success")
            return redirect(url_for("admin.dashboard"))

        except Exception as e:
            # Rollback database transaction
            try:
                conn.rollback()
            except Exception:
                pass
            
            # Clean up uploaded files if database insert fails
            if logo_filename:
                try:
                    logo_path = os.path.join(UPLOAD_FOLDER, logo_filename)
                    if os.path.exists(logo_path):
                        os.remove(logo_path)
                except Exception as cleanup_error:
                    print(f"Failed to cleanup logo file: {cleanup_error}")
            
            if upi_qr_filename:
                try:
                    qr_path = os.path.join(UPI_QR_UPLOAD_FOLDER, upi_qr_filename)
                    if os.path.exists(qr_path):
                        os.remove(qr_path)
                except Exception as cleanup_error:
                    print(f"Failed to cleanup QR file: {cleanup_error}")
            
            # Also try to clean up renamed files if they exist
            try:
                if logo_filename and 'hotel_id' in locals():
                    extension = logo_filename.rsplit('.', 1)[1].lower()
                    renamed_logo = f"hotel_{hotel_id}.{extension}"
                    renamed_logo_path = os.path.join(UPLOAD_FOLDER, renamed_logo)
                    if os.path.exists(renamed_logo_path):
                        os.remove(renamed_logo_path)
            except Exception:
                pass
            
            try:
                if upi_qr_filename and 'hotel_id' in locals():
                    extension = upi_qr_filename.rsplit('.', 1)[1].lower()
                    renamed_qr = f"qr_hotel_{hotel_id}.{extension}"
                    renamed_qr_path = os.path.join(UPI_QR_UPLOAD_FOLDER, renamed_qr)
                    if os.path.exists(renamed_qr_path):
                        os.remove(renamed_qr_path)
            except Exception:
                pass
            
            print("CREATE HOTEL ERROR 👉", e)
            flash(f"Error creating hotel: {e}", "error")

    return render_template("admin/create_hotel.html")


@admin_bp.route("/all-hotels")
def all_hotels():
    if "admin_id" not in session:
        return redirect(url_for("admin.login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            h.id, h.hotel_name, h.city,
            hm.kyc_enabled, hm.food_enabled,
            h.address,
            COALESCE(hw.balance, 0) as wallet_balance,
            COALESCE(hw.per_verification_charge, 0) as per_verification_charge,
            COALESCE(hw.per_order_charge, 0) as per_order_charge,
            h.upi_id,
            h.upi_qr_image,
            h.logo
        FROM hotels h
        JOIN hotel_modules hm ON h.id = hm.hotel_id
        LEFT JOIN hotel_wallet hw ON h.id = hw.hotel_id
        ORDER BY h.created_at DESC
    """)

    hotels = cursor.fetchall()
    conn.close()

    return render_template("admin/all_hotels.html", hotels=hotels)


@admin_bp.route("/api/update-hotel", methods=["POST"])
def api_update_hotel():
    """API endpoint to update hotel details (Admin only)"""
    print(f"[API DEBUG] api_update_hotel called")
    print(f"[API DEBUG] request.files: {list(request.files.keys())}")
    print(f"[API DEBUG] request.form: {list(request.form.keys())}")
    print(f"[API DEBUG] Content-Type: {request.content_type}")
    
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    # Check if this is a form submission with file upload
    if request.files:
        print(f"[API DEBUG] Routing to update_hotel_with_logo()")
        return update_hotel_with_logo()
    
    data = request.json
    hotel_id = data.get("hotel_id")
    hotel_name = data.get("hotel_name", "").strip()
    address = data.get("address", "").strip()
    city = data.get("city", "").strip()
    kyc_enabled = data.get("kyc_enabled", False)
    food_enabled = data.get("food_enabled", False)
    upi_id = data.get("upi_id", "").strip() or None

    if not hotel_id or not hotel_name:
        return jsonify({"success": False, "message": "Hotel ID and name are required"})

    if not kyc_enabled and not food_enabled:
        return jsonify({"success": False, "message": "At least one module must be enabled"})

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Update hotel details including UPI ID
        cursor.execute("""
            UPDATE hotels 
            SET hotel_name = %s, address = %s, city = %s, upi_id = %s
            WHERE id = %s
        """, (hotel_name, address, city, upi_id, hotel_id))

        # Update hotel modules
        cursor.execute("""
            UPDATE hotel_modules
            SET kyc_enabled = %s, food_enabled = %s
            WHERE hotel_id = %s
        """, (kyc_enabled, food_enabled, hotel_id))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"success": True, "message": "Hotel updated successfully"})

    except Exception as e:
        print(f"Error updating hotel: {e}")
        return jsonify({"success": False, "message": f"Error updating hotel: {str(e)}"})


def update_hotel_with_logo():
    """Handle hotel update with logo upload"""
    # Debug: Print received files and form data
    print(f"[LOGO DEBUG] request.files: {list(request.files.keys())}")
    print(f"[LOGO DEBUG] hotel_logo in files: {'hotel_logo' in request.files}")
    if 'hotel_logo' in request.files:
        logo_f = request.files['hotel_logo']
        print(f"[LOGO DEBUG] logo filename: {logo_f.filename}, content_type: {logo_f.content_type}")
    
    hotel_id = request.form.get("hotel_id")
    hotel_name = request.form.get("hotel_name", "").strip()
    address = request.form.get("address", "").strip()
    city = request.form.get("city", "").strip()
    kyc_enabled = request.form.get("kyc_enabled") == "true"
    food_enabled = request.form.get("food_enabled") == "true"
    
    # Get UPI details
    upi_id = request.form.get("upi_id", "").strip() or None
    remove_qr = request.form.get("remove_qr") == "true"
    
    # Validate UPI ID if provided
    if upi_id and not validate_upi_id(upi_id):
        return jsonify({
            "success": False, 
            "message": "Invalid UPI ID format. Use format: identifier@bank (e.g., 9876543210@paytm)"
        })
    
    # Track files to clean up on error
    new_logo_path = None
    new_qr_path = None
    old_logo_to_delete = None
    old_qr_to_delete = None
    
    conn = None
    cursor = None
    
    try:
        # Get old file paths before any changes
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT logo, upi_qr_image FROM hotels WHERE id = %s", (hotel_id,))
        result = cursor.fetchone()
        if not result:
            return jsonify({"success": False, "message": "Hotel not found"})
        
        old_logo = result[0]
        old_qr = result[1]
        
        # Handle logo upload
        logo_file = request.files.get('hotel_logo')
        logo_filename = None
        
        if logo_file and logo_file.filename:
            print(f"[LOGO DEBUG] Processing logo: {logo_file.filename}")
            if not allowed_file(logo_file.filename):
                print(f"[LOGO DEBUG] File type not allowed: {logo_file.filename}")
                return jsonify({"success": False, "message": "Invalid file type"})
            
            # Save new logo
            extension = logo_file.filename.rsplit('.', 1)[1].lower()
            new_filename = f"hotel_{hotel_id}.{extension}"
            new_logo_path = os.path.join(UPLOAD_FOLDER, new_filename)
            
            # Ensure upload folder exists
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
            
            logo_file.save(new_logo_path)
            logo_filename = new_filename
            print(f"[LOGO DEBUG] Logo saved: {new_logo_path}, db filename: {logo_filename}")
            
            # Mark old logo for deletion
            if old_logo:
                old_logo_to_delete = os.path.join(UPLOAD_FOLDER, old_logo)
        
        # Handle UPI QR upload
        upi_qr_file = request.files.get('upi_qr_image')
        upi_qr_filename = None
        
        if upi_qr_file and upi_qr_file.filename:
            if not allowed_qr_file(upi_qr_file.filename):
                # Clean up logo if it was uploaded
                if new_logo_path and os.path.exists(new_logo_path):
                    os.remove(new_logo_path)
                return jsonify({"success": False, "message": "Invalid QR file type"})
            
            # Save new QR
            extension = upi_qr_file.filename.rsplit('.', 1)[1].lower()
            new_qr_filename = f"qr_hotel_{hotel_id}.{extension}"
            new_qr_path = os.path.join(UPI_QR_UPLOAD_FOLDER, new_qr_filename)
            upi_qr_file.save(new_qr_path)
            upi_qr_filename = new_qr_filename
            
            # Mark old QR for deletion
            if old_qr:
                old_qr_to_delete = os.path.join(UPI_QR_UPLOAD_FOLDER, old_qr)
        
        # Handle QR removal
        if remove_qr:
            if old_qr:
                old_qr_to_delete = os.path.join(UPI_QR_UPLOAD_FOLDER, old_qr)
            upi_qr_filename = ""  # Set to empty string to clear in database
        
        # Build update query dynamically
        update_fields = []
        update_values = []
        
        update_fields.extend(["hotel_name = %s", "address = %s", "city = %s"])
        update_values.extend([hotel_name, address, city])
        
        if logo_filename:
            update_fields.append("logo = %s")
            update_values.append(logo_filename)
        
        # Always update UPI ID
        update_fields.append("upi_id = %s")
        update_values.append(upi_id)
        
        # Update QR if uploaded or removed
        if upi_qr_filename is not None:
            update_fields.append("upi_qr_image = %s")
            update_values.append(upi_qr_filename if upi_qr_filename else None)
        
        update_values.append(hotel_id)
        
        # Start transaction
        cursor.execute("START TRANSACTION")
        
        # Update hotel details
        query = f"UPDATE hotels SET {', '.join(update_fields)} WHERE id = %s"
        print(f"[LOGO DEBUG] SQL Query: {query}")
        print(f"[LOGO DEBUG] SQL Values: {update_values}")
        cursor.execute(query, tuple(update_values))
        
        # Update hotel modules
        cursor.execute("""
            UPDATE hotel_modules
            SET kyc_enabled = %s, food_enabled = %s
            WHERE hotel_id = %s
        """, (kyc_enabled, food_enabled, hotel_id))
        
        # Commit transaction
        conn.commit()
        
        # Only delete old files after successful database commit
        if old_logo_to_delete and os.path.exists(old_logo_to_delete):
            try:
                os.remove(old_logo_to_delete)
            except Exception as e:
                print(f"Warning: Could not delete old logo: {e}")
        
        if old_qr_to_delete and os.path.exists(old_qr_to_delete):
            try:
                os.remove(old_qr_to_delete)
            except Exception as e:
                print(f"Warning: Could not delete old QR: {e}")
        
        return jsonify({"success": True, "message": "Hotel updated successfully"})
        
    except Exception as e:
        # Rollback database changes
        if conn:
            try:
                conn.rollback()
            except:
                pass
        
        # Clean up newly uploaded files on error
        if new_logo_path and os.path.exists(new_logo_path):
            try:
                os.remove(new_logo_path)
            except Exception as cleanup_error:
                print(f"Error cleaning up logo: {cleanup_error}")
        
        if new_qr_path and os.path.exists(new_qr_path):
            try:
                os.remove(new_qr_path)
            except Exception as cleanup_error:
                print(f"Error cleaning up QR: {cleanup_error}")
        
        print(f"Error updating hotel: {e}")
        return jsonify({"success": False, "message": f"Error updating hotel: {str(e)}"})
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


@admin_bp.route("/api/delete-hotel", methods=["POST"])
def api_delete_hotel():
    """API endpoint to delete a hotel (Admin only)"""
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.json
    hotel_id = data.get("hotel_id")

    if not hotel_id:
        return jsonify({"success": False, "message": "Hotel ID is required"})

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if hotel exists
        cursor.execute("SELECT hotel_name FROM hotels WHERE id = %s", (hotel_id,))
        hotel = cursor.fetchone()
        if not hotel:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Hotel not found"})

        # Delete in proper order to respect foreign key constraints
        # 1. Delete waiter_table_assignments for waiters of this hotel
        cursor.execute("""
            DELETE wta FROM waiter_table_assignments wta
            JOIN waiters w ON wta.waiter_id = w.id
            WHERE w.hotel_id = %s
        """, (hotel_id,))

        # 2. Delete table_orders for tables of this hotel
        cursor.execute("""
            DELETE o FROM table_orders o
            JOIN tables t ON o.table_id = t.id
            WHERE t.hotel_id = %s
        """, (hotel_id,))

        # 3. Delete tables for this hotel
        cursor.execute("DELETE FROM tables WHERE hotel_id = %s", (hotel_id,))

        # 4. Delete waiters for this hotel
        cursor.execute("DELETE FROM waiters WHERE hotel_id = %s", (hotel_id,))

        # 5. Delete menu dishes for this hotel (before categories due to FK)
        cursor.execute("DELETE FROM menu_dishes WHERE hotel_id = %s", (hotel_id,))

        # 6. Delete menu categories for this hotel
        cursor.execute("DELETE FROM menu_categories WHERE hotel_id = %s", (hotel_id,))

        # 7. Delete KYC verifications for this hotel
        cursor.execute("DELETE FROM kyc_verifications WHERE hotel_id = %s", (hotel_id,))

        # 8. Delete hotel_managers assignment
        cursor.execute("DELETE FROM hotel_managers WHERE hotel_id = %s", (hotel_id,))

        # 9. Delete hotel_modules
        cursor.execute("DELETE FROM hotel_modules WHERE hotel_id = %s", (hotel_id,))
        
        # 10. Delete wallet transactions for this hotel
        cursor.execute("DELETE FROM wallet_transactions WHERE hotel_id = %s", (hotel_id,))
        
        # 11. Delete hotel wallet
        cursor.execute("DELETE FROM hotel_wallet WHERE hotel_id = %s", (hotel_id,))

        # 12. Finally delete the hotel
        cursor.execute("DELETE FROM hotels WHERE id = %s", (hotel_id,))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({"success": True, "message": f"Hotel '{hotel[0]}' deleted successfully"})

    except Exception as e:
        print(f"Error deleting hotel: {e}")
        try:
            conn.rollback()
        except:
            pass
        return jsonify({"success": False, "message": f"Error deleting hotel: {str(e)}"})


@admin_bp.route("/edit-hotel/<int:hotel_id>", methods=["GET", "POST"])
def edit_hotel_modules(hotel_id):
    if "admin_id" not in session:
        return redirect(url_for("admin.login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == "POST":
        kyc_enabled = request.form.get("kyc") == "on"
        food_enabled = request.form.get("food") == "on"

        if not (kyc_enabled or food_enabled):
            flash("At least one module must be enabled", "error")
            return redirect(url_for("admin.edit_hotel_modules", hotel_id=hotel_id))

        # Handle logo upload
        logo_file = request.files.get('hotel_logo')
        if logo_file and logo_file.filename:
            if allowed_file(logo_file.filename):
                # Get file extension
                extension = logo_file.filename.rsplit('.', 1)[1].lower()
                new_filename = f"hotel_{hotel_id}.{extension}"
                logo_path = os.path.join(UPLOAD_FOLDER, new_filename)
                
                # Save the new logo
                logo_file.save(logo_path)
                
                # Update logo in database
                cursor.execute("UPDATE hotels SET logo = %s WHERE id = %s", (new_filename, hotel_id))
            else:
                flash("Invalid file type. Allowed: png, jpg, jpeg, gif, svg", "error")
                return redirect(url_for("admin.edit_hotel_modules", hotel_id=hotel_id))

        cursor.execute("""
            UPDATE hotel_modules
            SET kyc_enabled=%s, food_enabled=%s
            WHERE hotel_id=%s
        """, (kyc_enabled, food_enabled, hotel_id))

        # Get hotel name for activity log
        cursor.execute("SELECT hotel_name FROM hotels WHERE id = %s", (hotel_id,))
        hotel_result = cursor.fetchone()
        hotel_name = hotel_result[0] if hotel_result else "Unknown"

        conn.commit()
        conn.close()

        log_activity('hotel', f"Hotel settings updated for '{hotel_name}'")
        flash("Hotel settings updated", "success")
        return redirect(url_for("admin.all_hotels"))

    # GET request - fetch hotel data including logo
    cursor.execute("""
        SELECT h.hotel_name, hm.kyc_enabled, hm.food_enabled, h.logo
        FROM hotels h
        JOIN hotel_modules hm ON h.id = hm.hotel_id
        WHERE h.id=%s
    """, (hotel_id,))
    hotel = cursor.fetchone()

    conn.close()
    return render_template("admin/edit_hotel_modules.html", hotel=hotel, hotel_id=hotel_id)


@admin_bp.route("/delete-hotel/<int:hotel_id>", methods=["POST"])
def delete_hotel(hotel_id):
    if "admin_id" not in session:
        return redirect(url_for("admin.login"))
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get hotel name before deletion
        cursor.execute("SELECT hotel_name FROM hotels WHERE id = %s", (hotel_id,))
        hotel = cursor.fetchone()
        hotel_name = hotel[0] if hotel else "Unknown"
        
        # Delete related records first (handle foreign key constraints)
        cursor.execute("DELETE FROM hotel_managers WHERE hotel_id = %s", (hotel_id,))
        cursor.execute("DELETE FROM hotel_modules WHERE hotel_id = %s", (hotel_id,))
        cursor.execute("DELETE FROM kyc_verifications WHERE hotel_id = %s", (hotel_id,))
        cursor.execute("DELETE FROM menu_dishes WHERE hotel_id = %s", (hotel_id,))
        cursor.execute("DELETE FROM menu_categories WHERE hotel_id = %s", (hotel_id,))
        cursor.execute("DELETE FROM waiters WHERE hotel_id = %s", (hotel_id,))
        
        # Delete the hotel
        cursor.execute("DELETE FROM hotels WHERE id = %s", (hotel_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        # Log activity
        log_activity('hotel', f"Hotel '{hotel_name}' was deleted")
        
        flash(f"Hotel '{hotel_name}' deleted successfully!", "success")
    except Exception as e:
        try:
            conn.rollback()
        except:
            pass
        flash(f"Error deleting hotel: {str(e)}", "error")
    
    return redirect(url_for("admin.all_hotels"))


# =========================
# MANAGER MANAGEMENT (STEP 5 FIXED)
# =========================

@admin_bp.route("/add-manager", methods=["GET", "POST"])
def add_manager():
    if "admin_id" not in session:
        return redirect(url_for("admin.login"))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Fetch only hotels that don't have a manager assigned (one hotel - one manager policy)
    cursor.execute("""
        SELECT h.id, h.hotel_name 
        FROM hotels h
        LEFT JOIN hotel_managers hm ON h.id = hm.hotel_id
        WHERE hm.id IS NULL
        ORDER BY h.hotel_name
    """)
    hotels = cursor.fetchall()

    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        username = request.form["username"].strip()
        password = request.form["password"]
        hotel_id = request.form["hotel_id"]
        
        # Validate email format
        if '@' not in email or '.' not in email.split('@')[-1]:
            flash("Invalid email format!", "error")
            conn.close()
            return render_template("admin/add_manager.html", hotels=hotels)

        try:
            # Insert manager (email already normalized to lowercase)
            cursor.execute(
                """
                INSERT INTO managers (name, email, username, password)
                VALUES (%s, %s, %s, SHA2(%s,256))
                """,
                (name, email, username, password)
            )
            manager_id = cursor.lastrowid

            # Assign hotel
            cursor.execute(
                "INSERT INTO hotel_managers (hotel_id, manager_id) VALUES (%s, %s)",
                (hotel_id, manager_id)
            )

            # Log activity
            log_activity('manager', f"Manager '{name}' was added")

            conn.commit()
            flash("Manager added and assigned to hotel successfully!", "success")
            return redirect(url_for("admin.dashboard"))

        except Exception as e:
            conn.rollback()
            error_msg = str(e)
            print("ADD MANAGER ERROR 👉", e)
            
            if "Duplicate entry" in error_msg:
                if "email" in error_msg:
                    flash("Email already exists. Please use a different email.", "error")
                elif "username" in error_msg:
                    flash("Username already exists. Please choose a different username.", "error")
                else:
                    flash("Duplicate entry found. Please check your input.", "error")
            else:
                flash(f"Error adding manager: {e}", "error")

    conn.close()
    return render_template("admin/add_manager.html", hotels=hotels)


@admin_bp.route("/all-managers")
def all_managers():
    if "admin_id" not in session:
        return redirect(url_for("admin.login"))

    managers = Manager.get_all_managers()
    return render_template("admin/all_managers.html", managers=managers)

@admin_bp.route("/edit-manager/<int:manager_id>", methods=["GET", "POST"])
def edit_manager(manager_id):
    if "admin_id" not in session:
        return redirect(url_for("admin.login"))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        username = request.form["username"].strip()
        password = request.form.get("password")
        hotel_id = request.form.get("hotel_id")
        
        # Validate email format
        if '@' not in email or '.' not in email.split('@')[-1]:
            flash("Invalid email format!", "error")
            manager = Manager.get_manager_by_id(manager_id)
            assigned_hotel = Manager.get_assigned_hotel(manager_id)
            conn.close()
            return render_template("admin/edit_manager.html", 
                                  manager=manager, 
                                  assigned_hotel=assigned_hotel,
                                  hotels=[])
        
        try:
            Manager.update_manager(manager_id, name, email, username, password if password else None)
            
            # Handle hotel assignment if provided
            if hotel_id:
                Manager.assign_hotel(manager_id, int(hotel_id))
            
            log_activity('manager', f"Manager '{name}' was updated")
            flash("Manager updated successfully!", "success")
            return redirect(url_for("admin.all_managers"))
        except Exception as e:
            flash(f"Error updating manager: {e}", "error")
    
    manager = Manager.get_manager_by_id(manager_id)
    assigned_hotel = Manager.get_assigned_hotel(manager_id)
    
    # Fetch only hotels that don't have a manager assigned (one hotel - one manager policy)
    cursor.execute("""
        SELECT h.id, h.hotel_name 
        FROM hotels h
        LEFT JOIN hotel_managers hm ON h.id = hm.hotel_id
        WHERE hm.id IS NULL
        ORDER BY h.hotel_name
    """)
    hotels = cursor.fetchall()
    conn.close()
    
    return render_template("admin/edit_manager.html", 
                          manager=manager, 
                          assigned_hotel=assigned_hotel,
                          hotels=hotels)

@admin_bp.route("/delete-manager/<int:manager_id>", methods=["POST"])
def delete_manager(manager_id):
    if "admin_id" not in session:
        return redirect(url_for("admin.login"))
    
    try:
        # Get manager name before deletion
        manager = Manager.get_manager_by_id(manager_id)
        manager_name = manager[1] if manager else "Unknown"
        
        Manager.delete_manager(manager_id)
        
        # Log activity
        log_activity('manager', f"Manager '{manager_name}' was removed")
        
        flash("Manager deleted successfully!", "success")
    except Exception as e:
        flash("Error deleting manager", "error")
    
    return redirect(url_for("admin.all_managers"))

@admin_bp.route("/change-username", methods=["GET", "POST"])
def change_username():
    if "admin_id" not in session:
        return redirect(url_for("admin.login"))
    
    if request.method == "POST":
        new_username = request.form["username"]
        try:
            Admin.update_username(session["admin_id"], new_username)
            session["admin_username"] = new_username
            log_activity('settings', f"Admin username changed to '{new_username}'")
            flash("Username updated successfully!", "success")
            return redirect(url_for("admin.account_settings"))
        except Exception as e:
            flash("Error updating username", "error")
    
    return redirect(url_for("admin.account_settings"))

@admin_bp.route("/change-password", methods=["GET", "POST"])
def change_password():
    if "admin_id" not in session:
        return redirect(url_for("admin.login"))
    
    if request.method == "POST":
        new_password = request.form["password"]
        try:
            Admin.update_password(session["admin_id"], new_password)
            log_activity('settings', "Admin password was changed")
            flash("Password updated successfully!", "success")
            return redirect(url_for("admin.account_settings"))
        except Exception as e:
            flash("Error updating password", "error")
    
    return redirect(url_for("admin.account_settings"))

@admin_bp.route("/account-settings")
def account_settings():
    if "admin_id" not in session:
        return redirect(url_for("admin.login"))
    
    return render_template("admin/account_settings.html")

# =========================
# API ENDPOINTS
# =========================

@admin_bp.route("/api/recent-activities")
def get_recent_activities():
    if "admin_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Ensure table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recent_activities (
                id INT AUTO_INCREMENT PRIMARY KEY,
                activity_type VARCHAR(50) NOT NULL,
                message TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)

        # Delete activities older than 3 days
        cursor.execute("DELETE FROM recent_activities WHERE created_at < NOW() - INTERVAL 3 DAY")
        conn.commit()

        # Fetch latest 5 admin-only activities (hotel_id IS NULL)
        cursor.execute("""
            SELECT activity_type, message, created_at
            FROM recent_activities
            WHERE hotel_id IS NULL
            ORDER BY created_at DESC
            LIMIT 5
        """)
        activities = cursor.fetchall()
        conn.close()

        result = []
        for activity in activities:
            result.append({
                "activity_type": activity[0],
                "message": activity[1],
                "created_at": activity[2].strftime("%Y-%m-%d %H:%M:%S")
            })

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route("/api/all-activities")
def get_all_activities():
    """Get all activities (up to 50) for View All modal"""
    if "admin_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Delete activities older than 3 days
        cursor.execute("DELETE FROM recent_activities WHERE created_at < NOW() - INTERVAL 3 DAY")
        conn.commit()

        # Fetch all admin-only activities (max 50, hotel_id IS NULL)
        cursor.execute("""
            SELECT activity_type, message, created_at
            FROM recent_activities
            WHERE hotel_id IS NULL
            ORDER BY created_at DESC
            LIMIT 50
        """)
        activities = cursor.fetchall()
        conn.close()

        result = []
        for activity in activities:
            result.append({
                "activity_type": activity[0],
                "message": activity[1],
                "created_at": activity[2].strftime("%Y-%m-%d %H:%M:%S")
            })

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500