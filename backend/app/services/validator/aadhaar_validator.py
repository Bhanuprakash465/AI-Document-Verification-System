"""Legacy standalone Aadhaar field checks.

DEPRECATED: the production pipeline uses
``app.services.document_service.validate_aadhaar_fields`` (structural
validation with Verhoeff-checksum warning + always ``not_verified``
authenticity). This module is kept only for backward compatibility and
must not be extended — do not add a second diverging implementation.
"""
from datetime import datetime


def validate_aadhaar(data):
    """Validate Aadhaar data fields."""
    if not data:
        return {
            "valid": False,
            "errors": ["No extracted data provided."]
        }

    errors = []
    aadhaar_number = data.get("aadhaar_number")

    if not aadhaar_number:
        errors.append("Aadhaar number is missing.")
    else:
        normalized = aadhaar_number.replace(" ", "")
        if len(normalized) != 12 or not normalized.isdigit():
            errors.append("Aadhaar number is invalid.")

    if not data.get("name"):
        errors.append("Name is missing.")

    if not data.get("dob"):
        errors.append("Date of birth is missing.")
    else:
        try:
            datetime.strptime(data["dob"], "%d/%m/%Y")
        except ValueError:
            errors.append("Date of birth is invalid.")

    if not data.get("gender"):
        errors.append("Gender is missing.")

    if data.get("pin_code") and (len(data["pin_code"]) != 6 or not data["pin_code"].isdigit()):
        errors.append("PIN code is invalid.")

    return {
        "valid": len(errors) == 0,
        "errors": errors
    }
