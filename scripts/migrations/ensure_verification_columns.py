"""
Migration script to ensure all required columns exist in guest_verifications table
This script checks and adds missing columns for the verification system
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db import get_db_connection

def ensure_verification_columns():
    """Ensure all required columns exist in guest_verifications table"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("\n" + "="*70)
        print("ENSURING GUEST_VERIFICATIONS TABLE COLUMNS")
        print("="*70)
        
        # Check and add selfie_path column
        cursor.execute("SHOW COLUMNS FROM guest_verifications LIKE 'selfie_path'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE guest_verifications ADD COLUMN selfie_path VARCHAR(500)")
            conn.commit()
            print("✓ Added column: selfie_path")
        else:
            print("- Column 'selfie_path' already exists")
        
        # Check and add kyc_document_path column
        cursor.execute("SHOW COLUMNS FROM guest_verifications LIKE 'kyc_document_path'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE guest_verifications ADD COLUMN kyc_document_path VARCHAR(500)")
            conn.commit()
            print("✓ Added column: kyc_document_path")
        else:
            print("- Column 'kyc_document_path' already exists")
        
        # Check and add aadhaar_path column
        cursor.execute("SHOW COLUMNS FROM guest_verifications LIKE 'aadhaar_path'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE guest_verifications ADD COLUMN aadhaar_path VARCHAR(500)")
            conn.commit()
            print("✓ Added column: aadhaar_path")
        else:
            print("- Column 'aadhaar_path' already exists")
        
        # Check and add hotel_id column
        cursor.execute("SHOW COLUMNS FROM guest_verifications LIKE 'hotel_id'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE guest_verifications ADD COLUMN hotel_id INT")
            conn.commit()
            print("✓ Added column: hotel_id")
        else:
            print("- Column 'hotel_id' already exists")
        
        # Check and add kyc_type column
        cursor.execute("SHOW COLUMNS FROM guest_verifications LIKE 'kyc_type'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE guest_verifications ADD COLUMN kyc_type VARCHAR(50) DEFAULT 'ID Document'")
            conn.commit()
            print("✓ Added column: kyc_type")
        else:
            print("- Column 'kyc_type' already exists")
        
        # Show current table structure
        print("\n" + "="*70)
        print("CURRENT TABLE STRUCTURE")
        print("="*70)
        cursor.execute("DESCRIBE guest_verifications")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[0]:<25} {col[1]:<20} {col[2]:<10} {col[3]:<10}")
        
        print("\n" + "="*70)
        print("MIGRATION COMPLETED SUCCESSFULLY")
        print("="*70 + "\n")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    ensure_verification_columns()
