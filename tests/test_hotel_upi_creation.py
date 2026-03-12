"""
Test script to verify hotel creation and update with UPI configuration
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database.db import get_db_connection
from payment.upi_utils import validate_upi_id

def test_hotel_creation_with_upi():
    """Test creating a hotel with UPI configuration"""
    print("Testing hotel creation with UPI configuration...")
    
    test_upi_id = "testhotel@paytm"
    
    # Validate UPI ID
    if not validate_upi_id(test_upi_id):
        print(f"❌ UPI ID validation failed for: {test_upi_id}")
        return False
    
    print(f"✓ UPI ID validation passed: {test_upi_id}")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create test hotel with UPI ID
        cursor.execute("""
            INSERT INTO hotels (hotel_name, address, city, upi_id)
            VALUES (%s, %s, %s, %s)
        """, ("Test Hotel UPI", "123 Test St", "Test City", test_upi_id))
        
        hotel_id = cursor.lastrowid
        print(f"✓ Hotel created with ID: {hotel_id}")
        
        # Verify the hotel was created with UPI ID
        cursor.execute("SELECT hotel_name, upi_id FROM hotels WHERE id = %s", (hotel_id,))
        result = cursor.fetchone()
        
        if result and result[1] == test_upi_id:
            print(f"✓ Hotel UPI ID verified: {result[1]}")
        else:
            print(f"❌ Hotel UPI ID mismatch")
            conn.rollback()
            return False
        
        # Clean up test data
        cursor.execute("DELETE FROM hotels WHERE id = %s", (hotel_id,))
        conn.commit()
        print(f"✓ Test hotel cleaned up")
        
        cursor.close()
        conn.close()
        
        print("✅ Hotel creation with UPI test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        try:
            conn.rollback()
        except:
            pass
        return False

def test_hotel_update_with_upi():
    """Test updating a hotel's UPI configuration"""
    print("\nTesting hotel update with UPI configuration...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Create test hotel without UPI
        cursor.execute("""
            INSERT INTO hotels (hotel_name, address, city)
            VALUES (%s, %s, %s)
        """, ("Test Hotel Update", "456 Test Ave", "Test City"))
        
        hotel_id = cursor.lastrowid
        print(f"✓ Test hotel created with ID: {hotel_id}")
        
        # Update hotel with UPI ID
        new_upi_id = "updated@paytm"
        cursor.execute("""
            UPDATE hotels SET upi_id = %s WHERE id = %s
        """, (new_upi_id, hotel_id))
        
        conn.commit()
        print(f"✓ Hotel updated with UPI ID: {new_upi_id}")
        
        # Verify the update
        cursor.execute("SELECT upi_id FROM hotels WHERE id = %s", (hotel_id,))
        result = cursor.fetchone()
        
        if result and result[0] == new_upi_id:
            print(f"✓ Hotel UPI ID update verified: {result[0]}")
        else:
            print(f"❌ Hotel UPI ID update failed")
            conn.rollback()
            return False
        
        # Clean up test data
        cursor.execute("DELETE FROM hotels WHERE id = %s", (hotel_id,))
        conn.commit()
        print(f"✓ Test hotel cleaned up")
        
        cursor.close()
        conn.close()
        
        print("✅ Hotel update with UPI test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        try:
            conn.rollback()
        except:
            pass
        return False

def test_payment_info_retrieval():
    """Test retrieving payment info for a hotel"""
    print("\nTesting payment info retrieval...")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get existing hotel
        cursor.execute("SELECT id, hotel_name, upi_id, upi_qr_image FROM hotels LIMIT 1")
        hotel = cursor.fetchone()
        
        if not hotel:
            print("⚠ No hotels found to test payment info retrieval")
            return True
        
        print(f"✓ Testing with hotel: {hotel['hotel_name']} (ID: {hotel['id']})")
        
        # Fetch payment info
        cursor.execute("""
            SELECT upi_id, upi_qr_image, hotel_name
            FROM hotels
            WHERE id = %s
        """, (hotel['id'],))
        
        result = cursor.fetchone()
        
        if result:
            print(f"✓ Payment info retrieved:")
            print(f"  - Hotel Name: {result['hotel_name']}")
            print(f"  - UPI ID: {result.get('upi_id')}")
            print(f"  - QR Image: {result.get('upi_qr_image')}")
        else:
            print(f"❌ Failed to retrieve payment info")
            return False
        
        cursor.close()
        conn.close()
        
        print("✅ Payment info retrieval test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Hotel UPI Payment Backend Tests")
    print("=" * 60)
    
    test1 = test_hotel_creation_with_upi()
    test2 = test_hotel_update_with_upi()
    test3 = test_payment_info_retrieval()
    
    print("\n" + "=" * 60)
    if test1 and test2 and test3:
        print("✅ All backend tests passed!")
    else:
        print("❌ Some tests failed")
    print("=" * 60)
