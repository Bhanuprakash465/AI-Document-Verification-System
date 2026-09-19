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


# =========================================================
# NAME HELPERS
# =========================================================

# Lines that are structural labels / boilerplate, never a person's
# name.  Used to reject OCR garbage that happens to look alphabetic.
_NAME_REJECTED = {
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
    "DOB",
    "YEAR OF BIRTH",
    "GENDER",
    "MALE",
    "FEMALE",
    "TRANSGENDER",
    "ELECTION COMMISSION",
    "ELECTOR",
    "EPIC",
    "VOTER",
    "IDENTITY CARD",
    "PHOTO IDENTITY",
    "SIGNATURE",
    "SCANNED BY",
    "CAMSCANNER",
    "SCANNER",
    "SCANNED",
}


def _split_camel_case(text: str) -> list[str]:
    """
    Split camelCase / PascalCase text into word tokens.

    Examples:
        AbhishekKumarsingh -> ["Abhishek", "Kumarsingh"]
        RAHUL SHARMA       -> ["RAHUL", "SHARMA"]
    """

    return re.findall(
        r"[A-Z]?[a-z]+|[A-Z]+(?![a-z])",
        text,
    )


def _char_diff(a: str, b: str) -> int:
    """
    Count character-level differences between two strings
    (case-insensitive).  Strings of very different length are
    considered dissimilar.
    """
    a = a.lower()
    b = b.lower()
    if abs(len(a) - len(b)) > 2:
        return 999
    max_len = max(len(a), len(b))
    a = a.ljust(max_len)
    b = b.ljust(max_len)
    return sum(1 for x, y in zip(a, b) if x != y)


def _looks_like_name(text: str) -> bool:
    """
    Heuristic: does *text* look like a real person name rather
    than OCR garbage or a structural label?
    """
    candidate = clean_name(text)
    if not candidate:
        return False

    upper = candidate.upper()

    for value in _NAME_REJECTED:
        if value in upper:
            return False

    # Reject lines with too many single-character tokens.
    words = upper.split()
    single_char_count = sum(
        len(word) == 1 for word in words
    )
    if single_char_count > 1:
        return False

    return True


def _looks_like_name_fragment(text: str) -> bool:
    """Like :func:`_looks_like_name` but for single-word continuations.

    ``clean_name`` requires >= 2 words, so a wrapped surname ("SHARMA")
    alone would never pass. A fragment is accepted when it is alphabetic
    (>= 2 chars), not a boilerplate label, and not dominated by
    single-character tokens.
    """
    cleaned = clean_line(text)
    if not cleaned:
        return False
    alpha = re.sub(r"[^A-Za-z.\s]", " ", cleaned)
    alpha = clean_line(alpha)
    words = alpha.split()
    # Must contain real alphabetic content (>= 2 letters); a bare EPIC
    # number or date leaves nothing after stripping digits/punctuation.
    letters_only = re.sub(r"[^A-Za-z]", "", alpha)
    if len(letters_only) < 2:
        return False
    if not words or any(len(word) < 2 for word in words):
        # Single letters / fragments are OCR noise, not a surname.
        if len(words) != 1 or len(words[0]) < 2:
            return False
    if len(words) > 8:
        return False
    # EPIC/identifier-looking lines are never a name continuation, even
    # though their letter runs ("ABC" in "ABC1234567") look alphabetic.
    if EPIC_PATTERN.search(cleaned):
        return False
    if DATE_PATTERN.search(cleaned):
        return False
    upper = alpha.upper()
    for value in _NAME_REJECTED:
        if value in upper:
            return False
    return True


