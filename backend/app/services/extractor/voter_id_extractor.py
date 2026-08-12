import re


# =========================================================
# VOTER ID / EPIC EXTRACTION
# =========================================================

EPIC_PATTERN = re.compile(
    r"\b[A-Z]{3}[0-9]{7}\b",
    re.IGNORECASE,
)

DATE_PATTERN = re.compile(
    r"\b\d{2}[./-]\d{2}[./-]\d{4}\b"
)


def clean_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def clean_name(text: str):
    if not text:
        return None

    text = clean_line(text)

    text = re.sub(
        r"[^A-Za-z.\s]",
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


def extract_voter_id_fields(ocr_text: list[str]) -> dict:
    fields = {
        "document_type": "voter_id",
        "voter_id": None,
        "epic_number": None,
        "name": None,
        "father_name": None,
        "date_of_birth": None,
        "gender": None,
        "address": None,
        "pin_code": None,
    }

    lines = [
        clean_line(line)
        for line in ocr_text
        if line and line.strip()
    ]

    full_text = "\n".join(lines)

    # =====================================================
    # EPIC NUMBER
    # =====================================================

    epic_match = EPIC_PATTERN.search(full_text)

    if epic_match:
        epic = epic_match.group().upper()

        fields["voter_id"] = epic
        fields["epic_number"] = epic

    # =====================================================
    # DATE OF BIRTH
    # =====================================================

    for index, line in enumerate(lines):

        normalized = line.lower()

        if (
            "date of birth" in normalized
            or "dob" in normalized
            or "birth" in normalized
        ):

            match = DATE_PATTERN.search(line)

            if match:
                fields["date_of_birth"] = match.group()
                break

            if index + 1 < len(lines):

                match = DATE_PATTERN.search(
                    lines[index + 1]
                )

                if match:
                    fields["date_of_birth"] = (
                        match.group()
                    )
                    break

    # =====================================================
    # NAME
    # =====================================================

    for index, line in enumerate(lines):

        normalized = line.lower()

        if (
            re.search(r"\bname\b", normalized)
            and "father" not in normalized
            and "husband" not in normalized
        ):

            same_line = re.sub(
                r"(?i).*?\bname\b\s*[:\-]?\s*",
                "",
                line,
            ).strip()

            candidate = clean_name(same_line)

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

    # =====================================================
    # FATHER / HUSBAND NAME
    # =====================================================

    for index, line in enumerate(lines):

        normalized = line.lower()

        if not (
            "father" in normalized
            or "husband" in normalized
            or "relation" in normalized
        ):
            continue

        same_line = re.sub(
            r"(?i).*?"
            r"(?:father'?s?|husband'?s?|relation)"
            r"\s*(?:name)?\s*[:\-]?\s*",
            "",
            line,
        ).strip()

        candidate = clean_name(same_line)

        if candidate:
            fields["father_name"] = candidate
            break

        if index + 1 < len(lines):

            candidate = clean_name(
                lines[index + 1]
            )

            if candidate:
                fields["father_name"] = candidate
                break

    # =====================================================
    # GENDER
    # =====================================================

    gender_patterns = {
        "male": r"\bmale\b|\bm\b",
        "female": r"\bfemale\b|\bf\b",
        "other": r"\bother\b|\btransgender\b",
    }

    for line in lines:

        normalized = line.lower()

        if re.search(
            gender_patterns["female"],
            normalized,
        ):
            fields["gender"] = "Female"
            break

        if re.search(
            gender_patterns["male"],
            normalized,
        ):
            fields["gender"] = "Male"
            break

        if re.search(
            gender_patterns["other"],
            normalized,
        ):
            fields["gender"] = "Other"
            break

    # =====================================================
    # PIN CODE
    # =====================================================

    pin_match = re.search(
        r"\b[1-9][0-9]{5}\b",
        full_text,
    )

    if pin_match:
        fields["pin_code"] = pin_match.group()

    # =====================================================
    # ADDRESS
    # =====================================================

    address_keywords = [
        "address",
        "residence",
        "village",
        "street",
        "road",
        "district",
        "taluk",
        "post",
        "po:",
    ]

    address_lines = []

    collecting = False

    for line in lines:

        normalized = line.lower()

        if any(
            keyword in normalized
            for keyword in address_keywords
        ):
            collecting = True

        if collecting:

            if (
                "election commission" in normalized
                or "elector" in normalized
                or "identity card" in normalized
            ):
                continue

            address_lines.append(line)

            if len(address_lines) >= 4:
                break

    if address_lines:

        address = " ".join(address_lines)

        address = re.sub(
            r"(?i)^.*?\baddress\b\s*[:\-]?\s*",
            "",
            address,
        )

        address = clean_line(address)

        if address:
            fields["address"] = address

    return fields