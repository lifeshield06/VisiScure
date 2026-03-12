"""
Check hotel logos in database
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db import get_db_connection

def check_logos():
    """Check hotel logos in database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if logo column exists
        cursor.execute("SHOW COLUMNS FROM hotels LIKE 'logo'")
        if not cursor.fetchone():
            print("✗ Logo column does not exist in hotels table")
            cursor.close()
            conn.close()
            return
        
        print("✓ Logo column exists in hotels table")
        
        # Fetch all hotels with logos
        cursor.execute("SELECT id, hotel_name, logo FROM hotels")
        hotels = cursor.fetchall()
        
        print(f"\n📊 Total Hotels: {len(hotels)}")
        print("\n" + "="*60)
        
        for hotel in hotels:
            hotel_id, hotel_name, logo = hotel
            logo_status = "✓ Has Logo" if logo else "✗ No Logo"
            print(f"Hotel ID: {hotel_id}")
            print(f"Name: {hotel_name}")
            print(f"Logo: {logo or 'None'}")
            print(f"Status: {logo_status}")
            
            # Check if file exists
            if logo:
                logo_path = os.path.join('static', 'uploads', 'hotel_logos', logo)
                if os.path.exists(logo_path):
                    print(f"File: ✓ Exists at {logo_path}")
                else:
                    print(f"File: ✗ Missing at {logo_path}")
            print("="*60)
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Error checking logos: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_logos()
