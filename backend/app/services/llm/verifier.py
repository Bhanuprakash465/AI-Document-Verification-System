from langchain import OpenAI


def verify_document_with_llm(text_lines):
    """Use an LLM to perform a high-level verification of document text."""
    prompt = "\n".join(text_lines)
    llm = OpenAI(temperature=0)

    response = llm(
        f"Please verify the following document text for authenticity and return a short status summary:\n{prompt}"
    )

    return {
        "status": "reviewed",
        "llm_result": str(response)
    }
