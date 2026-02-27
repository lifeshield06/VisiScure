from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from admin.models import Admin, Manager
from database.db import get_db_connection
from datetime import datetime

admin_bp = Blueprint("admin", __name__)

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
# HOTEL MANAGEMENT
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

        if not (kyc_enabled or food_enabled):
            flash("Please select at least one module", "error")
            return redirect(url_for("admin.create_hotel"))

        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Insert hotel
            cursor.execute(
                "INSERT INTO hotels (hotel_name, address, city) VALUES (%s, %s, %s)",
                (hotel_name, address, city)
            )
            hotel_id = cursor.lastrowid

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
            try:
                conn.rollback()
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
            COALESCE(hw.per_order_charge, 0) as per_order_charge
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
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Unauthorized"}), 401

    data = request.json
    hotel_id = data.get("hotel_id")
    hotel_name = data.get("hotel_name", "").strip()
    address = data.get("address", "").strip()
    city = data.get("city", "").strip()
    kyc_enabled = data.get("kyc_enabled", False)
    food_enabled = data.get("food_enabled", False)

    if not hotel_id or not hotel_name:
        return jsonify({"success": False, "message": "Hotel ID and name are required"})

    if not kyc_enabled and not food_enabled:
        return jsonify({"success": False, "message": "At least one module must be enabled"})

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Update hotel details
        cursor.execute("""
            UPDATE hotels 
            SET hotel_name = %s, address = %s, city = %s
            WHERE id = %s
        """, (hotel_name, address, city, hotel_id))

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

        cursor.execute("""
            UPDATE hotel_modules
            SET kyc_enabled=%s, food_enabled=%s
            WHERE hotel_id=%s
        """, (kyc_enabled, food_enabled, hotel_id))

        conn.commit()
        conn.close()

        log_activity('hotel', f"Hotel modules updated for '{hotel[0]}'")
        flash("Hotel modules updated", "success")
        return redirect(url_for("admin.all_hotels"))

    cursor.execute("""
        SELECT h.hotel_name, hm.kyc_enabled, hm.food_enabled
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