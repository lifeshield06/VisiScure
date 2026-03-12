# MSG91 OTP Troubleshooting Guide

## Current Status
✅ MSG91 integration is fully implemented with comprehensive debugging
✅ OTP is generated and logged in Flask console for testing
❌ SMS delivery is not working - needs MSG91 account verification

## Quick Test
Run this command to test MSG91 API directly:
```bash
python Hotel/scripts/sms/test_msg91_comprehensive.py 7722021558
```

## Check Flask Console
When you click "Send OTP" in the app, check the Flask console for detailed logs:
- Request details (phone number, auth key, template ID)
- MSG91 API response
- Debug OTP (printed for testing)

## Common Issues & Solutions

### 1. Template Not Approved
**Symptom:** MSG91 returns error about template
**Solution:**
1. Login to MSG91: https://control.msg91.com/
2. Go to: SMS → Templates
3. Find: VISSCU_OTP_TEMPLATE (ID: 1407177312988404171)
4. Status should be: **APPROVED**
5. If not approved, submit for approval

### 2. Insufficient Credits
**Symptom:** MSG91 returns error about balance/credits
**Solution:**
1. Login to MSG91: https://control.msg91.com/
2. Go to: Wallet
3. Check SMS credits balance
4. Add credits if needed

### 3. Incorrect Auth Key
**Symptom:** 401 Unauthorized error
**Solution:**
1. Login to MSG91: https://control.msg91.com/
2. Go to: Settings → API Keys
3. Verify auth key: `69b244d394b176db2203e483`
4. Update in `Hotel/config.py` if different

### 4. Test Mode / DLT Registration
**Symptom:** OTP works for some numbers but not others
**Solution:**
1. Check if MSG91 account is in test mode
2. Add your phone number as a test number
3. For production: Complete DLT registration (India requirement)

## Testing Without SMS
The system is designed to work even if SMS fails:
- OTP is always printed in Flask console
- Look for: `[OTP DEBUG] Phone: XXXXXXXXXX, OTP: 123456`
- Use this OTP to test the verification flow

## Next Steps
1. Run the test script: `python Hotel/scripts/sms/test_msg91_comprehensive.py 7722021558`
2. Check the detailed output for specific error messages
3. Follow the solutions for the specific error you see
4. If still not working, check MSG91 dashboard for account status
