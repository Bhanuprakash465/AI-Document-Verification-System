"""
Passport document extractor.

Extracts common fields from OCR text obtained from
Indian passport documents.
"""

import re


PASSPORT_NUMBER_PATTERN = re.compile(
    r"\b[A-Z][0-9]{7}\b",
    re.IGNORECASE,
)

DATE_PATTERN = re.compile(
    r"\b\d{2}[/-]\d{2}[/-]\d{4}\b"
)


def clean_line(text: str) -> str:
    """Normalize OCR text."""

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def clean_name(text: str) -> str | None:
    """Clean a possible person's name."""

    if not text:
        return None

    text = clean_line(text)

    text = re.sub(
        r"[^A-Za-z.\s]",
        " ",
        text,
    )

    text = clean_line(text)

    if not text:
        return None

    words = text.split()

    if len(words) < 2 or len(words) > 8:
        return None

    return text.upper()


def extract_passport_fields(
    ocr_text: list[str],
) -> dict:
    """
    Extract passport information from OCR lines.
    """

    fields = {
        "document_type": "passport",
        "passport_number": None,
        "name": None,
        "surname": None,
        "given_names": None,
        "nationality": None,
        "date_of_birth": None,
        "place_of_birth": None,
        "place_of_issue": None,
        "date_of_issue": None,
        "date_of_expiry": None,
        "sex": None,
    }

    lines = [
        clean_line(line)
        for line in ocr_text
        if line and line.strip()
    ]

    full_text = "\n".join(lines)

    # -------------------------------------------------
    # PASSPORT NUMBER
    # -------------------------------------------------

    match = PASSPORT_NUMBER_PATTERN.search(
        full_text
    )

    if match:
        fields["passport_number"] = (
            match.group().upper()
        )

    # -------------------------------------------------
    # DATE OF BIRTH
    # -------------------------------------------------

    for index, line in enumerate(lines):

        normalized = line.lower()

        if (
            "date of birth" in normalized
            or "dob" in normalized
            or "birth" in normalized
        ):

            date_match = DATE_PATTERN.search(
                line
            )

            if date_match:

                fields["date_of_birth"] = (
                    date_match.group()
                )

                break

            if index + 1 < len(lines):

                date_match = DATE_PATTERN.search(
                    lines[index + 1]
                )

                if date_match:

                    fields["date_of_birth"] = (
                        date_match.group()
                    )

                    break

    # -------------------------------------------------
    # DATE OF ISSUE
    # -------------------------------------------------

    for index, line in enumerate(lines):

        normalized = line.lower()

        if (
            "date of issue" in normalized
            or "issue date" in normalized
            or "issued" in normalized
        ):

            date_match = DATE_PATTERN.search(
                line
            )

            if date_match:

                fields["date_of_issue"] = (
                    date_match.group()
                )

                break

            if index + 1 < len(lines):

                date_match = DATE_PATTERN.search(
                    lines[index + 1]
                )

                if date_match:

                    fields["date_of_issue"] = (
                        date_match.group()
                    )

                    break

    # -------------------------------------------------
    # DATE OF EXPIRY
    # -------------------------------------------------

    for index, line in enumerate(lines):

        normalized = line.lower()

        if (
            "date of expiry" in normalized
            or "expiry date" in normalized
            or "date of expiration" in normalized
            or "valid until" in normalized
        ):

            date_match = DATE_PATTERN.search(
                line
            )

            if date_match:

                fields["date_of_expiry"] = (
                    date_match.group()
                )

                break

            if index + 1 < len(lines):

                date_match = DATE_PATTERN.search(
                    lines[index + 1]
                )

                if date_match:

                    fields["date_of_expiry"] = (
                        date_match.group()
                    )

                    break

    # -------------------------------------------------
    # NATIONALITY
    # -------------------------------------------------

    for index, line in enumerate(lines):

        normalized = line.lower()

        if "nationality" in normalized:

            value = re.sub(
                r"(?i).*?nationality\s*[:\-]?\s*",
                "",
                line,
            ).strip()

            if value:
                fields["nationality"] = value.upper()
                break

            if index + 1 < len(lines):

                value = clean_line(
                    lines[index + 1]
                )

                if value:
                    fields["nationality"] = value.upper()
                    break

    # -------------------------------------------------
    # SEX / GENDER
    # -------------------------------------------------

    for index, line in enumerate(lines):

        normalized = line.lower()

        if (
            re.search(r"\bsex\b", normalized)
            or re.search(r"\bgender\b", normalized)
        ):

            value = re.sub(
                r"(?i).*\b(?:sex|gender)\b\s*[:\-]?\s*",
                "",
                line,
            ).strip()

            if value.upper() in {
                "M",
                "MALE",
            }:

                fields["sex"] = "MALE"
                break

            if value.upper() in {
                "F",
                "FEMALE",
            }:

                fields["sex"] = "FEMALE"
                break

            if index + 1 < len(lines):

                next_value = (
                    lines[index + 1]
                    .strip()
                    .upper()
                )

                if next_value in {
                    "M",
                    "MALE",
                }:

                    fields["sex"] = "MALE"
                    break

                if next_value in {
                    "F",
                    "FEMALE",
                }:

                    fields["sex"] = "FEMALE"
                    break

    # -------------------------------------------------
    # NAME
    # -------------------------------------------------

    for index, line in enumerate(lines):

        normalized = line.lower()

        if (
            "surname" in normalized
            or "given name" in normalized
            or "given names" in normalized
        ):

            value = re.sub(
                r"(?i).*?(?:surname|given names?|given name)"
                r"\s*[:\-]?\s*",
                "",
                line,
            ).strip()

            candidate = clean_name(value)

            if candidate:

                if "surname" in normalized:
                    fields["surname"] = candidate
                else:
                    fields["given_names"] = candidate

            if index + 1 < len(lines):

                candidate = clean_name(
                    lines[index + 1]
                )

                if candidate:

                    if "surname" in normalized:
                        fields["surname"] = candidate
                    else:
                        fields["given_names"] = candidate

    # -------------------------------------------------
    # COMBINED NAME
    # -------------------------------------------------

    if (
        fields["surname"]
        and fields["given_names"]
    ):

        fields["name"] = (
            f"{fields['given_names']} "
            f"{fields['surname']}"
        )

    # -------------------------------------------------
    # GENERIC NAME LABEL
    # -------------------------------------------------

    if not fields["name"]:

        for index, line in enumerate(lines):

            normalized = line.lower()

            if re.search(
                r"\bname\b",
                normalized,
            ):

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

                    candidate = clean_name(
                        lines[index + 1]
                    )

                    if candidate:

                        fields["name"] = candidate
                        break

    # -------------------------------------------------
    # PLACE OF BIRTH
    # -------------------------------------------------

    for index, line in enumerate(lines):

        normalized = line.lower()

        if "place of birth" in normalized:

            value = re.sub(
                r"(?i).*?place of birth\s*[:\-]?\s*",
                "",
                line,
            ).strip()

            if value:
                fields["place_of_birth"] = value.upper()
                break

            if index + 1 < len(lines):

                value = clean_line(
                    lines[index + 1]
                )

                if value:
                    fields["place_of_birth"] = value.upper()
                    break

    # -------------------------------------------------
    # PLACE OF ISSUE
    # -------------------------------------------------

    for index, line in enumerate(lines):

        normalized = line.lower()

        if "place of issue" in normalized:

            value = re.sub(
                r"(?i).*?place of issue\s*[:\-]?\s*",
                "",
                line,
            ).strip()

            if value:
                fields["place_of_issue"] = value.upper()
                break

            if index + 1 < len(lines):

                value = clean_line(
                    lines[index + 1]
                )

                if value:
                    fields["place_of_issue"] = value.upper()
                    break

    return fields