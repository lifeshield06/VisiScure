"""Check hotel logo configuration and display"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from database.db import get_db_connection

def check_hotel_logos():
    """Check hotel logo configuration"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get all hotels with their logos
        cursor.execute("""
            SELECT id, hotel_name, logo 
            FROM hotels 
            ORDER BY id
        """)
        
        hotels = cursor.fetchall()
        
        print("\n=== HOTEL LOGO CONFIGURATION ===\n")
        
        for hotel in hotels:
            print(f"Hotel ID: {hotel['id']}")
            print(f"Hotel Name: {hotel['hotel_name']}")
            print(f"Logo Filename: {hotel['logo']}")
            
            # Check if file exists
            if hotel['logo']:
                logo_path = os.path.join('Hotel', 'static', 'uploads', 'hotel_logos', hotel['logo'])
                exists = os.path.exists(logo_path)
                print(f"File Exists: {exists}")
                if exists:
                    print(f"Full Path: {logo_path}")
            else:
                print("Logo: Not uploaded")
            
            print("-" * 50)
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_hotel_logos()
