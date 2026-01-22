"""Data mapping utilities for QuickBooks synchronization."""

from typing import Dict, Any, Optional


def map_address_to_qb(street: Optional[str] = None, 
                      city: Optional[str] = None,
                      country: Optional[str] = None,
                      postal_code: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Map address fields to QuickBooks address format.
    
    Args:
        street: Street address
        city: City name
        country: Country name
        postal_code: Postal/ZIP code
        
    Returns:
        Dict in QuickBooks address format or None if no address data
    """
    if not any([street, city, country, postal_code]):
        return None
    
    address = {}
    
    # QuickBooks address fields
    if street:
        address['Line1'] = street
    if city:
        address['City'] = city
    if country:
        address['Country'] = country
    if postal_code:
        address['PostalCode'] = postal_code
    
    return address if address else None


def validate_required_fields(data: Dict[str, Any], required_fields: list) -> Optional[str]:
    """
    Validate that all required fields are present and non-empty.
    
    Args:
        data: The data to validate
        required_fields: List of required field names
        
    Returns:
        Error message if validation fails, None if valid
    """
    missing_fields = []
    
    for field in required_fields:
        if field not in data or not data[field] or str(data[field]).strip() == '':
            missing_fields.append(field)
    
    if missing_fields:
        return f"Missing required fields: {', '.join(missing_fields)}"
    
    return None


def clean_phone_number(phone: Optional[str]) -> Optional[str]:
    """
    Clean and format phone number for QuickBooks.
    
    Args:
        phone: Raw phone number
        
    Returns:
        Cleaned phone number or None if invalid
    """
    if not phone:
        return None
    
    # Remove all non-digit characters
    cleaned = ''.join(c for c in phone if c.isdigit())
    
    # Basic validation - should have at least 10 digits for a valid phone number
    if len(cleaned) < 10:
        return None
    
    return cleaned


def clean_email(email: Optional[str]) -> Optional[str]:
    """
    Clean and validate email address.
    
    Args:
        email: Raw email address
        
    Returns:
        Cleaned email or None if invalid
    """
    if not email:
        return None
    
    email = email.strip().lower()
    
    # Basic email validation
    if '@' not in email or '.' not in email.split('@')[-1]:
        return None
    
    return email
