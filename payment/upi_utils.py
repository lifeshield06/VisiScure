"""
UPI Payment Utilities Module

This module provides utility functions for UPI payment processing including:
- UPI ID format validation
- UPI payment link generation
- QR file validation
"""

import re
from urllib.parse import quote


def validate_upi_id(upi_id: str) -> bool:
    """
    Validate UPI ID format.
    
    Valid UPI ID format: [identifier]@[bank]
    - Identifier can be email, phone number, or alphanumeric string
    - Bank suffix must be alphanumeric
    
    Args:
        upi_id: UPI ID string to validate
        
    Returns:
        True if UPI ID is valid, False otherwise
        
    Examples:
        >>> validate_upi_id("9876543210@paytm")
        True
        >>> validate_upi_id("user@okaxis")
        True
        >>> validate_upi_id("invalid")
        False
        >>> validate_upi_id("@bank")
        False
    """
    if not upi_id or not isinstance(upi_id, str):
        return False
    
    # UPI ID pattern: [identifier]@[bank]
    # Identifier: alphanumeric, dots, underscores, hyphens (min 3 chars)
    # Bank: alphanumeric (min 2 chars)
    pattern = r'^[a-zA-Z0-9._-]{3,}@[a-zA-Z0-9]{2,}$'
    
    return bool(re.match(pattern, upi_id))


def generate_upi_payment_link(upi_id: str, hotel_name: str, amount: float) -> str:
    """
    Generate UPI payment deep link.
    
    Creates a UPI deep link that can be used to initiate payment in any UPI app
    (Google Pay, PhonePe, Paytm, etc.)
    
    Args:
        upi_id: Valid UPI ID of the payee
        hotel_name: Name of the hotel (payee name)
        amount: Payment amount in INR (must be positive)
        
    Returns:
        UPI deep link string in format: upi://pay?pa={upi_id}&pn={hotel_name}&am={amount}&cu=INR
        
    Raises:
        ValueError: If amount is not positive or parameters are invalid
        
    Examples:
        >>> generate_upi_payment_link("hotel@paytm", "Grand Hotel", 1250.50)
        'upi://pay?pa=hotel%40paytm&pn=Grand+Hotel&am=1250.50&cu=INR'
    """
    if not upi_id or not isinstance(upi_id, str):
        raise ValueError("UPI ID must be a non-empty string")
    
    if not hotel_name or not isinstance(hotel_name, str):
        raise ValueError("Hotel name must be a non-empty string")
    
    if not isinstance(amount, (int, float)) or amount <= 0:
        raise ValueError("Amount must be a positive number")
    
    # Format amount to 2 decimal places
    formatted_amount = f"{amount:.2f}"
    
    # URL encode parameters
    encoded_upi_id = quote(upi_id)
    encoded_hotel_name = quote(hotel_name)
    
    # Construct UPI deep link
    upi_link = (
        f"upi://pay?"
        f"pa={encoded_upi_id}&"
        f"pn={encoded_hotel_name}&"
        f"am={formatted_amount}&"
        f"cu=INR"
    )
    
    return upi_link


def allowed_qr_file(filename: str) -> bool:
    """
    Validate if the uploaded file is an allowed QR image type.
    
    Allowed extensions: png, jpg, jpeg
    
    Args:
        filename: Name of the file to validate
        
    Returns:
        True if file extension is allowed, False otherwise
        
    Examples:
        >>> allowed_qr_file("qr_code.png")
        True
        >>> allowed_qr_file("qr_code.jpg")
        True
        >>> allowed_qr_file("document.pdf")
        False
    """
    if not filename or not isinstance(filename, str):
        return False
    
    ALLOWED_QR_EXTENSIONS = {'png', 'jpg', 'jpeg'}
    
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_QR_EXTENSIONS
