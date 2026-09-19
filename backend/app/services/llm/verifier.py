"""
Optional LLM-based verification helper (experimental, NOT used by the
production pipeline).

Nothing in the document pipeline imports this module. It exists only as
an isolated hook for future experimentation and requires the optional
``langchain`` dependency plus an OpenAI API key. Core verification works
without it and never claims LLM/authenticity verification.
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
