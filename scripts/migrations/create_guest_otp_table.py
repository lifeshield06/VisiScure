"""
Migration script to create guest_otp_verifications table
Run this script to set up OTP verification for guest verification module
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db import get_db_connection

def create_guest_otp_table():
    """Create guest_otp_verifications table"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS guest_otp_verifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                phone_number VARCHAR(10) NOT NULL,
                otp_code VARCHAR(6) NOT NULL,
                created_at DATETIME NOT NULL,
                expires_at DATETIME NOT NULL,
                attempts INT DEFAULT 0,
                verified BOOLEAN DEFAULT FALSE,
                INDEX idx_phone (phone_number),
                INDEX idx_created (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        conn.commit()
        print("✓ Table 'guest_otp_verifications' created successfully")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"✗ Error creating table: {e}")
        return False

if __name__ == "__main__":
    print("Creating guest_otp_verifications table...")
    success = create_guest_otp_table()
    
    if success:
        print("\n✓ Migration completed successfully!")
        print("\nNext steps:")
        print("1. Set SMS_ENABLED=true in environment or config.py for production")
        print("2. Configure MSG91 credentials (AUTH_KEY, TEMPLATE_ID, SENDER_ID) in .env")
        print("3. Test OTP flow in guest verification form")
    else:
        print("\n✗ Migration failed!")
        sys.exit(1)
