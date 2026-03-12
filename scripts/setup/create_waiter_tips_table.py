"""
Create waiter_tips table for distributed tip tracking
"""
from database.db import get_db_connection

def create_waiter_tips_table():
    """Create the waiter_tips table"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        print("Creating waiter_tips table...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS waiter_tips (
                id INT AUTO_INCREMENT PRIMARY KEY,
                waiter_id INT NOT NULL,
                bill_id INT NOT NULL,
                tip_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (waiter_id) REFERENCES waiters(id) ON DELETE CASCADE,
                FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE,
                INDEX idx_waiter_id (waiter_id),
                INDEX idx_bill_id (bill_id),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        
        connection.commit()
        print("✓ waiter_tips table created successfully!")
        
        # Verify table structure
        cursor.execute("DESCRIBE waiter_tips")
        columns = cursor.fetchall()
        
        print("\nTable structure:")
        for col in columns:
            print(f"  {col}")
        
        cursor.close()
        connection.close()
        
    except Exception as e:
        print(f"Error creating waiter_tips table: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_waiter_tips_table()
