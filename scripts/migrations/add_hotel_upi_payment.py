"""
Migration: Add UPI Payment Configuration to Hotels Table
Description: Adds upi_id and upi_qr_image columns to hotels table for UPI payment support
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db import get_db_connection

def migrate():
    """Add UPI payment columns to hotels table"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("🔄 Starting migration: Add Hotel UPI Payment Configuration...")
        
        # Check if columns already exist
        cursor.execute("SHOW COLUMNS FROM hotels LIKE 'upi_id'")
        upi_id_exists = cursor.fetchone()
        
        cursor.execute("SHOW COLUMNS FROM hotels LIKE 'upi_qr_image'")
        upi_qr_exists = cursor.fetchone()
        
        if upi_id_exists and upi_qr_exists:
            print("✅ UPI payment columns already exist. Skipping migration.")
            cursor.close()
            conn.close()
            return
        
        # Add upi_id column
        if not upi_id_exists:
            print("   Adding upi_id column...")
            cursor.execute("""
                ALTER TABLE hotels 
                ADD COLUMN upi_id VARCHAR(100) NULL AFTER logo
            """)
            print("   ✓ upi_id column added")
        
        # Add upi_qr_image column
        if not upi_qr_exists:
            print("   Adding upi_qr_image column...")
            cursor.execute("""
                ALTER TABLE hotels 
                ADD COLUMN upi_qr_image VARCHAR(255) NULL AFTER upi_id
            """)
            print("   ✓ upi_qr_image column added")
        
        conn.commit()
        print("✅ Migration completed successfully!")
        print("   Hotels table now supports UPI payment configuration")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        try:
            conn.rollback()
        except:
            pass
        raise

if __name__ == "__main__":
    migrate()
