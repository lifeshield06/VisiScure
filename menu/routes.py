import os
from datetime import datetime
from flask import jsonify, request, render_template, url_for, session
from werkzeug.utils import secure_filename
from . import menu_bp
from .models import MenuCategory, MenuDish
from database.db import get_db_connection
from wallet.models import HotelWallet

# Upload configuration
UPLOAD_FOLDER = 'static/uploads/menu_images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def log_menu_activity(activity_type, message, hotel_id=None):
    """Log menu-related activity with role='manager'"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO recent_activities (activity_type, message, hotel_id, role) VALUES (%s, %s, %s, %s)",
            (activity_type, message, hotel_id, 'manager')
        )
        conn.commit()
        print(f"[MENU ACTIVITY LOGGED] type={activity_type}, hotel_id={hotel_id}, role=manager")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[MENU ACTIVITY ERROR] {e}")

def check_food_module():
    """Check if food module is enabled for this manager's hotel"""
    if not session.get('manager_id'):
        return False
    return session.get('food_enabled', False)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, dish_id):
    """Save uploaded file and return filename"""
    if file and allowed_file(file.filename):
        filename = secure_filename(f"dish_{dish_id}_{file.filename}")
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        
        # Create upload directory if it doesn't exist
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        
        try:
            file.save(filepath)
            return filename
        except Exception as e:
            print(f"Error saving file: {e}")
            return None
    return None


def _public_order_wallet_available(hotel_id):
    """Real-time wallet balance gate for public QR/menu flows."""
    if not hotel_id:
        return True
    result = HotelWallet.check_balance_for_order(hotel_id)
    return bool(result.get('sufficient', True))


def _parse_offer_datetime(value):
    if not value:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace(' ', 'T'))
    except ValueError:
        return None


