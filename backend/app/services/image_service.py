import cv2
import os
def preprocess_image(image_path):
    image = cv2.imread(image_path)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    denoised = cv2.GaussianBlur(gray, (5, 5), 0)
    processed_path = os.path.join(
        "uploads",
        "processed_" + os.path.basename(image_path)
    )
    cv2.imwrite(processed_path, denoised)
    return processed_path