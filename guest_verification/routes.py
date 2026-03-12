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
            # Fetch hotel data for error display
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
                                 hotel_logo=hotel_logo,
                                 error='Phone number must be exactly 10 digits (numbers only)')
        
        # Check wallet balance BEFORE accepting submission (if hotel_id exists)
        if hotel_id:
            from wallet.models import HotelWallet
            balance_check = HotelWallet.check_balance_for_verification(hotel_id)
            if not balance_check.get('sufficient', True):
                # Fetch hotel data for error display
                hotel_name = None
                hotel_logo = None
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
                                     hotel_logo=hotel_logo,
                                     error=f"Cannot submit verification: Insufficient wallet balance. Required: ₹{balance_check.get('charge', 0):.2f}, Available: ₹{balance_check.get('balance', 0):.2f}. Please contact restaurant management.")
        
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
            
            # Fetch hotel data for success page
            success_hotel_name = None
            success_hotel_logo = None
            if hotel_id:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT hotel_name, logo FROM hotels WHERE id = %s", (hotel_id,))
                    result_data = cursor.fetchone()
                    if result_data:
                        success_hotel_name = result_data[0]
                        success_hotel_logo = result_data[1]
                    cursor.close()
                    conn.close()
                except Exception as e:
                    print(f"Error fetching hotel data for success: {e}")
            
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
            
            return render_template('verification_success.html',
                                 hotel_name=success_hotel_name,
                                 hotel_logo=success_hotel_logo)
        else:
            # Fetch hotel data for error display
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
                                 hotel_logo=hotel_logo,
                                 error=result['message'])
    
    except Exception as e:
        print(f"Error in submit_verification: {e}")
        import traceback
        traceback.print_exc()
        
        # Fetch hotel data for error display
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
            except Exception as ex:
                print(f"Error fetching hotel data: {ex}")
        
        return render_template('guest_verification_form.html', 
                             manager_id=manager_id,
                             hotel_id=hotel_id,
                             hotel_name=hotel_name,
                             hotel_logo=hotel_logo,
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
                        hotel_name = result[0].strip()  # Remove any whitespace
                        print(f"[ROUTE] ✅ Found hotel name from DB: '{hotel_name}'")
                    else:
                        print(f"[ROUTE] ⚠️ No hotel found with ID {hotel_id}, using default: '{hotel_name}'")
                    
                    cursor.close()
                    conn.close()
                else:
                    print(f"[ROUTE] ⚠️ Invalid hotel_id, using default: '{hotel_name}'")
            except Exception as e:
                print(f"[ROUTE] ❌ Error fetching hotel name: {e}")
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