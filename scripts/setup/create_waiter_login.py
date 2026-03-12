"""
Create Login Credentials for Waiter

This script sets up username and password for a waiter so they can login to the dashboard.
"""

from database.db import get_db_connection
import hashlib

def create_waiter_login(waiter_id, username, password):
    """Create login credentials for a waiter"""
    try:
        # Hash password using SHA256
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Update database
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if waiter exists
        cursor.execute("SELECT id, name, email FROM waiters WHERE id = %s", (waiter_id,))
        waiter = cursor.fetchone()
        
        if not waiter:
            print(f"❌ Waiter with ID {waiter_id} not found!")
            cursor.close()
            conn.close()
            return False
        
        # Update credentials
        cursor.execute(
            "UPDATE waiters SET username = %s, password = %s WHERE id = %s",
            (username, password_hash, waiter_id)
        )
        conn.commit()
        
        cursor.close()
        conn.close()
        
        print("=" * 60)
        print("✅ LOGIN CREDENTIALS CREATED SUCCESSFULLY!")
        print("=" * 60)
        print(f"\nWaiter: {waiter['name']}")
        print(f"Email: {waiter['email']}")
        print(f"\nLogin Credentials:")
        print(f"  Username: {username}")
        print(f"  Password: {password}")
        print(f"\nLogin URL:")
        print(f"  http://localhost:5000/waiter/login")
        print("\n" + "=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating login: {e}")
        return False

def list_waiters():
    """List all waiters in the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT w.id, w.name, w.email, w.username, 
                   CASE WHEN w.password IS NOT NULL THEN 'Yes' ELSE 'No' END as has_password
            FROM waiters w
            ORDER BY w.id
        """)
        waiters = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not waiters:
            print("No waiters found in database")
            return
        
        print("\n" + "=" * 80)
        print("WAITERS IN DATABASE")
        print("=" * 80)
        print(f"{'ID':<5} {'Name':<25} {'Email':<30} {'Username':<15} {'Password':<10}")
        print("-" * 80)
        
        for waiter in waiters:
            print(f"{waiter['id']:<5} {waiter['name']:<25} {waiter['email']:<30} "
                  f"{waiter['username'] or 'Not set':<15} {waiter['has_password']:<10}")
        
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"❌ Error listing waiters: {e}")

if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("CREATE WAITER LOGIN CREDENTIALS")
    print("=" * 60)
    
    # List existing waiters
    list_waiters()
    
    # Create login for Abhishek Sharma (ID: 16)
    print("Creating login for Abhishek Sharma (ID: 16)...")
    print()
    
    waiter_id = 16
    username = "abhishek"
    password = "password123"
    
    success = create_waiter_login(waiter_id, username, password)
    
    if success:
        print("\n✅ You can now login at: http://localhost:5000/waiter/login")
        print("   Username: abhishek")
        print("   Password: password123")
        print("\n💡 After login, you will see waiter call requests!")
    else:
        print("\n❌ Failed to create login credentials")
        print("   Please check the error message above")
