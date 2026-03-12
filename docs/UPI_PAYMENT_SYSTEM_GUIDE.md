# UPI Payment System - Implementation Guide

## Overview

The VisiScure Order system now supports hotel-specific UPI payments. Each hotel can configure their own UPI ID and/or QR code, allowing guests to pay directly through UPI apps (Google Pay, PhonePe, Paytm, etc.).

## Features

### Three Payment Modes

The system intelligently determines the payment mode based on available configuration:

1. **QR Code Display Mode**
   - Triggered when: Hotel has uploaded a UPI QR code image
   - Behavior: Shows a modal with the QR code, UPI ID, and bill amount
   - Guest action: Scan QR code with any UPI app and complete payment

2. **UPI Deep Link Mode**
   - Triggered when: Hotel has only configured UPI ID (no QR code)
   - Behavior: Generates and opens a UPI deep link
   - Guest action: Select UPI app from system prompt and complete payment

3. **Unavailable Mode**
   - Triggered when: Hotel has not configured any UPI payment details
   - Behavior: Shows message to use cash payment
   - Guest action: Pay with cash

## Architecture

### Database Schema

```sql
-- hotels table columns
upi_id VARCHAR(100) NULL          -- UPI ID (e.g., 9876543210@paytm)
upi_qr_image VARCHAR(255) NULL    -- QR code filename (e.g., hotel_1_qr.png)
```

### File Structure

```
Hotel/
├── payment/
│   ├── upi_utils.py              # UPI validation and link generation
│   └── __init__.py
├── orders/
│   └── table_routes.py           # Payment API endpoints
├── templates/
│   └── table_menu.html           # Guest payment UI
├── static/
│   └── uploads/
│       └── hotel_qr/             # QR code storage directory
└── scripts/
    ├── migrations/
    │   ├── add_hotel_upi_payment.py
    │   └── verify_upi_schema.py
    └── utils/
        └── test_upi_payment_system.py
```

## Implementation Details

### Backend Components

#### 1. UPI Utilities (`payment/upi_utils.py`)

**validate_upi_id(upi_id: str) -> bool**
- Validates UPI ID format using regex
- Pattern: `[identifier]@[bank]`
- Example: `9876543210@paytm`, `user@okaxis`

**generate_upi_payment_link(upi_id: str, hotel_name: str, amount: float) -> str**
- Generates UPI deep link following UPI specification
- Format: `upi://pay?pa={upi_id}&pn={hotel_name}&am={amount}&cu=INR`
- URL encodes parameters
- Formats amount to 2 decimal places

**allowed_qr_file(filename: str) -> bool**
- Validates QR image file extensions
- Allowed: png, jpg, jpeg

#### 2. Payment API Endpoints (`orders/table_routes.py`)

**GET /orders/api/get-payment-info**
- Fetches hotel UPI configuration
- Parameters: `hotel_id` (query param)
- Returns: `{success, upi_id, upi_qr_image, hotel_name}`

**POST /orders/api/process-payment**
- Processes payment and updates bill status
- Parameters: `{table_id, guest_name, payment_method, tip_amount}`
- Marks bill as PAID and releases table

#### 3. Table Menu Route (`orders/table_routes.py`)

**GET /menu/<int:table_id>**
- Renders guest menu page
- Fetches hotel UPI configuration from database
- Passes `upi_id`, `upi_qr_image`, `hotel_name` to template

### Frontend Components

#### 1. Payment Processing (`table_menu.html`)

**JavaScript Variables**
```javascript
const hotelUPIId = "{{ upi_id or '' }}";
const hotelUPIQRImage = "{{ upi_qr_image or '' }}";
const hotelName = "{{ hotel_name or 'Restaurant' }}";
```

**processPayment(method)**
- Main payment handler
- Implements three-case logic for UPI payments
- Handles cash payments directly

**generateUPILink(upiId, payeeName, amount)**
- Client-side UPI link generation
- Matches backend specification
- URL encodes parameters

**showUPIQRModal(amount)**
- Displays QR code modal
- Shows UPI ID and amount
- Provides payment confirmation button

**confirmUPIPayment()**
- Confirms payment completion
- Calls backend to process payment
- Updates bill status

#### 2. UI Modals

**UPI QR Modal**
- Displays QR code image
- Shows UPI ID and bill amount
- "I've Completed the Payment" button

**Payment Modal**
- Shows bill amount and tip section
- Cash and UPI payment options
- Calculates grand total with tip

## Payment Flow

### Guest Payment Journey

1. **Guest places order**
   - Adds items to cart
   - Reviews order
   - Clicks "Pay Now"

2. **Payment modal opens**
   - Shows bill amount
   - Optional tip section
   - Payment method selection (Cash/UPI)

3. **Guest selects UPI**
   - System checks hotel configuration
   - Determines payment mode

4. **Mode A: QR Code Display**
   ```
   → QR modal opens
   → Guest scans QR with UPI app
   → Guest completes payment in app
   → Guest clicks "I've Completed the Payment"
   → System processes payment
   → Success message shown
   ```

5. **Mode B: UPI Deep Link**
   ```
   → UPI link generated
   → System opens UPI app selector
   → Guest selects app (GPay/PhonePe/etc)
   → Guest completes payment in app
   → Confirmation dialog appears
   → Guest confirms payment
   → System processes payment
   → Success message shown
   ```

6. **Mode C: Unavailable**
   ```
   → Alert shown: "UPI not available, use Cash"
   → Guest selects Cash payment
   → Payment processed
   ```

