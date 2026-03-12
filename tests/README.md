# VisiScure Order - Test Files

This folder contains test files and HTML test pages for the VisiScure Order system.

## 📁 Test Files

### HTML Test Pages

- **[test_layout.html](test_layout.html)** - Layout and UI component testing page
- **[test_voice_playback.html](test_voice_playback.html)** - Voice notification playback testing

## 🧪 Running Tests

### HTML Test Pages

To test HTML pages:

1. **Start the Flask server**
   ```bash
   python app.py
   ```

2. **Open test pages in browser**
   - Layout test: `http://localhost:5000/tests/test_layout.html`
   - Voice test: `http://localhost:5000/tests/test_voice_playback.html`

### Python Test Scripts

Python test scripts are located in `../scripts/utils/`:

```bash
# Test waiter assignments
python scripts/utils/check_waiter_assignments.py

# Verify kitchen system
python scripts/utils/verify_kitchen_system.py

# Check wallet balance
python scripts/utils/check_wallet.py

# Verify all features
python scripts/utils/verify_system_features.py
```

### SMS/OTP Testing

SMS test scripts are in `../scripts/sms/`:

```bash
# Verify SMS configuration
python scripts/sms/verify_production_setup.py

# Test MSG91 API directly
python scripts/sms/test_msg91_direct.py

# Test complete OTP flow
python scripts/sms/send_test_sms.py
```

## 📝 Test Coverage

### Current Test Areas

- ✅ Layout and UI components
- ✅ Voice notification playback
- ✅ Waiter call system
- ✅ Tip distribution
- ✅ SMS/OTP functionality
- ✅ Kitchen order routing
- ✅ Wallet operations

### Adding New Tests

To add new test files:

1. Create test file in this folder
2. Follow naming convention: `test_*.html` or `test_*.py`
3. Document the test in this README
4. Add test instructions

## 🔍 Test Utilities

### Diagnostic Scripts

Located in `../scripts/utils/`:

- `check_and_assign_waiter.py` - Waiter assignment verification
- `check_bill_status.py` - Bill status checking
- `check_today_verifications.py` - Daily verification stats
- `debug_kitchen_orders.py` - Kitchen order debugging
- `debug_waiter_calls.py` - Waiter call debugging

### Setup Scripts

Located in `../scripts/setup/`:

- `create_test_kitchen.py` - Create test kitchen
- `create_waiter_login.py` - Create test waiter account
- `setup_tip_distribution.py` - Setup tip distribution system

## 📊 Test Results

Test results and validation reports are documented in:
- `../docs/VOICE_TEST_RESULTS.md` - Voice system test results

## 🆘 Troubleshooting Tests

If tests fail:

1. Check Flask server is running
2. Verify database connection
3. Check environment variables in `.env`
4. Review Flask console logs
5. Run diagnostic scripts

---

**Last Updated**: March 2026  
**Maintained By**: VisiScure Order Development Team