def _get_today_special_name_set(hotel_id):
    names = set()
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT dish_name
            FROM today_specials
            WHERE hotel_id = %s AND special_date = CURDATE() AND is_active = TRUE
            """,
            (hotel_id,)
        )
        for row in cursor.fetchall() or []:
            key = str(row.get('dish_name') or '').strip().lower()
            if key:
                names.add(key)
    except Exception as exc:
        print(f"[PUBLIC MENU] today special name map error: {exc}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return names


def _get_active_menu_offer_map(hotel_id, names):
    if not names:
        return {}

    conn = None
    cursor = None
    result = {}
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        placeholders = ','.join(['%s'] * len(names))
        query = f"""
            SELECT name, COALESCE(is_offer_active, 0) AS is_offer_active,
                   offer_price, discount_percent, offer_start, offer_end
            FROM menu_dishes
            WHERE hotel_id = %s
              AND COALESCE(is_active, 1) = 1
              AND LOWER(name) IN ({placeholders})
        """
        cursor.execute(query, [hotel_id] + list(names))
        now = datetime.now()
        for row in cursor.fetchall() or []:
            if not int(row.get('is_offer_active') or 0):
                continue
            start_dt = _parse_offer_datetime(row.get('offer_start'))
            end_dt = _parse_offer_datetime(row.get('offer_end'))
            if not start_dt or not end_dt or not (start_dt <= now <= end_dt):
                continue

            key = str(row.get('name') or '').strip().lower()
            if not key:
                continue

            result[key] = {
                'is_offer_active': 1,
                'offer_price': float(row['offer_price']) if row.get('offer_price') is not None else None,
                'discount_percent': float(row['discount_percent']) if row.get('discount_percent') is not None else None,
                'offer_type': 'percentage' if row.get('discount_percent') is not None else ('flat' if row.get('offer_price') is not None else None),
                'offer_source': 'menu'
            }
    except Exception as exc:
        print(f"[PUBLIC MENU] active offer map error: {exc}")
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
    return result


def _resolve_public_table(TableModel, incoming_id):
    """Resolve a public menu identifier to a table record.

    Supports both direct table IDs and revisit links where the ID is a hotel_id.
    """
    table = TableModel.get_table_by_id(incoming_id)
    if table:
        return table

    hotel_tables = TableModel.get_all_tables(incoming_id)
    if hotel_tables:
        return hotel_tables[0]

    return None

def _parse_dish_price_payload(form_data):
    price_type = (form_data.get("price_type") or "single").strip().lower()
    if price_type == "half_full":
        half_price_str = (form_data.get("half_price") or "").strip()
        full_price_str = (form_data.get("full_price") or "").strip()
        try:
            half_price = float(half_price_str) if half_price_str else 0
        except ValueError:
            return None, None, None, None, "Invalid half price format"
        try:
            full_price = float(full_price_str) if full_price_str else 0
        except ValueError:
            return None, None, None, None, "Invalid full price format"
        if half_price <= 0 or full_price <= 0:
            return None, None, None, None, "Half and full prices must be greater than 0"
        return "half_full", half_price, full_price, full_price, None

    price_str = (form_data.get("price") or "0").strip()
    try:
        price = float(price_str) if price_str else 0
    except ValueError:
        return None, None, None, None, "Invalid price format"
    if price <= 0:
        return None, None, None, None, "Price must be greater than 0"
    return "single", None, None, price, None

def _parse_offer_payload(form_data):
    """Parse offer settings from form data"""
    is_offer_active = form_data.get("is_offer_active") in ('true', '1', 'True', 'on')
    offer_price = None
    discount_percent = None
    offer_start = None
    offer_end = None
    offer_applies_to = 'both'
    
    if is_offer_active:
        # Parse offer price or discount percent
        offer_price_str = (form_data.get("offer_price") or "").strip()
        discount_str = (form_data.get("discount_percent") or "").strip()
        offer_start_str = (form_data.get("offer_start") or "").strip()
        offer_end_str = (form_data.get("offer_end") or "").strip()
        
        if offer_price_str:
            try:
                offer_price = float(offer_price_str)
                if offer_price <= 0:
                    return None, None, None, None, None, "Offer price must be greater than 0"
            except ValueError:
                return None, None, None, None, None, "Invalid offer price format"
        
        if discount_str:
            try:
                discount_percent = float(discount_str)
                if discount_percent < 0 or discount_percent > 100:
                    return None, None, None, None, None, "Discount percent must be between 0 and 100"
            except ValueError:
                return None, None, None, None, None, "Invalid discount percent format"
        
        if not offer_price and not discount_percent:
            return None, None, None, None, None, "Either offer price or discount percent must be set"
        
        if not offer_start_str or not offer_end_str:
            return None, None, None, None, None, "Offer start and end times are required"

        offer_applies_to = (form_data.get("offer_applies_to") or "").strip().lower()
        if offer_applies_to not in ('half', 'full', 'both'):
            return None, None, None, None, None, "Apply Offer To is required"

        try:
            start_dt = datetime.fromisoformat(offer_start_str)
            end_dt = datetime.fromisoformat(offer_end_str)
        except ValueError:
            return None, None, None, None, None, "Invalid offer date/time format"
        if end_dt <= start_dt:
            return None, None, None, None, None, "Offer end time must be after start time"
        
        offer_start = offer_start_str if offer_start_str else None
        offer_end = offer_end_str if offer_end_str else None
    
    return is_offer_active, offer_price, discount_percent, offer_start, offer_end, offer_applies_to, None

def build_image_urls(images):
    """Return only image URLs that actually exist on disk."""
    if not images:
        return []

    urls = []
    # Handle both comma-separated string and list
    if isinstance(images, str):
        images = [img.strip() for img in images.split(',') if img.strip()]
    else:
        # Filter out empty strings from list
        images = [img.strip() if isinstance(img, str) else img for img in images if img and (not isinstance(img, str) or img.strip())]
    
    for img in images:
        # Skip empty strings
        if not img or (isinstance(img, str) and not img.strip()):
            continue
        upload_path = os.path.join(UPLOAD_FOLDER, img)
        if os.path.exists(upload_path):
            urls.append(url_for('static', filename=f'uploads/menu_images/{img}'))
    return urls


def _serialize_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value.isoformat(timespec='seconds')
    value_str = str(value).strip()
    if not value_str:
        return None
    return value_str.replace(' ', 'T')


def _apply_runtime_offer_state(dish):
    """Mark offer active only when current server time is inside offer window."""
    is_enabled = bool(int(dish.get('is_offer_active') or 0))
    start_raw = dish.get('offer_start')
    end_raw = dish.get('offer_end')

    start_dt = None
    end_dt = None
    try:
        if start_raw:
            start_dt = datetime.fromisoformat(str(start_raw).replace(' ', 'T'))
        if end_raw:
            end_dt = datetime.fromisoformat(str(end_raw).replace(' ', 'T'))
    except ValueError:
        start_dt = None
        end_dt = None

    now = datetime.now()
    runtime_active = bool(is_enabled and start_dt and end_dt and start_dt <= now <= end_dt)
    dish['is_offer_active'] = 1 if runtime_active else 0
    return dish

def format_dish(dish_row):
    """Format a dish database row into the expected dictionary format"""
    images = dish_row.get('images', None)
    
    # Handle all possible image formats and filter empty values
    if images is None or images == '' or images == 'null':
        images_list = []
    elif isinstance(images, str):
        # Try JSON parsing first
        try:
            import json
            parsed = json.loads(images)
            if isinstance(parsed, list):
                images_list = [img.strip() for img in parsed if img and isinstance(img, str) and img.strip()]
            else:
                images_list = []
        except:
            # Fallback to comma-separated
            images_list = [img.strip() for img in images.split(',') if img.strip()]
    elif isinstance(images, list):
        # Filter out empty/None values from list
        images_list = [img.strip() if isinstance(img, str) else str(img) for img in images if img and (not isinstance(img, str) or img.strip())]
    else:
        images_list = []
    
    # Final validation - ensure no empty strings
    images_list = [img for img in images_list if img and img.strip()]
    
    # DEDUPLICATE - remove any duplicate image filenames while preserving order
    images_list = list(dict.fromkeys(images_list))
    
    # Build URLs only if we have valid images
    image_urls = build_image_urls(images_list) if images_list else []
    
    return {
        "id": dish_row['id'],
        "name": dish_row['name'],
        "is_active": int(dish_row.get('is_active', 1) if dish_row.get('is_active') is not None else 1),
        "price": float(dish_row['price']) if dish_row.get('price') is not None else 0.00,
        "price_type": (dish_row.get('price_type') or 'single').strip().lower(),
        "half_price": float(dish_row['half_price']) if dish_row.get('half_price') is not None else None,
        "full_price": float(dish_row['full_price']) if dish_row.get('full_price') is not None else None,
        "is_offer_active": int(dish_row.get('is_offer_active', 0) or 0),
        "offer_price": float(dish_row['offer_price']) if dish_row.get('offer_price') is not None else None,
        "discount_percent": float(dish_row['discount_percent']) if dish_row.get('discount_percent') is not None else None,
        "offer_start": _serialize_datetime(dish_row.get('offer_start')),
        "offer_end": _serialize_datetime(dish_row.get('offer_end')),
        "offer_applies_to": (dish_row.get('offer_applies_to') or 'both').strip().lower(),
        "quantity": dish_row['quantity'],
        "description": dish_row.get('description', ''),
        "images": images_list,
        "image_urls": image_urls,
        "category_id": dish_row.get('category_id'),
        "kitchen_id": dish_row.get('kitchen_id'),
        "cgst": float(dish_row['cgst']) if dish_row.get('cgst') is not None else 0.00,
        "sgst": float(dish_row['sgst']) if dish_row.get('sgst') is not None else 0.00,
        "display_price": float(dish_row['full_price']) if dish_row.get('price_type') == 'half_full' and dish_row.get('full_price') is not None else float(dish_row['price']) if dish_row.get('price') is not None else 0.00
    }

@menu_bp.route("/menu")
def menu_page():
    return render_template('menu/menu_page.html')

@menu_bp.route("/menu-dashboard")
def menu_dashboard():
    if not check_food_module():
        return jsonify({"success": False, "message": "Food ordering module not enabled for this hotel"}), 403
    return render_template('menu/menu_dashboard.html')

@menu_bp.route("/api/categories")
def get_categories():
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({"success": False, "message": "Hotel not found"}), 400
    
    categories_list = MenuCategory.get_categories_by_hotel(hotel_id)
    # Convert to dict format {id: name} for frontend compatibility
    categories = {cat['id']: cat['name'] for cat in categories_list}
    category_meta = {
        str(cat['id']): {
            "id": cat['id'],
            "name": cat['name'],
            "food_type": str(cat.get('food_type') or 'veg').strip().lower()
        }
        for cat in categories_list
    }
    return jsonify({"success": True, "categories": categories, "category_meta": category_meta})

@menu_bp.route("/api/kitchens")
def get_kitchens_for_menu():
    """Get all active kitchens for the hotel to populate the Assign Kitchen dropdown"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({"success": False, "message": "Hotel not found"}), 400
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, section_name as name FROM kitchen_sections WHERE hotel_id = %s AND is_active = TRUE ORDER BY section_name",
            (hotel_id,)
        )
        kitchens = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"success": True, "kitchens": kitchens})
    except Exception as e:
        print(f"Error fetching kitchens: {e}")
        return jsonify({"success": False, "message": "Error fetching kitchens"})

