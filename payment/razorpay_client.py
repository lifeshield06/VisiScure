"""
Razorpay Payment Gateway Integration
VisiScure Order - Multi-Hotel Restaurant Management System

This module handles Razorpay payment integration for wallet recharge.
"""

import razorpay
import hmac
import hashlib
from config import RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET


class RazorpayClient:
    """Razorpay Payment Gateway Client"""
    
    _instance = None
    _client = None
    
    def __new__(cls):
        """Singleton pattern to ensure single client instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize Razorpay client"""
        self.key_id = RAZORPAY_KEY_ID
        self.key_secret = RAZORPAY_KEY_SECRET
        self.enabled = bool(self.key_id and self.key_secret)
        
        if self.enabled:
            try:
                self._client = razorpay.Client(auth=(self.key_id, self.key_secret))
                print(f"[RAZORPAY] Client initialized with key: {self.key_id[:15]}...")
            except Exception as e:
                print(f"[RAZORPAY] Error initializing client: {e}")
                self.enabled = False
                self._client = None
        else:
            print("[RAZORPAY] Not configured - RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET missing")
            self._client = None
    
    @property
    def is_enabled(self):
        """Check if Razorpay is enabled"""
        return self.enabled
    
    @property
    def client(self):
        """Get Razorpay client instance"""
        return self._client
    
    def create_order(self, amount, currency="INR", notes=None):
        """
        Create a Razorpay order
        
        Args:
            amount: Amount in rupees (will be converted to paise)
            currency: Currency code (default: INR)
            notes: Optional dictionary of notes
            
        Returns:
            dict: Order details with order_id, or error dict
        """
        if not self.enabled or not self._client:
            return {"success": False, "message": "Razorpay is not configured"}
        
        try:
            order_data = {
                "amount": int(amount * 100),  # Convert to paise
                "currency": currency,
                "payment_capture": 1  # Auto-capture payment
            }
            
            if notes:
                order_data["notes"] = notes
            
            order = self._client.order.create(data=order_data)
            
            return {
                "success": True,
                "order_id": order["id"],
                "amount": amount,
                "currency": currency,
                "key_id": self.key_id
            }
            
        except Exception as e:
            print(f"[RAZORPAY] Error creating order: {e}")
            return {"success": False, "message": f"Error creating order: {str(e)}"}
    
    def verify_payment_signature(self, razorpay_order_id, razorpay_payment_id, razorpay_signature):
        """
        Verify Razorpay payment signature
        
        Args:
            razorpay_order_id: Order ID from Razorpay
            razorpay_payment_id: Payment ID from Razorpay
            razorpay_signature: Signature from Razorpay
            
        Returns:
            bool: True if signature is valid, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Generate expected signature
            signature_payload = f"{razorpay_order_id}|{razorpay_payment_id}"
            expected_signature = hmac.new(
                self.key_secret.encode('utf-8'),
                signature_payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, razorpay_signature)
            
        except Exception as e:
            print(f"[RAZORPAY] Error verifying signature: {e}")
            return False
    
    def fetch_payment(self, payment_id):
        """
        Fetch payment details from Razorpay
        
        Args:
            payment_id: Razorpay payment ID
            
        Returns:
            dict: Payment details or None
        """
        if not self.enabled or not self._client:
            return None
        
        try:
            return self._client.payment.fetch(payment_id)
        except Exception as e:
            print(f"[RAZORPAY] Error fetching payment: {e}")
            return None
    
    def get_config(self):
        """Get Razorpay configuration for frontend"""
        return {
            "enabled": self.enabled,
            "key_id": self.key_id if self.enabled else None
        }


# Singleton instance
razorpay_client = RazorpayClient()


def get_razorpay_client():
    """Get the Razorpay client singleton"""
    return razorpay_client
