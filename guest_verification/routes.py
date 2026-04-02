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

@guest_verification_bp.route('/test-api')
def test_api_page():
    """Test page for verification API"""
    return render_template('test_verification_api.html')

@guest_verification_bp.route('/dashboard/<int:manager_id>')
def verification_dashboard(manager_id):
    """Verification dashboard for managers"""
    if not check_kyc_module():
        return jsonify({"success": False, "message": "Customer verification module not enabled for this hotel"}), 403
    
    hotel_id = session.get('hotel_id')
    
    # Get all verifications for this hotel
    verifications = GuestVerification.get_verifications_by_hotel(hotel_id)
    
    # Fetch hotel name and logo
    hotel_name = session.get('hotel_name')
    hotel_logo = None
    if hotel_id:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT hotel_name, logo FROM hotels WHERE id = %s", (hotel_id,))
            result = cursor.fetchone()
            if result:
                hotel_name = result[0]
                hotel_logo = result[1]
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error fetching hotel data: {e}")
    
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
                         hotel_name=hotel_name,
                         hotel_logo=hotel_logo,
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
    
    # Get hotel name and logo if hotel_id is available
    hotel_name = None
    hotel_logo = None
    if hotel_id:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT hotel_name, logo FROM hotels WHERE id = %s", (hotel_id,))
            result = cursor.fetchone()
            if result:
                hotel_name = result[0]
                hotel_logo = result[1]
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Error fetching hotel data: {e}")
    
    return render_template('guest_verification_form.html', 
                         manager_id=manager_id, 
                         hotel_id=hotel_id,
                         hotel_name=hotel_name,
                         hotel_logo=hotel_logo)

