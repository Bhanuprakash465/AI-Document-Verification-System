import cv2
import os

from app.services.detector import detect_document


MAX_DIMENSION = 1800


def preprocess_image(image_path: str) -> str:

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(
            "The uploaded image could not be decoded."
        )

    # --------------------------------------------------
    # Resize BEFORE document detection
    # --------------------------------------------------
    # This is important for performance.
    # Large phone images can be 3000-5000+ pixels wide.
    # There is no reason to run the detector on that size.
    # --------------------------------------------------

    h, w = image.shape[:2]

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

    image = detect_document(image)


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


    # --------------------------------------------------
    # Save processed image
    # --------------------------------------------------

    processed_path = os.path.join(
        os.path.dirname(image_path),
        "processed_" + os.path.basename(image_path)
    )

    cv2.imwrite(
        processed_path,
        enhanced,
        [
            cv2.IMWRITE_JPEG_QUALITY,
            90
        ]
    )

    return processed_path