def _extract_name_from_label(
    lines: list[str],
    label_index: int,
) -> str | None:
    """
    Extract a person's name from the line at *label_index* (which
    contains a "Name:" label) and any continuation lines.

    Handles:
      * camelCase names with no spaces ("AbhishekKumarsingh")
      * names split across multiple OCR lines
      * OCR noise on the same line as the label
    """
    line = lines[label_index]

    # Strip the "Name:" label and any trailing punctuation.
    value = re.sub(
        r"(?i).*?\bname\b\s*[:\-]?\s*",
        "",
        line,
    ).strip()

    # Remove trailing punctuation that OCR sometimes fuses
    # onto the label (e.g. "Name: AbhishekKumarsingn" is fine,
    # but "Name. Abhishek" should still work).
    value = re.sub(r"^[.\-,:;\s]+", "", value).strip()

    # Split camelCase into word tokens.
    parts = _split_camel_case(value)

    # If the same-line value produced no usable tokens, try the
    # next line as a fallback (but only if it looks like a name).
    if not parts or not any(
        p.isalpha() and len(p) >= 2 for p in parts
    ):
        if label_index + 1 < len(lines):
            next_line = lines[label_index + 1]
            if _looks_like_name(next_line):
                parts = _split_camel_case(next_line)

    # -------------------------------------------------
    # Multi-line continuation: a *long single-token* value (camelCase
    # like "AbhishekKumarsingh", len > 6) plus a single-word next line
    # is likely a wrapped surname. Short single tokens ("RAHUL") do
    # NOT trigger this branch — a bare first name plus an unrelated
    # next line must not be concatenated.
    # -------------------------------------------------
    if (
        len(parts) == 1
        and len(parts[0]) > 6
        and label_index + 1 < len(lines)
    ):
        next_line = lines[label_index + 1]
        next_parts = _split_camel_case(next_line)

        # Only combine if the next line is a single alphabetic word
        # that looks like a name fragment (not a label or garbage).
        if (
            len(next_parts) == 1
            and next_parts[0].isalpha()
            and len(next_parts[0]) >= 2
        ):
            next_word = next_parts[0]

            # Try to split the long word where the next-line word
            # (or an OCR variant of it) begins as a suffix.
            # e.g. "Kumarsingn" + "Singh" -> "Kumar" + "Singh"
            # because "singn" is within 1 char of "Singh".
            split_done = False
            for split_pos in range(3, len(parts[0]) - 2):
                suffix = parts[0][split_pos:]
                if _char_diff(suffix, next_word) <= 1:
                    parts = [
                        parts[0][:split_pos],
                        next_word,
                    ]
                    split_done = True
                    break

            if not split_done:
                # No suffix match - just append the continuation.
                parts.append(next_word)

    # Also handle the case where the same-line value already has
    # multiple words but the next line is a continuation (e.g. first
    # name on the label line, surname wrapped below). The next line is
    # appended only when it looks like a name fragment: alphabetic,
    # non-boilerplate, and (for single-word fragments) not rejected as
    # a structural label. Unrelated OCR text must be ignored.
    elif (
        len(parts) >= 2
        and label_index + 1 < len(lines)
    ):
        next_line = lines[label_index + 1]
        next_parts = _split_camel_case(next_line)

        if (
            len(next_parts) == 1
            and next_parts[0].isalpha()
            and len(next_parts[0]) >= 2
            and _looks_like_name_fragment(next_line)
            # Only add if the next word isn't already a suffix
            # of the last part (avoid duplicates from OCR).
            and not parts[-1].lower().endswith(
                next_parts[0].lower()
            )
        ):
            # Check if the last part ends with a variant of
            # the next word (OCR corruption).
            last = parts[-1]
            if len(last) > 6:
                for split_pos in range(3, len(last) - 2):
                    suffix = last[split_pos:]
                    if _char_diff(suffix, next_parts[0]) <= 1:
                        parts = (
                            parts[:-1]
                            + [last[:split_pos]]
                            + [next_parts[0]]
                        )
                        break
                else:
                    parts.append(next_parts[0])
            else:
                parts.append(next_parts[0])

    if not parts:
        return None

    name = " ".join(parts)
    return clean_name(name)


def _extract_field_after_label(
    lines: list[str],
    label_index: int,
    label_regex: str,
) -> str | None:
    """
    Generic helper: extract the value after a label on the line at
    *label_index*, falling back to the next line only if it looks
    like a name.
    """
    line = lines[label_index]

    same_line = re.sub(
        label_regex,
        "",
        line,
    ).strip()

    same_line = re.sub(
        r"^[.\-,:;\s]+",
        "",
        same_line,
    ).strip()

    candidate = clean_name(same_line)

    if candidate:
        return candidate

    # Only fall back to the next line if it looks like a name.
    if label_index + 1 < len(lines):
        next_line = lines[label_index + 1]
        if _looks_like_name(next_line):
            return clean_name(next_line)

    return None


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

    if not lines:
        return fields

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

            name = _extract_name_from_label(
                lines,
                index,
            )

            if name:
                fields["name"] = name
                break

            # Name label present but value is a bare first name on its own
            # line with the surname wrapped below ("Name: RAHUL" / "SHARMA").
            # Only merge when the next line is a plausible name fragment.
            value = re.sub(
                r"(?i).*?\bname\b\s*[:\-]?\s*",
                "",
                line,
            ).strip()
            value = re.sub(r"^[.\-,:;\s]+", "", value).strip()
            if (
                value
                and _split_camel_case(value)
                and len(_split_camel_case(value)) == 1
                and index + 1 < len(lines)
                and _looks_like_name_fragment(lines[index + 1])
                and ":" not in lines[index + 1]
            ):
                fragment = clean_line(lines[index + 1])
                combined = clean_name(f"{value} {fragment}")
                if combined:
                    fields["name"] = combined
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

        father_name = _extract_field_after_label(
            lines,
            index,
            r"(?i).*?"
            r"(?:father'?s?|husband'?s?|relation)"
            r"\s*(?:name)?\s*[:\-]?\s*",
        )

        if father_name:
            fields["father_name"] = father_name
            break

    # =====================================================
    # GENDER
    # =====================================================

    # OCR frequently corrupts "Gender: Male" into fragments like
    # "foT/ Gender: yMale:" where "y" is a stray character before
    # "Male".  Using substring matching (without \b) for the full
    # word "male"/"female" tolerates these artifacts, while the
    # single-letter patterns still use \b to avoid matching inside
    # other words.
    gender_patterns = {
        "male": r"male|\bm\b",
        "female": r"female|\bf\b",
        "other": r"other|transgender",
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
