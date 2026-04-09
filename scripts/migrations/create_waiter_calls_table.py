"""
Migration: Create waiter_calls table for Hokitoki-Style Waiter Call System

This migration creates the waiter_calls table with proper schema, indexes,
and foreign key constraints to support real-time waiter assistance requests.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database.db import get_db_connection


def migrate():
    """Create waiter_calls table with all required columns and indexes"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        print("Creating waiter_calls table...")
        
        # Create waiter_calls table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS waiter_calls (
                id INT AUTO_INCREMENT PRIMARY KEY,
                hotel_id INT NOT NULL,
                table_id INT NOT NULL,
                waiter_id INT NULL,
                session_id VARCHAR(255),
                guest_name VARCHAR(100),
                status ENUM('PENDING', 'ACKNOWLEDGED', 'COMPLETED') DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                acknowledged_at TIMESTAMP NULL,
                completed_at TIMESTAMP NULL,
                
                FOREIGN KEY (hotel_id) REFERENCES hotels(id) ON DELETE CASCADE,
                FOREIGN KEY (table_id) REFERENCES tables(id) ON DELETE CASCADE,
                FOREIGN KEY (waiter_id) REFERENCES waiters(id) ON DELETE CASCADE,
                
                INDEX idx_waiter_status (waiter_id, status),
                INDEX idx_table_status (table_id, status),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        
        connection.commit()
        print("✓ waiter_calls table created successfully")
        print("✓ Foreign key constraints added")
        print("✓ Indexes created: idx_waiter_status, idx_table_status, idx_created_at")
        
        cursor.close()
        connection.close()
        
        return True
        
    except Exception as e:
        print(f"✗ Error creating waiter_calls table: {e}")
        import traceback
        traceback.print_exc()
        return False


def rollback():
    """Drop waiter_calls table (rollback migration)"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        print("Rolling back waiter_calls table...")
        cursor.execute("DROP TABLE IF EXISTS waiter_calls")
        
        connection.commit()
        print("✓ waiter_calls table dropped successfully")
        
        cursor.close()
        connection.close()
        
        return True
        
    except Exception as e:
        print(f"✗ Error rolling back waiter_calls table: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        print("Running rollback...")
        rollback()
    else:
        print("Running migration...")
        migrate()
