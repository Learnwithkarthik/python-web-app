import os
import json
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from google.cloud import storage

# -------------------------
# Flask App Setup
# -------------------------
app = Flask(__name__)
app.secret_key = "super-secret-key"  # required for sessions

# -------------------------
# Upload folder (local)
# -------------------------
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# -------------------------
# TEMP in-memory users DB
# (later replace with Firestore / SQL)
# -------------------------
users_db = {}

# -------------------------
# GCS CONFIG (IMPORTANT)
# -------------------------
GCS_BUCKET_NAME = "login-events-bucket-karthik"  # 🔴 CHANGE THIS

# -------------------------
# Helper: Write login event to GCS
# -------------------------
def write_login_event_to_gcs(username, status, ip):
    """
    Writes login attempt metadata to GCS.
    This will trigger Cloud Function later.
    """

    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET_NAME)

    event_data = {
        "username": username,
        "status": status,           # SUCCESS or FAILED
        "ip_address": ip,
        "timestamp": datetime.utcnow().isoformat()
    }

    filename = f"login-events/{username}-{datetime.utcnow().timestamp()}.json"
    blob = bucket.blob(filename)

    blob.upload_from_string(
        json.dumps(event_data),
        content_type="application/json"
    )

# -------------------------
# Routes
# -------------------------

# 🔹 Welcome Page
@app.route("/")
def welcome():
    return render_template("welcome.html")

# 🔹 Signup
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username in users_db:
            return "User already exists"

        users_db[username] = {
            "password": generate_password_hash(password)
        }

        return redirect(url_for("login"))

    return render_template("signup.html")

# 🔹 Login (EVENT IS GENERATED HERE)
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        ip = request.remote_addr

        user = users_db.get(username)

        # ❌ FAILED LOGIN
        if not user or not check_password_hash(user["password"], password):
            write_login_event_to_gcs(username, "FAILED", ip)
            return "Invalid username or password"

        # ✅ SUCCESS LOGIN
        write_login_event_to_gcs(username, "SUCCESS", ip)
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
    os.makedirs(user_folder, exist_ok=True)

    files = os.listdir(user_folder)

    return render_template("dashboard.html", user=username, files=files)

# 🔹 File Upload
@app.route("/upload", methods=["POST"])
def upload_file():
    if "user" not in session:
        return redirect(url_for("login"))

    file = request.files.get("file")
    if not file or file.filename == "":
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
# App Entry Point
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

