"""
Check hotel logo in database and verify file exists
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from database.db import get_db_connection

def check_hotel_logo():
    """Check hotel logo data in database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all hotels with their logo info
        cursor.execute("""
            SELECT id, hotel_name, logo, address, city
            FROM hotels
            ORDER BY id
        """)
        
        hotels = cursor.fetchall()
        
        print("\n" + "="*80)
        print("HOTEL LOGO DATABASE CHECK")
        print("="*80)
        
        for hotel in hotels:
            hotel_id, name, logo, address, city = hotel
            print(f"\n🏨 Hotel ID: {hotel_id}")
            print(f"   Name: {name}")
            print(f"   Logo in DB: {logo if logo else 'NULL'}")
            
            if logo:
                # Check if file exists
                logo_path = os.path.join('static', 'uploads', 'hotel_logos', logo)
                file_exists = os.path.exists(logo_path)
                print(f"   File exists: {'✅ YES' if file_exists else '❌ NO'}")
                print(f"   File path: {logo_path}")
                
                if file_exists:
                    file_size = os.path.getsize(logo_path)
                    print(f"   File size: {file_size} bytes")
            else:
                print(f"   Status: ⚠️  No logo set in database")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*80)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_hotel_logo()
