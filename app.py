import os
import mysql.connector
from datetime import datetime, date
from decimal import Decimal
from flask import Flask, render_template, request, jsonify
from flask.json.provider import DefaultJSONProvider
from mysql.connector import Error
from hotel_manager import hotel_manager_bp
from admin import admin_bp
from guest_verification import guest_verification_bp
from menu import menu_bp
from orders import orders_bp
from flask import redirect, url_for


class CustomJSONProvider(DefaultJSONProvider):
    """Custom JSON provider to handle datetime and Decimal serialization consistently"""
    
    def default(self, obj):
        if isinstance(obj, datetime):
            # Return ISO format string for consistent parsing in JavaScript
            return obj.strftime('%Y-%m-%dT%H:%M:%S')
        if isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


app = Flask(__name__)
app.json_provider_class = CustomJSONProvider
app.json = CustomJSONProvider(app)
app.secret_key = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")

# Register blueprints
app.register_blueprint(hotel_manager_bp, url_prefix='/hotel-manager')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(guest_verification_bp, url_prefix='/guest-verification')
app.register_blueprint(menu_bp)
app.register_blueprint(orders_bp, url_prefix='/orders')

# Import and register waiter blueprint
from waiter import waiter_bp
app.register_blueprint(waiter_bp, url_prefix='/waiter')

# Import and register kitchen blueprint
from kitchen import kitchen_bp
app.register_blueprint(kitchen_bp, url_prefix='/kitchen')

# Import and register wallet blueprint
from wallet import wallet_bp
app.register_blueprint(wallet_bp)

def get_db_connection():
    """Create a MySQL connection using environment variables."""
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", "Dattu@1234"),
        database=os.getenv("MYSQL_DATABASE", "test"),
    )

