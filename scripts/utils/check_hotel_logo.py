"""
Check Hotel Logo Path
Quick script to verify hotel logo path in database
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from database.db import get_db_connection

def check_hotel_logo(hotel_id):
    """Check logo path for a specific hotel"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, hotel_name, logo FROM hotels WHERE id = %s", (hotel_id,))
        result = cursor.fetchone()
        
        if result:
            hotel_id, hotel_name, logo = result
            print(f"\n{'='*60}")
            print(f"Hotel ID: {hotel_id}")
            print(f"Hotel Name: {hotel_name}")
            print(f"Logo Path: {logo}")
            print(f"{'='*60}\n")
            
            if logo:
                # Check if file exists
                possible_paths = [
                    f"static/{logo}",
                    logo,
                    f"static/uploads/{logo}",
                ]
                
                print("Checking file existence:")
                for path in possible_paths:
                    full_path = os.path.join(os.path.dirname(__file__), '../..', path)
                    exists = os.path.exists(full_path)
                    print(f"  {path}: {'✓ EXISTS' if exists else '✗ NOT FOUND'}")
                
                print(f"\nRecommended URL: /static/{logo}")
            else:
                print("⚠️ No logo set for this hotel")
        else:
            print(f"❌ Hotel with ID {hotel_id} not found")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Check hotel ID 9 (from your screenshot)
    check_hotel_logo(9)
