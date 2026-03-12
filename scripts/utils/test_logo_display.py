"""Test hotel logo display on table menu page"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from database.db import get_db_connection

def test_logo_display():
    """Test logo display for a table"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get a table with hotel_id
        cursor.execute("""
            SELECT t.id, t.table_number, t.hotel_id, h.hotel_name, h.logo
            FROM tables t
            LEFT JOIN hotels h ON t.hotel_id = h.id
            WHERE t.hotel_id IS NOT NULL
            LIMIT 1
        """)
        
        table = cursor.fetchone()
        
        if table:
            print("\n=== TABLE MENU LOGO TEST ===\n")
            print(f"Table ID: {table['id']}")
            print(f"Table Number: {table['table_number']}")
            print(f"Hotel ID: {table['hotel_id']}")
            print(f"Hotel Name: {table['hotel_name']}")
            print(f"Logo Filename: {table['logo']}")
            
            # Check if logo file exists
            if table['logo']:
                logo_path = os.path.join('Hotel', 'static', 'uploads', 'hotel_logos', table['logo'])
                exists = os.path.exists(logo_path)
                print(f"\nLogo File Exists: {exists}")
                
                if exists:
                    print(f"✓ Logo will display on: http://localhost:5000/orders/menu/{table['id']}")
                else:
                    print(f"✗ Logo file not found at: {logo_path}")
            else:
                print("\n✗ No logo uploaded for this hotel")
                print(f"Default icon will display on: http://localhost:5000/orders/menu/{table['id']}")
        else:
            print("No tables found with hotel_id")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_logo_display()
