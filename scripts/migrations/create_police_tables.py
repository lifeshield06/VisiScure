"""
Migration: Create police module tables
Run: python scripts/migrations/create_police_tables.py
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from dotenv import load_dotenv
load_dotenv()

from police.models import PoliceStation

PoliceStation.create_tables()

# Also create the hotel mapping table
from database.db import get_db_connection
conn = get_db_connection()
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS police_station_hotels (
        id INT AUTO_INCREMENT PRIMARY KEY,
        station_id INT NOT NULL,
        hotel_id INT NOT NULL,
        UNIQUE KEY unique_mapping (station_id, hotel_id),
        FOREIGN KEY (station_id) REFERENCES police_stations(id) ON DELETE CASCADE,
        FOREIGN KEY (hotel_id) REFERENCES hotels(id) ON DELETE CASCADE
    )
""")
conn.commit()
cursor.close()
conn.close()

print("Police tables created successfully.")
print("  - police_stations")
print("  - police_users")
print("  - police_access_logs")
print("  - police_station_hotels")
