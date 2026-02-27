"""
Create order_items table for item-level tracking with kitchen section assignment
"""
from database.db import get_db_connection

def create_order_items_table():
    """Create order_items table for granular item tracking"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        print("[ORDER_ITEMS] Creating order_items table...")
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS order_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                order_id INT NOT NULL,
                dish_id INT NOT NULL,
                dish_name VARCHAR(255) NOT NULL,
                category_id INT,
                kitchen_section_id INT,
                quantity INT NOT NULL DEFAULT 1,
                price DECIMAL(10,2) NOT NULL,
                item_status ENUM('ACTIVE', 'PREPARING', 'READY', 'COMPLETED') DEFAULT 'ACTIVE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES table_orders(id) ON DELETE CASCADE,
                FOREIGN KEY (dish_id) REFERENCES menu_dishes(id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES menu_categories(id) ON DELETE SET NULL,
                FOREIGN KEY (kitchen_section_id) REFERENCES kitchen_sections(id) ON DELETE SET NULL,
                INDEX idx_kitchen_section (kitchen_section_id),
                INDEX idx_item_status (item_status),
                INDEX idx_order_id (order_id)
            )
        """)
        
        connection.commit()
        print("[ORDER_ITEMS] ✓ Table created successfully")
        
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        print(f"[ORDER_ITEMS] Error: {e}")
        return False

def migrate_existing_orders():
    """Migrate existing orders to order_items table"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        print("[ORDER_ITEMS] Migrating existing orders...")
        
        # Get all existing orders
        cursor.execute("""
            SELECT id, items FROM table_orders
            WHERE id NOT IN (SELECT DISTINCT order_id FROM order_items)
        """)
        
        orders = cursor.fetchall()
        print(f"[ORDER_ITEMS] Found {len(orders)} orders to migrate")
        
        import json
        migrated_count = 0
        
        for order in orders:
            order_id = order['id']
            items = json.loads(order['items']) if isinstance(order['items'], str) else order['items']
            
            for item in items:
                dish_id = item.get('id')
                dish_name = item.get('name', 'Unknown')
                quantity = item.get('quantity', 1)
                price = item.get('price', 0)
                
                if not dish_id:
                    continue
                
                # Get category_id and kitchen_section_id for this dish
                cursor.execute("""
                    SELECT d.category_id, kcm.kitchen_section_id
                    FROM menu_dishes d
                    LEFT JOIN kitchen_category_mapping kcm ON d.category_id = kcm.category_id
                    WHERE d.id = %s
                    LIMIT 1
                """, (dish_id,))
                
                dish_info = cursor.fetchone()
                category_id = dish_info['category_id'] if dish_info else None
                kitchen_section_id = dish_info['kitchen_section_id'] if dish_info else None
                
                # Insert into order_items
                cursor.execute("""
                    INSERT INTO order_items 
                    (order_id, dish_id, dish_name, category_id, kitchen_section_id, quantity, price, item_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'ACTIVE')
                """, (order_id, dish_id, dish_name, category_id, kitchen_section_id, quantity, price))
                
                migrated_count += 1
        
        connection.commit()
        print(f"[ORDER_ITEMS] ✓ Migrated {migrated_count} items")
        
        cursor.close()
        connection.close()
        return True
        
    except Exception as e:
        print(f"[ORDER_ITEMS] Migration error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Order Items Table Creation & Migration")
    print("=" * 60)
    
    if create_order_items_table():
        migrate_existing_orders()
    
    print("=" * 60)
    print("Complete!")
