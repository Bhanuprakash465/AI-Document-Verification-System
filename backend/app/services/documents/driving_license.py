"""
Indian Driving Licence document detection and field extraction.
"""

import re


DOCUMENT_TYPE = "driving_license"

DISPLAY_NAME = "Driving Licence"


# ---------------------------------------------------------
# Document detection
# ---------------------------------------------------------

def detect(text: str) -> bool:

    text_lower = text.lower()

    keywords = [
        "driving licence",
        "driving license",
        "transport department",
        "licence to drive",
        "license to drive",
        "motor driving",
        "dl no",
    ]

    return any(
        keyword in text_lower
        for keyword in keywords
    )


# ---------------------------------------------------------
# Field extraction
# ---------------------------------------------------------

def extract_fields(text: str) -> dict:

    fields = {}


    # -----------------------------------------------------
    # Driving licence number
    # -----------------------------------------------------

    patterns = [

        r"(?:dl\s*no|dl\s*number)"
        r"\s*[:\-]?\s*([A-Z0-9\-\/]+)",

        r"(?:licence\s*no|license\s*no)"
        r"\s*[:\-]?\s*([A-Z0-9\-\/]+)",

        r"(?:driving\s*licence\s*no)"
        r"\s*[:\-]?\s*([A-Z0-9\-\/]+)",

    ]


    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            fields["license_number"] = (
                match.group(1)
                .upper()
            )

            break


    # -----------------------------------------------------
    # Date patterns
    # -----------------------------------------------------

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