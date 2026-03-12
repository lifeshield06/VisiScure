"""
Debug script to test file upload for hotel logo
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db import get_db_connection

def check_hotel_9_status():
    """Check the current status of hotel ID 9"""
    print("=" * 70)
    print("HOTEL ID 9 - CURRENT STATUS")
    print("=" * 70)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, hotel_name, logo, upi_id, upi_qr_image
            FROM hotels
            WHERE id = 9
        """)
        
        hotel = cursor.fetchone()
        
        if hotel:
            hotel_id, name, logo, upi_id, upi_qr = hotel
            
            print(f"\nHotel ID: {hotel_id}")
            print(f"Hotel Name: {name}")
            print(f"Logo in DB: {logo if logo else 'NULL'}")
            print(f"UPI ID in DB: {upi_id if upi_id else 'NULL'}")
            print(f"UPI QR in DB: {upi_qr if upi_qr else 'NULL'}")
            
            # Check if files exist on disk
            if logo:
                logo_path = os.path.join('Hotel/static/uploads/hotel_logos', logo)
                logo_exists = os.path.exists(logo_path)
                print(f"\nLogo file on disk: {'✓ EXISTS' if logo_exists else '✗ MISSING'}")
                if logo_exists:
                    logo_size = os.path.getsize(logo_path)
                    print(f"Logo file size: {logo_size} bytes ({logo_size/1024:.2f} KB)")
            else:
                print(f"\nLogo file on disk: N/A (no logo in database)")
            
            if upi_qr:
                qr_path = os.path.join('Hotel/static/uploads/hotel_qr', upi_qr)
                qr_exists = os.path.exists(qr_path)
                print(f"QR file on disk: {'✓ EXISTS' if qr_exists else '✗ MISSING'}")
                if qr_exists:
                    qr_size = os.path.getsize(qr_path)
                    print(f"QR file size: {qr_size} bytes ({qr_size/1024:.2f} KB)")
            else:
                print(f"QR file on disk: N/A (no QR in database)")
        else:
            print("\n✗ Hotel ID 9 not found in database")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 70)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

def simulate_logo_upload():
    """Simulate what happens during logo upload"""
    print("\n" + "=" * 70)
    print("SIMULATING LOGO UPLOAD PROCESS")
    print("=" * 70)
    
    hotel_id = 9
    
    # Check if upload directory exists
    logo_dir = 'Hotel/static/uploads/hotel_logos'
    print(f"\n1. Upload directory: {logo_dir}")
    print(f"   Exists: {'✓ YES' if os.path.exists(logo_dir) else '✗ NO'}")
    
    if os.path.exists(logo_dir):
        # Check if writable
        test_file = os.path.join(logo_dir, '.test_write')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.remove(test_file)
            print(f"   Writable: ✓ YES")
        except Exception as e:
            print(f"   Writable: ✗ NO - {e}")
    
    # Check what would be the filename
    print(f"\n2. Expected filename pattern: hotel_{hotel_id}.[extension]")
    print(f"   Example: hotel_9.png, hotel_9.jpg, hotel_9.jpeg")
    
    # Check if any files exist for this hotel
    if os.path.exists(logo_dir):
        files = [f for f in os.listdir(logo_dir) if f.startswith(f'hotel_{hotel_id}.')]
        if files:
            print(f"\n3. Existing files for hotel {hotel_id}:")
            for f in files:
                file_path = os.path.join(logo_dir, f)
                file_size = os.path.getsize(file_path)
                print(f"   - {f} ({file_size} bytes)")
        else:
            print(f"\n3. No existing files found for hotel {hotel_id}")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    check_hotel_9_status()
    simulate_logo_upload()
    
    print("\nDEBUG TIPS:")
    print("1. Check Flask console for error messages when uploading")
    print("2. Check browser console (F12) for JavaScript errors")
    print("3. Verify file size is under 2MB")
    print("4. Verify file type is PNG, JPG, JPEG, GIF, or SVG")
    print("5. Try uploading from Create Hotel form instead of Edit")
    print("=" * 70)
