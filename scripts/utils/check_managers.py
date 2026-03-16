"""
Check existing managers in the database
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db import get_db_connection

def check_managers():
    """Check existing managers"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("\n" + "="*70)
        print("CHECKING MANAGERS TABLE")
        print("="*70)
        
        # Check managers table
        cursor.execute("DESCRIBE managers")
        columns = cursor.fetchall()
        print("\nmanagers table structure:")
        for col in columns:
            print(f"  - {col[0]}")
        
        cursor.execute("SELECT * FROM managers LIMIT 10")
        managers = cursor.fetchall()
        
        if managers:
            print(f"\nFound {len(managers)} manager(s):")
            for m in managers:
                print(f"  - Manager: {m}")
        else:
            print("\n❌ No managers found")
        
        # Check hotels table
        print("\n" + "="*70)
        print("CHECKING HOTELS")
        print("="*70)
        cursor.execute("SELECT id, hotel_name FROM hotels LIMIT 10")
        hotels = cursor.fetchall()
        
        if hotels:
            print(f"\nFound {len(hotels)} hotel(s):")
            for h in hotels:
                print(f"  - ID: {h[0]}, Name: {h[1]}")
        else:
            print("\n❌ No hotels found")
        
        # Check guest_verifications
        print("\n" + "="*70)
        print("CHECKING GUEST VERIFICATIONS")
        print("="*70)
        cursor.execute("SELECT id, guest_name, phone, status, hotel_id, manager_id FROM guest_verifications LIMIT 10")
        verifications = cursor.fetchall()
        
        if verifications:
            print(f"\nFound {len(verifications)} verification(s):")
            for v in verifications:
                print(f"  - ID: {v[0]}, Guest: {v[1]}, Phone: {v[2]}, Status: {v[3]}, Hotel ID: {v[4]}, Manager ID: {v[5]}")
        else:
            print("\n❌ No verifications found")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_managers()
