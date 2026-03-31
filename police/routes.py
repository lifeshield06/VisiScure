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
    searched = False

    if hotel_ids and search:
        searched = True
        placeholders = ",".join(["%s"] * len(hotel_ids))
        cursor.execute(
            f"""
            SELECT gv.id, gv.guest_name, gv.phone, gv.kyc_number, gv.status,
                   h.hotel_name,
                   gv.selfie_path,
                   COALESCE(gv.aadhaar_path, gv.kyc_document_path) AS doc_path,
                   gv.submitted_at
            FROM guest_verifications gv
            JOIN hotels h ON gv.hotel_id = h.id
            WHERE gv.hotel_id IN ({placeholders})
              AND (gv.phone = %s OR gv.kyc_number LIKE %s OR gv.guest_name LIKE %s)
            ORDER BY gv.submitted_at DESC
            """,
            (*hotel_ids, search, f"%{search}%", f"%{search}%")
        )
        verifications = cursor.fetchall()

    cursor.close()
    conn.close()

    PoliceUser.log_action(session["police_user_id"], "Viewed dashboard", request.remote_addr)

    return render_template(
        "police/police_dashboard.html",
        user=user,
        verifications=verifications,
        search=search,
        searched=searched,
        hotels_assigned=hotels_assigned
    )


# ─── Search API (JSON) ────────────────────────────────────────────────────────

