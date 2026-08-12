from app.services.extractor.aadhaar_extractor import extract_aadhaar_fields
from app.services.extractor.driving_license_extractor import extract_driving_license_fields


def extract_fields(ocr_text):
    """
    Backward-compatible extractor entry point.

    Currently supports Aadhaar.
    Additional document-specific extractors are handled
    directly by document_service.py.
    """

    return extract_aadhaar_fields(ocr_text)


__all__ = [
    "extract_fields",
    "extract_aadhaar_fields",
    "extract_driving_license_fields",
]