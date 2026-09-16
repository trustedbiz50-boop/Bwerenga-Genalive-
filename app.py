#Calling flask#
from flask import Flask, render_template, request

#loading .env(READING)
from dotenv import load_dotenv
load_dotenv(

)
# === NEW: needed for Cloudinary photo uploads ===
import os
import uuid
from datetime import datetime
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
    location = request.form["location"]
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
        save_member(full_name, phone_number, location, birthday, share_birthday, photo_url)
    except sqlite3.IntegrityError:
        return "This phone number is already registered."
    
    return render_template("success.html", full_name=full_name)    

#Load life.html and then call any of the load funnctions(loop)
@app.route("/life")
def life():
    members_this_month = load_members_this_month()
    next_event = load_next_event()
    wall_posts = load_wall_posts()
    return render_template(
        "life.html",
        members=members_this_month,
        next_event=next_event,
        wall_posts=wall_posts
        )

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

#A mini API endpoint that hands frontend 3 prayer wall posts 

from flask import jsonify
@app.route("/api/wall-feed")
def wall_feed():
    offset = int(request.args.get("offset", 0))
    posts = load_wall_posts(limit=3, offset=offset)
    return jsonify(posts)

# Prayer Wall API . Feeds the scrolling wall + prayer counter
@app.route("/api/wall/<int:post_id>/pray", methods=["POST"])

def pray_for_post(post_id):
    add_prayer(post_id)
    return jsonify({"status": "ok"})

@app.route("/api/wall/new", methods=["POST"])
def wall_new():
    data = request.get_json()
    message = data.get("message", "").strip()
    author_name = data.get("author_name", "").strip() or None
    if not message:
        return jsonify({"error": "message required"}), 400
    save_wall_post(message, author_name)
    newest = load_wall_posts(limit=1, offset=0)
    return jsonify(newest[0])

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
            location TEXT NOT NULL,
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

    # === NEW: home page tables — events (for the "Next event" banner)
    # and wall_posts (for the prayer wall) ===
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            event_date TEXT NOT NULL,
            event_time TEXT,
            location TEXT,
            poster TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wall_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message TEXT NOT NULL,
            author_name TEXT,
            created_at TEXT NOT NULL,
            prayer_count INTEGER NOT NULL DEFAULT 0
        )
    """)
    # === END NEW ===

    conn.commit()
    conn.close()

def save_member(full_name, phone_number, location, birthday, share_birthday, photo=None):
    # === CHANGED: added photo=None parameter above, and photo column below ===
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT INTO members (full_name, phone_number, location, birthday, share_birthday, photo) VALUES (?, ?, ?, ?, ?, ?)",
        (full_name, phone_number, location, birthday, int(share_birthday), photo)
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

# === NEW: home page helpers ===

def load_members_this_month():
    """Members whose birthday falls in the current calendar month,
    ordered so the earliest day comes first. share_birthday must be
    on and we need a photo to show a circle for them."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    current_month = datetime.now().strftime("%m")  # e.g. "09"
    rows = conn.execute(
        """
        SELECT * FROM members
        WHERE share_birthday = 1
          AND photo IS NOT NULL
          AND strftime('%m', birthday) = ?
        ORDER BY strftime('%d', birthday)
        """,
        (current_month,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def save_event(title, event_date, event_time=None, location=None, poster=None):
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT INTO events (title, event_date, event_time, location, poster) VALUES (?, ?, ?, ?, ?)",
        (title, event_date, event_time, location, poster)
    )
    conn.commit()
    conn.close()

def load_next_event():
    """The soonest event that hasn't happened yet, or None if there isn't one."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    today = datetime.now().strftime("%Y-%m-%d")
    row = conn.execute(
        """
        SELECT * FROM events
        WHERE event_date >= ?
        ORDER BY event_date, event_time
        LIMIT 1
        """,
        (today,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None

def save_wall_post(message, author_name=None):
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT INTO wall_posts (message, author_name, created_at, prayer_count) VALUES (?, ?, ?, 0)",
        (message, author_name, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def load_wall_posts(limit=3, offset=0):
    """Newest posts first, a batch at a time — offset=0 gets the first
    3, offset=3 gets the next 3, and so on, for the scrolling feed."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM wall_posts ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_prayer(post_id):
    """Bumps the prayer count by 1 when someone taps 'pray for this'."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "UPDATE wall_posts SET prayer_count = prayer_count + 1 WHERE id = ?",
        (post_id,)
    )
    conn.commit()
    conn.close()
# === END NEW ===

init_db()  # runs on import, so gunicorn triggers it too, not just __main__
if __name__ == "__main__":
    # === CHANGED: was app.run(debug=True) — unsafe and unreachable on Render ===
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
