"""
PAN Card document detection and field extraction.
"""

import re


DOCUMENT_TYPE = "pan"

DISPLAY_NAME = "PAN Card"


# ---------------------------------------------------------
# PAN number pattern
# Example: ABCDE1234F
# ---------------------------------------------------------

PAN_PATTERN = re.compile(
    r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
    re.IGNORECASE
)


# ---------------------------------------------------------
# Document detection
# ---------------------------------------------------------

def detect(text: str) -> bool:

    text_lower = text.lower()

    keywords = [
        "income tax department",
        "income tax",
        "permanent account number",
        "pan card",
    ]

    keyword_match = any(
        keyword in text_lower
        for keyword in keywords
    )

    pan_match = PAN_PATTERN.search(
        text
    )

    return (
        keyword_match
        or pan_match is not None
    )


# ---------------------------------------------------------
# Field extraction
# ---------------------------------------------------------

def extract_fields(text: str) -> dict:

    fields = {}


    # PAN number
    pan_match = PAN_PATTERN.search(
        text
    )

    if pan_match:

        fields["pan_number"] = (
            pan_match
            .group()
            .upper()
        )


    return fields