@menu_bp.route("/api/dishes/<int:category_id>")
def get_dishes(category_id):
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({"success": False, "message": "Hotel not found"}), 400
    
    dishes_list = MenuDish.get_dishes_by_category(category_id, hotel_id)
    dishes = [format_dish(dish) for dish in dishes_list]
    return jsonify({"success": True, "dishes": dishes})

@menu_bp.route("/api/add-dish", methods=["POST"])
def add_dish():
    if not check_food_module():
        return jsonify({"success": False, "message": "Food ordering module not enabled for this hotel"}), 403
    
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({"success": False, "message": "Hotel not found"}), 400
    
    try:
        category_id = int(request.form.get("category_id", 0))
        kitchen_id = request.form.get("kitchen_id", "").strip()
        kitchen_id = int(kitchen_id) if kitchen_id else None
        name = request.form.get("name", "").strip()
        quantity_str = request.form.get("quantity", "").strip()
        description = request.form.get("description", "").strip()
        cgst_str = request.form.get("cgst", "0").strip()
        sgst_str = request.form.get("sgst", "0").strip()
        
        # Parse tax values
        try:
            cgst = float(cgst_str) if cgst_str.strip() != "" else 0.00
        except ValueError:
            cgst = 0.00
        try:
            sgst = float(sgst_str) if sgst_str.strip() != "" else 0.00
        except ValueError:
            sgst = 0.00

        price_type, half_price, full_price, price, price_error = _parse_dish_price_payload(request.form)
        if price_error:
            return jsonify({"success": False, "message": price_error})
        
        # Parse offer settings
        is_offer_active, offer_price, discount_percent, offer_start, offer_end, offer_applies_to, offer_error = _parse_offer_payload(request.form)
        if offer_error:
            return jsonify({"success": False, "message": offer_error})
        
        # Validation
        if not name:
            return jsonify({"success": False, "message": "Dish name is required"})
        
        # Quantity is optional - use as-is or empty string
        quantity = quantity_str if quantity_str else ""
        
        # Verify category exists for this hotel
        categories = MenuCategory.get_categories_by_hotel(hotel_id)
        category_ids = [cat['id'] for cat in categories]
        if category_id not in category_ids:
            return jsonify({"success": False, "message": "Category not found"})
        
        # Handle image uploads first to get filenames
        images = []
        uploaded_files = request.files.getlist('images')
        valid_files = [f for f in uploaded_files if f and f.filename and f.filename.strip()]
        
        if len(valid_files) > 3:
            return jsonify({"success": False, "message": "Maximum 3 images allowed"})
        
        # We need a temporary ID for saving files, so add dish first with empty images
        result = MenuDish.add_dish(
            hotel_id=hotel_id,
            category_id=category_id,
            name=name,
            price=price,
            quantity=quantity,
            description=description,
            images=[],  # Empty list initially
            kitchen_id=kitchen_id,
            cgst=cgst,
            sgst=sgst,
            price_type=price_type,
            half_price=half_price,
            full_price=full_price,
            is_offer_active=is_offer_active,
            offer_price=offer_price,
            discount_percent=discount_percent,
            offer_start=offer_start,
            offer_end=offer_end,
            offer_applies_to=offer_applies_to
        )
        
        if not result.get("success"):
            return jsonify({"success": False, "message": "Failed to add dish"})
        
        new_id = result.get("dish_id")
        
        # Now save files with the dish ID
        for file in valid_files:
            saved_filename = save_uploaded_file(file, new_id)
            if saved_filename:
                images.append(saved_filename)
        
        # Update dish with images if any were uploaded
        if images:
            MenuDish.update_dish(
                dish_id=new_id,
                name=name,
                price=price,
                quantity=quantity,
                description=description,
                images=images,  # Pass as list
                hotel_id=hotel_id,
                kitchen_id=kitchen_id,
                cgst=cgst,
                sgst=sgst,
                price_type=price_type,
                half_price=half_price,
                full_price=full_price,
                is_offer_active=is_offer_active,
                offer_price=offer_price,
                discount_percent=discount_percent,
                offer_start=offer_start,
                offer_end=offer_end,
                offer_applies_to=offer_applies_to
            )
        
        # Create response dish
        new_dish = {
            "id": new_id,
            "name": name,
            "price": price,
            "display_price": price,
            "price_type": price_type,
            "half_price": half_price,
            "full_price": full_price,
            "quantity": quantity,
            "description": description,
            "images": images,
            "image_urls": build_image_urls(images),
            "cgst": cgst,
            "sgst": sgst,
            "kitchen_id": kitchen_id
        }
        
        log_menu_activity('menu', f"Dish '{name}' added to menu (₹{price})", hotel_id)
        return jsonify({"success": True, "message": "Dish added successfully", "dish": new_dish})
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"})

