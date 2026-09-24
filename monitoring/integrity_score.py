from datetime import datetime
from database import get_db
import sys


# ============================================================
# 1. EVENT WEIGHTS
# ============================================================

EVENT_WEIGHTS = {
    "tab_switch": 10,
    "focus_lost": 5,

    "copy_attempt": 15,
    "paste_attempt": 15,
    "cut_attempt": 15,

    "right_click": 5,

    # Normal / informational events
    "tab_return": 0,
    "focus_gained": 0,
    "keyboard_activity": 0,
    "mouse_activity": 0,
    "answer_selected": 0,
    "answer_saved": 0,
    "exam_started": 0,
    "exam_paused": 0,
    "exam_resumed": 0,
}


# ============================================================
# 2. GET BROWSER EVENTS
# ============================================================

def get_browser_events(candidate_id, session_id):
    """
    Fetch all raw browser events for one exam session.

    Data comes from browser_events table.

    Example events:
        tab_switch
        focus_lost
        copy_attempt
        paste_attempt
        right_click
        keyboard_activity
        mouse_activity
    """

    connection = get_db()

    try:

        rows = connection.execute("""
            SELECT event_type
            FROM browser_events
            WHERE candidate_id = ?
            AND session_id = ?
        """, (
            candidate_id,
            session_id
        )).fetchall()

        return [dict(row) for row in rows]

    finally:
        connection.close()


# ============================================================
# 3. CALCULATE EVENT PENALTY
# ============================================================

def calculate_event_penalty(browser_events):
    """
    Calculate total penalty from browser events.

    Each event gets its penalty from EVENT_WEIGHTS.
    Unknown events receive 0 penalty.
    """

    total_penalty = 0

    for event in browser_events:

        event_type = event["event_type"]

        penalty = EVENT_WEIGHTS.get(
            event_type,
            0
        )

        total_penalty += penalty

    return total_penalty


# ============================================================
# 4. CALCULATE FACE PRESENCE RATIO
# ============================================================

def calculate_face_presence_ratio(
    candidate_id,
    session_id
):
    """
    Calculate percentage of exam time during which
    the candidate's face was present.

    Formula:

        Face Presence Ratio =
        Present Duration / Exam Duration * 100

    Face absence duration comes from face_events.

    Exam duration comes from exam_sessions.
    """

    connection = get_db()

    try:

        # ----------------------------------------------------
        # Get total confirmed face-absence duration
        # ----------------------------------------------------

        row = connection.execute("""
            SELECT
                COALESCE(
                    SUM(duration_seconds),
                    0
                ) AS absent_duration
            FROM face_events
            WHERE candidate_id = ?
            AND session_id = ?
            AND event_type = 'face_absent'
            AND duration_seconds IS NOT NULL
        """, (
            candidate_id,
            session_id
        )).fetchone()

        absent_duration = row["absent_duration"]


        # ----------------------------------------------------
        # Get exam start and submission time
        # ----------------------------------------------------

        session_row = connection.execute("""
            SELECT
                started_at,
                submitted_at
            FROM exam_sessions
            WHERE session_id = ?
            AND candidate_id = ?
        """, (
            session_id,
            candidate_id
        )).fetchone()


        # No session found
        if not session_row:
            return 0


        # No start time
        if not session_row["started_at"]:
            return 0


        # ----------------------------------------------------
        # Convert start time
        # ----------------------------------------------------

        start_time = datetime.fromisoformat(
            session_row["started_at"]
        )


        # ----------------------------------------------------
        # Determine end time
        #
        # If submitted:
        #     use submitted_at
        #
        # If still running:
        #     use current time
        # ----------------------------------------------------

        if session_row["submitted_at"]:

            end_time = datetime.fromisoformat(
                session_row["submitted_at"]
            )

        else:

            end_time = datetime.now()


        # ----------------------------------------------------
        # Calculate total exam duration
        # ----------------------------------------------------

        exam_duration = (
            end_time - start_time
        ).total_seconds()


        if exam_duration <= 0:
            return 0


        # ----------------------------------------------------
        # Calculate face-present duration
        # ----------------------------------------------------

        present_duration = (
            exam_duration -
            absent_duration
        )


        # Prevent negative duration
        present_duration = max(
            present_duration,
            0
        )


        # ----------------------------------------------------
        # Calculate percentage
        # ----------------------------------------------------

        ratio = (
            present_duration /
            exam_duration
        )


        face_presence_ratio = ratio * 100


        # Keep value between 0 and 100
        face_presence_ratio = min(
            max(face_presence_ratio, 0),
            100
        )


        return round(
            face_presence_ratio,
            2
        )

    finally:

        connection.close()


# ============================================================
# 5. CALCULATE INTEGRITY SCORE
# ============================================================

