"""
Auto-approve all pending verifications
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db import get_db_connection

def auto_approve_all():
    """Auto-approve all pending verifications"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("\n" + "="*70)
        print("AUTO-APPROVING ALL PENDING VERIFICATIONS")
        print("="*70)
        
        # Get count of pending verifications
        cursor.execute("SELECT COUNT(*) FROM guest_verifications WHERE status = 'pending'")
        pending_count = cursor.fetchone()[0]
        
        print(f"\nFound {pending_count} pending verification(s)")
        
        if pending_count > 0:
            # Update all pending to approved
            cursor.execute("""
                UPDATE guest_verifications 
                SET status = 'approved' 
                WHERE status = 'pending'
            """)
            
            conn.commit()
            print(f"✅ Updated {pending_count} verification(s) to 'approved' status")
        else:
            print("✅ No pending verifications to update")
        
        # Show current status distribution
        print("\n" + "="*70)
        print("CURRENT STATUS DISTRIBUTION")
        print("="*70)
        
        cursor.execute("""
            SELECT status, COUNT(*) as count 
            FROM guest_verifications 
            GROUP BY status
        """)
        
        status_counts = cursor.fetchall()
        for status, count in status_counts:
            print(f"  - {status}: {count} verification(s)")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*70)
        print("AUTO-APPROVAL COMPLETED")
        print("="*70 + "\n")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    auto_approve_all()