@menu_bp.route("/api/edit-dish", methods=["POST"])
def edit_dish():
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({"success": False, "message": "Hotel not found"}), 400
    
    try:
        dish_id = int(request.form.get("dish_id", 0))
        kitchen_id = request.form.get("kitchen_id", "").strip()
        kitchen_id = int(kitchen_id) if kitchen_id else None
        name = request.form.get("name", "").strip()
        quantity_str = request.form.get("quantity", "0").strip()
        description = request.form.get("description", "").strip()
        cgst_str = request.form.get("cgst", "0").strip()
        sgst_str = request.form.get("sgst", "0").strip()
        
        # Parse tax values
        try:
            cgst = float(cgst_str) if cgst_str.strip() != "" else 0.00
        except ValueError:
            cgst = 0.00
        try:
            sgst = float(sgst_str) if sgst_str.strip() != "" else 0.00
        except ValueError:
            sgst = 0.00

        price_type, half_price, full_price, price, price_error = _parse_dish_price_payload(request.form)
        if price_error:
            return jsonify({"success": False, "message": price_error})
        
        # Parse offer settings
        is_offer_active, offer_price, discount_percent, offer_start, offer_end, offer_applies_to, offer_error = _parse_offer_payload(request.form)
        if offer_error:
            return jsonify({"success": False, "message": offer_error})
        
        # Validation
        if not name:
            return jsonify({"success": False, "message": "Dish name is required"})
            
        quantity = quantity_str.strip() if quantity_str else "0"
        if not quantity:
            return jsonify({"success": False, "message": "Quantity is required"})
        
        # Get existing dish
        existing_dish = MenuDish.get_dish_by_id(dish_id, hotel_id)
        if not existing_dish:
            return jsonify({"success": False, "message": "Dish not found"})
        
        # Get existing images - already a list from get_dish_by_id()
        existing_images = existing_dish.get('images', [])
        if isinstance(existing_images, str):
            existing_images = [img.strip() for img in existing_images.split(',') if img.strip()]
        # Deduplicate existing images
        existing_images = list(dict.fromkeys(existing_images))  # Preserve order, remove duplicates
        existing_image_count = len(existing_images)
        
        # Handle new image uploads
        uploaded_files = request.files.getlist('images')
        valid_files = [f for f in uploaded_files if f and f.filename and f.filename.strip()]
        
        if valid_files:
            # Check if new uploads would exceed limit
            remaining_slots = 3 - existing_image_count
            if len(valid_files) > remaining_slots:
                return jsonify({
                    "success": False, 
                    "message": f"Cannot upload {len(valid_files)} images. You have {existing_image_count} existing image(s) and can only add {remaining_slots} more. (Max 3)"
                })
            
            if len(valid_files) + existing_image_count > 3:
                return jsonify({"success": False, "message": "Total images cannot exceed 3"})
            
            # Add new images to existing ones
            new_images = []
            for file in valid_files:
                saved_filename = save_uploaded_file(file, dish_id)
                if saved_filename and saved_filename not in existing_images:
                    new_images.append(saved_filename)
            # Combine and deduplicate
            images_list = list(dict.fromkeys(existing_images + new_images))
        else:
            # Keep existing images (already a list from the model)
            images_list = existing_images
        
        # Update dish
        success = MenuDish.update_dish(
            dish_id=dish_id,
            name=name,
            price=price,
            quantity=quantity,
            description=description,
            images=images_list,  # Pass as list
            hotel_id=hotel_id,
            kitchen_id=kitchen_id,
            cgst=cgst,
            sgst=sgst,
            price_type=price_type,
            half_price=half_price,
            full_price=full_price,
            is_offer_active=is_offer_active,
            offer_price=offer_price,
            discount_percent=discount_percent,
            offer_start=offer_start,
            offer_end=offer_end,
            offer_applies_to=offer_applies_to
        )
        
        if success:
            # Get updated dish for response
            updated_dish = MenuDish.get_dish_by_id(dish_id, hotel_id)
            log_menu_activity('menu', f"Dish '{name}' was updated", hotel_id)
            return jsonify({"success": True, "message": "Dish updated successfully", "dish": format_dish(updated_dish)})
        else:
            return jsonify({"success": False, "message": "Failed to update dish"})
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"})

