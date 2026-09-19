"""
Document classifier for the AI Document Verification System.

Classification is based on multiple weighted, document-specific
signals:

  * strong keywords  (highly characteristic phrases)
  * medium keywords  (supporting terminology)
  * identifier patterns (Aadhaar number, PAN, EPIC, passport no.)
  * passport MRZ

A lone identifier pattern is NOT enough on its own to classify a
document, because e.g. a random 12-digit run of digits is not proof
of an Aadhaar card. Identifier patterns only count as *supporting*
evidence once at least one keyword signal is present. When the best
score is too low to be trustworthy the classifier returns
``document_type = "unknown"`` instead of guessing.
"""

import re


# =========================================================
# DOCUMENT SIGNAL CONFIGURATION
# =========================================================

DOCUMENT_PATTERNS = {
    "passport": {
        "display_name": "Passport",
        "strong": [
            r"\bpassport\b",
            r"\bpassport\s*no\b",
            r"\bpassport\s*number\b",
            r"\brepublic\s+of\s+india\b",
            r"\btype\s*/\s*p\b",
        ],
        "medium": [
            r"\bdate\s+of\s+expiry\b",
            r"\bdate\s+of\s+issue\b",
            r"\bplace\s+of\s+birth\b",
            r"\bplace\s+of\s+issue\b",
            r"\bnationality\b",
            r"\bgiven\s+name\b",
            r"\bsurname\b",
        ],
        "mrz": True,
    },

    "aadhaar": {
        "display_name": "Aadhaar Card",
        "strong": [
            # Common OCR spellings: aadhaar/aadhar/adhaar/adhar.
            r"\b(?:aadhaar|aadhar|adhaar|adhar)\b",
            r"\buidai\b",
            r"\bunique\s+identification\s+authority\b",
            # OCR fuses words: "aadhaarcard", "aadhaarnumber".
            r"\b(?:aadhaar|aadhar)(?:card|number|no)\b",
        ],
        "medium": [
            r"\bunique\s+identification\b",
            r"\bgovernment\s+of\s+india\b",
            r"\benrol?ment\s+no\b",
            r"\bvid\b",
            # Demographic label printed on the front of every card.
            r"\b(?:dob|date\s+of\s+birth)\b",
        ],
        "identifier": "aadhaar_number",
    },

    "pan": {
        "display_name": "PAN Card",
        "strong": [
            r"\bpermanent\s+account\s+number\b",
            r"\bincome\s+tax\s+department\b",
        ],
        "medium": [
            r"\bpan\b",
            r"\b(?:dob|date\s+of\s+birth)\b",
        ],
        "identifier": "pan_number",
    },

    "driving_license": {
        "display_name": "Driving Licence",
        "strong": [
            r"\bdriving\s+licen[cs]e\b",
            r"\bdriver'?s\s+licen[cs]e\b",
            r"\blicen[cs]e\s+to\s+drive\b",
            r"\bdriving\s+licence\s+no\b",
        ],
        "medium": [
            r"\btransport\s+department\b",
            r"\brto\b",
            r"\bmotor\s+vehicle\b",
            r"\bdl\s*(?:no|number)\b",
            r"\bvalid\s+(?:from|upto|until)\b",
            r"\bblood\s+group\b",
            r"\b(?:dob|date\s+of\s+birth)\b",
        ],
    },

    "voter_id": {
        "display_name": "Voter ID",
        "strong": [
            r"\belection\s+commission\s+of\s+india\b",
            # OCR frequently corrupts "Election Commission of India"
            # (e.g. "ELECTION COMMISSIONA OFANDIA").  "Election
            # Commission" on its own is already highly distinctive, so
            # it is a strong signal even without the trailing "of
            # india".  No trailing \b so OCR-inserted extra characters
            # (e.g. "COMMISSIONA") do not break the match.
            r"\belection\s+commission",
            r"\belectors?\s+photo\s+identity\s+card\b",
            r"\belectoral\s+photo\s+identity\s+card\b",
            r"\bvoter\s+identity\s+card\b",
            r"\bvoter\s+id\b",
            r"\bepic\s*(?:no|number)?\b",
        ],
        "medium": [
            r"\bvoter\b",
            r"\belector\b",
            r"\bepic\b",
        ],
        "identifier": "epic_number",
    },


    "ration_card": {
        "display_name": "Ration Card",
        "strong": [
            r"\bration\s+card\b",
            r"\bpublic\s+distribution\s+system\b",
        ],
        "medium": [
            r"\bfood\s+and\s+civil\s+supplies\b",
            r"\bfood\s+supplies\s+department\b",
            r"\bfamily\s+card\b",
            r"\bpds\b",
        ],
    },

    "vehicle_rc": {
        "display_name": "Vehicle Registration Certificate",
        "strong": [
            r"\bcertificate\s+of\s+registration\b",
            r"\bregistration\s+certificate\b",
            r"\bregistered\s+owner\b",
        ],
        "medium": [
            r"\bvehicle\s+class\b",
            r"\bchassis\s+number\b",
            r"\bengine\s+number\b",
            r"\bregistration\s+number\b",
        ],
    },

    "gst_certificate": {
        "display_name": "GST Certificate",
        "strong": [
            r"\bgoods\s+and\s+services\s+tax\b",
            r"\bgst\s+certificate\b",
            r"\bgst\s+registration\b",
        ],
        "medium": [
            r"\bgstin\b",
            r"\btaxpayer\b",
        ],
    },
}


