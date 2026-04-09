"""
Live Table Order Tracking APIs
Provides real-time order management for Manager Dashboard

NOTE: This file contains ONLY NEW unique endpoints for live orders.
Existing endpoints like /api/update-order-status are in table_routes.py
"""

from flask import request, jsonify, session
from database.db import get_db_connection
from . import orders_bp
import json
from datetime import datetime


@orders_bp.route('/api/live-orders', methods=['GET'])
def get_live_orders():
    """
    Get all pending orders organized by table for Manager Dashboard
    Returns orders grouped by table with pending status
    """
    try:
        hotel_id = session.get('hotel_id')
        if not hotel_id and request.args.get('hotel_id'):
            hotel_id = request.args.get('hotel_id')
        
        if not hotel_id:
            return jsonify({"success": False, "message": "Not authenticated"}), 401
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Fetch all table numbers for this hotel
        cursor.execute("""
            SELECT id, table_number, status
            FROM tables
            WHERE hotel_id = %s
            ORDER BY CAST(table_number AS UNSIGNED)
        """, (hotel_id,))
        tables = cursor.fetchall()
        
        # Build response grouped by table
        live_orders = []
        
        for table in tables:
            table_id = table['id']
            table_number = table['table_number']
            
            # Get all pending orders for this table
            cursor.execute("""
                SELECT 
                    id,
                    table_id,
                    session_id,
                    guest_name,
                    items,
                    total_amount,
                    order_status,
                    created_at
                FROM table_orders
                WHERE table_id = %s 
                  AND hotel_id = %s
                  AND order_status IN ('ACTIVE', 'PREPARING')
                                    AND COALESCE(total_amount, 0) > 0
                                    AND COALESCE(JSON_LENGTH(items), 0) > 0
                ORDER BY created_at DESC
            """, (table_id, hotel_id))
            
            orders = cursor.fetchall()
            
            if orders:
                # Parse items JSON
                for order in orders:
                    if isinstance(order['items'], str):
                        order['items'] = json.loads(order['items'])
                
                live_orders.append({
                    'table_id': table_id,
                    'table_number': table_number,
                    'table_status': table['status'],
                    'orders': orders,
                    'order_count': len(orders)
                })
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "data": live_orders,
            "total_tables": len(tables),
            "tables_with_orders": len(live_orders),
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        print(f"[LIVE_ORDERS_ERROR] {e}")
        return jsonify({"success": False, "message": "Server error"}), 500


@orders_bp.route('/api/table-orders/<int:table_id>', methods=['GET'])
def get_table_orders(table_id):
    """
    Get all pending orders for a specific table with menu item details (images, names, prices)
    """
    try:
        hotel_id = session.get('hotel_id')
        if not hotel_id:
            return jsonify({"success": False, "message": "Not authenticated"}), 401
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get table info
        cursor.execute("""
            SELECT id, table_number, status
            FROM tables
            WHERE id = %s AND hotel_id = %s
        """, (table_id, hotel_id))
        
        table = cursor.fetchone()
        if not table:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Table not found"}), 404
        
        # Get pending orders with menu item enrichment
        cursor.execute("""
            SELECT 
                id,
                table_id,
                    session_id,
                guest_name,
                items,
                total_amount,
                order_status,
                created_at
            FROM table_orders
            WHERE table_id = %s 
              AND hotel_id = %s
                            AND order_status IN ('ACTIVE', 'PREPARING')
                            AND COALESCE(total_amount, 0) > 0
                            AND COALESCE(JSON_LENGTH(items), 0) > 0
            ORDER BY created_at DESC
        """, (table_id, hotel_id))
        
        orders = cursor.fetchall()
        
        # Parse items and enrich with menu details
        for order in orders:
            if isinstance(order['items'], str):
                items_data = json.loads(order['items'])
            else:
                items_data = order['items'] or []
            
            # Enrich each item with menu data (image, category, etc.)
            enriched_items = []
            for item in items_data:
                item_id = item.get('id')
                if item_id:
                    # Fetch menu item details
                    cursor.execute("""
                        SELECT id, name, description, price, images, category_id
                        FROM menu_dishes
                        WHERE id = %s
                        LIMIT 1
                    """, (item_id,))
                    
                    menu_item = cursor.fetchone()
                    if menu_item:
                        # Parse images JSON to get first image
                        image_url = '/static/images/default_profile.png'
                        try:
                            if menu_item.get('images') and isinstance(menu_item['images'], str):
                                images_data = json.loads(menu_item['images'])
                                if images_data and len(images_data) > 0:
                                    image_url = f"/static/uploads/menu_images/{images_data[0]}"
                        except:
                            pass
                        
                        enriched_item = {
                            'id': item_id,
                            'dish_name': menu_item['name'] or item.get('name', 'Unknown'),
                            'name': menu_item['name'] or item.get('name', 'Unknown'),
                            'quantity': item.get('quantity', 1),
                            'price': float(menu_item.get('price', item.get('price', 0))),
                            'image_url': image_url,
                            'description': menu_item.get('description', '')
                        }
                    else:
                        # Fallback if menu item not found
                        enriched_item = {
                            'id': item_id,
                            'dish_name': item.get('name', 'Unknown'),
                            'name': item.get('name', 'Unknown'),
                            'quantity': item.get('quantity', 1),
                            'price': float(item.get('price', 0)),
                            'image_url': '/static/images/default_profile.png',
                            'description': ''
                        }
                else:
                    enriched_item = item
                
                enriched_items.append(enriched_item)
            
            order['items'] = enriched_items
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "table": table,
            "orders": orders,
            "total_items": sum(len(o['items']) for o in orders) if orders else 0,
            "total_amount": sum(float(o['total_amount']) for o in orders) if orders else 0.0
        })
    
    except Exception as e:
        print(f"[TABLE_ORDERS_ERROR] {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": "Server error"}), 500


@orders_bp.route('/api/order-summary', methods=['GET'])
def get_order_summary():
    """
    Get dashboard summary: total pending, preparing, completed orders
    Groups by order_status and returns counts and totals
    """
    try:
        hotel_id = session.get('hotel_id')
        if not hotel_id:
            return jsonify({"success": False, "message": "Not authenticated"}), 401
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Get summary stats
        cursor.execute("""
            SELECT 
                order_status,
                COUNT(*) as count,
                SUM(total_amount) as total_amount
            FROM table_orders
            WHERE hotel_id = %s
              AND order_status IN ('ACTIVE', 'PREPARING', 'COMPLETED')
              AND COALESCE(total_amount, 0) > 0
              AND COALESCE(JSON_LENGTH(items), 0) > 0
            GROUP BY order_status
        """, (hotel_id,))
        
        stats = cursor.fetchall()
        
        # Format response
        summary = {
            'ACTIVE': {'count': 0, 'total_amount': 0},
            'PREPARING': {'count': 0, 'total_amount': 0},
            'COMPLETED': {'count': 0, 'total_amount': 0}
        }
        
        for stat in stats:
            status = stat['order_status']
            summary[status] = {
                'count': stat['count'],
                'total_amount': float(stat['total_amount'] or 0)
            }
        
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "summary": summary,
            "total_pending": summary['ACTIVE']['count'],
            "total_preparing": summary['PREPARING']['count'],
            "total_completed": summary['COMPLETED']['count']
        })
    
    except Exception as e:
        print(f"[ORDER_SUMMARY_ERROR] {e}")
        return jsonify({"success": False, "message": "Server error"}), 500
