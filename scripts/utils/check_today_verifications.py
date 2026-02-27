#!/usr/bin/env python3
"""Check today's verification count"""

from database.db import get_db_connection
from datetime import datetime

def check_today_verifications():
    """Check today's verification submissions"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get today's verifications for hotel_id = 9
        cursor.execute("""
            SELECT COUNT(*) as today_count
            FROM guest_verifications 
            WHERE hotel_id = 9 AND DATE(submitted_at) = CURDATE()
        """)
        today_result = cursor.fetchone()
        
        # Get all verifications for hotel_id = 9
        cursor.execute("""
            SELECT COUNT(*) as total_count
            FROM guest_verifications 
            WHERE hotel_id = 9
        """)
        total_result = cursor.fetchone()
        
        # Get verifications submitted today with details
        cursor.execute("""
            SELECT id, guest_name, phone, DATE(submitted_at) as date, TIME(submitted_at) as time
            FROM guest_verifications 
            WHERE hotel_id = 9 AND DATE(submitted_at) = CURDATE()
            ORDER BY submitted_at DESC
        """)
        today_verifications = cursor.fetchall()
        
        print("\n" + "="*80)
        print("TODAY'S VERIFICATION COUNT CHECK")
        print("="*80)
        print(f"\n📊 Statistics for Hotel ID: 9")
        print(f"   📅 Today's Date: {datetime.now().strftime('%Y-%m-%d')}")
        print(f"   ✅ Today's Verifications: {today_result['today_count']}")
        print(f"   📋 Total Verifications: {total_result['total_count']}")
        
        if today_verifications:
            print(f"\n📝 Today's Verification Details:")
            for v in today_verifications:
                print(f"   • ID: {v['id']} | Guest: {v['guest_name']} | Phone: {v['phone']} | Time: {v['time']}")
        else:
            print(f"\n⚠️  No verifications submitted today")
        
        print("\n" + "="*80)
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error checking verifications: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_today_verifications()
