from flask import Flask, request, render_template, session, redirect
from database import init_db, get_db
from werkzeug.security import check_password_hash, generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "examguard_secret_key"

@app.route("/")
def home():
    return "Welcome to Exam Guard"

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        hashed_password=generate_password_hash(password)
        print(f"Name: {name}, Email: {email}, Password: {hashed_password}")

        # Using 'with' automatically commits changes
        with get_db() as connection:
            connection.execute(
                """
                INSERT INTO candidates (name, email, password)
                VALUES (?, ?, ?)
                """,
                (name, email, hashed_password)
            )

        return redirect("/login")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        connection = get_db()

        candidate = connection.execute(
            """
            SELECT *
            FROM candidates
            WHERE email = ?  
            """,
            (email,)
        ).fetchone()

        connection.close()

        if candidate and check_password_hash(candidate["password"], password):
            session["candidate_id"] = candidate["id"]
            return redirect("/dashboard")
        
        return "Invalid email or password"

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "candidate_id" not in session:
        return "please login first"
    return render_template("dashboard.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")         

if __name__ == "__main__":
    init_db()
    app.run(debug=True)