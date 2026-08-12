"""
Passport document detection and field extraction.
"""

import re


DOCUMENT_TYPE = "passport"

DISPLAY_NAME = "Passport"


# ---------------------------------------------------------
# Indian passport number
# Typical format: A1234567
# ---------------------------------------------------------

PASSPORT_NUMBER_PATTERN = re.compile(
    r"\b[A-Z][0-9]{7}\b",
    re.IGNORECASE
)


# ---------------------------------------------------------
# Document detection
# ---------------------------------------------------------

def detect(text: str) -> bool:

    text_lower = text.lower()

    keywords = [
        "passport",
        "republic of india",
        "nationality",
        "date of issue",
        "date of expiry",
        "place of birth",
    ]

    keyword_matches = sum(
        keyword in text_lower
        for keyword in keywords
    )

    return keyword_matches >= 1


# ---------------------------------------------------------
# Field extraction
# ---------------------------------------------------------

def extract_fields(text: str) -> dict:

    fields = {}


    # Passport number
    passport_match = (
        PASSPORT_NUMBER_PATTERN.search(
            text
        )
    )

    if passport_match:

        fields["passport_number"] = (
            passport_match
            .group()
            .upper()
        )


    # Date patterns
    date_pattern = re.compile(
        r"\b\d{2}[/-]\d{2}[/-]\d{4}\b"
    )

    dates = date_pattern.findall(
        text
    )

    if len(dates) >= 1:

        fields["date_1"] = dates[0]


    if len(dates) >= 2:

        fields["date_2"] = dates[1]


    return fields