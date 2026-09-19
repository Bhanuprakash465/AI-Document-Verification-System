import re
from typing import Any


# =========================================================
# REGEX PATTERNS
# =========================================================

AADHAAR_PATTERN = re.compile(
    r"(?<!\d)"
    r"(?:\d{4}[\s-]?){2}\d{4}"
    r"(?!\d)"
)

DOB_PATTERN = re.compile(
    r"\b\d{2}[./-]\d{2}[./-]\d{4}\b"
)

PIN_PATTERN = re.compile(
    r"(?<!\d)"
    r"[1-9]\d{5}"
    r"(?!\d)"
)

SPACED_PIN_PATTERN = re.compile(
    r"(?<!\d)"
    r"[1-9]\d{2}[\s-]?\d{3}"
    r"(?!\d)"
)


# =========================================================
# COMMON OCR NOISE
# =========================================================

OCR_REPLACEMENTS = {
    "|": "I",
    "¦": "I",
    "§": "S",
    "0": "O",
}


# =========================================================
# HELPERS
# =========================================================

def clean_line(text: str) -> str:

    if not text:
        return ""

    text = str(text)

    text = text.replace("\n", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_text(text: str) -> str:

    text = clean_line(text)

    return text.upper()


def digits_only(text: str) -> str:

    return re.sub(
        r"\D",
        "",
        text or "",
    )


def normalize_aadhaar(number: str):

    digits = digits_only(number)

    if len(digits) != 12:
        return None

    return (
        f"{digits[:4]} "
        f"{digits[4:8]} "
        f"{digits[8:]}"
    )


def normalize_pin(pin: str):

    digits = digits_only(pin)

    if len(digits) != 6:
        return None

    if digits[0] == "0":
        return None

    return digits


def normalize_gender(text: str):

    if not text:
        return None

    value = normalize_text(text)

    if re.search(r"\bFEMALE\b", value):
        return "FEMALE"

    if re.search(r"\bMALE\b", value):
        return "MALE"

    if re.search(r"\bTRANSGENDER\b", value):
        return "TRANSGENDER"

    if re.search(r"\bF\b", value):
        return "FEMALE"

    if re.search(r"\bM\b", value):
        return "MALE"

    return None


def clean_name(text: str):

    if not text:
        return None

    text = clean_line(text)

    # Remove digits.
    text = re.sub(
        r"\d+",
        " ",
        text,
    )

    # Keep only alphabetic characters,
    # spaces, apostrophes and dots.
    text = re.sub(
        r"[^A-Za-z.'\s]",
        " ",
        text,
    )

    text = clean_line(text)

    if not text:
        return None

    words = text.split()

    if len(words) < 2:
        return None

    if len(words) > 5:
        return None

    # Reject extremely short/noisy tokens.
    valid_words = [
        word
        for word in words
        if len(re.sub(r"[^A-Za-z]", "", word)) >= 2
    ]

    if len(valid_words) < 2:
        return None

    # A useful OCR-name heuristic:
    # mostly alphabetic content.
    letters = sum(
        character.isalpha()
        for character in text
    )

    total = sum(
        not character.isspace()
        for character in text
    )

    if total == 0:
        return None

    if letters / total < 0.70:
        return None

    return " ".join(valid_words).upper()


def looks_like_name(text: str):

    candidate = clean_name(text)

    if not candidate:
        return False

    upper = candidate.upper()

    rejected = [
        "GOVERNMENT OF INDIA",
        "GOVT OF INDIA",
        "GOVERNMENT",
        "UNIQUE IDENTIFICATION",
        "AUTHORITY",
        "AADHAAR",
        "UIDAI",
        "INDIA",
        "ADDRESS",
        "DATE OF BIRTH",
        "YEAR OF BIRTH",
        "DOB",
        "GENDER",
        "MALE",
        "FEMALE",
        "TRANSGENDER",
        "ENROLMENT",
        "ENROLLMENT",
        "IDENTIFICATION",
        "IDENTITY",
        "SIGNATURE",
        "MY AADHAAR",
        "VID",
    ]

    for value in rejected:
        if value in upper:
            return False

    # Reject text with too many single-character tokens.
    words = upper.split()

    single_char_count = sum(
        len(word) == 1
        for word in words
    )

    if single_char_count > 1:
        return False

    return True


def find_dates(lines: list[str]):

    dates = []

    for line in lines:

        matches = DOB_PATTERN.findall(line)

        for match in matches:

            if match not in dates:
                dates.append(match)

    return dates


def find_aadhaar_numbers(lines: list[str]):

    numbers = []

    for line in lines:

        matches = AADHAAR_PATTERN.findall(line)

        for match in matches:

            normalized = normalize_aadhaar(match)

            if normalized:
                numbers.append(normalized)

    # Also search complete OCR text because
    # DocTR may split the number across lines.
    complete_text = " ".join(lines)

    matches = AADHAAR_PATTERN.findall(
        complete_text
    )

    for match in matches:

        normalized = normalize_aadhaar(match)

        if normalized:
            numbers.append(normalized)

    # Remove duplicates.
    unique = []

    for number in numbers:

        if number not in unique:
            unique.append(number)

    return unique


def find_pins(lines: list[str]):

    pins = []

    for line in lines:

        # Standard six-digit PIN.
        for match in PIN_PATTERN.findall(line):

            pin = normalize_pin(match)

            if pin:
                pins.append(pin)

        # OCR sometimes outputs:
        # 560 001
        # 560-001
        for match in SPACED_PIN_PATTERN.findall(line):

            pin = normalize_pin(match)

            if pin:
                pins.append(pin)

    # Search complete OCR text as fallback.
    complete_text = " ".join(lines)

    for match in SPACED_PIN_PATTERN.findall(
        complete_text
    ):

        pin = normalize_pin(match)

        if pin:
            pins.append(pin)

    unique = []

    for pin in pins:

        if pin not in unique:
            unique.append(pin)

    return unique


# =========================================================
# ADDRESS DETECTION
# =========================================================

def is_address_start(line: str):

    normalized = normalize_text(line)

    address_keywords = [
        "ADDRESS",
        "ADDR",
        "S/O",
        "D/O",
        "W/O",
        "C/O",
        "HOUSE",
        "H NO",
        "H.NO",
        "VILLAGE",
        "VILL",
        "TOWN",
        "CITY",
        "DISTRICT",
        "DIST",
        "STATE",
        "ROAD",
        "STREET",
        "NAGAR",
        "LAYOUT",
        "COLONY",
        "TALUK",
        "TALUKA",
        "PIN",
    ]

    return any(
        keyword in normalized
        for keyword in address_keywords
    )


def is_address_stop(line: str):

    normalized = normalize_text(line)

    stop_words = [
        "DATE OF BIRTH",
        "DOB",
        "YEAR OF BIRTH",
        "GENDER",
        "MALE",
        "FEMALE",
        "TRANSGENDER",
        "AADHAAR NUMBER",
        "AADHAAR NO",
        "UIDAI",
        "UNIQUE IDENTIFICATION",
        "GOVERNMENT OF INDIA",
        "SIGNATURE",
        "ENROLMENT",
        "ENROLLMENT",
    ]

    return any(
        value in normalized
        for value in stop_words
    )


def extract_address(
    lines: list[str],
    pin_code: str | None,
):

    # -----------------------------------------------------
    # First: find explicit address label.
    # -----------------------------------------------------

    start_index = None

    for index, line in enumerate(lines):

        if is_address_start(line):

            normalized = normalize_text(line)

            if (
                "ADDRESS" in normalized
                or "ADDR" in normalized
            ):

                start_index = index
                break

    if start_index is not None:

        address_lines = []

        first_line = re.sub(
            r"(?i).*?\bADDRESS\b\s*[:\-]?\s*",
            "",
            lines[start_index],
        ).strip()

        if (
            first_line
            and first_line.upper() != "ADDRESS"
        ):

            address_lines.append(
                first_line
            )

        for index in range(
            start_index + 1,
            min(
                start_index + 8,
                len(lines),
            ),
        ):

            line = clean_line(
                lines[index]
            )

            if not line:
                continue

            if is_address_stop(line):
                break

            address_lines.append(line)

            # Stop after the line containing PIN.
            if pin_code and pin_code in digits_only(line):
                break

        if address_lines:

            address = clean_line(
                " ".join(address_lines)
            )

            # Remove PIN from address ending.
            if pin_code:

                address = re.sub(
                    rf"\b{re.escape(pin_code[:3])}"
                    rf"[\s-]?{re.escape(pin_code[3:])}\b",
                    "",
                    address,
                )

                address = clean_line(
                    address
                )

            if len(address) >= 8:

                return address

    # -----------------------------------------------------
    # Second: reconstruct address from lines around PIN.
    # -----------------------------------------------------

    if pin_code:

        for index, line in enumerate(lines):

            if pin_code in digits_only(line):

                address_lines = []

                # Look backwards for up to 4 lines.
                start = max(
                    0,
                    index - 4,
                )

                for previous_index in range(
                    start,
                    index + 1,
                ):

                    candidate = clean_line(
                        lines[previous_index]
                    )

                    if not candidate:
                        continue

                    if is_address_stop(
                        candidate
                    ):
                        continue

                    # Don't add Aadhaar number.
                    if AADHAAR_PATTERN.search(
                        candidate
                    ):
                        continue

                    # Don't add obvious DOB.
                    if DOB_PATTERN.search(
                        candidate
                    ):
                        continue

                    address_lines.append(
                        candidate
                    )

                if address_lines:

                    address = clean_line(
                        " ".join(address_lines)
                    )

                    if len(address) >= 8:

                        return address

    return None


# =========================================================
# NAME DETECTION
# =========================================================

def _name_plausibility(candidate: str) -> int:
    """
    Score how much a cleaned line looks like a real person name
    written in Latin script (English/romanised Indian names).

    Devanagari-derived OCR garbage ("SSSTRT IT", "STETK TCT")
    has very few vowels and long consonant runs, while real names
    ("Prakash Ranjan") have a healthy vowel ratio. This score is
    what separates the two when both are near the DOB line.
    """

    letters = [
        character
        for character in candidate.upper()
        if character.isalpha()
    ]

    if not letters:
        return -100

    vowels = sum(
        character in "AEIOU"
        for character in letters
    )

    ratio = vowels / len(letters)

    score = 0

    # Real romanised names sit roughly in 0.25-0.60.
    if 0.25 <= ratio <= 0.60:
        score += 6
    elif ratio < 0.15 or ratio > 0.75:
        score -= 8

    # Penalise 3+ identical consecutive letters ("SSS").
    if re.search(
        r"(.)\1{2,}",
        candidate.upper(),
    ):
        score -= 8

    # Penalise runs of 4+ consonants ("SSSTRT").
    if re.search(
        r"[BCDFGHJKLMNPQRSTVWXYZ]{4,}",
        candidate.upper(),
    ):
        score -= 6

    return score


def extract_name(
    lines: list[str],
    dates: list[str],
    aadhaar_numbers: list[str],
):

    rejected = [
        "GOVERNMENT OF INDIA",
        "GOVT OF INDIA",
        "GOVERNMENT",
        "UNIQUE IDENTIFICATION",
        "AUTHORITY",
        "AADHAAR",
        "AADHAR",
        "UIDAI",
        "INDIA",
        "ADDRESS",
        "DATE OF BIRTH",
        "DOB",
        "YEAR OF BIRTH",
        "GENDER",
        "MALE",
        "FEMALE",
        "TRANSGENDER",
        "ENROLMENT",
        "ENROLLMENT",
        "IDENTIFICATION",
        "IDENTITY",
        "SIGNATURE",
        "MY AADHAAR",
        # Scanner watermarks are never the person's name.
        "SCANNED BY",
        "CAMSCANNER",
        "SCANNER",
        "SCANNED",
    ]

    candidates = []

    for index, line in enumerate(lines):

        candidate = clean_name(line)

        if not candidate:
            continue

        # Strip a leading "NAME" label token - many cards print
        # "Name: RAHUL SHARMA" and the label must not become part
        # of the extracted person name.
        candidate = re.sub(
            r"^NAME\s*[:\-]?\s*",
            "",
            candidate,
            flags=re.IGNORECASE,
        ).strip()

        candidate = clean_name(candidate)

        if not candidate:
            continue

        upper = candidate.upper()

        if any(
            word in upper
            for word in rejected
        ):
            continue

        if AADHAAR_PATTERN.search(line):
            continue

        if DOB_PATTERN.search(line):
            continue

        if PIN_PATTERN.search(
            digits_only(line)
        ):
            continue

        # Don't select lines with too much
        # OCR noise.
        words = candidate.split()

        if any(
            len(word) == 1
            for word in words
        ):
            continue

        # Score candidate.
        score = 0

        # Plausibility dominates: a line that does not look like a
        # Latin-script person name must lose to one that does,
        # regardless of position.
        score += _name_plausibility(candidate)

        # Names generally contain 2-4 words.
        if 2 <= len(words) <= 4:
            score += 5

        # Prefer reasonable word lengths.
        if all(
            2 <= len(word) <= 15
            for word in words
        ):
            score += 3

        # Prefer candidates near DOB/gender (weak context bonus).
        nearby = " ".join(
            lines[
                index + 1:
                min(index + 4, len(lines))
            ]
        ).lower()

        if (
            DOB_PATTERN.search(nearby)
            or "male" in nearby
            or "female" in nearby
            or re.search(
                r"\b[MF]\b",
                nearby,
            )
        ):
            score += 3

        # Penalize suspiciously long names.
        if len(candidate) > 40:
            score -= 5

        candidates.append(
            (
                score,
                index,
                candidate,
            )
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: (
            item[0],
            -item[1],
        ),
        reverse=True,
    )

    return candidates[0][2]


# =========================================================
# MAIN AADHAAR EXTRACTION
# =========================================================

def extract_aadhaar_fields(
    ocr_text: list[str],
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
    # CLEAN OCR
    # -----------------------------------------------------

    lines = [
        clean_line(line)
        for line in ocr_text
        if line and clean_line(line)
    ]

    if not lines:
        return fields

    # -----------------------------------------------------
    # COMPLETE OCR TEXT
    # -----------------------------------------------------

    full_text = "\n".join(lines)

    # =====================================================
    # AADHAAR NUMBER
    # =====================================================

    aadhaar_numbers = find_aadhaar_numbers(
        lines
    )

    if aadhaar_numbers:

        # Prefer the first valid 12-digit number.
        fields["aadhaar_number"] = (
            aadhaar_numbers[0]
        )

    # =====================================================
    # DOB
    # =====================================================

    dates = find_dates(lines)

    if dates:

        fields["dob"] = dates[0]

    # =====================================================
    # GENDER
    # =====================================================

    for line in lines:

        gender = normalize_gender(line)

        if gender:

            fields["gender"] = gender
            break

    # =====================================================
    # PIN CODE
    # =====================================================

    pins = find_pins(lines)

    if pins:

        # Prefer PINs appearing near address-like text.
        selected_pin = None

        for index, line in enumerate(lines):

            if is_address_start(line):

                nearby = " ".join(
                    lines[
                        index:
                        min(index + 6, len(lines))
                    ]
                )

                nearby_pins = find_pins(
                    [nearby]
                )

                if nearby_pins:

                    selected_pin = (
                        nearby_pins[0]
                    )

                    break

        fields["pin_code"] = (
            selected_pin
            or pins[-1]
        )

    # =====================================================
    # NAME
    # =====================================================

    fields["name"] = extract_name(
        lines,
        dates,
        aadhaar_numbers,
    )

    # =====================================================
    # ADDRESS
    # =====================================================

    fields["address"] = extract_address(
        lines,
        fields["pin_code"],
    )

    # =====================================================
    # FINAL CLEANUP
    # =====================================================

    if fields["name"]:

        fields["name"] = clean_name(
            fields["name"]
        )

    if fields["pin_code"]:

        fields["pin_code"] = normalize_pin(
            fields["pin_code"]
        )

    if fields["aadhaar_number"]:

        fields["aadhaar_number"] = (
            normalize_aadhaar(
                fields["aadhaar_number"]
            )
        )

    return fields


# =========================================================
# BACKWARD COMPATIBILITY
# =========================================================

def extract_fields(
    ocr_text: list[str],
) -> dict[str, Any]:

    return extract_aadhaar_fields(
        ocr_text
    )