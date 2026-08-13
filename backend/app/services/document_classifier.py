"""
Robust document classifier for VerifyAI.

Classification is based on weighted document-specific signals.
Generic phrases such as "Government of India" are intentionally
given very low weight because they occur on multiple documents.
"""

import re


DOCUMENT_PATTERNS = {
    "passport": {
        "display_name": "Passport",
        "strong": [
            r"\bpassport\b",
            r"\bpassport\s*no\b",
            r"\bpassport\s*number\b",
            r"\bdate\s+of\s+expiry\b",
            r"\bplace\s+of\s+issue\b",
            r"\brepublic\s+of\s+india\b",
        ],
        "medium": [
            r"\bdate\s+of\s+issue\b",
            r"\bplace\s+of\s+birth\b",
            r"\bnationality\b",
            r"\btype\s*/?\s*p\b",
        ],
        "mrz": True,
    },

    "aadhaar": {
        "display_name": "Aadhaar Card",
        "strong": [
            r"\baadhaar\b",
            r"\baadhaar\s+number\b",
            r"\buidai\b",
            r"\bunique\s+identification\s+authority\b",
        ],
        "medium": [
            r"\bunique\s+identification\b",
            r"\bgovernment\s+of\s+india\b",
        ],
        "aadhaar_number": True,
    },

    "pan": {
        "display_name": "PAN Card",
        "strong": [
            r"\bpermanent\s+account\s+number\b",
            r"\bincome\s+tax\s+department\b",
        ],
        "medium": [
            r"\bpan\b",
        ],
        "pan_number": True,
    },

    "driving_license": {
        "display_name": "Driving Licence",
        "strong": [
            r"\bdriving\s+licen[cs]e\b",
            r"\bdriver'?s\s+licen[cs]e\b",
            r"\blicen[cs]e\s+to\s+drive\b",
        ],
        "medium": [
            r"\btransport\s+department\b",
            r"\bmotor\s+vehicle\b",
            r"\bdl\s*(?:no|number)?\b",
        ],
    },

    "voter_id": {
        "display_name": "Voter ID",
        "strong": [
            r"\belection\s+commission\s+of\s+india\b",
            r"\belectors?\s+photo\s+identity\s+card\b",
            r"\bvoter\s+identity\s+card\b",
            r"\bepic\s*(?:no|number)?\b",
        ],
        "medium": [
            r"\bvoter\b",
            r"\belector\b",
            r"\bepic\b",
        ],
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
            r"\bpds\b",
            r"\bfamily\s+card\b",
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


PASSPORT_MRZ_LINE = re.compile(
    r"^[A-Z0-9<]{30,44}$"
)

AADHAAR_NUMBER = re.compile(
    r"\b\d{4}\s?\d{4}\s?\d{4}\b"
)

PAN_NUMBER = re.compile(
    r"\b[A-Z]{5}\d{4}[A-Z]\b",
    re.IGNORECASE,
)

EPIC_NUMBER = re.compile(
    r"\b[A-Z]{3}\d{7}\b",
    re.IGNORECASE,
)


def _normalise_text(text: str) -> str:
    text = str(text or "").upper()

    text = text.replace("|", " ")
    text = text.replace("_", " ")

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def _looks_like_passport_mrz(text: str) -> bool:

    lines = [
        re.sub(
            r"\s+",
            "",
            line.upper(),
        )
        for line in str(text).splitlines()
        if line.strip()
    ]

    mrz_lines = [
        line
        for line in lines
        if PASSPORT_MRZ_LINE.fullmatch(line)
        and "<" in line
    ]

    if len(mrz_lines) >= 2:
        return True

    # OCR sometimes drops/changes a few MRZ characters.
    p_line = any(
        line.startswith("P<")
        or line.startswith("P<<")
        for line in lines
    )

    return p_line and any(
        "<" in line and len(line) >= 30
        for line in lines
    )


def _score_document(
    text: str,
    lines: list[str],
    config: dict,
) -> float:

    score = 0.0

    for pattern in config.get("strong", []):
        if re.search(
            pattern,
            text,
            re.IGNORECASE,
        ):
            score += 4.0

    for pattern in config.get("medium", []):
        if re.search(
            pattern,
            text,
            re.IGNORECASE,
        ):
            score += 1.5

    if config.get("aadhaar_number"):
        if AADHAAR_NUMBER.search(text):
            score += 4.0

    if config.get("pan_number"):
        if PAN_NUMBER.search(text):
            score += 4.0

    if config.get("mrz"):
        if _looks_like_passport_mrz(
            "\n".join(lines)
        ):
            score += 10.0

    return score


def classify_document(
    ocr_text: str | list[str],
) -> dict:

    if isinstance(ocr_text, list):

        lines = [
            str(line).strip()
            for line in ocr_text
            if line
        ]

    else:

        lines = [
            line.strip()
            for line in str(
                ocr_text or ""
            ).splitlines()
            if line.strip()
        ]

    if not lines:

        return {
            "document_type": "unknown",
            "display_name": "Unknown Document",
            "confidence": 0.0,
        }

    text = _normalise_text(
        "\n".join(lines)
    )

    scores = []

    for document_type, config in DOCUMENT_PATTERNS.items():

        score = _score_document(
            text,
            lines,
            config,
        )

        if score > 0:

            scores.append(
                (
                    document_type,
                    score,
                )
            )

    if not scores:

        return {
            "document_type": "unknown",
            "display_name": "Unknown Document",
            "confidence": 0.0,
        }

    scores.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    best_type, best_score = scores[0]

    second_score = (
        scores[1][1]
        if len(scores) > 1
        else 0.0
    )

    # Confidence based on absolute evidence.
    confidence = min(
        0.99,
        0.50 + best_score * 0.045,
    )

    # Penalise very close classification collisions.
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
        "confidence": round(
            confidence,
            2,
        ),
    }