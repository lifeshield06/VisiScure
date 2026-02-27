-- Create recent_activities table for live dashboard updates
CREATE TABLE IF NOT EXISTS recent_activities (
    id INT PRIMARY KEY AUTO_INCREMENT,
    hotel_id INT NULL,
    activity_type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_created_at (created_at),
    INDEX idx_hotel_id (hotel_id)
);

-- Auto-cleanup query (run periodically or before fetching)
-- DELETE FROM recent_activities WHERE created_at < NOW() - INTERVAL 3 DAY;
