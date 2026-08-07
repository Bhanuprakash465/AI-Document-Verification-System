import re
from difflib import SequenceMatcher


def _clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip(" :,-")


def _format_aadhaar(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    return " ".join((digits[:4], digits[4:8], digits[8:]))


def _normalise_name(value: str) -> str:
    return re.sub(r"[^a-z]", "", value.lower())


def _is_name_candidate(line: str, skip_words: list[str]) -> bool:
    """Return whether a line looks like a person's Latin-script name."""
    if len(line) < 5 or any(word.lower() in line.lower() for word in skip_words):
        return False
    if any(character.isdigit() for character in line):
        return False
    words = line.split()
    alpha_characters = sum(character.isalpha() for character in line)
    return 2 <= len(words) <= 5 and alpha_characters >= 5


def extract_fields(ocr_text):

    if isinstance(ocr_text, list):
        text = "\n".join(ocr_text)
    else:
        text = str(ocr_text)

    result = {
        "document_type": "Unknown",
        "name": None,
        "aadhaar_number": None,
        "dob": None,
        "gender": None,
        "address": None,
        "pin_code": None,
    }

    # Detect document type
    if re.search(r"\b(aadhaar|uidai|unique identification)\b", text, re.IGNORECASE):
        result["document_type"] = "Aadhaar"

    # Aadhaar number
    aadhaar = re.search(r"(?<!\d)(?:\d[\s-]?){11}\d(?!\d)", text)
    if aadhaar:
        result["aadhaar_number"] = _format_aadhaar(aadhaar.group())

    # DOB
    dob = re.search(r"(?:DOB|Date\s*of\s*Birth)?\s*[:.-]?\s*(\d{2}[/-]\d{2}[/-]\d{4})", text, re.IGNORECASE)
    if dob:
        result["dob"] = dob.group(1).replace("-", "/")

    # Gender
    if re.search(r"\bMale\b", text, re.IGNORECASE):
        result["gender"] = "Male"
    elif re.search(r"\bFemale\b", text, re.IGNORECASE):
        result["gender"] = "Female"

    # PIN code
    pin = re.search(r"(?:PIN(?:\s*Code)?|Pincode)\s*[:.-]?\s*(\d{6})\b", text, re.IGNORECASE)
    pin = pin or re.search(r"\b([1-9]\d{5})\b", text)
    if pin:
        result["pin_code"] = pin.group(1)

    # Better name extraction
    lines = text.split("\n")

    skip_words = [
        "Government",
        "Unique",
        "Authority",
        "Enrollment",
        "Aadhaar",
        "India",
        "PIN",
        "District",
        "State",
        "Male",
        "Female",
        "DOB",
        "Mobile",
        "To", "Address", "VID", "Year of Birth",
    ]

    candidates = []
    for index, raw_line in enumerate(lines):
        line = _clean_line(raw_line)
        if not _is_name_candidate(line, skip_words):
            continue

        # Aadhaar's front side normally places the name immediately before
        # DOB/gender; the address side commonly places it right after "To".
        nearby_lines = " ".join(_clean_line(item) for item in lines[max(0, index - 2):index + 4])
        score = 0
        if any(_clean_line(item).lower() == "to" for item in lines[max(0, index - 2):index]):
            score += 35
        if re.search(r"\b(dob|male|female)\b", nearby_lines, re.IGNORECASE):
            score += 45
        candidates.append({"index": index, "value": line, "score": score})

    # OCR often reads the name on both sides of an Aadhaar card.  Treat similar
    # lines as one candidate: their repetition is much stronger evidence than a
    # one-off piece of OCR noise.  Pick the earliest occurrence, which is usually
    # the cleaner address-side rendition.
    for candidate in candidates:
        candidate_key = _normalise_name(candidate["value"])
        for other in candidates:
            if other is candidate:
                continue
            similarity = SequenceMatcher(None, candidate_key, _normalise_name(other["value"])).ratio()
            if similarity >= 0.82:
                candidate["score"] += 35

    if candidates:
        best_score = max(candidate["score"] for candidate in candidates)
        related = [candidate for candidate in candidates if candidate["score"] == best_score]
        # A duplicate can have different per-line context scores. Include every
        # near-match of the strongest candidate before choosing its first reading.
        strongest = related[0]
        strongest_key = _normalise_name(strongest["value"])
        related = [
            candidate for candidate in candidates
            if SequenceMatcher(None, strongest_key, _normalise_name(candidate["value"])).ratio() >= 0.82
        ]
        chosen = min(related, key=lambda candidate: candidate["index"])
        result["name"] = chosen["value"].title() if chosen["value"].isupper() else chosen["value"]

    # Keep non-header address lines once the name has been found.  It is useful
    # context, but deliberately never used as a hard verification requirement.
    if result["name"]:
        name_index = next((i for i, line in enumerate(lines) if _clean_line(line).lower() == result["name"].lower()), -1)
        address_lines = [_clean_line(line) for line in lines[name_index + 1:] if _clean_line(line)]
        address_lines = [line for line in address_lines if not re.search(r"aadhaar|uidai|dob|male|female|\d{4}\s+\d{4}", line, re.IGNORECASE)]
        result["address"] = ", ".join(address_lines[:4]) or None

    return result
