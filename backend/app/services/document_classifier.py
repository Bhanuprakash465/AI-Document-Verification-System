"""
Document classifier for VerifyAI.

Detects supported Indian identity and government documents
from OCR-extracted text.
"""

import re


DOCUMENT_PATTERNS = {
    "aadhaar": {
        "display_name": "Aadhaar Card",
        "patterns": [
            r"\baadhaar\b",
            r"\buidai\b",
            r"unique identification",
            r"government of india",
            r"\b\d{4}\s\d{4}\s\d{4}\b",
        ],
    },

    "pan": {
        "display_name": "PAN Card",
        "patterns": [
            r"permanent account number",
            r"income tax department",
            r"\bpan\b",
            r"\b[a-z]{5}\d{4}[a-z]\b",
        ],
    },

    "driving_license": {
        "display_name": "Driving Licence",
        "patterns": [
            r"driving licence",
            r"driving license",
            r"driver'?s license",
            r"driver'?s licence",
            r"transport department",
            r"motor vehicle",
            r"licence to drive",
            r"license to drive",
            r"\bdl\s*(?:no|number)?\b",
        ],
    },

    "passport": {
        "display_name": "Passport",
        "patterns": [
            r"\bpassport\b",
            r"republic of india",
            r"government of india",
            r"nationality",
            r"date of issue",
            r"date of expiry",
            r"place of issue",
            r"\btype\s*p\b",
        ],
    },

    "voter_id": {
        "display_name": "Voter ID",
        "patterns": [
            r"election commission of india",
            r"election commission",
            r"voter",
            r"elector",
            r"electors photo identity card",
            r"epic",
            r"epic no",
            r"voter identity card",
        ],
    },

    "ration_card": {
        "display_name": "Ration Card",
        "patterns": [
            r"ration card",
            r"food and civil supplies",
            r"food supplies department",
            r"public distribution system",
            r"\bpds\b",
            r"family card",
        ],
    },

    "vehicle_rc": {
        "display_name": "Vehicle Registration Certificate",
        "patterns": [
            r"registration certificate",
            r"certificate of registration",
            r"transport department",
            r"registered owner",
            r"registration number",
            r"vehicle class",
            r"chassis number",
            r"engine number",
        ],
    },

    "gst_certificate": {
        "display_name": "GST Certificate",
        "patterns": [
            r"goods and services tax",
            r"gst certificate",
            r"gst registration",
            r"gstin",
            r"taxpayer",
            r"registration number",
        ],
    },
}


def _normalise_text(text: str) -> str:
    """
    Normalise OCR text before classification.
    """

    text = text.lower()

    # Replace common OCR separators with spaces.
    text = re.sub(r"[_|]+", " ", text)

    # Collapse multiple spaces.
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def _calculate_score(
    text: str,
    patterns: list[str],
) -> float:
    """
    Calculate a simple confidence score based on
    how many document-specific indicators were detected.
    """

    matches = 0

    for pattern in patterns:
        try:
            if re.search(pattern, text, re.IGNORECASE):
                matches += 1
        except re.error:
            continue

    if matches == 0:
        return 0.0

    # Base score increases with matched indicators.
    score = 0.4 + (matches * 0.12)

    return min(score, 0.98)


def classify_document(
    ocr_text: str | list[str],
) -> dict:
    """
    Classify a document from OCR text.

    Returns:

    {
        "document_type": "...",
        "display_name": "...",
        "confidence": 0.0
    }
    """

    # Support both a string and list[str].
    if isinstance(ocr_text, list):
        text = " ".join(
            str(line)
            for line in ocr_text
            if line
        )
    else:
        text = str(ocr_text or "")

    text = _normalise_text(text)

    if not text:
        return {
            "document_type": "unknown",
            "display_name": "Unknown Document",
            "confidence": 0.0,
        }

    candidates = []

    for document_type, config in DOCUMENT_PATTERNS.items():

        score = _calculate_score(
            text,
            config["patterns"],
        )

        if score > 0:
            candidates.append(
                {
                    "document_type": document_type,
                    "display_name": config["display_name"],
                    "confidence": score,
                }
            )

    # No document matched.
    if not candidates:
        return {
            "document_type": "unknown",
            "display_name": "Unknown Document",
            "confidence": 0.0,
        }

    # Highest scoring document wins.
    candidates.sort(
        key=lambda item: item["confidence"],
        reverse=True,
    )

    best = candidates[0]

    return {
        "document_type": best["document_type"],
        "display_name": best["display_name"],
        "confidence": round(
            best["confidence"],
            2,
        ),
    }