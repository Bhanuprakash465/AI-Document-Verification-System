"""
Voter ID document detection and field extraction.
"""

import re


DOCUMENT_TYPE = "voter_id"

DISPLAY_NAME = "Voter ID"


# ---------------------------------------------------------
# EPIC / Voter ID number
# Typical format: ABC1234567
# ---------------------------------------------------------

EPIC_PATTERN = re.compile(
    r"\b[A-Z]{3}[0-9]{7}\b",
    re.IGNORECASE
)


# ---------------------------------------------------------
# Document detection
# ---------------------------------------------------------

def detect(text: str) -> bool:

    text_lower = text.lower()

    keywords = [
        "election commission of india",
        "elector",
        "elector photo identity card",
        "epic",
        "voter",
        "मतदाता",
    ]

    keyword_match = any(
        keyword in text_lower
        for keyword in keywords
    )

    epic_match = EPIC_PATTERN.search(
        text
    )

    return (
        keyword_match
        or epic_match is not None
    )


# ---------------------------------------------------------
# Field extraction
# ---------------------------------------------------------

def extract_fields(text: str) -> dict:

    fields = {}


    # Voter / EPIC number
    epic_match = EPIC_PATTERN.search(
        text
    )

    if epic_match:

        fields["voter_id"] = (
            epic_match
            .group()
            .upper()
        )


    # Date of birth if present
    dob_pattern = re.compile(
        r"\b\d{2}[/-]\d{2}[/-]\d{4}\b"
    )

    dob_match = dob_pattern.search(
        text
    )

    if dob_match:

        fields["date_of_birth"] = (
            dob_match.group()
        )


    return fields