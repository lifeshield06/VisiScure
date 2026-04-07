from database.db import get_db_connection
from mysql.connector import Error
from datetime import datetime


class HotelWallet:
    """Hotel Wallet Management - handles balance, charges, and transactions"""
    
    @staticmethod
    def create_tables():
        """Create wallet-related tables"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            # Create hotel_wallet table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hotel_wallet (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    hotel_id INT NOT NULL UNIQUE,
                    balance DECIMAL(10, 2) DEFAULT 0.00,
                    per_verification_charge DECIMAL(10, 2) DEFAULT 0.00,
                    per_order_charge DECIMAL(10, 2) DEFAULT 0.00,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (hotel_id) REFERENCES hotels(id) ON DELETE CASCADE
                )
            """)
            
            # Create wallet_transactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wallet_transactions (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    hotel_id INT NOT NULL,
                    transaction_type ENUM('CREDIT', 'DEBIT') NOT NULL,
                    amount DECIMAL(10, 2) NOT NULL,
                    balance_after DECIMAL(10, 2) NOT NULL,
                    utr_number VARCHAR(100),
                    reference_type ENUM('RECHARGE', 'VERIFICATION', 'ORDER', 'ADJUSTMENT') NOT NULL,
                    reference_id INT,
                    created_by_type ENUM('ADMIN', 'MANAGER', 'SYSTEM') NOT NULL,
                    created_by_id INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (hotel_id) REFERENCES hotels(id) ON DELETE CASCADE
                )
            """)
            
            # Add utr_number column if it doesn't exist (migration)
            cursor.execute("SHOW COLUMNS FROM wallet_transactions LIKE 'utr_number'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE wallet_transactions ADD COLUMN utr_number VARCHAR(100) AFTER balance_after")
            
            # Add razorpay_payment_id column if it doesn't exist (migration)
            cursor.execute("SHOW COLUMNS FROM wallet_transactions LIKE 'razorpay_payment_id'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE wallet_transactions ADD COLUMN razorpay_payment_id VARCHAR(100) AFTER utr_number")
            
            # Add razorpay_order_id column if it doesn't exist (migration)
            cursor.execute("SHOW COLUMNS FROM wallet_transactions LIKE 'razorpay_order_id'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE wallet_transactions ADD COLUMN razorpay_order_id VARCHAR(100) AFTER razorpay_payment_id")
            
            # Remove description column if it exists (migration)
            cursor.execute("SHOW COLUMNS FROM wallet_transactions LIKE 'description'")
            if cursor.fetchone():
                cursor.execute("ALTER TABLE wallet_transactions DROP COLUMN description")

            # Add bill-level charge-deduction flag if it doesn't exist
            # Used as an additional guard to prevent duplicate bill-charge deductions.
            cursor.execute("SHOW COLUMNS FROM bills LIKE 'is_charge_deducted'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE bills ADD COLUMN is_charge_deducted BOOLEAN DEFAULT FALSE")
            
            connection.commit()
            cursor.close()
            connection.close()
            print("Wallet tables created successfully")
            return True
        except Error as exc:
            print(f"Error creating wallet tables: {exc}")
            return False
    
    @staticmethod
    def create_wallet(hotel_id, per_verification_charge=0.00, per_order_charge=0.00):
        """Create a wallet for a new hotel"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor()
            
            cursor.execute("""
                INSERT INTO hotel_wallet (hotel_id, balance, per_verification_charge, per_order_charge)
                VALUES (%s, 0.00, %s, %s)
                ON DUPLICATE KEY UPDATE
                per_verification_charge = VALUES(per_verification_charge),
                per_order_charge = VALUES(per_order_charge)
            """, (hotel_id, per_verification_charge, per_order_charge))
            
            connection.commit()
            cursor.close()
            connection.close()
            return {'success': True, 'message': 'Wallet created successfully'}
        except Error as exc:
            print(f"Error creating wallet: {exc}")
            return {'success': False, 'message': f'Database error: {str(exc)}'}
    
    @staticmethod
    def get_wallet(hotel_id):
        """Get wallet details for a hotel"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT * FROM hotel_wallet WHERE hotel_id = %s
            """, (hotel_id,))
            
            wallet = cursor.fetchone()
            cursor.close()
            connection.close()
            
            if wallet:
                return {
                    'id': wallet['id'],
                    'hotel_id': wallet['hotel_id'],
                    'balance': float(wallet['balance']),
                    'per_verification_charge': float(wallet['per_verification_charge']),
                    'per_order_charge': float(wallet['per_order_charge']),
                    'created_at': wallet['created_at'],
                    'updated_at': wallet['updated_at']
                }
            return None
        except Error as exc:
            print(f"Error getting wallet: {exc}")
            return None
    
    @staticmethod
    def get_or_create_wallet(hotel_id):
        """Get wallet for a hotel, create if not exists (auto-create feature)"""
        try:
            # First try to get existing wallet
            wallet = HotelWallet.get_wallet(hotel_id)
            if wallet:
                return wallet
            
            # Wallet doesn't exist, create it with default charges (0)
            print(f"Auto-creating wallet for hotel_id: {hotel_id}")
            result = HotelWallet.create_wallet(
                hotel_id=hotel_id,
                per_verification_charge=0.0,
                per_order_charge=0.0
            )
            
            if result.get('success'):
                # Fetch and return the newly created wallet
                return HotelWallet.get_wallet(hotel_id)
            else:
                print(f"Failed to auto-create wallet: {result.get('message')}")
                return None
        except Error as exc:
            print(f"Error in get_or_create_wallet: {exc}")
            return None
    
    @staticmethod
    def get_all_wallets():
        """Get all hotel wallets with hotel details"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT 
                    hw.*,
                    h.hotel_name,
                    h.city
                FROM hotel_wallet hw
                JOIN hotels h ON hw.hotel_id = h.id
                ORDER BY h.hotel_name
            """)
            
            wallets = cursor.fetchall()
            cursor.close()
            connection.close()
            
            result = []
            for w in wallets:
                result.append({
                    'id': w['id'],
                    'hotel_id': w['hotel_id'],
                    'hotel_name': w['hotel_name'],
                    'city': w['city'],
                    'balance': float(w['balance']),
                    'per_verification_charge': float(w['per_verification_charge']),
                    'per_order_charge': float(w['per_order_charge']),
                    'updated_at': w['updated_at']
                })
            return result
        except Error as exc:
            print(f"Error getting all wallets: {exc}")
            return []
    
    @staticmethod
    def add_balance(hotel_id, amount, utr_number, created_by_type, created_by_id):
        """Add balance to hotel wallet with UTR number"""
        try:
            if amount <= 0:
                return {'success': False, 'message': 'Amount must be positive'}
            
            if not utr_number or not utr_number.strip():
                return {'success': False, 'message': 'UTR Number is required'}
            
            # Auto-create wallet if not exists
            wallet_check = HotelWallet.get_or_create_wallet(hotel_id)
            if not wallet_check:
                return {'success': False, 'message': 'Could not create or retrieve wallet'}
            
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Get current balance
            cursor.execute("SELECT balance FROM hotel_wallet WHERE hotel_id = %s FOR UPDATE", (hotel_id,))
            wallet = cursor.fetchone()
            
            if not wallet:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Wallet not found'}
            
            new_balance = float(wallet['balance']) + amount
            
            # Update balance
            cursor.execute("""
                UPDATE hotel_wallet SET balance = %s WHERE hotel_id = %s
            """, (new_balance, hotel_id))
            
            # Record transaction with UTR number
            cursor.execute("""
                INSERT INTO wallet_transactions 
                (hotel_id, transaction_type, amount, balance_after, utr_number, reference_type, created_by_type, created_by_id)
                VALUES (%s, 'CREDIT', %s, %s, %s, 'RECHARGE', %s, %s)
            """, (hotel_id, amount, new_balance, utr_number.strip(), created_by_type, created_by_id))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return {'success': True, 'message': 'Balance added successfully', 'new_balance': new_balance}
        except Error as exc:
            print(f"Error adding balance: {exc}")
            return {'success': False, 'message': f'Database error: {str(exc)}'}
    
    @staticmethod
    def add_balance_razorpay(hotel_id, amount, razorpay_payment_id, razorpay_order_id, created_by_type, created_by_id):
        """Add balance to hotel wallet via Razorpay payment"""
        try:
            if amount <= 0:
                return {'success': False, 'message': 'Amount must be positive'}
            
            if not razorpay_payment_id:
                return {'success': False, 'message': 'Razorpay Payment ID is required'}
            
            # Auto-create wallet if not exists
            wallet_check = HotelWallet.get_or_create_wallet(hotel_id)
            if not wallet_check:
                return {'success': False, 'message': 'Could not create or retrieve wallet'}
            
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Check if this payment ID was already processed (prevent duplicate credits)
            cursor.execute("""
                SELECT id FROM wallet_transactions WHERE razorpay_payment_id = %s
            """, (razorpay_payment_id,))
            if cursor.fetchone():
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'This payment has already been processed'}
            
            # Get current balance
            cursor.execute("SELECT balance FROM hotel_wallet WHERE hotel_id = %s FOR UPDATE", (hotel_id,))
            wallet = cursor.fetchone()
            
            if not wallet:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Wallet not found'}
            
            new_balance = float(wallet['balance']) + amount
            
            # Update balance
            cursor.execute("""
                UPDATE hotel_wallet SET balance = %s WHERE hotel_id = %s
            """, (new_balance, hotel_id))
            
            # Record transaction with Razorpay details
            cursor.execute("""
                INSERT INTO wallet_transactions 
                (hotel_id, transaction_type, amount, balance_after, razorpay_payment_id, razorpay_order_id, reference_type, created_by_type, created_by_id)
                VALUES (%s, 'CREDIT', %s, %s, %s, %s, 'RECHARGE', %s, %s)
            """, (hotel_id, amount, new_balance, razorpay_payment_id, razorpay_order_id, created_by_type, created_by_id))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return {'success': True, 'message': 'Balance added successfully via Razorpay', 'new_balance': new_balance}
        except Error as exc:
            print(f"Error adding balance via Razorpay: {exc}")
            return {'success': False, 'message': f'Database error: {str(exc)}'}
    
    @staticmethod
    def deduct_for_verification(hotel_id, verification_id):
        """Deduct charge for verification - returns success/failure"""
        try:
            print(f"[WALLET] deduct_for_verification called - hotel_id={hotel_id}, verification_id={verification_id}")
            
            # Auto-create wallet if not exists
            wallet_check = HotelWallet.get_or_create_wallet(hotel_id)
            if not wallet_check:
                print(f"[WALLET] Could not create or retrieve wallet for hotel_id={hotel_id}")
                return {'success': False, 'message': 'Could not create or retrieve wallet', 'insufficient_balance': False}
            
            print(f"[WALLET] Wallet found/created: {wallet_check}")
            
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Get wallet and charge
            cursor.execute("""
                SELECT balance, per_verification_charge FROM hotel_wallet WHERE hotel_id = %s FOR UPDATE
            """, (hotel_id,))
            wallet = cursor.fetchone()
            
            if not wallet:
                cursor.close()
                connection.close()
                print(f"[WALLET] Wallet not found in database for hotel_id={hotel_id}")
                return {'success': False, 'message': 'Wallet not found', 'insufficient_balance': False}
            
            charge = float(wallet['per_verification_charge'])
            current_balance = float(wallet['balance'])
            
            print(f"[WALLET] Current balance: ₹{current_balance}, Charge: ₹{charge}")
            
            # If charge is 0, allow without deduction
            if charge == 0:
                cursor.close()
                connection.close()
                print(f"[WALLET] No charge configured, skipping deduction")
                return {'success': True, 'message': 'No charge configured', 'deducted': 0}
            
            # Check sufficient balance
            if current_balance < charge:
                cursor.close()
                connection.close()
                print(f"[WALLET] Insufficient balance - Required: ₹{charge}, Available: ₹{current_balance}")
                return {
                    'success': False, 
                    'message': f'Insufficient wallet balance. Required: ₹{charge:.2f}, Available: ₹{current_balance:.2f}',
                    'insufficient_balance': True
                }
            
            new_balance = current_balance - charge
            
            print(f"[WALLET] Deducting ₹{charge}, New balance will be: ₹{new_balance}")
            
            # Update balance
            cursor.execute("""
                UPDATE hotel_wallet SET balance = %s WHERE hotel_id = %s
            """, (new_balance, hotel_id))
            
            # Record transaction (no description, system-generated)
            cursor.execute("""
                INSERT INTO wallet_transactions 
                (hotel_id, transaction_type, amount, balance_after, reference_type, reference_id, created_by_type)
                VALUES (%s, 'DEBIT', %s, %s, 'VERIFICATION', %s, 'SYSTEM')
            """, (hotel_id, charge, new_balance, verification_id))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            print(f"[WALLET] Deduction successful - ₹{charge} deducted, new balance: ₹{new_balance}")
            
            return {'success': True, 'message': 'Charge deducted successfully', 'deducted': charge, 'new_balance': new_balance}
        except Error as exc:
            print(f"[WALLET] Error deducting verification charge: {exc}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'message': f'Database error: {str(exc)}'}
    
    @staticmethod
    def deduct_for_order(hotel_id, order_id):
        """Deduct configured per-order charge for one order placement action."""
        try:
            # Auto-create wallet if not exists
            wallet_check = HotelWallet.get_or_create_wallet(hotel_id)
            if not wallet_check:
                return {'success': False, 'message': 'Could not create or retrieve wallet', 'insufficient_balance': False}
            
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            # Get wallet and charge
            cursor.execute("""
                SELECT balance, per_order_charge FROM hotel_wallet WHERE hotel_id = %s FOR UPDATE
            """, (hotel_id,))
            wallet = cursor.fetchone()
            
            if not wallet:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Wallet not found', 'insufficient_balance': False}
            
            per_order_charge = float(wallet['per_order_charge'])
            charge = per_order_charge
            current_balance = float(wallet['balance'])
            
            # If charge is 0, allow without deduction
            if charge == 0:
                cursor.close()
                connection.close()
                return {'success': True, 'message': 'No charge configured', 'deducted': 0}
            
            # Check sufficient balance
            if current_balance < charge:
                cursor.close()
                connection.close()
                return {
                    'success': False, 
                    'message': f'Insufficient wallet balance. Required: ₹{charge:.2f}, Available: ₹{current_balance:.2f}',
                    'insufficient_balance': True
                }
            
            new_balance = current_balance - charge
            
            # Update balance
            cursor.execute("""
                UPDATE hotel_wallet SET balance = %s WHERE hotel_id = %s
            """, (new_balance, hotel_id))
            
            # Record transaction (no description, system-generated)
            cursor.execute("""
                INSERT INTO wallet_transactions 
                (hotel_id, transaction_type, amount, balance_after, reference_type, reference_id, created_by_type)
                VALUES (%s, 'DEBIT', %s, %s, 'ORDER', %s, 'SYSTEM')
            """, (hotel_id, charge, new_balance, order_id))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return {
                'success': True,
                'message': f'₹{charge:.2f} deducted for order charges',
                'deducted': charge,
                'new_balance': new_balance,
                'components': {
                    'per_order_charge': per_order_charge
                },
                'reference_type': 'ORDER',
                'transaction_type': 'DEBIT'
            }
        except Error as exc:
            print(f"Error deducting order charge: {exc}")
            return {'success': False, 'message': f'Database error: {str(exc)}'}

    @staticmethod
    def deduct_order_charge_on_payment(hotel_id, bill_id, table_id=None, session_id=None, guest_name=None):
        """Deduct configured per guest-bill charge once when payment is completed.

        Rules:
        - Deduct only after bill payment is marked PAID
        - Deduct only once per bill (idempotent by bill_id transaction reference)
        - Deduct hotel_wallet.per_order_charge (fixed configured charge), not bill total
        - Record a single ORDER/DEBIT transaction per bill
        """
        try:
            wallet_check = HotelWallet.get_or_create_wallet(hotel_id)
            if not wallet_check:
                return {'success': False, 'message': 'Could not create or retrieve wallet', 'insufficient_balance': False}

            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)

            # Idempotency: prevent duplicate debits on retries/refreshes.
            cursor.execute("""
                SELECT id, amount, balance_after
                FROM wallet_transactions
                WHERE hotel_id = %s
                  AND transaction_type = 'DEBIT'
                  AND reference_type = 'ORDER'
                  AND reference_id = %s
                LIMIT 1
            """, (hotel_id, bill_id))
            existing_txn = cursor.fetchone()
            if existing_txn:
                cursor.close()
                connection.close()
                return {
                    'success': True,
                    'already_deducted': True,
                    'deducted': float(existing_txn.get('amount') or 0),
                    'new_balance': float(existing_txn.get('balance_after') or 0),
                    'message': 'Payment already settled in wallet for this bill',
                    'reference_type': 'ORDER',
                    'transaction_type': 'DEBIT'
                }

            # Deduct only after payment is successful.
            cursor.execute(
                """
                  SELECT id, payment_status, payment_method, bill_status, grand_total, total_amount,
                      COALESCE(is_charge_deducted, 0) as is_charge_deducted
                FROM bills
                WHERE id = %s
                LIMIT 1
                """,
                (bill_id,)
            )
            bill = cursor.fetchone()
            if not bill:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Bill not found for wallet settlement', 'insufficient_balance': False}

            if str(bill.get('payment_status') or '').upper() != 'PAID':
                cursor.close()
                connection.close()
                return {
                    'success': False,
                    'message': 'Payment is not completed yet. Wallet deduction is allowed only after successful payment.',
                    'insufficient_balance': False
                }

            if bool(bill.get('is_charge_deducted')):
                cursor.close()
                connection.close()
                return {
                    'success': True,
                    'already_deducted': True,
                    'deducted': 0.0,
                    'message': 'Bill charge already deducted for this bill',
                    'reference_type': 'ORDER',
                    'transaction_type': 'DEBIT'
                }

            cursor.execute("""
                SELECT balance, per_order_charge
                FROM hotel_wallet
                WHERE hotel_id = %s
                FOR UPDATE
            """, (hotel_id,))
            wallet = cursor.fetchone()

            if not wallet:
                cursor.close()
                connection.close()
                return {'success': False, 'message': 'Wallet not found', 'insufficient_balance': False}

            current_balance = float(wallet.get('balance') or 0)
            charge = round(float(wallet.get('per_order_charge') or 0), 2)

            if charge <= 0:
                cursor.close()
                connection.close()
                return {
                    'success': True,
                    'already_deducted': False,
                    'deducted': 0.0,
                    'message': 'Payment successful. No per guest bill charge configured for wallet deduction',
                    'reference_type': 'ORDER',
                    'transaction_type': 'DEBIT'
                }

            if current_balance < charge:
                cursor.close()
                connection.close()
                return {
                    'success': False,
                    'message': f'Insufficient wallet balance. Required: ₹{charge:.2f}, Available: ₹{current_balance:.2f}',
                    'insufficient_balance': True
                }

            new_balance = round(current_balance - charge, 2)

            cursor.execute("""
                UPDATE hotel_wallet
                SET balance = %s
                WHERE hotel_id = %s
            """, (new_balance, hotel_id))

            cursor.execute("""
                INSERT INTO wallet_transactions
                (hotel_id, transaction_type, amount, balance_after, reference_type, reference_id, created_by_type)
                VALUES (%s, 'DEBIT', %s, %s, 'ORDER', %s, 'SYSTEM')
            """, (hotel_id, charge, new_balance, bill_id))

            cursor.execute("""
                UPDATE bills
                SET is_charge_deducted = TRUE
                WHERE id = %s
            """, (bill_id,))

            if table_id and session_id:
                cursor.execute("""
                    UPDATE table_orders
                    SET charge_deducted = TRUE
                    WHERE table_id = %s AND session_id = %s AND payment_status = 'PAID'
                """, (table_id, session_id))
            elif table_id and guest_name:
                cursor.execute("""
                    UPDATE table_orders
                    SET charge_deducted = TRUE
                    WHERE table_id = %s AND guest_name = %s AND payment_status = 'PAID'
                """, (table_id, guest_name))

            connection.commit()
            cursor.close()
            connection.close()

            return {
                'success': True,
                'already_deducted': False,
                'deducted': charge,
                'new_balance': new_balance,
                'message': f'Payment successful. Per guest bill charge ₹{charge:.2f} deducted from wallet',
                'reference_type': 'ORDER',
                'transaction_type': 'DEBIT'
            }
        except Error as exc:
            print(f"Error deducting payment-time order charge: {exc}")
            return {'success': False, 'message': f'Database error: {str(exc)}'}
    
    @staticmethod
    def check_balance_for_verification(hotel_id):
        """Check if hotel has sufficient balance for verification"""
        try:
            # Auto-create wallet if not exists
            wallet_check = HotelWallet.get_or_create_wallet(hotel_id)
            if not wallet_check:
                return {'sufficient': True, 'message': 'Could not retrieve wallet, allowing operation'}
            
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT balance, per_verification_charge FROM hotel_wallet WHERE hotel_id = %s
            """, (hotel_id,))
            wallet = cursor.fetchone()
            cursor.close()
            connection.close()
            
            if not wallet:
                return {'sufficient': True, 'message': 'No wallet configured'}
            
            charge = float(wallet['per_verification_charge'])
            balance = float(wallet['balance'])
            
            if charge == 0:
                return {'sufficient': True, 'charge': 0, 'balance': balance}
            
            return {
                'sufficient': balance >= charge,
                'charge': charge,
                'balance': balance,
                'shortfall': max(0, charge - balance)
            }
        except Error as exc:
            print(f"Error checking balance: {exc}")
            return {'sufficient': True, 'message': 'Error checking balance'}
    
    @staticmethod
    def check_balance_for_order(hotel_id):
        """Check if hotel has sufficient balance for order"""
        try:
            # Auto-create wallet if not exists
            wallet_check = HotelWallet.get_or_create_wallet(hotel_id)
            if not wallet_check:
                return {'sufficient': True, 'message': 'Could not retrieve wallet, allowing operation'}
            
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT balance, per_order_charge FROM hotel_wallet WHERE hotel_id = %s
            """, (hotel_id,))
            wallet = cursor.fetchone()
            cursor.close()
            connection.close()
            
            if not wallet:
                return {'sufficient': True, 'message': 'No wallet configured'}
            
            charge = float(wallet['per_order_charge'])
            balance = float(wallet['balance'])
            
            if charge == 0:
                return {'sufficient': True, 'charge': 0, 'balance': balance}
            
            return {
                'sufficient': balance >= charge,
                'charge': charge,
                'balance': balance,
                'shortfall': max(0, charge - balance)
            }
        except Error as exc:
            print(f"Error checking balance: {exc}")
            return {'sufficient': True, 'message': 'Error checking balance'}
    
    @staticmethod
    def get_transactions(hotel_id, limit=50):
        """Get transaction history for a hotel"""
        try:
            connection = get_db_connection()
            cursor = connection.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT * FROM wallet_transactions 
                WHERE hotel_id = %s 
                ORDER BY created_at DESC 
                LIMIT %s
            """, (hotel_id, limit))
            
            transactions = cursor.fetchall()
            cursor.close()
            connection.close()
            
            result = []
            for t in transactions:
                result.append({
                    'id': t['id'],
                    'transaction_type': t['transaction_type'],
                    'amount': float(t['amount']),
                    'balance_after': float(t['balance_after']),
                    'utr_number': t.get('utr_number'),
                    'razorpay_payment_id': t.get('razorpay_payment_id'),
                    'razorpay_order_id': t.get('razorpay_order_id'),
                    'reference_type': t['reference_type'],
                    'reference_id': t['reference_id'],
                    'created_by_type': t['created_by_type'],
                    'created_at': t['created_at'].strftime('%Y-%m-%d %H:%M:%S') if t['created_at'] else None
                })
            return result
        except Error as exc:
            print(f"Error getting transactions: {exc}")
            return []
    
    @staticmethod
    def update_charges(hotel_id, per_verification_charge, per_order_charge):
        """Update hotel charges"""
        try:
            # Auto-create wallet if not exists
            wallet_check = HotelWallet.get_or_create_wallet(hotel_id)
            if not wallet_check:
                return {'success': False, 'message': 'Could not create or retrieve wallet'}
            
            connection = get_db_connection()
            cursor = connection.cursor()
            
            cursor.execute("""
                UPDATE hotel_wallet 
                SET per_verification_charge = %s, per_order_charge = %s
                WHERE hotel_id = %s
            """, (per_verification_charge, per_order_charge, hotel_id))
            
            connection.commit()
            cursor.close()
            connection.close()
            
            return {'success': True, 'message': 'Charges updated successfully'}
        except Error as exc:
            print(f"Error updating charges: {exc}")
            return {'success': False, 'message': f'Database error: {str(exc)}'}
