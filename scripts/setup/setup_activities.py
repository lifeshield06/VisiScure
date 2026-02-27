"""
Setup script to create recent_activities table
Run this once to set up the live activity tracking feature
"""

from database.db import get_db_connection

def setup_activities_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recent_activities (
            id INT PRIMARY KEY AUTO_INCREMENT,
            activity_type VARCHAR(50) NOT NULL,
            message TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_created_at (created_at)
        )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("✅ recent_activities table created successfully!")

if __name__ == "__main__":
    setup_activities_table()
