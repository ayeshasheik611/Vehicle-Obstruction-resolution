"""Utility functions"""

from .auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    extract_user_id_from_token
)

from .vehicle_validation import (
    normalize_vehicle_number,
    validate_vehicle_format,
    mask_vehicle_number,
    get_format_requirements
)

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "extract_user_id_from_token",
    "normalize_vehicle_number",
    "validate_vehicle_format",
    "mask_vehicle_number",
    "get_format_requirements"
]
