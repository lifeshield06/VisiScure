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

            def drop_table_fk_constraints_for_archival(table_name, column_name='table_id'):
                """Drop FK constraints pointing to tables(id) so table deletion doesn't remove history."""
                try:
                    cursor.execute(
                        """
                        SELECT CONSTRAINT_NAME
                        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                        WHERE TABLE_SCHEMA = DATABASE()
                          AND TABLE_NAME = %s
                          AND COLUMN_NAME = %s
                          AND REFERENCED_TABLE_NAME = 'tables'
                        """,
                        (table_name, column_name)
                    )
                    constraints = cursor.fetchall() or []
                    for row in constraints:
                        constraint_name = row[0] if isinstance(row, tuple) else row.get('CONSTRAINT_NAME')
                        if constraint_name:
                            cursor.execute(f"ALTER TABLE {table_name} DROP FOREIGN KEY {constraint_name}")
                except Exception as e:
                    print(f"Error dropping FK {table_name}.{column_name} -> tables.id: {e}")
            
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
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                    utr_id VARCHAR(100),
                    paid_at TIMESTAMP NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            
            # Create waiter_tips table for distributed tip tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS waiter_tips (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    waiter_id INT NOT NULL,
                    bill_id INT NOT NULL,
                    tip_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_waiter_id (waiter_id),
                    INDEX idx_bill_id (bill_id),
                    INDEX idx_created_at (created_at),
                    UNIQUE KEY unique_waiter_bill_tip (waiter_id, bill_id)
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
            ensure_column("bills", "utr_id", "utr_id VARCHAR(100)")
            
            # Ensure per-waiter tips visibility column
            ensure_column("waiters", "show_waiter_tips", "show_waiter_tips TINYINT(1) DEFAULT 1")
            
            # Ensure payment columns exist in table_orders
            ensure_column("table_orders", "payment_status", "payment_status ENUM('PENDING', 'PAID') DEFAULT 'PENDING'")
            ensure_column("table_orders", "payment_method", "payment_method VARCHAR(50)")

            # Critical data-retention rule:
            # Keep orders/bills independent from table lifecycle.
            drop_table_fk_constraints_for_archival("table_orders", "table_id")
            drop_table_fk_constraints_for_archival("bills", "table_id")
            
            # Ensure charge_deducted column exists in table_orders (for per-order charge tracking)
            ensure_column("table_orders", "charge_deducted", "charge_deducted BOOLEAN DEFAULT FALSE")
            
            # Ensure waiter_id column exists in table_orders for direct waiter assignment
            ensure_column("table_orders", "waiter_id", "waiter_id INT")
            
            # Ensure columns exist in active_tables
            ensure_column("active_tables", "hotel_id", "hotel_id INT")
            ensure_column("active_tables", "session_id", "session_id VARCHAR(100)")
            
            # Ensure digital_fee_enabled column exists in hotel_wallet
            ensure_column("hotel_wallet", "digital_fee_enabled", "digital_fee_enabled TINYINT(1) DEFAULT 1")
            
            # Ensure frozen bill columns exist in bills table
            ensure_column("bills", "final_subtotal", "final_subtotal DECIMAL(10,2) DEFAULT NULL")
            ensure_column("bills", "final_tax", "final_tax DECIMAL(10,2) DEFAULT NULL")
            ensure_column("bills", "final_digital_fee", "final_digital_fee DECIMAL(10,2) DEFAULT NULL")
            ensure_column("bills", "final_total", "final_total DECIMAL(10,2) DEFAULT NULL")
            ensure_column("bills", "charges", "charges DECIMAL(10,2) DEFAULT 0.00")
            ensure_column("bills", "grand_total", "grand_total DECIMAL(10,2) DEFAULT NULL")
            ensure_column("bills", "payment_method", "payment_method VARCHAR(50)")
            ensure_column("bills", "is_charge_deducted", "is_charge_deducted BOOLEAN DEFAULT FALSE")
            ensure_column("bills", "convenience_fee", "convenience_fee DECIMAL(10,2) DEFAULT 0.00")
            ensure_column("bills", "bill_date", "bill_date DATETIME DEFAULT CURRENT_TIMESTAMP")
            ensure_column("bills", "discount_percent", "discount_percent DECIMAL(5,2) DEFAULT 0.00")
            ensure_column("bills", "discount_amount", "discount_amount DECIMAL(10,2) DEFAULT 0.00")
            
            # Ensure frozen total column in table_orders
            ensure_column("table_orders", "final_total", "final_total DECIMAL(10,2) DEFAULT NULL")
            
            # Ensure bill_requested column in table_orders
            ensure_column("table_orders", "bill_requested", "bill_requested TINYINT(1) DEFAULT 0")

            # Link each order to its resolved bill for one-running-bill workflows
            ensure_column("table_orders", "bill_id", "bill_id INT NULL")

            # Create bill_requests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bill_requests (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    table_id INT NOT NULL,
                    session_id VARCHAR(100),
                    guest_name VARCHAR(255),
                    hotel_id INT,
                    status ENUM('PENDING', 'APPROVED', 'REJECTED') DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            
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
    def sanitize_order_items(items):
        """Keep only valid items with positive quantity and non-negative price."""
        cleaned = []
        if not isinstance(items, list):
            return cleaned

        for item in items:
            if not isinstance(item, dict):
                continue

            try:
                quantity = int(item.get('quantity', 0))
                price = float(item.get('price', 0))
            except Exception:
                continue

            if quantity <= 0 or price < 0:
                continue

            name = str(item.get('name') or '').strip()
            if not name:
                continue

            cleaned.append({
                'id': item.get('id'),
                'name': name,
                'price': price,
                'quantity': quantity
            })

        return cleaned

    @staticmethod
    def resolve_valid_kitchen_section_id(cursor, kitchen_section_id):
        """Return a valid kitchen section id or None to satisfy FK constraints."""
        if kitchen_section_id is None:
            return None
        try:
            cursor.execute(
                "SELECT id FROM kitchen_sections WHERE id = %s LIMIT 1",
                (kitchen_section_id,)
            )
            row = cursor.fetchone()
            return row['id'] if row else None
        except Exception:
            return None

    @staticmethod
    def get_active_order_for_guest(table_id, session_id=None, guest_name=None):
        """Get existing ACTIVE/PREPARING order for same table + guest/session.

        Active condition:
        - order_status != COMPLETED
        - payment_status != PAID
        """
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            if session_id:
                cursor.execute("""
                    SELECT *
                    FROM table_orders
                    WHERE table_id = %s
                      AND session_id = %s
                      AND order_status IN ('ACTIVE', 'PREPARING')
                      AND COALESCE(payment_status, 'PENDING') != 'PAID'
                                            AND COALESCE(total_amount, 0) > 0
                                            AND COALESCE(JSON_LENGTH(items), 0) > 0
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (table_id, session_id))
            else:
                cursor.execute("""
                    SELECT *
                    FROM table_orders
                    WHERE table_id = %s
                      AND guest_name = %s
                      AND order_status IN ('ACTIVE', 'PREPARING')
                      AND COALESCE(payment_status, 'PENDING') != 'PAID'
                                            AND COALESCE(total_amount, 0) > 0
                                            AND COALESCE(JSON_LENGTH(items), 0) > 0
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (table_id, guest_name))

            row = cursor.fetchone()
            cursor.close()
            connection.close()
            return row
        except Exception as e:
            print(f"Error finding active order: {e}")
            return None

    @staticmethod
    def add_items_to_order(order_id, items):
        """Merge new items into an existing ACTIVE order."""
        try:
            items = TableOrder.sanitize_order_items(items)
            if not items:
                return None, "No valid items to add"

            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute("SELECT items FROM table_orders WHERE id = %s", (order_id,))
            order = cursor.fetchone()
            if not order:
                cursor.close()
                connection.close()
                return None, "Order not found"

            import json
            existing_items = json.loads(order['items']) if isinstance(order['items'], str) else (order['items'] or [])

            # Merge quantities for same dish (id+name+price fallback)
            for new_item in items:
                new_id = new_item.get('id')
                new_name = new_item.get('name')
                new_price = float(new_item.get('price', 0))
                new_qty = int(new_item.get('quantity', 1))

                matched = False
                for old_item in existing_items:
                    old_id = old_item.get('id')
                    old_name = old_item.get('name')
                    old_price = float(old_item.get('price', 0))
                    if (new_id and old_id and new_id == old_id) or (old_name == new_name and old_price == new_price):
                        old_item['quantity'] = int(old_item.get('quantity', 0)) + new_qty
                        matched = True
                        break

                if not matched:
                    existing_items.append(new_item)

            # Recompute order total from merged items
            merged_total = sum(float(i.get('price', 0)) * int(i.get('quantity', 1)) for i in existing_items)

            cursor.execute(
                "UPDATE table_orders SET items = %s, total_amount = %s WHERE id = %s",
                (json.dumps(existing_items), merged_total, order_id)
            )

            # Add new rows to order_items for kitchen routing
            for item in items:
                dish_id = item.get('id')
                dish_name = item.get('name', 'Unknown')
                quantity = item.get('quantity', 1)
                price = item.get('price', 0)
                if not dish_id:
                    continue

                cursor.execute("""
                    SELECT category_id, kitchen_id
                    FROM menu_dishes
                    WHERE id = %s
                    LIMIT 1
                """, (dish_id,))
                dish_info = cursor.fetchone()
                category_id = dish_info['category_id'] if dish_info else None
                kitchen_section_id = dish_info['kitchen_id'] if dish_info else None
                kitchen_section_id = TableOrder.resolve_valid_kitchen_section_id(cursor, kitchen_section_id)

                cursor.execute("""
                    INSERT INTO order_items
                    (order_id, dish_id, dish_name, category_id, kitchen_section_id, quantity, price, item_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'ACTIVE')
                """, (order_id, dish_id, dish_name, category_id, kitchen_section_id, quantity, price))

            connection.commit()
            cursor.close()
            connection.close()
            return order_id, None
        except Exception as e:
            print(f"Error merging items into order: {e}")
            import traceback
            traceback.print_exc()
            return None, str(e)

    @staticmethod
    def add_order(table_id, session_id, items, total_amount, hotel_id=None, guest_name=None, waiter_id=None):
        """Add new ACTIVE order and set table BUSY with assigned waiter. Also populate order_items table with kitchen routing."""
        try:
            items = TableOrder.sanitize_order_items(items)
            if not items:
                return None, "Order must contain at least one valid item"

            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            import json
            items_json = json.dumps(items)
            computed_total = round(sum(float(i.get('price', 0)) * int(i.get('quantity', 0)) for i in items), 2)
            if computed_total <= 0:
                cursor.close()
                connection.close()
                return None, "Order total must be greater than zero"
            
            # Add order as ACTIVE with guest_name and waiter_id from assigned table waiter
            cursor.execute(
                "INSERT INTO table_orders (table_id, session_id, guest_name, items, total_amount, order_status, hotel_id, waiter_id) VALUES (%s, %s, %s, %s, %s, 'ACTIVE', %s, %s)",
                (table_id, session_id, guest_name, items_json, computed_total, hotel_id, waiter_id)
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
                kitchen_section_id = TableOrder.resolve_valid_kitchen_section_id(cursor, kitchen_section_id)
                
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
    def get_all_orders(hotel_id=None, date_from=None, date_to=None, payment_method=None, payment_status=None, table_number=None):
        """Get all orders with table info for a specific hotel with optional filters."""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            conditions = []
            params = []

            if hotel_id:
                conditions.append("(o.hotel_id = %s OR (o.hotel_id IS NULL AND t.hotel_id = %s))")
                params.extend([hotel_id, hotel_id])

            # Safety filter: manager views should never show empty/unconfirmed orders.
            conditions.append("COALESCE(o.total_amount, 0) > 0")
            conditions.append("COALESCE(JSON_LENGTH(o.items), 0) > 0")

            if date_from:
                conditions.append("DATE(o.created_at) >= %s")
                params.append(date_from)

            if date_to:
                conditions.append("DATE(o.created_at) <= %s")
                params.append(date_to)

            if payment_method:
                conditions.append("""
                    EXISTS (
                        SELECT 1 FROM bills bfm
                        WHERE bfm.table_id = o.table_id
                          AND bfm.session_id = o.session_id
                          AND UPPER(COALESCE(bfm.payment_method, '')) = %s
                    )
                """)
                params.append(payment_method)

            paid_condition = """
                (
                    UPPER(COALESCE(o.payment_status, '')) = 'PAID'
                    OR EXISTS (
                        SELECT 1 FROM bills bps
                        WHERE bps.table_id = o.table_id
                          AND bps.session_id = o.session_id
                          AND UPPER(COALESCE(bps.payment_status, '')) = 'PAID'
                    )
                    OR EXISTS (
                        SELECT 1 FROM bills bpm
                        WHERE bpm.table_id = o.table_id
                          AND bpm.session_id = o.session_id
                          AND UPPER(COALESCE(bpm.payment_method, '')) IN ('UPI', 'ONLINE', 'RAZORPAY', 'CARD', 'NETBANKING', 'WALLET')
                    )
                )
            """

            if payment_status == 'PAID':
                conditions.append(paid_condition)
            elif payment_status == 'PENDING':
                conditions.append(f"NOT {paid_condition}")

            if table_number:
                conditions.append("COALESCE(CAST(t.table_number AS CHAR), 'Table Deleted') LIKE %s")
                params.append(f"%{table_number}%")

            where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

            query = f"""
                  SELECT o.*, COALESCE(CAST(t.table_number AS CHAR), 'Table Deleted') as table_number,
                      COALESCE(t.status, 'DELETED') as table_status,
                       (SELECT b.payment_method FROM bills b
                        WHERE b.table_id = o.table_id AND b.session_id = o.session_id
                        ORDER BY b.created_at DESC LIMIT 1) as payment_method,
                       (SELECT b.utr_id FROM bills b
                        WHERE b.table_id = o.table_id AND b.session_id = o.session_id
                        ORDER BY b.created_at DESC LIMIT 1) as bill_utr_id,
                       (SELECT b.payment_status FROM bills b
                        WHERE b.table_id = o.table_id AND b.session_id = o.session_id
                        ORDER BY b.created_at DESC LIMIT 1) as bill_payment_status,
                       (SELECT br.id FROM bill_requests br
                        WHERE br.table_id = o.table_id AND br.session_id = o.session_id
                        ORDER BY br.created_at DESC LIMIT 1) as bill_request_id,
                       (SELECT br.status FROM bill_requests br
                        WHERE br.table_id = o.table_id AND br.session_id = o.session_id
                        ORDER BY br.created_at DESC LIMIT 1) as bill_request_status,
                       (SELECT COALESCE(b.final_total, b.total_amount) FROM bills b
                        WHERE b.table_id = o.table_id AND b.session_id = o.session_id
                        AND b.payment_status = 'PAID'
                        ORDER BY b.created_at DESC LIMIT 1) as bill_frozen_total,
                       (SELECT COALESCE(b.final_total, b.grand_total, b.total_amount) FROM bills b
                        WHERE b.table_id = o.table_id AND b.session_id = o.session_id
                        ORDER BY b.created_at DESC LIMIT 1) as bill_running_total,
                       (SELECT COALESCE(b.charges, 0) FROM bills b
                        WHERE b.table_id = o.table_id AND b.session_id = o.session_id
                        ORDER BY b.created_at DESC LIMIT 1) as bill_charges,
                       (SELECT COUNT(*) FROM bills b
                        WHERE b.table_id = o.table_id AND b.session_id = o.session_id
                        LIMIT 1) as bill_exists
                FROM table_orders o
                LEFT JOIN tables t ON o.table_id = t.id
                {where_clause}
                ORDER BY o.created_at DESC
            """

            cursor.execute(query, tuple(params))
            
            orders = cursor.fetchall()
            
            import json
            for order in orders:
                payment_method = str(order.get('payment_method') or '').upper()
                is_digital_method = payment_method in ('UPI', 'ONLINE', 'RAZORPAY', 'CARD', 'NETBANKING', 'WALLET')
                bill_payment_status = str(order.get('bill_payment_status') or '').upper()
                order['utr_id'] = order.get('bill_utr_id') or order.get('utr_id')

                # For digital modes, payment is treated as auto-completed in manager flow.
                if (bill_payment_status == 'PAID' or is_digital_method) and order.get('payment_status') != 'PAID':
                    order['payment_status'] = 'PAID'
                    try:
                        cursor.execute(
                            "UPDATE table_orders SET payment_status = 'PAID' WHERE id = %s AND (payment_status IS NULL OR payment_status != 'PAID')",
                            (order.get('id'),)
                        )
                    except Exception:
                        pass

                raw_items = order.get('items')
                if raw_items:
                    try:
                        order['items'] = json.loads(raw_items) if isinstance(raw_items, str) else raw_items
                    except Exception:
                        order['items'] = []
                else:
                    order['items'] = []

                # Sync request flags from latest bill_requests so manager UI is consistent.
                latest_request_status = order.get('bill_request_status')
                order['billRequestStatus'] = latest_request_status
                order['billRequestId'] = order.get('bill_request_id')
                order['bill_requested'] = bool(order.get('bill_requested')) or (latest_request_status in ('PENDING', 'APPROVED'))

                # Always use bill totals as source of truth (includes tax, charges, tip).
                subtotal = float(order.get('total_amount', 0))
                order['subtotal_amount'] = subtotal
                if order.get('payment_status') == 'PAID':
                    frozen = (
                        order.get('bill_frozen_total') or
                        order.get('bill_running_total')
                    )
                    if frozen is not None:
                        order['total_amount'] = float(frozen)
                        order['per_order_charge'] = round(float(frozen) - subtotal, 2)
                    else:
                        # Last resort: use stored total_amount as-is (no dynamic fee added)
                        order['total_amount'] = subtotal
                        order['per_order_charge'] = 0.0
                    order['digital_fee_enabled'] = order['per_order_charge'] > 0
                else:
                    running_total = order.get('bill_running_total')
                    if running_total is not None:
                        order['total_amount'] = float(running_total)
                        bill_charges = float(order.get('bill_charges') or 0)
                        if bill_charges <= 0:
                            bill_charges = max(0.0, float(running_total) - subtotal)
                        order['per_order_charge'] = bill_charges
                        order['digital_fee_enabled'] = bill_charges > 0
                    else:
                        order['total_amount'] = subtotal
                        order['per_order_charge'] = 0.0
                        order['digital_fee_enabled'] = False

            connection.commit()
            
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
                                SELECT o.*, COALESCE(CAST(t.table_number AS CHAR), 'Table Deleted') as table_number,
                                             COALESCE(t.status, 'DELETED') as table_status
                FROM table_orders o
                                LEFT JOIN tables t ON o.table_id = t.id
                WHERE o.table_id = %s AND o.session_id = %s
                  AND COALESCE(o.total_amount, 0) > 0
                  AND COALESCE(JSON_LENGTH(o.items), 0) > 0
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
    def get_digital_convenience_fee(hotel_id):
        """Get configured per-bill digital fee for a hotel with toggle support."""
        if not hotel_id:
            return 0.0
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                "SELECT per_order_charge, COALESCE(digital_fee_enabled, 1) as digital_fee_enabled FROM hotel_wallet WHERE hotel_id = %s",
                (hotel_id,)
            )
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            if not row or not bool(row.get('digital_fee_enabled')):
                return 0.0
            return round(float(row.get('per_order_charge') or 0.0), 2)
        except Exception:
            return 0.0

    @staticmethod
    def normalize_bill_totals(bill):
        """Normalize bill totals while honoring live digital fee toggle for open bills."""
        if not bill:
            return bill

        subtotal = round(float(bill.get('subtotal') or 0.0), 2)
        tax_amount = round(float(bill.get('tax_amount') or 0.0), 2)
        payment_status = str(bill.get('payment_status') or '').upper()
        bill_status = str(bill.get('bill_status') or '').upper()
        is_open_bill = bill_status == 'OPEN' and payment_status != 'PAID'

        discount_percent = round(float(bill.get('discount_percent') or 0.0), 2)
        discount_amount = round(float(bill.get('discount_amount') or 0.0), 2)

        if is_open_bill:
            # Always use latest DB toggle for open bills.
            charges = Bill.get_digital_convenience_fee(bill.get('hotel_id'))
            charges = round(float(charges or 0.0), 2)
            grand_total = round(subtotal + tax_amount + charges, 2)
            has_discount = discount_amount > 0 or discount_percent > 0
            final_total = round(max(grand_total - discount_amount, 0.0), 2) if has_discount else None
            total_amount = final_total if final_total is not None else grand_total

            bill['charges'] = charges
            bill['convenience_fee'] = charges
            bill['per_order_charge'] = charges
            bill['total_convenience_fee'] = charges
            bill['grand_total'] = grand_total
            bill['final_total'] = final_total
            bill['total_amount'] = total_amount
            bill['discount_percent'] = discount_percent
            bill['discount_amount'] = discount_amount
            return bill

        stored_total = bill.get('total_amount')
        stored_grand = bill.get('grand_total')
        grand_total = float(stored_grand) if stored_grand is not None else (float(stored_total) if stored_total is not None else 0.0)
        grand_total = round(grand_total, 2)

        stored_charges = bill.get('charges')
        if stored_charges is not None:
            charges = round(float(stored_charges), 2)
        else:
            derived_charges = grand_total - subtotal - tax_amount
            charges = round(derived_charges if derived_charges > 0 else 0.0, 2)

        raw_final_total = bill.get('final_total')
        final_total = round(float(raw_final_total), 2) if raw_final_total is not None else None

        bill['charges'] = charges
        bill['per_order_charge'] = charges
        bill['total_convenience_fee'] = charges
        bill['grand_total'] = grand_total
        bill['final_total'] = final_total
        bill['total_amount'] = final_total if final_total is not None else grand_total
        bill['discount_percent'] = discount_percent
        bill['discount_amount'] = discount_amount
        return bill

    @staticmethod
    def apply_discount(bill_id, discount_percent=None, discount_amount=None):
        """Apply bill-level discount and persist discount values plus final_total."""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT id, bill_status, payment_status, total_amount, grand_total
                FROM bills
                WHERE id = %s
                """,
                (bill_id,)
            )
            bill = cursor.fetchone()

            if not bill:
                cursor.close()
                connection.close()
                return {"success": False, "message": "Bill not found"}

            if bill.get('payment_status') == 'PAID' or bill.get('bill_status') == 'COMPLETED':
                cursor.close()
                connection.close()
                return {"success": False, "message": "Cannot apply discount to a paid bill"}

            base_total = bill.get('grand_total') if bill.get('grand_total') is not None else bill.get('total_amount')
            base_total = round(float(base_total or 0.0), 2)

            discount_percent_value = None if discount_percent is None else float(discount_percent)
            discount_amount_value = None if discount_amount is None else float(discount_amount)

            if discount_percent_value is not None:
                if discount_percent_value < 0 or discount_percent_value > 100:
                    cursor.close()
                    connection.close()
                    return {"success": False, "message": "Discount percentage must be between 0 and 100"}
                resolved_discount_percent = round(discount_percent_value, 2)
                resolved_discount_amount = round(base_total * resolved_discount_percent / 100.0, 2)
            else:
                if discount_amount_value is None:
                    discount_amount_value = 0.0
                if discount_amount_value < 0 or discount_amount_value > base_total:
                    cursor.close()
                    connection.close()
                    return {"success": False, "message": "Discount amount must be between 0 and bill total"}
                resolved_discount_amount = round(discount_amount_value, 2)
                resolved_discount_percent = None

            final_total = round(max(base_total - resolved_discount_amount, 0.0), 2)

            cursor.execute(
                """
                UPDATE bills
                SET discount_percent = %s,
                    discount_amount = %s,
                    final_total = %s
                WHERE id = %s
                """,
                (resolved_discount_percent, resolved_discount_amount, final_total, bill_id)
            )

            connection.commit()
            cursor.close()
            connection.close()

            return {
                "success": True,
                "bill_id": bill_id,
                "subtotal": base_total,
                "discount_percent": resolved_discount_percent,
                "discount_amount": resolved_discount_amount,
                "final_total": final_total,
            }
        except Exception as e:
            print(f"Error applying bill discount: {e}")
            return {"success": False, "message": "Server error"}
    
    @staticmethod
    def apply_frozen_values(bill):
        """If bill is PAID and has frozen final_* values, use them instead of recalculating.
        Returns the bill dict with correct totals."""
        if not bill:
            return bill
        is_paid = bill.get('payment_status') == 'PAID'
        has_frozen = bill.get('final_total') is not None
        if is_paid and has_frozen:
            bill['subtotal'] = float(bill.get('final_subtotal') or bill.get('subtotal', 0))
            bill['tax_amount'] = float(bill.get('final_tax') or bill.get('tax_amount', 0))
            final_fee = float(bill.get('final_digital_fee') or 0)
            final_total = float(bill['final_total'])
            bill['charges'] = final_fee
            bill['total_convenience_fee'] = final_fee
            bill['per_order_charge'] = final_fee
            bill['grand_total'] = final_total
            bill['total_amount'] = final_total
            bill['_frozen'] = True
        return Bill.normalize_bill_totals(bill)

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
            cgst_pct = 0.0
            sgst_pct = 0.0
            
            if dish_id:
                cursor.execute("""
                    SELECT mc.name as category_name, 
                           COALESCE(d.cgst, 0) as cgst_percentage, 
                           COALESCE(d.sgst, 0) as sgst_percentage 
                    FROM menu_dishes d
                    LEFT JOIN menu_categories mc ON d.category_id = mc.id
                    WHERE d.id = %s
                """, (dish_id,))
                cat_info = cursor.fetchone()
                if cat_info:
                    category_name = cat_info.get('category_name') or "Other"
                    cgst_pct = float(cat_info.get('cgst_percentage') if cat_info.get('cgst_percentage') is not None else 0.0)
                    sgst_pct = float(cat_info.get('sgst_percentage') if cat_info.get('sgst_percentage') is not None else 0.0)
            
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
            cgst_pct = 0.0
            sgst_pct = 0.0
            
            if dish_id:
                cursor.execute("""
                    SELECT mc.name as category_name, 
                           COALESCE(d.cgst, 0) as cgst_percentage, 
                           COALESCE(d.sgst, 0) as sgst_percentage 
                    FROM menu_dishes d
                    LEFT JOIN menu_categories mc ON d.category_id = mc.id
                    WHERE d.id = %s
                """, (dish_id,))
                cat_info = cursor.fetchone()
                if cat_info:
                    category_name = cat_info.get('category_name') or "Other"
                    cgst_pct = float(cat_info.get('cgst_percentage') if cat_info.get('cgst_percentage') is not None else 0.0)
                    sgst_pct = float(cat_info.get('sgst_percentage') if cat_info.get('sgst_percentage') is not None else 0.0)
            
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
            if bill:
                bill = Bill.normalize_bill_totals(bill)
            
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
                bill = Bill.normalize_bill_totals(bill)
            
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
            charges = Bill.get_digital_convenience_fee(bill.get('hotel_id'))
            grand_total = round(subtotal + tax_amount + charges, 2)
            
            # Calculate effective tax rate for display (backward compatibility)
            tax_rate = round((tax_amount / subtotal) * 100, 2) if subtotal > 0 else 5.0
            
            # Update bill with CGST/SGST, tax breakdown, and enriched items
            cursor.execute("""
                UPDATE bills 
                SET items = %s, subtotal = %s, tax_rate = %s, tax_amount = %s, 
                    cgst_amount = %s, sgst_amount = %s, tax_breakdown = %s,
                    charges = %s, convenience_fee = %s, grand_total = %s, total_amount = %s,
                    discount_percent = 0.00, discount_amount = 0.00, final_total = NULL
                WHERE id = %s
            """, (json.dumps(enriched_items), subtotal, tax_rate, tax_amount, 
                  cgst_amount, sgst_amount, json.dumps(tax_breakdown),
                  charges, charges, grand_total, grand_total, bill_id))

            # Keep order-to-bill linkage so all orders on the table point to the same running bill
            if new_order_id:
                cursor.execute("UPDATE table_orders SET bill_id = %s WHERE id = %s", (bill_id, new_order_id))
            
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
                'charges': charges,
                'grand_total': grand_total,
                'total_amount': grand_total,
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
            charges = Bill.get_digital_convenience_fee(hotel_id)
            grand_total = round(subtotal + tax_amount + charges, 2)
            
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
                                 table_number, items, subtotal, tax_rate, tax_amount, cgst_amount, sgst_amount, tax_breakdown,
                                 charges, convenience_fee, grand_total, total_amount, bill_status, waiter_id, bill_date)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'OPEN', %s, NOW())
            """, (bill_number, order_id, hotel_id, table_id, session_id, guest_name, hotel_name, hotel_address,
                                    table_number, items_json, subtotal, tax_rate, tax_amount, cgst_amount, sgst_amount, tax_breakdown_json,
                                    charges, charges, grand_total, grand_total, waiter_id))
            
            bill_id = cursor.lastrowid

            # Persist linkage back to order so future lookups reuse this bill
            if order_id:
                cursor.execute("UPDATE table_orders SET bill_id = %s WHERE id = %s", (bill_id, order_id))
            
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
                'charges': charges,
                'grand_total': grand_total,
                'total_amount': grand_total
            }
        except Exception as e:
            print(f"Error creating bill: {e}")
            return None
    
    @staticmethod
    def get_bill_by_order(order_id):
        """Get bill for a specific order.

        Resolution priority:
        1) Direct mapping via bills.order_id
        2) Linked mapping via table_orders.bill_id
        3) Current OPEN bill for same table+session
        4) Latest bill for same table+session
        """
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            # 1) Direct mapping
            cursor.execute("""
                SELECT b.*, h.hotel_name, h.logo as hotel_logo
                FROM bills b
                LEFT JOIN hotels h ON b.hotel_id = h.id
                WHERE b.order_id = %s
                ORDER BY b.created_at DESC
                LIMIT 1
            """, (order_id,))

            bill = cursor.fetchone()

            # Fetch order context for fallback lookups
            cursor.execute("SELECT table_id, session_id, bill_id FROM table_orders WHERE id = %s", (order_id,))
            order_row = cursor.fetchone()

            # 2) Linked mapping via table_orders.bill_id
            if not bill and order_row and order_row.get('bill_id'):
                cursor.execute("""
                    SELECT b.*, h.hotel_name, h.logo as hotel_logo
                    FROM bills b
                    LEFT JOIN hotels h ON b.hotel_id = h.id
                    WHERE b.id = %s
                    LIMIT 1
                """, (order_row['bill_id'],))
                bill = cursor.fetchone()

            # 3) Current OPEN bill for same table+session
            if not bill and order_row and order_row.get('table_id') and order_row.get('session_id'):
                cursor.execute("""
                    SELECT b.*, h.hotel_name, h.logo as hotel_logo
                    FROM bills b
                    LEFT JOIN hotels h ON b.hotel_id = h.id
                    WHERE b.table_id = %s AND b.session_id = %s AND b.bill_status = 'OPEN'
                    ORDER BY b.created_at DESC
                    LIMIT 1
                """, (order_row['table_id'], order_row['session_id']))
                bill = cursor.fetchone()

            # 4) Latest bill for same table+session (covers completed bills)
            if not bill and order_row and order_row.get('table_id') and order_row.get('session_id'):
                cursor.execute("""
                    SELECT b.*, h.hotel_name, h.logo as hotel_logo
                    FROM bills b
                    LEFT JOIN hotels h ON b.hotel_id = h.id
                    WHERE b.table_id = %s AND b.session_id = %s
                    ORDER BY b.created_at DESC
                    LIMIT 1
                """, (order_row['table_id'], order_row['session_id']))
                bill = cursor.fetchone()
            
            if bill:
                import json
                # Always parse items into a list
                raw_items = bill.get('items')
                if raw_items:
                    try:
                        items = json.loads(raw_items) if isinstance(raw_items, str) else raw_items
                    except Exception:
                        items = []
                else:
                    items = []
                if items:
                    items = Bill.enrich_items_with_tax(items, cursor)
                bill['items'] = items

                bill = Bill.normalize_bill_totals(bill)
            
            # Use frozen values if bill is already PAID
            bill = Bill.apply_frozen_values(bill)

            # Backfill order linkage if missing
            if bill and order_row and not order_row.get('bill_id'):
                try:
                    cursor.execute("UPDATE table_orders SET bill_id = %s WHERE id = %s", (bill['id'], order_id))
                    connection.commit()
                except Exception:
                    pass

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
                Bill.normalize_bill_totals(bill)
                Bill.normalize_bill_totals(bill)
            
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
                SELECT payment_status, payment_method, bill_number, cgst_amount, sgst_amount,
                       tax_breakdown, charges, grand_total, total_amount, final_total,
                       discount_percent, discount_amount, utr_id
                FROM bills 
                WHERE table_id = %s AND session_id = %s
                ORDER BY created_at DESC LIMIT 1
            """, (table_id, session_id))
            bill_info = cursor.fetchone()
            
            if bill_info:
                payment_status = bill_info.get('payment_status', 'PENDING')
                payment_method = bill_info.get('payment_method', '')
                utr_id = bill_info.get('utr_id', '')
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
                utr_id = ''
                bill_number = ''
            
            # Enrich items with per-item tax info before returning
            enriched_items = Bill.enrich_items_with_tax(all_items, cursor)
            
            # Use persisted bill totals when available
            total_convenience_fee = 0.0
            discount_percent = 0.0
            discount_amount = 0.0
            final_total = None
            if bill_info:
                discount_percent = float(bill_info.get('discount_percent') or 0.0)
                discount_amount = float(bill_info.get('discount_amount') or 0.0)
                payment_status = str(bill_info.get('payment_status') or '').upper()

                if payment_status == 'PAID':
                    persisted_total = (
                        bill_info.get('final_total')
                        if bill_info.get('final_total') is not None
                        else (bill_info.get('grand_total') if bill_info.get('grand_total') is not None else bill_info.get('total_amount'))
                    )
                    if persisted_total is not None:
                        total_amount = float(persisted_total)
                    final_total = bill_info.get('final_total')
                    persisted_charges = bill_info.get('charges')
                    if persisted_charges is not None:
                        total_convenience_fee = float(persisted_charges)
                    else:
                        total_convenience_fee = max(0.0, total_amount - subtotal - tax_amount)
                else:
                    live_fee = Bill.get_digital_convenience_fee(first_order.get('hotel_id'))
                    total_convenience_fee = round(float(live_fee or 0.0), 2)
                    base_total = round(subtotal + tax_amount + total_convenience_fee, 2)
                    has_discount = discount_amount > 0 or discount_percent > 0
                    final_total = round(max(base_total - discount_amount, 0.0), 2) if has_discount else None
                    total_amount = final_total if final_total is not None else base_total
            per_order_charge = total_convenience_fee

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
                'per_order_charge': per_order_charge,
                'total_convenience_fee': total_convenience_fee,
                'charges': total_convenience_fee,
                'grand_total': total_amount,
                'total_amount': total_amount,
                'discount_percent': discount_percent,
                'discount_amount': discount_amount,
                'final_total': final_total,
                'payment_status': payment_status,
                'payment_method': payment_method,
                'utr_id': utr_id,
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
    def process_payment_atomic(table_id, bill_id, payment_method='CASH', tip_amount=0.00, utr_id=None):
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
                SELECT id, bill_status, table_id, session_id, guest_name, subtotal, tax_amount,
                       total_amount, grand_total, final_total, charges, waiter_id, hotel_id, discount_amount
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
            
            # Calculate new total with tip from latest open-bill totals (live fee toggle).
            subtotal = float(bill.get('subtotal', 0))
            tax_amount = float(bill.get('tax_amount', 0))
            tip = float(tip_amount) if tip_amount else 0.00
            
            # Validate tip (must be non-negative)
            if tip < 0:
                tip = 0.00
            
            live_fee = Bill.get_digital_convenience_fee(bill.get('hotel_id'))
            base_digital_fee = round(float(live_fee or 0.0), 2)
            discount_amount = round(float(bill.get('discount_amount') or 0), 2)
            pre_discount_total = round(subtotal + tax_amount + base_digital_fee, 2)
            base_payable = round(max(pre_discount_total - discount_amount, 0.0), 2)
            new_total = round(base_payable + tip, 2)
            
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
                                INSERT INTO waiter_tips (waiter_id, bill_id, tip_amount, hotel_id, created_at)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (bill_waiter_id, bill_id, tip, bill.get('hotel_id'), paid_at))
                            
                            print(f"[PAYMENT ATOMIC] Tip recorded successfully: waiter_id={bill_waiter_id}, amount=₹{tip}")
                        except Exception as tip_error:
                            print(f"[PAYMENT ATOMIC WARNING] Could not record tip in waiter_tips table: {tip_error}")
                            print(f"[PAYMENT ATOMIC WARNING] This might indicate the waiter_tips table doesn't exist yet")
                            # Try to create the table if it doesn't exist
                            try:
                                cursor.execute("""
                                    CREATE TABLE IF NOT EXISTS waiter_tips (
                                        id INT AUTO_INCREMENT PRIMARY KEY,
                                        waiter_id INT NOT NULL,
                                        bill_id INT NOT NULL,
                                        tip_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                        INDEX idx_waiter_id (waiter_id),
                                        INDEX idx_bill_id (bill_id),
                                        INDEX idx_created_at (created_at),
                                        UNIQUE KEY unique_waiter_bill_tip (waiter_id, bill_id)
                                    )
                                """)
                                # Try inserting the tip again
                                cursor.execute("""
                                    INSERT INTO waiter_tips (waiter_id, bill_id, tip_amount, hotel_id, created_at)
                                    VALUES (%s, %s, %s, %s, %s)
                                """, (bill_waiter_id, bill_id, tip, bill.get('hotel_id'), paid_at))
                                print(f"[PAYMENT ATOMIC] Created waiter_tips table and recorded tip: waiter_id={bill_waiter_id}, amount=₹{tip}")
                            except Exception as create_error:
                                print(f"[PAYMENT ATOMIC ERROR] Could not create waiter_tips table or insert tip: {create_error}")
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
                                        INSERT INTO waiter_tips (waiter_id, bill_id, tip_amount, hotel_id, created_at)
                                        VALUES (%s, %s, %s, %s, %s)
                                    """, (waiter_id, bill_id, tip_per_waiter, bill.get('hotel_id'), paid_at))
                                    
                                    print(f"[PAYMENT ATOMIC] Tip recorded: waiter_id={waiter_id}, amount=₹{tip_per_waiter}")
                            except Exception as tip_error:
                                print(f"[PAYMENT ATOMIC WARNING] Could not record tips in waiter_tips table: {tip_error}")
                        else:
                            print(f"[PAYMENT ATOMIC WARNING] No waiter_id in bill and no waiters assigned to table {table_id}, tip not distributed")
                except Exception as e:
                    # Gracefully handle any tip distribution errors - don't fail the payment
                    print(f"[PAYMENT ATOMIC WARNING] Error during tip distribution: {e}")
                    print(f"[PAYMENT ATOMIC WARNING] Payment will continue, but tips not distributed")
            
            # Mark bill as PAID and COMPLETED with tip — freeze persisted values
            digital_fee_at_payment = base_digital_fee
            final_subtotal = round(subtotal, 2)
            final_tax = round(tax_amount, 2)
            final_digital_fee = round(digital_fee_at_payment, 2)
            final_total = round(max(final_subtotal + final_tax + final_digital_fee - discount_amount + tip, 0.0), 2)
            new_total = final_total

            cursor.execute("""
                UPDATE bills 
                SET payment_status = 'PAID', 
                    payment_method = %s, 
                    utr_id = %s,
                    paid_at = %s, 
                    bill_status = 'COMPLETED',
                    tip_amount = %s,
                    charges = %s,
                    convenience_fee = %s,
                    grand_total = %s,
                    total_amount = %s,
                    final_subtotal = %s,
                    final_tax = %s,
                    final_digital_fee = %s,
                    final_total = %s
                WHERE id = %s
            """, (payment_method, utr_id, paid_at, tip, final_digital_fee, final_digital_fee, final_total, new_total,
                  final_subtotal, final_tax, final_digital_fee, final_total,
                  bill_id))
            
            print(f"[PAYMENT ATOMIC] Bill updated, rows affected: {cursor.rowcount}")
            
            # Update associated orders to PAID — also freeze final_total on each order
            bill_session_id = bill.get('session_id')
            bill_guest_name = bill.get('guest_name')
            # final_total per order = order subtotal + digital fee (tip stays on bill only)
            order_frozen_total_sql = "ROUND(total_amount + %s, 2)"
            
            if bill_session_id:
                cursor.execute(f"""
                    UPDATE table_orders 
                    SET payment_status = 'PAID',
                        final_total = {order_frozen_total_sql}
                    WHERE table_id = %s AND session_id = %s
                """, (final_digital_fee, table_id, bill_session_id))
                print(f"[PAYMENT ATOMIC] Orders updated by session_id, rows affected: {cursor.rowcount}")
            elif bill_guest_name:
                cursor.execute(f"""
                    UPDATE table_orders 
                    SET payment_status = 'PAID',
                        final_total = {order_frozen_total_sql}
                    WHERE table_id = %s AND guest_name = %s
                """, (final_digital_fee, table_id, bill_guest_name))
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
            
            # Get bill info first (including values to freeze)
            cursor.execute("""
                  SELECT b.table_id, b.guest_name, b.subtotal, b.tax_amount, b.hotel_id,
                      b.total_amount, b.grand_total, b.charges,
                       b.final_subtotal, b.final_total, b.discount_amount
                FROM bills b WHERE b.id = %s
            """, (bill_id,))
            bill = cursor.fetchone()
            
            if not bill:
                cursor.close()
                connection.close()
                print(f"[COMPLETE_BILL] Bill not found: {bill_id}")
                return False
            
            table_id = bill['table_id']
            
            final_subtotal = round(float(bill.get('subtotal', 0)), 2)
            final_tax = round(float(bill.get('tax_amount', 0)), 2)
            is_paid = str(bill.get('payment_status') or '').upper() == 'PAID'
            is_completed = str(bill.get('bill_status') or '').upper() == 'COMPLETED'
            if is_paid or is_completed:
                final_digital_fee = round(float(bill.get('charges') or 0), 2)
            else:
                final_digital_fee = round(float(Bill.get_digital_convenience_fee(bill.get('hotel_id')) or 0), 2)
            discount_amount = round(float(bill.get('discount_amount') or 0), 2)
            derived_total = final_subtotal + final_tax + final_digital_fee - discount_amount
            final_total = round(float(derived_total), 2)

            # Mark bill as COMPLETED and PAID with timestamp + frozen values
            import datetime
            paid_at = datetime.datetime.now()
            
            cursor.execute("""
                UPDATE bills 
                SET bill_status = 'COMPLETED', 
                    payment_status = 'PAID',
                    paid_at = %s,
                    charges = %s,
                    convenience_fee = %s,
                    grand_total = %s,
                    final_subtotal = %s,
                    final_tax = %s,
                    final_digital_fee = %s,
                    final_total = %s,
                    total_amount = %s
                WHERE id = %s
            """, (paid_at, final_digital_fee, final_digital_fee, final_total, final_subtotal, final_tax, final_digital_fee, final_total, final_total, bill_id))
            
            print(f"[COMPLETE_BILL] Updated bill {bill_id} to COMPLETED/PAID, frozen total=₹{final_total}")
            
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
                if items:
                    items = Bill.enrich_items_with_tax(items, cursor)
                bill['items'] = items

                bill = Bill.normalize_bill_totals(bill)
            
            # Use frozen values if bill is already PAID
            bill = Bill.apply_frozen_values(bill)
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
                if items:
                    items = Bill.enrich_items_with_tax(items, cursor)
                    bill['items'] = items
                else:
                    bill['items'] = items

                bill = Bill.normalize_bill_totals(bill)
            
            # Use frozen values if bill is already PAID
            bill = Bill.apply_frozen_values(bill)
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
                Bill.normalize_bill_totals(bill)
            
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
                Bill.normalize_bill_totals(bill)
            
            cursor.close()
            connection.close()
            return bills
        except Exception as e:
            print(f"Error getting all bills: {e}")
            return []

    @staticmethod
    def get_filtered_bills_for_manager(hotel_id, date_from=None, date_to=None, payment_method=None,
                                       payment_status=None, table_number=None):
        """Get filtered bills for manager dashboard bill management table."""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            query = """
                SELECT
                    b.id,
                    b.bill_number,
                    b.order_id,
                    b.table_number,
                    b.guest_name,
                    ROUND(COALESCE(b.grand_total, b.total_amount, 0), 2) AS total_amount,
                    ROUND(COALESCE(b.cgst_amount, 0), 2) AS cgst_amount,
                    ROUND(COALESCE(b.sgst_amount, 0), 2) AS sgst_amount,
                    ROUND(
                        COALESCE(
                            b.convenience_fee,
                            b.charges,
                            (COALESCE(b.grand_total, b.total_amount, 0) - COALESCE(b.subtotal, 0) - COALESCE(b.tax_amount, 0)),
                            0
                        ),
                        2
                    ) AS convenience_fee,
                    UPPER(COALESCE(b.payment_method, '')) AS payment_method,
                    UPPER(COALESCE(b.payment_status, 'PENDING')) AS payment_status,
                    COALESCE(b.bill_date, b.created_at) AS bill_date,
                    b.created_at
                FROM bills b
                WHERE b.hotel_id = %s
            """

            params = [hotel_id]

            if date_from:
                query += " AND DATE(COALESCE(b.bill_date, b.created_at)) >= %s"
                params.append(date_from)

            if date_to:
                query += " AND DATE(COALESCE(b.bill_date, b.created_at)) <= %s"
                params.append(date_to)

            if payment_method:
                query += " AND UPPER(COALESCE(b.payment_method, '')) = %s"
                params.append(str(payment_method).upper())

            if payment_status:
                query += " AND UPPER(COALESCE(b.payment_status, 'PENDING')) = %s"
                params.append(str(payment_status).upper())

            if table_number:
                query += " AND b.table_number = %s"
                params.append(str(table_number).strip())

            query += " ORDER BY COALESCE(b.bill_date, b.created_at) DESC, b.id DESC"

            cursor.execute(query, tuple(params))
            bills = cursor.fetchall()

            cursor.close()
            connection.close()
            return bills
        except Exception as e:
            print(f"Error getting filtered manager bills: {e}")
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
            
            print(f"[TIP_SUMMARY] Getting waiter tips for hotel_id={hotel_id}, period={period}")
            
            # Check if waiter_tips table exists
            cursor.execute("SHOW TABLES LIKE 'waiter_tips'")
            waiter_tips_exists = cursor.fetchone() is not None
            
            print(f"[TIP_SUMMARY] waiter_tips table exists: {waiter_tips_exists}")
            
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
                query = f"""
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
                """
                print(f"[TIP_SUMMARY] Using waiter_tips table query: {query}")
                cursor.execute(query, (hotel_id,))
            else:
                # Fallback to bills table (old method)
                print("[TIP_SUMMARY] waiter_tips table not found, using bills table (run setup_tip_distribution.py)")
                query = f"""
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
                """
                print(f"[TIP_SUMMARY] Using bills table query: {query}")
                cursor.execute(query, (hotel_id,))
            
            waiters = cursor.fetchall()
            
            print(f"[TIP_SUMMARY] Found {len(waiters)} waiters with tips")
            for waiter in waiters:
                print(f"[TIP_SUMMARY] Waiter: {waiter['waiter_name']} (ID: {waiter['waiter_id']}) - Today: ₹{waiter['today_tip']}, Total: ₹{waiter['total_tip']}")
            
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


