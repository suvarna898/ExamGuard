import os
import sqlite3
import uuid


from flask import Flask, request, render_template, session, redirect, url_for
from database import init_db, get_db
from werkzeug.security import generate_password_hash, check_password_hash
from camera import capture_photo
from monitoring.alert_manager import create_alert, create_risk_alert
from monitoring.face_logger import log_face_state
from monitoring.face_monitoring import detect_face
from monitoring import event_detector
from monitoring.ai_repor_manager import save_ai_report, get_ai_report

import base64
from monitoring.evidence_manager import save_evidence




from datetime import datetime
from monitoring.incident_logger import create_incident
from monitoring.integrity_score import compute_integrity_score


# from flask import Flask, request, render_template, session, redirect, url_for
# from database import init_db, get_db
# from werkzeug.security import generate_password_hash, check_password_hash
# from camera import capture_photo
# from monitoring.face_logger import log_face_state
# from monitoring.face_monitoring import detect_face

from ai.integrity_agent import generate_real_integrity_report
from monitoring.face_monitoring import close_open_face_event



# ----------------------------------------
# FLASK APPLICATION
# ----------------------------------------
app = Flask(__name__)

app.secret_key = "exam_guard_key"

upload_folder = "static/uploads"


# ----------------------------------------
# INITIALIZE DATABASE
# ----------------------------------------
init_db()


# ----------------------------------------
# HOME
# ----------------------------------------
@app.route("/")
def home():

    return "Welcome to Exam Guard"


# ----------------------------------------
# CAPTURE CANDIDATE PHOTO
# ----------------------------------------
@app.route("/capture-photo", methods=["POST"])
def captureCandidatePhoto():

    photo = request.files.get("photo")

    if not photo:

        return {
            "success": False,
            "message": "No photo uploaded"
        }, 400


    # Read uploaded image
    image_data = photo.read()


    # Process and save image
    photo_path = capture_photo(image_data)


    if not photo_path:

        return {
            "success": False,
            "message": "Could not process photo"
        }, 400


    # Temporarily store photo path
    # until registration is completed
    session["capture_photo"] = photo_path


    return {
        "success": True,
        "message": "Photo captured successfully",
        "photo_path": photo_path
    }, 200


