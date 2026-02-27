from flask import request, jsonify, render_template, redirect, url_for, send_file, session
from . import guest_verification_bp
from .models import GuestVerification
import qrcode
import io
import base64
from urllib.parse import urljoin
from database.db import get_db_connection

def check_kyc_module():
    """Check if KYC module is enabled for this manager's hotel"""
    if not session.get('manager_id'):
        return False
    return session.get('kyc_enabled', False)

@guest_verification_bp.route('/dashboard/<int:manager_id>')
def verification_dashboard(manager_id):
    """Verification dashboard for managers"""
    if not check_kyc_module():
        return jsonify({"success": False, "message": "Customer verification module not enabled for this hotel"}), 403
    
    hotel_id = session.get('hotel_id')
    
    # Get all verifications for this hotel
    verifications = GuestVerification.get_verifications_by_hotel(hotel_id)
    
    # Generate QR code for public form (using hotel_id for hotel-specific form)
    public_url = f"{request.url_root}guest-verification/form/{manager_id}?hotel_id={hotel_id}"
    
    # Create QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(public_url)
    qr.make(fit=True)
    
    # Convert QR to base64 image
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    qr_code_base64 = base64.b64encode(img_buffer.getvalue()).decode()
    
    return render_template('verification_dashboard.html', 
                         manager_id=manager_id,
                         hotel_id=hotel_id,
                         verifications=verifications,
                         public_url=public_url,
                         qr_code=qr_code_base64)

@guest_verification_bp.route('/form/<int:manager_id>')
def public_form(manager_id):
    """Public guest verification form"""
    hotel_id = request.args.get('hotel_id')
    
    # Convert to int if present
    if hotel_id:
        try:
            hotel_id = int(hotel_id)
        except (ValueError, TypeError):
            hotel_id = None
    
    # Get hotel name if hotel_id is available
    hotel_name = None
    if hotel_id:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT hotel_name FROM hotels WHERE id = %s", (hotel_id,))
            result = cursor.fetchone()
            if result:
                hotel_name = result[0]
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error fetching hotel name: {e}")
    
    return render_template('guest_verification_form.html', 
                         manager_id=manager_id, 
                         hotel_id=hotel_id,
                         hotel_name=hotel_name)

@guest_verification_bp.route('/submit/<int:manager_id>', methods=['POST'])
def submit_verification(manager_id):
    """Handle verification form submission with automatic wallet deduction"""
    try:
        # Get form data
        guest_name = request.form.get('guest_name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address')
        kyc_number = request.form.get('kyc_number')
        kyc_type = request.form.get('kyc_type')  # Get the selected ID type
        hotel_id = request.form.get('hotel_id') or request.args.get('hotel_id')
        
        print(f"[VERIFICATION SUBMIT] Raw hotel_id from form: {request.form.get('hotel_id')}")
        print(f"[VERIFICATION SUBMIT] Raw hotel_id from args: {request.args.get('hotel_id')}")
        print(f"[VERIFICATION SUBMIT] Combined hotel_id: {hotel_id}")
        
        # Convert hotel_id to int or None
        if hotel_id:
            try:
                hotel_id = int(hotel_id)
                print(f"[VERIFICATION SUBMIT] Converted hotel_id to int: {hotel_id}")
            except (ValueError, TypeError):
                hotel_id = None
                print(f"[VERIFICATION SUBMIT] Failed to convert hotel_id to int, set to None")
        else:
            hotel_id = None
            print(f"[VERIFICATION SUBMIT] hotel_id is empty, set to None")
        
        # Validate phone: exactly 10 digits, numbers only
        if not phone.isdigit() or len(phone) != 10:
            return render_template('guest_verification_form.html', 
                                 manager_id=manager_id, 
                                 hotel_id=hotel_id,
                                 error='Phone number must be exactly 10 digits (numbers only)')
        
        # Check wallet balance BEFORE accepting submission (if hotel_id exists)
        if hotel_id:
            from wallet.models import HotelWallet
            balance_check = HotelWallet.check_balance_for_verification(hotel_id)
            if not balance_check.get('sufficient', True):
                return render_template('guest_verification_form.html', 
                                     manager_id=manager_id, 
                                     hotel_id=hotel_id,
                                     error=f"Cannot submit verification: Insufficient wallet balance. Required: ₹{balance_check.get('charge', 0):.2f}, Available: ₹{balance_check.get('balance', 0):.2f}. Please contact hotel management.")
        
        # Handle file upload
        identity_file = request.files.get('identity_file')
        file_path = None
        
        if identity_file and identity_file.filename:
            file_path = GuestVerification.save_uploaded_file(identity_file, manager_id)
        
        # Submit verification with hotel_id and kyc_type (use file_path, not identity_file)
        result = GuestVerification.submit_verification(
            manager_id, guest_name, phone, address, kyc_number, file_path, hotel_id, kyc_type
        )
        
        if result['success']:
            verification_id = result.get('id')
            
            print(f"[VERIFICATION] Submission successful - verification_id: {verification_id}, hotel_id: {hotel_id}")
            
            # Automatically deduct wallet balance on submission (if hotel_id exists)
            if hotel_id and verification_id:
                print(f"[VERIFICATION] Attempting wallet deduction for hotel_id={hotel_id}, verification_id={verification_id}")
                from wallet.models import HotelWallet
                deduct_result = HotelWallet.deduct_for_verification(hotel_id, verification_id)
                print(f"[VERIFICATION] Deduction result: {deduct_result}")
                if not deduct_result.get('success'):
                    print(f"[VERIFICATION] Warning: Verification submitted but wallet deduction failed: {deduct_result.get('message')}")
            else:
                print(f"[VERIFICATION] Skipping wallet deduction - hotel_id={hotel_id}, verification_id={verification_id}")
            
            # Log activity with hotel_id
            if hotel_id:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO recent_activities (activity_type, message, hotel_id, role) VALUES (%s, %s, %s, %s)",
                        ('verification', f"Guest '{guest_name}' completed ID verification", hotel_id, 'manager')
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
                except Exception as e:
                    print(f"Error logging activity: {e}")
            
            return render_template('verification_success.html')
        else:
            return render_template('guest_verification_form.html', 
                                 manager_id=manager_id,
                                 hotel_id=hotel_id,
                                 error=result['message'])
    
    except Exception as e:
        print(f"Error in submit_verification: {e}")
        import traceback
        traceback.print_exc()
        return render_template('guest_verification_form.html', 
                             manager_id=manager_id, 
                             error=f"Error: {str(e)}")

