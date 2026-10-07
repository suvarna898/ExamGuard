import sqlite3
from datetime import datetime, timedelta
import uuid
import os

from werkzeug.security import generate_password_hash

from database import get_db


# ============================================================
# SAMPLE CANDIDATES
# ============================================================

def insert_candidates(connection):

    candidates = [
        ("Arun Kumar", "arun@example.com"),
        ("Priya Sharma", "priya@example.com"),
        ("Rahul Kumar", "rahul@example.com"),
        ("Sneha Reddy", "sneha@example.com"),
        ("Karthik Raj", "karthik@example.com"),
        ("Divya Sri", "divya@example.com"),
        ("Vignesh Kumar", "vignesh@example.com"),
        ("Anjali Rao", "anjali@example.com"),
        ("Suresh Babu", "suresh@example.com"),
        ("Meena Devi", "meena@example.com"),
    ]

    for name, email in candidates:

        # Do not insert duplicate candidates
        existing = connection.execute("""
            SELECT id
            FROM candidates
            WHERE email = ?
        """, (email,)).fetchone()

        if existing:
            continue

        connection.execute("""
            INSERT INTO candidates
            (
                name,
                email,
                password,
                photo
            )
            VALUES (?, ?, ?, ?)
        """, (
            name,
            email,
            generate_password_hash("password123"),
            None
        ))


# ============================================================
# INSERT EXAM SESSIONS
# ============================================================

def insert_exam_sessions(connection):

    candidates = connection.execute("""
        SELECT id
        FROM candidates
        ORDER BY id
        LIMIT 10
    """).fetchall()

    sessions = []

    base_time = datetime.now() - timedelta(days=10)

    for index, candidate in enumerate(candidates):

        candidate_id = candidate["id"]

        session_id = str(uuid.uuid4())

        started_at = (
            base_time +
            timedelta(days=index)
        )

        submitted_at = (
            started_at +
            timedelta(minutes=30)
        )

        connection.execute("""
            INSERT OR IGNORE INTO exam_sessions
            (
                candidate_id,
                session_id,
                status,
                started_at,
                submitted_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            candidate_id,
            session_id,
            "submitted",
            started_at.isoformat(),
            submitted_at.isoformat()
        ))

        sessions.append({
            "candidate_id": candidate_id,
            "session_id": session_id,
            "started_at": started_at,
            "submitted_at": submitted_at
        })

    return sessions


# ============================================================
# INSERT FACE EVENTS
# ============================================================

def insert_face_events(connection, sessions):

    # Different absence patterns for each candidate.
    #
    # 0  = no absence
    # 30 = 30 seconds absent
    # 60 = 1 minute absent
    # etc.

    absence_durations = [
        0,
        30,
        60,
        90,
        120,
        180,
        240,
        300,
        420,
        600
    ]

    for index, session in enumerate(sessions):

        candidate_id = session["candidate_id"]
        session_id = session["session_id"]
        started_at = session["started_at"]

        absence_duration = absence_durations[index]

        # Candidate with zero absence
        # does not need a face_absent record.
        if absence_duration == 0:
            continue

        absence_start = (
            started_at +
            timedelta(minutes=10)
        )

        absence_end = (
            absence_start +
            timedelta(
                seconds=absence_duration
            )
        )

        connection.execute("""
            INSERT INTO face_events
            (
                candidate_id,
                session_id,
                event_type,
                started_at,
                ended_at,
                duration_seconds
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            candidate_id,
            session_id,
            "face_absent",
            absence_start.isoformat(),
            absence_end.isoformat(),
            absence_duration
        ))


# ============================================================
# INSERT BROWSER EVENTS
# ============================================================

