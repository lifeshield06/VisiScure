"""
Add authentication fields to kitchen_sections table
"""
from database.db import get_db_connection

def add_kitchen_auth_fields():
    """Add username, password, and is_active fields to kitchen_sections"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        print("=" * 70)
        print("ADDING KITCHEN AUTHENTICATION FIELDS")
        print("=" * 70)
        
        # Check and add username column
        cursor.execute("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'kitchen_sections'
              AND COLUMN_NAME = 'username'
        """)
        
        if cursor.fetchone()[0] == 0:
            print("\n✓ Adding 'username' column...")
            cursor.execute("""
                ALTER TABLE kitchen_sections 
                ADD COLUMN username VARCHAR(100) UNIQUE
            """)
            print("  Done!")
        else:
            print("\n✓ 'username' column already exists")
        
        # Check and add password column
        cursor.execute("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'kitchen_sections'
              AND COLUMN_NAME = 'password'
        """)
        
        if cursor.fetchone()[0] == 0:
            print("✓ Adding 'password' column...")
            cursor.execute("""
                ALTER TABLE kitchen_sections 
                ADD COLUMN password VARCHAR(255)
            """)
            print("  Done!")
        else:
            print("✓ 'password' column already exists")
        
        # Check and add is_active column
        cursor.execute("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'kitchen_sections'
              AND COLUMN_NAME = 'is_active'
        """)
        
        if cursor.fetchone()[0] == 0:
            print("✓ Adding 'is_active' column...")
            cursor.execute("""
                ALTER TABLE kitchen_sections 
                ADD COLUMN is_active BOOLEAN DEFAULT TRUE
            """)
            print("  Done!")
        else:
            print("✓ 'is_active' column already exists")
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print("\n" + "=" * 70)
        print("✅ KITCHEN AUTHENTICATION FIELDS ADDED SUCCESSFULLY")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    add_kitchen_auth_fields()
