"""
Fix hotel 9 logo issue - clear missing file reference from database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db import get_db_connection

def fix_hotel_9():
    """Fix hotel 9 by clearing the missing logo reference"""
    print("=" * 70)
    print("FIXING HOTEL 9 LOGO ISSUE")
    print("=" * 70)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check current status
        cursor.execute("SELECT id, hotel_name, logo, upi_qr_image FROM hotels WHERE id = 9")
        hotel = cursor.fetchone()
        
        if not hotel:
            print("\n✗ Hotel ID 9 not found")
            return
        
        hotel_id, name, logo, upi_qr = hotel
        
        print(f"\nCurrent Status:")
        print(f"  Hotel: {name} (ID: {hotel_id})")
        print(f"  Logo in DB: {logo}")
        print(f"  UPI QR in DB: {upi_qr}")
        
        # Check if logo file exists
        if logo:
            logo_path = os.path.join('Hotel/static/uploads/hotel_logos', logo)
            logo_exists = os.path.exists(logo_path)
            print(f"  Logo file exists: {'YES' if logo_exists else 'NO'}")
            
            if not logo_exists:
                print(f"\n⚠ Logo file '{logo}' is missing from disk!")
                print(f"  Clearing logo reference from database...")
                
                cursor.execute("UPDATE hotels SET logo = NULL WHERE id = %s", (hotel_id,))
                conn.commit()
                
                print(f"  ✓ Logo reference cleared from database")
                print(f"\n✅ You can now upload a new logo for this hotel")
        
        # Check QR file
        if upi_qr:
            qr_path = os.path.join('Hotel/static/uploads/hotel_qr', upi_qr)
            qr_exists = os.path.exists(qr_path)
            print(f"\n  UPI QR file exists: {'YES' if qr_exists else 'NO'}")
            
            if not qr_exists:
                print(f"\n⚠ QR file '{upi_qr}' is missing from disk!")
                print(f"  Clearing QR reference from database...")
                
                cursor.execute("UPDATE hotels SET upi_qr_image = NULL WHERE id = %s", (hotel_id,))
                conn.commit()
                
                print(f"  ✓ QR reference cleared from database")
        
        # Show final status
        cursor.execute("SELECT logo, upi_qr_image FROM hotels WHERE id = 9")
        final = cursor.fetchone()
        
        print(f"\nFinal Status:")
        print(f"  Logo in DB: {final[0] if final[0] else 'NULL (ready for new upload)'}")
        print(f"  UPI QR in DB: {final[1] if final[1] else 'NULL (ready for new upload)'}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 70)
        print("FIX COMPLETE")
        print("=" * 70)
        print("\nYou can now:")
        print("1. Go to Admin Dashboard → All Hotels")
        print("2. Click Edit on 'Tip top' hotel")
        print("3. Upload a new logo")
        print("4. Click Save Changes")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_hotel_9()