# =========================================================
# IDENTIFIER PATTERNS
# =========================================================

PASSPORT_MRZ_LINE = re.compile(
    r"^[A-Z0-9<]{30,44}$"
)

AADHAAR_NUMBER = re.compile(
    r"(?<!\d)(?:\d{4}[\s-]?){2}\d{4}(?!\d)"
)

PAN_NUMBER = re.compile(
    r"\b[A-Z]{5}\d{4}[A-Z]\b",
    re.IGNORECASE,
)

EPIC_NUMBER = re.compile(
    r"\b[A-Z]{3}\d{7}\b",
    re.IGNORECASE,
)

# A 4-digit year range is extremely common; deliberately NOT a
# driver of any classification.

STRONG_WEIGHT = 4.0
MEDIUM_WEIGHT = 1.5
MRZ_BONUS = 10.0

# Identifier patterns are only "supporting" evidence - they add a
# small bonus and only when keyword evidence already exists.
IDENTIFIER_SUPPORT_BONUS = 2.5

# Minimum score required to report a confident document type.
# Below this the classifier returns "unknown" rather than guessing.
# 3.5 means: at least one strong keyword, or (two medium keywords
# PLUS a matching identifier) - single medium keywords alone are
# never sufficient evidence.
MIN_SCORE = 3.5


# =========================================================
# HELPERS
# =========================================================

def _compile_flexible(pattern: str) -> re.Pattern:
    """
    Compile an OCR-tolerant variant of a keyword pattern.

    OCR frequently DROPS spaces between words ("GOVERNMENT OFINDIA",
    "PERMANENTACCOUNTNUMBER"). Replacing every in-pattern whitespace
    requirement with ``\\s*`` lets the phrase match with any amount of
    missing whitespace while word-boundary anchors still prevent
    accidental substring matches (e.g. "PAN" inside "COMPANY").
    """

    flexible = pattern.replace(r"\s+", r"\s*")
    flexible = flexible.replace(" ", r"\s*")

    return re.compile(
        flexible,
        re.IGNORECASE,
    )


