"""
OTP Service for Guest Mobile Verification
Handles OTP generation, verification, and expiry
"""
from database.db import get_db_connection
from mysql.connector import Error
from datetime import datetime, timedelta
import random
import requests
import os

class OTPService:
    """Service for managing OTP verification"""
    
    OTP_EXPIRY_MINUTES = 5
    MAX_ATTEMPTS = 3
    RESEND_COOLDOWN_SECONDS = 30
    
    @staticmethod
    def generate_otp():
        """Generate a 6-digit OTP"""
        return str(random.randint(100000, 999999))
    
    @staticmethod
    def send_otp_sms(phone_number, otp_code, hotel_name="VisiScure Order"):
        """
        Send OTP via MSG91 SMS API
        
        Args:
            phone_number: Mobile number (with country code 91)
            otp_code: 6-digit OTP code
            hotel_name: Name of the hotel/restaurant for ##var1## in template
            
        Returns:
            dict: {success: bool, message: str}
        """
        try:
            # Get MSG91 credentials from environment
            MSG91_AUTH_KEY = os.getenv('MSG91_AUTH_KEY', '451618A0Y44msLOxW685a4c6aP1')
            MSG91_TEMPLATE_ID = os.getenv('MSG91_TEMPLATE_ID', '69b244d394b176db2203e483')
            
            # Clean and format phone number
            original_phone = phone_number
            phone_number = phone_number.replace(' ', '').replace('-', '').replace('+', '')
            
            # Ensure phone number has country code 91
            if not phone_number.startswith('91'):
                phone_number = '91' + phone_number
            
            print(f"[MSG91] User entered mobile: {original_phone}")
            print(f"[MSG91] Formatted mobile: {phone_number}")
            print(f"[MSG91] Generated OTP: {otp_code}")
            print(f"[MSG91] Hotel name: {hotel_name}")
            
            # MSG91 OTP API endpoint (Send OTP) - Using GET method with query params
            # Template format: Welcome to ##var1##. Your verification OTP is ##OTP##. Please enter this code to complete guest verification. VisiScure Order
            # Variables: var1 = hotel_name, OTP = otp_code
            
            # URL encode the hotel name to handle spaces and special characters
            from urllib.parse import quote
            hotel_name_encoded = quote(hotel_name)
            
            url = f"https://control.msg91.com/api/v5/otp?template_id={MSG91_TEMPLATE_ID}&mobile={phone_number}&authkey={MSG91_AUTH_KEY}&var1={hotel_name_encoded}&otp={otp_code}"
            
            print(f"[MSG91] Hotel name (original): {hotel_name}")
            print(f"[MSG91] Hotel name (encoded): {hotel_name_encoded}")
            
            print(f"[MSG91] Sending request to: {url}")
            
            # Send OTP via MSG91 using GET request
            response = requests.get(url, timeout=10)
            
            print(f"[MSG91] Response Status: {response.status_code}")
            print(f"[MSG91] Response Body: {response.text}")
            
            # Check response
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    if response_data.get('type') == 'success':
                        request_id = response_data.get('request_id', 'N/A')
                        print(f"[MSG91] ✅ OTP sent successfully to {phone_number}")
                        print(f"[MSG91] Request ID: {request_id}")
                        return {
                            'success': True,
                            'message': 'OTP sent successfully to your mobile number',
                            'request_id': request_id,
                            'otp_debug': otp_code  # For development/testing
                        }
                    else:
                        error_msg = response_data.get('message', 'Unknown error')
                        print(f"[MSG91] ❌ API Error: {error_msg}")
                        return {
                            'success': False,
                            'message': f'Failed to send OTP: {error_msg}'
                        }
                except ValueError:
                    print(f"[MSG91] ❌ Invalid JSON response: {response.text}")
                    return {
                        'success': False,
                        'message': 'Invalid response from SMS service'
                    }
            else:
                print(f"[MSG91] ❌ HTTP Error: {response.status_code}")
                return {
                    'success': False,
                    'message': f'Failed to send OTP. Please try again. (Error: {response.status_code})'
                }
                
        except requests.exceptions.Timeout:
            print(f"[MSG91] ❌ Request timeout")
            return {
                'success': False,
                'message': 'Request timeout. Please check your internet connection and try again.'
            }
        except requests.exceptions.RequestException as e:
            print(f"[MSG91] ❌ Request error: {e}")
            return {
                'success': False,
                'message': f'Network error: {str(e)}'
            }
        except Exception as e:
            print(f"[MSG91] ❌ Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f'Failed to send OTP: {str(e)}'
            }
    
    @staticmethod
    def send_otp(phone_number, hotel_name="VisiScure Order"):
        """Send OTP to phone number via SMS with hotel name for ##var1##"""
        try:
            # Store original 10-digit number for database and display
            original_phone = phone_number.strip()
            
            # Format phone number (add country code 91)
            phone_for_api = original_phone
            if not phone_for_api.startswith('91'):
                phone_for_api = '91' + phone_for_api
            
            print(f"\n[OTP] User entered mobile: {original_phone}")
            print(f"[OTP] Formatted mobile: {phone_for_api}")
            print(f"[OTP] Hotel name: {hotel_name}")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check for recent OTP (cooldown period) - use original 10-digit number
            cursor.execute("""
                SELECT created_at FROM guest_otp_verifications 
                WHERE phone_number = %s 
                ORDER BY created_at DESC LIMIT 1
            """, (original_phone,))
            
            last_otp = cursor.fetchone()
            if last_otp:
                time_diff = (datetime.now() - last_otp[0]).total_seconds()
                if time_diff < OTPService.RESEND_COOLDOWN_SECONDS:
                    remaining = int(OTPService.RESEND_COOLDOWN_SECONDS - time_diff)
                    cursor.close()
                    conn.close()
                    return {
                        'success': False,
                        'message': f'Please wait {remaining} seconds before requesting a new OTP'
                    }
            
            # Generate new OTP
            otp_code = OTPService.generate_otp()
            expires_at = datetime.now() + timedelta(minutes=OTPService.OTP_EXPIRY_MINUTES)
            
            # Store OTP in database with original 10-digit number
            cursor.execute("""
                INSERT INTO guest_otp_verifications 
                (phone_number, otp_code, created_at, expires_at, attempts, verified)
                VALUES (%s, %s, %s, %s, 0, FALSE)
            """, (original_phone, otp_code, datetime.now(), expires_at))
            
            conn.commit()
            
            # Send OTP via SMS using formatted number with country code
            sms_result = OTPService.send_otp_sms(phone_for_api, otp_code, hotel_name)
            
            # In development mode, always log the OTP for testing
            print(f"[OTP DEBUG] Phone: {original_phone}, OTP: {otp_code}")
            print(f"[OTP DEBUG] SMS Result: {sms_result}")
            
            cursor.close()
            conn.close()
            
            # Return the SMS result directly
            return sms_result
        
        except Error as e:
            print(f"Database error in send_otp: {e}")
            return {
                'success': False,
                'message': 'Failed to send OTP. Please try again.'
            }
        except Exception as e:
            print(f"Error in send_otp: {e}")
            return {
                'success': False,
                'message': 'Failed to send OTP. Please try again.'
            }
    
    @staticmethod
    def verify_otp(phone_number, otp_code):
        """Verify OTP for phone number"""
        try:
            # Use original 10-digit number (strip any country code if present)
            original_phone = phone_number.strip()
            if original_phone.startswith('91') and len(original_phone) == 12:
                original_phone = original_phone[2:]  # Remove '91' prefix
            
            print(f"[OTP] Verifying OTP for mobile: {original_phone}")
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get latest OTP for this phone number
            cursor.execute("""
                SELECT id, otp_code, expires_at, attempts, verified
                FROM guest_otp_verifications
                WHERE phone_number = %s
                ORDER BY created_at DESC
                LIMIT 1
            """, (original_phone,))
            
            otp_record = cursor.fetchone()
            
            if not otp_record:
                cursor.close()
                conn.close()
                return {
                    'success': False,
                    'message': 'No OTP found for this phone number'
                }
            
            otp_id, stored_otp, expires_at, attempts, verified = otp_record
            
            # Check if already verified
            if verified:
                cursor.close()
                conn.close()
                return {
                    'success': True,
                    'message': 'Phone number already verified'
                }
            
            # Check if expired
            if datetime.now() > expires_at:
                cursor.close()
                conn.close()
                return {
                    'success': False,
                    'message': 'OTP has expired. Please request a new one.'
                }
            
            # Check max attempts
            if attempts >= OTPService.MAX_ATTEMPTS:
                cursor.close()
                conn.close()
                return {
                    'success': False,
                    'message': 'Maximum verification attempts exceeded. Please request a new OTP.'
                }
            
            # Verify OTP
            if otp_code == stored_otp:
                # Mark as verified
                cursor.execute("""
                    UPDATE guest_otp_verifications
                    SET verified = TRUE, attempts = attempts + 1
                    WHERE id = %s
                """, (otp_id,))
                conn.commit()
                cursor.close()
                conn.close()
                
                return {
                    'success': True,
                    'message': 'Phone number verified successfully!'
                }
            else:
                # Increment attempts
                cursor.execute("""
                    UPDATE guest_otp_verifications
                    SET attempts = attempts + 1
                    WHERE id = %s
                """, (otp_id,))
                conn.commit()
                
                remaining_attempts = OTPService.MAX_ATTEMPTS - (attempts + 1)
                cursor.close()
                conn.close()
                
                return {
                    'success': False,
                    'message': f'Invalid OTP. {remaining_attempts} attempts remaining.'
                }
        
        except Error as e:
            print(f"Database error in verify_otp: {e}")
            return {
                'success': False,
                'message': 'Failed to verify OTP. Please try again.'
            }
        except Exception as e:
            print(f"Error in verify_otp: {e}")
            return {
                'success': False,
                'message': 'Failed to verify OTP. Please try again.'
            }
    
    @staticmethod
    def check_verification_status(phone_number):
        """Check if phone number has been verified"""
        try:
            # Use original 10-digit number (strip any country code if present)
            original_phone = phone_number.strip()
            if original_phone.startswith('91') and len(original_phone) == 12:
                original_phone = original_phone[2:]  # Remove '91' prefix
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT verified, expires_at
                FROM guest_otp_verifications
                WHERE phone_number = %s AND verified = TRUE
                ORDER BY created_at DESC
                LIMIT 1
            """, (original_phone,))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if result and result[0]:
                return {
                    'success': True,
                    'verified': True,
                    'message': 'Phone number is verified'
                }
            else:
                return {
                    'success': True,
                    'verified': False,
                    'message': 'Phone number not verified'
                }
        
        except Exception as e:
            print(f"Error in check_verification_status: {e}")
            return {
                'success': False,
                'verified': False,
                'message': 'Failed to check verification status'
            }