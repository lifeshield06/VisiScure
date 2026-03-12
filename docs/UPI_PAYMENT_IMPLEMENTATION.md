# Hotel UPI QR Payment System - Implementation Guide

## ✅ Implementation Complete

The Hotel UPI QR Payment System has been successfully implemented. This document provides setup instructions and usage guide.

## 📋 What Was Implemented

### 1. Database Changes
- Added `upi_id` column to hotels table (VARCHAR 100)
- Added `upi_qr_image` column to hotels table (VARCHAR 255)
- Migration script created: `scripts/migrations/add_hotel_upi_payment.py`

### 2. Admin Panel Updates
- **Create Hotel Form**: Added UPI ID and QR Code upload fields
- **Edit Hotel Form**: Added ability to edit UPI ID, replace QR code, and remove QR code
- **File Upload**: QR images stored in `static/uploads/hotel_qr/`

### 3. Guest Payment Integration
- **Case A - QR Code Exists**: Shows modal with QR code, UPI ID, and bill amount
- **Case B - UPI ID Only**: Generates dynamic UPI payment link
- **Case C - No UPI Config**: Shows message that UPI is not available

### 4. Backend Changes
- Updated `admin/routes.py` to handle UPI configuration
- Updated `orders/table_routes.py` to pass UPI data to template
- File upload handling for QR codes with secure naming

### 5. Frontend Changes
- Updated `templates/admin/create_hotel.html` with UPI fields
- Updated `templates/admin/all_hotels.html` with UPI edit capability
- Updated `templates/table_menu.html` with UPI payment modal and logic

## 🚀 Setup Instructions

### Step 1: Run Database Migration

You need to run the migration script to add UPI columns to the hotels table.

**Option A: Using Python directly**
```bash
python Hotel/scripts/migrations/add_hotel_upi_payment.py
```

**Option B: Using the batch file (Windows)**
```bash
Hotel\run_python.bat scripts\migrations\add_hotel_upi_payment.py
```

**Option C: Manual SQL (if Python not available)**
```sql
ALTER TABLE hotels 
ADD COLUMN upi_id VARCHAR(100) NULL AFTER logo;

ALTER TABLE hotels 
ADD COLUMN upi_qr_image VARCHAR(255) NULL AFTER upi_id;
```

### Step 2: Verify Folder Structure

Ensure the UPI QR upload folder exists:
```
Hotel/static/uploads/hotel_qr/
```

This folder has already been created during implementation.

### Step 3: Restart Flask Server

After running the migration, restart your Flask application:
```bash
python Hotel/app.py
```

Or use the batch file:
```bash
Hotel\start_server.bat
```

## 📖 Usage Guide

### For Admin: Configure Hotel UPI Payment

1. **Create New Hotel**:
   - Go to Admin Dashboard → Create Hotel
   - Fill in hotel details
   - Scroll to "UPI Payment Configuration" section
   - Enter Hotel UPI ID (e.g., `hotel@paytm`, `9876543210@ybl`)
   - Upload UPI QR Code image (PNG, JPG, JPEG - Max 2MB)
   - Click "Create Hotel"

2. **Edit Existing Hotel**:
   - Go to Admin Dashboard → All Hotels
   - Click "Edit" button on any hotel
   - Scroll to "UPI Payment Configuration" section
   - Update UPI ID or upload new QR code
   - To remove QR code, click "Remove QR Code" button
   - Click "Save Changes"

### For Guests: Pay via UPI

1. **Complete Order**:
   - Guest scans table QR code
   - Places order from menu
   - Clicks "View Bill" button

2. **Payment Process**:
   - Click "Pay Now" button
   - Select "UPI" payment method

3. **Three Scenarios**:

   **Scenario A: Hotel has QR Code**
   - Modal opens showing hotel's UPI QR code
   - Guest scans QR with any UPI app (Google Pay, PhonePe, Paytm, etc.)
   - Completes payment in UPI app
   - Returns to browser and clicks "I've Completed the Payment"

   **Scenario B: Hotel has UPI ID only (no QR)**
   - UPI payment link opens automatically
   - Guest's UPI app opens with pre-filled payment details
   - Guest completes payment in UPI app
   - Returns to browser and confirms payment

   **Scenario C: Hotel has no UPI configuration**
   - Alert message: "UPI payment is not configured for this hotel. Please choose Cash."
   - Guest must select Cash payment method

## 🔧 Technical Details

