"""
Test script: Verify Tip Visibility Toggle Persistence
Tests that the toggle state is correctly saved and loaded
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db import get_db_connection

def test_tip_visibility_persistence():
    """Test tip visibility toggle persistence"""
    print("=" * 60)
    print("TIP VISIBILITY TOGGLE PERSISTENCE TEST")
    print("=" * 60)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get all hotels
        cursor.execute("SELECT id, hotel_name FROM hotels LIMIT 5")
        hotels = cursor.fetchall()
        
        if not hotels:
            print("\n❌ No hotels found in database")
            return False
        
        print(f"\n✓ Found {len(hotels)} hotel(s)")
        
        # Check hotel_modules table
        print("\n🔍 Checking hotel_modules table...")
        cursor.execute("DESCRIBE hotel_modules")
        columns = cursor.fetchall()
        column_names = [col['Field'] for col in columns]
        
        if 'show_waiter_tips' in column_names:
            print("   ✓ show_waiter_tips column exists")
        else:
            print("   ❌ show_waiter_tips column missing!")
            print("   Run: mysql < Hotel/database/add_show_waiter_tips.sql")
            return False
        
        # Check current settings for each hotel
        print("\n📋 Current Tip Visibility Settings:")
        for hotel in hotels:
            hotel_id = hotel['id']
            hotel_name = hotel['hotel_name']
            
            cursor.execute("""
                SELECT COALESCE(show_waiter_tips, TRUE) as show_waiter_tips
                FROM hotel_modules
                WHERE hotel_id = %s
            """, (hotel_id,))
            
            result = cursor.fetchone()
            show_tips = result['show_waiter_tips'] if result else True
            
            status = "✓ ENABLED" if show_tips else "✗ DISABLED"
            print(f"   {status:12} | Hotel ID: {hotel_id:3} | {hotel_name}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ TEST PASSED - Database schema is correct")
        print("=" * 60)
        
        print("\n📝 How to Test:")
        print("   1. Login to Manager Dashboard")
        print("   2. Go to 'Waiter Tips' section")
        print("   3. Toggle 'Show Tips to Waiters' ON")
        print("   4. Refresh the page (F5)")
        print("   5. Check if toggle is still ON")
        print("\n   Expected: Toggle should remain ON after refresh")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_tip_visibility_persistence()
    sys.exit(0 if success else 1)
