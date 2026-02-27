"""
Debug script to diagnose kitchen order routing issues
"""
from database.db import get_db_connection
import json

def debug_kitchen_orders():
    """Comprehensive debug of kitchen order routing"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        
        print("=" * 80)
        print("KITCHEN ORDER ROUTING DEBUG")
        print("=" * 80)
        
        # 1. Check menu dishes and their categories
        print("\n1️⃣ MENU DISHES & CATEGORIES")
        print("-" * 80)
        cursor.execute("""
            SELECT d.id, d.name, d.category_id, c.name as category_name
            FROM menu_dishes d
            LEFT JOIN menu_categories c ON d.category_id = c.id
            ORDER BY c.name, d.name
            LIMIT 20
        """)
        dishes = cursor.fetchall()
        
        if dishes:
            for dish in dishes:
                cat = dish['category_name'] or '⚠ NO CATEGORY'
                print(f"  Dish: {dish['name']} (ID: {dish['id']})")
                print(f"    Category: {cat} (ID: {dish['category_id']})")
        else:
            print("  ⚠ No dishes found!")
        
        # 2. Check kitchen sections
        print("\n2️⃣ KITCHEN SECTIONS")
        print("-" * 80)
        cursor.execute("SELECT id, section_name FROM kitchen_sections")
        sections = cursor.fetchall()
        
        if sections:
            for section in sections:
                print(f"  {section['section_name']} (ID: {section['id']})")
        else:
            print("  ⚠ No kitchen sections found!")
        
        # 3. Check category → kitchen mapping
        print("\n3️⃣ CATEGORY → KITCHEN MAPPING")
        print("-" * 80)
        cursor.execute("""
            SELECT 
                ks.id as kitchen_id,
                ks.section_name,
                c.id as category_id,
                c.name as category_name
            FROM kitchen_sections ks
            LEFT JOIN kitchen_category_mapping kcm ON ks.id = kcm.kitchen_section_id
            LEFT JOIN menu_categories c ON kcm.category_id = c.id
            ORDER BY ks.section_name, c.name
        """)
        mappings = cursor.fetchall()
        
        if mappings:
            current_kitchen = None
            for mapping in mappings:
                if mapping['section_name'] != current_kitchen:
                    current_kitchen = mapping['section_name']
                    print(f"\n  {current_kitchen}:")
                
                if mapping['category_name']:
                    print(f"    ✓ {mapping['category_name']} (ID: {mapping['category_id']})")
                else:
                    print(f"    ⚠ No categories assigned")
        else:
            print("  ⚠ No mappings found!")
        
        # 4. Check recent orders
        print("\n4️⃣ RECENT ORDERS (table_orders)")
        print("-" * 80)
        cursor.execute("""
            SELECT 
                o.id,
                o.table_id,
                o.order_status,
                o.created_at,
                t.table_number,
                o.items
            FROM table_orders o
            JOIN tables t ON o.table_id = t.id
            ORDER BY o.created_at DESC
            LIMIT 5
        """)
        orders = cursor.fetchall()
        
        if orders:
            for order in orders:
                print(f"\n  Order ID: {order['id']} | Table: {order['table_number']} | Status: {order['order_status']}")
                print(f"  Created: {order['created_at']}")
                
                # Parse items
                items = json.loads(order['items']) if isinstance(order['items'], str) else order['items']
                print(f"  Items ({len(items)}):")
                for item in items:
                    print(f"    - {item.get('name')} (Dish ID: {item.get('id')}) x{item.get('quantity', 1)}")
        else:
            print("  ⚠ No orders found!")
        
        # 5. Check order_items table
        print("\n5️⃣ ORDER ITEMS (order_items table)")
        print("-" * 80)
        cursor.execute("""
            SELECT 
                oi.id,
                oi.order_id,
                oi.dish_name,
                oi.category_id,
                oi.kitchen_section_id,
                oi.item_status,
                c.name as category_name,
                ks.section_name as kitchen_name
            FROM order_items oi
            LEFT JOIN menu_categories c ON oi.category_id = c.id
            LEFT JOIN kitchen_sections ks ON oi.kitchen_section_id = ks.id
            ORDER BY oi.created_at DESC
            LIMIT 10
        """)
        order_items = cursor.fetchall()
        
        if order_items:
            for item in order_items:
                kitchen = item['kitchen_name'] or '⚠ UNASSIGNED'
                category = item['category_name'] or '⚠ NO CATEGORY'
                print(f"\n  Item ID: {item['id']} | Order: {item['order_id']}")
                print(f"  Dish: {item['dish_name']}")
                print(f"  Category: {category} (ID: {item['category_id']})")
                print(f"  Kitchen: {kitchen} (ID: {item['kitchen_section_id']})")
                print(f"  Status: {item['item_status']}")
        else:
            print("  ⚠ No order items found!")
        
        # 6. Check what each kitchen should see
        print("\n6️⃣ WHAT EACH KITCHEN SHOULD SEE")
        print("-" * 80)
        
        for section in sections:
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM order_items oi
                WHERE oi.kitchen_section_id = %s
                  AND oi.item_status != 'COMPLETED'
            """, (section['id'],))
            
            result = cursor.fetchone()
            count = result['count'] if result else 0
            
            print(f"\n  {section['section_name']} (ID: {section['id']}): {count} active items")
            
            if count > 0:
                cursor.execute("""
                    SELECT 
                        oi.dish_name,
                        oi.item_status,
                        c.name as category_name,
                        t.table_number
                    FROM order_items oi
                    JOIN menu_categories c ON oi.category_id = c.id
                    JOIN table_orders o ON oi.order_id = o.id
                    JOIN tables t ON o.table_id = t.id
                    WHERE oi.kitchen_section_id = %s
                      AND oi.item_status != 'COMPLETED'
                """, (section['id'],))
                
                items = cursor.fetchall()
                for item in items:
                    print(f"    ✓ {item['dish_name']} ({item['category_name']}) - Table {item['table_number']} - {item['item_status']}")
        
        # 7. Identify issues
        print("\n7️⃣ ISSUE DETECTION")
        print("-" * 80)
        
        issues = []
        
        # Check for dishes without categories
        cursor.execute("SELECT COUNT(*) as count FROM menu_dishes WHERE category_id IS NULL")
        result = cursor.fetchone()
        if result['count'] > 0:
            issues.append(f"⚠ {result['count']} dishes have no category assigned")
        
        # Check for categories without kitchen mapping
        cursor.execute("""
            SELECT c.id, c.name
            FROM menu_categories c
            LEFT JOIN kitchen_category_mapping kcm ON c.id = kcm.category_id
            WHERE kcm.category_id IS NULL
        """)
        unmapped_cats = cursor.fetchall()
        if unmapped_cats:
            issues.append(f"⚠ {len(unmapped_cats)} categories not assigned to any kitchen:")
            for cat in unmapped_cats:
                issues.append(f"    - {cat['name']} (ID: {cat['id']})")
        
        # Check for order items without kitchen assignment
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM order_items
            WHERE kitchen_section_id IS NULL
              AND item_status != 'COMPLETED'
        """)
        result = cursor.fetchone()
        if result['count'] > 0:
            issues.append(f"⚠ {result['count']} active order items have no kitchen assignment")
        
        if issues:
            print("\n  ISSUES FOUND:")
            for issue in issues:
                print(f"  {issue}")
        else:
            print("\n  ✓ No issues detected!")
        
        # 8. Recommendations
        print("\n8️⃣ RECOMMENDATIONS")
        print("-" * 80)
        
        if not sections:
            print("  1. Create kitchen sections in Manager Dashboard → Kitchen Mapping")
        
        if unmapped_cats:
            print("  2. Assign all categories to kitchen sections")
        
        if order_items:
            print("  3. Kitchen routing is active - check kitchen dashboard URLs:")
            for section in sections:
                print(f"     http://127.0.0.1:5000/orders/kitchen/{section['id']}")
        else:
            print("  3. Place a test order to verify routing")
        
        cursor.close()
        connection.close()
        
        print("\n" + "=" * 80)
        print("DEBUG COMPLETE")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_kitchen_orders()
