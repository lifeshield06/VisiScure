from database.db import get_db_connection
import json

class MenuCategory:
    @staticmethod
    def get_categories_by_hotel(hotel_id):
        """Get all categories for a specific hotel - returns list of dicts"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            if hotel_id:
                cursor.execute(
                    "SELECT id, name, COALESCE(food_type, 'veg') as food_type, COALESCE(cgst_percentage, 0.00) as cgst_percentage, COALESCE(sgst_percentage, 0.00) as sgst_percentage FROM menu_categories WHERE hotel_id = %s ORDER BY id",
                    (hotel_id,)
                )
            else:
                cursor.execute("SELECT id, name, COALESCE(food_type, 'veg') as food_type, COALESCE(cgst_percentage, 0.00) as cgst_percentage, COALESCE(sgst_percentage, 0.00) as sgst_percentage FROM menu_categories ORDER BY id")
            
            categories = cursor.fetchall()
            for category in categories:
                category['food_type'] = str(category.get('food_type') or 'veg').strip().lower()
            cursor.close()
            connection.close()
            
            # Return list of dicts with id, name, cgst_percentage, sgst_percentage
            return categories if categories else []
        except Exception as e:
            print(f"Error getting categories: {e}")
            return []
    
    @staticmethod
    def add_category(hotel_id, name, food_type='veg'):
        """Add a new category for a hotel"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            normalized_food_type = 'nonveg' if str(food_type).strip().lower() == 'nonveg' else 'veg'
            
            cursor.execute(
                "INSERT INTO menu_categories (hotel_id, name, food_type) VALUES (%s, %s, %s)",
                (hotel_id, name, normalized_food_type)
            )
            
            category_id = cursor.lastrowid
            connection.commit()
            cursor.close()
            connection.close()
            
            return {"success": True, "category_id": category_id, "message": "Category added successfully"}
        except Exception as e:
            print(f"Error adding category: {e}")
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def update_category(category_id, name, food_type='veg', hotel_id=None):
        """Update a category"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            normalized_food_type = 'nonveg' if str(food_type).strip().lower() == 'nonveg' else 'veg'
            
            if hotel_id:
                cursor.execute(
                    "UPDATE menu_categories SET name = %s, food_type = %s WHERE id = %s AND hotel_id = %s",
                    (name, normalized_food_type, category_id, hotel_id)
                )
            else:
                cursor.execute(
                    "UPDATE menu_categories SET name = %s, food_type = %s WHERE id = %s",
                    (name, normalized_food_type, category_id)
                )
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return {"success": True, "message": "Category updated successfully"}
        except Exception as e:
            print(f"Error updating category: {e}")
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def delete_category(category_id, hotel_id=None):
        """Delete a category"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            if hotel_id:
                cursor.execute(
                    "DELETE FROM menu_categories WHERE id = %s AND hotel_id = %s",
                    (category_id, hotel_id)
                )
            else:
                cursor.execute(
                    "DELETE FROM menu_categories WHERE id = %s",
                    (category_id,)
                )
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return {"success": True, "message": "Category deleted successfully"}
        except Exception as e:
            print(f"Error deleting category: {e}")
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def update_category_tax(category_id, cgst_percentage, sgst_percentage, hotel_id=None):
        """Update CGST and SGST percentages for a category"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            if hotel_id:
                cursor.execute(
                    "UPDATE menu_categories SET cgst_percentage = %s, sgst_percentage = %s WHERE id = %s AND hotel_id = %s",
                    (cgst_percentage, sgst_percentage, category_id, hotel_id)
                )
            else:
                cursor.execute(
                    "UPDATE menu_categories SET cgst_percentage = %s, sgst_percentage = %s WHERE id = %s",
                    (cgst_percentage, sgst_percentage, category_id)
                )
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return {"success": True, "message": "Category tax updated successfully"}
        except Exception as e:
            print(f"Error updating category tax: {e}")
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def get_category_tax(category_id):
        """Get tax rates for a specific category"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute(
                "SELECT COALESCE(cgst_percentage, 0.00) as cgst_percentage, COALESCE(sgst_percentage, 0.00) as sgst_percentage FROM menu_categories WHERE id = %s",
                (category_id,)
            )
            
            result = cursor.fetchone()
            cursor.close()
            connection.close()
            
            if result:
                return {
                    'cgst_percentage': float(result['cgst_percentage']),
                    'sgst_percentage': float(result['sgst_percentage'])
                }
            return {'cgst_percentage': 0.00, 'sgst_percentage': 0.00}  # Default
        except Exception as e:
            print(f"Error getting category tax: {e}")
            return {'cgst_percentage': 0.00, 'sgst_percentage': 0.00}  # Default


