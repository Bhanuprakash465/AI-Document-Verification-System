import cv2
import os
from app.services.detector import detect_document

def preprocess_image(image_path):

    image = cv2.imread(image_path)
    if image is None:
        raise ValueError("The uploaded image could not be decoded.")

    image = detect_document(image)

    # Resize if image is huge
    h, w = image.shape[:2]

    if max(h, w) > 1800:
        scale = 1800 / max(h, w)
        image = cv2.resize(image, None, fx=scale, fy=scale)

    # Convert to LAB color space
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

    l, a, b = cv2.split(lab)

    # Improve contrast
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    l = clahe.apply(l)

    lab = cv2.merge((l,a,b))

    enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    # Small denoise
    enhanced = cv2.fastNlMeansDenoisingColored(
        enhanced,
        None,
        10,
        10,
        7,
        21
    )

    processed_path = os.path.join(os.path.dirname(image_path), "processed_" + os.path.basename(image_path))

    cv2.imwrite(processed_path, enhanced)

    return processed_path
