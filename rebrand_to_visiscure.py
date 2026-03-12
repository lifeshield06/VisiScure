"""
Rebrand Script: VisiScure Order
Replaces all occurrences of "HotelEase" with "VisiScure Order" across the project
"""
import os
import re

# Define replacements
REPLACEMENTS = {
    'HotelEase': 'VisiScure Order',
    'hotelease': 'visiscure order',
    'HOTELEASE': 'VISISCURE ORDER',
    'Hotel Management': 'Smart Restaurant Management',
    'hotel management': 'smart restaurant management',
}

# File extensions to process
EXTENSIONS = ['.html', '.md', '.txt', '.py', '.css', '.js']

# Directories to skip
SKIP_DIRS = ['venv', '__pycache__', '.git', 'node_modules', 'static/uploads']

def should_process_file(filepath):
    """Check if file should be processed"""
    # Skip if in excluded directory
    for skip_dir in SKIP_DIRS:
        if skip_dir in filepath:
            return False
    
    # Check extension
    _, ext = os.path.splitext(filepath)
    return ext in EXTENSIONS

def replace_in_file(filepath):
    """Replace text in a single file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Apply all replacements
        for old_text, new_text in REPLACEMENTS.items():
            content = content.replace(old_text, new_text)
        
        # Only write if content changed
        if content != original_content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
    
    return False

def main():
    """Main rebranding function"""
    print("=" * 70)
    print("REBRANDING: VisiScure Order")
    print("=" * 70)
    print()
    
    files_processed = 0
    files_updated = 0
    
    # Walk through all files
    for root, dirs, files in os.walk('.'):
        # Remove skip directories from dirs list
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        
        for file in files:
            filepath = os.path.join(root, file)
            
            if should_process_file(filepath):
                files_processed += 1
                if replace_in_file(filepath):
                    files_updated += 1
                    print(f"✓ Updated: {filepath}")
    
    print()
    print("=" * 70)
    print("REBRANDING COMPLETE")
    print("=" * 70)
    print(f"Files processed: {files_processed}")
    print(f"Files updated: {files_updated}")
    print()
    print("Next steps:")
    print("1. Review changes")
    print("2. Test the application")
    print("3. Restart Flask server")
    print("=" * 70)

if __name__ == "__main__":
    main()
