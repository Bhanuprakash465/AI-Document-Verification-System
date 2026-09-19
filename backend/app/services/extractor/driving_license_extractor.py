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


def _clean_number(value: str | None) -> str | None:
    """
    Normalise a licence number: uppercase, strip internal spaces
    (OCR frequently inserts or drops spaces inside long numbers).
    """
    if not value:
        return None

    value = re.sub(r"\s+", "", str(value)).upper().strip()

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
    # OCR-tolerant: "DL" is frequently misread as "DLI"/"D1"/"DL1"
    # and the number itself may contain stray spaces or have its
    # leading letter misread as a digit (e.g. TS -> 1S). The label
    # pattern therefore allows D/L/I/1 variants, and the captured
    # number is normalised (uppercased, spaces removed).
    #
    # Matching is done PER LINE: a whole-text search could match
    # "LICENCE" at the end of the "DRIVING LICENCE" heading and
    # then swallow the start of the NEXT line as the "number".
    # ---------------------------------------------------------

    licence_number = None

    label_patterns = [
        re.compile(
            r"(?:D[L1][I1lL]?|LICEN[CS]E)\s*(?:NO|NUMBER|N0)?\s*[:.\-]?\s*"
            r"([A-Z0-9][A-Z0-9 /-]{4,24})\s*$",
            re.IGNORECASE,
        ),
    ]

    generic_pattern = re.compile(
        r"\b([A-Z]{2,3}\d{2}[ ]?\d{4,15})\b",
        re.IGNORECASE,
    )

    for line in lines:

        for pattern in label_patterns:

            match = pattern.search(line)

            if match:
                licence_number = _clean_number(
                    match.group(1)
                )
                break

        if licence_number:
            break

    if not licence_number:

        for line in lines:

            match = generic_pattern.search(line)

            if match:
                licence_number = _clean_number(
                    match.group(1)
                )
                break

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