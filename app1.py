from flask import Flask, request, render_template, session, redirect, url_for
from database import init_db, get_db
from werkzeug.security import generate_password_hash, check_password_hash
from camera import capture_photo
from monitoring.face_logger import log_face_state
from monitoring.face_monitoring import detect_face
from monitoring import eventdetector

import os
import sqlite3
import uuid



app = Flask(__name__)
app.secret_key = "examguard-secret-key"

init_db()


# ------------------------------------------------
# HOME
# ------------------------------------------------
@app.route("/")
def home():
    if "candidate_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


# ------------------------------------------------
# REGISTER
# ------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            return render_template(
                "register.html",
                error="Please fill in every field."
            )

        # Photo must already be captured via /capture-photo (webcam AJAX flow)
        photo_path = session.get("capture_photo")

        if not photo_path:
            return render_template(
                "register.html",
                error="Please capture your photo before registering."
            )

        hashed_password = generate_password_hash(password)

        connection = get_db()

        try:
            connection.execute("""
                INSERT INTO candidates (name, email, password, photo)
                VALUES (?, ?, ?, ?)
            """, (name, email, hashed_password, photo_path))

            connection.commit()

            session.pop("captured_photo", None)

            return redirect(url_for("login", registered=1))

        except sqlite3.IntegrityError:
            connection.rollback()
            return render_template(
                "register.html",
                error="An account with this email already exists."
            )

        except Exception as e:
            connection.rollback()
            return render_template(
                "register.html",
                error=f"Registration failed: {e}"
            )

        finally:
            connection.close()

    return render_template("register.html")


# ------------------------------------------------
# CAPTURE PHOTO (webcam AJAX call from register.html)
# ------------------------------------------------
@app.route("/capture-photo", methods=["POST"])
def capture_candidate_photo():

    photo = request.files.get("photo")

    if not photo:
        return {"success": False, "message": "No photo received"}, 400

    image_data = photo.read()
    photo_path = save_captured_photo(image_data)

    if not photo_path:
        return {"success": False, "message": "Could not process photo"}, 400

    session["captured_photo"] = photo_path

    return {
        "success": True,
        "message": "Photo captured successfully",
        "photo_path": photo_path,
    }


# ------------------------------------------------
# LOGIN
# ------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        connection = get_db()

        try:
            candidate = connection.execute("""
                SELECT * FROM candidates WHERE email = ?
            """, (email,)).fetchone()

            if candidate and check_password_hash(candidate["password"], password):
                session["candidate_id"] = candidate["id"]
                session["candidate_name"] = candidate["name"]
                return redirect(url_for("dashboard"))

            return render_template("login.html", error="Invalid email or password.")

        finally:
            connection.close()

    registered = request.args.get("registered")
    return render_template("login.html", registered=registered)


# ------------------------------------------------
# DASHBOARD
# ------------------------------------------------
@app.route("/dashboard")
def dashboard():

    if "candidate_id" not in session:
        return redirect(url_for("login"))

    candidate_id = session["candidate_id"]

    connection = get_db()

    try:
        candidate = connection.execute("""
            SELECT * FROM candidates WHERE id = ?
        """, (candidate_id,)).fetchone()

        if not candidate:
            session.clear()
            return redirect(url_for("login"))

        recent_sessions = connection.execute("""
            SELECT session_id, status, started_at, submitted_at
            FROM exam_sessions
            WHERE candidate_id = ?
            ORDER BY started_at DESC
            LIMIT 5
        """, (candidate_id,)).fetchall()

        return render_template(
            "dashboard.html",
            candidate=candidate,
            recent_sessions=recent_sessions,
        )

    finally:
        connection.close()


# ------------------------------------------------
# LOGOUT
# ------------------------------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ------------------------------------------------
# START EXAM
# ------------------------------------------------
@app.route("/start-exam")
def start_exam():

    if "candidate_id" not in session:
        return {
            "success": False,
            "message": "Candidate is not logged in"
        }, 401

    exam_session_id = str(uuid.uuid4())

    session["exam_session_id"] = exam_session_id

    questions = [
        {
            "question": "What is the output of print(2 ** 3)?",
            "options": ["5", "6", "8", "9"]
        },
        {
            "question": "Which keyword is used to define a function in Python?",
            "options": ["function", "def", "fun", "define"]
        },
        {
            "question": "Which of the following is a Python list?",
            "options": ["(1,2,3)", "[1,2,3]", "{1,2,3}", "<1,2,3>"]
        },
        {
            "question": "Which function is used to find the length of a list?",
            "options": ["size()", "length()", "len()", "count()"]
        },
        {
            "question": "Which data type stores True or False?",
            "options": ["int", "str", "bool", "float"]
        },
        {
            "question": "What is the output of print(10 // 3)?",
            "options": ["3", "3.33", "1", "4"]
        },
        {
            "question": "Which symbol is used for a single-line comment in Python?",
            "options": ["//", "#", "/*", "--"]
        },
        {
            "question": "Which method adds an element to the end of a list?",
            "options": ["add()", "insert()", "append()", "push()"]
        },
        {
            "question": "Which loop is commonly used to iterate through a list?",
            "options": ["for", "switch", "repeat", "foreach"]
        },
        {
            "question": "What is the output of print(type(10))?",
            "options": ["float", "str", "int", "bool"]
        }
    ]

    return render_template(
        "exam.html",
        questions=questions
    )