def calculate_integrity_score(
    browser_events,
    face_presence_ratio
):
    """
    Calculate final integrity score.

    Starting score = 100

    Final score =
        100
        - browser event penalty
        - face presence penalty
    """

    # --------------------------------------------------------
    # Browser event penalty
    # --------------------------------------------------------

    event_penalty = calculate_event_penalty(
        browser_events
    )


    # --------------------------------------------------------
    # Face presence penalty
    # --------------------------------------------------------

    face_penalty = 0


    if face_presence_ratio < 80:

        face_penalty = 10


    if face_presence_ratio < 60:

        face_penalty = 20


    if face_presence_ratio < 40:

        face_penalty = 30


    # --------------------------------------------------------
    # Total penalty
    # --------------------------------------------------------

    total_penalty = (
        event_penalty +
        face_penalty
    )


    # --------------------------------------------------------
    # Final score
    # --------------------------------------------------------

    score = 100 - total_penalty


    # Score cannot be negative
    score = max(
        score,
        0
    )


    return score


# ============================================================
# 6. GET RISK LEVEL
# ============================================================

def get_risk_level(score):
    """
    Convert numerical integrity score
    into a project-defined review category.

        80 - 100 -> Low
        60 - 79  -> Medium
        0 - 59   -> High
    """

    if score >= 80:

        return "Low"


    elif score >= 60:

        return "Medium"


    else:

        return "High"


# ============================================================
# 7. COMPUTE COMPLETE INTEGRITY SCORE
# ============================================================

def compute_integrity_score(
    candidate_id,
    session_id
):
    """
    Main entry point for integrity scoring.

    Steps:

        1. Get browser events
        2. Calculate face presence ratio
        3. Calculate event penalty
        4. Calculate integrity score
        5. Determine risk level
        6. Save result
        7. Return result
    """

    # --------------------------------------------------------
    # Step 1: Get browser events
    # --------------------------------------------------------

    browser_events = get_browser_events(
        candidate_id,
        session_id
    )


    # --------------------------------------------------------
    # Step 2: Calculate face presence
    # --------------------------------------------------------

    face_presence_ratio = calculate_face_presence_ratio(
        candidate_id,
        session_id
    )


    # --------------------------------------------------------
    # Step 3: Calculate event penalty
    # --------------------------------------------------------

    event_penalty = calculate_event_penalty(
        browser_events
    )


    # --------------------------------------------------------
    # Step 4: Calculate integrity score
    # --------------------------------------------------------

    score = calculate_integrity_score(
        browser_events,
        face_presence_ratio
    )


    # --------------------------------------------------------
    # Step 5: Determine risk level
    # --------------------------------------------------------

    risk_level = get_risk_level(
        score
    )


    # --------------------------------------------------------
    # Step 6: Prepare result
    # --------------------------------------------------------

    result = {

        "candidate_id": candidate_id,

        "session_id": session_id,

        "event_penalty": event_penalty,

        "face_presence_ratio": face_presence_ratio,

        "integrity_score": score,

        "risk_level": risk_level
    }


    # --------------------------------------------------------
    # Step 7: Save result
    # --------------------------------------------------------

    save_integrity_score(
        result
    )


    return result


# ============================================================
# 8. SAVE INTEGRITY SCORE
# ============================================================

def save_integrity_score(result):
    """
    Save integrity score to integrity_scores table.

    If the session already has a score,
    update the existing record.
    """

    connection = get_db()

    try:

        connection.execute("""
            INSERT INTO integrity_scores
            (
                session_id,
                candidate_id,
                event_penalty,
                face_presence_ratio,
                integrity_score,
                risk_level,
                computed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))

            ON CONFLICT(session_id)
            DO UPDATE SET

                event_penalty =
                    excluded.event_penalty,

                face_presence_ratio =
                    excluded.face_presence_ratio,

                integrity_score =
                    excluded.integrity_score,

                risk_level =
                    excluded.risk_level,

                computed_at =
                    excluded.computed_at

        """, (
            result["session_id"],
            result["candidate_id"],
            result["event_penalty"],
            result["face_presence_ratio"],
            result["integrity_score"],
            result["risk_level"]
        ))


        connection.commit()

    finally:

        connection.close()


# ============================================================
# 9. COMMAND-LINE TESTING
# ============================================================

if __name__ == "__main__":

    if len(sys.argv) < 3:

        print(
            "Usage: python integrity_score.py "
            "<candidate_id> <session_id>"
        )

        sys.exit(1)


    candidate_id = int(
        sys.argv[1]
    )

    session_id = sys.argv[2]


    result = compute_integrity_score(
        candidate_id,
        session_id
    )


    print("\n========== INTEGRITY RESULT ==========")

    for key, value in result.items():

        print(
            f"{key:22}: {value}"
        )

    print("======================================")