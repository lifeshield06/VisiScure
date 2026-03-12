"""
Test script to verify file upload system for Hotel Logo and UPI QR Code
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db import get_db_connection

def test_file_upload_system():
    """Test the file upload system"""
    print("=" * 60)
    print("FILE UPLOAD SYSTEM TEST")
    print("=" * 60)
    
    # 1. Check if upload directories exist
    print("\n1. Checking Upload Directories:")
    logo_dir = 'Hotel/static/uploads/hotel_logos'
    qr_dir = 'Hotel/static/uploads/hotel_qr'
    
    logo_exists = os.path.exists(logo_dir)
    qr_exists = os.path.exists(qr_dir)
    
    print(f"   Hotel Logos Directory: {'✓ EXISTS' if logo_exists else '✗ MISSING'}")
    print(f"   UPI QR Directory: {'✓ EXISTS' if qr_exists else '✗ MISSING'}")
    
    if logo_exists:
        logo_files = os.listdir(logo_dir)
        print(f"   Logo files found: {len(logo_files)}")
        for f in logo_files[:5]:  # Show first 5
            print(f"      - {f}")
    
    if qr_exists:
        qr_files = os.listdir(qr_dir)
        print(f"   QR files found: {len(qr_files)}")
        for f in qr_files[:5]:  # Show first 5
            print(f"      - {f}")
    
    # 2. Check database schema
    print("\n2. Checking Database Schema:")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SHOW COLUMNS FROM hotels LIKE 'logo'")
        logo_col = cursor.fetchone()
        
        cursor.execute("SHOW COLUMNS FROM hotels LIKE 'upi_id'")
        upi_id_col = cursor.fetchone()
        
        cursor.execute("SHOW COLUMNS FROM hotels LIKE 'upi_qr_image'")
        upi_qr_col = cursor.fetchone()
        
        print(f"   'logo' column: {'✓ EXISTS' if logo_col else '✗ MISSING'}")
        print(f"   'upi_id' column: {'✓ EXISTS' if upi_id_col else '✗ MISSING'}")
        print(f"   'upi_qr_image' column: {'✓ EXISTS' if upi_qr_col else '✗ MISSING'}")
        
        # 3. Check hotels with files
        print("\n3. Checking Hotels with Uploaded Files:")
        cursor.execute("""
            SELECT id, hotel_name, logo, upi_id, upi_qr_image
            FROM hotels
            WHERE logo IS NOT NULL OR upi_qr_image IS NOT NULL
            ORDER BY id DESC
            LIMIT 5
        """)
        
        hotels = cursor.fetchall()
        
        if hotels:
            print(f"   Found {len(hotels)} hotel(s) with uploaded files:")
            for hotel in hotels:
                hotel_id, name, logo, upi_id, upi_qr = hotel
                print(f"\n   Hotel ID: {hotel_id} - {name}")
                print(f"      Logo: {logo if logo else 'None'}")
                if logo:
                    logo_path = os.path.join(logo_dir, logo)
                    print(f"      Logo file exists: {'✓ YES' if os.path.exists(logo_path) else '✗ NO'}")
                print(f"      UPI ID: {upi_id if upi_id else 'None'}")
                print(f"      UPI QR: {upi_qr if upi_qr else 'None'}")
                if upi_qr:
                    qr_path = os.path.join(qr_dir, upi_qr)
                    print(f"      QR file exists: {'✓ YES' if os.path.exists(qr_path) else '✗ NO'}")
        else:
            print("   No hotels found with uploaded files")
        
        # 4. Check all hotels
        print("\n4. All Hotels Summary:")
        cursor.execute("SELECT COUNT(*) FROM hotels")
        total_hotels = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM hotels WHERE logo IS NOT NULL AND logo != ''")
        hotels_with_logo = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM hotels WHERE upi_id IS NOT NULL AND upi_id != ''")
        hotels_with_upi = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM hotels WHERE upi_qr_image IS NOT NULL AND upi_qr_image != ''")
        hotels_with_qr = cursor.fetchone()[0]
        
        print(f"   Total Hotels: {total_hotels}")
        print(f"   Hotels with Logo: {hotels_with_logo}")
        print(f"   Hotels with UPI ID: {hotels_with_upi}")
        print(f"   Hotels with UPI QR: {hotels_with_qr}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("TEST COMPLETED")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_file_upload_system()
