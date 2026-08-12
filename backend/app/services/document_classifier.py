"""
Document classifier.

Determines which supported document type is present
based on OCR text.
"""

from app.services.documents import (
    aadhaar,
    pan,
    passport,
    voter_id,
    driving_license,
)


# ---------------------------------------------------------
# Supported document types
# ---------------------------------------------------------

DOCUMENT_HANDLERS = [

    (
        aadhaar.DOCUMENT_TYPE,
        aadhaar.DISPLAY_NAME,
        aadhaar.detect,
    ),

    (
        pan.DOCUMENT_TYPE,
        pan.DISPLAY_NAME,
        pan.detect,
    ),

    (
        passport.DOCUMENT_TYPE,
        passport.DISPLAY_NAME,
        passport.detect,
    ),

    (
        voter_id.DOCUMENT_TYPE,
        voter_id.DISPLAY_NAME,
        voter_id.detect,
    ),

    (
        driving_license.DOCUMENT_TYPE,
        driving_license.DISPLAY_NAME,
        driving_license.detect,
    ),

]


# ---------------------------------------------------------
# Classify document
# ---------------------------------------------------------

def classify_document(
    text: str
) -> dict:
    """
    Identify the uploaded document type.

    Returns:
        {
            "document_type": "...",
            "display_name": "...",
            "confidence": ...
        }
    """

    if not text or not text.strip():

        return {
            "document_type": "unknown",
            "display_name": "Unknown Document",
            "confidence": 0.0,
        }


    text_lower = text.lower()


    # -----------------------------------------------------
    # Score every document type
    # -----------------------------------------------------

    results = []


    for (
        document_type,
        display_name,
        detector,
    ) in DOCUMENT_HANDLERS:

        try:

            detected = detector(
                text
            )

            if detected:

                # Basic confidence score.
                #
                # This is intentionally conservative.
                # Later we can replace this with a proper
                # ML classifier.

                confidence = 0.80

                results.append(
                    {
                        "document_type":
                            document_type,

                        "display_name":
                            display_name,

                        "confidence":
                            confidence,
                    }
                )

        except Exception as exc:

            print(
                f"[CLASSIFIER] "
                f"{document_type} detection failed: "
                f"{exc}"
            )


    # -----------------------------------------------------
    # No document detected
    # -----------------------------------------------------

    if not results:

        return {
            "document_type": "unknown",
            "display_name": "Unknown Document",
            "confidence": 0.0,
        }


    # -----------------------------------------------------
    # Choose strongest result
    # -----------------------------------------------------

    best_result = max(
        results,
        key=lambda item:
            item["confidence"]
    )


    return best_result