### File Structure
```
Hotel/
├── admin/
│   └── routes.py                          # Updated with UPI handling
├── orders/
│   └── table_routes.py                    # Updated to pass UPI data
├── templates/
│   ├── admin/
│   │   ├── create_hotel.html             # Added UPI fields
│   │   └── all_hotels.html               # Added UPI edit capability
│   └── table_menu.html                    # Added UPI payment modal
├── static/
│   └── uploads/
│       └── hotel_qr/                      # QR code storage folder
└── scripts/
    └── migrations/
        └── add_hotel_upi_payment.py       # Database migration
```

### Database Schema
```sql
hotels table:
- upi_id VARCHAR(100) NULL
- upi_qr_image VARCHAR(255) NULL
```

### UPI Link Format
```
upi://pay?pa=<upi_id>&pn=<hotel_name>&am=<amount>&cu=INR
```

Example:
```
upi://pay?pa=hotel@paytm&pn=Grand%20Hotel&am=1250.50&cu=INR
```

### File Naming Convention
QR images are stored with hotel ID:
```
qr_hotel_1.png
qr_hotel_2.jpg
qr_hotel_3.jpeg
```

## 🔍 Troubleshooting

### Issue: Python not found

**Solution**: Use the batch file or run SQL manually
```bash
# Windows
Hotel\run_python.bat scripts\migrations\add_hotel_upi_payment.py

# Or run SQL directly in MySQL
```

### Issue: Migration already run

**Message**: "✅ UPI payment columns already exist. Skipping migration."

**Solution**: This is normal. The columns are already added. No action needed.

### Issue: QR image not displaying

**Check**:
1. File exists in `Hotel/static/uploads/hotel_qr/`
2. Filename matches database entry
3. File permissions allow reading
4. Flask static file serving is working

### Issue: UPI link not opening

**Check**:
1. UPI ID format is correct (identifier@bank)
2. Guest has UPI app installed
3. Browser allows opening external apps
4. Try on mobile device (UPI apps are mobile-only)

### Issue: File upload fails

**Check**:
1. Folder `Hotel/static/uploads/hotel_qr/` exists
2. Folder has write permissions
3. File size is under 2MB
4. File format is PNG, JPG, or JPEG

## 📊 Testing Checklist

### Admin Panel Testing
- [ ] Create hotel with UPI ID only
- [ ] Create hotel with UPI ID and QR code
- [ ] Create hotel without UPI configuration
- [ ] Edit hotel to add UPI ID
- [ ] Edit hotel to upload QR code
- [ ] Edit hotel to replace existing QR code
- [ ] Edit hotel to remove QR code
- [ ] Verify QR image displays in edit modal

### Guest Payment Testing
- [ ] Test payment with QR code (Case A)
- [ ] Test payment with UPI ID only (Case B)
- [ ] Test payment with no UPI config (Case C)
- [ ] Verify QR modal displays correctly
- [ ] Verify UPI link opens UPI app
- [ ] Verify payment confirmation works
- [ ] Test on mobile device
- [ ] Test with different UPI apps

## 🎯 Best Practices

### For Hotel Admins
1. **UPI ID Format**: Use format `identifier@bank`
   - Examples: `hotel@paytm`, `9876543210@ybl`, `hotel@okaxis`
2. **QR Code Quality**: Upload clear, high-resolution QR codes
3. **QR Code Size**: Keep under 2MB for fast loading
4. **Testing**: Test UPI payment before going live
5. **Backup**: Keep original QR code file as backup

### For Developers
1. **Security**: QR images are stored with secure filenames
2. **Validation**: UPI ID format should be validated
3. **Error Handling**: All file operations have error handling
4. **Cleanup**: Old QR files are deleted when replaced
5. **Logging**: Errors are logged for debugging

## 📝 API Endpoints

### Admin Endpoints
- `POST /admin/create-hotel` - Create hotel with UPI config
- `POST /admin/api/update-hotel` - Update hotel UPI config
- `GET /admin/all-hotels` - List hotels with UPI info

### Guest Endpoints
- `GET /orders/menu/<table_id>` - Get menu with UPI data
- `POST /orders/api/process-payment` - Process payment

## 🔐 Security Considerations

1. **File Upload**: Only PNG, JPG, JPEG allowed
2. **File Size**: Limited to 2MB
3. **Secure Filenames**: Using `secure_filename()` from Werkzeug
4. **Path Traversal**: Prevented by secure filename generation
5. **Access Control**: Only admins can configure UPI settings
6. **Payment Verification**: Manual confirmation required from guest

## 📞 Support

For issues or questions:
1. Check this documentation
2. Review error logs in Flask console
3. Run diagnostic: Check if columns exist in database
4. Verify file permissions on upload folder
5. Contact development team

---

**Implementation Date**: March 2026  
**Version**: 1.0  
**Status**: ✅ Complete and Ready for Testing
