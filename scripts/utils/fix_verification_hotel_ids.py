"""
Fix existing verification records by setting hotel_id based on manager_id
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db import get_db_connection

def fix_verification_hotel_ids():
    """Update existing verifications with hotel_id"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("\n" + "="*70)
        print("FIXING VERIFICATION HOTEL IDs")
        print("="*70)
        
        # Get verifications without hotel_id
        cursor.execute("""
            SELECT id, manager_id, guest_name 
            FROM guest_verifications 
            WHERE hotel_id IS NULL
        """)
        verifications = cursor.fetchall()
        
        print(f"\nFound {len(verifications)} verification(s) without hotel_id")
        
        if verifications:
            # Get manager to hotel mapping
            cursor.execute("""
                SELECT manager_id, hotel_id 
                FROM hotel_managers
            """)
            manager_hotel_map = {row[0]: row[1] for row in cursor.fetchall()}
            
            print(f"\nManager to Hotel mapping: {manager_hotel_map}")
            
            # Update each verification
            updated_count = 0
            for v_id, manager_id, guest_name in verifications:
                hotel_id = manager_hotel_map.get(manager_id)
                if hotel_id:
                    cursor.execute("""
                        UPDATE guest_verifications 
                        SET hotel_id = %s 
                        WHERE id = %s
                    """, (hotel_id, v_id))
                    print(f"  ✓ Updated verification ID {v_id} (Guest: {guest_name}) with hotel_id={hotel_id}")
                    updated_count += 1
                else:
                    print(f"  ⚠ No hotel found for manager_id={manager_id} (verification ID {v_id})")
            
            conn.commit()
            print(f"\n✅ Updated {updated_count} verification(s)")
        else:
            print("\n✅ All verifications already have hotel_id")
        
        # Show updated records
        print("\n" + "="*70)
        print("VERIFICATION RECORDS AFTER UPDATE")
        print("="*70)
        cursor.execute("""
            SELECT id, guest_name, phone, status, hotel_id, manager_id 
            FROM guest_verifications 
            ORDER BY id DESC 
            LIMIT 10
        """)
        verifications = cursor.fetchall()
        
        for v in verifications:
            print(f"  - ID: {v[0]}, Guest: {v[1]}, Phone: {v[2]}, Status: {v[3]}, Hotel ID: {v[4]}, Manager ID: {v[5]}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*70)
        print("FIX COMPLETED")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_verification_hotel_ids()
