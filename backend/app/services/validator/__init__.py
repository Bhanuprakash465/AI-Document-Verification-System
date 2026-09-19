"""Legacy validator package (deprecated).

The production pipeline validates via
``app.services.document_service``. This package is retained only for
backward compatibility; do not add new validators here.
"""
from .aadhaar_validator import validate_aadhaar

__all__ = ["validate_aadhaar"]
