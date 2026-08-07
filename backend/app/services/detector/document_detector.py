import cv2
import numpy as np
from app.services.detector.perspective import four_point_transform


def detect_document(image):

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

    for contour in contours:

        area = cv2.contourArea(contour)

        if area < 50000:
            continue

        peri = cv2.arcLength(contour, True)

        approx = cv2.approxPolyDP(
            contour,
            0.02 * peri,
            True
        )

        if len(approx) == 4:

            return four_point_transform(
                image,
                approx.reshape(4, 2)
            )

    return image