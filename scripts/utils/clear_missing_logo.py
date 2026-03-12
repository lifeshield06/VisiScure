"""
Clear logo reference from database if file doesn't exist
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from database.db import get_db_connection

def clear_missing_logo():
    """Clear logo reference if file doesn't exist"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all hotels with logo
        cursor.execute("""
            SELECT id, hotel_name, logo
            FROM hotels
            WHERE logo IS NOT NULL AND logo != ''
        """)
        
        hotels = cursor.fetchall()
        
        print("\n" + "="*80)
        print("CLEARING MISSING LOGO REFERENCES")
        print("="*80)
        
        for hotel in hotels:
            hotel_id, name, logo = hotel
            logo_path = os.path.join('static', 'uploads', 'hotel_logos', logo)
            
            if not os.path.exists(logo_path):
                print(f"\n🏨 Hotel ID {hotel_id}: {name}")
                print(f"   Logo in DB: {logo}")
                print(f"   File missing: {logo_path}")
                print(f"   Action: Clearing logo reference...")
                
                cursor.execute("UPDATE hotels SET logo = NULL WHERE id = %s", (hotel_id,))
                conn.commit()
                
                print(f"   ✅ Logo reference cleared")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*80)
        print("✅ Done! Now you can upload a new logo.")
        print("="*80 + "\n")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    clear_missing_logo()
