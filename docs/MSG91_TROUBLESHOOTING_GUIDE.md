# MSG91 OTP Not Receiving - Troubleshooting Guide

## ✅ API Status: WORKING
The MSG91 API is responding successfully with `{"type":"success"}` responses.

## 🔍 Why OTP May Not Be Delivered to Phone

### 1. **DND (Do Not Disturb) Settings**
- If your number is on DND, promotional SMS may be blocked
- **Solution**: Check with your telecom provider or disable DND

### 2. **Template Not Approved**
- MSG91 templates need DLT (Distributed Ledger Technology) approval
- **Check**: Login to MSG91 dashboard → Templates → Check status
- **Status should be**: "Approved" or "Active"

### 3. **Sender ID Not Approved**
- Sender ID "VisScu" must be approved by MSG91
- **Check**: MSG91 dashboard → Sender IDs → Verify "VisScu" status

### 4. **Insufficient MSG91 Credits**
- Your MSG91 account may be out of credits
- **Check**: MSG91 dashboard → Wallet/Credits
- **Solution**: Recharge your MSG91 account

### 5. **Template Variables Mismatch**
- Template variables must match exactly
- **Your template uses**: `{{hotel_name}}` and `{{OTP}}`
- **Code sends**: `hotel_name` and `OTP`
- **Status**: ✅ Correct

### 6. **Phone Number Format**
- Must be in format: 91XXXXXXXXXX (country code + 10 digits)
- **Current format**: ✅ Correct (917722021558)

### 7. **Network/Carrier Issues**
- Some carriers have delays in SMS delivery
- **Wait time**: 1-5 minutes
- **Solution**: Try different phone number or carrier

## 🧪 Testing Steps

### Step 1: Check MSG91 Dashboard
1. Login to https://control.msg91.com/
2. Go to "Reports" → "SMS Logs"
3. Check if OTP was sent (look for request_id)
4. Check delivery status

### Step 2: Verify Template
1. Go to "Templates" section
2. Find template ID: `1407177312988404171`
3. Verify status is "Approved"
4. Check template content matches:
```
Welcome to {{hotel_name}}!
Your verification OTP is {{OTP}}.
Please enter this code to complete guest verification.
– VisiScure Order
```

### Step 3: Check Credits
1. Go to "Wallet" or "Credits" section
2. Ensure you have sufficient balance
3. Minimum required: ₹0.20 per SMS

### Step 4: Test with Different Number
1. Try with a different mobile number
2. Try with a number from different carrier (Airtel, Jio, Vi)
3. Try with a non-DND number

### Step 5: Check Sender ID
1. Go to "Sender IDs" section
2. Verify "VisScu" is approved
3. If not approved, use default sender ID or request approval

## 🔧 Quick Fixes

### Fix 1: Use Test Mode (Development)
The OTP is printed in console logs for testing:
```
[OTP DEBUG] Phone: 7722021558, OTP: 123456
```
Use this OTP from console to test the verification flow.

### Fix 2: Check Flask Console
When you click "Send OTP", check the Flask console for:
```
[MSG91] ✅ OTP sent successfully to 917722021558
[MSG91] Request ID: 36636c70704a614b6a794535
```

### Fix 3: Verify in MSG91 Dashboard
1. Copy the `request_id` from console
2. Search in MSG91 dashboard SMS logs
3. Check delivery status

### Fix 4: Contact MSG91 Support
If API shows success but SMS not delivered:
1. Email: support@msg91.com
2. Provide: request_id, phone number, timestamp
3. They can check delivery status on their end

## 📱 Common MSG91 Response Codes

| Response | Meaning | Action |
|----------|---------|--------|
| `{"type":"success"}` | API accepted request | Check delivery in dashboard |
| `{"type":"error","message":"..."}` | API error | Check error message |
| Status 401 | Invalid auth key | Verify MSG91_AUTH_KEY |
| Status 400 | Bad request | Check phone format |

## ✅ Current Implementation Status

- ✅ MSG91 API integration working
- ✅ API returning success responses
- ✅ Phone number format correct
- ✅ Template variables correct
- ✅ OTP generation working
- ✅ Database storage working
- ⚠️ SMS delivery depends on MSG91 account setup

## 🎯 Next Steps

1. **Check MSG91 Dashboard** - Verify template approval and credits
2. **Test with Console OTP** - Use OTP from console logs for testing
3. **Contact MSG91 Support** - If dashboard shows delivered but not received
4. **Try Different Number** - Test with non-DND number

## 📞 MSG91 Support

- Website: https://msg91.com/help
- Email: support@msg91.com
- Phone: Check MSG91 website for support number
- Dashboard: https://control.msg91.com/

## 💡 Pro Tip

For development/testing, you can use the OTP printed in console logs:
```python
print(f"[OTP DEBUG] Phone: {original_phone}, OTP: {otp_code}")
```

This allows you to test the complete verification flow even if SMS delivery has issues.
