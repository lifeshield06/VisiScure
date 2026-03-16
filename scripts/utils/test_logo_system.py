"""
Test the hotel logo system end-to-end
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db import get_db_connection

def test_logo_system():
    """Test hotel logo system"""
    print("="*70)
    print("🔍 HOTEL LOGO SYSTEM TEST")
    print("="*70)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Check database column
        print("\n1️⃣ Checking database schema...")
        cursor.execute("SHOW COLUMNS FROM hotels LIKE 'logo'")
        if cursor.fetchone():
            print("   ✓ Logo column exists in hotels table")
        else:
            print("   ✗ Logo column missing!")
            return
        
        # 2. Check hotels with logos
        print("\n2️⃣ Checking hotels in database...")
        cursor.execute("SELECT id, hotel_name, logo FROM hotels")
        hotels = cursor.fetchall()
        print(f"   Found {len(hotels)} hotel(s)")
        
        for hotel in hotels:
            hotel_id, hotel_name, logo = hotel
            print(f"\n   Hotel: {hotel_name} (ID: {hotel_id})")
            print(f"   Logo in DB: {logo or 'None'}")
            
            if logo:
                # Check if file exists
                logo_path = os.path.join('Hotel', 'static', 'uploads', 'hotel_logos', logo)
                if os.path.exists(logo_path):
                    file_size = os.path.getsize(logo_path)
                    print(f"   ✓ File exists: {logo_path} ({file_size} bytes)")
                else:
                    print(f"   ✗ File missing: {logo_path}")
        
        # 3. Check upload directory
        print("\n3️⃣ Checking upload directory...")
        upload_dir = os.path.join('Hotel', 'static', 'uploads', 'hotel_logos')
        if os.path.exists(upload_dir):
            files = os.listdir(upload_dir)
            print(f"   ✓ Directory exists: {upload_dir}")
            print(f"   Files in directory: {len(files)}")
            for f in files:
                print(f"      - {f}")
        else:
            print(f"   ✗ Directory missing: {upload_dir}")
        
        # 4. Check manager assignments
        print("\n4️⃣ Checking manager-hotel assignments...")
        cursor.execute("""
            SELECT hm.id, m.name, h.hotel_name, h.logo
            FROM hotel_managers hm
            JOIN managers m ON hm.manager_id = m.id
            JOIN hotels h ON hm.hotel_id = h.id
        """)
        assignments = cursor.fetchall()
        print(f"   Found {len(assignments)} manager assignment(s)")
        
        for assignment in assignments:
            hm_id, manager_name, hotel_name, logo = assignment
            print(f"\n   Manager: {manager_name}")
            print(f"   Hotel: {hotel_name}")
            print(f"   Logo: {logo or 'None'}")
            if logo:
                print(f"   URL: /static/uploads/hotel_logos/{logo}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*70)
        print("✅ TEST COMPLETE")
        print("="*70)
        
    except Exception as e:
        print(f"\n✗ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_logo_system()
