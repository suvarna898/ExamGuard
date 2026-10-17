import cv2
import numpy as np
from datetime import datetime
from database import get_db

# Pre-trained Haar Cascade classifier that ships with OpenCV.
# The project spec explicitly calls for this (no custom model
# training required for face presence checks).
_FACE_CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
_face_cascade = cv2.CascadeClassifier(_FACE_CASCADE_PATH)


def detect_face(image_data):
    """
    Takes raw JPEG bytes (a single webcam frame sent from the
    exam page) and returns True if at least one face is visible,
    False otherwise.

    This performs presence detection only - no face recognition
    or identity/liveness checks, matching the project scope.
    """

    image_array = np.frombuffer(image_data, np.uint8)
    frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if frame is None:
        # Couldn't decode the frame at all - treat as "can't confirm
        # presence" rather than crashing the monitoring loop.
        return False

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = _face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(60, 60),
    )

    return len(faces) > 0

def close_open_face_event(
    candidate_id,
    session_id
):

    connection = get_db()

    try:

        row = connection.execute("""
            SELECT *
            FROM face_events
            WHERE candidate_id = ?
            AND session_id = ?
            AND ended_at IS NULL
            ORDER BY id DESC
            LIMIT 1
        """, (
            candidate_id,
            session_id
        )).fetchone()


        # No open face event
        if not row:

            return


        ended_at = datetime.now()


        started_at = datetime.fromisoformat(
            row["started_at"]
        )


        duration = (
            ended_at - started_at
        ).total_seconds()


        connection.execute("""
            UPDATE face_events

            SET
                ended_at = ?,
                duration_seconds = ?

            WHERE id = ?
        """, (
            ended_at.isoformat(),
            duration,
            row["id"]
        ))


        connection.commit()

    finally:

        connection.close()