class BillRequest:
    @staticmethod
    def create_table():
        """Create bill_requests table if not exists"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS bill_requests (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    table_id INT NOT NULL,
                    session_id VARCHAR(100),
                    guest_name VARCHAR(255),
                    hotel_id INT,
                    status ENUM('PENDING', 'APPROVED', 'REJECTED') DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            connection.commit()
            cursor.close()
            connection.close()
            return True
        except Exception as e:
            print(f"Error creating bill_requests table: {e}")
            return False

    @staticmethod
    def create_request(table_id, session_id, guest_name, hotel_id):
        """Insert a new PENDING bill request.

        Returns:
            {'id': <request_id>, 'created': True} when newly created
            {'id': <request_id>, 'created': False} when existing pending request found
            None on failure
        """
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            # Check for existing PENDING request
            cursor.execute(
                "SELECT id FROM bill_requests WHERE table_id = %s AND session_id = %s AND status = 'PENDING'",
                (table_id, session_id)
            )
            existing = cursor.fetchone()
            if existing:
                cursor.close()
                connection.close()
                return {'id': existing['id'], 'created': False}
            cursor.execute(
                "INSERT INTO bill_requests (table_id, session_id, guest_name, hotel_id, status) VALUES (%s, %s, %s, %s, 'PENDING')",
                (table_id, session_id, guest_name, hotel_id)
            )
            request_id = cursor.lastrowid
            connection.commit()
            cursor.close()
            connection.close()
            return {'id': request_id, 'created': True}
        except Exception as e:
            print(f"Error creating bill request: {e}")
            return None

    @staticmethod
    def get_pending_requests(hotel_id):
        """Return all PENDING requests for a hotel, joined with tables for table_number."""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute("""
                SELECT br.*, t.table_number
                FROM bill_requests br
                LEFT JOIN tables t ON br.table_id = t.id
                WHERE br.hotel_id = %s AND br.status = 'PENDING'
                ORDER BY br.created_at ASC
            """, (hotel_id,))
            rows = cursor.fetchall()
            cursor.close()
            connection.close()
            return rows
        except Exception as e:
            print(f"Error getting pending bill requests: {e}")
            return []

    @staticmethod
    def update_status(request_id, status):
        """Update request status to APPROVED or REJECTED."""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            cursor.execute(
                "UPDATE bill_requests SET status = %s WHERE id = %s",
                (status, request_id)
            )
            connection.commit()
            cursor.close()
            connection.close()
            return True
        except Exception as e:
            print(f"Error updating bill request status: {e}")
            return False

    @staticmethod
    def get_request_status(table_id, session_id):
        """Return the latest request status for a table+session, or None if no request."""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            cursor.execute(
                "SELECT status FROM bill_requests WHERE table_id = %s AND session_id = %s ORDER BY created_at DESC LIMIT 1",
                (table_id, session_id)
            )
            row = cursor.fetchone()
            cursor.close()
            connection.close()
            return row['status'] if row else None
        except Exception as e:
            print(f"Error getting bill request status: {e}")
            return None

    @staticmethod
    def reset_for_new_order(table_id, session_id):
        """Reset bill request state when new items are added in the same open session.

        Reset is skipped when the session is already paid/completed.
        """
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT bill_status, payment_status
                FROM bills
                WHERE table_id = %s AND session_id = %s
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (table_id, session_id)
            )
            latest_bill = cursor.fetchone()

            # Do not reset if bill is already finalized.
            if latest_bill and (
                latest_bill.get('bill_status') == 'COMPLETED'
                or latest_bill.get('payment_status') == 'PAID'
            ):
                cursor.close()
                connection.close()
                return False

            cursor.execute(
                """
                UPDATE table_orders
                SET bill_requested = 0
                WHERE table_id = %s AND session_id = %s
                  AND (payment_status IS NULL OR payment_status != 'PAID')
                """,
                (table_id, session_id)
            )

            # Clear prior requests so the latest state becomes fresh for this new order wave.
            cursor.execute(
                "DELETE FROM bill_requests WHERE table_id = %s AND session_id = %s",
                (table_id, session_id)
            )

            connection.commit()
            cursor.close()
            connection.close()
            return True
        except Exception as e:
            print(f"Error resetting bill request state for new order: {e}")
            return False