def insert_browser_events(connection, sessions):

    # Number of events for each session.
    #
    # This creates different behavioral patterns
    # for Data Science / K-Means.

    event_counts = [
        {
            "tab_switch": 1,
            "focus_lost": 1,
            "copy_attempt": 0,
            "paste_attempt": 0,
            "right_click": 1
        },

        {
            "tab_switch": 2,
            "focus_lost": 1,
            "copy_attempt": 0,
            "paste_attempt": 0,
            "right_click": 1
        },

        {
            "tab_switch": 3,
            "focus_lost": 2,
            "copy_attempt": 0,
            "paste_attempt": 0,
            "right_click": 1
        },

        {
            "tab_switch": 4,
            "focus_lost": 3,
            "copy_attempt": 1,
            "paste_attempt": 0,
            "right_click": 2
        },

        {
            "tab_switch": 5,
            "focus_lost": 3,
            "copy_attempt": 1,
            "paste_attempt": 1,
            "right_click": 2
        },

        {
            "tab_switch": 7,
            "focus_lost": 4,
            "copy_attempt": 1,
            "paste_attempt": 1,
            "right_click": 3
        },

        {
            "tab_switch": 8,
            "focus_lost": 5,
            "copy_attempt": 2,
            "paste_attempt": 1,
            "right_click": 3
        },

        {
            "tab_switch": 10,
            "focus_lost": 6,
            "copy_attempt": 2,
            "paste_attempt": 2,
            "right_click": 4
        },

        {
            "tab_switch": 12,
            "focus_lost": 7,
            "copy_attempt": 3,
            "paste_attempt": 2,
            "right_click": 5
        },

        {
            "tab_switch": 15,
            "focus_lost": 9,
            "copy_attempt": 3,
            "paste_attempt": 3,
            "right_click": 6
        }
    ]

    for index, session in enumerate(sessions):

        candidate_id = session["candidate_id"]
        session_id = session["session_id"]
        started_at = session["started_at"]

        counts = event_counts[index]

        event_number = 0

        for event_type, count in counts.items():

            for _ in range(count):

                event_time = (
                    started_at +
                    timedelta(
                        minutes=(
                            5 + event_number
                        )
                    )
                )

                connection.execute("""
                    INSERT INTO browser_events
                    (
                        candidate_id,
                        session_id,
                        event_type,
                        event_time,
                        details
                    )
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    candidate_id,
                    session_id,
                    event_type,
                    event_time.isoformat(),
                    "Sample analytics data"
                ))

                event_number += 1


# ============================================================
# INSERT SUSPICIOUS EVENTS
# ============================================================

def insert_suspicious_events(
    connection,
    sessions
):

    # Number of suspicious events for each session.
    suspicious_counts = [
        0,
        0,
        1,
        1,
        2,
        2,
        3,
        3,
        4,
        5
    ]

    for index, session in enumerate(sessions):

        candidate_id = session["candidate_id"]
        session_id = session["session_id"]
        started_at = session["started_at"]

        count = suspicious_counts[index]

        for event_number in range(count):

            event_time = (
                started_at +
                timedelta(
                    minutes=(
                        15 + event_number
                    )
                )
            )

            connection.execute("""
                INSERT INTO suspicious_events
                (
                    candidate_id,
                    session_id,
                    event_type,
                    reason,
                    event_time,
                    severity
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                candidate_id,
                session_id,
                "excessive_tab_switching",
                "Multiple browser focus changes detected",
                event_time.isoformat(),
                "medium"
            ))


# ============================================================
# INSERT INTEGRITY SCORES
# ============================================================

