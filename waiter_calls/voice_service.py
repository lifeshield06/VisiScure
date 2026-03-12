"""
Voice Generation Service for Waiter Call System
Uses gTTS (Google Text-to-Speech) to generate voice announcements
"""

import os
from gtts import gTTS
from datetime import datetime


class VoiceService:
    """Service for generating voice announcements using gTTS"""
    
    # Directory to store voice files
    VOICE_DIR = os.path.join('static', 'sounds', 'waiter_calls')
    
    @classmethod
    def ensure_voice_directory(cls):
        """Ensure the voice directory exists"""
        if not os.path.exists(cls.VOICE_DIR):
            os.makedirs(cls.VOICE_DIR, exist_ok=True)
            print(f"[VOICE_SERVICE] Created directory: {cls.VOICE_DIR}")
    
    @classmethod
    def generate_voice_file(cls, table_number, request_id=None):
        """
        Generate a voice announcement file for a waiter call
        
        Args:
            table_number (int): The table number calling the waiter
            request_id (int, optional): The request ID for unique filename
            
        Returns:
            dict: {
                'success': bool,
                'filename': str (relative path from static/),
                'message': str
            }
        """
        try:
            # Ensure directory exists
            cls.ensure_voice_directory()
            
            # Create the voice message text
            text = f"Table {table_number} is calling waiter"
            
            # Generate unique filename
            if request_id:
                filename = f"call_{request_id}.mp3"
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"call_table_{table_number}_{timestamp}.mp3"
            
            filepath = os.path.join(cls.VOICE_DIR, filename)
            
            # Generate voice using gTTS
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(filepath)
            
            # Return relative path from static directory
            relative_path = os.path.join('sounds', 'waiter_calls', filename).replace('\\', '/')
            
            print(f"[VOICE_SERVICE] Generated voice file: {relative_path}")
            
            return {
                'success': True,
                'filename': relative_path,
                'message': 'Voice file generated successfully'
            }
            
        except Exception as e:
            print(f"[VOICE_SERVICE ERROR] Failed to generate voice: {e}")
            return {
                'success': False,
                'filename': None,
                'message': f'Failed to generate voice: {str(e)}'
            }
    
    @classmethod
    def cleanup_old_files(cls, max_age_hours=24):
        """
        Clean up old voice files to save disk space
        
        Args:
            max_age_hours (int): Delete files older than this many hours
        """
        try:
            if not os.path.exists(cls.VOICE_DIR):
                return
            
            current_time = datetime.now().timestamp()
            deleted_count = 0
            
            for filename in os.listdir(cls.VOICE_DIR):
                if filename.endswith('.mp3'):
                    filepath = os.path.join(cls.VOICE_DIR, filename)
                    file_age_hours = (current_time - os.path.getmtime(filepath)) / 3600
                    
                    if file_age_hours > max_age_hours:
                        os.remove(filepath)
                        deleted_count += 1
            
            if deleted_count > 0:
                print(f"[VOICE_SERVICE] Cleaned up {deleted_count} old voice files")
                
        except Exception as e:
            print(f"[VOICE_SERVICE ERROR] Cleanup failed: {e}")
