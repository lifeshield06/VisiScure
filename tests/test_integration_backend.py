"""
Integration test for complete backend implementation
Tests the full workflow: hotel creation, update, payment info retrieval
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from database.db import get_db_connection
from payment.upi_utils import validate_upi_id, generate_upi_payment_link

def test_complete_workflow():
    """Test complete workflow from hotel creation to payment info retrieval"""
    print("Testing complete backend workflow...")
    print("-" * 60)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Step 1: Create hotel with UPI configuration
        print("\n1. Creating hotel with UPI configuration...")
        test_upi_id = "integration@paytm"
        test_hotel_name = "Integration Test Hotel"
        
        if not validate_upi_id(test_upi_id):
            print(f"❌ UPI ID validation failed")
            return False
        
        cursor.execute("""
            INSERT INTO hotels (hotel_name, address, city, upi_id)
            VALUES (%s, %s, %s, %s)
        """, (test_hotel_name, "123 Integration St", "Test City", test_upi_id))
        
        hotel_id = cursor.lastrowid
        conn.commit()
        print(f"✓ Hotel created with ID: {hotel_id}")
        print(f"✓ Hotel name: {test_hotel_name}")
        print(f"✓ UPI ID: {test_upi_id}")
        
        # Step 2: Verify hotel creation
        print("\n2. Verifying hotel creation...")
        cursor.execute("""
            SELECT id, hotel_name, upi_id, upi_qr_image
            FROM hotels WHERE id = %s
        """, (hotel_id,))
        
        hotel = cursor.fetchone()
        if not hotel:
            print(f"❌ Hotel not found after creation")
            return False
        
        print(f"✓ Hotel verified in database")
        print(f"  - ID: {hotel['id']}")
        print(f"  - Name: {hotel['hotel_name']}")
        print(f"  - UPI ID: {hotel['upi_id']}")
        print(f"  - QR Image: {hotel['upi_qr_image']}")
        
        # Step 3: Update hotel with QR image
        print("\n3. Updating hotel with QR image...")
        qr_filename = f"qr_hotel_{hotel_id}.png"
        cursor.execute("""
            UPDATE hotels SET upi_qr_image = %s WHERE id = %s
        """, (qr_filename, hotel_id))
        
        conn.commit()
        print(f"✓ QR image added: {qr_filename}")
        
        # Step 4: Verify QR update
        print("\n4. Verifying QR image update...")
        cursor.execute("""
            SELECT upi_qr_image FROM hotels WHERE id = %s
        """, (hotel_id,))
        
        result = cursor.fetchone()
        if result['upi_qr_image'] != qr_filename:
            print(f"❌ QR image update failed")
            return False
        
        print(f"✓ QR image verified: {result['upi_qr_image']}")
        
        # Step 5: Test payment info retrieval
        print("\n5. Testing payment info retrieval...")
        cursor.execute("""
            SELECT upi_id, upi_qr_image, hotel_name
            FROM hotels WHERE id = %s
        """, (hotel_id,))
        
        payment_info = cursor.fetchone()
        if not payment_info:
            print(f"❌ Payment info retrieval failed")
            return False
        
        print(f"✓ Payment info retrieved successfully:")
        print(f"  - Hotel Name: {payment_info['hotel_name']}")
        print(f"  - UPI ID: {payment_info['upi_id']}")
        print(f"  - QR Image: {payment_info['upi_qr_image']}")
        
        # Step 6: Test UPI link generation
        print("\n6. Testing UPI link generation...")
        test_amount = 1250.50
        upi_link = generate_upi_payment_link(
            payment_info['upi_id'],
            payment_info['hotel_name'],
            test_amount
        )
        
        print(f"✓ UPI link generated:")
        print(f"  {upi_link}")
        
        # Verify link format
        if not upi_link.startswith("upi://pay?"):
            print(f"❌ Invalid UPI link format")
            return False
        
        if "pa=" not in upi_link or "pn=" not in upi_link or "am=" not in upi_link:
            print(f"❌ UPI link missing required parameters")
            return False
        
        print(f"✓ UPI link format validated")
        
        # Step 7: Test QR replacement
        print("\n7. Testing QR replacement...")
        new_qr_filename = f"qr_hotel_{hotel_id}_v2.png"
        cursor.execute("""
            UPDATE hotels SET upi_qr_image = %s WHERE id = %s
        """, (new_qr_filename, hotel_id))
        
        conn.commit()
        print(f"✓ QR replaced with: {new_qr_filename}")
        
        # Verify replacement
        cursor.execute("SELECT upi_qr_image FROM hotels WHERE id = %s", (hotel_id,))
        result = cursor.fetchone()
        if result['upi_qr_image'] != new_qr_filename:
            print(f"❌ QR replacement verification failed")
            return False
        
        print(f"✓ QR replacement verified")
        
        # Step 8: Test UPI ID update
        print("\n8. Testing UPI ID update...")
        new_upi_id = "updated@ybl"
        
        if not validate_upi_id(new_upi_id):
            print(f"❌ New UPI ID validation failed")
            return False
        
        cursor.execute("""
            UPDATE hotels SET upi_id = %s WHERE id = %s
        """, (new_upi_id, hotel_id))
        
        conn.commit()
        print(f"✓ UPI ID updated to: {new_upi_id}")
        
        # Verify update
        cursor.execute("SELECT upi_id FROM hotels WHERE id = %s", (hotel_id,))
        result = cursor.fetchone()
        if result['upi_id'] != new_upi_id:
            print(f"❌ UPI ID update verification failed")
            return False
        
        print(f"✓ UPI ID update verified")
        
        # Step 9: Clean up
        print("\n9. Cleaning up test data...")
        cursor.execute("DELETE FROM hotels WHERE id = %s", (hotel_id,))
        conn.commit()
        print(f"✓ Test hotel deleted")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ Complete backend workflow test PASSED!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        try:
            conn.rollback()
        except:
            pass
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Backend Integration Test")
    print("=" * 60)
    
    success = test_complete_workflow()
    
    if not success:
        print("\n❌ Integration test FAILED")
        sys.exit(1)
