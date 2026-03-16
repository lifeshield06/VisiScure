from database.db import get_db_connection

class Table:
    @staticmethod
    def create_tables():
        """Create tables if not exist"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()

            def ensure_column(table_name, column_name, column_def):
                try:
                    cursor.execute(
                        """
                        SELECT COUNT(*)
                        FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_SCHEMA = DATABASE()
                          AND TABLE_NAME = %s
                          AND COLUMN_NAME = %s
                        """,
                        (table_name, column_name)
                    )
                    exists = cursor.fetchone()[0]
                    if not exists:
                        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_def}")
                except Exception as e:
                    print(f"Error ensuring column {table_name}.{column_name}: {e}")
            
            # Ensure gst_percentage column exists in hotels table
            try:
                conn_hotels = get_db_connection()
                cursor_hotels = conn_hotels.cursor()
                cursor_hotels.execute("SHOW COLUMNS FROM hotels LIKE 'gst_percentage'")
                if not cursor_hotels.fetchone():
                    cursor_hotels.execute("ALTER TABLE hotels ADD COLUMN gst_percentage DECIMAL(5,2) DEFAULT 5.00")
                    conn_hotels.commit()
                    print("[BILL] Added gst_percentage column to hotels table")
                cursor_hotels.close()
                conn_hotels.close()
            except Exception as e:
                print(f"[BILL] Error ensuring gst_percentage column in hotels: {e}")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tables (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    hotel_id INT,
                    table_number VARCHAR(50) NOT NULL,
                    qr_code_path VARCHAR(500),
                    current_session_id VARCHAR(100),
                    current_guest_name VARCHAR(255),
                    status ENUM('AVAILABLE', 'BUSY') DEFAULT 'AVAILABLE',
                    waiter_id INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_table_per_hotel (hotel_id, table_number)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS table_orders (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    hotel_id INT,
                    table_id INT NOT NULL,
                    session_id VARCHAR(100),
                    guest_name VARCHAR(255),
                    items JSON NOT NULL,
                    total_amount DECIMAL(10,2) NOT NULL,
                    order_status ENUM('ACTIVE', 'PREPARING', 'COMPLETED') DEFAULT 'ACTIVE',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (table_id) REFERENCES tables(id) ON DELETE CASCADE
                )
            """)

            # Backward-compatible schema updates
            ensure_column("tables", "current_session_id", "current_session_id VARCHAR(100)")
            ensure_column("tables", "current_guest_name", "current_guest_name VARCHAR(255)")
            ensure_column("tables", "hotel_id", "hotel_id INT")
            ensure_column("tables", "waiter_id", "waiter_id INT")
            ensure_column("table_orders", "session_id", "session_id VARCHAR(100)")
            ensure_column("table_orders", "guest_name", "guest_name VARCHAR(255)")
            ensure_column("table_orders", "hotel_id", "hotel_id INT")

            # Ensure enums match expected values
            try:
                cursor.execute(
                    "ALTER TABLE table_orders MODIFY COLUMN order_status ENUM('ACTIVE', 'PREPARING', 'COMPLETED') DEFAULT 'ACTIVE'"
                )
            except Exception as e:
                print(f"Error ensuring order_status enum: {e}")
            
            # Create bills table with guest_name and bill_status
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bills (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    bill_number VARCHAR(50) NOT NULL UNIQUE,
                    order_id INT,
                    hotel_id INT,
                    table_id INT NOT NULL,
                    session_id VARCHAR(100),
                    guest_name VARCHAR(255),
                    hotel_name VARCHAR(255),
                    hotel_address TEXT,
                    table_number VARCHAR(50),
                    items JSON NOT NULL,
                    subtotal DECIMAL(10,2) NOT NULL,
                    tax_rate DECIMAL(5,2) DEFAULT 0.00,
                    tax_amount DECIMAL(10,2) DEFAULT 0.00,
                    tip_amount DECIMAL(10,2) DEFAULT 0.00,
                    total_amount DECIMAL(10,2) NOT NULL,
                    bill_status ENUM('OPEN', 'COMPLETED') DEFAULT 'OPEN',
                    payment_status ENUM('PENDING', 'PAID') DEFAULT 'PENDING',
                    payment_method VARCHAR(50),
                    paid_at TIMESTAMP NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (table_id) REFERENCES tables(id) ON DELETE CASCADE
                )
            """)
            
            # Create active_tables table for tracking active table sessions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS active_tables (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    table_id INT NOT NULL,
                    bill_id INT,
                    hotel_id INT,
                    guest_name VARCHAR(255),
                    session_id VARCHAR(100),
                    status ENUM('ACTIVE', 'CLOSED') DEFAULT 'ACTIVE',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    closed_at TIMESTAMP NULL,
                    FOREIGN KEY (table_id) REFERENCES tables(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_active_table (table_id, status)
                )
            """)
            
            # Ensure new columns exist in bills table
            ensure_column("bills", "guest_name", "guest_name VARCHAR(255)")
            ensure_column("bills", "bill_status", "bill_status ENUM('OPEN', 'COMPLETED') DEFAULT 'OPEN'")
            ensure_column("bills", "tip_amount", "tip_amount DECIMAL(10,2) DEFAULT 0.00")
            ensure_column("bills", "waiter_id", "waiter_id INT")
            ensure_column("bills", "cgst_amount", "cgst_amount DECIMAL(10,2) DEFAULT 0.00")
            ensure_column("bills", "sgst_amount", "sgst_amount DECIMAL(10,2) DEFAULT 0.00")
            ensure_column("bills", "tax_breakdown", "tax_breakdown JSON")
            
            # Ensure payment_status column exists in table_orders
            ensure_column("table_orders", "payment_status", "payment_status ENUM('PENDING', 'PAID') DEFAULT 'PENDING')")
            
            # Ensure charge_deducted column exists in table_orders (for per-order charge tracking)
            ensure_column("table_orders", "charge_deducted", "charge_deducted BOOLEAN DEFAULT FALSE")
            
            # Ensure waiter_id column exists in table_orders for direct waiter assignment
            ensure_column("table_orders", "waiter_id", "waiter_id INT")
            
            # Ensure columns exist in active_tables
            ensure_column("active_tables", "hotel_id", "hotel_id INT")
            ensure_column("active_tables", "session_id", "session_id VARCHAR(100)")
            
            connection.commit()
            cursor.close()
            connection.close()
            return True
        except Exception as e:
            print(f"Error creating tables: {e}")
            return False
    
    @staticmethod
    def add_table(table_number, qr_code_path, hotel_id=None):
        """Add new table"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            cursor.execute(
                "INSERT INTO tables (table_number, qr_code_path, hotel_id) VALUES (%s, %s, %s)",
                (table_number, qr_code_path, hotel_id)
            )
            
            table_id = cursor.lastrowid
            connection.commit()
            cursor.close()
            connection.close()
            return table_id
        except Exception as e:
            print(f"Error adding table: {e}")
            return None
    
    @staticmethod
    def get_all_tables(hotel_id=None):
        """Get all tables for a specific hotel with active table info and waiter assignment"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Join with active_tables to get current status and waiter info
            if hotel_id:
                cursor.execute("""
                    SELECT t.*, 
                           at.id as active_entry_id, 
                           at.bill_id as active_bill_id,
                           at.guest_name as active_guest_name,
                           at.created_at as active_since,
                           b.bill_number as active_bill_number,
                           b.total_amount as active_bill_total,
                           w.name as waiter_name,
                           CASE WHEN at.status = 'ACTIVE' THEN 'BUSY' ELSE t.status END as derived_status
                    FROM tables t
                    LEFT JOIN active_tables at ON t.id = at.table_id AND at.status = 'ACTIVE'
                    LEFT JOIN bills b ON at.bill_id = b.id
                    LEFT JOIN waiters w ON t.waiter_id = w.id
                    WHERE t.hotel_id = %s 
                    ORDER BY t.table_number
                """, (hotel_id,))
            else:
                cursor.execute("""
                    SELECT t.*, 
                           at.id as active_entry_id, 
                           at.bill_id as active_bill_id,
                           at.guest_name as active_guest_name,
                           at.created_at as active_since,
                           b.bill_number as active_bill_number,
                           b.total_amount as active_bill_total,
                           w.name as waiter_name,
                           CASE WHEN at.status = 'ACTIVE' THEN 'BUSY' ELSE t.status END as derived_status
                    FROM tables t
                    LEFT JOIN active_tables at ON t.id = at.table_id AND at.status = 'ACTIVE'
                    LEFT JOIN bills b ON at.bill_id = b.id
                    LEFT JOIN waiters w ON t.waiter_id = w.id
                    ORDER BY t.table_number
                """)
            tables = cursor.fetchall()
            
            # Update status field to reflect derived status from active_tables
            for table in tables:
                if table.get('derived_status'):
                    table['status'] = table['derived_status']
            
            cursor.close()
            connection.close()
            return tables
        except Exception as e:
            print(f"Error getting tables: {e}")
            return []
    
    @staticmethod
    def get_table_by_id(table_id):
        """Get table by ID"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("SELECT * FROM tables WHERE id = %s", (table_id,))
            table = cursor.fetchone()
            
            cursor.close()
            connection.close()
            return table
        except Exception as e:
            print(f"Error getting table: {e}")
            return None
    
    @staticmethod
    def start_table_session(table_id, session_id):
        """Start a new session for table (mark as BUSY)"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            cursor.execute(
                "UPDATE tables SET status = 'BUSY', current_session_id = %s WHERE id = %s",
                (session_id, table_id)
            )
            
            connection.commit()
            cursor.close()
            connection.close()
            return True
        except Exception as e:
            print(f"Error starting table session: {e}")
            return False
    
    @staticmethod
    def end_table_session(table_id):
        """End table session (mark as AVAILABLE)"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            cursor.execute(
                "UPDATE tables SET status = 'AVAILABLE', current_session_id = NULL WHERE id = %s",
                (table_id,)
            )
            
            connection.commit()
            cursor.close()
            connection.close()
            return True
        except Exception as e:
            print(f"Error ending table session: {e}")
            return False
    
    @staticmethod
    def get_table_session(table_id):
        """Get current session ID for table"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("SELECT current_session_id FROM tables WHERE id = %s", (table_id,))
            result = cursor.fetchone()
            
            cursor.close()
            connection.close()
            return result['current_session_id'] if result else None
        except Exception as e:
            print(f"Error getting table session: {e}")
            return None