# ------------------------------------------------
# PAUSE / RESUME / SUBMIT EXAM (session lifecycle)
# ------------------------------------------------
@app.route("/pause-exam", methods=["POST"])
def pause_exam():

    if "candidate_id" not in session or "exam_session_id" not in session:
        return {"success": False, "message": "No active exam session"}, 400

    connection = get_db()

    try:
        connection.execute("""
            UPDATE exam_sessions
            SET status = 'paused', paused_at = ?
            WHERE session_id = ?
        """, (datetime.now().isoformat(), session["exam_session_id"]))
        connection.commit()

    finally:
        connection.close()

    return {"success": True, "message": "Exam paused"}


@app.route("/resume-exam", methods=["POST"])
def resume_exam():

    if "candidate_id" not in session or "exam_session_id" not in session:
        return {"success": False, "message": "No active exam session"}, 400

    connection = get_db()

    try:
        connection.execute("""
            UPDATE exam_sessions
            SET status = 'in_progress', resumed_at = ?
            WHERE session_id = ?
        """, (datetime.now().isoformat(), session["exam_session_id"]))
        connection.commit()

    finally:
        connection.close()

    return {"success": True, "message": "Exam resumed"}


@app.route("/submit-exam", methods=["POST"])
def submit_exam():

    # --------------------------------------------------
    # 1. Check candidate login and active exam session
    # --------------------------------------------------

    if (
        "candidate_id" not in session
        or "exam_session_id" not in session
    ):
        return {
            "success": False,
            "message": "No active exam session"
        }, 400


    candidate_id = session["candidate_id"]

    exam_session_id = session["exam_session_id"]


    # --------------------------------------------------
    # 2. Record exam submission time
    # --------------------------------------------------

    submitted_at = datetime.now().isoformat()


    connection = get_db()

    try:

        connection.execute("""
            UPDATE exam_sessions
            SET
                status = 'submitted',
                submitted_at = ?
            WHERE session_id = ?
            AND candidate_id = ?
        """, (
            submitted_at,
            exam_session_id,
            candidate_id
        ))

        connection.commit()

    except Exception as e:

        connection.rollback()

        return {
            "success": False,
            "message": str(e)
        }, 500

    finally:

        connection.close()




    # --------------------------------------------------
    # 4. Calculate final integrity score
    # --------------------------------------------------

    result = compute_integrity_score(
        candidate_id,
        exam_session_id
    )


    # --------------------------------------------------
    # 5. Remove active exam session
    # --------------------------------------------------

    session.pop(
        "exam_session_id",
        None
    )


    # --------------------------------------------------
    # 6. Return final result
    # --------------------------------------------------

    return {
        "success": True,
        "message": "Exam submitted successfully",

        "integrity_score":
            result["integrity_score"],

        "face_presence_ratio":
            result["face_presence_ratio"],

        "event_penalty":
            result["event_penalty"],

        "risk_level":
            result["risk_level"],

        "redirect":
            url_for("dashboard")
    }


# ------------------------------------------------
# FACE MONITORING (webcam frame -> OpenCV Haar Cascade)
# ------------------------------------------------
@app.route("/monitor-face", methods=["POST"])
def monitor_face():

    if "candidate_id" not in session:
        return {"success": False, "message": "Candidate not logged in"}, 401

    candidate_id = session["candidate_id"]
    exam_session_id = session.get("exam_session_id")

    if not exam_session_id:
        return {"success": False, "message": "Exam session not started"}, 400

    image = request.files.get("frame")

    if not image:
        return {"success": False, "message": "No frame received"}, 400

    image_data = image.read()

    face_present = detect_face(image_data)
    current_state = "face_detected" if face_present else "face_absent"

    log_face_state(candidate_id, exam_session_id, current_state)

    return {"success": True, "state": current_state}


# ------------------------------------------------
# BROWSER EVENT LOGGING + RULE-BASED DETECTION
# ------------------------------------------------
@app.route("/log-browser-event", methods=["POST"])
def log_browser_event():

    if "candidate_id" not in session:
        return {"success": False, "message": "Candidate not logged in"}, 401

    candidate_id = session["candidate_id"]
    exam_session_id = session.get("exam_session_id")

    if not exam_session_id:
        return {"success": False, "message": "Exam session not started"}, 400

    data = request.get_json(silent=True)

    if not data:
        return {"success": False, "message": "No event data received"}, 400

    event_type = data.get("event_type")
    details = data.get("details", "")

    if not event_type:
        return {"success": False, "message": "Event type is required"}, 400

    connection = get_db()

    try:
        connection.execute("""
            INSERT INTO browser_events
                (candidate_id, session_id, event_type, event_time, details)
            VALUES (?, ?, ?, ?, ?)
        """, (
            candidate_id,
            exam_session_id,
            event_type,
            datetime.now().isoformat(),
            details,
        ))

        connection.commit()

        # Run the rule-based suspicious event detection engine
        event_detector.evaluate_browser_event(
            connection, candidate_id, exam_session_id, event_type
        )

    except Exception as e:
        connection.rollback()
        return {"success": False, "message": str(e)}, 500

    finally:
        connection.close()

    return {"success": True, "message": "Browser event saved"}


# ------------------------------------------------
# RUN FLASK
# ------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)