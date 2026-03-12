import os

# MySQL Configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "Dattu21234")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "test")

# Flask Configuration
DEBUG = True
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")

# SMS Configuration for OTP (MSG91)
SMS_ENABLED = os.getenv("SMS_ENABLED", "true").lower() == "true"
MSG91_AUTH_KEY = os.getenv("MSG91_AUTH_KEY", "451618A0Y44msLOxW685a4c6aP1")
MSG91_TEMPLATE_ID = os.getenv("MSG91_TEMPLATE_ID", "1407177312988404171")
MSG91_SENDER_ID = os.getenv("MSG91_SENDER_ID", "VisScu")

# OTP Configuration
OTP_EXPIRY_MINUTES = 5
OTP_MAX_ATTEMPTS = 3
OTP_RESEND_COOLDOWN_SECONDS = 30

# Razorpay Configuration (Test Keys - replace with live keys in production)
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "rzp_test_RPIKv0UoeCuE4T")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "Wr1gDTqvaQ4p0KQHrBzWI5nf")
