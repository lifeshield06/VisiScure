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
            
            conn.commit()
            cursor.close()
            conn.close()
            print("Guest verifications table initialized")
        except Error as e:
            print(f"Error creating guest_verifications table: {e}")
    
    @staticmethod
    def allowed_file(filename):
        """Check if file extension is allowed"""
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in GuestVerification.ALLOWED_EXTENSIONS
    
    @staticmethod
    def save_uploaded_file(file, manager_id):
        """Save uploaded identity file and return the file path"""
        try:
            if file and GuestVerification.allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add timestamp to filename to avoid conflicts
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{manager_id}_{timestamp}_{filename}"
                
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
    def get_verifications_by_manager(manager_id):
        """Get all verifications for a specific manager"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, guest_name, phone, address, kyc_number, kyc_type, identity_file, 
                       submitted_at, status, hotel_id
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
                       submitted_at, status, hotel_id
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
