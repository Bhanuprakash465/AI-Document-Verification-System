"""OCR adapter.

The model is loaded lazily so starting the API never downloads a model or spends
memory until a document is actually uploaded.
"""

from functools import lru_cache

from fastapi import HTTPException


@lru_cache(maxsize=1)
def _get_model():
    try:
        from doctr.models import ocr_predictor
        return ocr_predictor(pretrained=True)
    except Exception as exc:  # model package, weights, or torch may be unavailable
        raise RuntimeError(
            "OCR is not available. Install the backend requirements and ensure the "
            "DocTR model weights can be downloaded on the first request."
        ) from exc


def extract_text(image_path: str) -> list[str]:
    try:
        from doctr.io import DocumentFile
        document = (
            DocumentFile.from_pdf(image_path)
            if image_path.lower().endswith(".pdf")
            else DocumentFile.from_images(image_path)
        )
        rendered_text = _get_model()(document).render()
        return [line.strip() for line in rendered_text.splitlines() if line.strip()]
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="OCR processing failed. Confirm that DocTR and its model weights are available.",
        ) from exc