@guest_verification_bp.route('/submit/<int:manager_id>', methods=['POST'])
def submit_verification(manager_id):
    """Handle verification form submission with automatic wallet deduction"""
    try:
        # Get form data
        guest_name = request.form.get('guest_name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '')
        kyc_number = request.form.get('kyc_number', '')
        kyc_type = request.form.get('kyc_type', '')
        selfie_data = request.form.get('selfie_data', '')
        hotel_id = request.form.get('hotel_id') or request.args.get('hotel_id')
        print(f"[FORM DATA] selfie_data length: {len(selfie_data) if selfie_data else 0}")
        print(f"[FORM DATA] hotel_id from form: {request.form.get('hotel_id')}")
        print(f"[FORM DATA] hotel_id from args: {request.args.get('hotel_id')}")
        print(f"[FORM DATA] Combined hotel_id: {hotel_id}")
        
        # Check uploaded files
        print(f"[FILES] identity_file: {request.files.get('identity_file').filename if request.files.get('identity_file') else 'None'}")
        print(f"[FILES] aadhaar_file: {request.files.get('aadhaar_file').filename if request.files.get('aadhaar_file') else 'None'}")
        
        # Convert hotel_id to int or None
        if hotel_id:
            try:
                hotel_id = int(hotel_id)
            except (ValueError, TypeError):
                hotel_id = None
        else:
            hotel_id = None

        # ── OTP session check (server-side gate) ────────────────────────────
        verified_phone = session.get('otp_verified_phone')
        if not verified_phone or verified_phone != phone:
            hn, hl, *_ = get_hotel_data(hotel_id)
            return render_template('guest_verification_form.html',
                                   manager_id=manager_id, hotel_id=hotel_id,
                                   hotel_name=hn, hotel_logo=hl,
                                   error='Mobile OTP verification is required before submitting.')
        
        # Validate required fields (relaxed for testing)
        print(f"\n[VALIDATION] Checking required fields...")
        if not guest_name:
            print(f"[VALIDATION] ❌ guest_name is missing")
            hotel_name, hotel_logo, *_ = get_hotel_data(hotel_id)
            return render_template('guest_verification_form.html', 
                                 manager_id=manager_id, 
                                 hotel_id=hotel_id,
                                 hotel_name=hotel_name,
                                 hotel_logo=hotel_logo,
                                 error='Guest name is required')
        
        if not phone:
            print(f"[VALIDATION] ❌ phone is missing")
            hotel_name, hotel_logo, *_ = get_hotel_data(hotel_id)
            return render_template('guest_verification_form.html', 
                                 manager_id=manager_id, 
                                 hotel_id=hotel_id,
                                 hotel_name=hotel_name,
                                 hotel_logo=hotel_logo,
                                 error='Phone number is required')
        
        # Validate phone: exactly 10 digits, numbers only
        if not phone.isdigit() or len(phone) != 10:
            print(f"[VALIDATION] ❌ phone format invalid: {phone}")
            hotel_name, hotel_logo, *_ = get_hotel_data(hotel_id)
            return render_template('guest_verification_form.html', 
                                 manager_id=manager_id, 
                                 hotel_id=hotel_id,
                                 hotel_name=hotel_name,
                                 hotel_logo=hotel_logo,
                                 error='Phone number must be exactly 10 digits (numbers only)')
        
        if not address:
            print(f"[VALIDATION] ❌ address is missing")
            hotel_name, hotel_logo, *_ = get_hotel_data(hotel_id)
            return render_template('guest_verification_form.html', 
                                 manager_id=manager_id, 
                                 hotel_id=hotel_id,
                                 hotel_name=hotel_name,
                                 hotel_logo=hotel_logo,
                                 error='Address is required')
        
        if not selfie_data:
            print(f"[VALIDATION] ❌ selfie_data is missing")
            hotel_name, hotel_logo, *_ = get_hotel_data(hotel_id)
            return render_template('guest_verification_form.html', 
                                 manager_id=manager_id, 
                                 hotel_id=hotel_id,
                                 hotel_name=hotel_name,
                                 hotel_logo=hotel_logo,
                                 error='Selfie capture is required')
        
        print(f"[VALIDATION] ✅ All required fields present")
        
        # Check wallet balance BEFORE accepting submission (if hotel_id exists)
        if hotel_id:
            print(f"\n[WALLET] Checking balance for hotel_id={hotel_id}")
            from wallet.models import HotelWallet
            balance_check = HotelWallet.check_balance_for_verification(hotel_id)
            print(f"[WALLET] Balance check result: {balance_check}")
            if not balance_check.get('sufficient', True):
                print(f"[WALLET] ❌ Insufficient balance")
                hotel_name, hotel_logo, *_ = get_hotel_data(hotel_id)
                return render_template('guest_verification_form.html', 
                                     manager_id=manager_id, 
                                     hotel_id=hotel_id,
                                     hotel_name=hotel_name,
                                     hotel_logo=hotel_logo,
                                     error=f"Cannot submit verification: Insufficient wallet balance. Required: ₹{balance_check.get('charge', 0):.2f}, Available: ₹{balance_check.get('balance', 0):.2f}. Please contact restaurant management.")
            print(f"[WALLET] ✅ Sufficient balance")
        
        # Save selfie from base64
        print(f"\n[FILE PROCESSING] Saving selfie...")
        selfie_path = None
        if selfie_data:
            selfie_path = GuestVerification.save_selfie_from_base64(selfie_data, manager_id)
            print(f"[FILE PROCESSING] Selfie saved: {selfie_path}")
        else:
            print(f"[FILE PROCESSING] No selfie data")
        
        # Handle file upload (KYC document)
        print(f"[FILE PROCESSING] Processing KYC document...")
        identity_file = request.files.get('identity_file')
        file_path = None
        if identity_file and identity_file.filename:
            file_path = GuestVerification.save_uploaded_file(identity_file, manager_id)
            print(f"[FILE PROCESSING] KYC document saved: {file_path}")
        else:
            print(f"[FILE PROCESSING] No KYC document uploaded")
        
        # Handle Aadhaar file upload (OPTIONAL for testing)
        print(f"[FILE PROCESSING] Processing Aadhaar...")
        aadhaar_file = request.files.get('aadhaar_file')
        aadhaar_path = None
        if aadhaar_file and aadhaar_file.filename:
            aadhaar_path = GuestVerification.save_uploaded_file(aadhaar_file, manager_id, file_prefix='aadhaar')
            print(f"[FILE PROCESSING] Aadhaar saved: {aadhaar_path}")
        else:
            # Aadhaar is optional for testing - allow submission without it
            print(f"[FILE PROCESSING] ⚠️ Aadhaar not provided (allowing for testing)")
            aadhaar_path = None
        
        # Submit verification with selfie, KYC, and Aadhaar
        print(f"\n[DATABASE] Submitting verification to database...")
        print(f"[DATABASE] Parameters:")
        print(f"  - manager_id: {manager_id}")
        print(f"  - hotel_id: {hotel_id}")
        print(f"  - guest_name: {guest_name}")
        print(f"  - phone: {phone}")
        print(f"  - kyc_type: {kyc_type}")
        print(f"  - kyc_number: {kyc_number}")
        print(f"  - selfie_path: {selfie_path}")
        print(f"  - kyc_document_path: {file_path}")
        print(f"  - aadhaar_path: {aadhaar_path}")
        
        result = GuestVerification.submit_multistep_verification(
            manager_id=manager_id,
            guest_name=guest_name,
            phone=phone,
            address=address,
            kyc_number=kyc_number,
            kyc_type=kyc_type,
            selfie_path=selfie_path,
            kyc_document_path=file_path,
            aadhaar_path=aadhaar_path,
            hotel_id=hotel_id,
            pan_status=session.pop('pan_status', 'UNKNOWN'),
            api_name=session.pop('api_name', ''),
            name_match=session.pop('name_match', 'UNKNOWN'),
        )
        
        print(f"[DATABASE] Submission result: {result}")
        
        if result['success']:
            verification_id = result.get('id')
            
            print(f"\n[SUCCESS] ✅ Verification submitted successfully!")
            print(f"[SUCCESS] verification_id: {verification_id}")
            print(f"[SUCCESS] hotel_id: {hotel_id}")
            
            # Automatically deduct wallet balance on submission (if hotel_id exists)
            if hotel_id and verification_id:
                print(f"[WALLET DEDUCTION] Attempting deduction...")
                from wallet.models import HotelWallet
                deduct_result = HotelWallet.deduct_for_verification(hotel_id, verification_id)
                print(f"[WALLET DEDUCTION] Result: {deduct_result}")
                if not deduct_result.get('success'):
                    print(f"[WALLET DEDUCTION] ⚠️ Warning: {deduct_result.get('message')}")
            else:
                print(f"[WALLET DEDUCTION] Skipped (hotel_id={hotel_id}, verification_id={verification_id})")
            
            # Log activity with hotel_id
            if hotel_id:
                print(f"[ACTIVITY LOG] Logging activity...")
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
                    print(f"[ACTIVITY LOG] ✅ Activity logged")
                except Exception as e:
                    print(f"[ACTIVITY LOG] ❌ Error: {e}")
            
            # Clear OTP session after successful submission (one-time use)
            session.pop('otp_verified_phone', None)
            success_hotel_name, success_hotel_logo, success_hotel_address, success_hotel_phone, success_hotel_email, success_hotel_city, success_hotel_upi = get_hotel_data(hotel_id)
            return render_template('verification_success.html',
                                 hotel_name=success_hotel_name,
                                 hotel_logo=success_hotel_logo,
                                 hotel_address=success_hotel_address,
                                 hotel_phone=success_hotel_phone,
                                 hotel_email=success_hotel_email,
                                 hotel_city=success_hotel_city,
                                 hotel_upi=success_hotel_upi)
        else:
            print(f"\n[ERROR] ❌ Submission failed: {result['message']}")
            print("="*80 + "\n")
            hotel_name, hotel_logo, *_ = get_hotel_data(hotel_id)
            return render_template('guest_verification_form.html', 
                                 manager_id=manager_id,
                                 hotel_id=hotel_id,
                                 hotel_name=hotel_name,
                                 hotel_logo=hotel_logo,
                                 error=result['message'])
    
    except Exception as e:
        print(f"\n[EXCEPTION] ❌ Error in submit_verification: {e}")
        import traceback
        traceback.print_exc()
        print("="*80 + "\n")
        
        hotel_name, hotel_logo, *_ = get_hotel_data(hotel_id if 'hotel_id' in locals() else None)
        return render_template('guest_verification_form.html', 
                             manager_id=manager_id,
                             hotel_id=hotel_id if 'hotel_id' in locals() else None,
                             hotel_name=hotel_name,
                             hotel_logo=hotel_logo,
                             error=f"Error: {str(e)}")

def get_hotel_data(hotel_id):
    """Helper function to fetch hotel name, logo, and contact details"""
    hotel_name    = None
    hotel_logo    = None
    hotel_address = None
    hotel_phone   = None
    hotel_email   = None
    hotel_city    = None
    hotel_upi     = None
    if hotel_id:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            # Fetch all available columns safely
            cursor.execute("""
                SELECT hotel_name, logo, address, city,
                       IFNULL(phone, NULL)  AS phone,
                       IFNULL(email, NULL)  AS email,
                       IFNULL(upi_id, NULL) AS upi_id
                FROM hotels WHERE id = %s
            """, (hotel_id,))
            result = cursor.fetchone()
            if result:
                hotel_name    = result[0]
                hotel_logo    = result[1]
                hotel_address = result[2]
                hotel_city    = result[3]
                hotel_phone   = result[4]
                hotel_email   = result[5]
                hotel_upi     = result[6]
            cursor.close()
            conn.close()
        except Exception as e:
            # Fallback: try without optional columns
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT hotel_name, logo, address, city FROM hotels WHERE id = %s",
                    (hotel_id,)
                )
                result = cursor.fetchone()
                if result:
                    hotel_name    = result[0]
                    hotel_logo    = result[1]
                    hotel_address = result[2]
                    hotel_city    = result[3]
                cursor.close()
                conn.close()
            except Exception as e2:
                print(f"Error fetching hotel data: {e2}")
    return hotel_name, hotel_logo, hotel_address, hotel_phone, hotel_email, hotel_city, hotel_upi

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
        # Helper function to normalize file paths
        def normalize_path(file_path):
            if not file_path:
                return None
            # Convert backslashes to forward slashes
            file_path = file_path.replace('\\', '/')
            # Ensure path starts with /static/
            if file_path.startswith('static/'):
                return f"/{file_path}"
            elif not file_path.startswith('/static/'):
                return f"/static/uploads/kyc_documents/{file_path}"
            return file_path
        
        # Determine which image to show (prioritize new columns over old)
        kyc_image_path = None
        if len(v) > 11 and v[11]:  # kyc_document_path (new column)
            kyc_image_path = normalize_path(v[11])
        elif len(v) > 10 and v[10]:  # selfie_path (new column) 
            kyc_image_path = normalize_path(v[10])
        elif v[6]:  # identity_file (old column, fallback)
            kyc_image_path = normalize_path(v[6])
        
        verification_list.append({
            'id': v[0],
            'guest_name': v[1],
            'phone': v[2],
            'address': v[3],
            'kyc_number': v[4],
            'kyc_type': v[5] if v[5] else 'ID Document',  # kyc_type is at index 5
            'kyc_image': kyc_image_path,  # Use the determined image path
            'submitted_at': v[7].isoformat() if v[7] else None,  # submitted_at is at index 7
            'status': v[8],  # status is at index 8
            'selfie_path': normalize_path(v[10]) if len(v) > 10 and v[10] else None,  # selfie_path
            'kyc_document_path': normalize_path(v[11]) if len(v) > 11 and v[11] else None,  # kyc_document_path
            'aadhaar_path': normalize_path(v[12]) if len(v) > 12 and v[12] else None  # aadhaar_path
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

@guest_verification_bp.route('/api/send-otp', methods=['POST'])
def send_otp():
    """API endpoint to send OTP to phone number"""
    try:
        from .otp_service import OTPService
        
        data = request.json
        phone_number = data.get('phone_number', '').strip()
        hotel_id = data.get('hotel_id') or session.get('hotel_id')
        
        print("\n" + "="*70)
        print("SEND OTP REQUEST RECEIVED")
        print("="*70)
        print(f"[ROUTE] Original Input: {phone_number}")
        print(f"[ROUTE] Hotel ID: {hotel_id}")
        print(f"[ROUTE] Input Length: {len(phone_number)}")
        print(f"[ROUTE] Is Digit: {phone_number.isdigit()}")
        
        # Validate phone number
        if not phone_number or not phone_number.isdigit() or len(phone_number) != 10:
            print(f"[ROUTE] ❌ Validation Failed")
            print(f"[ROUTE] Expected: 10-digit number")
            print(f"[ROUTE] Got: {phone_number}")
            print("="*70 + "\n")
            return jsonify({
                'success': False,
                'message': 'Invalid phone number. Please enter a valid 10-digit number.'
            }), 400
        
        # Get hotel name from database dynamically for ##var1##
        hotel_name = "VisiScure Order"  # Default fallback
        
        print(f"[ROUTE] Hotel ID received: {hotel_id} (type: {type(hotel_id)})")
        
        if hotel_id:
            try:
                # Convert hotel_id to int if it's a string
                if isinstance(hotel_id, str):
                    hotel_id = int(hotel_id) if hotel_id.isdigit() else None
                
                if hotel_id:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT hotel_name FROM hotels WHERE id = %s", (hotel_id,))
                    result = cursor.fetchone()
                    
                    if result and result[0]:
                        fetched_name = result[0].strip()  # Remove any whitespace
                        # Only use fetched name if it's not empty
                        if fetched_name:
                            hotel_name = fetched_name
                            print(f"[ROUTE] ✅ Found hotel name from DB: '{hotel_name}'")
                        else:
                            print(f"[ROUTE] ⚠️ Hotel name is empty in DB for ID {hotel_id}, using default: '{hotel_name}'")
                    else:
                        print(f"[ROUTE] ⚠️ No hotel found with ID {hotel_id}, using default: '{hotel_name}'")
                    
                    cursor.close()
                    conn.close()
                else:
                    print(f"[ROUTE] ⚠️ Invalid hotel_id, using default: '{hotel_name}'")
            except Exception as e:
                print(f"[ROUTE] ❌ Error fetching hotel name: {e}")
                import traceback
                traceback.print_exc()
                print(f"[ROUTE] Using default hotel name: '{hotel_name}'")
        else:
            print(f"[ROUTE] ⚠️ No hotel_id provided, using default: '{hotel_name}'")
        
        print(f"[ROUTE] ✅ Validation Passed")
        print(f"[ROUTE] Using hotel name: {hotel_name}")
        print(f"[ROUTE] Calling OTPService.send_otp('{phone_number}', '{hotel_name}')")
        print("="*70)
        
        # Send OTP with hotel name
        result = OTPService.send_otp(phone_number, hotel_name)
        
        print("\n" + "="*70)
        print("SEND OTP RESULT")
        print("="*70)
        print(f"[ROUTE] Success: {result.get('success')}")
        print(f"[ROUTE] Message: {result.get('message')}")
        if 'otp_debug' in result:
            print(f"[ROUTE] 🔐 DEBUG OTP: {result.get('otp_debug')}")
        print("="*70 + "\n")
        
        return jsonify(result)
    
    except Exception as e:
        print(f"\n[ROUTE] ❌ ERROR in send_otp: {e}")
        import traceback
        traceback.print_exc()
        print("\n")
        return jsonify({
            'success': False,
            'message': f'Failed to send OTP: {str(e)}'
        }), 500

@guest_verification_bp.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    """API endpoint to verify OTP"""
    try:
        from .otp_service import OTPService
        
        data = request.json
        phone_number = data.get('phone_number', '').strip()
        otp_code = data.get('otp_code', '').strip()
        
        # Validate inputs
        if not phone_number or not otp_code:
            return jsonify({
                'success': False,
                'message': 'Phone number and OTP are required.'
            }), 400
        
        if not otp_code.isdigit() or len(otp_code) != 6:
            return jsonify({
                'success': False,
                'message': 'Invalid OTP format. Please enter a 6-digit code.'
            }), 400
        
        # Verify OTP
        result = OTPService.verify_otp(phone_number, otp_code)

        # On success, store verified phone in session so backend can gate submission
        if result.get('success'):
            session['otp_verified_phone'] = phone_number
            session.modified = True

        return jsonify(result)
    
    except Exception as e:
        print(f"Error in verify_otp: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'Failed to verify OTP: {str(e)}'
        }), 500

@guest_verification_bp.route('/api/check-otp-status', methods=['POST'])
def check_otp_status():
    """API endpoint to check if phone number has verified OTP"""
    try:
        from .otp_service import OTPService
        
        data = request.json
        phone_number = data.get('phone_number', '').strip()
        
        if not phone_number:
            return jsonify({
                'success': False,
                'message': 'Phone number is required.'
            }), 400
        
        # Check OTP status
        result = OTPService.check_verification_status(phone_number)
        
        return jsonify(result)
    
    except Exception as e:
        print(f"Error in check_otp_status: {e}")
        return jsonify({
            'success': False,
            'message': f'Failed to check OTP status: {str(e)}'
        }), 500

@guest_verification_bp.route('/success')
def verification_success():
    """Success page after verification submission"""
    return render_template('verification_success.html')


# ─── OCR Document Upload Verification ────────────────────────────────────────

@guest_verification_bp.route('/api/verify-upload', methods=['POST'])
def verify_upload():
    """OCR-based document verification: extract name and match with user input."""
    from .ocr_service import (
        allowed_file, save_document, extract_text, extract_name,
        match_names, MAX_BYTES
    )

    file      = request.files.get('file')
    user_name = (request.form.get('user_name') or '').strip()
    doc_type  = (request.form.get('doc_type') or '').strip()

    if not user_name:
        return jsonify({'success': False, 'status': 'NAME_REQUIRED',
                        'message': 'Please enter your Full Name before verification.'}), 400

    if not file or not file.filename:
        return jsonify({'success': False, 'status': 'ERROR', 'message': 'No file uploaded.'})

    if not allowed_file(file.filename):
        return jsonify({'success': False, 'status': 'ERROR',
                        'message': 'Invalid file type. Only PNG, JPG, PDF allowed.'})

    # Check size
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_BYTES:
        return jsonify({'success': False, 'status': 'ERROR',
                        'message': 'File exceeds 5 MB limit.'})

    try:
        file_path = save_document(file)
    except Exception as e:
        return jsonify({'success': False, 'status': 'ERROR',
                        'message': f'Failed to save file: {e}'})

    # Image quality check (selfie detection, blur, brightness)
    from .ocr_service import check_image_quality
    qc = check_image_quality(file_path)
    if not qc['ok']:
        return jsonify({'success': False, 'status': 'INVALID', 'message': qc['reason']})

    try:
        from .ocr_service import _surepass_name_cache
        _surepass_name_cache['doc_type'] = doc_type  # pass doc_type for endpoint selection
        raw_text   = extract_text(file_path)
        doc_name   = extract_name(doc_type, raw_text)
        result     = match_names(user_name, doc_name)
    except Exception as e:
        import traceback
        err_detail = traceback.format_exc()
        print(f"[OCR ERROR] {err_detail}")
        return jsonify({
            'success': True,
            'status': 'RETRY',
            'message': f'OCR error: {str(e)} — Please try uploading a clearer image.',
            'doc_name': '',
            'debug': str(e)
        })

    # Persist to DB
    try:
        conn   = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_verifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255),
                doc_type VARCHAR(100),
                file_path VARCHAR(500),
                extracted_name VARCHAR(255),
                verification_status VARCHAR(20),
                created_at DATETIME DEFAULT NOW()
            )
        """)
        cursor.execute("""
            INSERT INTO document_verifications
                (name, doc_type, file_path, extracted_name, verification_status)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_name, doc_type, file_path, result['doc_name'], result['status']))
        conn.commit()
        cursor.close(); conn.close()
    except Exception as e:
        print(f"[OCR DB] Error: {e}")

    # Store in session for form submission
    session.update(
        pan_status=result['status'],
        name_match='MATCHED' if result['status'] == 'VERIFIED' else result['status'],
        api_name=result['doc_name'],
        kyc_status=result['status']
    )

    return jsonify({
        'success': True,
        'status':  result['status'],
        'message': result['message'],
        'doc_name': result['doc_name']
    })


