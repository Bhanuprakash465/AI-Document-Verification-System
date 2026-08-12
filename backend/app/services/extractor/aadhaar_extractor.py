import re
from typing import Any


# =========================================================
# REGEX PATTERNS
# =========================================================

AADHAAR_PATTERN = re.compile(
    r"\b\d{4}\s?\d{4}\s?\d{4}\b"
)

DOB_PATTERN = re.compile(
    r"\b\d{2}[./-]\d{2}[./-]\d{4}\b"
)

PIN_PATTERN = re.compile(
    r"\b[1-9][0-9]{5}\b"
)


# =========================================================
# HELPERS
# =========================================================

def clean_line(text: str) -> str:

    if not text:
        return ""

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


def clean_name(text: str):

    if not text:
        return None

    text = clean_line(text)

    # Remove obvious OCR noise.
    text = re.sub(
        r"[^A-Za-z.\s]",
        " ",
        text
    )

    text = clean_line(text)

    if not text:
        return None

    words = text.split()

    if len(words) < 2:
        return None

    if len(words) > 8:
        return None

    return text.upper()


def normalize_aadhaar(number: str):

    if not number:
        return None

    digits = re.sub(
        r"\D",
        "",
        number
    )

    if len(digits) != 12:
        return None

    return (
        f"{digits[:4]} "
        f"{digits[4:8]} "
        f"{digits[8:]}"
    )


# =========================================================
# AADHAAR EXTRACTION
# =========================================================

