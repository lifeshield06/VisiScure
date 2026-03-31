"""
Guest Verification Models
Handles database operations for guest KYC verification
"""
import os
from werkzeug.utils import secure_filename
from database.db import get_db_connection
from mysql.connector import Error
from datetime import datetime

class GuestVerification:
    """Model for managing guest verification records"""
    
    UPLOAD_FOLDER = 'static/uploads/kyc_documents'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
    
    @staticmethod
    def create_table():
        """Create guest_verifications table if not exists"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS guest_verifications (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    manager_id INT NOT NULL,
                    hotel_id INT,
                    guest_name VARCHAR(255) NOT NULL,
                    phone VARCHAR(20) NOT NULL,
                    address TEXT NOT NULL,
                    kyc_number VARCHAR(100) NOT NULL,
                    kyc_type VARCHAR(50) DEFAULT 'ID Document',
                    identity_file VARCHAR(500),
                    selfie_path VARCHAR(500),
                    kyc_document_path VARCHAR(500),
                    aadhaar_path VARCHAR(500),
                    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (manager_id) REFERENCES managers(id) ON DELETE CASCADE,
                    FOREIGN KEY (hotel_id) REFERENCES hotels(id) ON DELETE CASCADE
                )
            """)
            
            # Ensure kyc_type column exists
            cursor.execute("SHOW COLUMNS FROM guest_verifications LIKE 'kyc_type'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE guest_verifications ADD COLUMN kyc_type VARCHAR(50) DEFAULT 'ID Document'")
            
            # Ensure hotel_id column exists
            cursor.execute("SHOW COLUMNS FROM guest_verifications LIKE 'hotel_id'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE guest_verifications ADD COLUMN hotel_id INT")
                cursor.execute("ALTER TABLE guest_verifications ADD FOREIGN KEY (hotel_id) REFERENCES hotels(id) ON DELETE CASCADE")
            
            # Ensure selfie_path column exists
            cursor.execute("SHOW COLUMNS FROM guest_verifications LIKE 'selfie_path'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE guest_verifications ADD COLUMN selfie_path VARCHAR(500)")
            
            # Ensure kyc_document_path column exists
            cursor.execute("SHOW COLUMNS FROM guest_verifications LIKE 'kyc_document_path'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE guest_verifications ADD COLUMN kyc_document_path VARCHAR(500)")
            
            # Ensure aadhaar_path column exists
            cursor.execute("SHOW COLUMNS FROM guest_verifications LIKE 'aadhaar_path'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE guest_verifications ADD COLUMN aadhaar_path VARCHAR(500)")

            # Ensure pan_status column exists
            cursor.execute("SHOW COLUMNS FROM guest_verifications LIKE 'pan_status'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE guest_verifications ADD COLUMN pan_status VARCHAR(20) DEFAULT 'not_checked'")
            
            conn.commit()
            cursor.close()
            conn.close()
            print("Guest verifications table initialized with all required columns")
        except Error as e:
            print(f"Error creating guest_verifications table: {e}")
    
    @staticmethod
    def allowed_file(filename):
        """Check if file extension is allowed"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in GuestVerification.ALLOWED_EXTENSIONS
    
    @staticmethod
    def save_uploaded_file(file, manager_id, file_prefix='doc'):
        """Save uploaded identity file and return the file path"""
        try:
            if file and GuestVerification.allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add timestamp to filename to avoid conflicts
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{manager_id}_{file_prefix}_{timestamp}_{filename}"
                
                # Ensure upload directory exists
                upload_path = GuestVerification.UPLOAD_FOLDER
                if not os.path.exists(upload_path):
                    os.makedirs(upload_path)
                
                file_path = os.path.join(upload_path, filename)
                file.save(file_path)
                return file_path
            return None
        except Exception as e:
            print(f"Error saving file: {e}")
            return None
    
    @staticmethod
    def submit_verification(manager_id, guest_name, phone, address, kyc_number, identity_file_path, hotel_id=None, kyc_type='ID Document'):
        """Submit a new guest verification"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO guest_verifications 
                (manager_id, hotel_id, guest_name, phone, address, kyc_number, kyc_type, identity_file, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'pending')
            """, (manager_id, hotel_id, guest_name, phone, address, kyc_number, kyc_type, identity_file_path))
            
            verification_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': 'Verification submitted successfully',
                'id': verification_id
            }
        except Error as e:
            print(f"Error submitting verification: {e}")
            return {
                'success': False,
                'message': f'Failed to submit verification: {str(e)}'
            }
    
    @staticmethod
    def submit_multistep_verification(manager_id, guest_name, phone, address, kyc_number, kyc_type,
                                     selfie_path=None, kyc_document_path=None, aadhaar_path=None,
                                     hotel_id=None, pan_status='not_checked',
                                     api_name='', name_match='UNKNOWN'):
        """Submit multi-step guest verification with selfie, KYC document, and Aadhaar"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Ensure columns exist
            for col, defn in [
                ('pan_status',  "VARCHAR(20) DEFAULT 'not_checked'"),
                ('api_name',    "VARCHAR(255) DEFAULT NULL"),
                ('name_match',  "VARCHAR(20) DEFAULT 'UNKNOWN'"),
            ]:
                cursor.execute(f"SHOW COLUMNS FROM guest_verifications LIKE '{col}'")
                if not cursor.fetchone():
                    cursor.execute(f"ALTER TABLE guest_verifications ADD COLUMN {col} {defn}")
                    conn.commit()

            # Determine overall kyc_status
            if name_match == 'MATCHED':
                kyc_status = 'approved'
            elif name_match == 'MISMATCH':
                kyc_status = 'pending'
            else:
                kyc_status = 'pending'

            cursor.execute("""
                INSERT INTO guest_verifications
                (manager_id, hotel_id, guest_name, phone, address, kyc_number, kyc_type,
                 selfie_path, kyc_document_path, aadhaar_path, pan_status, api_name, name_match, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (manager_id, hotel_id, guest_name, phone, address, kyc_number, kyc_type,
                  selfie_path, kyc_document_path, aadhaar_path,
                  pan_status, api_name, name_match, kyc_status))

            verification_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()

            return {'success': True, 'message': 'Verification submitted successfully', 'id': verification_id}
        except Error as e:
            import traceback; traceback.print_exc()
            return {'success': False, 'message': f'Failed to submit verification: {str(e)}'}
        except Exception as e:
            import traceback; traceback.print_exc()
            return {'success': False, 'message': f'Failed to submit verification: {str(e)}'}
    
    @staticmethod
    def save_selfie_from_base64(base64_data, manager_id):
        """Save selfie from base64 data and return file path"""
        try:
            import base64
            import re
            
            # Extract base64 data (remove data:image/jpeg;base64, prefix)
            base64_match = re.match(r'data:image/(\w+);base64,(.+)', base64_data)
            if not base64_match:
                return None
            
            image_format = base64_match.group(1)
            image_data = base64_match.group(2)
            
            # Decode base64
            image_bytes = base64.b64decode(image_data)
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"selfie_{manager_id}_{timestamp}.{image_format}"
            
            # Ensure upload directory exists
            upload_path = GuestVerification.UPLOAD_FOLDER
            if not os.path.exists(upload_path):
                os.makedirs(upload_path)
            
            file_path = os.path.join(upload_path, filename)
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(image_bytes)
            
            return file_path
        except Exception as e:
            print(f"Error saving selfie: {e}")
            return None
    
    @staticmethod
    def get_verifications_by_manager(manager_id):
        """Get all verifications for a specific manager"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, guest_name, phone, address, kyc_number, kyc_type, identity_file, 
                       submitted_at, status, hotel_id, selfie_path, kyc_document_path, aadhaar_path
                FROM guest_verifications
                WHERE manager_id = %s
                ORDER BY submitted_at DESC
            """, (manager_id,))
            
            verifications = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return verifications
        except Error as e:
            print(f"Error fetching verifications: {e}")
            return []
    
    @staticmethod
    def get_verifications_by_hotel(hotel_id):
        """Get all verifications for a specific hotel"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, guest_name, phone, address, kyc_number, kyc_type, identity_file, 
                       submitted_at, status, hotel_id, selfie_path, kyc_document_path, aadhaar_path
                FROM guest_verifications
                WHERE hotel_id = %s
                ORDER BY submitted_at DESC
            """, (hotel_id,))
            
            verifications = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return verifications
        except Error as e:
            print(f"Error fetching verifications by hotel: {e}")
            return []
    
    @staticmethod
    def update_status(verification_id, status):
        """Update verification status"""
        try:
            if status not in ['pending', 'approved', 'rejected']:
                return {
                    'success': False,
                    'message': 'Invalid status'
                }
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE guest_verifications
                SET status = %s
                WHERE id = %s
            """, (status, verification_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': f'Status updated to {status}'
            }
        except Error as e:
            print(f"Error updating status: {e}")
            return {
                'success': False,
                'message': f'Failed to update status: {str(e)}'
            }
