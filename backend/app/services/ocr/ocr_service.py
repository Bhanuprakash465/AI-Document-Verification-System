"""OCR service for VerifyAI."""

from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException


@lru_cache(maxsize=1)
def _get_model():

    try:

        print("[OCR] Loading DocTR model...")

        from doctr.models import ocr_predictor

        model = ocr_predictor(
            pretrained=True,
            assume_straight_pages=True,
        )

        print("[OCR] DocTR model loaded.")

        return model

    except Exception as exc:

        raise RuntimeError(
            "OCR is not available. Install the backend "
            "requirements and ensure DocTR model weights "
            "are available."
        ) from exc


def extract_text(
    image_path: str,
) -> list[str]:

    try:

        from doctr.io import DocumentFile


        path = Path(image_path)


        # =================================================
        # LOAD DOCUMENT
        # =================================================

        if path.suffix.lower() == ".pdf":

            document = DocumentFile.from_pdf(
                str(path)
            )

        else:

            document = DocumentFile.from_images(
                str(path)
            )


        # =================================================
        # OCR
        # =================================================

        model = _get_model()

        result = model(document)


        # =================================================
        # EXTRACT OCR TEXT
        # =================================================

        lines = []


        for page in result.pages:

            for block in page.blocks:

                for line in block.lines:

                    words = []

                    for word in line.words:

                        value = (
                            word.value
                            if hasattr(word, "value")
                            else str(word)
                        )

                        value = value.strip()

                        if value:

                            words.append(value)


                    if words:

                        text = " ".join(words).strip()

                        if text:

                            lines.append(text)


        # =================================================
        # FALLBACK
        # =================================================

        if not lines:

            rendered = result.render()

            lines = [
                line.strip()
                for line in rendered.splitlines()
                if line.strip()
            ]


        # =================================================
        # DEBUG
        # =================================================

        print("[OCR] Extracted lines:")

        for index, line in enumerate(lines):

            print(
                f"[OCR {index}] {line}"
            )


        return lines


    except HTTPException:

        raise


    except Exception as exc:

        print(
            "[OCR ERROR]",
            str(exc)
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "OCR processing failed. "
                "Confirm that DocTR and its model "
                "weights are available."
            ),
        ) from exc