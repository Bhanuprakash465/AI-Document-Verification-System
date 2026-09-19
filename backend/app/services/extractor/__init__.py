from app.services.extractor.aadhaar_extractor import (
    extract_aadhaar_fields,
)

from app.services.extractor.pan_extractor import (
    extract_pan_fields,
)

from app.services.extractor.driving_license_extractor import (
    extract_driving_license_fields,
)

from app.services.extractor.passport_extractor import (
    extract_passport_fields,
)

from app.services.extractor.voter_id_extractor import (
    extract_voter_id_fields,
)


def extract_fields(
    ocr_text,
):
    """
    Backward-compatible Aadhaar extractor.

    Existing code that imports extract_fields()
    will continue to work.
    """

    return extract_aadhaar_fields(
        ocr_text
    )


__all__ = [
    "extract_fields",
    "extract_aadhaar_fields",
    "extract_pan_fields",
    "extract_driving_license_fields",
    "extract_passport_fields",
    "extract_voter_id_fields",
]
