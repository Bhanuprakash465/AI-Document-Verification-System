"""
OCR service for VerifyAI.

Runs docTR OCR and performs lightweight normalization
without destroying the original recognized text.
"""

from functools import lru_cache
from pathlib import Path
import re

from fastapi import HTTPException

# Identity documents are effectively 1-2 pages. Any PDF larger
# than this is truncated before OCR to keep requests bounded.
MAX_PDF_PAGES = 5

# Upper bound for PDF raster resolution. High-resolution or heavily
# compressed PDFs can otherwise consume excessive CPU/RAM during
# rasterization; DocTR forwards kwargs to pypdfium2's page render.
MAX_PDF_DPI = 150


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
) -> tuple[list[str], dict]:
    """
    Returns (lines, stats) where stats carries diagnostic counts
    (blocks/words/confidence) used only for logging.
    """

    lines = []

    word_count = 0
    confidences = []

    for block in page.blocks:

        for line in block.lines:

            words = []

            for word in line.words:

                word_count += 1

                confidence = getattr(
                    word,
                    "confidence",
                    None,
                )

                if isinstance(confidence, (int, float)):
                    confidences.append(float(confidence))

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

    stats = {
        "blocks": len(page.blocks),
        "words": word_count,
        "avg_confidence": (
            round(sum(confidences) / len(confidences), 3)
            if confidences
            else None
        ),
    }

    return lines, stats


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
    max_dpi: int = 150,
) -> list[str]:

    try:

        from doctr.io import DocumentFile

        path = Path(
            image_path
        )

        is_pdf = path.suffix.lower() == ".pdf"

        # =====================================================
        # DIAGNOSTICS: input dimensions (images only - PDF pages
        # are rasterized internally by DocTR, one size per page)
        # =====================================================

        if not is_pdf:

            try:
                import cv2

                debug_image = cv2.imread(str(path))

                if debug_image is not None:
                    h, w = debug_image.shape[:2]
                    print(f"[OCR] Input image: {w}x{h}")

            except Exception:
                # Diagnostics only - never let this block OCR.
                pass

        # =====================================================
        # LOAD
        # =====================================================

        if is_pdf:

            # Bounded rasterization: cap pages (below) and resolution so
            # hostile/oversized PDFs fail gracefully instead of exhausting
            # CPU/RAM. DocTR forwards kwargs to pypdfium2 page rendering.
            render_scale = max(1.0, min(float(max_dpi), float(MAX_PDF_DPI)) / 72.0)
            try:
                document = DocumentFile.from_pdf(
                    str(path),
                    scale=render_scale,
                )
            except TypeError:
                # Older DocTR/pypdfium2 builds without the scale kwarg.
                document = DocumentFile.from_pdf(
                    str(path)
                )

        else:

            document = DocumentFile.from_images(
                str(path)
            )

        print(f"[OCR] Number of pages: {len(document)}")

        # -----------------------------------------------------
        # PDF PAGE CAP
        # -----------------------------------------------------
        # Very large PDFs would be extremely slow (DocTR runs per
        # page). Only the first MAX_PDF_PAGES pages are processed;
        # identity documents are effectively single/double page.
        # -----------------------------------------------------

        if len(document) > MAX_PDF_PAGES:

            print(
                f"[OCR] Capping PDF to first "
                f"{MAX_PDF_PAGES} pages "
                f"(had {len(document)})."
            )

            document = document[:MAX_PDF_PAGES]

        # =====================================================
        # OCR
        # =====================================================

        print("[OCR] Running DocTR...")

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

            page_lines, stats = _extract_page_lines(
                page
            )

            print(
                f"[OCR] Page {page_index + 1}: "
                f"{stats['blocks']} blocks"
            )

            print(
                f"[OCR] Page {page_index + 1}: "
                f"{len(page_lines)} lines"
            )

            print(
                f"[OCR] Page {page_index + 1}: "
                f"{stats['words']} words"
            )

            if stats["avg_confidence"] is not None:
                print(
                    f"[OCR] Page {page_index + 1}: "
                    f"avg confidence {stats['avg_confidence']}"
                )

            lines.extend(
                page_lines
            )

        lines = _deduplicate_lines(
            lines
        )

        # =====================================================
        # FALLBACK (rendered text)
        # =====================================================
        # The structured block/line/word walk above is the normal
        # path. If it produced nothing, DocTR's own .render() is
        # tried as a last resort before giving up - this occasionally
        # recovers text that the structured walk missed.
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

        print(f"[OCR] Total lines: {len(lines)}")

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