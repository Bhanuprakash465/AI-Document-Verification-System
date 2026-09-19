import cv2
import os

from app.services.detector import detect_document


# =========================================================
# CONFIGURATION
# =========================================================

# Nothing bigger than this goes INTO the document detector.
# Large phone photos can be 3000-5000+ pixels wide and there is
# no benefit to running contour detection on the full-size image.
MAX_DIMENSION = 1800

# DocTR's detection/recognition models are trained on document-like
# images and tend to perform poorly (or find nothing at all) on very
# small crops. If, after detection/cropping, the image is smaller
# than this on its shortest side, it is intelligently upscaled
# (aspect ratio preserved) before being handed to OCR.
MIN_OCR_SIDE = 900

# Absolute safety floor. If an image (or crop) is smaller than this
# on either side, it is not safe to run through OCR at all - this
# is the kind of degenerate crop that previously crashed the DocTR
# recognition model with errors like "Given input size: (128x1x16)".
MIN_SAFE_SIDE = 10


def _log_dimensions(label: str, image) -> None:
    h, w = image.shape[:2]
    print(f"[PREPROCESS] {label}: {w}x{h}")


def _upscale_if_small(image):
    """
    Upscales the image (preserving aspect ratio) when its shortest
    side is below MIN_OCR_SIDE. Uses cubic interpolation, which is
    the right choice for enlarging images (INTER_AREA, used for
    shrinking elsewhere in this file, would blur an upscale).
    """

    h, w = image.shape[:2]
    shortest_side = min(h, w)

    if shortest_side <= 0:
        raise ValueError(
            "The document image is invalid (zero-sized)."
        )

    if shortest_side >= MIN_OCR_SIDE:
        return image

    scale = MIN_OCR_SIDE / shortest_side

    # Don't upscale absurdly far - a tiny thumbnail upscaled 20x
    # will not magically contain more legible text, it will just
    # be slow and blurry. Cap the scale factor.
    scale = min(scale, 4.0)

    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))

    print(
        f"[PREPROCESS] Upscaling small image {w}x{h} -> "
        f"{new_w}x{new_h} (x{scale:.2f})"
    )

    return cv2.resize(
        image,
        (new_w, new_h),
        interpolation=cv2.INTER_CUBIC,
    )


def _load_and_prepare(image_path: str):
    """
    Shared steps for both preprocessing modes:
    load -> validate -> downscale-if-huge -> detect/crop -> upscale-if-small.
    Returns a BGR image ready for the mode-specific enhancement step.
    """

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(
            "The uploaded image could not be decoded. "
            "The file may be corrupt or in an unsupported format."
        )

    _log_dimensions("Input image", image)

    h, w = image.shape[:2]

    if min(h, w) < MIN_SAFE_SIDE:
        raise ValueError(
            "The uploaded image is too small to process."
        )

    # --------------------------------------------------
    # Resize BEFORE document detection (performance)
    # --------------------------------------------------

    if max(h, w) > MAX_DIMENSION:

        scale = MAX_DIMENSION / max(h, w)

        new_width = int(w * scale)
        new_height = int(h * scale)

        image = cv2.resize(
            image,
            (new_width, new_height),
            interpolation=cv2.INTER_AREA
        )

    # --------------------------------------------------
    # Detect/crop document
    # --------------------------------------------------
    # detect_document() now contains its own sanity checks and
    # safely falls back to returning the input image unchanged
    # if it cannot find a trustworthy document boundary.
    # --------------------------------------------------

    image = detect_document(image)

    if image is None or image.size == 0:
        raise ValueError(
            "Document detection produced an invalid image."
        )

    cropped_h, cropped_w = image.shape[:2]

    if min(cropped_h, cropped_w) < MIN_SAFE_SIDE:
        raise ValueError(
            "The document could not be reliably located in the image."
        )

    # --------------------------------------------------
    # Upscale small crops so OCR has enough detail to work with
    # --------------------------------------------------

    image = _upscale_if_small(image)

    _log_dimensions("Prepared image (before enhancement)", image)

    return image


def _save_processed(image, image_path: str, suffix: str) -> str:

    processed_path = os.path.join(
        os.path.dirname(image_path),
        f"processed_{suffix}_" + os.path.basename(image_path)
    )

    cv2.imwrite(
        processed_path,
        image,
        [
            cv2.IMWRITE_JPEG_QUALITY,
            90
        ]
    )

    _log_dimensions("Saved processed image", image)
    print(f"[PREPROCESS] Wrote: {processed_path}")

    return processed_path


def preprocess_image(image_path: str, mode: str = "enhanced") -> str:
    """
    Prepares an uploaded image for OCR.

    mode="enhanced" (default): the normal pipeline - grayscale +
        contrast enhancement (CLAHE) + light sharpening. Good for
        most scanned/photographed documents.

    mode="minimal": a lighter-touch fallback pipeline - grayscale
        only, no contrast/sharpening. Used as a second OCR attempt
        when the enhanced pipeline extracts zero text, in case the
        contrast/sharpening step is what destroyed the text (e.g.
        on already high-contrast or very small-font documents).
    """

    image = _load_and_prepare(image_path)

    # --------------------------------------------------
    # Convert to grayscale
    # --------------------------------------------------
    # OCR generally does not need the full colour image.
    # Grayscale also reduces the amount of data processed.
    # --------------------------------------------------

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    if mode == "minimal":
        return _save_processed(gray, image_path, "minimal")

    # --------------------------------------------------
    # Light contrast enhancement
    # --------------------------------------------------

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8)
    )

    enhanced = clahe.apply(gray)

    # --------------------------------------------------
    # Light sharpening
    # --------------------------------------------------
    # Much cheaper than fastNlMeansDenoisingColored.
    # Helps characters remain clear for OCR.
    # --------------------------------------------------

    blurred = cv2.GaussianBlur(
        enhanced,
        (3, 3),
        0
    )

    enhanced = cv2.addWeighted(
        enhanced,
        1.15,
        blurred,
        -0.15,
        0
    )

    return _save_processed(enhanced, image_path, "enhanced")
