"""
Migration script to add multi-step verification columns to guest_verifications table
Adds: selfie_path, kyc_document_path, aadhaar_path, kyc_document_number, verification_step
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db import get_db_connection

def add_multistep_columns():
    """Add multi-step verification columns to guest_verifications table"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check and add selfie_path column
        cursor.execute("SHOW COLUMNS FROM guest_verifications LIKE 'selfie_path'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE guest_verifications ADD COLUMN selfie_path VARCHAR(500)")
            print("✓ Added column: selfie_path")
        else:
            print("- Column 'selfie_path' already exists")
        
        # Check and add kyc_document_path column
        cursor.execute("SHOW COLUMNS FROM guest_verifications LIKE 'kyc_document_path'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE guest_verifications ADD COLUMN kyc_document_path VARCHAR(500)")
            print("✓ Added column: kyc_document_path")
        else:
            print("- Column 'kyc_document_path' already exists")
        
        # Check and add aadhaar_path column
        cursor.execute("SHOW COLUMNS FROM guest_verifications LIKE 'aadhaar_path'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE guest_verifications ADD COLUMN aadhaar_path VARCHAR(500)")
            print("✓ Added column: aadhaar_path")
        else:
            print("- Column 'aadhaar_path' already exists")
        
        # Check and add kyc_document_number column
        cursor.execute("SHOW COLUMNS FROM guest_verifications LIKE 'kyc_document_number'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE guest_verifications ADD COLUMN kyc_document_number VARCHAR(100)")
            print("✓ Added column: kyc_document_number")
        else:
            print("- Column 'kyc_document_number' already exists")
        
        # Check and add verification_step column
        cursor.execute("SHOW COLUMNS FROM guest_verifications LIKE 'verification_step'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE guest_verifications ADD COLUMN verification_step INT DEFAULT 0")
            print("✓ Added column: verification_step")
        else:
            print("- Column 'verification_step' already exists")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"✗ Error adding columns: {e}")
        return False

if __name__ == "__main__":
    print("Adding multi-step verification columns to guest_verifications table...")
    success = add_multistep_columns()
    
    if success:
        print("\n✓ Migration completed successfully!")
    else:
        print("\n✗ Migration failed!")
        sys.exit(1)
