from flask import Flask, request, render_template
from database import init_db , get_db

app = Flask(__name__)
init_db

@app.route("/")
def home():
    return "Welcome to Exam Guard"


# @app.route("/register", methods=["GET", "POST"])
# def register():

#     if request.method == "POST":
#         name = request.form["name"]
#         email = request.form["email"]
#         password = request.form["password"]

#         print("name:", name)
#         print("email:", email)
#         print("password:", password)

#     return render_template("register.html")


@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        connection = get_db()
        connection.execute(
            """
            INSERT INTO candidates
            (name, email, password)
            VALUES (?, ?, ?)
            """,
            (name, email, password)
        )
        
        connection.commit()
        connection.close()
        
        return "registration successful"

        print("name:", name)
        print("email:", email)
        print("password:", password)

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
            WHERE email = ? AND password = ?
            """,
            (email, password)
        ).fetchone()

        connection.close()

        if candidate:
            return "Login successful!"

        return "Invalid email or password"

    return render_template("login.html")
            
if __name__ == "__main__":
    init_db()
    app.run(debug=True)