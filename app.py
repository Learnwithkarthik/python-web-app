import os
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "super-secret-key"  # required for sessions

# -------------------------
# File upload configuration
# -------------------------
UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------------
# Temporary in-memory user DB
# -------------------------
users_db = {}

# -------------------------
# Routes
# -------------------------

# 🔹 Welcome / Landing Page
@app.route("/")
def welcome():
    return render_template("welcome.html")


# 🔹 Signup
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


# 🔹 Login
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


# 🔹 Dashboard (Protected)
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    username = session["user"]
    user_folder = os.path.join(app.config["UPLOAD_FOLDER"], username)

    files = []
    if os.path.exists(user_folder):
        files = os.listdir(user_folder)

    return render_template(
        "dashboard.html",
        user=username,
        files=files
    )


# 🔹 File Upload (User-specific)
@app.route("/upload", methods=["POST"])
def upload_file():
    if "user" not in session:
        return redirect(url_for("login"))

    if "file" not in request.files:
        return redirect(url_for("dashboard"))

    file = request.files["file"]

    if file.filename == "":
        return redirect(url_for("dashboard"))

    username = session["user"]
    user_folder = os.path.join(app.config["UPLOAD_FOLDER"], username)
    os.makedirs(user_folder, exist_ok=True)

    file.save(os.path.join(user_folder, file.filename))

    return redirect(url_for("dashboard"))


# 🔹 Logout
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("welcome"))


# -------------------------
# App entry point (CRITICAL)
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

