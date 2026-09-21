from datetime import datetime

from database import get_db


# ----------------------------------------
# LOG FACE STATE
# ----------------------------------------
def log_face_state(
    candidate_id,
    session_id,
    current_state
):

    connection = get_db()

    now = datetime.now().isoformat()


    # ----------------------------------------
    # GET PREVIOUS OPEN EVENT
    # ----------------------------------------
    previous = connection.execute("""
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


    # ----------------------------------------
    # FIRST FACE EVENT
    # ----------------------------------------
    if not previous:

        connection.execute("""
            INSERT INTO face_events
            (
                candidate_id,
                session_id,
                event_type,
                started_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            candidate_id,
            session_id,
            current_state,
            now
        ))


    else:

        # ----------------------------------------
        # SAME STATE
        # ----------------------------------------
        # If the face state has not changed,
        # there is no need to create another event.

        if previous["event_type"] == current_state:

            connection.close()

            return


        # ----------------------------------------
        # STATE CHANGED
        # ----------------------------------------
        started_at = datetime.fromisoformat(
            previous["started_at"]
        )

        ended_at = datetime.fromisoformat(now)

        duration = (
            ended_at - started_at
        ).total_seconds()


        # ----------------------------------------
        # CLOSE PREVIOUS EVENT
        # ----------------------------------------
        connection.execute("""
            UPDATE face_events

            SET
                ended_at = ?,
                duration_seconds = ?

            WHERE id = ?
        """, (
            now,
            duration,
            previous["id"]
        ))


        # ----------------------------------------
        # START NEW EVENT
        # ----------------------------------------
        connection.execute("""
            INSERT INTO face_events
            (
                candidate_id,
                session_id,
                event_type,
                started_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            candidate_id,
            session_id,
            current_state,
            now
        ))


    # ----------------------------------------
    # SAVE CHANGES
    # ----------------------------------------
    connection.commit()

    connection.close()