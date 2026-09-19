"""
PAN (Permanent Account Number) extractor.

Extracts common Indian PAN card fields from OCR text:

  * PAN number   (AAAAA9999A)
  * Name
  * Father's name
  * Date of birth
"""

import re
from typing import Any


PAN_PATTERN = re.compile(
    r"\b[A-Z]{5}[0-9]{4}[A-Z]\b",
    re.IGNORECASE,
)

DATE_PATTERN = re.compile(
    r"\b\d{2}[./-]\d{2}[./-]\d{4}\b"
)


def clean_line(text: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(text or ""),
    ).strip()


def clean_name(text: str):
    if not text:
        return None

    text = clean_line(text)

    text = re.sub(
        r"[^A-Za-z.\s'-]",
        " ",
        text,
    )

    text = clean_line(text)

    words = text.split()

    if len(words) < 2:
        return None

    if len(words) > 8:
        return None

    return text.upper()


def extract_pan_fields(
    ocr_text: list[str],
) -> dict[str, Any]:

    fields = {
        "document_type": "pan",
        "pan_number": None,
        "name": None,
        "father_name": None,
        "dob": None,
    }

    lines = [
        clean_line(line)
        for line in ocr_text
        if line and line.strip()
    ]

    if not lines:
        return fields

    full_text = "\n".join(lines)

    # -----------------------------------------------------
    # PAN NUMBER
    # -----------------------------------------------------

    match = PAN_PATTERN.search(full_text)

    if match:
        fields["pan_number"] = match.group().upper()

    # -----------------------------------------------------
    # DATE OF BIRTH
    # -----------------------------------------------------

    for line in lines:

        date_match = DATE_PATTERN.search(line)

        if date_match:
            fields["dob"] = date_match.group()
            break

    # -----------------------------------------------------
    # NAME (skip father-name lines)
    # -----------------------------------------------------

    for index, line in enumerate(lines):

        normalized = line.lower()

        if "father" in normalized:
            continue

        if not re.search(r"\bname\b", normalized):
            continue

        value = re.sub(
            r"(?i).*?\bname\b\s*[:\-]?\s*",
            "",
            line,
        ).strip()

        candidate = clean_name(value)

        if candidate:
            fields["name"] = candidate
            break

        if index + 1 < len(lines):
            candidate = clean_name(lines[index + 1])

            if candidate:
                fields["name"] = candidate
                break

    # -----------------------------------------------------
    # FATHER'S NAME
    # -----------------------------------------------------

    for index, line in enumerate(lines):

        normalized = line.lower()

        if "father" not in normalized:
            continue

        value = re.sub(
            r"(?i).*?father'?s?\s*name\s*[:\-]?\s*",
            "",
            line,
        ).strip()

        candidate = clean_name(value)

        if candidate:
            fields["father_name"] = candidate
            break

        if index + 1 < len(lines):
            candidate = clean_name(lines[index + 1])

            if candidate:
                fields["father_name"] = candidate
                break

    return fields


# Backward-compatible alias.
def extract_fields(ocr_text):
    return extract_pan_fields(ocr_text)