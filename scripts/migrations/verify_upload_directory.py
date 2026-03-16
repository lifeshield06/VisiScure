"""
Verification script: Check upload directory exists and has proper permissions
"""

import os
import sys

def verify_upload_directory():
    """Verify upload directory exists and is writable"""
    upload_dir = "Hotel/static/uploads/hotel_qr/"
    
    print("🔍 Verifying upload directory...")
    print(f"   Directory path: {upload_dir}")
    
    # Check if directory exists
    if not os.path.exists(upload_dir):
        print(f"❌ Directory does not exist: {upload_dir}")
        return False
    
    print(f"   ✓ Directory exists")
    
    # Check if it's a directory
    if not os.path.isdir(upload_dir):
        print(f"❌ Path exists but is not a directory: {upload_dir}")
        return False
    
    print(f"   ✓ Path is a directory")
    
    # Check write permissions by creating a test file
    test_file = os.path.join(upload_dir, ".write_test")
    try:
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        print(f"   ✓ Directory is writable")
    except Exception as e:
        print(f"❌ Directory is not writable: {e}")
        return False
    
    # List existing files
    files = os.listdir(upload_dir)
    print(f"\n📁 Existing files in directory: {len(files)}")
    for file in files:
        file_path = os.path.join(upload_dir, file)
        size = os.path.getsize(file_path)
        print(f"   - {file} ({size} bytes)")
    
    print("\n✅ Upload directory verification passed!")
    return True

if __name__ == "__main__":
    success = verify_upload_directory()
    sys.exit(0 if success else 1)