class MenuDish:
    IMAGE_UPLOAD_FOLDER = 'static/uploads/menu_images'

    @staticmethod
    def _build_image_url(filename):
        return f"/static/uploads/menu_images/{filename}"

    @staticmethod
    def get_dishes_by_category(category_id, hotel_id=None, active_only=False):
        """Get dishes for a specific category"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            active_clause = " AND COALESCE(is_active, 1) = 1" if active_only else ""

            if hotel_id:
                query = """SELECT id, name, price, quantity, description, images, kitchen_id, cgst, sgst, price_type, half_price, full_price,
                              COALESCE(is_active, 1) as is_active,
                              COALESCE(is_offer_active, 0) as is_offer_active,
                          offer_price, discount_percent, offer_start, offer_end, COALESCE(offer_applies_to, 'both') as offer_applies_to
                       FROM menu_dishes 
                       WHERE category_id = %s AND hotel_id = %s""" + active_clause + """
                       ORDER BY id"""
                cursor.execute(
                    query,
                    (category_id, hotel_id)
                )
            else:
                query = """SELECT id, name, price, quantity, description, images, kitchen_id, cgst, sgst, price_type, half_price, full_price,
                              COALESCE(is_active, 1) as is_active,
                              COALESCE(is_offer_active, 0) as is_offer_active,
                          offer_price, discount_percent, offer_start, offer_end, COALESCE(offer_applies_to, 'both') as offer_applies_to
                       FROM menu_dishes 
                       WHERE category_id = %s""" + active_clause + """
                       ORDER BY id"""
                cursor.execute(
                    query,
                    (category_id,)
                )
            
            dishes = cursor.fetchall()
            cursor.close()
            connection.close()
            
            # Parse JSON images and build image_urls
            for dish in dishes:
                if dish['images'] and dish['images'].strip():
                    try:
                        parsed = json.loads(dish['images'])
                        # Filter out empty strings and None values
                        if isinstance(parsed, list):
                            filtered = [img.strip() for img in parsed if img and isinstance(img, str) and img.strip()]
                            # DEDUPLICATE - remove any duplicate image filenames
                            dish['images'] = list(dict.fromkeys(filtered))
                        else:
                            dish['images'] = []
                    except (json.JSONDecodeError, TypeError, AttributeError):
                        dish['images'] = []
                else:
                    dish['images'] = []
                
                # Build image URLs only for valid images
                if dish['images'] and len(dish['images']) > 0:
                    dish['image_urls'] = [MenuDish._build_image_url(img) for img in dish['images'] if img and img.strip()]
                else:
                    dish['images'] = []  # Ensure empty list
                    dish['image_urls'] = []
                dish['price'] = float(dish['price']) if dish.get('price') is not None else 0.00
                dish['price_type'] = (dish.get('price_type') or 'single').strip().lower()
                dish['half_price'] = float(dish['half_price']) if dish.get('half_price') is not None else None
                dish['full_price'] = float(dish['full_price']) if dish.get('full_price') is not None else None
            
            return dishes
        except Exception as e:
            print(f"Error getting dishes: {e}")
            return []
    
    @staticmethod
    def get_all_dishes_by_hotel(hotel_id, active_only=False):
        """Get all dishes for a specific hotel grouped by category"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            active_clause = " AND COALESCE(d.is_active, 1) = 1" if active_only else ""

            query = """SELECT d.id, d.name, d.price, d.quantity, d.description, d.images, d.category_id, c.name as category_name, COALESCE(c.food_type, 'veg') as category_food_type, d.kitchen_id, d.cgst, d.sgst, d.price_type, d.half_price, d.full_price,
                        COALESCE(d.is_offer_active, 0) as is_offer_active, d.offer_price, d.discount_percent, d.offer_start, d.offer_end, COALESCE(d.offer_applies_to, 'both') as offer_applies_to
                   FROM menu_dishes d
                   JOIN menu_categories c ON d.category_id = c.id
                   WHERE d.hotel_id = %s""" + active_clause + """
                   ORDER BY c.id, d.id"""
            cursor.execute(
                query,
                (hotel_id,)
            )
            
            dishes = cursor.fetchall()
            cursor.close()
            connection.close()
            
            # Parse JSON images
            for dish in dishes:
                if dish['images'] and dish['images'].strip():
                    try:
                        parsed = json.loads(dish['images'])
                        # Filter out empty strings and None values
                        if isinstance(parsed, list):
                            filtered = [img.strip() for img in parsed if img and isinstance(img, str) and img.strip()]
                            # DEDUPLICATE - remove any duplicate image filenames
                            dish['images'] = list(dict.fromkeys(filtered))
                        else:
                            dish['images'] = []
                    except (json.JSONDecodeError, TypeError, AttributeError):
                        dish['images'] = []
                else:
                    dish['images'] = []
                # Only build URLs for valid images
                if dish['images'] and len(dish['images']) > 0:
                    dish['image_urls'] = [MenuDish._build_image_url(img) for img in dish['images'] if img and img.strip()]
                else:
                    dish['images'] = []  # Ensure empty list
                    dish['image_urls'] = []
                dish['price'] = float(dish['price']) if dish.get('price') is not None else 0.00
                dish['price_type'] = (dish.get('price_type') or 'single').strip().lower()
                dish['half_price'] = float(dish['half_price']) if dish.get('half_price') is not None else None
                dish['full_price'] = float(dish['full_price']) if dish.get('full_price') is not None else None
            
            return dishes
        except Exception as e:
            print(f"Error getting all dishes: {e}")
            return []
    
    @staticmethod
    def add_dish(hotel_id, category_id, name, price, quantity, description, images=None, kitchen_id=None, cgst=0.00, sgst=0.00, price_type='single', half_price=None, full_price=None, is_offer_active=False, offer_price=None, discount_percent=None, offer_start=None, offer_end=None, offer_applies_to='both'):
        """Add a new dish"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            images_json = json.dumps(images) if images else '[]'
            normalized_price_type = 'half_full' if str(price_type).lower() == 'half_full' else 'single'
            normalized_half_price = half_price if half_price is not None else None
            normalized_full_price = full_price if full_price is not None else None
            stored_price = normalized_full_price if normalized_price_type == 'half_full' and normalized_full_price is not None else price
            
            is_offer_active_int = 1 if is_offer_active else 0
            offer_price_val = float(offer_price) if offer_price and offer_price > 0 else None
            discount_percent_val = float(discount_percent) if discount_percent and discount_percent > 0 else None
            offer_applies_to_val = (offer_applies_to or 'both').strip().lower()
            if offer_applies_to_val not in ('half', 'full', 'both'):
                offer_applies_to_val = 'both'
            
            cursor.execute(
                """INSERT INTO menu_dishes (hotel_id, category_id, name, price, quantity, description, images, kitchen_id, cgst, sgst, price_type, half_price, full_price, is_offer_active, offer_price, discount_percent, offer_start, offer_end, offer_applies_to) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (hotel_id, category_id, name, stored_price, quantity, description, images_json, kitchen_id, cgst, sgst, normalized_price_type, normalized_half_price, normalized_full_price, is_offer_active_int, offer_price_val, discount_percent_val, offer_start, offer_end, offer_applies_to_val)
            )
            
            dish_id = cursor.lastrowid
            connection.commit()
            cursor.close()
            connection.close()
            
            return {"success": True, "dish_id": dish_id, "message": "Dish added successfully"}
        except Exception as e:
            print(f"Error adding dish: {e}")
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def update_dish(dish_id, name, price, quantity, description, images=None, hotel_id=None, kitchen_id=None, cgst=0.00, sgst=0.00, price_type='single', half_price=None, full_price=None, is_offer_active=False, offer_price=None, discount_percent=None, offer_start=None, offer_end=None, offer_applies_to='both'):
        """Update a dish"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # CRITICAL FIX: Handle empty list properly - empty list should become '[]' not None
            # images=None means don't update images, images=[] means clear all images
            should_update_images = images is not None
            images_json = json.dumps(images) if images is not None else None
            normalized_price_type = 'half_full' if str(price_type).lower() == 'half_full' else 'single'
            normalized_half_price = half_price if half_price is not None else None
            normalized_full_price = full_price if full_price is not None else None
            stored_price = normalized_full_price if normalized_price_type == 'half_full' and normalized_full_price is not None else price
            
            is_offer_active_int = 1 if is_offer_active else 0
            offer_price_val = float(offer_price) if offer_price and offer_price > 0 else None
            discount_percent_val = float(discount_percent) if discount_percent and discount_percent > 0 else None
            offer_applies_to_val = (offer_applies_to or 'both').strip().lower()
            if offer_applies_to_val not in ('half', 'full', 'both'):
                offer_applies_to_val = 'both'
            
            if should_update_images and hotel_id:
                cursor.execute(
                    """UPDATE menu_dishes 
                       SET name = %s, price = %s, quantity = %s, description = %s, images = %s, kitchen_id = %s, cgst = %s, sgst = %s, price_type = %s, half_price = %s, full_price = %s, is_offer_active = %s, offer_price = %s, discount_percent = %s, offer_start = %s, offer_end = %s, offer_applies_to = %s
                       WHERE id = %s AND hotel_id = %s""",
                    (name, stored_price, quantity, description, images_json, kitchen_id, cgst, sgst, normalized_price_type, normalized_half_price, normalized_full_price, is_offer_active_int, offer_price_val, discount_percent_val, offer_start, offer_end, offer_applies_to_val, dish_id, hotel_id)
                )
            elif should_update_images:
                cursor.execute(
                    """UPDATE menu_dishes 
                       SET name = %s, price = %s, quantity = %s, description = %s, images = %s, kitchen_id = %s, cgst = %s, sgst = %s, price_type = %s, half_price = %s, full_price = %s, is_offer_active = %s, offer_price = %s, discount_percent = %s, offer_start = %s, offer_end = %s, offer_applies_to = %s
                       WHERE id = %s""",
                    (name, stored_price, quantity, description, images_json, kitchen_id, cgst, sgst, normalized_price_type, normalized_half_price, normalized_full_price, is_offer_active_int, offer_price_val, discount_percent_val, offer_start, offer_end, offer_applies_to_val, dish_id)
                )
            elif hotel_id:
                cursor.execute(
                    """UPDATE menu_dishes 
                       SET name = %s, price = %s, quantity = %s, description = %s, kitchen_id = %s, cgst = %s, sgst = %s, price_type = %s, half_price = %s, full_price = %s, is_offer_active = %s, offer_price = %s, discount_percent = %s, offer_start = %s, offer_end = %s, offer_applies_to = %s
                       WHERE id = %s AND hotel_id = %s""",
                    (name, stored_price, quantity, description, kitchen_id, cgst, sgst, normalized_price_type, normalized_half_price, normalized_full_price, is_offer_active_int, offer_price_val, discount_percent_val, offer_start, offer_end, offer_applies_to_val, dish_id, hotel_id)
                )
            else:
                cursor.execute(
                    """UPDATE menu_dishes 
                       SET name = %s, price = %s, quantity = %s, description = %s, kitchen_id = %s, cgst = %s, sgst = %s, price_type = %s, half_price = %s, full_price = %s, is_offer_active = %s, offer_price = %s, discount_percent = %s, offer_start = %s, offer_end = %s, offer_applies_to = %s
                       WHERE id = %s""",
                    (name, stored_price, quantity, description, kitchen_id, cgst, sgst, normalized_price_type, normalized_half_price, normalized_full_price, is_offer_active_int, offer_price_val, discount_percent_val, offer_start, offer_end, offer_applies_to_val, dish_id)
                )
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return {"success": True, "message": "Dish updated successfully"}
        except Exception as e:
            print(f"Error updating dish: {e}")
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def delete_dish(dish_id, hotel_id=None):
        """Delete a dish"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            if hotel_id:
                cursor.execute(
                    "DELETE FROM menu_dishes WHERE id = %s AND hotel_id = %s",
                    (dish_id, hotel_id)
                )
            else:
                cursor.execute(
                    "DELETE FROM menu_dishes WHERE id = %s",
                    (dish_id,)
                )
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return {"success": True, "message": "Dish deleted successfully"}
        except Exception as e:
            print(f"Error deleting dish: {e}")
            return {"success": False, "message": str(e)}
    
    @staticmethod
    def get_dish_by_id(dish_id, hotel_id=None):
        """Get a single dish by ID"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            if hotel_id:
                cursor.execute(
                    "SELECT id, name, price, quantity, description, images, category_id, hotel_id, kitchen_id, cgst, sgst, price_type, half_price, full_price, COALESCE(is_active,1) as is_active, COALESCE(is_offer_active,0) as is_offer_active, offer_price, discount_percent, offer_start, offer_end, COALESCE(offer_applies_to, 'both') as offer_applies_to FROM menu_dishes WHERE id = %s AND hotel_id = %s",
                    (dish_id, hotel_id)
                )
            else:
                cursor.execute(
                    "SELECT id, name, price, quantity, description, images, category_id, hotel_id, kitchen_id, cgst, sgst, price_type, half_price, full_price, COALESCE(is_active,1) as is_active, COALESCE(is_offer_active,0) as is_offer_active, offer_price, discount_percent, offer_start, offer_end, COALESCE(offer_applies_to, 'both') as offer_applies_to FROM menu_dishes WHERE id = %s",
                    (dish_id,)
                )
            
            dish = cursor.fetchone()
            cursor.close()
            connection.close()
            
            if dish:
                # CRITICAL FIX: Properly handle images - ensure empty list when no images
                if dish['images'] and dish['images'].strip():
                    try:
                        parsed_images = json.loads(dish['images'])
                        # Filter out empty strings, None values, and whitespace-only strings
                        if isinstance(parsed_images, list):
                            filtered = [img.strip() for img in parsed_images if img and isinstance(img, str) and img.strip()]
                            # DEDUPLICATE - remove any duplicate image filenames
                            dish['images'] = list(dict.fromkeys(filtered))
                        else:
                            dish['images'] = []
                    except (json.JSONDecodeError, TypeError, AttributeError):
                        dish['images'] = []
                else:
                    dish['images'] = []
                dish['price_type'] = (dish.get('price_type') or 'single').strip().lower()
                dish['half_price'] = float(dish['half_price']) if dish.get('half_price') is not None else None
                dish['full_price'] = float(dish['full_price']) if dish.get('full_price') is not None else None
                
                # Only create URLs for valid image filenames - ensure list is truly empty when no images
                if dish['images'] and len(dish['images']) > 0:
                    # Create URLs from deduplicated image list
                    dish['image_urls'] = [MenuDish._build_image_url(img) for img in dish['images'] if img and img.strip()]
                else:
                    dish['images'] = []  # Ensure it's an empty list, not None or other
                    dish['image_urls'] = []
                
                dish['price'] = float(dish['price'])
                dish['price_type'] = (dish.get('price_type') or 'single').strip().lower()
                dish['half_price'] = float(dish['half_price']) if dish.get('half_price') is not None else None
                dish['full_price'] = float(dish['full_price']) if dish.get('full_price') is not None else None
            
            return dish
        except Exception as e:
            print(f"Error getting dish: {e}")
            return None
