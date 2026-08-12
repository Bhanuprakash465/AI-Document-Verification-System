"""
Driving Licence extractor.

Extracts common Indian Driving Licence fields from OCR text.
"""

import re
from typing import Any


def _clean(value: str | None) -> str | None:
    if not value:
        return None

    value = re.sub(r"\s+", " ", value).strip()

    return value or None


def _find_first(
    text: str,
    patterns: list[str],
) -> str | None:

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            return _clean(match.group(1))

    return None


def extract_driving_license_fields(
    ocr_text: str | list[str],
) -> dict[str, Any]:

    # ---------------------------------------------------------
    # Convert OCR input into lines
    # ---------------------------------------------------------

    if isinstance(ocr_text, list):

        lines = [
            str(line).strip()
            for line in ocr_text
            if line
        ]

    else:

        lines = str(ocr_text).splitlines()

    lines = [
        line
        for line in lines
        if line.strip()
    ]

    text = "\n".join(lines)

    # ---------------------------------------------------------
    # Licence number
    # ---------------------------------------------------------

    licence_number = _find_first(
        text,
        [
            r"(?:DL\s*(?:NO|NUMBER)?|LICEN[CS]E\s*(?:NO|NUMBER)?)[\s:.-]*([A-Z0-9/-]{6,25})",

            r"\b([A-Z]{2}\d{2}\s?\d{4,15})\b",
        ],
    )

    # ---------------------------------------------------------
    # Name
    # ---------------------------------------------------------

    name = _find_first(
        text,
        [
            r"(?:NAME|HOLDER\s*NAME|DRIVER\s*NAME)[\s:.-]*([A-Z][A-Z .'-]{2,80})",
        ],
    )

    # ---------------------------------------------------------
    # Date of Birth
    # ---------------------------------------------------------

    date_of_birth = _find_first(
        text,
        [
            r"(?:DATE\s*OF\s*BIRTH|DOB|D\.O\.B)[\s:.-]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        ],
    )

    # ---------------------------------------------------------
    # Issue date
    # ---------------------------------------------------------

    issue_date = _find_first(
        text,
        [
            r"(?:VALID\s*FROM|ISSUED\s*ON|DATE\s*OF\s*ISSUE|ISSUE\s*DATE)[\s:.-]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        ],
    )

    # ---------------------------------------------------------
    # Expiry date
    # ---------------------------------------------------------

    expiry_date = _find_first(
        text,
        [
            r"(?:VALID\s*(?:UPTO|UNTIL|TO)|VALIDITY|DATE\s*OF\s*EXPIRY|EXPIRY\s*DATE)[\s:.-]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        ],
    )

    # ---------------------------------------------------------
    # Blood group
    # ---------------------------------------------------------

    blood_group = _find_first(
        text,
        [
            r"(?:BLOOD\s*GROUP|BLOOD)[\s:.-]*([ABO]{1,2}\s*[+-])",

            r"\b((?:A|B|AB|O)\s*[+-])\b",
        ],
    )

    if blood_group:
        blood_group = blood_group.replace(
            " ",
            "",
        ).upper()

    # ---------------------------------------------------------
    # Address
    # ---------------------------------------------------------

    address = _find_first(
        text,
        [
            r"(?:ADDRESS|RESIDENTIAL\s*ADDRESS)[\s:.-]*(.{10,150})",
        ],
    )

    # ---------------------------------------------------------
    # Vehicle classes
    # ---------------------------------------------------------

    vehicle_classes = []

    class_patterns = [
        r"\bMCWG\b",
        r"\bMCWOG\b",
        r"\bLMV\b",
        r"\bHMV\b",
        r"\bHGMV\b",
        r"\bHPMV\b",
        r"\bTRANS\b",
        r"\bTR\b",
        r"\bMC\b",
    ]

    for pattern in class_patterns:

        matches = re.findall(
            pattern,
            text,
            re.IGNORECASE,
        )

        for match in matches:

            value = match.upper()

            if value not in vehicle_classes:
                vehicle_classes.append(value)

    # ---------------------------------------------------------
    # Result
    # ---------------------------------------------------------

    return {
        "document_type": "driving_license",
        "licence_number": licence_number,
        "name": name,
        "date_of_birth": date_of_birth,
        "issue_date": issue_date,
        "expiry_date": expiry_date,
        "blood_group": blood_group,
        "vehicle_classes": vehicle_classes,
        "address": address,
    }