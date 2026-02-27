"""
Migration script to add kitchen_section_id to table_orders for proper kitchen routing
"""
from database.db import get_db_connection

def add_kitchen_section_column():
    """Add kitchen_section_id column to table_orders table"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Check if column already exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'table_orders'
              AND COLUMN_NAME = 'kitchen_section_id'
        """)
        
        exists = cursor.fetchone()[0]
        
        if not exists:
            print("[KITCHEN_ROUTING] Adding kitchen_section_id column to table_orders...")
            cursor.execute("""
                ALTER TABLE table_orders 
                ADD COLUMN kitchen_section_id INT NULL,
                ADD FOREIGN KEY (kitchen_section_id) REFERENCES kitchen_sections(id) ON DELETE SET NULL
            """)
            connection.commit()
            print("[KITCHEN_ROUTING] ✓ Column added successfully")
        else:
            print("[KITCHEN_ROUTING] Column already exists")
        
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        print(f"[KITCHEN_ROUTING] Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Kitchen Routing Fix - Database Migration")
    print("=" * 60)
    add_kitchen_section_column()
    print("=" * 60)
    print("Migration complete!")
