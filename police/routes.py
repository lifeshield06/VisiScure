from flask import render_template, request, redirect, url_for, session, flash
from police import police_bp
from police.models import PoliceStation, PoliceUser
from database.db import get_db_connection


def police_login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "police_user_id" not in session:
            return redirect(url_for("police.login"))
        return f(*args, **kwargs)
    return decorated


# ─── Hidden Login ────────────────────────────────────────────────────────────

@police_bp.route("/police-login", methods=["GET", "POST"])
def login():
    from police.models import PoliceStation
    PoliceStation.create_tables()  # ensure tables exist on first hit

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = PoliceUser.authenticate(username, password)
        if user:
            session["police_user_id"] = user.id
            session["police_username"] = user.username
            session["police_station_id"] = user.station_id
            session["police_station_name"] = user.station_name
            PoliceUser.log_action(user.id, "Login", request.remote_addr)
            return redirect(url_for("police.dashboard"))
        flash("Invalid username or password", "error")
    return render_template("police/police_login.html")


@police_bp.route("/police/logout")
def logout():
    if "police_user_id" in session:
        PoliceUser.log_action(session["police_user_id"], "Logout", request.remote_addr)
    session.pop("police_user_id", None)
    session.pop("police_username", None)
    session.pop("police_station_id", None)
    session.pop("police_station_name", None)
    return redirect(url_for("police.login"))


# ─── Police Dashboard ─────────────────────────────────────────────────────────

@police_bp.route("/police/dashboard")
@police_login_required
def dashboard():
    user = PoliceUser.get_by_id(session["police_user_id"])
    station_id = session["police_station_id"]
    search = request.args.get("search", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Ensure mapping table exists (safe guard)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS police_station_hotels (
            id INT AUTO_INCREMENT PRIMARY KEY,
            station_id INT NOT NULL,
            hotel_id INT NOT NULL,
            UNIQUE KEY unique_mapping (station_id, hotel_id),
            FOREIGN KEY (station_id) REFERENCES police_stations(id) ON DELETE CASCADE,
            FOREIGN KEY (hotel_id) REFERENCES hotels(id) ON DELETE CASCADE
        )
    """)

    # Get hotels assigned to this police station
    cursor.execute("""
        SELECT h.id FROM hotels h
        JOIN police_station_hotels psh ON h.id = psh.hotel_id
        WHERE psh.station_id = %s
    """, (station_id,))
    hotel_ids = [r[0] for r in cursor.fetchall()]

    hotels_assigned = len(hotel_ids) > 0
    verifications = []

    if hotel_ids:
        placeholders = ",".join(["%s"] * len(hotel_ids))
        base_query = f"""
            SELECT gv.id, gv.guest_name, gv.phone, gv.kyc_number, gv.status,
                   h.hotel_name,
                   gv.selfie_path,
                   COALESCE(gv.aadhaar_path, gv.kyc_document_path) AS doc_path,
                   gv.submitted_at
            FROM guest_verifications gv
            JOIN hotels h ON gv.hotel_id = h.id
            WHERE gv.hotel_id IN ({placeholders})
        """
        if search:
            cursor.execute(
                base_query + " AND (gv.phone LIKE %s OR gv.kyc_number LIKE %s OR gv.guest_name LIKE %s) ORDER BY gv.submitted_at DESC",
                (*hotel_ids, f"%{search}%", f"%{search}%", f"%{search}%")
            )
        else:
            cursor.execute(base_query + " ORDER BY gv.submitted_at DESC", tuple(hotel_ids))
        verifications = cursor.fetchall()

    cursor.close()
    conn.close()

    PoliceUser.log_action(session["police_user_id"], "Viewed dashboard", request.remote_addr)

    return render_template(
        "police/police_dashboard.html",
        user=user,
        verifications=verifications,
        search=search,
        hotels_assigned=hotels_assigned
    )