def _normalise_text(text: str) -> str:
    text = str(text or "").upper()
    text = text.replace("|", " ")
    text = text.replace("_", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _looks_like_passport_mrz(text: str) -> bool:
    lines = [
        re.sub(r"\s+", "", line.upper())
        for line in str(text).splitlines()
        if line.strip()
    ]

    mrz_lines = [
        line
        for line in lines
        if PASSPORT_MRZ_LINE.fullmatch(line) and "<" in line
    ]

    if len(mrz_lines) >= 2:
        return True

    p_line = any(
        line.startswith("P<") or line.startswith("P<<")
        for line in lines
    )

    return p_line and any(
        "<" in line and len(line) >= 30 for line in lines
    )


def _identifier_present(
    identifier: str,
    text: str,
) -> bool:
    if identifier == "aadhaar_number":
        return AADHAAR_NUMBER.search(text) is not None

    if identifier == "pan_number":
        return PAN_NUMBER.search(text) is not None

    if identifier == "epic_number":
        return EPIC_NUMBER.search(text) is not None

    return False


def _score_document(
    text: str,
    raw_text: str,
    config: dict,
) -> tuple[float, list[str]]:
    """
    Returns (score, matched_signals) for one document config.
    """

    score = 0.0
    signals = []

    strong_hits = 0
    medium_hits = 0

    for pattern in config.get("strong", []):
        if (
            re.search(pattern, text, re.IGNORECASE)
            or _compile_flexible(pattern).search(text)
        ):
            score += STRONG_WEIGHT
            strong_hits += 1

    for pattern in config.get("medium", []):
        if (
            re.search(pattern, text, re.IGNORECASE)
            or _compile_flexible(pattern).search(text)
        ):
            score += MEDIUM_WEIGHT
            medium_hits += 1

    keyword_hits = strong_hits + medium_hits

    if strong_hits:
        signals.append(f"{strong_hits} strong keyword match(es)")

    if medium_hits:
        signals.append(f"{medium_hits} supporting keyword match(es)")

    # -----------------------------------------------------
    # Identifier patterns only SUPPORT a classification.
    # A lone 12-digit number must NOT make a document Aadhaar.
    # -----------------------------------------------------

    identifier = config.get("identifier")

    if identifier and keyword_hits > 0:

        if _identifier_present(identifier, text):
            score += IDENTIFIER_SUPPORT_BONUS
            signals.append(f"{identifier} pattern present")

    # -----------------------------------------------------
    # MRZ (passport)
    # -----------------------------------------------------

    if config.get("mrz"):

        if _looks_like_passport_mrz(raw_text):
            score += MRZ_BONUS
            signals.append("MRZ detected")

    return score, signals


# =========================================================
# PUBLIC API
# =========================================================

def classify_document(
    ocr_text: str | list[str],
) -> dict:
    """
    Classify OCR text into a document type.

    Returns a dict with:
      document_type, display_name, confidence, signals, scores
    """

    if isinstance(ocr_text, list):
        lines = [
            str(line).strip()
            for line in ocr_text
            if line
        ]
    else:
        lines = [
            line.strip()
            for line in str(ocr_text or "").splitlines()
            if line.strip()
        ]

    if not lines:
        return {
            "document_type": "unknown",
            "display_name": "Unknown Document",
            "confidence": 0.0,
            "signals": [],
            "scores": {},
        }

    raw_text = "\n".join(lines)
    text = _normalise_text(raw_text)

    scored = []

    for document_type, config in DOCUMENT_PATTERNS.items():

        score, signals = _score_document(
            text,
            raw_text,
            config,
        )

        if score > 0:
            scored.append(
                (document_type, score, signals)
            )

    if not scored:
        return {
            "document_type": "unknown",
            "display_name": "Unknown Document",
            "confidence": 0.0,
            "signals": [],
            "scores": {},
        }

    scored.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    best_type, best_score, best_signals = scored[0]

    second_score = (
        scored[1][1] if len(scored) > 1 else 0.0
    )

    # -----------------------------------------------------
    # Not enough evidence -> report uncertainty, do not guess.
    # -----------------------------------------------------

    if best_score < MIN_SCORE:
        return {
            "document_type": "unknown",
            "display_name": "Unknown Document",
            "confidence": round(
                min(0.49, 0.10 + best_score * 0.05),
                2,
            ),
            "signals": best_signals,
            "scores": {
                item[0]: round(item[1], 2)
                for item in scored
            },
        }

    confidence = min(
        0.99,
        0.50 + best_score * 0.045,
    )

    # Penalise ambiguous collisions.
    if (
        second_score > 0
        and best_score - second_score < 2.0
    ):
        confidence *= 0.85

    return {
        "document_type": best_type,
        "display_name": DOCUMENT_PATTERNS[
            best_type
        ]["display_name"],
        "confidence": round(confidence, 2),
        "signals": best_signals,
        "scores": {
            item[0]: round(item[1], 2)
            for item in scored
        },
    }