@menu_bp.route("/api/toggle-dish-status", methods=["POST"])
@menu_bp.route("/menu/api/toggle-dish-status", methods=["POST"])
def toggle_dish_status():
    """Toggle is_active status for a dish (manager only)"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({"success": False, "message": "Hotel not found"}), 400
    try:
        data = request.get_json(silent=True) or {}
        dish_id = int(data.get("dish_id", 0))
        is_active = int(data.get("is_active", 1))  # 1 = active, 0 = inactive

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, hotel_id, COALESCE(is_active, 1) as is_active FROM menu_dishes WHERE id = %s AND (hotel_id = %s OR hotel_id IS NULL) LIMIT 1",
            (dish_id, hotel_id)
        )
        row = cursor.fetchone()
        if not row:
            cursor.close()
            conn.close()
            return jsonify({"success": False, "message": "Dish not found or update failed"}), 404

        cursor.execute(
            "UPDATE menu_dishes SET is_active = %s WHERE id = %s AND (hotel_id = %s OR hotel_id IS NULL)",
            (is_active, dish_id, hotel_id)
        )
        affected_rows = cursor.rowcount
        conn.commit()

        cursor.execute(
            "SELECT COALESCE(is_active, 1) FROM menu_dishes WHERE id = %s AND (hotel_id = %s OR hotel_id IS NULL) LIMIT 1",
            (dish_id, hotel_id)
        )
        status_row = cursor.fetchone()
        cursor.close()
        conn.close()

        db_is_active = status_row[0] if status_row else None
        if affected_rows == 0:
            print(f"[TOGGLE_DISH_STATUS] No-op update for dish_id={dish_id} hotel_id={hotel_id} requested={is_active} db_is_active={db_is_active}")
        else:
            print(f"[TOGGLE_DISH_STATUS] dish_id={dish_id} hotel_id={hotel_id} requested={is_active} affected_rows={affected_rows} db_is_active={db_is_active}")

        if db_is_active is None:
            return jsonify({"success": False, "message": "Dish not found or update failed"}), 404

        status_label = "Active" if is_active else "Inactive"
        log_menu_activity('menu', f"Dish ID {dish_id} set to {status_label}", hotel_id)
        response = jsonify({"success": True, "is_active": int(db_is_active)})
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        return response
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@menu_bp.route("/api/delete-dish", methods=["POST"])
def delete_dish():
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({"success": False, "message": "Hotel not found"}), 400
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data provided"})
        
        dish_id = int(data.get("dish_id", 0))
        
        # Get dish name before deletion for logging
        dish = MenuDish.get_dish_by_id(dish_id, hotel_id)
        dish_name = dish.get('name', 'Unknown') if dish else 'Unknown'
        
        result = MenuDish.delete_dish(dish_id, hotel_id)
        
        if result.get('success'):
            log_menu_activity('menu', f"Dish '{dish_name}' was deleted", hotel_id)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"})

@menu_bp.route("/api/delete-dish-image", methods=["POST"])
def delete_dish_image():
    """Delete a specific image from a dish using image filename"""
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({"success": False, "message": "Hotel not found"}), 400
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data provided"})
        
        dish_id = int(data.get("dish_id", 0))
        image_filename = data.get("image_filename", "").strip()
        
        if dish_id <= 0 or not image_filename:
            return jsonify({"success": False, "message": "Invalid dish or image"})
        
        # Get existing dish and verify ownership
        existing_dish = MenuDish.get_dish_by_id(dish_id, hotel_id)
        if not existing_dish:
            return jsonify({"success": False, "message": "Dish not found or access denied"})
        
        # Get existing images
        existing_images = existing_dish.get('images', [])
        if isinstance(existing_images, str):
            existing_images = [img.strip() for img in existing_images.split(',') if img.strip()]
        
        # Find and remove the image by filename
        if image_filename not in existing_images:
            return jsonify({"success": False, "message": "Image not found in dish"})
        
        existing_images.remove(image_filename)
        
        # Update dish with new image list
        success = MenuDish.update_dish(
            dish_id=dish_id,
            name=existing_dish['name'],
            price=existing_dish['price'],
            quantity=existing_dish['quantity'],
            description=existing_dish.get('description', ''),
            images=existing_images,
            hotel_id=hotel_id
        )
        
        if success:
            # Delete the actual file from disk
            try:
                file_path = os.path.join(UPLOAD_FOLDER, image_filename)
                if os.path.exists(file_path):
                    os.remove(file_path)
            except Exception as file_error:
                print(f"Warning: Could not delete image file: {file_error}")
            
            # Get updated dish for response
            updated_dish = MenuDish.get_dish_by_id(dish_id, hotel_id)
            remaining_count = len(existing_images)
            
            log_menu_activity('menu', f"Image removed from dish '{existing_dish['name']}'", hotel_id)
            return jsonify({
                "success": True, 
                "message": "Image removed successfully",
                "remaining_images": remaining_count,
                "dish": format_dish(updated_dish)
            })
        else:
            return jsonify({"success": False, "message": "Failed to update dish"})
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"})

@menu_bp.route("/api/add-category", methods=["POST"])
def add_category():
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({"success": False, "message": "Hotel not found"}), 400
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data provided"})
        
        name = data.get("name", "").strip()
        food_type = str(data.get("food_type", "")).strip().lower()
        
        if not name:
            return jsonify({"success": False, "message": "Category name is required"})
        if food_type not in ("veg", "nonveg"):
            return jsonify({"success": False, "message": "Food type is required"})
        
        # Check if category already exists for this hotel
        existing_categories = MenuCategory.get_categories_by_hotel(hotel_id)
        for cat in existing_categories:
            if cat['name'].lower() == name.lower():
                return jsonify({"success": False, "message": "Category already exists"})
        
        result = MenuCategory.add_category(hotel_id, name, food_type)  # hotel_id first
        
        if result.get("success"):
            log_menu_activity('menu', f"Category '{name}' was created", hotel_id)
            return jsonify({
                "success": True, 
                "message": f"Category '{name}' added successfully", 
                "category": {"id": result.get("category_id"), "name": name, "food_type": food_type}
            })
        else:
            return jsonify({"success": False, "message": result.get("message", "Failed to add category")})
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"})

@menu_bp.route("/api/edit-category", methods=["POST"])
def edit_category():
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({"success": False, "message": "Hotel not found"}), 400
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data provided"})
        
        category_id = int(data.get("category_id", 0))
        name = data.get("name", "").strip()
        food_type = str(data.get("food_type", "")).strip().lower()
        
        if not name:
            return jsonify({"success": False, "message": "Category name is required"})
        if food_type not in ("veg", "nonveg"):
            return jsonify({"success": False, "message": "Food type is required"})
        
        # Check if category exists for this hotel
        existing_categories = MenuCategory.get_categories_by_hotel(hotel_id)
        category_ids = [cat['id'] for cat in existing_categories]
        if category_id not in category_ids:
            return jsonify({"success": False, "message": "Category not found"})
        
        # Check if name already exists (excluding current category)
        for cat in existing_categories:
            if cat['id'] != category_id and cat['name'].lower() == name.lower():
                return jsonify({"success": False, "message": "Category name already exists"})
        
        result = MenuCategory.update_category(category_id, name, food_type, hotel_id)
        
        if result.get("success"):
            log_menu_activity('menu', f"Category updated to '{name}'", hotel_id)
            return jsonify({
                "success": True, 
                "message": f"Category updated to '{name}' successfully", 
                "category": {"id": category_id, "name": name, "food_type": food_type}
            })
        else:
            return jsonify({"success": False, "message": result.get("message", "Failed to update category")})
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"})

@menu_bp.route("/api/delete-category", methods=["POST"])
def delete_category():
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({"success": False, "message": "Hotel not found"}), 400
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "message": "No data provided"})
        
        category_id = int(data.get("category_id", 0))
        
        # Check if category exists for this hotel
        existing_categories = MenuCategory.get_categories_by_hotel(hotel_id)
        category = None
        for cat in existing_categories:
            if cat['id'] == category_id:
                category = cat
                break
        
        if not category:
            return jsonify({"success": False, "message": "Category not found"})
        
        category_name = category['name']
        
        # Get dishes count before deletion
        dishes = MenuDish.get_dishes_by_category(category_id, hotel_id)
        dishes_count = len(dishes)
        
        # Delete category (dishes will be deleted via CASCADE or manually)
        result = MenuCategory.delete_category(category_id, hotel_id)
        
        if result.get("success"):
            log_menu_activity('menu', f"Category '{category_name}' deleted ({dishes_count} dishes)", hotel_id)
            return jsonify({
                "success": True, 
                "message": f"Category '{category_name}' and {dishes_count} dish(es) deleted successfully"
            })
        else:
            return jsonify({"success": False, "message": result.get("message", "Failed to delete category")})
        
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"})

@menu_bp.route("/api/full-menu")
def get_full_menu():
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({"success": False, "message": "Hotel not found"}), 400
    
    full_menu = []
    categories = MenuCategory.get_categories_by_hotel(hotel_id)
    
    for category in categories:
        dishes_list = MenuDish.get_dishes_by_category(category['id'], hotel_id)
        category_food_type = str(category.get('food_type') or 'veg').strip().lower()
        dishes = [
            {
                **format_dish(dish),
                "food_type": category_food_type
            }
            for dish in dishes_list
        ]
        full_menu.append({
            "category_id": category['id'],
            "category_name": category['name'],
            "food_type": category_food_type,
            "dishes": dishes
        })
    return jsonify({"success": True, "menu": full_menu})


@menu_bp.route("/api/public-menu/<int:table_id>")
def get_public_menu(table_id):
    """Public API to get menu for a table - no login required"""
    try:
        from orders.table_models import Table
        
        # Resolve table directly or via visit-again hotel_id fallback
        table = _resolve_public_table(Table, table_id)
        if not table:
            return jsonify({"success": False, "message": "Table not found"}), 404
        
        hotel_id = table.get('hotel_id')
        if not hotel_id:
            return jsonify({"success": False, "message": "Hotel not configured for this table"}), 400

        if not _public_order_wallet_available(hotel_id):
            return jsonify({
                "success": False,
                "message": "Service temporarily unavailable. Please contact hotel staff."
            }), 503
        
        full_menu = []
        today_special_names = _get_today_special_name_set(hotel_id)
        categories = MenuCategory.get_categories_by_hotel(hotel_id)
        
        for category in categories:
            dishes_list = MenuDish.get_dishes_by_category(category['id'], hotel_id, active_only=True)
            category_food_type = str(category.get('food_type') or 'veg').strip().lower()
            dishes = []
            for dish in dishes_list:
                # Double-check: skip any dish that is explicitly inactive
                if int(dish.get('is_active', 1) or 1) == 0:
                    print(f"[PUBLIC MENU] Skipping inactive dish id={dish.get('id')} name={dish.get('name')}")
                    continue
                formatted = {
                    **format_dish(dish),
                    "food_type": category_food_type
                }
                formatted = _apply_runtime_offer_state(formatted)
                formatted['is_today_special'] = str(formatted.get('name') or '').strip().lower() in today_special_names
                dishes.append(formatted)
            if not dishes:
                continue
            full_menu.append({
                "category_id": category['id'],
                "category_name": category['name'],
                "food_type": category_food_type,
                "dishes": dishes
            })
        response = jsonify({"success": True, "menu": full_menu})
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        return response
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@menu_bp.route("/api/public-daily-special/<int:table_id>")
def get_public_daily_special(table_id):
    """Public API to get today's daily specials for a table - no login required"""
    try:
        from orders.table_models import Table
        from hotel_manager.models import DailySpecialMenu, DailySpecialSettings
        
        # Resolve table directly or via visit-again hotel_id fallback
        table = _resolve_public_table(Table, table_id)
        if not table:
            return jsonify({"success": False, "message": "Table not found"}), 404
        
        hotel_id = table.get('hotel_id')
        if not hotel_id:
            return jsonify({"success": False, "message": "Hotel not configured for this table"}), 400

        if not _public_order_wallet_available(hotel_id):
            return jsonify({
                "success": False,
                "message": "Service temporarily unavailable. Please contact hotel staff."
            }), 503
        
        # Get all today's specials for this hotel
        specials = DailySpecialMenu.get_today_specials(hotel_id)
        settings = DailySpecialSettings.get_settings(hotel_id)
        special_names = {str(s.get('dish_name') or '').strip().lower() for s in specials if s.get('dish_name')}
        menu_offer_map = _get_active_menu_offer_map(hotel_id, special_names)
        
        # Format specials for API response
        formatted_specials = []
        for special in specials:
            base_price = float(special['price'])
            special_offer_active = int(special.get('is_offer_active') or 0) == 1
            offer_type = (special.get('offer_type') or '').strip().lower()
            offer_value = float(special['offer_value']) if special.get('offer_value') is not None else None
            offer_price = float(special['offer_price']) if special.get('offer_price') is not None else None
            discount_percent = float(special['discount_percent']) if special.get('discount_percent') is not None else None

            if not special_offer_active:
                synced = menu_offer_map.get(str(special.get('dish_name') or '').strip().lower())
                if synced:
                    special_offer_active = True
                    offer_price = synced.get('offer_price')
                    discount_percent = synced.get('discount_percent')
                    offer_type = synced.get('offer_type') or ''
                    if offer_type == 'percentage':
                        offer_value = discount_percent
                    elif offer_type == 'flat' and offer_price is not None:
                        offer_value = max(0.0, base_price - float(offer_price))

            formatted_specials.append({
                "id": special['id'],
                "dish_name": special['dish_name'],
                "menu_name": special['dish_name'],  # backward compatibility
                "description": special['description'],
                "price": base_price,
                "image_path": special.get('image_path'),
                "is_offer_active": 1 if special_offer_active else 0,
                "offer_type": offer_type,
                "offer_value": offer_value,
                "offer_price": offer_price,
                "discount_percent": discount_percent,
                "start_datetime": special.get('start_datetime'),
                "end_datetime": special.get('end_datetime'),
                "daily_start_time": special.get('daily_start_time'),
                "daily_end_time": special.get('daily_end_time')
            })
        
        # Also return single 'special' for backward compatibility
        single_special = formatted_specials[0] if formatted_specials else None
        
        return jsonify({
            "success": True, 
            "specials": formatted_specials,
            "special": single_special,  # backward compatibility
            "settings": settings
        })
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@menu_bp.route("/api/dish/<int:dish_id>")
def get_dish(dish_id):
    hotel_id = session.get('hotel_id')
    if not hotel_id:
        return jsonify({"success": False, "message": "Hotel not found"}), 400
    
    try:
        dish = MenuDish.get_dish_by_id(dish_id, hotel_id)
        if dish:
            return jsonify({"success": True, "dish": format_dish(dish)})
        return jsonify({"success": False, "message": "Dish not found"})
    except Exception as e:
        return jsonify({"success": False, "message": f"Server error: {str(e)}"})

# Initialize database tables for menu if using database
def init_menu_db():
    """Initialize menu database tables if needed"""
    pass