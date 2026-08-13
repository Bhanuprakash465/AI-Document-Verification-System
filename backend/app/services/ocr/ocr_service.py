"""
OCR service for VerifyAI.

Runs docTR OCR and performs lightweight normalization
without destroying the original recognized text.
"""

from functools import lru_cache
from pathlib import Path
import re

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
            "OCR is not available. "
            "Install the backend requirements "
            "and ensure DocTR model weights "
            "are available."
        ) from exc


def _clean_ocr_line(
    text: str,
) -> str:

    text = str(
        text or ""
    ).strip()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text


def _is_useful_line(
    text: str,
) -> bool:

    if not text:
        return False

    # Ignore extremely tiny OCR fragments.
    if len(text.strip()) < 2:
        return False

    return True


def _extract_page_lines(
    page,
) -> list[str]:

    lines = []

    for block in page.blocks:

        for line in block.lines:

            words = []

            for word in line.words:

                value = getattr(
                    word,
                    "value",
                    str(word),
                )

                value = _clean_ocr_line(
                    value
                )

                if value:
                    words.append(value)

            if not words:
                continue

            text = _clean_ocr_line(
                " ".join(words)
            )

            if _is_useful_line(text):
                lines.append(text)

    return lines


def _deduplicate_lines(
    lines: list[str],
) -> list[str]:

    result = []

    seen = set()

    for line in lines:

        normalized = re.sub(
            r"\s+",
            " ",
            line.lower(),
        ).strip()

        if not normalized:
            continue

        if normalized in seen:
            continue

        seen.add(normalized)

        result.append(line)

    return result


def extract_text(
    image_path: str,
) -> list[str]:

    try:

        from doctr.io import DocumentFile

        path = Path(
            image_path
        )

        # =====================================================
        # LOAD
        # =====================================================

        if path.suffix.lower() == ".pdf":

            document = DocumentFile.from_pdf(
                str(path)
            )

        else:

            document = DocumentFile.from_images(
                str(path)
            )

        # =====================================================
        # OCR
        # =====================================================

        model = _get_model()

        result = model(
            document
        )

        # =====================================================
        # EXTRACT STRUCTURED LINES
        # =====================================================

        lines = []

        for page_index, page in enumerate(
            result.pages
        ):

            page_lines = _extract_page_lines(
                page
            )

            print(
                f"[OCR] Page {page_index + 1}: "
                f"{len(page_lines)} lines"
            )

            lines.extend(
                page_lines
            )

        lines = _deduplicate_lines(
            lines
        )

        # =====================================================
        # FALLBACK
        # =====================================================

        if not lines:

            rendered = result.render()

            lines = [
                _clean_ocr_line(line)
                for line in rendered.splitlines()
                if _is_useful_line(
                    _clean_ocr_line(line)
                )
            ]

            lines = _deduplicate_lines(
                lines
            )

        # =====================================================
        # DEBUG
        # =====================================================

        print(
            "[OCR] Extracted lines:"
        )

        for index, line in enumerate(
            lines
        ):

            print(
                f"[OCR {index}] {line}"
            )

        return lines

    except HTTPException:

        raise

    except Exception as exc:

        print(
            "[OCR ERROR]",
            repr(exc),
        )

        raise HTTPException(
            status_code=503,
            detail=(
                "OCR processing failed. "
                "Confirm that DocTR and its "
                "model weights are available."
            ),
        ) from exc