@police_bp.route("/police/search", methods=["GET", "POST"])
@police_login_required
def search_api():
    """
    Unified search across guest_name, phone, kyc_number, hotel_name, status, date.
    Accepts:
      q       – free-text (searches all text fields via LIKE)
      status  – filter: approved | pending | rejected
      date    – filter: YYYY-MM-DD
      image   – file upload (POST only)
    Returns JSON {success, results, total, image_search}.
    """
    import os
    from flask import jsonify

    if request.method == "POST":
        q      = request.form.get("q", "").strip()
        status = request.form.get("status", "").strip().lower()
        date   = request.form.get("date", "").strip()
        image  = request.files.get("image")
    else:
        q      = request.args.get("q", "").strip()
        status = request.args.get("status", "").strip().lower()
        date   = request.args.get("date", "").strip()
        image  = None

    has_text   = bool(q or status or date)
    has_image  = bool(image and image.filename)

    if not has_text and not has_image:
        return jsonify({"success": False,
                        "message": "Enter a search term, apply a filter, or upload a photo.",
                        "results": []})

    # ── Save uploaded image ──────────────────────────────────────────────────
    image_saved_path = None
    if has_image:
        allowed_mime = {"image/jpeg", "image/jpg", "image/png"}
        if image.mimetype not in allowed_mime:
            return jsonify({"success": False, "message": "Only JPG/PNG images allowed.", "results": []})
        image.seek(0, 2)
        if image.tell() > 5 * 1024 * 1024:
            return jsonify({"success": False, "message": "Image must be under 5 MB.", "results": []})
        image.seek(0)
        save_dir = os.path.join("static", "uploads", "search")
        os.makedirs(save_dir, exist_ok=True)
        from datetime import datetime
        from werkzeug.utils import secure_filename
        fname = f"search_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{secure_filename(image.filename)}"
        image_saved_path = os.path.join(save_dir, fname)
        image.save(image_saved_path)

    # ── Get hotels for this station ──────────────────────────────────────────
    station_id = session["police_station_id"]
    conn   = get_db_connection()
    cursor = conn.cursor()

    # Ensure indexes exist for performance (idempotent)
    for idx_sql in [
        "CREATE INDEX IF NOT EXISTS idx_gv_phone    ON guest_verifications(phone)",
        "CREATE INDEX IF NOT EXISTS idx_gv_kyc      ON guest_verifications(kyc_number(20))",
        "CREATE INDEX IF NOT EXISTS idx_gv_name     ON guest_verifications(guest_name(30))",
        "CREATE INDEX IF NOT EXISTS idx_gv_status   ON guest_verifications(status)",
        "CREATE INDEX IF NOT EXISTS idx_gv_hotel    ON guest_verifications(hotel_id)",
        "CREATE INDEX IF NOT EXISTS idx_gv_submitted ON guest_verifications(submitted_at)",
    ]:
        try:
            cursor.execute(idx_sql)
        except Exception:
            pass  # index may already exist under a different name

    cursor.execute("""
        SELECT h.id FROM hotels h
        JOIN police_station_hotels psh ON h.id = psh.hotel_id
        WHERE psh.station_id = %s
    """, (station_id,))
    hotel_ids = [r[0] for r in cursor.fetchall()]

    if not hotel_ids:
        cursor.close(); conn.close()
        return jsonify({"success": True, "results": [], "total": 0,
                        "image_search": image_saved_path is not None})

    ph = ",".join(["%s"] * len(hotel_ids))
    params = list(hotel_ids)
    where_parts = []

    # ── Text search across all fields ───────────────────────────────────────
    if q:
        like = f"%{q}%"
        where_parts.append("""(
            gv.guest_name  LIKE %s
            OR gv.phone    LIKE %s
            OR gv.kyc_number LIKE %s
            OR h.hotel_name  LIKE %s
            OR gv.status     LIKE %s
            OR DATE_FORMAT(gv.submitted_at, '%%d %%b %%Y') LIKE %s
            OR DATE_FORMAT(gv.submitted_at, '%%Y-%%m-%%d') LIKE %s
        )""")
        params += [like, like, like, like, like, like, like]

    # ── Status filter ────────────────────────────────────────────────────────
    if status and status in ("approved", "pending", "rejected"):
        where_parts.append("gv.status = %s")
        params.append(status)

    # ── Date filter ──────────────────────────────────────────────────────────
    if date:
        where_parts.append("DATE(gv.submitted_at) = %s")
        params.append(date)

    # ── Image-only: return recent 20 with selfies ────────────────────────────
    if not where_parts:
        sql = f"""
            SELECT gv.id, gv.guest_name, gv.phone, gv.kyc_number, gv.status,
                   h.hotel_name, gv.selfie_path,
                   COALESCE(gv.aadhaar_path, gv.kyc_document_path),
                   gv.submitted_at
            FROM guest_verifications gv
            JOIN hotels h ON gv.hotel_id = h.id
            WHERE gv.hotel_id IN ({ph}) AND gv.selfie_path IS NOT NULL
            ORDER BY gv.submitted_at DESC LIMIT 20
        """
        cursor.execute(sql, hotel_ids)
    else:
        where_clause = " AND ".join(where_parts)
        sql = f"""
            SELECT gv.id, gv.guest_name, gv.phone, gv.kyc_number, gv.status,
                   h.hotel_name, gv.selfie_path,
                   COALESCE(gv.aadhaar_path, gv.kyc_document_path),
                   gv.submitted_at
            FROM guest_verifications gv
            JOIN hotels h ON gv.hotel_id = h.id
            WHERE gv.hotel_id IN ({ph}) AND ({where_clause})
            ORDER BY gv.submitted_at DESC
            LIMIT 200
        """
        cursor.execute(sql, params)

    rows = cursor.fetchall()
    cursor.close(); conn.close()

    def mask(val):
        s = str(val) if val else ""
        return "XXXX-XXXX-" + s[-4:] if len(s) >= 4 else "XXXX"

    def norm_path(p):
        if not p: return None
        p = p.replace("\\", "/").strip()
        if p.startswith("static/"):
            p = p[len("static/"):]
        if "/" not in p:
            p = "uploads/kyc_documents/" + p
        return p

    results = [{
        "id":         r[0],
        "guest_name": r[1],
        "phone":      r[2],
        "aadhaar":    mask(r[3]),
        "status":     r[4] or "pending",
        "hotel":      r[5],
        "selfie":     norm_path(r[6]),
        "doc":        norm_path(r[7]),
        "date":       r[8].strftime("%d %b %Y") if r[8] else "—",
        "datetime":   r[8].strftime("%Y-%m-%d") if r[8] else "",
    } for r in rows]

    PoliceUser.log_action(
        session["police_user_id"],
        f"Search: q={q!r} status={status!r} date={date!r} image={'yes' if image_saved_path else 'no'}",
        request.remote_addr
    )
    return jsonify({
        "success":      True,
        "results":      results,
        "total":        len(results),
        "image_search": image_saved_path is not None,
        "image_path":   "/" + image_saved_path.replace("\\", "/") if image_saved_path else None,
    })


# ─── Face Search via AWS Rekognition ─────────────────────────────────────────

