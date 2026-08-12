"""
Generic document handler.

Used when the uploaded document does not match
one of the supported document types.
"""


DOCUMENT_TYPE = "unknown"

DISPLAY_NAME = "Unknown Document"


# ---------------------------------------------------------
# Generic detection
# ---------------------------------------------------------

def detect(text: str) -> bool:
    """
    Generic handler always returns True.

    It is used as the final fallback after all
    supported document types have been checked.
    """

    return True


# ---------------------------------------------------------
# Generic field extraction
# ---------------------------------------------------------

def extract_fields(text: str) -> dict:
    """
    Return basic information for unsupported documents.
    """

    cleaned_text = text.strip()


    return {

        "raw_text_available": bool(
            cleaned_text
        ),

        "text_length": len(
            cleaned_text
        ),

    }