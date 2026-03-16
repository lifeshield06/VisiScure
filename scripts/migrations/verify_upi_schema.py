"""
Verification script: Check UPI payment columns in hotels table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db import get_db_connection

def verify_schema():
    """Verify UPI payment columns exist in hotels table"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("🔍 Verifying UPI payment schema...")
        
        # Get all columns from hotels table
        cursor.execute("DESCRIBE hotels")
        columns = cursor.fetchall()
        
        # Check for upi_id and upi_qr_image columns
        column_names = [col[0] for col in columns]
        
        upi_id_exists = 'upi_id' in column_names
        upi_qr_exists = 'upi_qr_image' in column_names
        
        print("\n📋 Hotels table columns:")
        for col in columns:
            col_name = col[0]
            col_type = col[1]
            col_null = col[2]
            if col_name in ['upi_id', 'upi_qr_image']:
                print(f"   ✓ {col_name}: {col_type} (NULL: {col_null})")
        
        print("\n✅ Verification Results:")
        print(f"   upi_id column exists: {upi_id_exists}")
        print(f"   upi_qr_image column exists: {upi_qr_exists}")
        
        if upi_id_exists and upi_qr_exists:
            print("\n✅ Schema verification passed! UPI payment columns are present.")
        else:
            print("\n❌ Schema verification failed! Missing columns.")
            return False
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

if __name__ == "__main__":
    success = verify_schema()
    sys.exit(0 if success else 1)