def insert_integrity_scores(
    connection,
    sessions
):

    event_counts = [
        1,
        2,
        3,
        4,
        5,
        7,
        8,
        10,
        12,
        15
    ]

    absence_durations = [
        0,
        30,
        60,
        90,
        120,
        180,
        240,
        300,
        420,
        600
    ]

    for index, session in enumerate(sessions):

        candidate_id = session["candidate_id"]
        session_id = session["session_id"]

        tab_switch = event_counts[index]

        # ----------------------------------------------------
        # Calculate event penalty
        # ----------------------------------------------------

        # Every session also gets some focus loss,
        # right-click, copy, etc.
        #
        # These values mirror the browser event
        # patterns inserted above.

        focus_lost = min(
            index + 1,
            9
        )

        copy_attempt = max(
            0,
            index - 2
        )

        paste_attempt = max(
            0,
            index - 4
        )

        right_click = min(
            index + 1,
            6
        )

        event_penalty = (
            tab_switch * 10
            + focus_lost * 5
            + copy_attempt * 15
            + paste_attempt * 15
            + right_click * 5
        )

        # ----------------------------------------------------
        # Face presence
        # ----------------------------------------------------

        exam_duration = 30 * 60

        absent_duration = (
            absence_durations[index]
        )

        present_duration = max(
            exam_duration -
            absent_duration,
            0
        )

        face_presence_ratio = (
            present_duration /
            exam_duration
        ) * 100

        face_presence_ratio = round(
            face_presence_ratio,
            2
        )

        # ----------------------------------------------------
        # Face penalty
        # ----------------------------------------------------

        face_penalty = 0

        if face_presence_ratio < 80:
            face_penalty = 10

        if face_presence_ratio < 60:
            face_penalty = 20

        if face_presence_ratio < 40:
            face_penalty = 30

        # ----------------------------------------------------
        # Integrity score
        # ----------------------------------------------------

        integrity_score = (
            100
            - event_penalty
            - face_penalty
        )

        integrity_score = max(
            integrity_score,
            0
        )

        # ----------------------------------------------------
        # Risk level
        # ----------------------------------------------------

        if integrity_score >= 80:

            risk_level = "Low"

        elif integrity_score >= 60:

            risk_level = "Medium"

        else:

            risk_level = "High"

        # ----------------------------------------------------
        # Save score
        # ----------------------------------------------------

        connection.execute("""
            INSERT OR REPLACE INTO integrity_scores
            (
                session_id,
                candidate_id,
                event_penalty,
                face_presence_ratio,
                integrity_score,
                risk_level,
                computed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id,
            candidate_id,
            event_penalty,
            face_presence_ratio,
            integrity_score,
            risk_level,
            datetime.now().isoformat()
        ))


# ============================================================
# MAIN
# ============================================================

def seed_database():

    connection = get_db()

    try:

        print(
            "\n======================================"
        )

        print(
            "      EXAMGUARD SAMPLE DATA"
        )

        print(
            "======================================"
        )


        # ----------------------------------------------------
        # 1. Candidates
        # ----------------------------------------------------

        insert_candidates(
            connection
        )

        connection.commit()

        print(
            "\n10 candidate records prepared."
        )


        # ----------------------------------------------------
        # 2. Exam sessions
        # ----------------------------------------------------

        sessions = insert_exam_sessions(
            connection
        )

        connection.commit()

        print(
            "10 exam session records inserted."
        )


        # ----------------------------------------------------
        # 3. Face events
        # ----------------------------------------------------

        insert_face_events(
            connection,
            sessions
        )

        connection.commit()

        print(
            "Face event data inserted."
        )


        # ----------------------------------------------------
        # 4. Browser events
        # ----------------------------------------------------

        insert_browser_events(
            connection,
            sessions
        )

        connection.commit()

        print(
            "Browser event data inserted."
        )


        # ----------------------------------------------------
        # 5. Suspicious events
        # ----------------------------------------------------

        insert_suspicious_events(
            connection,
            sessions
        )

        connection.commit()

        print(
            "Suspicious event data inserted."
        )


        # ----------------------------------------------------
        # 6. Integrity scores
        # ----------------------------------------------------

        insert_integrity_scores(
            connection,
            sessions
        )

        connection.commit()

        print(
            "Integrity score data inserted."
        )


        print(
            "\n======================================"
        )

        print(
            "Sample data insertion completed."
        )

        print(
            "======================================"
        )


    except Exception as e:

        connection.rollback()

        print(
            "\nERROR:"
        )

        print(e)

    finally:

        connection.close()


# ============================================================
# RUN SCRIPT
# ============================================================

if __name__ == "__main__":

    seed_database()