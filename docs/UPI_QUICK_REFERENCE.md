# UPI Payment System - Quick Reference

## For Developers

### Key Files

```
Hotel/payment/upi_utils.py          # UPI validation & link generation
Hotel/orders/table_routes.py        # Payment API endpoints
Hotel/templates/table_menu.html     # Guest payment UI
Hotel/static/uploads/hotel_qr/      # QR code storage
```

### API Endpoints

#### Get Payment Info
```http
GET /orders/api/get-payment-info?hotel_id=1
```
Response:
```json
{
  "success": true,
  "upi_id": "9876543210@paytm",
  "upi_qr_image": "hotel_1_qr.png",
  "hotel_name": "Grand Hotel"
}
```

#### Process Payment
```http
POST /orders/api/process-payment
Content-Type: application/json

{
  "table_id": 1,
  "guest_name": "John Doe",
  "payment_method": "UPI",
  "tip_amount": 50.00
}
```
Response:
```json
{
  "success": true,
  "message": "Payment successful! Thank you for dining with us."
}
```

### UPI Utility Functions

```python
from payment.upi_utils import validate_upi_id, generate_upi_payment_link

# Validate UPI ID
is_valid = validate_upi_id("9876543210@paytm")  # Returns True

# Generate UPI link
link = generate_upi_payment_link(
    upi_id="9876543210@paytm",
    hotel_name="Grand Hotel",
    amount=1250.50
)
# Returns: upi://pay?pa=9876543210%40paytm&pn=Grand+Hotel&am=1250.50&cu=INR
```

### JavaScript Functions

```javascript
// Process payment (handles all three modes)
processPayment('UPI');

// Generate UPI link
const link = generateUPILink(upiId, hotelName, amount);

// Show QR modal
showUPIQRModal(amount);

// Confirm UPI payment
confirmUPIPayment();
```

### Payment Mode Logic

```javascript
if (hotelUPIQRImage && hotelUPIQRImage.trim() !== '') {
    // Mode A: Show QR modal
    showUPIQRModal(grandTotal);
} else if (hotelUPIId && hotelUPIId.trim() !== '') {
    // Mode B: Generate and open UPI link
    const upiLink = generateUPILink(hotelUPIId, hotelName, grandTotal);
    window.location.href = upiLink;
} else {
    // Mode C: UPI unavailable
    alert('UPI payment is not available. Please use Cash.');
}
```

### Database Queries

```sql
-- Get hotel UPI configuration
SELECT upi_id, upi_qr_image, hotel_name 
FROM hotels 
WHERE id = ?;

-- Update hotel UPI configuration
UPDATE hotels 
SET upi_id = ?, upi_qr_image = ? 
WHERE id = ?;

-- Check if hotel has UPI configured
SELECT 
    CASE 
        WHEN upi_qr_image IS NOT NULL THEN 'QR_DISPLAY'
        WHEN upi_id IS NOT NULL THEN 'UPI_LINK'
        ELSE 'UNAVAILABLE'
    END as payment_mode
FROM hotels 
WHERE id = ?;
```

### Testing Commands

```bash
# Run full test suite
python Hotel/scripts/utils/test_upi_payment_system.py

# Verify schema
python Hotel/scripts/migrations/verify_upi_schema.py

# Test UPI validation
python -c "from payment.upi_utils import validate_upi_id; print(validate_upi_id('test@paytm'))"

# Test link generation
python -c "from payment.upi_utils import generate_upi_payment_link; print(generate_upi_payment_link('test@paytm', 'Hotel', 100))"
```

### Common Patterns

#### Admin: Save UPI Configuration
```python
# In admin/routes.py
upi_id = request.form.get('upi_id', '').strip()
upi_qr_file = request.files.get('upi_qr_image')

# Validate UPI ID
if upi_id and not validate_upi_id(upi_id):
    return jsonify({"success": False, "message": "Invalid UPI ID format"})

# Validate and save QR file
if upi_qr_file and upi_qr_file.filename:
    if not allowed_qr_file(upi_qr_file.filename):
        return jsonify({"success": False, "message": "Invalid file type"})
    
    filename = secure_filename(upi_qr_file.filename)
    # Save file and update database
```

#### Guest: Fetch Payment Info
```javascript
// In table_menu.html
fetch(`/orders/api/get-payment-info?hotel_id=${hotelId}`)
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            hotelUPIId = data.upi_id || '';
            hotelUPIQRImage = data.upi_qr_image || '';
            hotelName = data.hotel_name || 'Restaurant';
        }
    });
```

#### Guest: Process UPI Payment
```javascript
// In table_menu.html
fetch('/orders/api/process-payment', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        table_id: tableId,
        guest_name: guestName,
        payment_method: 'UPI',
        tip_amount: selectedTipAmount
    })
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        showPaymentSuccess();
    }
});
```

