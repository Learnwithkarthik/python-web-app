from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "super-secret-key"

# Temporary in-memory DB (will move to GCS later)
users_db = {}

# 🔹 Welcome / Landing Page (DEFAULT)
@app.route("/")
def welcome():
    return render_template("welcome.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        if username in users_db:
            return "User already exists!"

        users_db[username] = {
            "email": email,
            "password": generate_password_hash(password)
        }

        return redirect(url_for("login"))

    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = users_db.get(username)

        if not user or not check_password_hash(user["password"], password):
            return "Invalid username or password"

        session["user"] = username
        return redirect(url_for("dashboard"))

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    return render_template("dashboard.html", user=session["user"])

@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("welcome"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