# ─── Unified Document Verification (PAN / Aadhaar / DL / Voter / Passport) ───

# Keep old route as alias for backward compat
@guest_verification_bp.route('/api/verify-pan', methods=['POST'])
def verify_pan():
    data = request.json or {}
    data['doc_type'] = 'PAN Card'
    data['doc_number'] = data.get('pan_number', '')
    data['user_name'] = data.get('name', '')
    return _verify_document(data)


@guest_verification_bp.route('/api/verify-document', methods=['POST'])
def verify_document():
    return _verify_document(request.json or {})


def _verify_document(data):
    import os, re, requests as req
    from dotenv import load_dotenv
    load_dotenv(override=True)

    doc_type   = data.get('doc_type', '').strip()
    doc_number = data.get('doc_number', '').strip().upper()
    user_name  = data.get('user_name', '').strip()

    # Block verification if name is missing
    if not user_name:
        return jsonify({'success': False, 'doc_status': 'NAME_REQUIRED',
                        'name_match': 'NAME_REQUIRED', 'api_name': '',
                        'kyc_status': 'PENDING',
                        'message': 'Please enter your Full Name before verification.'}), 400

    # ── Aadhaar: no direct number-lookup API (OTP-based only) ────────────────
    if doc_type == 'Aadhaar Card':
        if not re.match(r'^\d{12}$', doc_number):
            return jsonify({'success': False, 'doc_status': 'INVALID',
                            'message': 'Invalid Aadhaar number. Must be 12 digits.'})
        session.update(pan_status='UNKNOWN', name_match='UNKNOWN', api_name='', kyc_status='PENDING')
        return jsonify({'success': True, 'doc_status': 'UNKNOWN', 'name_match': 'UNKNOWN',
                        'api_name': '', 'kyc_status': 'PENDING',
                        'message': 'Aadhaar number recorded. Will be verified manually by hotel staff.'})

    # ── API endpoint map ──────────────────────────────────────────────────────
    API_MAP = {
        'PAN Card':        'https://kyc-api.surepass.io/api/v1/pan/pan',
        'Driving License': 'https://kyc-api.surepass.io/api/v1/driving-license/driving-license',
        'Voter ID':        'https://kyc-api.surepass.io/api/v1/voter-id/voter-id',
        'Passport':        'https://kyc-api.surepass.io/api/v1/passport/passport',
    }

    # ── Format validation ─────────────────────────────────────────────────────
    PATTERNS = {
        'PAN Card':        r'^[A-Z]{5}[0-9]{4}[A-Z]$',
        'Aadhaar Card':    r'^\d{12}$',
        'Driving License': r'^[A-Z]{2}\d{2}\s?\d{11}$',
        'Voter ID':        r'^[A-Z]{3}\d{7}$',
        'Passport':        r'^[A-Z]\d{7}$',
    }

    if doc_type not in API_MAP:
        return jsonify({'success': False, 'doc_status': 'ERROR',
                        'message': f'Unsupported document type: {doc_type}'})

    pat = PATTERNS.get(doc_type)
    if pat and not re.match(pat, doc_number):
        return jsonify({'success': False, 'doc_status': 'INVALID',
                        'message': f'Invalid {doc_type} format'})

    token = os.getenv('SUREPASS_TOKEN', '').strip()
    if not token or token == 'your_surepass_bearer_token':
        session.update(doc_status='UNKNOWN', name_match='UNKNOWN', api_name='', kyc_status='PENDING')
        return jsonify({'success': True, 'doc_status': 'UNKNOWN', 'name_match': 'UNKNOWN',
                        'api_name': '', 'kyc_status': 'PENDING',
                        'message': 'Verification API not configured. Marked as Pending.'})

    try:
        resp = req.post(
            API_MAP[doc_type],
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json={'id_number': doc_number},
            timeout=10
        )
        print(f"[SUREPASS:{doc_type}] status={resp.status_code} raw={resp.text[:300]}")
        try:
            result = resp.json()
        except Exception:
            print(f"[SUREPASS:{doc_type}] Non-JSON response (status={resp.status_code}): {resp.text[:500]}")
            session.update(pan_status='UNKNOWN', name_match='UNKNOWN', api_name='', kyc_status='PENDING')
            if resp.status_code == 401:
                msg = 'Verification API token expired or invalid. Marked as Pending.'
            elif resp.status_code == 403:
                msg = 'Verification API access denied. Marked as Pending.'
            elif resp.status_code == 422:
                msg = 'Invalid document number format. Marked as Pending.'
            else:
                msg = f'Verification API error (HTTP {resp.status_code}). Marked as Pending.'
            return jsonify({'success': True, 'doc_status': 'UNKNOWN', 'name_match': 'UNKNOWN',
                            'api_name': '', 'kyc_status': 'PENDING', 'message': msg})
        print(f"[SUREPASS:{doc_type}] response={result}")

        if result.get('success'):
            d = result.get('data') or {}
            # Try all known name fields across different Surepass endpoints
            api_name = (
                d.get('name') or d.get('full_name') or d.get('pan_holder_name') or
                d.get('holder_name') or d.get('name_on_card') or
                (d.get('first_name', '') + ' ' + d.get('last_name', '')).strip() or ''
            ).strip()
            print(f"[SUREPASS:{doc_type}] api_name='{api_name}' keys={list(d.keys())}")

            # Name is mandatory — block if not provided
            if not user_name:
                session.update(pan_status='NAME_REQUIRED', name_match='NAME_REQUIRED',
                               api_name=api_name, kyc_status='PENDING')
                return jsonify({'success': False, 'doc_status': 'NAME_REQUIRED',
                                'name_match': 'NAME_REQUIRED', 'api_name': api_name,
                                'kyc_status': 'PENDING',
                                'message': 'Please enter your Full Name before verification.'})

            doc_status = 'VALID'
            if api_name:
                u = ' '.join(user_name.lower().split())
                a = ' '.join(api_name.lower().split())
                # Allow minor variations: word-overlap similarity
                u_words = set(u.split()); a_words = set(a.split())
                overlap = len(u_words & a_words)
                sim = overlap / max(len(u_words), len(a_words)) if (u_words and a_words) else 0
                if sim >= 0.7:
                    name_match = 'MATCHED'; kyc_status = 'VERIFIED'
                    message = f'Document Verified ✔ (Name: {api_name}) ✅ Name Matched'
                else:
                    name_match = 'MISMATCH'; kyc_status = 'REVIEW'
                    message = f'Name does not match document — Document shows: "{api_name}"'
            else:
                name_match = 'UNKNOWN'; kyc_status = 'VERIFIED'
                message = 'Document Verified ✔ (Name not available in registry)'
        else:
            api_name = ''; doc_status = 'INVALID'; name_match = 'UNKNOWN'; kyc_status = 'PENDING'
            message = result.get('message', 'Document verification failed')

    except req.exceptions.ConnectionError as e:
        print(f"[SUREPASS:{doc_type}] ConnectionError: {e}")
        api_name = ''; doc_status = 'UNKNOWN'; name_match = 'UNKNOWN'; kyc_status = 'PENDING'
        message = 'Cannot reach verification API. Marked as Pending.'
    except req.exceptions.Timeout as e:
        print(f"[SUREPASS:{doc_type}] Timeout: {e}")
        api_name = ''; doc_status = 'UNKNOWN'; name_match = 'UNKNOWN'; kyc_status = 'PENDING'
        message = 'Verification API timed out. Marked as Pending.'
    except req.exceptions.JSONDecodeError as e:
        print(f"[SUREPASS:{doc_type}] JSONDecodeError (non-JSON response): {e}")
        api_name = ''; doc_status = 'UNKNOWN'; name_match = 'UNKNOWN'; kyc_status = 'PENDING'
        message = 'Verification API returned invalid response. Marked as Pending.'
    except Exception as e:
        import traceback
        print(f"[SUREPASS:{doc_type}] Unexpected Exception: {type(e).__name__}: {e}")
        traceback.print_exc()
        api_name = ''; doc_status = 'UNKNOWN'; name_match = 'UNKNOWN'; kyc_status = 'PENDING'
        message = f'Verification API unavailable. Marked as Pending.'

    session.update(pan_status=doc_status, name_match=name_match,
                   api_name=api_name, kyc_status=kyc_status)
    return jsonify({'success': True, 'doc_status': doc_status, 'pan_status': doc_status,
                    'name_match': name_match, 'api_name': api_name,
                    'kyc_status': kyc_status, 'message': message})


