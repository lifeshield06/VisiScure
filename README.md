# VisiScure Order - Smart Restaurant Management System

A comprehensive Flask-based restaurant management system with features for guest verification, order management, waiter coordination, kitchen operations, and more.

## 📁 Project Structure

```
Hotel/
├── 📂 admin/                    # Admin module
│   ├── models.py
│   ├── routes.py
│   └── __init__.py
│
├── 📂 database/                 # Database configuration
│   ├── db.py                    # Database connection
│   └── *.sql                    # SQL schema files
│
├── 📂 guest_verification/       # Guest ID verification module
│   ├── models.py                # Verification data models
│   ├── routes.py                # Verification endpoints
│   ├── otp_service.py           # OTP/SMS service (MSG91)
│   └── __init__.py
│
├── 📂 hotel_manager/            # Hotel manager module
│   ├── models.py
│   ├── routes.py
│   └── __init__.py
│
├── 📂 kitchen/                  # Kitchen operations module
│   ├── models.py
│   ├── routes.py
│   └── __init__.py
│
├── 📂 menu/                     # Menu management module
│   ├── models.py
│   ├── routes.py
│   ├── templates/
│   └── __init__.py
│
├── 📂 orders/                   # Order management module
│   ├── table_models.py          # Table and bill models
│   ├── table_routes.py          # Order endpoints
│   ├── table_services.py        # Order business logic
│   └── __init__.py
│
├── 📂 waiter/                   # Waiter module
│   ├── models.py
│   ├── routes.py
│   └── __init__.py
│
├── 📂 waiter_calls/             # Waiter call system
│   ├── models.py                # Call request models
│   ├── routes.py                # Call endpoints
│   ├── voice_service.py         # Voice notification service
│   └── __init__.py
│
├── 📂 wallet/                   # Hotel wallet system
│   ├── models.py                # Wallet models
│   ├── routes.py                # Wallet endpoints
│   └── __init__.py
│
├── 📂 scripts/                  # Utility scripts
│   ├── 📂 migrations/           # Database migration scripts
│   ├── 📂 setup/                # Setup scripts
│   ├── 📂 utils/                # Utility scripts
│   └── 📂 sms/                  # SMS/OTP scripts
│
├── 📂 static/                   # Static files
│   ├── 📂 css/                  # Stylesheets
│   ├── 📂 js/                   # JavaScript files
│   ├── 📂 images/               # Images and logos
│   ├── 📂 sounds/               # Audio files (waiter calls)
│   └── 📂 uploads/              # User uploaded files
│
├── 📂 templates/                # HTML templates
│   ├── index.html               # Landing page
│   ├── manager_dashboard.html   # Manager interface
│   ├── waiter_dashboard_mobile.html  # Waiter interface
│   ├── table_menu.html          # Guest menu
│   └── 📂 shared/               # Shared templates
│
├── 📂 docs/                     # Documentation
│   ├── MSG91_SETUP_STEPS.md
│   ├── LOGO_SYSTEM_DOCUMENTATION.md
│   ├── VOICE_SYSTEM_SETUP.md
│   ├── WAITER_CALL_VOICE_SYSTEM.md
│   ├── DASHBOARD_LAYOUT_FIX.md
│   ├── LOGO_DISPLAY_FIXES.md
│   ├── TEMPLATE_FIX.md
│   ├── VOICE_TEST_RESULTS.md
│   ├── QUICK_MSG91_SETUP.txt
│   ├── QUICK_START_VOICE.txt
│   └── QUICK_FIX_GUIDE.txt
│
├── 📂 tests/                    # Test files
│   ├── test_layout.html
│   └── test_voice_playback.html
│
├── 📄 app.py                    # Main Flask application
├── 📄 config.py                 # Configuration file
├── 📄 requirements.txt          # Python dependencies
├── 📄 .env                      # Environment variables (not in git)
├── 📄 .env.example              # Environment template
├── 📄 .gitignore                # Git ignore rules
├── 📄 run_python.bat            # Windows Python runner
├── 📄 start_server.bat          # Windows server starter
└── 📄 README.md                 # This file
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- MySQL 5.7+
- pip (Python package manager)

### Installation

1. **Clone the repository**
   ```bash
   cd Hotel
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Setup database**
   ```bash
   # Create MySQL database
   mysql -u root -p
   CREATE DATABASE test;
   
   # Run migrations
   python scripts/migrations/create_guest_otp_table.py
   python scripts/migrations/create_waiter_calls_table.py
   # ... run other migrations as needed
   ```

5. **Start the server**
   ```bash
   python app.py
   # Or on Windows:
   start_server.bat
   ```

6. **Access the application**
   - Open browser: `http://localhost:5000`

## 📚 Key Features

### 1. Guest Verification System
- QR code-based guest check-in
- Mobile OTP verification (MSG91)
- ID document upload and verification
- Wallet-based charging system

### 2. Order Management
- Table-based ordering via QR codes
- Real-time order tracking
- Kitchen order routing
- Bill generation and payment