class TableOrder:
    @staticmethod
    def add_order(table_id, session_id, items, total_amount, hotel_id=None, guest_name=None, waiter_id=None):
        """Add new ACTIVE order and set table BUSY with assigned waiter. Also populate order_items table with kitchen routing."""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            import json
            items_json = json.dumps(items)
            
            # Add order as ACTIVE with guest_name and waiter_id from assigned table waiter
            cursor.execute(
                "INSERT INTO table_orders (table_id, session_id, guest_name, items, total_amount, order_status, hotel_id, waiter_id) VALUES (%s, %s, %s, %s, %s, 'ACTIVE', %s, %s)",
                (table_id, session_id, guest_name, items_json, total_amount, hotel_id, waiter_id)
            )
            
            order_id = cursor.lastrowid
            
            # Populate order_items table with kitchen section assignment
            for item in items:
                dish_id = item.get('id')
                dish_name = item.get('name', 'Unknown')
                quantity = item.get('quantity', 1)
                price = item.get('price', 0)
                
                if not dish_id:
                    continue
                
                # Get category_id and kitchen_id directly from the dish
                cursor.execute("""
                    SELECT category_id, kitchen_id
                    FROM menu_dishes
                    WHERE id = %s
                    LIMIT 1
                """, (dish_id,))
                
                dish_info = cursor.fetchone()
                category_id = dish_info['category_id'] if dish_info else None
                kitchen_section_id = dish_info['kitchen_id'] if dish_info else None
                
                # Insert into order_items with kitchen routing
                cursor.execute("""
                    INSERT INTO order_items 
                    (order_id, dish_id, dish_name, category_id, kitchen_section_id, quantity, price, item_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'ACTIVE')
                """, (order_id, dish_id, dish_name, category_id, kitchen_section_id, quantity, price))
                
                print(f"[ORDER_ROUTING] Item '{dish_name}' → Kitchen Section {kitchen_section_id}")
            
            # Set table BUSY and store guest_name
            cursor.execute(
                "UPDATE tables SET status = 'BUSY', current_session_id = COALESCE(current_session_id, %s), current_guest_name = COALESCE(current_guest_name, %s) WHERE id = %s",
                (session_id, guest_name, table_id)
            )
            
            connection.commit()
            cursor.close()
            connection.close()
            return order_id, None
        except Exception as e:
            print(f"Error adding order: {e}")
            import traceback
            traceback.print_exc()
            return None, str(e)
    
    @staticmethod
    def complete_order(order_id):
        """Complete order - mark as COMPLETED (served). Bill stays OPEN until payment."""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Get table_id for this order
            cursor.execute("SELECT table_id FROM table_orders WHERE id = %s", (order_id,))
            result = cursor.fetchone()
            
            if not result:
                return False
            
            # Update order to COMPLETED (meaning: served to guest)
            # NOTE: Do NOT close the bill here - bill closes ONLY after payment
            cursor.execute(
                "UPDATE table_orders SET order_status = 'COMPLETED' WHERE id = %s",
                (order_id,)
            )
            
            connection.commit()
            cursor.close()
            connection.close()
            return True
        except Exception as e:
            print(f"Error completing order: {e}")
            return False
    
    @staticmethod
    def get_all_orders(hotel_id=None):
        """Get all orders with table info for a specific hotel"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            if hotel_id:
                # Match orders by hotel_id OR by table's hotel_id (fallback for older orders)
                # Also join with bills to get payment_method
                cursor.execute("""
                    SELECT o.*, t.table_number, t.status as table_status, b.payment_method
                    FROM table_orders o
                    JOIN tables t ON o.table_id = t.id
                    LEFT JOIN bills b ON o.table_id = b.table_id AND o.session_id = b.session_id
                    WHERE o.hotel_id = %s OR (o.hotel_id IS NULL AND t.hotel_id = %s)
                    ORDER BY o.created_at DESC
                """, (hotel_id, hotel_id))
            else:
                cursor.execute("""
                    SELECT o.*, t.table_number, t.status as table_status, b.payment_method
                    FROM table_orders o
                    JOIN tables t ON o.table_id = t.id
                    LEFT JOIN bills b ON o.table_id = b.table_id AND o.session_id = b.session_id
                    ORDER BY o.created_at DESC
                """)
            
            orders = cursor.fetchall()
            
            # Parse JSON items
            import json
            for order in orders:
                if order['items']:
                    order['items'] = json.loads(order['items'])
            
            cursor.close()
            connection.close()
            return orders
        except Exception as e:
            print(f"Error getting orders: {e}")
            return []

    @staticmethod
    def update_order_status(order_id, status):
        """Update order status (ACTIVE/PREPARING/COMPLETED). Does NOT affect bill status."""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()

            # Simply update the order status - bill stays OPEN until payment
            cursor.execute(
                "UPDATE table_orders SET order_status = %s WHERE id = %s",
                (status, order_id)
            )

            connection.commit()
            cursor.close()
            connection.close()
            return True
        except Exception as e:
            print(f"Error updating order status: {e}")
            return False

    @staticmethod
    def get_orders_by_session(table_id, session_id):
        """Get orders for a specific table session"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT o.*, t.table_number, t.status as table_status
                FROM table_orders o
                JOIN tables t ON o.table_id = t.id
                WHERE o.table_id = %s AND o.session_id = %s
                ORDER BY o.created_at DESC
                """,
                (table_id, session_id)
            )

            orders = cursor.fetchall()

            import json
            for order in orders:
                if order['items']:
                    order['items'] = json.loads(order['items'])

            cursor.close()
            connection.close()
            return orders
        except Exception as e:
            print(f"Error getting session orders: {e}")
            return []


class Bill:
    TAX_RATE = 5.0  # 5% tax rate (DEPRECATED - use hotel's gst_percentage instead)
    
    @staticmethod
    def enrich_items_with_tax(items, cursor):
        """Add CGST/SGST percentages and amounts to each item.
        Uses per-dish tax rates (cgst, sgst columns in menu_dishes).
        Returns enriched items list with tax info per item."""
        enriched_items = []
        
        for item in items:
            item_copy = dict(item)  # Make a copy to avoid modifying original
            item_price = float(item.get('price', 0))
            item_qty = int(item.get('quantity', 1))
            item_total = item_price * item_qty
            dish_id = item.get('id')
            
            # Get category name and DISH-SPECIFIC tax percentages
            category_name = "Other"
            cgst_pct = 2.50
            sgst_pct = 2.50
            
            if dish_id:
                cursor.execute("""
                    SELECT mc.name as category_name, 
                           COALESCE(d.cgst, 2.50) as cgst_percentage, 
                           COALESCE(d.sgst, 2.50) as sgst_percentage 
                    FROM menu_dishes d
                    LEFT JOIN menu_categories mc ON d.category_id = mc.id
                    WHERE d.id = %s
                """, (dish_id,))
                cat_info = cursor.fetchone()
                if cat_info:
                    category_name = cat_info.get('category_name') or "Other"
                    cgst_pct = float(cat_info.get('cgst_percentage') or 2.50)
                    sgst_pct = float(cat_info.get('sgst_percentage') or 2.50)
            
            # Calculate item tax
            item_cgst = round(item_total * (cgst_pct / 100), 2)
            item_sgst = round(item_total * (sgst_pct / 100), 2)
            item_total_with_tax = round(item_total + item_cgst + item_sgst, 2)
            
            # Add tax info to item
            item_copy['category'] = category_name
            item_copy['cgst_percentage'] = cgst_pct
            item_copy['sgst_percentage'] = sgst_pct
            item_copy['cgst_amount'] = item_cgst
            item_copy['sgst_amount'] = item_sgst
            item_copy['total_with_tax'] = item_total_with_tax
            
            enriched_items.append(item_copy)
        
        return enriched_items
    
    @staticmethod
    def calculate_category_tax_breakdown(items, cursor):
        """Calculate dish-wise CGST and SGST breakdown for items.
        Uses per-dish tax rates (cgst, sgst columns in menu_dishes).
        Returns dict with tax_breakdown, total_cgst, total_sgst"""
        import json
        
        # Track tax by category for display purposes: {category_name: {subtotal, cgst_amt, sgst_amt}}
        category_taxes = {}
        total_cgst = 0.0
        total_sgst = 0.0
        
        for item in items:
            item_total = float(item.get('price', 0)) * int(item.get('quantity', 1))
            dish_id = item.get('id')
            
            # Get category name and DISH-SPECIFIC tax percentages
            category_name = "Other"
            cgst_pct = 2.50
            sgst_pct = 2.50
            
            if dish_id:
                cursor.execute("""
                    SELECT mc.name as category_name, 
                           COALESCE(d.cgst, 2.50) as cgst_percentage, 
                           COALESCE(d.sgst, 2.50) as sgst_percentage 
                    FROM menu_dishes d
                    LEFT JOIN menu_categories mc ON d.category_id = mc.id
                    WHERE d.id = %s
                """, (dish_id,))
                cat_info = cursor.fetchone()
                if cat_info:
                    category_name = cat_info.get('category_name') or "Other"
                    cgst_pct = float(cat_info.get('cgst_percentage') or 2.50)
                    sgst_pct = float(cat_info.get('sgst_percentage') or 2.50)
            
            # Calculate item tax
            item_cgst = round(item_total * (cgst_pct / 100), 2)
            item_sgst = round(item_total * (sgst_pct / 100), 2)
            
            # Aggregate by category
            if category_name not in category_taxes:
                category_taxes[category_name] = {
                    'cgst_percentage': cgst_pct,
                    'sgst_percentage': sgst_pct,
                    'subtotal': 0.0,
                    'cgst_amount': 0.0,
                    'sgst_amount': 0.0
                }
            
            category_taxes[category_name]['subtotal'] += item_total
            category_taxes[category_name]['cgst_amount'] += item_cgst
            category_taxes[category_name]['sgst_amount'] += item_sgst
            
            total_cgst += item_cgst
            total_sgst += item_sgst
        
        # Round totals
        total_cgst = round(total_cgst, 2)
        total_sgst = round(total_sgst, 2)
        
        # Round category amounts
        for cat in category_taxes.values():
            cat['subtotal'] = round(cat['subtotal'], 2)
            cat['cgst_amount'] = round(cat['cgst_amount'], 2)
            cat['sgst_amount'] = round(cat['sgst_amount'], 2)
        
        return {
            'breakdown': category_taxes,
            'total_cgst': total_cgst,
            'total_sgst': total_sgst
        }
    
    @staticmethod
    def get_hotel_gst_percentage(hotel_id):
        """Get GST percentage for a specific hotel (dynamic per hotel)"""
        try:
            if not hotel_id:
                return 5.0  # Default fallback
            
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("SELECT gst_percentage FROM hotels WHERE id = %s", (hotel_id,))
            result = cursor.fetchone()
            
            cursor.close()
            connection.close()
            
            if result and result.get('gst_percentage') is not None:
                return float(result['gst_percentage'])
            return 5.0  # Default fallback if not set
        except Exception as e:
            print(f"Error getting hotel GST percentage: {e}")
            return 5.0  # Default fallback on error
    
    @staticmethod
    def generate_bill_number():
        """Generate unique bill number"""
        import datetime
        import random
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        random_suffix = random.randint(100, 999)
        return f"BILL-{timestamp}-{random_suffix}"
    
    @staticmethod
    def get_open_bill_for_guest(table_id, guest_name):
        """Get existing OPEN bill for same guest at same table"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT b.*, h.hotel_name, h.logo as hotel_logo
                FROM bills b
                LEFT JOIN hotels h ON b.hotel_id = h.id
                WHERE b.table_id = %s AND b.guest_name = %s AND b.bill_status = 'OPEN'
                ORDER BY b.created_at DESC LIMIT 1
            """, (table_id, guest_name))
            
            bill = cursor.fetchone()
            
            if bill and bill.get('items'):
                import json
                items = json.loads(bill['items'])
                # Enrich items with tax info if missing
                if items:  # Always enrich with current tax rates
                    items = Bill.enrich_items_with_tax(items, cursor)
                bill['items'] = items
            
            cursor.close()
            connection.close()
            return bill
        except Exception as e:
            print(f"Error getting open bill: {e}")
            return None
    
    @staticmethod
    def get_any_open_bill_for_table(table_id):
        """Get any existing OPEN bill for a table (regardless of guest)"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT b.*, h.hotel_name, h.logo as hotel_logo
                FROM bills b
                LEFT JOIN hotels h ON b.hotel_id = h.id
                WHERE b.table_id = %s AND b.bill_status = 'OPEN'
                ORDER BY b.created_at DESC LIMIT 1
            """, (table_id,))
            
            bill = cursor.fetchone()
            
            if bill:
                import json
                if bill.get('items'):
                    items = json.loads(bill['items']) if isinstance(bill['items'], str) else bill['items']
                    # Always enrich items with tax info to ensure they have current rates
                    items = Bill.enrich_items_with_tax(items, cursor)
                    bill['items'] = items
                if bill.get('tax_breakdown'):
                    bill['tax_breakdown'] = json.loads(bill['tax_breakdown']) if isinstance(bill['tax_breakdown'], str) else bill['tax_breakdown']
            
            cursor.close()
            connection.close()
            return bill
        except Exception as e:
            print(f"Error getting open bill for table: {e}")
            return None
    
    @staticmethod
    def add_items_to_bill(bill_id, new_items, new_order_id):
        """Add new items to an existing OPEN bill"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Get current bill
            cursor.execute("SELECT items, subtotal, hotel_id FROM bills WHERE id = %s AND bill_status = 'OPEN'", (bill_id,))
            bill = cursor.fetchone()
            
            if not bill:
                cursor.close()
                connection.close()
                return None
            
            import json
            existing_items = json.loads(bill['items']) if isinstance(bill['items'], str) else bill['items']
            
            # Merge items - combine quantities for same items (use basic info first)
            for new_item in new_items:
                found = False
                for existing_item in existing_items:
                    if existing_item['name'] == new_item['name'] and existing_item['price'] == new_item['price']:
                        existing_item['quantity'] += new_item['quantity']
                        found = True
                        break
                if not found:
                    existing_items.append(new_item)
            
            # Enrich items with per-item tax info
            enriched_items = Bill.enrich_items_with_tax(existing_items, cursor)
            
            # Recalculate totals with category-wise CGST/SGST using helper
            subtotal = sum(item['price'] * item['quantity'] for item in enriched_items)
            
            # Calculate category-wise tax breakdown using helper
            tax_result = Bill.calculate_category_tax_breakdown(enriched_items, cursor)
            cgst_amount = tax_result['total_cgst']
            sgst_amount = tax_result['total_sgst']
            tax_breakdown = tax_result['breakdown']
            tax_amount = cgst_amount + sgst_amount
            total_amount = round(subtotal + tax_amount, 2)
            
            # Calculate effective tax rate for display (backward compatibility)
            tax_rate = round((tax_amount / subtotal) * 100, 2) if subtotal > 0 else 5.0
            
            # Update bill with CGST/SGST, tax breakdown, and enriched items
            cursor.execute("""
                UPDATE bills 
                SET items = %s, subtotal = %s, tax_rate = %s, tax_amount = %s, 
                    cgst_amount = %s, sgst_amount = %s, tax_breakdown = %s, total_amount = %s
                WHERE id = %s
            """, (json.dumps(enriched_items), subtotal, tax_rate, tax_amount, 
                  cgst_amount, sgst_amount, json.dumps(tax_breakdown), total_amount, bill_id))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return {
                'bill_id': bill_id,
                'subtotal': subtotal,
                'tax_rate': tax_rate,
                'tax_amount': tax_amount,
                'cgst_amount': cgst_amount,
                'sgst_amount': sgst_amount,
                'tax_breakdown': tax_breakdown,
                'total_amount': total_amount,
                'items_added': True
            }
        except Exception as e:
            print(f"Error adding items to bill: {e}")
            return None
    
    @staticmethod
    def create_bill(order_id, table_id, session_id, items, subtotal, hotel_id=None, guest_name=None):
        """Create a new bill for an order or add to existing OPEN bill for the same table.
        RULE: Only ONE open bill per table at any time. All orders merge into it."""
        try:
            # Check for ANY existing OPEN bill for this table (regardless of guest)
            existing_bill = Bill.get_any_open_bill_for_table(table_id)
            if existing_bill:
                # Add items to existing bill instead of creating new one
                # This ensures only ONE bill per table until payment is complete
                return Bill.add_items_to_bill(existing_bill['id'], items, order_id)
            
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Get hotel info
            hotel_name = ""
            hotel_address = ""
            table_number = ""
            waiter_id = None
            
            if hotel_id:
                cursor.execute("SELECT hotel_name, address, city FROM hotels WHERE id = %s", (hotel_id,))
                hotel = cursor.fetchone()
                if hotel:
                    hotel_name = hotel.get('hotel_name', '')
                    address = hotel.get('address', '')
                    city = hotel.get('city', '')
                    hotel_address = f"{address}, {city}" if address else city
            
            # Get table number and waiter_id
            cursor.execute("SELECT table_number, waiter_id FROM tables WHERE id = %s", (table_id,))
            table = cursor.fetchone()
            if table:
                table_number = table.get('table_number', '')
                waiter_id = table.get('waiter_id')
            
            # If waiter_id not in table, try to get from order
            if not waiter_id and order_id:
                cursor.execute("SELECT waiter_id FROM table_orders WHERE id = %s", (order_id,))
                order = cursor.fetchone()
                if order:
                    waiter_id = order.get('waiter_id')
            
            # Enrich items with per-item tax info
            enriched_items = Bill.enrich_items_with_tax(items, cursor)
            
            # Calculate category-wise tax breakdown using helper
            tax_result = Bill.calculate_category_tax_breakdown(items, cursor)
            cgst_amount = tax_result['total_cgst']
            sgst_amount = tax_result['total_sgst']
            tax_breakdown = tax_result['breakdown']
            tax_amount = cgst_amount + sgst_amount
            total_amount = round(subtotal + tax_amount, 2)
            
            # Calculate effective tax rate for display (backward compatibility)
            tax_rate = round((tax_amount / subtotal) * 100, 2) if subtotal > 0 else 5.0
            
            # Generate bill number
            bill_number = Bill.generate_bill_number()
            
            import json
            items_json = json.dumps(enriched_items)
            tax_breakdown_json = json.dumps(tax_breakdown)
            
            cursor.execute("""
                INSERT INTO bills 
                (bill_number, order_id, hotel_id, table_id, session_id, guest_name, hotel_name, hotel_address, 
                 table_number, items, subtotal, tax_rate, tax_amount, cgst_amount, sgst_amount, tax_breakdown, total_amount, bill_status, waiter_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'OPEN', %s)
            """, (bill_number, order_id, hotel_id, table_id, session_id, guest_name, hotel_name, hotel_address,
                  table_number, items_json, subtotal, tax_rate, tax_amount, cgst_amount, sgst_amount, tax_breakdown_json, total_amount, waiter_id))
            
            bill_id = cursor.lastrowid
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return {
                'bill_id': bill_id,
                'bill_number': bill_number,
                'subtotal': subtotal,
                'tax_rate': tax_rate,
                'tax_amount': tax_amount,
                'cgst_amount': cgst_amount,
                'sgst_amount': sgst_amount,
                'tax_breakdown': tax_breakdown,
                'total_amount': total_amount
            }
        except Exception as e:
            print(f"Error creating bill: {e}")
            return None
    
    @staticmethod
    def get_bill_by_order(order_id):
        """Get bill for a specific order"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT b.*, h.hotel_name, h.logo as hotel_logo
                FROM bills b
                LEFT JOIN hotels h ON b.hotel_id = h.id
                WHERE b.order_id = %s
            """, (order_id,))
            
            bill = cursor.fetchone()
            
            if bill and bill.get('items'):
                import json
                items = json.loads(bill['items'])
                # Enrich items with tax info if missing
                if items:  # Always enrich with current tax rates
                    items = Bill.enrich_items_with_tax(items, cursor)
                    bill['items'] = items
                else:
                    bill['items'] = items
            
            cursor.close()
            connection.close()
            return bill
        except Exception as e:
            print(f"Error getting bill: {e}")
            return None
    
    @staticmethod
    def get_bill_by_session(table_id, session_id):
        """Get all bills for a session"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT * FROM bills 
                WHERE table_id = %s AND session_id = %s
                ORDER BY created_at DESC
            """, (table_id, session_id))
            
            bills = cursor.fetchall()
            
            import json
            for bill in bills:
                if bill.get('items'):
                    items = json.loads(bill['items'])
                    # Enrich items with tax info if missing
                    if items:  # Always enrich with current tax rates
                        items = Bill.enrich_items_with_tax(items, cursor)
                    bill['items'] = items
            
            cursor.close()
            connection.close()
            return bills
        except Exception as e:
            print(f"Error getting session bills: {e}")
            return []
    
    @staticmethod
    def get_session_total(table_id, session_id):
        """Get combined bill for entire session"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Get all orders for this session
            cursor.execute("""
                SELECT o.*, t.table_number, h.hotel_name, h.address, h.city, h.logo as hotel_logo
                FROM table_orders o
                JOIN tables t ON o.table_id = t.id
                LEFT JOIN hotels h ON t.hotel_id = h.id
                WHERE o.table_id = %s AND o.session_id = %s
                ORDER BY o.created_at ASC
            """, (table_id, session_id))
            
            orders = cursor.fetchall()
            
            if not orders:
                cursor.close()
                connection.close()
                return None
            
            # Combine all items
            import json
            all_items = []
            subtotal = 0
            
            for order in orders:
                items = json.loads(order['items']) if isinstance(order['items'], str) else order['items']
                all_items.extend(items)
                subtotal += float(order['total_amount'])
            
            # Get hotel info from first order
            first_order = orders[0]
            hotel_name = first_order.get('hotel_name', '')
            hotel_logo = first_order.get('hotel_logo', '')
            address = first_order.get('address', '')
            city = first_order.get('city', '')
            hotel_address = f"{address}, {city}" if address else city
            table_number = first_order.get('table_number', '')
            guest_name = first_order.get('guest_name', '')
            
            # Calculate category-wise tax breakdown using helper
            tax_result = Bill.calculate_category_tax_breakdown(all_items, cursor)
            cgst_amount = tax_result['total_cgst']
            sgst_amount = tax_result['total_sgst']
            tax_breakdown = tax_result['breakdown']
            tax_amount = cgst_amount + sgst_amount
            total_amount = round(subtotal + tax_amount, 2)
            
            # Calculate effective tax rate for display (backward compatibility)
            tax_rate = round((tax_amount / subtotal) * 100, 2) if subtotal > 0 else 5.0
            
            # Get payment status and payment_method from bills table
            cursor.execute("""
                SELECT payment_status, payment_method, bill_number, cgst_amount, sgst_amount, tax_breakdown
                FROM bills 
                WHERE table_id = %s AND session_id = %s
                ORDER BY created_at DESC LIMIT 1
            """, (table_id, session_id))
            bill_info = cursor.fetchone()
            
            if bill_info:
                payment_status = bill_info.get('payment_status', 'PENDING')
                payment_method = bill_info.get('payment_method', '')
                bill_number = bill_info.get('bill_number', '')
                # Use stored values if available
                if bill_info.get('cgst_amount') is not None:
                    cgst_amount = float(bill_info.get('cgst_amount'))
                    sgst_amount = float(bill_info.get('sgst_amount'))
                if bill_info.get('tax_breakdown'):
                    stored_breakdown = bill_info.get('tax_breakdown')
                    if isinstance(stored_breakdown, str):
                        tax_breakdown = json.loads(stored_breakdown)
                    else:
                        tax_breakdown = stored_breakdown
            else:
                # Fallback: check if all orders are paid
                cursor.execute("""
                    SELECT COUNT(*) as unpaid FROM table_orders 
                    WHERE table_id = %s AND session_id = %s AND payment_status != 'PAID'
                """, (table_id, session_id))
                unpaid_result = cursor.fetchone()
                payment_status = 'PAID' if unpaid_result['unpaid'] == 0 else 'PENDING'
                payment_method = ''
                bill_number = ''
            
            # Enrich items with per-item tax info before returning
            enriched_items = Bill.enrich_items_with_tax(all_items, cursor)
            
            cursor.close()
            connection.close()
            
            return {
                'hotel_name': hotel_name,
                'hotel_logo': hotel_logo,
                'hotel_address': hotel_address,
                'table_number': table_number,
                'guest_name': guest_name,
                'items': enriched_items,
                'subtotal': subtotal,
                'tax_rate': tax_rate,
                'tax_amount': tax_amount,
                'cgst_amount': cgst_amount,
                'sgst_amount': sgst_amount,
                'tax_breakdown': tax_breakdown,
                'total_amount': total_amount,
                'payment_status': payment_status,
                'payment_method': payment_method,
                'bill_number': bill_number,
                'order_count': len(orders),
                'created_at': orders[0]['created_at']
            }
        except Exception as e:
            print(f"Error getting session total: {e}")
            return None
    
    @staticmethod
    def process_payment(table_id, session_id, payment_method='CASH'):
        """Process payment for all orders in a session (atomic transaction)"""
        try:
            connection = get_db_connection()
            connection.start_transaction()
            cursor = connection.cursor()
            import datetime
            paid_at = datetime.datetime.now()
            # Update all orders in session to PAID
            cursor.execute("""
                UPDATE table_orders 
                SET payment_status = 'PAID'
                WHERE table_id = %s AND session_id = %s
            """, (table_id, session_id))
            # Update all bills in session to PAID and COMPLETED
            cursor.execute("""
                UPDATE bills 
                SET payment_status = 'PAID', payment_method = %s, paid_at = %s, bill_status = 'COMPLETED'
                WHERE table_id = %s AND session_id = %s
            """, (payment_method, paid_at, table_id, session_id))
            # Also update any OPEN bills for this table (fallback for session mismatch)
            cursor.execute("""
                UPDATE bills 
                SET payment_status = 'PAID', payment_method = %s, paid_at = %s, bill_status = 'COMPLETED'
                WHERE table_id = %s AND bill_status = 'OPEN'
            """, (payment_method, paid_at, table_id))
            # Mark table as available and clear session + guest_name
            cursor.execute("""
                UPDATE tables 
                SET status = 'AVAILABLE', current_session_id = NULL, current_guest_name = NULL
                WHERE id = %s
            """, (table_id,))
            # Close the active table entry (CRITICAL: bill closed = active table closed)
            cursor.execute("""
                UPDATE active_tables 
                SET status = 'CLOSED', closed_at = %s
                WHERE table_id = %s AND status = 'ACTIVE'
            """, (paid_at, table_id))
            connection.commit()
            cursor.close()
            connection.close()
            return True
        except Exception as e:
            if 'connection' in locals():
                connection.rollback()
                cursor.close()
                connection.close()
            print(f"Error processing payment: {e}")
            return False

    @staticmethod
    def process_payment_atomic(table_id, bill_id, payment_method='CASH', tip_amount=0.00):
        """Process payment atomically - ALWAYS succeeds if bill exists and is OPEN
        tip_amount: Optional tip for waiter (does NOT affect hotel wallet)
        Tips are assigned to the specific waiter who served the order (from bill.waiter_id)
        """
        connection = None
        cursor = None
        try:
            import datetime
            connection = get_db_connection()
            connection.start_transaction()
            cursor = connection.cursor(dictionary=True)
            
            print(f"[PAYMENT ATOMIC] Starting payment for table_id={table_id}, bill_id={bill_id}, tip={tip_amount}")
            
            # Lock and verify bill is OPEN - also get waiter_id for tip assignment
            cursor.execute("""
                SELECT id, bill_status, table_id, session_id, guest_name, subtotal, tax_amount, waiter_id
                FROM bills 
                WHERE id = %s AND bill_status = 'OPEN'
                FOR UPDATE
            """, (bill_id,))
            
            bill = cursor.fetchone()
            if not bill:
                print(f"[PAYMENT ATOMIC ERROR] Bill not found or not OPEN: bill_id={bill_id}")
                connection.rollback()
                if cursor:
                    cursor.close()
                if connection:
                    connection.close()
                return False
            
            print(f"[PAYMENT ATOMIC] Bill found: {bill}")
            
            paid_at = datetime.datetime.now()
            
            # Calculate new total with tip
            subtotal = float(bill.get('subtotal', 0))
            tax_amount = float(bill.get('tax_amount', 0))
            tip = float(tip_amount) if tip_amount else 0.00
            
            # Validate tip (must be non-negative)
            if tip < 0:
                tip = 0.00
            
            new_total = round(subtotal + tax_amount + tip, 2)
            
            print(f"[PAYMENT ATOMIC] Calculated totals: subtotal={subtotal}, tax={tax_amount}, tip={tip}, new_total={new_total}")
            
            # Assign tip to the waiter who served this order (from bill.waiter_id)
            if tip > 0:
                try:
                    # First priority: Use waiter_id from the bill itself (the actual server)
                    bill_waiter_id = bill.get('waiter_id')
                    
                    if bill_waiter_id:
                        # Assign full tip to the waiter who served this order
                        print(f"[PAYMENT ATOMIC] Assigning tip to bill's waiter: waiter_id={bill_waiter_id}, amount=₹{tip}")
                        
                        try:
                            cursor.execute("""
                                INSERT INTO waiter_tips (waiter_id, bill_id, tip_amount, created_at)
                                VALUES (%s, %s, %s, %s)
                            """, (bill_waiter_id, bill_id, tip, paid_at))
                            
                            print(f"[PAYMENT ATOMIC] Tip recorded: waiter_id={bill_waiter_id}, amount=₹{tip}")
                        except Exception as tip_error:
                            print(f"[PAYMENT ATOMIC WARNING] Could not record tip in waiter_tips table: {tip_error}")
                    else:
                        # Fallback: Try to get waiters from table assignments (for backward compatibility)
                        cursor.execute("""
                            SELECT DISTINCT waiter_id 
                            FROM waiter_table_assignments 
                            WHERE table_id = %s
                        """, (table_id,))
                        
                        assigned_waiters = cursor.fetchall()
                        
                        if assigned_waiters and len(assigned_waiters) > 0:
                            waiter_count = len(assigned_waiters)
                            tip_per_waiter = round(tip / waiter_count, 2)
                            
                            print(f"[PAYMENT ATOMIC] No waiter_id in bill, distributing to {waiter_count} assigned waiters: ₹{tip_per_waiter} each")
                            
                            # Also update the bill's waiter_id with the first assigned waiter for record keeping
                            first_waiter_id = assigned_waiters[0]['waiter_id']
                            cursor.execute("""
                                UPDATE bills SET waiter_id = %s WHERE id = %s AND waiter_id IS NULL
                            """, (first_waiter_id, bill_id))
                            
                            try:
                                for waiter in assigned_waiters:
                                    waiter_id = waiter['waiter_id']
                                    cursor.execute("""
                                        INSERT INTO waiter_tips (waiter_id, bill_id, tip_amount, created_at)
                                        VALUES (%s, %s, %s, %s)
                                    """, (waiter_id, bill_id, tip_per_waiter, paid_at))
                                    
                                    print(f"[PAYMENT ATOMIC] Tip recorded: waiter_id={waiter_id}, amount=₹{tip_per_waiter}")
                            except Exception as tip_error:
                                print(f"[PAYMENT ATOMIC WARNING] Could not record tips in waiter_tips table: {tip_error}")
                        else:
                            print(f"[PAYMENT ATOMIC WARNING] No waiter_id in bill and no waiters assigned to table {table_id}, tip not distributed")
                except Exception as e:
                    # Gracefully handle any tip distribution errors - don't fail the payment
                    print(f"[PAYMENT ATOMIC WARNING] Error during tip distribution: {e}")
                    print(f"[PAYMENT ATOMIC WARNING] Payment will continue, but tips not distributed")
            
            # Mark bill as PAID and COMPLETED with tip
            cursor.execute("""
                UPDATE bills 
                SET payment_status = 'PAID', 
                    payment_method = %s, 
                    paid_at = %s, 
                    bill_status = 'COMPLETED',
                    tip_amount = %s,
                    total_amount = %s
                WHERE id = %s
            """, (payment_method, paid_at, tip, new_total, bill_id))
            
            print(f"[PAYMENT ATOMIC] Bill updated, rows affected: {cursor.rowcount}")
            
            # Update associated orders to PAID
            bill_session_id = bill.get('session_id')
            bill_guest_name = bill.get('guest_name')
            
            if bill_session_id:
                cursor.execute("""
                    UPDATE table_orders 
                    SET payment_status = 'PAID'
                    WHERE table_id = %s AND session_id = %s
                """, (table_id, bill_session_id))
                print(f"[PAYMENT ATOMIC] Orders updated by session_id, rows affected: {cursor.rowcount}")
            elif bill_guest_name:
                cursor.execute("""
                    UPDATE table_orders 
                    SET payment_status = 'PAID'
                    WHERE table_id = %s AND guest_name = %s
                """, (table_id, bill_guest_name))
                print(f"[PAYMENT ATOMIC] Orders updated by guest_name, rows affected: {cursor.rowcount}")
            
            # Check if any other OPEN bills exist for this table
            cursor.execute("""
                SELECT COUNT(*) as count FROM bills 
                WHERE table_id = %s AND bill_status = 'OPEN' AND id != %s
            """, (table_id, bill_id))
            
            result = cursor.fetchone()
            other_open_bills = result['count'] if result else 0
            
            print(f"[PAYMENT ATOMIC] Other open bills for table: {other_open_bills}")
            
            # Release table ONLY if no other open bills
            if other_open_bills == 0:
                cursor.execute("""
                    UPDATE tables 
                    SET status = 'AVAILABLE', 
                        current_session_id = NULL, 
                        current_guest_name = NULL
                    WHERE id = %s
                """, (table_id,))
                
                print(f"[PAYMENT ATOMIC] Table released, rows affected: {cursor.rowcount}")
                
                # Close active table entry - DELETE instead of UPDATE to avoid unique constraint issues
                cursor.execute("""
                    DELETE FROM active_tables 
                    WHERE table_id = %s AND status = 'ACTIVE'
                """, (table_id,))
                
                print(f"[PAYMENT ATOMIC] Active table entry deleted, rows affected: {cursor.rowcount}")
            
            connection.commit()
            print(f"[PAYMENT ATOMIC SUCCESS] Transaction committed for bill_id={bill_id}")
            
            if cursor:
                cursor.close()
            if connection:
                connection.close()
            return True
            
        except Exception as e:
            import traceback
            print(f"[PAYMENT ATOMIC ERROR] Exception: {e}")
            print(f"[PAYMENT ATOMIC ERROR] Traceback: {traceback.format_exc()}")
            if connection:
                try:
                    connection.rollback()
                    print(f"[PAYMENT ATOMIC] Transaction rolled back")
                except Exception as rollback_error:
                    print(f"[PAYMENT ATOMIC ERROR] Rollback failed: {rollback_error}")
            if cursor:
                try:
                    cursor.close()
                except:
                    pass
            if connection:
                try:
                    connection.close()
                except:
                    pass
            return False

    @staticmethod
    def process_payment_by_guest(table_id, guest_name, payment_method='CASH'):
        """Process payment for a specific guest's OPEN bill (atomic transaction)"""
        try:
            connection = get_db_connection()
            connection.start_transaction()
            cursor = connection.cursor()
            import datetime
            paid_at = datetime.datetime.now()
            # Update the guest's OPEN bill to PAID
            cursor.execute("""
                UPDATE bills 
                SET payment_status = 'PAID', payment_method = %s, paid_at = %s, bill_status = 'COMPLETED'
                WHERE table_id = %s AND guest_name = %s AND bill_status = 'OPEN'
            """, (payment_method, paid_at, table_id, guest_name))
            rows_updated = cursor.rowcount
            if rows_updated > 0:
                # Update associated orders
                cursor.execute("""
                    UPDATE table_orders 
                    SET payment_status = 'PAID'
                    WHERE table_id = %s AND guest_name = %s AND payment_status != 'PAID'
                """, (table_id, guest_name))
                # Check if there are any remaining OPEN bills for this table
                cursor.execute("""
                    SELECT COUNT(*) FROM bills 
                    WHERE table_id = %s AND bill_status = 'OPEN'
                """, (table_id,))
                open_bills_count = cursor.fetchone()[0]
                # Clear table and close active entry only if no other open bills
                if open_bills_count == 0:
                    cursor.execute("""
                        UPDATE tables 
                        SET status = 'AVAILABLE', current_session_id = NULL, current_guest_name = NULL
                        WHERE id = %s
                    """, (table_id,))
                    # Close the active table entry (CRITICAL: bill closed = active table closed)
                    cursor.execute("""
                        UPDATE active_tables 
                        SET status = 'CLOSED', closed_at = %s
                        WHERE table_id = %s AND status = 'ACTIVE'
                    """, (paid_at, table_id))
            connection.commit()
            cursor.close()
            connection.close()
            return rows_updated > 0
        except Exception as e:
            if 'connection' in locals():
                connection.rollback()
                cursor.close()
                connection.close()
            print(f"Error processing payment by guest: {e}")
            return False
    
    @staticmethod
    def complete_bill(bill_id):
        """Complete a bill - lock it and finalize, free table if no other open bills"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Get bill info first
            cursor.execute("SELECT table_id, guest_name FROM bills WHERE id = %s", (bill_id,))
            bill = cursor.fetchone()
            
            if not bill:
                cursor.close()
                connection.close()
                print(f"[COMPLETE_BILL] Bill not found: {bill_id}")
                return False
            
            table_id = bill['table_id']
            
            # Mark bill as COMPLETED and PAID with timestamp
            import datetime
            paid_at = datetime.datetime.now()
            
            cursor.execute("""
                UPDATE bills 
                SET bill_status = 'COMPLETED', 
                    payment_status = 'PAID',
                    paid_at = %s
                WHERE id = %s
            """, (paid_at, bill_id))
            
            print(f"[COMPLETE_BILL] Updated bill {bill_id} to COMPLETED/PAID")
            
            # Check if there are any remaining OPEN bills for this table
            cursor.execute(
                "SELECT COUNT(*) as count FROM bills WHERE table_id = %s AND bill_status = 'OPEN'",
                (table_id,)
            )
            result = cursor.fetchone()
            open_bills_count = result['count'] if result else 0
            
            print(f"[COMPLETE_BILL] Remaining open bills for table {table_id}: {open_bills_count}")
            
            # Free table and close active entry only if no more open bills
            if open_bills_count == 0:
                closed_at = datetime.datetime.now()
                
                cursor.execute("""
                    UPDATE tables 
                    SET status = 'AVAILABLE', current_session_id = NULL, current_guest_name = NULL
                    WHERE id = %s
                """, (table_id,))
                
                print(f"[COMPLETE_BILL] Released table {table_id}")
                
                # Delete the active table entry instead of updating to avoid unique constraint issues
                # (table_id, status) has a unique constraint, so we delete ACTIVE entries
                cursor.execute("""
                    DELETE FROM active_tables 
                    WHERE table_id = %s AND status = 'ACTIVE'
                """, (table_id,))
                
                print(f"[COMPLETE_BILL] Deleted active_tables entry for table {table_id}")
            
            connection.commit()
            cursor.close()
            connection.close()
            
            print(f"[COMPLETE_BILL] Successfully completed bill {bill_id}")
            return True
        except Exception as e:
            print(f"[COMPLETE_BILL ERROR] Error completing bill {bill_id}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @staticmethod
    def get_open_bill_by_table_and_guest(table_id, guest_name):
        """Get open bill for a specific table and guest"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT b.*, h.hotel_name, h.logo as hotel_logo
                FROM bills b
                LEFT JOIN hotels h ON b.hotel_id = h.id
                WHERE b.table_id = %s AND b.guest_name = %s AND b.bill_status = 'OPEN'
                ORDER BY b.created_at DESC LIMIT 1
            """, (table_id, guest_name))
            
            bill = cursor.fetchone()
            
            if bill and bill.get('items'):
                import json
                items = json.loads(bill['items'])
                # Enrich items with tax info if missing
                if items:  # Always enrich with current tax rates
                    items = Bill.enrich_items_with_tax(items, cursor)
                bill['items'] = items
            
            cursor.close()
            connection.close()
            return bill
        except Exception as e:
            print(f"Error getting open bill: {e}")
            return None
    
    @staticmethod
    def get_bill_by_id(bill_id):
        """Get bill by ID with table info and hotel logo"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT b.*, t.table_number, h.hotel_name, h.logo as hotel_logo
                FROM bills b
                JOIN tables t ON b.table_id = t.id
                LEFT JOIN hotels h ON b.hotel_id = h.id
                WHERE b.id = %s
            """, (bill_id,))
            bill = cursor.fetchone()
            
            if bill and bill.get('items'):
                import json
                items = json.loads(bill['items'])
                # Enrich items with tax info if missing
                if items:  # Always enrich with current tax rates
                    items = Bill.enrich_items_with_tax(items, cursor)
                    bill['items'] = items
                else:
                    bill['items'] = items
            
            cursor.close()
            connection.close()
            return bill
        except Exception as e:
            print(f"Error getting bill: {e}")
            return None
    
    @staticmethod
    def get_all_active_bills(hotel_id=None):
        """Get all OPEN bills for the hotel - one per table"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            if hotel_id:
                cursor.execute("""
                    SELECT b.*, t.status as table_status, t.table_number, h.hotel_name, h.logo as hotel_logo
                    FROM bills b
                    JOIN tables t ON b.table_id = t.id
                    LEFT JOIN hotels h ON b.hotel_id = h.id
                    WHERE b.hotel_id = %s AND b.bill_status = 'OPEN'
                    ORDER BY b.created_at DESC
                """, (hotel_id,))
            else:
                cursor.execute("""
                    SELECT b.*, t.status as table_status, t.table_number, h.hotel_name, h.logo as hotel_logo
                    FROM bills b
                    JOIN tables t ON b.table_id = t.id
                    LEFT JOIN hotels h ON b.hotel_id = h.id
                    WHERE b.bill_status = 'OPEN'
                    ORDER BY b.created_at DESC
                """)
            
            bills = cursor.fetchall()
            
            import json
            for bill in bills:
                if bill.get('items'):
                    items = json.loads(bill['items'])
                    # Enrich items with tax info if missing
                    if items:  # Always enrich with current tax rates
                        items = Bill.enrich_items_with_tax(items, cursor)
                    bill['items'] = items
            
            cursor.close()
            connection.close()
            return bills
        except Exception as e:
            print(f"Error getting active bills: {e}")
            return []
    
    @staticmethod
    def get_all_bills(hotel_id=None, status=None):
        """Get all bills for hotel with optional status filter"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            query = """
                SELECT b.*, t.table_number, h.hotel_name, h.logo as hotel_logo
                FROM bills b
                JOIN tables t ON b.table_id = t.id
                LEFT JOIN hotels h ON b.hotel_id = h.id
                WHERE 1=1
            """
            params = []
            
            if hotel_id:
                query += " AND b.hotel_id = %s"
                params.append(hotel_id)
            
            if status:
                query += " AND b.bill_status = %s"
                params.append(status)
            
            query += " ORDER BY b.created_at DESC"
            
            cursor.execute(query, params)
            bills = cursor.fetchall()
            
            import json
            for bill in bills:
                if bill.get('items'):
                    items = json.loads(bill['items'])
                    # Enrich items with tax info if missing
                    if items:  # Always enrich with current tax rates
                        items = Bill.enrich_items_with_tax(items, cursor)
                    bill['items'] = items
            
            cursor.close()
            connection.close()
            return bills
        except Exception as e:
            print(f"Error getting all bills: {e}")
            return []
    
    @staticmethod
    def get_tip_statistics_for_hotel(hotel_id, period='today'):
        """Get tip statistics for hotel (Manager Dashboard)
        period: 'today', 'week', 'month', 'all'
        """
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            date_filter = ""
            if period == 'today':
                date_filter = "AND DATE(paid_at) = CURDATE()"
            elif period == 'week':
                date_filter = "AND paid_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
            elif period == 'month':
                date_filter = "AND paid_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)"
            
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as bills_with_tips,
                    SUM(tip_amount) as total_tips,
                    AVG(tip_amount) as avg_tip,
                    MAX(tip_amount) as max_tip
                FROM bills 
                WHERE hotel_id = %s 
                AND payment_status = 'PAID' 
                AND tip_amount > 0
                {date_filter}
            """, (hotel_id,))
            
            stats = cursor.fetchone()
            
            cursor.close()
            connection.close()
            
            return {
                'bills_with_tips': stats['bills_with_tips'] or 0,
                'total_tips': float(stats['total_tips'] or 0),
                'avg_tip': float(stats['avg_tip'] or 0),
                'max_tip': float(stats['max_tip'] or 0)
            }
        except Exception as e:
            print(f"Error getting tip statistics: {e}")
            return {
                'bills_with_tips': 0,
                'total_tips': 0.0,
                'avg_tip': 0.0,
                'max_tip': 0.0
            }
    
    @staticmethod
    def get_tip_statistics_for_waiter(waiter_id, period='today'):
        """Get tip statistics for waiter (Waiter Dashboard)
        period: 'today', 'week', 'month', 'all'
        """
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            date_filter = ""
            if period == 'today':
                date_filter = "AND DATE(paid_at) = CURDATE()"
            elif period == 'week':
                date_filter = "AND paid_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
            elif period == 'month':
                date_filter = "AND paid_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)"
            
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as bills_with_tips,
                    SUM(tip_amount) as total_tips,
                    AVG(tip_amount) as avg_tip,
                    MAX(tip_amount) as max_tip
                FROM bills 
                WHERE waiter_id = %s 
                AND payment_status = 'PAID' 
                AND tip_amount > 0
                {date_filter}
            """, (waiter_id,))
            
            stats = cursor.fetchone()
            
            cursor.close()
            connection.close()
            
            return {
                'bills_with_tips': stats['bills_with_tips'] or 0,
                'total_tips': float(stats['total_tips'] or 0),
                'avg_tip': float(stats['avg_tip'] or 0),
                'max_tip': float(stats['max_tip'] or 0)
            }
        except Exception as e:
            print(f"Error getting waiter tip statistics: {e}")
            return {
                'bills_with_tips': 0,
                'total_tips': 0.0,
                'avg_tip': 0.0,
                'max_tip': 0.0
            }
    
    @staticmethod
    def get_waiter_tip_details(waiter_id, limit=10):
        """Get recent tip details for waiter"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT 
                    bill_number,
                    table_number,
                    guest_name,
                    tip_amount,
                    total_amount,
                    paid_at
                FROM bills 
                WHERE waiter_id = %s 
                AND payment_status = 'PAID' 
                AND tip_amount > 0
                ORDER BY paid_at DESC
                LIMIT %s
            """, (waiter_id, limit))
            
            tips = cursor.fetchall()
            
            cursor.close()
            connection.close()
            return tips
        except Exception as e:
            print(f"Error getting waiter tip details: {e}")
            return []
    
    @staticmethod
    def get_waiter_wise_tips(hotel_id, period='today'):
        """Get tip breakdown by waiter for manager dashboard
        period: 'today', 'week', 'month', 'all'
        Uses waiter_tips table for distributed tip tracking (falls back to bills table if not available)
        """
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Check if waiter_tips table exists
            cursor.execute("SHOW TABLES LIKE 'waiter_tips'")
            waiter_tips_exists = cursor.fetchone() is not None
            
            date_filter = ""
            if period == 'today':
                date_filter_wt = "AND DATE(wt.created_at) = CURDATE()"
                date_filter_b = "AND DATE(b.paid_at) = CURDATE()"
            elif period == 'week':
                date_filter_wt = "AND wt.created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
                date_filter_b = "AND b.paid_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
            elif period == 'month':
                date_filter_wt = "AND wt.created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)"
                date_filter_b = "AND b.paid_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)"
            else:
                date_filter_wt = ""
                date_filter_b = ""
            
            if waiter_tips_exists:
                # Use waiter_tips table for distributed tip tracking
                cursor.execute(f"""
                    SELECT 
                        w.id as waiter_id,
                        w.name as waiter_name,
                        SUM(CASE WHEN DATE(wt.created_at) = CURDATE() THEN wt.tip_amount ELSE 0 END) as today_tip,
                        SUM(wt.tip_amount) as total_tip,
                        COUNT(DISTINCT CASE WHEN DATE(wt.created_at) = CURDATE() THEN wt.bill_id END) as today_bills,
                        COUNT(DISTINCT wt.bill_id) as total_bills
                    FROM waiter_tips wt
                    JOIN waiters w ON wt.waiter_id = w.id
                    JOIN bills b ON wt.bill_id = b.id
                    WHERE b.hotel_id = %s 
                    AND wt.tip_amount > 0
                    {date_filter_wt}
                    GROUP BY w.id, w.name
                    ORDER BY today_tip DESC, total_tip DESC
                """, (hotel_id,))
            else:
                # Fallback to bills table (old method)
                print("[TIP_SUMMARY] waiter_tips table not found, using bills table (run setup_tip_distribution.py)")
                cursor.execute(f"""
                    SELECT 
                        w.id as waiter_id,
                        w.name as waiter_name,
                        SUM(CASE WHEN DATE(b.paid_at) = CURDATE() THEN b.tip_amount ELSE 0 END) as today_tip,
                        SUM(b.tip_amount) as total_tip,
                        COUNT(CASE WHEN DATE(b.paid_at) = CURDATE() THEN 1 END) as today_bills,
                        COUNT(*) as total_bills
                    FROM bills b
                    JOIN waiters w ON b.waiter_id = w.id
                    WHERE b.hotel_id = %s 
                    AND b.payment_status = 'PAID' 
                    AND b.tip_amount > 0
                    {date_filter_b}
                    GROUP BY b.waiter_id, w.name
                    ORDER BY today_tip DESC, total_tip DESC
                """, (hotel_id,))
            
            waiters = cursor.fetchall()
            
            # Convert Decimal to float for JSON serialization
            for waiter in waiters:
                waiter['today_tip'] = float(waiter['today_tip'] or 0)
                waiter['total_tip'] = float(waiter['total_tip'] or 0)
            
            cursor.close()
            connection.close()
            
            return waiters
        except Exception as e:
            print(f"Error getting waiter-wise tips: {e}")
            import traceback
            traceback.print_exc()
            return []


class ActiveTable:
    """Manages active table sessions - tracks which tables have open bills"""
    
    @staticmethod
    def create_or_get_active_entry(table_id, bill_id, guest_name, session_id=None, hotel_id=None):
        """Create new active table entry or get existing one. One ACTIVE entry per table."""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Check if there's already an ACTIVE entry for this table
            cursor.execute("""
                SELECT * FROM active_tables 
                WHERE table_id = %s AND status = 'ACTIVE'
            """, (table_id,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing entry with new bill_id if changed
                if existing.get('bill_id') != bill_id:
                    cursor.execute("""
                        UPDATE active_tables 
                        SET bill_id = %s, guest_name = %s, session_id = %s
                        WHERE id = %s
                    """, (bill_id, guest_name, session_id, existing['id']))
                    connection.commit()
                cursor.close()
                connection.close()
                return existing['id']
            
            # Create new ACTIVE entry
            cursor.execute("""
                INSERT INTO active_tables (table_id, bill_id, hotel_id, guest_name, session_id, status)
                VALUES (%s, %s, %s, %s, %s, 'ACTIVE')
            """, (table_id, bill_id, hotel_id, guest_name, session_id))
            
            entry_id = cursor.lastrowid
            
            # Also update the table status to BUSY
            cursor.execute("""
                UPDATE tables SET status = 'BUSY', current_guest_name = %s, current_session_id = %s
                WHERE id = %s
            """, (guest_name, session_id, table_id))
            
            connection.commit()
            cursor.close()
            connection.close()
            return entry_id
        except Exception as e:
            print(f"Error creating active table entry: {e}")
            return None
    
    @staticmethod
    def close_active_entry(table_id):
        """Close active table entry when payment is completed"""
        try:
            import datetime
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Mark active entry as CLOSED
            cursor.execute("""
                UPDATE active_tables 
                SET status = 'CLOSED', closed_at = %s
                WHERE table_id = %s AND status = 'ACTIVE'
            """, (datetime.datetime.now(), table_id))
            
            # Also update table to AVAILABLE
            cursor.execute("""
                UPDATE tables 
                SET status = 'AVAILABLE', current_guest_name = NULL, current_session_id = NULL
                WHERE id = %s
            """, (table_id,))
            
            connection.commit()
            cursor.close()
            connection.close()
            return True
        except Exception as e:
            print(f"Error closing active table entry: {e}")
            return False
    
    @staticmethod
    def get_active_entry(table_id):
        """Get the ACTIVE entry for a table if exists"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT at.*, t.table_number, b.bill_number, b.total_amount, b.bill_status
                FROM active_tables at
                JOIN tables t ON at.table_id = t.id
                LEFT JOIN bills b ON at.bill_id = b.id
                WHERE at.table_id = %s AND at.status = 'ACTIVE'
            """, (table_id,))
            
            entry = cursor.fetchone()
            cursor.close()
            connection.close()
            return entry
        except Exception as e:
            print(f"Error getting active table entry: {e}")
            return None
    
    @staticmethod
    def get_all_active_tables(hotel_id=None):
        """Get all ACTIVE table entries for dashboard display"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            if hotel_id:
                cursor.execute("""
                    SELECT at.*, t.table_number, b.bill_number, b.total_amount, b.bill_status, b.items
                    FROM active_tables at
                    JOIN tables t ON at.table_id = t.id
                    LEFT JOIN bills b ON at.bill_id = b.id
                    WHERE at.status = 'ACTIVE' AND at.hotel_id = %s
                    ORDER BY at.created_at DESC
                """, (hotel_id,))
            else:
                cursor.execute("""
                    SELECT at.*, t.table_number, b.bill_number, b.total_amount, b.bill_status, b.items
                    FROM active_tables at
                    JOIN tables t ON at.table_id = t.id
                    LEFT JOIN bills b ON at.bill_id = b.id
                    WHERE at.status = 'ACTIVE'
                    ORDER BY at.created_at DESC
                """)
            
            entries = cursor.fetchall()
            
            import json
            for entry in entries:
                if entry.get('items'):
                    entry['items'] = json.loads(entry['items'])
            
            cursor.close()
            connection.close()
            return entries
        except Exception as e:
            print(f"Error getting all active tables: {e}")
            return []
    
    @staticmethod
    def is_table_active(table_id):
        """Check if a table has an ACTIVE entry (linked to open bill)"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM active_tables 
                WHERE table_id = %s AND status = 'ACTIVE'
            """, (table_id,))
            
            count = cursor.fetchone()[0]
            cursor.close()
            connection.close()
            return count > 0
        except Exception as e:
            print(f"Error checking table active status: {e}")
            return False
    
    @staticmethod
    def sync_with_bills():
        """Sync active_tables with bill status - close entries where bill is completed"""
        try:
            import datetime
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Close active entries where the linked bill is COMPLETED
            cursor.execute("""
                UPDATE active_tables at
                JOIN bills b ON at.bill_id = b.id
                SET at.status = 'CLOSED', at.closed_at = %s
                WHERE at.status = 'ACTIVE' AND b.bill_status = 'COMPLETED'
            """, (datetime.datetime.now(),))
            
            # Also close active entries that have no open bill for their table
            cursor.execute("""
                UPDATE active_tables at
                SET at.status = 'CLOSED', at.closed_at = %s
                WHERE at.status = 'ACTIVE' 
                AND NOT EXISTS (
                    SELECT 1 FROM bills b 
                    WHERE b.table_id = at.table_id AND b.bill_status = 'OPEN'
                )
            """, (datetime.datetime.now(),))
            
            connection.commit()
            cursor.close()
            connection.close()
            return True
        except Exception as e:
            print(f"Error syncing active tables with bills: {e}")
            return False