def extract_aadhaar_fields(
    ocr_text: list[str]
) -> dict[str, Any]:

    fields = {

        "document_type": "aadhaar",

        "name": None,

        "aadhaar_number": None,

        "dob": None,

        "gender": None,

        "address": None,

        "pin_code": None,
    }


    # -----------------------------------------------------
    # CLEAN OCR LINES
    # -----------------------------------------------------

    lines = [

        clean_line(line)

        for line in ocr_text

        if line and line.strip()
    ]


    if not lines:
        return fields


    full_text = "\n".join(lines)


    # =====================================================
    # AADHAAR NUMBER
    # =====================================================

    aadhaar_match = AADHAAR_PATTERN.search(
        full_text
    )

    if aadhaar_match:

        fields["aadhaar_number"] = (
            normalize_aadhaar(
                aadhaar_match.group()
            )
        )


    # =====================================================
    # DATE OF BIRTH
    # =====================================================

    for index, line in enumerate(lines):

        normalized = line.lower()


        if (
            "date of birth" in normalized
            or re.search(r"\bdob\b", normalized)
            or "birth" in normalized
        ):

            date_match = DOB_PATTERN.search(
                line
            )

            if date_match:

                fields["dob"] = (
                    date_match.group()
                )

                break


            # Check next OCR line.

            if index + 1 < len(lines):

                date_match = DOB_PATTERN.search(
                    lines[index + 1]
                )

                if date_match:

                    fields["dob"] = (
                        date_match.group()
                    )

                    break


    # -----------------------------------------------------
    # FALLBACK DOB
    # -----------------------------------------------------

    if not fields["dob"]:

        dates = DOB_PATTERN.findall(
            full_text
        )

        if dates:

            fields["dob"] = dates[0]


    # =====================================================
    # GENDER
    # =====================================================

    for line in lines:

        normalized = line.lower()


        if re.search(
            r"\b(male|female|transgender)\b",
            normalized
        ):

            match = re.search(
                r"\b(male|female|transgender)\b",
                normalized
            )

            if match:

                fields["gender"] = (
                    match.group(1).upper()
                )

                break


        # Common Hindi/English OCR layouts.

        if re.search(
            r"\b(m|f)\b",
            normalized
        ):

            match = re.search(
                r"\b(m|f)\b",
                normalized
            )

            if match:

                value = match.group(1).upper()

                fields["gender"] = (
                    "MALE"
                    if value == "M"
                    else "FEMALE"
                )

                break


    # =====================================================
    # NAME
    # =====================================================

    name_rejected = [

        "GOVERNMENT OF INDIA",

        "GOVT OF INDIA",

        "UNIQUE IDENTIFICATION",

        "AUTHORITY",

        "AADHAAR",

        "AADHAAR CARD",

        "UIDAI",

        "DATE OF BIRTH",

        "DOB",

        "YEAR OF BIRTH",

        "MALE",

        "FEMALE",

        "ADDRESS",

        "INDIA",

        "SIGNATURE",

        "ENROLMENT",

        "ENROLLMENT",

        "IDENTIFICATION",

        "IDENTITY",

        "MY AADHAAR",

    ]


    # -----------------------------------------------------
    # Explicit NAME label
    # -----------------------------------------------------

    for index, line in enumerate(lines):

        normalized = line.lower()


        if "name" not in normalized:

            continue


        # Ignore labels that are clearly not person names.

        if (
            "father" in normalized
            or "husband" in normalized
            or "mother" in normalized
        ):

            continue


        # Same-line extraction.

        same_line = re.sub(
            r"(?i).*?\bname\b\s*[:\-]?\s*",
            "",
            line
        ).strip()


        candidate = clean_name(
            same_line
        )


        if candidate:

            upper_candidate = candidate.upper()


            if not any(
                rejected in upper_candidate
                for rejected in name_rejected
            ):

                fields["name"] = candidate

                break


        # Next-line extraction.

        if index + 1 < len(lines):

            candidate = clean_name(
                lines[index + 1]
            )


            if candidate:

                upper_candidate = candidate.upper()


                if not any(
                    rejected in upper_candidate
                    for rejected in name_rejected
                ):

                    fields["name"] = candidate

                    break


    # =====================================================
    # FALLBACK NAME DETECTION
    # =====================================================

    if not fields["name"]:

        candidates = []


        for index, line in enumerate(lines):

            candidate = clean_name(
                line
            )


            if not candidate:
                continue


            upper = candidate.upper()


            # Reject obvious non-name lines.

            if any(
                rejected in upper
                for rejected in name_rejected
            ):
                continue


            # Reject Aadhaar number.

            if AADHAAR_PATTERN.fullmatch(
                candidate
            ):
                continue


            # Reject dates.

            if DOB_PATTERN.fullmatch(
                candidate
            ):
                continue


            # Reject PIN-only lines.

            if PIN_PATTERN.fullmatch(
                candidate
            ):
                continue


            candidates.append(
                (
                    index,
                    candidate
                )
            )


        if candidates:

            # Prefer realistic multi-word names.

            candidates.sort(
                key=lambda item: (
                    len(item[1].split()),
                    len(item[1])
                ),
                reverse=True
            )


            fields["name"] = (
                candidates[0][1]
            )


    # =====================================================
    # PIN CODE
    # =====================================================

    # Prefer a PIN near an address-related line.

    for index, line in enumerate(lines):

        normalized = line.lower()


        if "address" in normalized:

            pin_match = PIN_PATTERN.search(
                line
            )

            if pin_match:

                fields["pin_code"] = (
                    pin_match.group()
                )

                break


            # Search a few lines after ADDRESS.

            for next_index in range(
                index + 1,
                min(index + 5, len(lines))
            ):

                pin_match = PIN_PATTERN.search(
                    lines[next_index]
                )

                if pin_match:

                    fields["pin_code"] = (
                        pin_match.group()
                    )

                    break


            if fields["pin_code"]:
                break


    # -----------------------------------------------------
    # Fallback PIN detection
    # -----------------------------------------------------

    if not fields["pin_code"]:

        pin_matches = PIN_PATTERN.findall(
            full_text
        )

        if pin_matches:

            fields["pin_code"] = (
                pin_matches[-1]
            )


    # =====================================================
    # ADDRESS
    # =====================================================

    address_lines = []

    address_started = False


    for index, line in enumerate(lines):

        normalized = line.lower()


        if "address" in normalized:

            address_started = True


            same_line = re.sub(
                r"(?i).*?\baddress\b\s*[:\-]?\s*",
                "",
                line
            ).strip()


            if same_line:

                address_lines.append(
                    same_line
                )


            continue


        if address_started:

            upper = line.upper()


            # Stop at obvious document fields.

            if any(
                stop_word in normalized
                for stop_word in [
                    "date of birth",
                    "dob",
                    "gender",
                    "male",
                    "female",
                    "signature",
                    "aadhaar",
                    "government of india",
                    "unique identification"
                ]
            ):

                break


            address_lines.append(line)


            if len(address_lines) >= 5:

                break


    if address_lines:

        address = " ".join(
            address_lines
        )


        address = clean_line(
            address
        )


        if address:

            fields["address"] = address


    return fields


# =========================================================
# BACKWARD-COMPATIBLE ALIAS
# =========================================================

def extract_fields(
    ocr_text: list[str]
) -> dict[str, Any]:

    return extract_aadhaar_fields(
        ocr_text
    )