### Error Handling

```python
# Backend error handling
try:
    # Payment processing logic
    result = process_payment(...)
    return jsonify({"success": True, "message": "Payment successful"})
except Exception as e:
    print(f"[PAYMENT ERROR] {e}")
    import traceback
    traceback.print_exc()
    return jsonify({"success": False, "message": "Server error"})
```

```javascript
// Frontend error handling
fetch('/orders/api/process-payment', {...})
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showPaymentSuccess();
        } else {
            alert('Payment failed: ' + (data.message || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Payment error:', error);
        alert('Network error. Please try again.');
    });
```

### Configuration Examples

#### Hotel with QR Code
```json
{
  "hotel_id": 1,
  "upi_id": "9876543210@paytm",
  "upi_qr_image": "hotel_1_qr.png",
  "payment_mode": "QR_DISPLAY"
}
```

#### Hotel with UPI ID Only
```json
{
  "hotel_id": 2,
  "upi_id": "hotel@okaxis",
  "upi_qr_image": null,
  "payment_mode": "UPI_LINK"
}
```

#### Hotel without UPI
```json
{
  "hotel_id": 3,
  "upi_id": null,
  "upi_qr_image": null,
  "payment_mode": "UNAVAILABLE"
}
```

### UPI Link Format

```
upi://pay?pa={upi_id}&pn={payee_name}&am={amount}&cu=INR

Parameters:
- pa: Payee address (UPI ID)
- pn: Payee name (URL encoded)
- am: Amount (formatted to 2 decimals)
- cu: Currency (always INR)

Example:
upi://pay?pa=9876543210%40paytm&pn=Grand+Hotel&am=1250.50&cu=INR
```

### File Upload Configuration

```python
# Flask configuration
UPLOAD_FOLDER = 'static/uploads/hotel_qr/'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB

# File naming convention
filename = f"hotel_{hotel_id}_qr.{extension}"
```

### Security Checklist

- [ ] Validate UPI ID format before saving
- [ ] Validate file type for QR uploads
- [ ] Use secure_filename for file uploads
- [ ] Parameterized SQL queries
- [ ] Template escaping enabled
- [ ] Amount validation (positive, 2 decimals)
- [ ] Guest confirmation required
- [ ] Atomic database transactions

### Debugging Tips

1. **Check server logs** for payment processing errors
2. **Inspect network tab** for API request/response
3. **Console.log** UPI configuration variables
4. **Verify database** entries for hotel UPI config
5. **Test UPI link** manually in browser
6. **Check file permissions** for QR upload directory
7. **Run test suite** to verify all components

### Quick Fixes

**QR not showing:**
```bash
# Check file exists
ls -la Hotel/static/uploads/hotel_qr/

# Check database entry
mysql> SELECT upi_qr_image FROM hotels WHERE id = 1;
```

**UPI link not working:**
```javascript
// Test link generation
console.log(generateUPILink('test@paytm', 'Hotel', 100));
// Should output: upi://pay?pa=test%40paytm&pn=Hotel&am=100.00&cu=INR
```

**Payment not processing:**
```python
# Check bill status
SELECT * FROM bills WHERE table_id = 1 AND bill_status = 'OPEN';

# Check table status
SELECT * FROM tables WHERE id = 1;
```

## For Admins

### Setup Steps

1. Login to admin panel
2. Navigate to Hotels → Edit Hotel
3. Enter UPI ID (e.g., `9876543210@paytm`)
4. Upload QR code image (optional)
5. Click Save

### UPI ID Format

Valid formats:
- `9876543210@paytm`
- `hotel@okaxis`
- `user.name@ybl`
- `email@bank`

Invalid formats:
- `invalid` (no @ symbol)
- `@bank` (no identifier)
- `user@` (no bank)

### QR Code Requirements

- Format: PNG, JPG, or JPEG
- Size: Max 5MB
- Content: Valid UPI QR code
- Naming: Auto-generated as `hotel_{id}_qr.{ext}`

### Payment Modes

| Configuration | Mode | Guest Experience |
|--------------|------|------------------|
| UPI ID + QR | QR Display | Scan QR code |
| UPI ID only | UPI Link | Select UPI app |
| Neither | Unavailable | Use cash |

### Testing Payment

1. Create test order as guest
2. Click "Pay Now"
3. Select UPI payment
4. Verify correct mode appears
5. Complete test payment
6. Confirm bill status updates

## Support

- Documentation: `Hotel/docs/UPI_PAYMENT_SYSTEM_GUIDE.md`
- Test script: `Hotel/scripts/utils/test_upi_payment_system.py`
- Code: `Hotel/payment/upi_utils.py`
- API: `Hotel/orders/table_routes.py`
