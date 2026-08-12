"""Fast OCR adapter for document verification."""

from functools import lru_cache

from fastapi import HTTPException


# =========================================================
# OCR MODEL
# =========================================================

@lru_cache(maxsize=1)
def _get_model():

    try:

        from doctr.models import ocr_predictor

        print("[OCR] Loading DocTR model...")

        model = ocr_predictor(
            pretrained=True,
            det_arch="db_resnet50",
            reco_arch="crnn_vgg16_bn",
            assume_straight_pages=True,
            straighten_pages=False,
            detect_language=False,
        )

        print("[OCR] DocTR model loaded.")

        return model

    except Exception as exc:

        raise RuntimeError(
            "OCR is not available. Install the backend "
            "requirements and ensure the DocTR model "
            "weights are available."
        ) from exc


# =========================================================
# OCR EXTRACTION
# =========================================================

def extract_text(
    image_path: str
) -> list[str]:

    try:

        from doctr.io import DocumentFile


        # -------------------------------------------------
        # Load document
        # -------------------------------------------------

        if image_path.lower().endswith(".pdf"):

            document = DocumentFile.from_pdf(
                image_path
            )

        else:

            document = DocumentFile.from_images(
                image_path
            )


        # -------------------------------------------------
        # Get cached model
        # -------------------------------------------------

        model = _get_model()


        # -------------------------------------------------
        # Run OCR
        # -------------------------------------------------

        result = model(
            document
        )


        # -------------------------------------------------
        # Extract text
        # -------------------------------------------------

        rendered_text = result.render()


        return [
            line.strip()
            for line in rendered_text.splitlines()
            if line.strip()
        ]


    except HTTPException:

        raise


    except Exception as exc:

        print(
            f"[OCR ERROR] {exc}"
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "OCR processing failed. "
                "Confirm that DocTR and its model "
                "weights are available."
            )
        ) from exc