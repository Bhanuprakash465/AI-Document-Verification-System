import cv2
import numpy as np
from app.services.detector.perspective import four_point_transform


# =========================================================
# SANITY-CHECK THRESHOLDS
# =========================================================
# The previous version accepted ANY 4-point contour whose area
# was at least 50000 px^2. On a resized image that can be as
# large as ~1800x1800, 50000 px^2 is less than ~2% of the frame,
# so the detector would happily "detect" a stray rectangle
# (a photo box, a logo, a table cell, JPEG/Canny noise) instead
# of the actual document, and crop to that tiny/incorrectly
# shaped region. That is the root cause of OCR being fed a
# 387x516 (or, in worse cases, a near-1px-wide) sliver of the
# original document, which then reports 0 detected lines - or
# crashes the recognition model on a degenerate crop.
#
# These thresholds make the detector reject any candidate that
# does not look like "most of the photographed document" and
# fall back to using the full (undistorted) image instead,
# which is always a safe choice for OCR.
# =========================================================

MIN_AREA_RATIO = 0.20      # contour must cover >= 20% of the frame
MIN_SIDE_PIXELS = 150      # cropped width/height must be >= 150px
MIN_ASPECT_RATIO = 0.20    # width/height must not be too "thin"
MAX_ASPECT_RATIO = 5.0     # ... in either direction


def _is_valid_document_crop(warped, image_area: float) -> bool:
    """
    Returns True only if the warped/cropped region looks like a
    real document (reasonable size + reasonable aspect ratio),
    not a degenerate sliver caused by a bad contour match.
    """

    if warped is None or warped.size == 0:
        return False

    h, w = warped.shape[:2]

    if h < MIN_SIDE_PIXELS or w < MIN_SIDE_PIXELS:
        print(
            f"[DETECTOR] Rejected crop: too small ({w}x{h})"
        )
        return False

    aspect_ratio = w / float(h)

    if aspect_ratio < MIN_ASPECT_RATIO or aspect_ratio > MAX_ASPECT_RATIO:
        print(
            f"[DETECTOR] Rejected crop: implausible aspect "
            f"ratio ({w}x{h} -> {aspect_ratio:.2f})"
        )
        return False

    crop_area = h * w

    if image_area > 0 and (crop_area / image_area) < MIN_AREA_RATIO:
        print(
            f"[DETECTOR] Rejected crop: covers only "
            f"{(crop_area / image_area) * 100:.1f}% of the frame"
        )
        return False

    return True


def detect_document(image):

    original_h, original_w = image.shape[:2]
    image_area = float(original_h * original_w)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    blur = cv2.GaussianBlur(gray, (5, 5), 0)

    edged = cv2.Canny(blur, 50, 150)

    contours, _ = cv2.findContours(
        edged,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    contours = sorted(
        contours,
        key=cv2.contourArea,
        reverse=True
    )

    # Only the largest few contours are worth checking - a document
    # photo should produce its outline as one of the biggest shapes.
    for contour in contours[:5]:

        area = cv2.contourArea(contour)

        # Contour must cover a meaningful portion of the frame
        # BEFORE we even attempt a perspective transform.
        if image_area > 0 and (area / image_area) < MIN_AREA_RATIO:
            continue

        peri = cv2.arcLength(contour, True)

        approx = cv2.approxPolyDP(
            contour,
            0.02 * peri,
            True
        )

        if len(approx) != 4:
            continue

        warped = four_point_transform(
            image,
            approx.reshape(4, 2)
        )

        if _is_valid_document_crop(warped, image_area):

            print(
                f"[DETECTOR] Using detected document crop: "
                f"{warped.shape[1]}x{warped.shape[0]} "
                f"(from {original_w}x{original_h})"
            )

            return warped

        # This candidate looked like a 4-point shape but produced
        # an unusable crop - keep checking the next contour instead
        # of immediately giving up on detection entirely.

    print(
        f"[DETECTOR] No reliable document contour found - "
        f"using full image ({original_w}x{original_h})"
    )

    return image