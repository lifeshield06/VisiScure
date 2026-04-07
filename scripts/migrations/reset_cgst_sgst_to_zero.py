"""
One-time migration: reset all cgst/sgst values of 2.5 to 0.00
in both menu_dishes and menu_categories tables.
"""
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from dotenv import load_dotenv
load_dotenv()
from database.db import get_db_connection

conn   = get_db_connection()
cursor = conn.cursor()

cursor.execute("UPDATE menu_dishes SET cgst = 0.00, sgst = 0.00 WHERE cgst = 2.50 OR sgst = 2.50")
dishes_updated = cursor.rowcount

cursor.execute("UPDATE menu_categories SET cgst_percentage = 0.00, sgst_percentage = 0.00 WHERE cgst_percentage = 2.50 OR sgst_percentage = 2.50")
cats_updated = cursor.rowcount

conn.commit()
cursor.close()
conn.close()

print(f"✅ menu_dishes updated:     {dishes_updated} rows")
print(f"✅ menu_categories updated: {cats_updated} rows")