# ─── Manager: Approve / Reject verification ───────────────────────────────────

@guest_verification_bp.route('/api/approve/<int:verification_id>', methods=['POST'])
def approve_verification(verification_id):
    from flask import jsonify
    if not session.get('manager_id') and not session.get('police_user_id'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    result = GuestVerification.update_status(verification_id, 'approved')
    return jsonify(result)


@guest_verification_bp.route('/api/reject/<int:verification_id>', methods=['POST'])
def reject_verification(verification_id):
    from flask import jsonify
    if not session.get('manager_id') and not session.get('police_user_id'):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    result = GuestVerification.update_status(verification_id, 'rejected')
    return jsonify(result)


# ─── New hotel-id-based public form ──────────────────────────────────────────

@guest_verification_bp.route('/submit/<int:hotel_id>', methods=['GET'])
def submit_form(hotel_id):
    hotel_name, hotel_logo, *_ = get_hotel_data(hotel_id)
    return render_template('guest_verification_submit.html',
                           hotel_id=hotel_id, hotel_name=hotel_name, hotel_logo=hotel_logo)


@guest_verification_bp.route('/submit/<int:hotel_id>', methods=['POST'])
def submit_form_post(hotel_id):
    try:
        name        = request.form.get('name', '').strip()
        phone       = request.form.get('phone', '').strip()
        selfie_data = request.form.get('selfie_data', '')
        hotel_name, hotel_logo, *_ = get_hotel_data(hotel_id)

        def _err(msg):
            return render_template('guest_verification_submit.html',
                                   hotel_id=hotel_id, hotel_name=hotel_name,
                                   hotel_logo=hotel_logo, error=msg)

        if not name:                                    return _err('Full name is required.')
        if not phone or not phone.isdigit() or len(phone) != 10:
                                                        return _err('Enter a valid 10-digit phone number.')
        if not selfie_data:                             return _err('Selfie capture is required.')

        selfie_path = GuestVerification.save_selfie_from_base64(selfie_data, hotel_id)
        conn   = get_db_connection()
        cursor = conn.cursor()
        # Ensure pan_status column exists
        cursor.execute("SHOW COLUMNS FROM guest_verifications LIKE 'pan_status'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE guest_verifications ADD COLUMN pan_status VARCHAR(20) DEFAULT 'not_checked'")
            conn.commit()
        cursor.execute("""
            INSERT INTO guest_verifications
                (hotel_id, guest_name, phone, selfie_path, pan_status, status, submitted_at)
            VALUES (%s, %s, %s, %s, 'not_checked', 'pending', NOW())
        """, (hotel_id, name, phone, selfie_path))
        conn.commit(); cursor.close(); conn.close()
        return render_template('verification_success.html',
                               hotel_name=hotel_name, hotel_logo=hotel_logo)
    except Exception as e:
        hotel_name, hotel_logo, *_ = get_hotel_data(hotel_id)
        return render_template('guest_verification_submit.html',
                               hotel_id=hotel_id, hotel_name=hotel_name,
                               hotel_logo=hotel_logo, error=str(e))


# ─── Hotel-filtered verifications API ────────────────────────────────────────

@guest_verification_bp.route('/api/verifications-by-hotel/<int:hotel_id>')
def api_verifications_by_hotel(hotel_id):
    from flask import jsonify
    if session.get('hotel_id') != hotel_id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    try:
        conn   = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, guest_name, phone, selfie_path, status, submitted_at
            FROM   guest_verifications
            WHERE  hotel_id = %s
            ORDER  BY submitted_at DESC
        """, (hotel_id,))
        rows = cursor.fetchall()
        cursor.close(); conn.close()
        for row in rows:
            if row.get('submitted_at'):
                row['submitted_at'] = row['submitted_at'].isoformat()
            sp = row.get('selfie_path')
            if sp:
                sp = sp.replace('\\', '/')
                if not sp.startswith('/'): sp = '/' + sp
                row['selfie_path'] = sp
        return jsonify({'success': True, 'verifications': rows})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500