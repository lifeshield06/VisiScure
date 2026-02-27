#!/usr/bin/env python3
"""Check wallet configuration for debugging"""

from database.db import get_db_connection

def check_wallet_config():
    """Check wallet configuration"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get all wallets
        cursor.execute("""
            SELECT hw.*, h.hotel_name 
            FROM hotel_wallet hw
            JOIN hotels h ON hw.hotel_id = h.id
        """)
        wallets = cursor.fetchall()
        
        print("\n" + "="*80)
        print("WALLET CONFIGURATION CHECK")
        print("="*80)
        
        if not wallets:
            print("\n❌ No wallets found in database!")
        else:
            for wallet in wallets:
                print(f"\n🏨 Hotel: {wallet['hotel_name']} (ID: {wallet['hotel_id']})")
                print(f"   💰 Balance: ₹{float(wallet['balance']):.2f}")
                print(f"   📋 Per Verification Charge: ₹{float(wallet['per_verification_charge']):.2f}")
                print(f"   🍽️  Per Order Charge: ₹{float(wallet['per_order_charge']):.2f}")
                print(f"   📅 Last Updated: {wallet['updated_at']}")
                
                # Check if charges are configured
                if float(wallet['per_verification_charge']) == 0:
                    print(f"   ⚠️  WARNING: Verification charge is 0 - deductions will be skipped!")
                if float(wallet['per_order_charge']) == 0:
                    print(f"   ⚠️  WARNING: Order charge is 0 - deductions will be skipped!")
        
        print("\n" + "="*80)
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error checking wallet: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_wallet_config()
