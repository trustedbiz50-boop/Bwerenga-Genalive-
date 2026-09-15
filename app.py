#Calling flask#
from flask import Flask, render_template, request

#loading .env(READING)
from dotenv import load_dotenv
load_dotenv(

)
# === NEW: needed for Cloudinary photo uploads ===
import os
import uuid
import cloudinary
import cloudinary.uploader
import requests
# === END NEW ===

app = Flask(__name__)

# === NEW: Cloudinary config — reads keys from environment variables ===
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB cap

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
# === END NEW ===

#routes

@app.route("/")
def home():
    return render_template("register.html")

@app.route("/register", methods=["POST"])
def register():
    full_name = request.form["full_name"]
    phone_number = request.form["phone_number"]
    birthday = request.form["birthday"]
    share_birthday = "share_birthday" in request.form

    # === NEW: handle the uploaded photo ===
    photo_url = None
    photo = request.files.get("photo")
    if photo and photo.filename:
        if not allowed_file(photo.filename):
            return "Only JPG, PNG, or WEBP photos are allowed.", 400
        try:
            result = cloudinary.uploader.upload(
                photo, public_id=f"members/{uuid.uuid4().hex}", overwrite=False
            )
            photo_url = result["secure_url"]
        except Exception as e:
            app.logger.error(f"Cloudinary upload failed: {e}")
            return "Photo upload failed. Please try again.", 502
    # === END NEW ===

    try:
        # === CHANGED: added photo_url as 5th argument ===
        save_member(full_name, phone_number, birthday, share_birthday, photo_url)
    except sqlite3.IntegrityError:
        return "This phone number is already registered."
    
    return render_template("success.html", full_name=full_name)    

@app.route("/success")
def success():
    return render_template("success.html", full_name=None)

@app.route("/dashboard")
def dashboard():
    members = load_members()
    return render_template("dashboard.html", members=members)
    
@app.route("/celebrate/<int:id>")
def celebrate(id):
    person = get_member(id)
    return render_template("celebrate.html", person=person)

#SQlite Database#--------------------------
import sqlite3

DB_FILE = "members.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL UNIQUE,
            phone_number TEXT NOT NULL,
            birthday TEXT NOT NULL,
            share_birthday INTEGER NOT NULL,
            photo TEXT
        )
    """)
    # === NEW: migration so this also works on your existing members.db ===
    existing_cols = [row[1] for row in conn.execute("PRAGMA table_info(members)")]
    if "photo" not in existing_cols:
        conn.execute("ALTER TABLE members ADD COLUMN photo TEXT")
    # === END NEW ===
    conn.commit()
    conn.close()

def save_member(full_name, phone_number, birthday, share_birthday, photo=None):
    # === CHANGED: added photo=None parameter above, and photo column below ===
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT INTO members (full_name, phone_number, birthday, share_birthday, photo) VALUES (?, ?, ?, ?, ?)",
        (full_name, phone_number, birthday, int(share_birthday), photo)
    )
    conn.commit()
    conn.close()

def load_members():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    rows = conn.execute("SELECT * FROM members").fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_member(member_id):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
    conn.close()
    return dict(row) if row else None

init_db() #rubs on import, so gunicorn triggers it too
if __name__ == "__main__":
    # === CHANGED: was app.run(debug=True) — unsafe and unreachable on Render ===
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
