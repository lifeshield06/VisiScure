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
            hn, hl = get_hotel_data(hotel_id)
            return render_template('guest_verification_form.html',
                                   manager_id=manager_id, hotel_id=hotel_id,
                                   hotel_name=hn, hotel_logo=hl,
                                   error='Mobile OTP verification is required before submitting.')
        
        # Validate required fields (relaxed for testing)
        print(f"\n[VALIDATION] Checking required fields...")
        if not guest_name:
            print(f"[VALIDATION] ❌ guest_name is missing")
            hotel_name, hotel_logo = get_hotel_data(hotel_id)
            return render_template('guest_verification_form.html', 
                                 manager_id=manager_id, 
                                 hotel_id=hotel_id,
                                 hotel_name=hotel_name,
                                 hotel_logo=hotel_logo,
                                 error='Guest name is required')
        
        if not phone:
            print(f"[VALIDATION] ❌ phone is missing")
            hotel_name, hotel_logo = get_hotel_data(hotel_id)
            return render_template('guest_verification_form.html', 
                                 manager_id=manager_id, 
                                 hotel_id=hotel_id,
                                 hotel_name=hotel_name,
                                 hotel_logo=hotel_logo,
                                 error='Phone number is required')
        
        # Validate phone: exactly 10 digits, numbers only
        if not phone.isdigit() or len(phone) != 10:
            print(f"[VALIDATION] ❌ phone format invalid: {phone}")
            hotel_name, hotel_logo = get_hotel_data(hotel_id)
            return render_template('guest_verification_form.html', 
                                 manager_id=manager_id, 
                                 hotel_id=hotel_id,
                                 hotel_name=hotel_name,
                                 hotel_logo=hotel_logo,
                                 error='Phone number must be exactly 10 digits (numbers only)')
        
        if not address:
            print(f"[VALIDATION] ❌ address is missing")
            hotel_name, hotel_logo = get_hotel_data(hotel_id)
            return render_template('guest_verification_form.html', 
                                 manager_id=manager_id, 
                                 hotel_id=hotel_id,
                                 hotel_name=hotel_name,
                                 hotel_logo=hotel_logo,
                                 error='Address is required')
        
        if not selfie_data:
            print(f"[VALIDATION] ❌ selfie_data is missing")
            hotel_name, hotel_logo = get_hotel_data(hotel_id)
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
                hotel_name, hotel_logo = get_hotel_data(hotel_id)
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
            hotel_id=hotel_id
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
            success_hotel_name, success_hotel_logo = get_hotel_data(hotel_id)
            return render_template('verification_success.html',
                                 hotel_name=success_hotel_name,
                                 hotel_logo=success_hotel_logo)
        else:
            print(f"\n[ERROR] ❌ Submission failed: {result['message']}")
            print("="*80 + "\n")
            hotel_name, hotel_logo = get_hotel_data(hotel_id)
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
        
        hotel_name, hotel_logo = get_hotel_data(hotel_id if 'hotel_id' in locals() else None)
        return render_template('guest_verification_form.html', 
                             manager_id=manager_id,
                             hotel_id=hotel_id if 'hotel_id' in locals() else None,
                             hotel_name=hotel_name,
                             hotel_logo=hotel_logo,
                             error=f"Error: {str(e)}")

def get_hotel_data(hotel_id):
    """Helper function to fetch hotel name and logo"""
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
    return hotel_name, hotel_logo

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