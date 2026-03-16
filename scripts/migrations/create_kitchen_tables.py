"""
Create kitchen sections and category mapping tables
"""

from database.db import get_db_connection

def create_kitchen_tables():
    """Create kitchen_sections and kitchen_category_mapping tables"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Create kitchen_sections table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kitchen_sections (
                id INT AUTO_INCREMENT PRIMARY KEY,
                hotel_id INT NOT NULL,
                section_name VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (hotel_id) REFERENCES hotels(id) ON DELETE CASCADE,
                UNIQUE KEY unique_section_per_hotel (hotel_id, section_name)
            )
        """)
        
        print("✅ Created kitchen_sections table")
        
        # Create kitchen_category_mapping table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kitchen_category_mapping (
                id INT AUTO_INCREMENT PRIMARY KEY,
                kitchen_section_id INT NOT NULL,
                category_id INT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (kitchen_section_id) REFERENCES kitchen_sections(id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES menu_categories(id) ON DELETE CASCADE,
                UNIQUE KEY unique_category_mapping (kitchen_section_id, category_id)
            )
        """)
        
        print("✅ Created kitchen_category_mapping table")
        
        connection.commit()
        cursor.close()
        connection.close()
        
        print("\n✅ Kitchen tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating kitchen tables: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("CREATING KITCHEN TABLES")
    print("="*60 + "\n")
    
    success = create_kitchen_tables()
    
    if success:
        print("\n" + "="*60)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ MIGRATION FAILED")
        print("="*60)
