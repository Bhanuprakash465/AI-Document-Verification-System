"""
Optional LLM-based verification helper.

The LLM integration is OPTIONAL. It must never break application
startup or the OCR/verification import chain when ``langchain`` is
not installed, so the heavy dependency is imported lazily inside
the function that actually needs it.
"""


def verify_document_with_llm(text_lines):
    """
    Use an LLM to perform a high-level verification of document text.

    Raises a clear RuntimeError if the optional ``langchain``
    dependency is not installed, instead of failing at import time.
    """

    try:
        from langchain import OpenAI
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "LLM verification is optional and requires the "
            "'langchain' package. Install it (pip install langchain) "
            "or disable LLM verification to use this feature."
        ) from exc

    prompt = "\n".join(text_lines or [])

    llm = OpenAI(temperature=0)

    response = llm(
        "Please verify the following document text for "
        f"authenticity and return a short status summary:\n{prompt}"
    )

    return {
        "status": "reviewed",
        "llm_result": str(response),
    }
