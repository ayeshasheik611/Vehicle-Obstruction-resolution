"""
Vehicle number format validation utilities

This module provides vehicle number validation functions:
- Format validation using regex patterns
- Normalization (whitespace removal, uppercase conversion)
- Length validation
- Vehicle number masking for privacy

**Validates Requirements**: 3.1, 3.2, 3.3, 3.4, 3.5, 7.1, 7.2, 7.3, 7.4, 7.5
"""
import re
from typing import List


# Define valid vehicle number patterns for different regional formats
# Validates Requirement 3.3
VEHICLE_PATTERNS: List[str] = [
    r"^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$",  # Indian format: MH12AB1234, RJ14CV0002
    r"^[A-Z]{2}[0-9]{1}[A-Z]{1}[0-9]{4}$",    # Indian format: TN8F4089 (Tamil Nadu style)
    r"^[A-Z]{3}[0-9]{4}$",                      # Simple format: ABC1234
    r"^[0-9]{2}[A-Z]{2}[0-9]{4}$",             # Alternative: 12AB3456
    r"^[A-Z]{2}[0-9]{4}[A-Z]{2}$",             # Format: AB1234CD
    r"^[A-Z]{1}[0-9]{6}$",                      # Format: A123456
    r"^[A-Z]{2}[0-9]{6}$",                      # Format: AB123456
]


def normalize_vehicle_number(vehicle_number: str) -> str:
    """
    Normalize vehicle number by removing whitespace and converting to uppercase.
    
    **Validates Requirements**: 3.1
    
    Args:
        vehicle_number: Raw vehicle number string
        
    Returns:
        Normalized vehicle number (uppercase, no whitespace)
        
    Example:
        >>> normalize_vehicle_number("mh 12 ab 1234")
        'MH12AB1234'
        >>> normalize_vehicle_number("  abc1234  ")
        'ABC1234'
    """
    if not vehicle_number:
        return ""
    
    # Remove all whitespace and convert to uppercase
    normalized = vehicle_number.strip().replace(" ", "").upper()
    return normalized


def validate_vehicle_format(vehicle_number: str) -> bool:
    """
    Validate vehicle number format using regex patterns.
    
    **Validates Requirements**: 3.1, 3.2, 3.3, 3.4, 3.5
    
    The function:
    1. Normalizes the vehicle number (removes whitespace, converts to uppercase)
    2. Checks length constraints (6-10 characters)
    3. Validates against multiple regional format patterns
    
    Args:
        vehicle_number: Vehicle number to validate
        
    Returns:
        True if vehicle number matches at least one valid pattern, False otherwise
        
    Example:
        >>> validate_vehicle_format("MH12AB1234")
        True
        >>> validate_vehicle_format("ABC1234")
        True
        >>> validate_vehicle_format("INVALID")
        False
        >>> validate_vehicle_format("12345")  # Too short
        False
    """
    # Step 1: Normalize vehicle number (Requirement 3.1)
    normalized = normalize_vehicle_number(vehicle_number)
    
    # Step 2: Check length constraints (Requirement 3.2)
    if len(normalized) < 6 or len(normalized) > 10:
        return False
    
    # Step 3: Check against valid patterns (Requirement 3.3, 3.4)
    for pattern in VEHICLE_PATTERNS:
        if re.match(pattern, normalized):
            return True
    
    # Step 4: No pattern matched (Requirement 3.5)
    return False


def mask_vehicle_number(vehicle_number: str) -> str:
    """
    Mask vehicle number for privacy by replacing middle characters with asterisks.
    
    **Validates Requirements**: 7.1, 7.2, 7.3, 7.4, 7.5
    
    Masking strategy based on length:
    - Length <= 4: Show first and last character, mask middle
    - Length 5-7: Show first 2 and last 2 characters, mask middle
    - Length >= 8: Show first 2 and last 3 characters, mask middle
    
    Args:
        vehicle_number: Vehicle number to mask
        
    Returns:
        Masked vehicle number with same length as input
        
    Raises:
        ValueError: If vehicle_number is empty or None
        
    Example:
        >>> mask_vehicle_number("MH12AB1234")
        'MH****1234'
        >>> mask_vehicle_number("ABC1234")
        'AB***34'
        >>> mask_vehicle_number("KA05MH1234")
        'KA*****234'
        >>> mask_vehicle_number("TEST")
        'T**T'
    """
    # Precondition: vehicle_number is non-empty
    if not vehicle_number:
        raise ValueError("Vehicle number cannot be empty or None")
    
    # Step 1: Normalize input (Requirement 7.1)
    normalized = normalize_vehicle_number(vehicle_number)
    length = len(normalized)
    
    # Precondition: Must have at least 2 characters to mask
    if length < 2:
        raise ValueError("Vehicle number must have at least 2 characters")
    
    # Step 2: Determine masking strategy based on length
    if length <= 4:
        # Requirement 7.1: Too short to mask safely, mask middle characters
        # Show first and last character
        if length == 2:
            # Edge case: no middle to mask
            masked = normalized
        else:
            masked = normalized[0] + "*" * (length - 2) + normalized[-1]
    elif length <= 7:
        # Requirement 7.2: Medium length - show first 2 and last 2, mask middle
        masked = normalized[:2] + "*" * (length - 4) + normalized[-2:]
    else:
        # Requirement 7.3: Long format - show first 2 and last 3, mask middle
        masked_chars = length - 5  # 5 visible chars (2 first + 3 last)
        masked = normalized[:2] + "*" * masked_chars + normalized[-3:]
    
    # Postcondition: Masked string has same length as input (Requirement 7.4)
    assert len(masked) == length, "Masked length must equal original length"
    
    # Postcondition: Middle characters are asterisks (Requirement 7.5)
    # Exception: 2-character strings have no middle to mask
    if length > 2:
        assert "*" in masked, "Masked string must contain asterisks"
    
    return masked


def get_format_requirements() -> str:
    """
    Get a human-readable description of vehicle number format requirements.
    
    Returns:
        String describing valid vehicle number formats
    """
    return (
        "Vehicle number must be 6-10 characters long and match one of the following formats:\n"
        "- Indian format: MH12AB1234 (2 letters, 2 digits, 1-2 letters, 4 digits)\n"
        "- Simple format: ABC1234 (3 letters, 4 digits)\n"
        "- Alternative: 12AB3456 (2 digits, 2 letters, 4 digits)\n"
        "- Format: AB1234CD (2 letters, 4 digits, 2 letters)\n"
        "- Format: A123456 (1 letter, 6 digits)\n"
        "- Format: AB123456 (2 letters, 6 digits)"
    )
