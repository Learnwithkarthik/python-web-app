import os
import time
import sqlalchemy
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from google.cloud.sql.connector import Connector

# ------------------------
# Flask App Setup
# ------------------------
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")

# ------------------------
# Cloud SQL Configuration
# ------------------------
PROJECT_ID = "terraform-482817"
REGION = "us-central1"
INSTANCE_NAME = "db-instance"

INSTANCE_CONNECTION_NAME = f"{PROJECT_ID}:{REGION}:{INSTANCE_NAME}"
DB_NAME = "appdb"
DB_USER = "appuser"
DB_PASSWORD = os.environ["DB_PASSWORD"]  # from Secret Manager

# ------------------------
# Cloud SQL Connector
# ------------------------
connector = Connector()

def getconn():
    conn = connector.connect(
        INSTANCE_CONNECTION_NAME,
        "pg8000",
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
    )
    return conn

engine = sqlalchemy.create_engine(
    "postgresql+pg8000://",
    creator=getconn,
    pool_size=5,
    max_overflow=2,
    pool_timeout=30,
    pool_recycle=1800,
)

# ------------------------
# Routes
# ------------------------

@app.route("/")
def welcome():
    return render_template("welcome.html")

# ------------------------
# DB Health Check
# ------------------------
@app.route("/db-check")
def db_check():
    start = time.time()
    with engine.connect() as conn:
        conn.execute(sqlalchemy.text("SELECT 1")).fetchone()
    latency_ms = (time.time() - start) * 1000
    return f"DB OK ✅ | latency={latency_ms:.2f} ms"

# ------------------------
# Signup
# ------------------------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        password_hash = generate_password_hash(password)

        with engine.begin() as conn:
            conn.execute(
                sqlalchemy.text("""
                    INSERT INTO users (username, email, password_hash)
                    VALUES (:username, :email, :password_hash)
                """),
                {
                    "username": username,
                    "email": email,
                    "password_hash": password_hash,
                }
            )

        return redirect(url_for("login"))

    return render_template("signup.html")

# ------------------------
# Login
# ------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        start = time.time()

        with engine.connect() as conn:
            user = conn.execute(
                sqlalchemy.text("""
                    SELECT id, password_hash
                    FROM users
                    WHERE username = :username
                """),
                {"username": username}
            ).fetchone()

        latency_ms = (time.time() - start) * 1000
        status = "FAILED"
        user_id = None

        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            user_id = user.id
            status = "SUCCESS"

        # Store login event
        with engine.begin() as conn:
            conn.execute(
                sqlalchemy.text("""
                    INSERT INTO login_events (user_id, status, latency_ms)
                    VALUES (:user_id, :status, :latency)
                """),
                {
                    "user_id": user_id,
                    "status": status,
                    "latency": int(latency_ms),
                }
            )

        if status == "SUCCESS":
            return redirect(url_for("dashboard"))

        return "Invalid username or password", 401

    return render_template("login.html")

# ------------------------
# Dashboard
# ------------------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html")

# ------------------------
# Logout
# ------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("welcome"))

# ------------------------
# App Entry Point
# ------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
