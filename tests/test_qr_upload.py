"""
Test script to verify QR image upload and replacement functionality
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database.db import get_db_connection
from payment.upi_utils import allowed_qr_file

def test_qr_file_validation():
    """Test QR file validation"""
    print("Testing QR file validation...")
    
    valid_files = ["qr_code.png", "payment.jpg", "upi.jpeg"]
    invalid_files = ["document.pdf", "image.gif", "file.txt", "noextension"]
    
    for filename in valid_files:
        if not allowed_qr_file(filename):
            print(f"❌ Valid file rejected: {filename}")
            return False
        print(f"✓ Valid file accepted: {filename}")
    
    for filename in invalid_files:
        if allowed_qr_file(filename):
            print(f"❌ Invalid file accepted: {filename}")
            return False
        print(f"✓ Invalid file rejected: {filename}")
    
    print("✅ QR file validation test passed!")
    return True

def test_qr_upload_directory():
    """Test that QR upload directory exists"""
    print("\nTesting QR upload directory...")
    
    qr_dir = "Hotel/static/uploads/hotel_qr"
    
    if not os.path.exists(qr_dir):
        print(f"❌ QR upload directory does not exist: {qr_dir}")
        return False
    
    if not os.path.isdir(qr_dir):
        print(f"❌ QR upload path is not a directory: {qr_dir}")
        return False
    
    # Check if directory is writable
    test_file = os.path.join(qr_dir, "test_write.tmp")
    try:
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        print(f"✓ QR upload directory exists and is writable: {qr_dir}")
    except Exception as e:
        print(f"❌ QR upload directory is not writable: {e}")
        return False
    
    print("✅ QR upload directory test passed!")
    return True

def test_qr_replacement():
    """Test QR image replacement in database"""
    print("\nTesting QR image replacement...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create test hotel
        cursor.execute("""
            INSERT INTO hotels (hotel_name, address, city, upi_id, upi_qr_image)
            VALUES (%s, %s, %s, %s, %s)
        """, ("Test QR Hotel", "789 Test Rd", "Test City", "test@paytm", "old_qr.png"))
        
        hotel_id = cursor.lastrowid
        print(f"✓ Test hotel created with ID: {hotel_id}")
        
        # Verify initial QR
        cursor.execute("SELECT upi_qr_image FROM hotels WHERE id = %s", (hotel_id,))
        result = cursor.fetchone()
        if result[0] != "old_qr.png":
            print(f"❌ Initial QR image mismatch")
            conn.rollback()
            return False
        print(f"✓ Initial QR image: {result[0]}")
        
        # Replace QR image
        new_qr = f"qr_hotel_{hotel_id}.png"
        cursor.execute("""
            UPDATE hotels SET upi_qr_image = %s WHERE id = %s
        """, (new_qr, hotel_id))
        
        conn.commit()
        print(f"✓ QR image updated to: {new_qr}")
        
        # Verify replacement
        cursor.execute("SELECT upi_qr_image FROM hotels WHERE id = %s", (hotel_id,))
        result = cursor.fetchone()
        if result[0] != new_qr:
            print(f"❌ QR image replacement failed")
            conn.rollback()
            return False
        print(f"✓ QR image replacement verified: {result[0]}")
        
        # Clean up
        cursor.execute("DELETE FROM hotels WHERE id = %s", (hotel_id,))
        conn.commit()
        print(f"✓ Test hotel cleaned up")
        
        cursor.close()
        conn.close()
        
        print("✅ QR replacement test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        try:
            conn.rollback()
        except:
            pass
        return False

def test_qr_removal():
    """Test removing QR image from hotel"""
    print("\nTesting QR image removal...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create test hotel with QR
        cursor.execute("""
            INSERT INTO hotels (hotel_name, address, city, upi_id, upi_qr_image)
            VALUES (%s, %s, %s, %s, %s)
        """, ("Test QR Remove", "101 Test Blvd", "Test City", "remove@paytm", "remove_qr.png"))
        
        hotel_id = cursor.lastrowid
        print(f"✓ Test hotel created with QR image")
        
        # Remove QR image
        cursor.execute("""
            UPDATE hotels SET upi_qr_image = NULL WHERE id = %s
        """, (hotel_id,))
        
        conn.commit()
        print(f"✓ QR image removed")
        
        # Verify removal
        cursor.execute("SELECT upi_qr_image FROM hotels WHERE id = %s", (hotel_id,))
        result = cursor.fetchone()
        if result[0] is not None:
            print(f"❌ QR image removal failed")
            conn.rollback()
            return False
        print(f"✓ QR image removal verified")
        
        # Clean up
        cursor.execute("DELETE FROM hotels WHERE id = %s", (hotel_id,))
        conn.commit()
        print(f"✓ Test hotel cleaned up")
        
        cursor.close()
        conn.close()
        
        print("✅ QR removal test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        try:
            conn.rollback()
        except:
            pass
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("QR Upload and Replacement Tests")
    print("=" * 60)
    
    test1 = test_qr_file_validation()
    test2 = test_qr_upload_directory()
    test3 = test_qr_replacement()
    test4 = test_qr_removal()
    
    print("\n" + "=" * 60)
    if test1 and test2 and test3 and test4:
        print("✅ All QR upload tests passed!")
    else:
        print("❌ Some tests failed")
    print("=" * 60)
