"""
Aadhaar document detection and field extraction.
"""

import re


DOCUMENT_TYPE = "aadhaar"

DISPLAY_NAME = "Aadhaar Card"


# ---------------------------------------------------------
# Aadhaar number
# ---------------------------------------------------------

AADHAAR_PATTERN = re.compile(
    r"\b\d{4}\s?\d{4}\s?\d{4}\b"
)


# ---------------------------------------------------------
# Date of birth
# ---------------------------------------------------------

DOB_PATTERN = re.compile(
    r"\b\d{2}[/-]\d{2}[/-]\d{4}\b"
)


# ---------------------------------------------------------
# Document detection
# ---------------------------------------------------------

def detect(text: str) -> bool:

    text_lower = text.lower()

    keywords = [
        "aadhaar",
        "uidai",
        "unique identification",
        "government of india",
    ]

    keyword_matches = sum(
        keyword in text_lower
        for keyword in keywords
    )

    aadhaar_number = AADHAAR_PATTERN.search(
        text
    )

    return (
        keyword_matches >= 1
        or aadhaar_number is not None
    )


# ---------------------------------------------------------
# Field extraction
# ---------------------------------------------------------

def extract_fields(text: str) -> dict:

    fields = {}


    # Aadhaar number
    aadhaar_match = AADHAAR_PATTERN.search(
        text
    )

    if aadhaar_match:

        fields["aadhaar_number"] = (
            aadhaar_match
            .group()
            .replace(" ", "")
        )


    # Date of birth
    dob_match = DOB_PATTERN.search(
        text
    )

    if dob_match:

        fields["date_of_birth"] = (
            dob_match.group()
        )


    return fields