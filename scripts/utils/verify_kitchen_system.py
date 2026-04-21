"""
Verify Kitchen Management System
Checks database schema and kitchen records
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from database.db import get_db_connection

def verify_kitchen_system():
    """Verify kitchen system is properly configured"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        print("=" * 60)
        print("KITCHEN MANAGEMENT SYSTEM VERIFICATION")
        print("=" * 60)
        
        # Check kitchen_sections table structure
        print("\n1. Checking kitchen_sections table structure...")
        cursor.execute("DESCRIBE kitchen_sections")
        columns = cursor.fetchall()
        
        column_names = [col['Field'] for col in columns]
        required_columns = ['id', 'hotel_id', 'section_name', 'kitchen_unique_id', 'is_active']
        
        print(f"   Found columns: {', '.join(column_names)}")
        
        missing_columns = [col for col in required_columns if col not in column_names]
        if missing_columns:
            print(f"   ❌ Missing columns: {', '.join(missing_columns)}")
        else:
            print("   ✅ All required columns present")
        
        # Check for kitchen_unique_id uniqueness
        kitchen_unique_id_col = next((col for col in columns if col['Field'] == 'kitchen_unique_id'), None)
        if kitchen_unique_id_col:
            if 'UNI' in kitchen_unique_id_col.get('Key', ''):
                print("   ✅ kitchen_unique_id has UNIQUE constraint")
            else:
                print("   ⚠️  kitchen_unique_id should have UNIQUE constraint")
        
        # Check existing kitchens
        print("\n2. Checking existing kitchens...")
        cursor.execute("""
            SELECT 
                id,
                hotel_id,
                section_name,
                kitchen_unique_id,
                is_active,
                created_at
            FROM kitchen_sections
            ORDER BY id
        """)
        
        kitchens = cursor.fetchall()
        
        if not kitchens:
            print("   ℹ️  No kitchens found in database")
        else:
            print(f"   Found {len(kitchens)} kitchen(s):")
            for kitchen in kitchens:
                status = "✅ ACTIVE" if kitchen['is_active'] else "❌ INACTIVE"
                kitchen_id = kitchen['kitchen_unique_id'] or "⚠️  NOT SET"
                print(f"   - ID {kitchen['id']}: {kitchen['section_name']}")
                print(f"     Kitchen ID: {kitchen_id}")
                print(f"     Status: {status}")
                print(f"     Hotel ID: {kitchen['hotel_id']}")
        
        # Check kitchen_category_mapping
        print("\n3. Checking kitchen category mappings...")
        cursor.execute("""
            SELECT 
                kcm.kitchen_section_id,
                ks.section_name,
                COUNT(kcm.category_id) as category_count
            FROM kitchen_category_mapping kcm
            JOIN kitchen_sections ks ON kcm.kitchen_section_id = ks.id
            GROUP BY kcm.kitchen_section_id, ks.section_name
        """)
        
        mappings = cursor.fetchall()
        
        if not mappings:
            print("   ℹ️  No category mappings found")
        else:
            print(f"   Found mappings for {len(mappings)} kitchen(s):")
            for mapping in mappings:
                print(f"   - {mapping['section_name']}: {mapping['category_count']} categories assigned")
        
        # Check for kitchens without valid numeric kitchen_unique_id
        print("\n4. Checking for kitchens without Kitchen ID...")
        cursor.execute("""
            SELECT id, section_name
            FROM kitchen_sections
            WHERE kitchen_unique_id IS NULL OR kitchen_unique_id <= 0
        """)
        
        missing_ids = cursor.fetchall()
        
        if missing_ids:
            print(f"   ⚠️  Found {len(missing_ids)} kitchen(s) without Kitchen ID:")
            for kitchen in missing_ids:
                print(f"   - ID {kitchen['id']}: {kitchen['section_name']}")
            print("   Run migration script: py scripts/migrations/add_kitchen_unique_id.py")
        else:
            print("   ✅ All kitchens have Kitchen IDs")
        
        # Summary
        print("\n" + "=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)
        
        all_good = True
        
        if missing_columns:
            print("❌ Database schema incomplete")
            all_good = False
        else:
            print("✅ Database schema complete")
        
        if missing_ids:
            print("⚠️  Some kitchens need Kitchen IDs")
            all_good = False
        else:
            print("✅ All kitchens have Kitchen IDs")
        
        if all_good:
            print("\n🎉 Kitchen Management System is ready!")
        else:
            print("\n⚠️  Some issues need attention")
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    verify_kitchen_system()
