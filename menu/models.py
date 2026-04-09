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
                    "SELECT id, name, COALESCE(cgst_percentage, 0.00) as cgst_percentage, COALESCE(sgst_percentage, 0.00) as sgst_percentage FROM menu_categories WHERE hotel_id = %s ORDER BY id",
                    (hotel_id,)
                )
            else:
                cursor.execute("SELECT id, name, COALESCE(cgst_percentage, 0.00) as cgst_percentage, COALESCE(sgst_percentage, 0.00) as sgst_percentage FROM menu_categories ORDER BY id")
            
            categories = cursor.fetchall()
            cursor.close()
            connection.close()
            
            # Return list of dicts with id, name, cgst_percentage, sgst_percentage
            return categories if categories else []
        except Exception as e:
            print(f"Error getting categories: {e}")
            return []
    
    @staticmethod
    def add_category(hotel_id, name):
        """Add a new category for a hotel"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            cursor.execute(
                "INSERT INTO menu_categories (hotel_id, name) VALUES (%s, %s)",
                (hotel_id, name)
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
    def update_category(category_id, name, hotel_id=None):
        """Update a category"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            if hotel_id:
                cursor.execute(
                    "UPDATE menu_categories SET name = %s WHERE id = %s AND hotel_id = %s",
                    (name, category_id, hotel_id)
                )
            else:
                cursor.execute(
                    "UPDATE menu_categories SET name = %s WHERE id = %s",
                    (name, category_id)
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
    def get_dishes_by_category(category_id, hotel_id=None):
        """Get all dishes for a specific category"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            if hotel_id:
                cursor.execute(
                    """SELECT id, name, price, quantity, description, images, kitchen_id, cgst, sgst
                       FROM menu_dishes 
                       WHERE category_id = %s AND hotel_id = %s
                       ORDER BY id""",
                    (category_id, hotel_id)
                )
            else:
                cursor.execute(
                    """SELECT id, name, price, quantity, description, images, kitchen_id, cgst, sgst
                       FROM menu_dishes 
                       WHERE category_id = %s
                       ORDER BY id""",
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
                dish['price'] = float(dish['price'])
            
            return dishes
        except Exception as e:
            print(f"Error getting dishes: {e}")
            return []
    
    @staticmethod
    def get_all_dishes_by_hotel(hotel_id):
        """Get all dishes for a specific hotel grouped by category"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute(
                """SELECT d.id, d.name, d.price, d.quantity, d.description, d.images, d.category_id, c.name as category_name, d.kitchen_id, d.cgst, d.sgst
                   FROM menu_dishes d
                   JOIN menu_categories c ON d.category_id = c.id
                   WHERE d.hotel_id = %s
                   ORDER BY c.id, d.id""",
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
                dish['price'] = float(dish['price'])
            
            return dishes
        except Exception as e:
            print(f"Error getting all dishes: {e}")
            return []
    
    @staticmethod
    def add_dish(hotel_id, category_id, name, price, quantity, description, images=None, kitchen_id=None, cgst=0.00, sgst=0.00):
        """Add a new dish"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            images_json = json.dumps(images) if images else '[]'
            
            cursor.execute(
                """INSERT INTO menu_dishes (hotel_id, category_id, name, price, quantity, description, images, kitchen_id, cgst, sgst) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (hotel_id, category_id, name, price, quantity, description, images_json, kitchen_id, cgst, sgst)
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
    def update_dish(dish_id, name, price, quantity, description, images=None, hotel_id=None, kitchen_id=None, cgst=0.00, sgst=0.00):
        """Update a dish"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # CRITICAL FIX: Handle empty list properly - empty list should become '[]' not None
            # images=None means don't update images, images=[] means clear all images
            should_update_images = images is not None
            images_json = json.dumps(images) if images is not None else None
            
            if should_update_images and hotel_id:
                cursor.execute(
                    """UPDATE menu_dishes 
                       SET name = %s, price = %s, quantity = %s, description = %s, images = %s, kitchen_id = %s, cgst = %s, sgst = %s 
                       WHERE id = %s AND hotel_id = %s""",
                    (name, price, quantity, description, images_json, kitchen_id, cgst, sgst, dish_id, hotel_id)
                )
            elif should_update_images:
                cursor.execute(
                    """UPDATE menu_dishes 
                       SET name = %s, price = %s, quantity = %s, description = %s, images = %s, kitchen_id = %s, cgst = %s, sgst = %s 
                       WHERE id = %s""",
                    (name, price, quantity, description, images_json, kitchen_id, cgst, sgst, dish_id)
                )
            elif hotel_id:
                cursor.execute(
                    """UPDATE menu_dishes 
                       SET name = %s, price = %s, quantity = %s, description = %s, kitchen_id = %s, cgst = %s, sgst = %s 
                       WHERE id = %s AND hotel_id = %s""",
                    (name, price, quantity, description, kitchen_id, cgst, sgst, dish_id, hotel_id)
                )
            else:
                cursor.execute(
                    """UPDATE menu_dishes 
                       SET name = %s, price = %s, quantity = %s, description = %s, kitchen_id = %s, cgst = %s, sgst = %s 
                       WHERE id = %s""",
                    (name, price, quantity, description, kitchen_id, cgst, sgst, dish_id)
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
                    "SELECT id, name, price, quantity, description, images, category_id, hotel_id, kitchen_id, cgst, sgst FROM menu_dishes WHERE id = %s AND hotel_id = %s",
                    (dish_id, hotel_id)
                )
            else:
                cursor.execute(
                    "SELECT id, name, price, quantity, description, images, category_id, hotel_id, kitchen_id, cgst, sgst FROM menu_dishes WHERE id = %s",
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
                
                # Only create URLs for valid image filenames - ensure list is truly empty when no images
                if dish['images'] and len(dish['images']) > 0:
                    # Create URLs from deduplicated image list
                    dish['image_urls'] = [MenuDish._build_image_url(img) for img in dish['images'] if img and img.strip()]
                else:
                    dish['images'] = []  # Ensure it's an empty list, not None or other
                    dish['image_urls'] = []
                
                dish['price'] = float(dish['price'])
            
            return dish
        except Exception as e:
            print(f"Error getting dish: {e}")
            return None