### 3. Waiter Management
- Multi-waiter table assignments
- Call waiter system (notifies all assigned waiters)
- Tip distribution (equal split among assigned waiters)
- Mobile-friendly waiter dashboard

### 4. Kitchen Operations
- Kitchen-specific order views
- Order status management
- Kitchen authentication system
- Real-time order updates

### 5. Menu Management
- Dynamic menu creation
- Category-based organization
- Image upload support
- Price management

### 6. Wallet System
- Hotel wallet for service charges
- Automatic deductions for verifications
- Transaction history
- Balance tracking

## 🔧 Configuration

### Environment Variables

See `.env.example` for all available configuration options.

**Key Variables:**
```bash
# Database
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=test

# SMS (MSG91)
SMS_ENABLED=false              # Set to 'true' for production
MSG91_AUTH_KEY=your_auth_key
MSG91_TEMPLATE_ID=             # Optional
MSG91_SENDER_ID=TIPTOP

# Flask
DEBUG=True
SECRET_KEY=your-secret-key
```

## 📖 Documentation

All documentation has been organized in the `docs/` folder:

### Setup Guides
- **MSG91 SMS Setup**: `docs/MSG91_SETUP_STEPS.md` - Complete MSG91 integration guide
- **Quick MSG91 Setup**: `docs/QUICK_MSG91_SETUP.txt` - Quick reference for SMS setup
- **Voice System Setup**: `docs/VOICE_SYSTEM_SETUP.md` - Waiter call voice system setup
- **Quick Voice Start**: `docs/QUICK_START_VOICE.txt` - Quick voice system reference

### System Documentation
- **Logo System**: `docs/LOGO_SYSTEM_DOCUMENTATION.md` - Hotel logo display system
- **Waiter Call Voice**: `docs/WAITER_CALL_VOICE_SYSTEM.md` - Voice notification system

### Fix Guides
- **Dashboard Layout**: `docs/DASHBOARD_LAYOUT_FIX.md` - Dashboard layout fixes
- **Logo Display**: `docs/LOGO_DISPLAY_FIXES.md` - Logo display troubleshooting
- **Template Fixes**: `docs/TEMPLATE_FIX.md` - Template-related fixes
- **Quick Fix Guide**: `docs/QUICK_FIX_GUIDE.txt` - Common issues and solutions

### Test Results
- **Voice Test Results**: `docs/VOICE_TEST_RESULTS.md` - Voice system test results

## 🧪 Testing

### Run Tests
```bash
# Test multi-waiter call system
python tests/test_multi_waiter_call.py

# Test tip distribution
python tests/test_tip_distribution.py
```

### SMS Testing
```bash
# Verify SMS configuration
python scripts/sms/verify_production_setup.py

# Test MSG91 API directly
python scripts/sms/test_msg91_direct.py

# Test complete OTP flow
python scripts/sms/send_test_sms.py
```

### System Verification
```bash
# Check waiter assignments
python scripts/utils/check_waiter_assignments.py

# Verify kitchen system
python scripts/utils/verify_kitchen_system.py

# Check wallet balance
python scripts/utils/check_wallet.py

# Verify all features
python scripts/utils/verify_system_features.py
```

## 🛠️ Development

### Running Migrations

```bash
# Run a specific migration
python scripts/migrations/create_guest_otp_table.py

# Setup tip distribution
python scripts/setup/setup_tip_distribution.py
```

### Creating New Features

1. Create module folder in root (e.g., `new_feature/`)
2. Add `__init__.py`, `models.py`, `routes.py`
3. Register blueprint in `app.py`
4. Add templates in `templates/`
5. Add static files in `static/`

## 📦 Dependencies

Key dependencies (see `requirements.txt` for full list):
- Flask - Web framework
- mysql-connector-python - MySQL driver
- python-dotenv - Environment management
- qrcode - QR code generation
- requests - HTTP library (for MSG91 API)

## 🔐 Security

- Environment variables for sensitive data
- Session-based authentication
- SQL injection prevention (parameterized queries)
- File upload validation
- OTP rate limiting (30s cooldown)
- Maximum OTP attempts (3)

## 🐛 Troubleshooting

### Common Issues

**Database Connection Error**
```bash
# Check MySQL is running
mysql -u root -p

# Verify credentials in .env
```

**OTP Not Received**
```bash
# Check SMS configuration
python scripts/sms/verify_production_setup.py

# Test MSG91 directly
python scripts/sms/test_msg91_direct.py
```

**Import Errors**
```bash
# Reinstall dependencies
pip install -r requirements.txt
```

## 📝 License

Proprietary - VisiScure Order Development Team

## 👥 Support

For issues or questions:
1. Check documentation in `docs/`
2. Run diagnostic scripts in `scripts/utils/`
3. Review Flask console logs
4. Contact development team

## 🔄 Recent Updates

- ✅ Migrated from Fast2SMS to MSG91 for OTP
- ✅ Implemented multi-waiter call system
- ✅ Added equal tip distribution among waiters
- ✅ Organized project structure
- ✅ Created comprehensive documentation

---

**Last Updated**: March 2026  
**Version**: 2.0  
**Status**: Production Ready