@police_bp.route("/police/search-by-face", methods=["POST"])
@police_login_required
def search_by_face():
    """
    Compare an uploaded photo against all stored selfies for this station's hotels.
    Uses AWS Rekognition compare_faces.  Returns top matches (similarity >= 80 %).
    """
    import os
    from flask import jsonify

    try:
        from aws_rekognition import compare_faces
    except ImportError as e:
        return jsonify({"success": False, "message": f"aws_rekognition module error: {e}", "results": []})

    image = request.files.get("image")
    if not image or not image.filename:
        return jsonify({"success": False, "message": "No image uploaded.", "results": []})

    # Validate mime + size
    if image.mimetype not in {"image/jpeg", "image/jpg", "image/png"}:
        return jsonify({"success": False, "message": "Only JPG/PNG images allowed.", "results": []})
    image.seek(0, 2)
    if image.tell() > 5 * 1024 * 1024:
        return jsonify({"success": False, "message": "Image must be under 5 MB.", "results": []})
    image.seek(0)
    source_bytes = image.read()

    # Check AWS credentials are configured
    if not os.getenv("AWS_ACCESS_KEY") or not os.getenv("AWS_SECRET_KEY"):
        return jsonify({
            "success": False,
            "message": "AWS credentials not configured. Set AWS_ACCESS_KEY and AWS_SECRET_KEY in .env.",
            "results": []
        })

    try:
        # Get hotels for this station
        station_id = session["police_station_id"]
        conn   = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT h.id FROM hotels h
            JOIN police_station_hotels psh ON h.id = psh.hotel_id
            WHERE psh.station_id = %s
        """, (station_id,))
        hotel_ids = [r[0] for r in cursor.fetchall()]

        if not hotel_ids:
            cursor.close(); conn.close()
            return jsonify({"success": True, "results": [], "total": 0})

        ph = ",".join(["%s"] * len(hotel_ids))
        cursor.execute(f"""
            SELECT gv.id, gv.guest_name, gv.phone, gv.kyc_number, gv.status,
                   h.hotel_name, gv.selfie_path,
                   COALESCE(gv.aadhaar_path, gv.kyc_document_path),
                   gv.submitted_at
            FROM guest_verifications gv
            JOIN hotels h ON gv.hotel_id = h.id
            WHERE gv.hotel_id IN ({ph}) AND gv.selfie_path IS NOT NULL
            ORDER BY gv.submitted_at DESC
        """, hotel_ids)
        rows = cursor.fetchall()
        cursor.close(); conn.close()

    except Exception as e:
        return jsonify({"success": False, "message": f"Database error: {str(e)}", "results": []})

    def norm_path(p):
        if not p: return None
        p = p.replace("\\", "/").strip()
        if p.startswith("static/"): p = p[len("static/"):]
        if "/" not in p: p = "uploads/kyc_documents/" + p
        return p

    def mask(val):
        s = str(val) if val else ""
        return "XXXX-XXXX-" + s[-4:] if len(s) >= 4 else "XXXX"

    THRESHOLD   = 80.0
    matches     = []
    errors_seen = 0
    first_aws_error = None

    for r in rows:
        selfie_rel = norm_path(r[6])
        if not selfie_rel:
            continue
        disk_path = os.path.join("static", selfie_rel)
        result = compare_faces(source_bytes, disk_path, threshold=THRESHOLD)

        if result.get("error") and result["error"] not in ("no_face_detected", "target_not_found"):
            errors_seen += 1
            if first_aws_error is None:
                first_aws_error = result["error"]
            if errors_seen >= 3:
                break
            continue

        if result["matched"]:
            matches.append({
                "id":         r[0],
                "guest_name": r[1],
                "phone":      r[2],
                "aadhaar":    mask(r[3]),
                "status":     r[4] or "pending",
                "hotel":      r[5],
                "selfie":     selfie_rel,
                "doc":        norm_path(r[7]),
                "date":       r[8].strftime("%d %b %Y") if r[8] else "—",
                "similarity": result["similarity"],
            })

    # If AWS errored on every attempt, return a helpful message
    if errors_seen >= 3 and not matches:
        return jsonify({
            "success": False,
            "message": f"AWS Rekognition error: {first_aws_error}. Check your AWS credentials and region.",
            "results": []
        })

    matches.sort(key=lambda x: x["similarity"], reverse=True)
    matches = matches[:10]

    PoliceUser.log_action(
        session["police_user_id"],
        f"Face search: {len(matches)} match(es) from {len(rows)} records",
        request.remote_addr
    )
    return jsonify({
        "success":    True,
        "results":    matches,
        "total":      len(matches),
        "face_search": True,
    })