def init_db():
    """Initialize database tables"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Create managers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS managers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                username VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create waiters table with login credentials
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS waiters (
                id INT AUTO_INCREMENT PRIMARY KEY,
                manager_id INT NOT NULL,
                hotel_id INT,
                name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                phone VARCHAR(20) NOT NULL,
                username VARCHAR(255) UNIQUE,
                password VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (manager_id) REFERENCES managers(id) ON DELETE CASCADE,
                FOREIGN KEY (hotel_id) REFERENCES hotels(id) ON DELETE CASCADE
            )
        """)
        
        # Ensure waiters table has all required columns
        cursor.execute("SHOW COLUMNS FROM waiters LIKE 'hotel_id'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE waiters ADD COLUMN hotel_id INT")
            cursor.execute("ALTER TABLE waiters ADD FOREIGN KEY (hotel_id) REFERENCES hotels(id) ON DELETE CASCADE")
        
        cursor.execute("SHOW COLUMNS FROM waiters LIKE 'username'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE waiters ADD COLUMN username VARCHAR(255) UNIQUE")
        
        cursor.execute("SHOW COLUMNS FROM waiters LIKE 'password'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE waiters ADD COLUMN password VARCHAR(255)")
        
        cursor.execute("SHOW COLUMNS FROM waiters LIKE 'is_active'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE waiters ADD COLUMN is_active BOOLEAN DEFAULT TRUE")
        
        # Create waiter_table_assignments table for linking waiters to tables (many-to-many)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS waiter_table_assignments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                waiter_id INT NOT NULL,
                table_id INT NOT NULL,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (waiter_id) REFERENCES waiters(id) ON DELETE CASCADE,
                FOREIGN KEY (table_id) REFERENCES tables(id) ON DELETE CASCADE,
                UNIQUE KEY unique_waiter_table (waiter_id, table_id)
            )
        """)
        
        # Fix old constraints that prevent many-to-many relationships (one-time migration)
        # Get all unique indexes on waiter_table_assignments table
        cursor.execute("""
            SELECT index_name FROM information_schema.statistics 
            WHERE table_schema = DATABASE() 
            AND table_name = 'waiter_table_assignments' 
            AND non_unique = 0
            AND index_name != 'PRIMARY'
        """)
        existing_indexes = [row[0] for row in cursor.fetchall()]
        
        # Check for problematic index that restricts one waiter per table
        problematic_indexes = ['unique_table_assignment', 'table_id_unique']
        for idx_name in problematic_indexes:
            if idx_name in existing_indexes:
                try:
                    # First try to find and drop any foreign key that might depend on this index
                    cursor.execute("""
                        SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE 
                        WHERE TABLE_SCHEMA = DATABASE() 
                        AND TABLE_NAME = 'waiter_table_assignments'
                        AND REFERENCED_TABLE_NAME IS NOT NULL
                    """)
                    fk_constraints = cursor.fetchall()
                    
                    for (fk_name,) in fk_constraints:
                        try:
                            cursor.execute(f"ALTER TABLE waiter_table_assignments DROP FOREIGN KEY {fk_name}")
                            print(f"Dropped foreign key: {fk_name}")
                        except:
                            pass
                    
                    # Now drop the problematic index
                    cursor.execute(f"ALTER TABLE waiter_table_assignments DROP INDEX {idx_name}")
                    print(f"Dropped problematic index: {idx_name}")
                    
                    # Re-add foreign keys
                    try:
                        cursor.execute("""
                            ALTER TABLE waiter_table_assignments 
                            ADD FOREIGN KEY (waiter_id) REFERENCES waiters(id) ON DELETE CASCADE
                        """)
                        cursor.execute("""
                            ALTER TABLE waiter_table_assignments 
                            ADD FOREIGN KEY (table_id) REFERENCES tables(id) ON DELETE CASCADE
                        """)
                        print("Re-added foreign key constraints")
                    except:
                        pass
                        
                except Exception as e:
                    print(f"Note: Could not modify index {idx_name}: {e}")
        
        # Ensure composite unique key exists (waiter_id, table_id) - allows multiple waiters per table
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.statistics 
            WHERE table_schema = DATABASE() 
            AND table_name = 'waiter_table_assignments' 
            AND index_name = 'unique_waiter_table'
        """)
        if cursor.fetchone()[0] == 0:
            try:
                cursor.execute("ALTER TABLE waiter_table_assignments ADD UNIQUE KEY unique_waiter_table (waiter_id, table_id)")
                print("Added composite unique key: unique_waiter_table (waiter_id, table_id)")
            except Exception as e:
                print(f"Composite unique key might already exist: {e}")

        # Create admins table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                username VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create hotels table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hotels (
                id INT AUTO_INCREMENT PRIMARY KEY,
                hotel_name VARCHAR(255) NOT NULL,
                address TEXT,
                city VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Ensure legacy hotels table has expected columns
        cursor.execute("SHOW COLUMNS FROM hotels LIKE 'city'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE hotels ADD COLUMN city VARCHAR(100)")

        cursor.execute("SHOW COLUMNS FROM hotels LIKE 'name'")
        if cursor.fetchone():
            cursor.execute("ALTER TABLE hotels MODIFY COLUMN name VARCHAR(255) NULL")

        cursor.execute("SHOW COLUMNS FROM hotels LIKE 'email'")
        if cursor.fetchone():
            cursor.execute("ALTER TABLE hotels MODIFY COLUMN email VARCHAR(100) NULL")

        cursor.execute("SHOW COLUMNS FROM hotels LIKE 'password'")
        if cursor.fetchone():
            cursor.execute("ALTER TABLE hotels MODIFY COLUMN password VARCHAR(255) NULL")
        
        # Create hotel_modules table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hotel_modules (
                id INT AUTO_INCREMENT PRIMARY KEY,
                hotel_id INT NOT NULL,
                kyc_enabled BOOLEAN DEFAULT FALSE,
                food_enabled BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (hotel_id) REFERENCES hotels(id) ON DELETE CASCADE
            )
        """)
        
        # Create hotel_managers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hotel_managers (
                id INT AUTO_INCREMENT PRIMARY KEY,
                hotel_id INT NOT NULL,
                manager_id INT NOT NULL,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (hotel_id) REFERENCES hotels(id) ON DELETE CASCADE,
                FOREIGN KEY (manager_id) REFERENCES managers(id) ON DELETE CASCADE
            )
        """)
        
        # Create kyc_verifications table (alias for guest_verifications)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS kyc_verifications (
                id INT AUTO_INCREMENT PRIMARY KEY,
                manager_id INT NOT NULL,
                hotel_id INT,
                guest_name VARCHAR(255) NOT NULL,
                phone VARCHAR(20) NOT NULL,
                address TEXT NOT NULL,
                kyc_number VARCHAR(100) NOT NULL,
                identity_file VARCHAR(500),
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (manager_id) REFERENCES managers(id) ON DELETE CASCADE,
                FOREIGN KEY (hotel_id) REFERENCES hotels(id) ON DELETE CASCADE
            )
        """)
        
        # Ensure kyc_verifications table has hotel_id column
        cursor.execute("SHOW COLUMNS FROM kyc_verifications LIKE 'hotel_id'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE kyc_verifications ADD COLUMN hotel_id INT")
        
        # Create menu_categories table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS menu_categories (
                id INT AUTO_INCREMENT PRIMARY KEY,
                hotel_id INT,
                name VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Ensure menu_categories has hotel_id column
        cursor.execute("SHOW COLUMNS FROM menu_categories LIKE 'hotel_id'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE menu_categories ADD COLUMN hotel_id INT")
        
        # Create menu_dishes table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS menu_dishes (
                id INT AUTO_INCREMENT PRIMARY KEY,
                hotel_id INT,
                category_id INT NOT NULL,
                name VARCHAR(255) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                quantity VARCHAR(50),
                description TEXT,
                images JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Ensure menu_dishes has hotel_id column
        cursor.execute("SHOW COLUMNS FROM menu_dishes LIKE 'hotel_id'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE menu_dishes ADD COLUMN hotel_id INT")
        
        # Create default admin if not exists
        import hashlib
        cursor.execute("SELECT * FROM admins WHERE username = 'admin'")
        if not cursor.fetchone():
            default_password = hashlib.sha256('admin123'.encode()).hexdigest()
            cursor.execute(
                "INSERT INTO admins (name, username, password) VALUES (%s, %s, %s)",
                ('Administrator', 'admin', default_password)
            )
            print("Default admin created - Username: admin, Password: admin123")
        
        connection.commit()
        cursor.close()
        connection.close()
        
        # Initialize guest verification table
        from guest_verification.models import GuestVerification
        GuestVerification.create_table()
        
        print("Database initialized successfully")
    except Error as exc:
        print(f"Error initializing database: {exc}")

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/db-test")
def db_test():
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE();")
        current_db = cursor.fetchone()
        cursor.close()
        connection.close()
        return jsonify({
            "status": "success",
            "database": current_db[0] if current_db else None,
        })
    except Error as exc:
        return jsonify({"status": "error", "message": str(exc)}), 500

@app.route("/create-hotel", methods=["GET", "POST"])
def create_hotel_redirect():
    code = 307 if request.method == "POST" else 302
    return redirect(url_for("admin.create_hotel"), code=code)

if os.getenv("ENABLE_DB_INIT") == "1":
    init_db()  # Initialize database tables on startup

if __name__ == "__main__":
    app.run(debug=True)
