-- Migration: Create today_specials table for multiple daily specials
-- Run this script to enable multi-special support

-- Create the new today_specials table
CREATE TABLE IF NOT EXISTS today_specials (
    id INT AUTO_INCREMENT PRIMARY KEY,
    hotel_id INT NOT NULL,
    dish_name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10, 2) NOT NULL,
    image_path VARCHAR(500) DEFAULT NULL,
    special_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    display_order INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_hotel_date_active (hotel_id, special_date, is_active)
);

-- Note: The old daily_special_menu table is kept for backward compatibility
-- The create_table() method in DailySpecialMenu class will auto-create this table
-- when the application starts if it doesn't exist
