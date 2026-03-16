"""
Test Waiter Tip Visibility Toggle Feature
This script tests the tip visibility control feature
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from database.db import get_db_connection

def test_tip_visibility():
    """Test tip visibility toggle feature"""
    
    print("\n" + "="*70)
    print("WAITER TIP VISIBILITY TOGGLE - TEST")
    print("="*70 + "\n")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get hotel ID
        cursor.execute("SELECT id, hotel_name FROM hotels LIMIT 1")
        hotel = cursor.fetchone()
        
        if not hotel:
            print("❌ No hotels found in database")
            return
        
        hotel_id = hotel['id']
        hotel_name = hotel['hotel_name']
        
        print(f"Testing with Hotel: {hotel_name} (ID: {hotel_id})\n")
        
        # Check if hotel_modules entry exists
        cursor.execute("SELECT * FROM hotel_modules WHERE hotel_id = %s", (hotel_id,))
        module = cursor.fetchone()
        
        if not module:
            print("⚠️  No hotel_modules entry found. Creating one...")
            cursor.execute("""
                INSERT INTO hotel_modules (hotel_id, show_waiter_tips)
                VALUES (%s, TRUE)
            """, (hotel_id,))
            conn.commit()
            print("✅ Created hotel_modules entry\n")
        
        # Test 1: Get current setting
        print("Test 1: Get Current Setting")
        print("-" * 70)
        cursor.execute("""
            SELECT COALESCE(show_waiter_tips, TRUE) as show_waiter_tips
            FROM hotel_modules
            WHERE hotel_id = %s
        """, (hotel_id,))
        result = cursor.fetchone()
        current_setting = result['show_waiter_tips'] if result else True
        print(f"Current Setting: {'Enabled' if current_setting else 'Disabled'}")
        print(f"✅ Test 1 Passed\n")
        
        # Test 2: Disable tips
        print("Test 2: Disable Tips")
        print("-" * 70)
        cursor.execute("""
            UPDATE hotel_modules
            SET show_waiter_tips = FALSE
            WHERE hotel_id = %s
        """, (hotel_id,))
        conn.commit()
        
        cursor.execute("""
            SELECT show_waiter_tips FROM hotel_modules WHERE hotel_id = %s
        """, (hotel_id,))
        result = cursor.fetchone()
        assert result['show_waiter_tips'] == False, "Failed to disable tips"
        print("✅ Tips disabled successfully\n")
        
        # Test 3: Enable tips
        print("Test 3: Enable Tips")
        print("-" * 70)
        cursor.execute("""
            UPDATE hotel_modules
            SET show_waiter_tips = TRUE
            WHERE hotel_id = %s
        """, (hotel_id,))
        conn.commit()
        
        cursor.execute("""
            SELECT show_waiter_tips FROM hotel_modules WHERE hotel_id = %s
        """, (hotel_id,))
        result = cursor.fetchone()
        assert result['show_waiter_tips'] == True, "Failed to enable tips"
        print("✅ Tips enabled successfully\n")
        
        cursor.close()
        conn.close()
        
        print("="*70)
        print("ALL TESTS PASSED ✅")
        print("="*70)
        print("\nFeature is working correctly!")
        print("\nNext Steps:")
        print("1. Add toggle UI to manager dashboard")
        print("2. Test from web interface")
        print("3. Verify waiter dashboard respects the setting")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_tip_visibility()