### Backend Payment Processing

1. **Receive payment request**
   - Validate table_id and guest_name
   - Find open bill for table

2. **Process payment atomically**
   - Update bill status to PAID
   - Update bill payment_method
   - Add tip amount if provided
   - Update table status to AVAILABLE
   - Remove from active_tables

3. **Return success response**
   - Clear guest session
   - Show success message
   - Hide bill button

## Admin Configuration

### Setting Up UPI Payment

1. **Navigate to Hotel Edit Panel**
   - Login as admin
   - Go to Hotels section
   - Click Edit on desired hotel

2. **Configure UPI ID**
   - Enter valid UPI ID (e.g., `9876543210@paytm`)
   - System validates format on save

3. **Upload QR Code (Optional)**
   - Click "Choose File" for QR upload
   - Select PNG/JPG/JPEG image
   - System validates file type
   - QR saved to `static/uploads/hotel_qr/`

4. **Save Configuration**
   - Click Save
   - System validates and stores configuration
   - Configuration immediately available for guests

### Updating UPI Configuration

- **Change UPI ID**: Edit and save new UPI ID
- **Replace QR Code**: Upload new QR (old one deleted automatically)
- **Remove QR Code**: Delete QR file (falls back to UPI link mode)
- **Remove All**: Clear both fields (payment unavailable)

## Testing

### Running Tests

```bash
# Test UPI payment system
python Hotel/scripts/utils/test_upi_payment_system.py

# Verify database schema
python Hotel/scripts/migrations/verify_upi_schema.py

# Verify upload directory
python Hotel/scripts/migrations/verify_upload_directory.py
```

### Test Coverage

1. **UPI ID Validation**
   - Valid formats
   - Invalid formats
   - Edge cases (empty, null)

2. **UPI Link Generation**
   - Correct format
   - URL encoding
   - Amount formatting
   - Parameter presence

3. **QR File Validation**
   - Allowed extensions
   - Disallowed extensions
   - Edge cases

4. **Database Schema**
   - Column existence
   - Column types
   - NULL constraints

5. **Payment Modes**
   - QR display logic
   - UPI link logic
   - Unavailable logic

### Manual Testing Checklist

- [ ] Admin can configure UPI ID
- [ ] Admin can upload QR code
- [ ] Admin can update UPI configuration
- [ ] Guest sees QR modal when QR exists
- [ ] Guest can scan and pay via QR
- [ ] Guest sees UPI link when only UPI ID exists
- [ ] UPI link opens correct app
- [ ] Guest sees unavailable message when no config
- [ ] Payment processes correctly for all modes
- [ ] Bill status updates to PAID
- [ ] Table releases after payment
- [ ] Tip amount adds correctly

## Security Considerations

### File Upload Security

- **File type validation**: Only PNG/JPG/JPEG allowed
- **Secure filename**: Uses `werkzeug.utils.secure_filename`
- **File size limits**: Enforced by Flask configuration
- **Directory permissions**: Upload directory has proper permissions

### Payment Security

- **No payment processing**: System doesn't handle actual money transfer
- **UPI app handles payment**: Secure payment through official UPI apps
- **Confirmation required**: Guest must confirm payment completion
- **Atomic transactions**: Database updates are atomic

### Data Validation

- **UPI ID format**: Validated with regex before saving
- **Amount validation**: Positive numbers only, formatted to 2 decimals
- **SQL injection prevention**: Parameterized queries used throughout
- **XSS prevention**: Template escaping enabled

## Troubleshooting

### Common Issues

**Issue: QR code not displaying**
- Check if file exists in `static/uploads/hotel_qr/`
- Verify filename matches database entry
- Check file permissions
- Verify image format (PNG/JPG/JPEG)

**Issue: UPI link not opening**
- Verify UPI ID format is correct
- Check if device has UPI apps installed
- Test link format manually
- Verify browser allows `upi://` protocol

**Issue: Payment not processing**
- Check database connection
- Verify bill exists and is OPEN
- Check table_id and guest_name match
- Review server logs for errors

**Issue: Configuration not saving**
- Verify database schema is up to date
- Check file upload permissions
- Review validation errors
- Check server logs

### Debug Mode

Enable debug logging in `table_routes.py`:

```python
print(f"[PAYMENT] Processing payment for table_id={table_id}")
print(f"[PAYMENT] UPI config: upi_id={upi_id}, qr={upi_qr_image}")
```

## Future Enhancements

### Potential Improvements

1. **Payment Verification**
   - Integrate with UPI payment gateway
   - Automatic payment verification
   - Real-time payment status updates

2. **QR Code Generation**
   - Auto-generate QR from UPI ID
   - Dynamic QR with amount embedded
   - QR code customization

3. **Payment Analytics**
   - Track UPI vs Cash payments
   - Payment success rates
   - Average payment times

4. **Multi-Payment Support**
   - Split payments
   - Partial payments
   - Group payments

5. **Enhanced Security**
   - Payment OTP verification
   - Transaction ID tracking
   - Payment receipt generation

## Support

For issues or questions:
- Check server logs: `Hotel/logs/`
- Review database: Check `hotels` table
- Test utilities: Run test scripts
- Documentation: This guide and inline code comments

## Version History

- **v1.0** (Current): Initial UPI payment implementation
  - Three payment modes
  - Admin configuration
  - Guest payment flow
  - Database schema
  - Test suite
