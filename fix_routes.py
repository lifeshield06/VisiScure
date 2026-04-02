path = 'guest_verification/routes.py'
with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Line 781 is index 780 — fix it
for i, line in enumerate(lines):
    if "kyc_status': kyc_status, 'message': message})" in line and "pan_number" in line:
        lines[i] = "                    'kyc_status': kyc_status, 'message': message})\n"
        print(f"Fixed line {i+1}")
    # Remove the orphan invalid_format line right after
    if "'Invalid PAN format. Expected: ABCDE1234F'" in line and "return jsonify" in line and i > 0:
        if "pan_number" not in lines[i-1]:  # only remove if not part of real code
            lines[i] = ''
            print(f"Removed orphan line {i+1}")

with open(path, 'w', encoding='utf-8') as f:
    f.writelines(lines)
print("Done")
