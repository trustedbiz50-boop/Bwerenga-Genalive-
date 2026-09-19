#Calling flask#
from flask import Flask, render_template, request, jsonify

#loading .env(READING)
from dotenv import load_dotenv
load_dotenv()

import os
import uuid
from contextlib import contextmanager
from datetime import datetime
import cloudinary
import cloudinary.uploader
import requests

# === CHANGED: Postgres (Neon) instead of SQLite ===
import psycopg2
from psycopg2.extras import RealDictCursor
# === END CHANGED ===

app = Flask(__name__)

# Cloudinary config — reads keys from environment variables
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB cap

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

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

    # handle the uploaded photo
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

    try:
        save_member(full_name, phone_number, location, birthday, share_birthday, photo_url)
    # === CHANGED: was sqlite3.IntegrityError ===
    except psycopg2.IntegrityError:
        return "This phone number is already registered."
    # === END CHANGED ===

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

# Postgres Database (Neon) #--------------------------

# === CHANGED: connection comes from the DATABASE_URL env var ===
DATABASE_URL = os.environ.get("DATABASE_URL")

@contextmanager
def get_db():
    """Opens a connection, hands back a cursor that returns dict rows,
    commits on success, rolls back on error, and always closes."""
    conn = psycopg2.connect(
        DATABASE_URL, cursor_factory=RealDictCursor, connect_timeout=15
    )
    try:
        with conn:  # commit on success / rollback on exception
            with conn.cursor() as cur:
                yield cur
    finally:
        conn.close()

def init_db():
    with get_db() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS members (
                id SERIAL PRIMARY KEY,
                full_name TEXT NOT NULL UNIQUE,
                phone_number TEXT NOT NULL,
                location TEXT NOT NULL,
                birthday TEXT NOT NULL,
                share_birthday INTEGER NOT NULL,
                photo TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id SERIAL PRIMARY KEY,
                title TEXT NOT NULL,
                event_date TEXT NOT NULL,
                event_time TEXT,
                location TEXT,
                poster TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS wall_posts (
                id SERIAL PRIMARY KEY,
                message TEXT NOT NULL,
                author_name TEXT,
                created_at TEXT NOT NULL,
                prayer_count INTEGER NOT NULL DEFAULT 0
            )
        """)

def save_member(full_name, phone_number, location, birthday, share_birthday, photo=None):
    with get_db() as cur:
        cur.execute(
            "INSERT INTO members (full_name, phone_number, location, birthday, share_birthday, photo) VALUES (%s, %s, %s, %s, %s, %s)",
            (full_name, phone_number, location, birthday, int(share_birthday), photo)
        )

def load_members():
    with get_db() as cur:
        cur.execute("SELECT * FROM members")
        rows = cur.fetchall()
    return [dict(row) for row in rows]

def get_member(member_id):
    with get_db() as cur:
        cur.execute("SELECT * FROM members WHERE id = %s", (member_id,))
        row = cur.fetchone()
    return dict(row) if row else None

# home page helpers

def load_members_this_month():
    """Members whose birthday falls in the current calendar month,
    ordered so the earliest day comes first. Only share_birthday=1
    is required — members without a photo still show up, using
    initials instead (handled in the template)."""
    now = datetime.now()
    # === CHANGED: strftime('%m', ...) is SQLite-only; Postgres uses EXTRACT ===
    with get_db() as cur:
        cur.execute(
            """
            SELECT * FROM members
            WHERE share_birthday = 1
              AND EXTRACT(MONTH FROM birthday::date) = %s
            ORDER BY EXTRACT(DAY FROM birthday::date)
            """,
            (now.month,)
        )
        rows = cur.fetchall()
    # === END CHANGED ===

    members = []
    for row in rows:
        member = dict(row)
        # birthday is stored as the person's actual birth date (e.g. 1998-09-21).
        # We need THIS year's weekday for that month/day, not the birth year's.
        born = datetime.strptime(member["birthday"], "%Y-%m-%d")
        this_year = born.replace(year=now.year)
        member["bday_day"] = this_year.strftime("%d").lstrip("0")
        member["bday_weekday"] = this_year.strftime("%a")  # e.g. "Mon"
        members.append(member)
    return members

def save_event(title, event_date, event_time=None, location=None, poster=None):
    with get_db() as cur:
        cur.execute(
            "INSERT INTO events (title, event_date, event_time, location, poster) VALUES (%s, %s, %s, %s, %s)",
            (title, event_date, event_time, location, poster)
        )

def load_next_event():
    """The soonest event that hasn't happened yet, or None if there isn't one."""
    today = datetime.now().strftime("%Y-%m-%d")
    with get_db() as cur:
        cur.execute(
            """
            SELECT * FROM events
            WHERE event_date >= %s
            ORDER BY event_date, event_time
            LIMIT 1
            """,
            (today,)
        )
        row = cur.fetchone()
    return dict(row) if row else None

def save_wall_post(message, author_name=None):
    with get_db() as cur:
        cur.execute(
            "INSERT INTO wall_posts (message, author_name, created_at, prayer_count) VALUES (%s, %s, %s, 0)",
            (message, author_name, datetime.now().isoformat())
        )

def load_wall_posts(limit=3, offset=0):
    """Newest posts first, a batch at a time — offset=0 gets the first
    3, offset=3 gets the next 3, and so on, for the scrolling feed."""
    with get_db() as cur:
        cur.execute(
            "SELECT * FROM wall_posts ORDER BY created_at DESC LIMIT %s OFFSET %s",
            (limit, offset)
        )
        rows = cur.fetchall()
    return [dict(row) for row in rows]

def add_prayer(post_id):
    """Bumps the prayer count by 1 when someone taps 'pray for this'."""
    with get_db() as cur:
        cur.execute(
            "UPDATE wall_posts SET prayer_count = prayer_count + 1 WHERE id = %s",
            (post_id,)
        )
# === END CHANGED ===

init_db()  # runs on import, so gunicorn triggers it too, not just __main__
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
