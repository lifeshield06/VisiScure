-- Create waiter_tips table for distributed tip tracking
CREATE TABLE IF NOT EXISTS waiter_tips (
    id INT AUTO_INCREMENT PRIMARY KEY,
    waiter_id INT NOT NULL,
    bill_id INT NOT NULL,
    tip_amount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (waiter_id) REFERENCES waiters(id) ON DELETE CASCADE,
    FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE CASCADE,
    INDEX idx_waiter_id (waiter_id),
    INDEX idx_bill_id (bill_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
