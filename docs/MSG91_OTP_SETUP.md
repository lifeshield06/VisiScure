# MSG91 OTP Integration Setup Guide

## Overview
This guide explains the MSG91 OTP integration for VisiScure Order guest verification system.

## Configuration

### Environment Variables (.env)
```env
SMS_ENABLED=true
MSG91_AUTH_KEY=451618A0Y44msLOxW685a4c6aP1
MSG91_TEMPLATE_ID=1407177312988404171
MSG91_SENDER_ID=VisScu
```

### MSG91 Template
**Template Name:** VISSCU_OTP_TEMPLATE

**SMS Format:**
```
Welcome to {{hotel_name}}!
Your verification OTP is {{OTP}}.
Please enter this code to complete guest verification.
– VisiScure Order
```

## Setup Steps

### 1. Database Setup
Run the migration to create the OTP table:
```bash
python Hotel/scripts/migrations/create_guest_otp_table.py
```

### 2. Test MSG91 Integration
Test the OTP sending functionality:
```bash
python Hotel/scripts/sms/test_msg91_integration.py
```

### 3. Start the Application
```bash
cd Hotel
python app.py
```

## API Endpoints

### Send OTP
**Endpoint:** `POST /guest-verification/api/send-otp`

**Request:**
```json
{
  "phone_number": "9876543210",
  "hotel_id": 1
}
```

**Response:**
```json
{
  "success": true,
  "message": "OTP sent successfully to your mobile number",
  "otp_debug": "123456"
}
```

### Verify OTP
**Endpoint:** `POST /guest-verification/api/verify-otp`

**Request:**
```json
{
  "phone_number": "9876543210",
  "otp_code": "123456"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Phone number verified successfully!"
}
```

## Features

✅ OTP sent via MSG91 API
✅ 6-digit OTP generation
✅ 5-minute OTP expiry
✅ 3 verification attempts
✅ 30-second resend cooldown
✅ Dynamic hotel name in SMS
✅ Phone number validation
✅ Frontend with countdown timer
✅ Verified badge display

## Testing

1. Open guest verification form: `http://localhost:5000/guest-verification/form/{manager_id}?hotel_id={hotel_id}`
2. Enter 10-digit mobile number
3. Click "Send OTP"
4. Check your phone for the OTP
5. Enter the 6-digit OTP
6. Click "Verify"
7. Submit the form

## Troubleshooting

### OTP not received
- Check MSG91 dashboard for delivery status
- Verify AUTH_KEY and TEMPLATE_ID are correct
- Check phone number format (10 digits, no country code in input)
- Ensure SMS_ENABLED=true in .env

### API errors
- Check console logs for detailed error messages
- Verify internet connection
- Check MSG91 account balance

## Files Modified

1. `Hotel/guest_verification/otp_service.py` - MSG91 API integration
2. `Hotel/.env` - MSG91 credentials
3. `Hotel/config.py` - Configuration defaults
4. `Hotel/templates/guest_verification_form.html` - Frontend (already implemented)
5. `Hotel/guest_verification/routes.py` - API endpoints (already implemented)

## Support

For MSG91 support: https://msg91.com/help
For VisiScure Order support: Contact your system administrator
