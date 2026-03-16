"""
Test script to verify guest verification submission works correctly
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db import get_db_connection
from guest_verification.models import GuestVerification

def test_verification_submission():
    """Test submitting a verification record"""
    try:
        print("\n" + "="*70)
        print("TESTING GUEST VERIFICATION SUBMISSION")
        print("="*70)
        
        # Test data
        manager_id = 1  # Adjust this to a valid manager ID
        hotel_id = 1    # Adjust this to a valid hotel ID
        guest_name = "Test Guest"
        phone = "9876543210"
        address = "123 Test Street, Test City"
        kyc_number = "ABCDE1234F"
        kyc_type = "PAN Card"
        selfie_path = "static/uploads/kyc_documents/test_selfie.jpg"
        kyc_document_path = "static/uploads/kyc_documents/test_kyc.jpg"
        aadhaar_path = "static/uploads/kyc_documents/test_aadhaar.jpg"
        
        print(f"\n[TEST] Submitting verification with:")
        print(f"  - manager_id: {manager_id}")
        print(f"  - hotel_id: {hotel_id}")
        print(f"  - guest_name: {guest_name}")
        print(f"  - phone: {phone}")
        print(f"  - kyc_type: {kyc_type}")
        
        # Submit verification
        result = GuestVerification.submit_multistep_verification(
            manager_id=manager_id,
            guest_name=guest_name,
            phone=phone,
            address=address,
            kyc_number=kyc_number,
            kyc_type=kyc_type,
            selfie_path=selfie_path,
            kyc_document_path=kyc_document_path,
            aadhaar_path=aadhaar_path,
            hotel_id=hotel_id
        )
        
        print(f"\n[TEST] Result: {result}")
        
        if result['success']:
            verification_id = result['id']
            print(f"\n[TEST] ✅ Verification submitted successfully!")
            print(f"[TEST] Verification ID: {verification_id}")
            
            # Verify it was inserted
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM guest_verifications WHERE id = %s", (verification_id,))
            record = cursor.fetchone()
            
            if record:
                print(f"\n[TEST] ✅ Record found in database:")
                print(f"  - ID: {record[0]}")
                print(f"  - Manager ID: {record[1]}")
                print(f"  - Guest Name: {record[2]}")
                print(f"  - Phone: {record[3]}")
                print(f"  - Status: {record[9]}")
                print(f"  - Hotel ID: {record[10]}")
            else:
                print(f"\n[TEST] ❌ Record NOT found in database!")
            
            # Clean up test record
            cursor.execute("DELETE FROM guest_verifications WHERE id = %s", (verification_id,))
            conn.commit()
            print(f"\n[TEST] Test record deleted")
            
            cursor.close()
            conn.close()
        else:
            print(f"\n[TEST] ❌ Submission failed: {result['message']}")
        
        print("\n" + "="*70)
        print("TEST COMPLETED")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n[TEST] ❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_verification_submission()
