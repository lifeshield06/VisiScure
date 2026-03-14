"""
Check the most recent verification records
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db import get_db_connection

def check_recent_verifications():
    """Check recent verifications"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("\n" + "="*70)
        print("CHECKING RECENT VERIFICATIONS (Last 20)")
        print("="*70)
        
        cursor.execute("""
            SELECT id, guest_name, phone, status, hotel_id, manager_id, submitted_at 
            FROM guest_verifications 
            ORDER BY id DESC 
            LIMIT 20
        """)
        verifications = cursor.fetchall()
        
        if verifications:
            print(f"\nFound {len(verifications)} verification(s):")
            for v in verifications:
                print(f"  - ID: {v[0]}, Guest: {v[1]}, Phone: {v[2]}, Status: {v[3]}, Hotel ID: {v[4]}, Manager ID: {v[5]}, Submitted: {v[6]}")
        else:
            print("\n❌ No verifications found")
        
        # Check what the API endpoint would return
        print("\n" + "="*70)
        print("SIMULATING API CALL: /guest-verification/api/verifications/10")
        print("="*70)
        
        manager_id = 10
        hotel_id = 9
        
        # Fetch by manager_id first
        cursor.execute("""
            SELECT id, guest_name, phone, address, kyc_number, kyc_type, identity_file, 
                   submitted_at, status, hotel_id
            FROM guest_verifications
            WHERE manager_id = %s
            ORDER BY submitted_at DESC
        """, (manager_id,))
        
        verifications = cursor.fetchall()
        print(f"\nStep 1: Found {len(verifications)} verifications for manager_id={manager_id}")
        
        # Filter by hotel_id
        filtered_verifications = []
        for v in verifications:
            v_hotel_id = v[9] if len(v) > 9 else None
            if v_hotel_id == hotel_id or v_hotel_id is None:
                filtered_verifications.append(v)
        
        print(f"Step 2: After hotel_id={hotel_id} filtering: {len(filtered_verifications)} verifications")
        
        if filtered_verifications:
            print("\nVerifications that SHOULD appear in dashboard:")
            for v in filtered_verifications[:10]:
                print(f"  - ID: {v[0]}, Guest: {v[1]}, Phone: {v[2]}, Status: {v[8]}, Hotel ID: {v[9]}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_recent_verifications()
