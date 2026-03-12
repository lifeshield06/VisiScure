"""
Add username and password columns to waiters table

This migration adds login credentials support for waiters.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from database.db import get_db_connection

def add_waiter_login_columns():
    """Add username and password columns to waiters table"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        print("=" * 60)
        print("Adding username and password columns to waiters table...")
        print("=" * 60)
        
        # Check if username column exists
        cursor.execute("SHOW COLUMNS FROM waiters LIKE 'username'")
        if not cursor.fetchone():
            print("\n✓ Adding 'username' column...")
            cursor.execute("ALTER TABLE waiters ADD COLUMN username VARCHAR(255) UNIQUE")
            print("  ✅ Added successfully")
        else:
            print("\n✓ 'username' column already exists")
        
        # Check if password column exists
        cursor.execute("SHOW COLUMNS FROM waiters LIKE 'password'")
        if not cursor.fetchone():
            print("\n✓ Adding 'password' column...")
            cursor.execute("ALTER TABLE waiters ADD COLUMN password VARCHAR(255)")
            print("  ✅ Added successfully")
        else:
            print("\n✓ 'password' column already exists")
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print("\n" + "=" * 60)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Run: python create_waiter_login.py")
        print("2. Login at: http://localhost:5000/waiter/login")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == '__main__':
    add_waiter_login_columns()
