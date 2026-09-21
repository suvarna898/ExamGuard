import cv2
import numpy as np


# ----------------------------------------
# LOAD FACE DETECTOR
# ----------------------------------------
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades +
    "haarcascade_frontalface_default.xml"
)


# ----------------------------------------
# DETECT FACE
# ----------------------------------------
def detect_face(image_data):

    # Convert image bytes into NumPy array
    image_array = np.frombuffer(
        image_data,
        dtype=np.uint8
    )


    # Convert image array into OpenCV image
    image = cv2.imdecode(
        image_array,
        cv2.IMREAD_COLOR
    )


    # Check whether image was decoded
    if image is None:
        return False, None


    # ----------------------------------------
    # CONVERT TO GRAYSCALE
    # ----------------------------------------
    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )


    # ----------------------------------------
    # DETECT FACES
    # ----------------------------------------
    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5
    )


    # ----------------------------------------
    # DRAW FACE RECTANGLE
    # ----------------------------------------
    for (x, y, w, h) in faces:

        cv2.rectangle(
            image,
            (x, y),
            (x + w, y + h),
            (0, 255, 0),
            2
        )

        return True, image


    # No face detected
    return False, image