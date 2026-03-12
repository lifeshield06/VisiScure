"""
Cleanup orphaned files that exist on disk but not in database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db import get_db_connection

def cleanup_orphaned_files(dry_run=True):
    """Remove orphaned files"""
    print("=" * 70)
    print("ORPHANED FILES CLEANUP")
    print("=" * 70)
    
    if dry_run:
        print("\n⚠ DRY RUN MODE - No files will be deleted")
        print("Run with dry_run=False to actually delete files\n")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all logos from database
        cursor.execute("SELECT logo FROM hotels WHERE logo IS NOT NULL AND logo != ''")
        db_logos = set(row[0] for row in cursor.fetchall())
        
        # Get all QR images from database
        cursor.execute("SELECT upi_qr_image FROM hotels WHERE upi_qr_image IS NOT NULL AND upi_qr_image != ''")
        db_qrs = set(row[0] for row in cursor.fetchall())
        
        cursor.close()
        conn.close()
        
        # Check logo directory
        logo_dir = 'Hotel/static/uploads/hotel_logos'
        if os.path.exists(logo_dir):
            disk_logos = set(os.listdir(logo_dir))
            orphaned_logos = disk_logos - db_logos
            
            if orphaned_logos:
                print(f"\nFound {len(orphaned_logos)} orphaned logo file(s):")
                for logo in orphaned_logos:
                    logo_path = os.path.join(logo_dir, logo)
                    file_size = os.path.getsize(logo_path)
                    print(f"   - {logo} ({file_size} bytes)")
                    
                    if not dry_run:
                        os.remove(logo_path)
                        print(f"     ✓ Deleted")
            else:
                print("\n✓ No orphaned logo files found")
        
        # Check QR directory
        qr_dir = 'Hotel/static/uploads/hotel_qr'
        if os.path.exists(qr_dir):
            disk_qrs = set(os.listdir(qr_dir))
            orphaned_qrs = disk_qrs - db_qrs
            
            if orphaned_qrs:
                print(f"\nFound {len(orphaned_qrs)} orphaned QR file(s):")
                for qr in orphaned_qrs:
                    qr_path = os.path.join(qr_dir, qr)
                    file_size = os.path.getsize(qr_path)
                    print(f"   - {qr} ({file_size} bytes)")
                    
                    if not dry_run:
                        os.remove(qr_path)
                        print(f"     ✓ Deleted")
            else:
                print("\n✓ No orphaned QR files found")
        
        print("\n" + "=" * 70)
        if dry_run:
            print("DRY RUN COMPLETE - No files were deleted")
            print("To actually delete files, run: cleanup_orphaned_files(dry_run=False)")
        else:
            print("CLEANUP COMPLETE")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Run in dry-run mode by default
    cleanup_orphaned_files(dry_run=True)
    
    # Uncomment to actually delete files:
    # cleanup_orphaned_files(dry_run=False)