@guest_verification_bp.route('/update-status', methods=['POST'])
def update_status():
    """Update verification status (AJAX)"""
    data = request.json
    result = GuestVerification.update_status(
        data.get('verification_id'), 
        data.get('status')
    )
    return jsonify(result)

@guest_verification_bp.route('/download-qr/<int:manager_id>')
def download_qr(manager_id):
    """Download QR code as PNG file"""
    # Get hotel_id from session to include in QR code URL
    hotel_id = session.get('hotel_id')
    
    # Generate public URL with hotel_id parameter
    public_url = f"{request.url_root}guest-verification/form/{manager_id}?hotel_id={hotel_id}"
    
    # Create QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(public_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    return send_file(img_buffer, 
                     mimetype='image/png',
                     as_attachment=True,
                     download_name=f'verification_qr_manager_{manager_id}.png')

@guest_verification_bp.route('/api/verifications/<int:manager_id>')
def api_get_verifications(manager_id):
    """API endpoint to get verifications for AJAX calls"""
    # Get hotel_id from session for hotel-specific filtering
    hotel_id = session.get('hotel_id')
    
    print(f"[API] Fetching verifications - manager_id: {manager_id}, hotel_id: {hotel_id}")
    
    # Always fetch by manager_id first, then filter by hotel if needed
    verifications = GuestVerification.get_verifications_by_manager(manager_id)
    
    print(f"[API] Found {len(verifications)} verifications for manager {manager_id}")
    
    # If hotel_id is set, filter to only show verifications for this hotel
    # But also include verifications where hotel_id is NULL (legacy data)
    if hotel_id:
        filtered_verifications = []
        for v in verifications:
            v_hotel_id = v[9] if len(v) > 9 else None  # hotel_id is at index 9
            if v_hotel_id == hotel_id or v_hotel_id is None:
                filtered_verifications.append(v)
        verifications = filtered_verifications
        print(f"[API] After hotel filtering: {len(verifications)} verifications")
    
    # Convert to JSON-serializable format with named properties
    verification_list = []
    for v in verifications:
        verification_list.append({
            'id': v[0],
            'guest_name': v[1],
            'phone': v[2],
            'address': v[3],
            'kyc_number': v[4],
            'kyc_type': v[5] if v[5] else 'ID Document',  # kyc_type is at index 5
            'kyc_image': f"/static/{v[6]}" if v[6] else None,  # identity_file is at index 6
            'submitted_at': v[7].isoformat() if v[7] else None,  # submitted_at is at index 7
            'status': v[8]  # status is at index 8
        })
    
    print(f"[API] Returning {len(verification_list)} verifications")
    return jsonify({'verifications': verification_list})

@guest_verification_bp.route('/api/qr-code/<int:manager_id>')
def api_get_qr_code(manager_id):
    """API endpoint to get QR code data for AJAX calls"""
    # Get hotel_id from session to include in QR code URL
    hotel_id = session.get('hotel_id')
    
    # Generate public URL with hotel_id parameter
    public_url = f"{request.url_root}guest-verification/form/{manager_id}?hotel_id={hotel_id}"
    
    # Create QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(public_url)
    qr.make(fit=True)
    
    # Convert QR to base64 image
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    qr_code_base64 = base64.b64encode(img_buffer.getvalue()).decode()
    
    return jsonify({
        'qr_code': qr_code_base64,
        'public_url': public_url
    })