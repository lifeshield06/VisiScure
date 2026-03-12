"""
Link the orphaned QR file to hotel 9
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db import get_db_connection

def link_qr_to_hotel_9():
    """Link the orphaned qr_hotel_9.jpeg to hotel 9"""
    print("=" * 70)
    print("LINKING ORPHANED QR TO HOTEL 9")
    print("=" * 70)
    
    qr_file = 'qr_hotel_9.jpeg'
    qr_path = os.path.join('Hotel/static/uploads/hotel_qr', qr_file)
    
    # Check if file exists
    if not os.path.exists(qr_path):
        print(f"\n✗ QR file '{qr_file}' not found on disk")
        return
    
    print(f"\n✓ QR file found: {qr_file}")
    file_size = os.path.getsize(qr_path)
    print(f"  File size: {file_size} bytes ({file_size/1024:.2f} KB)")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check current status
        cursor.execute("SELECT id, hotel_name, upi_id, upi_qr_image FROM hotels WHERE id = 9")
        hotel = cursor.fetchone()
        
        if not hotel:
            print("\n✗ Hotel ID 9 not found")
            return
        
        hotel_id, name, upi_id, current_qr = hotel
        
        print(f"\nHotel Status:")
        print(f"  Name: {name}")
        print(f"  UPI ID: {upi_id if upi_id else 'NULL'}")
        print(f"  Current QR in DB: {current_qr if current_qr else 'NULL'}")
        
        if current_qr == qr_file:
            print(f"\n✓ QR is already linked to this hotel")
        else:
            print(f"\n  Linking QR file to hotel...")
            cursor.execute("UPDATE hotels SET upi_qr_image = %s WHERE id = %s", (qr_file, hotel_id))
            conn.commit()
            print(f"  ✓ QR file linked successfully")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 70)
        print("COMPLETE")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    link_qr_to_hotel_9()
