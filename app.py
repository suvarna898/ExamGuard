# from flask import Flask, request, render_template, session, redirect
# from database import init_db, get_db
# from werkzeug.security import generate_password_hash, check_password_hash
# from werkzeug.utils import secure_filename
# from camera import capture_image
# import os


# app = Flask(__name__)
# app.secret_key = "exam_guard_key" 
# upload_folder = "static/uploads"




# @app.route("/capture", methods=["POST"])
# def captureCandidateImage():
#     photo=request.files.get("photo")
#     if not photo:
#         return{
#             "success": False,
#             "message": "No photo uploaded"
#         },400
#     image_data = photo.read()
#     photo_path = capture_image(image_data)
#     if not photo_path:
#         return{
#             "success": False,
#             "message": "Failed to capture image"
#         },400
#     session["photo_path"] = 
#     return{
        
#         "success": True,
#         "message": "Image captured successfully",
#         "photo_path": photo_path
#     },200
#  # Required for session management


# # Initialize database
# init_db()


# @app.route("/")
# def home():
#     return "Welcome to Exam Guard"


# @app.route("/register", methods=["GET", "POST"])
# def register():

#     if request.method == "POST":

#         name = request.form["name"]
#         email = request.form["email"]
#         password = request.form["password"]
#         hashed_password = generate_password_hash(password)
#         print(f"Name: {name}, Email: {email}, Password: {hashed_password}")
#         photo = request.files.get("photo")

#         if not photo or photo.filename == "":
#             return "No photo uploaded"

#         os.makedirs(upload_folder, exist_ok=True)
#         filename=secure_filename(photo.filename)
#         photo_path = os.path.join(upload_folder, filename)
#         photo.save(photo_path)

#         connection = get_db()

#         connection.execute(
#             """
#             INSERT INTO candidates
#             (name, email, password, photo)
#             VALUES (?, ?, ?, ?)
#             """,
#             (name, email, hashed_password, photo_path)
#         )

#         connection.commit()
#         connection.close()

#         #return "Registration successful"
#         return redirect("/login")
        
#     return render_template("register.html")


# # 
# @app.route("/login", methods=["GET", "POST"])
# def login():

#     if request.method == "POST":

#         email = request.form["email"]
#         password = request.form["password"]

#         connection = get_db()

#         try:
#             candidate = connection.execute("""
#                 SELECT *
#                 FROM candidates
#                 WHERE email = ? 
#             """, (email,)
#             ).fetchone()

#             if candidate and check_password_hash(candidate["password"], password):
         
#                 session["candidate_id"] = candidate["id"]
#                 return redirect("/dashboard")

#             return "Invalid email or password"

#         finally:
#             connection.close()

#     return render_template("login.html")

# @app.route("/dashboard")
# def dashboard():
#     if 'candidate_id' not in session:
#         return "Please log in first"
    
#     return render_template("dashboard.html")


# @app.route("/logout")
# def logout():
#     session.pop('candidate_id', None)
#     return "Logged out successfully"



# if __name__ == "__main__":
#     app.run(debug=True)
from flask import Flask, request, render_template, session, redirect
from database import init_db, get_db
from werkzeug.security import generate_password_hash, check_password_hash
from camera import capture_photo
from monitoring.face_logger import log_face_state
from monitoring.face_monitoring import detect_face
from monitoring import eventdetector

import os
import sqlite3
import uuid


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

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]


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
                error="Please capture your photo before registering"
            )


        # ----------------------------------------
        # HASH PASSWORD
        # ----------------------------------------
        hashed_password = generate_password_hash(
            password
        )


        connection = get_db()


        try:

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

            # ----------------------------------------
            # DELETE PHOTO IF REGISTRATION FAILS
            # ----------------------------------------
            if os.path.exists(photo_path):

                os.remove(photo_path)


            session.pop(
                "capture_photo",
                None
            )


            return render_template(
                "register.html",
                error="Email already registered. Please use a different email."
            )


        finally:

            connection.close()


        # ----------------------------------------
        # REMOVE TEMPORARY PHOTO SESSION
        # ----------------------------------------
        session.pop(
            "capture_photo",
            None
        )


        return redirect("/login")


    return render_template(
        "register.html"
    )


# ----------------------------------------
# LOGIN
# ----------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

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
        if candidate and check_password_hash(
            candidate["password"],
            password
        ):

            session["candidate_id"] = candidate["id"]

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

        return "Please login first"


    return render_template(
        "dashboard.html"
    )


# ----------------------------------------
# START EXAM
# ----------------------------------------
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


# ----------------------------------------
# MONITOR FACE
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
        eventdetector.evaluate_browser_event(connection,candidate_id,session_id)


    except Exception as e:

        connection.rollback()

        return {
            "success": False,
            "message": str(e)
        }, 500


    finally:

        connection.close()


    return {
        "success": True,
        "message": "Browser event saved"
    }

    
# ----------------------------------------
# LOGOUT
# ----------------------------------------
@app.route("/logout")
def logout():

    # Clear login and exam session
    session.clear()


    return redirect(
        "/login"
    )


# ----------------------------------------
# RUN APPLICATION
# ----------------------------------------
if __name__ == "__main__":

    app.run(
        debug=True
    )