# ----------------------------------------
# REGISTER
# ----------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        # ----------------------------------------
        # GET FORM DATA
        # ----------------------------------------

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        # ----------------------------------------
        # VALIDATE REQUIRED FIELDS
        # ----------------------------------------

        if not name or not email or not password:

            return render_template(
                "register.html",
                error="Please fill in all required fields"
            )

        # ----------------------------------------
        # GET CAPTURED PHOTO
        # ----------------------------------------

        photo_path = session.get("capture_photo")

        if not photo_path:

            return render_template(
                "register.html",
                error="Please capture a photo before registering."
            )

        # ----------------------------------------
        # HASH PASSWORD
        # ----------------------------------------

        hashed_password = generate_password_hash(password)

        # ----------------------------------------
        # DATABASE CONNECTION
        # ----------------------------------------

        connection = get_db()

        try:

            print("Candidate email:", email)

            # ----------------------------------------
            # INSERT CANDIDATE
            # ----------------------------------------

            connection.execute(
                """
                INSERT INTO candidates
                (
                    name,
                    email,
                    password,
                    photo
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    name,
                    email,
                    hashed_password,
                    photo_path
                )
            )

            connection.commit()

        except sqlite3.IntegrityError:

            connection.rollback()

            if photo_path and os.path.exists(photo_path):
                os.remove(photo_path)

            return render_template(
                "register.html",
                error="Email already registered. Please use a different email."
            )

        except Exception as e:

            connection.rollback()

            if photo_path and os.path.exists(photo_path):
                os.remove(photo_path)

            print("Registration error:", e)

            return render_template(
                "register.html",
                error="Registration failed. Please try again."
            )

        finally:

            connection.close()

        # ----------------------------------------
        # REGISTRATION SUCCESS
        # ----------------------------------------

        session.pop("capture_photo", None)

        return redirect(url_for("login"))

    # ----------------------------------------
    # GET REQUEST
    # ----------------------------------------

    return render_template("register.html")


# ----------------------------------------
# LOGIN
# ----------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        action = request.form.get("action")

        # ----------------------------------------
        # FORGOT PASSWORD
        # ----------------------------------------
        if action == "forgot_password":

            email = request.form["email"]
            new_password = request.form["new_password"]

            connection = get_db()

            try:

                # FIND CANDIDATE
                candidate = connection.execute(
                    """
                    SELECT *
                    FROM candidates
                    WHERE email = ?
                    """,
                    (email,)
                ).fetchone()

                if not candidate:
                    return "Email not found"

                # ----------------------------------------
                # UPDATE PASSWORD
                # ----------------------------------------
                hashed_password = generate_password_hash(
                    new_password
                )

                connection.execute(
                    """
                    UPDATE candidates
                    SET password = ?
                    WHERE email = ?
                    """,
                    (hashed_password, email)
                )

                connection.commit()

            finally:

                connection.close()

            return "Password changed successfully. Please login again."


        # ----------------------------------------
        # NORMAL LOGIN
        # ----------------------------------------
        email = request.form["email"]
        password = request.form["password"]

        connection = get_db()

        try:

            # ----------------------------------------
            # FIND CANDIDATE
            # ----------------------------------------
            candidate = connection.execute(
                """
                SELECT *
                FROM candidates
                WHERE email = ?
                """,
                (email,)
            ).fetchone()

        finally:

            connection.close()


        # ----------------------------------------
        # VERIFY PASSWORD
        # ----------------------------------------
        if candidate and check_password_hash(candidate["password"], password):
             session["candidate_id"] = candidate["id"]


             session["candidate_name"] = candidate["name"]

             return redirect("/dashboard")


        return "Invalid email or password"


    return render_template(
        "login.html"
    )

# ----------------------------------------
# DASHBOARD
# ----------------------------------------
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


# ----------------------------------------
# START EXAM
# ----------------------------------------
@app.route("/start-exam")
def start_exam():

    if "candidate_id" not in session:
        return redirect(url_for("login"))

    exam_session_id = str(uuid.uuid4())
    session["exam_session_id"] = exam_session_id

    connection = get_db()

    try:
        connection.execute("""
            INSERT INTO exam_sessions
                (candidate_id, session_id, status, started_at)
            VALUES (?, ?, 'in_progress', ?)
        """, (
            session["candidate_id"],
            exam_session_id,
            datetime.now().isoformat(),
        ))
        connection.commit()

    finally:
        connection.close()

    return render_template("exam.html", candidate_name=session.get("candidate_name"))

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
    # 3. Close the final open face event
    # --------------------------------------------------

    close_open_face_event(
        candidate_id,
        exam_session_id
    )

    # --------------------------------------------------
    # 4. Calculate final integrity score
    # --------------------------------------------------

    result = compute_integrity_score(
        candidate_id,
        exam_session_id
    )


    create_risk_alert(
        candidate_id=candidate_id,
        session_id=exam_session_id,
        risk_level=result["risk_level"],
        integrity_score=result["integrity_score"]
    )


    # --------------------------------------------------
    # 5. Generate integrity report using AI agent
    # --------------------------------------------------
    report = generate_real_integrity_report(
        candidate_id,
        exam_session_id
    )

    save_report_result = save_ai_report(
        candidate_id=candidate_id,
        session_id=exam_session_id,
        report=report
    )

    print("Report saved in database with ID:", save_report_result.get("id"))


    
    # print("AI-Generated Integrity Report:")
    # print(report)



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
# ----------------------------------------
# Face MONITORING
# ----------------------------------------
@app.route("/monitor-face", methods=["POST"])
def monitor_face():

    # ----------------------------------------
    # CHECK LOGIN
    # ----------------------------------------
    if "candidate_id" not in session:

        return {
            "success": False,
            "message": "Candidate is not logged in"
        }, 401


    candidate_id = session["candidate_id"]


    # ----------------------------------------
    # GET EXAM SESSION
    # ----------------------------------------
    exam_session_id = session.get(
        "exam_session_id"
    )


    if not exam_session_id:

        return {
            "success": False,
            "message": "Exam not started"
        }, 400


    # ----------------------------------------
    # GET IMAGE FROM BROWSER
    # ----------------------------------------
    image = request.files.get(
        "image"
    )


    if not image:

        return {
            "success": False,
            "message": "No image received"
        }, 400


    # ----------------------------------------
    # READ IMAGE
    # ----------------------------------------
    image_data = image.read()
    # ----------------------------------------
    # DETECT FACE
    # ----------------------------------------
    face_present, processed_image = detect_face(
        image_data
    )
    # ----------------------------------------
    # DETERMINE FACE STATE
    # ----------------------------------------
    if face_present:

        current_state = "face_detected"

    else:

        current_state = "face_absent"

    # ----------------------------------------
    # LOG FACE STATE
    # ----------------------------------------
    log_face_state(
        candidate_id,
        exam_session_id,
        current_state
    )


    # ----------------------------------------
    # RETURN RESULT
    # ----------------------------------------
    return {
        "success": True,
        "state": current_state
    }, 200


@app.route("/log-browser-event", methods=["POST"])
def log_browser_event():
    if "candidate_id" not in session:
    
            return {
                "success": False,
                "message": "Candidate is not logged in"
            }, 401
    
    
    candidate_id = session["candidate_id"]

    exam_session_id = session.get("exam_session_id")
    if not exam_session_id:
        return {
            "success": False,
            "message": "Exam not started"
        }, 400
    data=request.get_json()
    if not data or "event" not in data:
        return {
            "success": False,
            "message": "No event data received"
        }, 400
    event_type=data["event"]
    details=data.get("details", "")

    if not event_type:
        return {
            "success": False,
            "message": "Event type is required"
        }, 400
    connection=get_db()
    try:

        # Insert browser event
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
            exam_session_id,
            event_type,
            datetime.now().isoformat(),
            details
        ))


        # Save changes
        connection.commit()


        print("================================")
        print("BROWSER EVENT RECEIVED")
        print("candidate_id:", candidate_id)
        print("session_id:", exam_session_id)
        print("event_type:", event_type)
        print("details:", details)
        print("================================")

        screenshot_required = False

        # Run the rule-based suspicious event detection engine
        rule_results=event_detector.evaluate_browser_event(
            connection, candidate_id, exam_session_id, event_type
        )
        
        print("rule_results:", rule_results)
        
        if rule_results:
            create_incident(candidate_id = candidate_id,
                            session_id= exam_session_id,
                            event_type=rule_results["event_type"],
                            description=rule_results["reason"],
                            severity=rule_results["severity"]
                            )
            create_alert(candidate_id = candidate_id,
                         session_id= exam_session_id,
                         alert_type=rule_results["event_type"],
                         message=rule_results["reason"],
                         severity=rule_results["severity"]
            )

            screenshot_required = True

    except Exception as e:

        connection.rollback()

        return {
            "success": False,
            "message": str(e)
        }, 500


    finally:

        connection.close()


    return {"success": True, "message": "Browser event saved", "screenshot_required": screenshot_required}


@app.route("/upload-evidence", methods=["POST"])
def upload_evidence():

    # --------------------------------------------------
    # Check active candidate/session
    # --------------------------------------------------

    if (
        "candidate_id" not in session
        or "exam_session_id" not in session
    ):

        return {
            "success": False,
            "message": "No active exam session"
        }, 400

    # --------------------------------------------------
    # Read JSON
    # --------------------------------------------------

    data = request.get_json(
        silent=True
    )

    if not data:

        return {
            "success": False,
            "message": "No evidence data received"
        }, 400

    image_data = data.get(
        "image"
    )

    if not image_data:

        return {
            "success": False,
            "message": "Screenshot is required"
        }, 400

    try:

        if "," in image_data:

            image_data = image_data.split(
                ",",
                1
            )[1]

        # --------------------------------------------------
        # Base64 → binary bytes
        # --------------------------------------------------

        file_data = base64.b64decode(
            image_data
        )

        if not file_data:

            return {
                "success": False,
                "message": "Screenshot data is empty"
            }, 400

        # --------------------------------------------------
        # Save evidence
        #
        # save_evidence() calculates SHA-256 internally
        # --------------------------------------------------

        result = save_evidence(
            candidate_id=session["candidate_id"],
            session_id=session["exam_session_id"],
            evidence_type="screenshot",
            filename="suspicious_event.jpg",
            mime_type="image/jpeg",
            file_data=file_data
        )

        return {
            "success": True,
            "message": "Screenshot evidence saved",
            "sha256_hash": result["sha256_hash"]
        }

    except Exception as e:

        return {
            "success": False,
            "message": str(e)
        }, 500

@app.route("/verify-evidence/<int:evidence_id>", methods=["GET"])
def verify_evidence(evidence_id):
    
    if "candidate_id" not in session:
        return {"success": False, "message": "Candidate not logged in"}, 401

    results = verify_evidence(evidence_id)
    if results["message"]=="Evidence is invalid":
        return {"success": False, "message": "Evidence is invalid"}, 400
    return {"success": True, "message": "Evidence is valid", "evidence_id": results["evidence_id"], "stored_hash": results["stored_hash"], "calculated_hash": results["calculated_hash"]}, 200

@app.route("/ai-report/<int:candidate_id>/<session_id>", methods=["GET"])
def ai_report(candidate_id, session_id):

    result = get_ai_report(
        candidate_id,
        session_id
    )

    if result is None:
        return {
            "success": False,
            "message": "AI report not found"
        }, 404

    return {
        "success": True,
        "report": result
    }



    
# ----------------------------------------
# LOGOUT
# ----------------------------------------
@app.route("/logout")
def logout():

    # Clear login and exam session
    session.clear()


    return redirect(
        url_for("login")
    )


# ----------------------------------------
# RUN APPLICATION
# ----------------------------------------
if __name__ == "__main__":

    app.run(
        debug=True
    )