"""
Test script for gTTS voice generation system
Run this to verify the voice system is working correctly
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from waiter_calls.voice_service import VoiceService


def test_voice_generation():
    """Test voice file generation"""
    print("=" * 60)
    print("Testing gTTS Voice Generation System")
    print("=" * 60)
    print()
    
    # Test 1: Generate voice for table 5
    print("Test 1: Generating voice for Table 5...")
    result = VoiceService.generate_voice_file(table_number=5)
    
    if result['success']:
        print(f"✅ SUCCESS: {result['message']}")
        print(f"   File: {result['filename']}")
        print(f"   Full path: static/{result['filename']}")
    else:
        print(f"❌ FAILED: {result['message']}")
    
    print()
    
    # Test 2: Generate voice with request ID
    print("Test 2: Generating voice for Table 10 with request ID 123...")
    result = VoiceService.generate_voice_file(table_number=10, request_id=123)
    
    if result['success']:
        print(f"✅ SUCCESS: {result['message']}")
        print(f"   File: {result['filename']}")
        print(f"   Full path: static/{result['filename']}")
    else:
        print(f"❌ FAILED: {result['message']}")
    
    print()
    
    # Test 3: Check directory
    print("Test 3: Checking voice directory...")
    voice_dir = VoiceService.VOICE_DIR
    
    if os.path.exists(voice_dir):
        files = [f for f in os.listdir(voice_dir) if f.endswith('.mp3')]
        print(f"✅ Directory exists: {voice_dir}")
        print(f"   Voice files found: {len(files)}")
        
        if files:
            print("   Files:")
            for f in files[:5]:  # Show first 5 files
                filepath = os.path.join(voice_dir, f)
                size_kb = os.path.getsize(filepath) / 1024
                print(f"     - {f} ({size_kb:.1f} KB)")
            
            if len(files) > 5:
                print(f"     ... and {len(files) - 5} more")
    else:
        print(f"❌ Directory not found: {voice_dir}")
    
    print()
    print("=" * 60)
    print("Testing Complete!")
    print("=" * 60)
    print()
    print("Next Steps:")
    print("1. Check the generated files in: static/sounds/waiter_calls/")
    print("2. Play one of the MP3 files to verify audio quality")
    print("3. Start the Flask server and test from waiter dashboard")
    print()


if __name__ == "__main__":
    try:
        test_voice_generation()
    except ImportError as e:
        print("❌ ERROR: gTTS not installed!")
        print()
        print("Please install gTTS:")
        print("  pip install gTTS==2.5.0")
        print()
        print("Or run: install_gtts.bat")
        print()
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
