import os
import sqlite3
from datetime import datetime, date
from functools import wraps
from uuid import uuid4

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "traveloop.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

app = Flask(__name__)
app.config["SECRET_KEY"] = "change-this-secret-key-for-production"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def query_db(query, args=(), one=False):
    conn = get_db()
    cur = conn.execute(query, args)
    rows = cur.fetchall()
    conn.close()
    return (rows[0] if rows else None) if one else rows


def execute_db(query, args=()):
    conn = get_db()
    cur = conn.execute(query, args)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            photo TEXT,
            language TEXT DEFAULT 'English',
            saved_destinations TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS cities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            country TEXT NOT NULL,
            region TEXT NOT NULL,
            cost_index INTEGER NOT NULL,
            popularity INTEGER NOT NULL,
            description TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS activity_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city_id INTEGER,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            duration_hours REAL NOT NULL,
            cost REAL NOT NULL,
            description TEXT NOT NULL,
            image_url TEXT,
            FOREIGN KEY(city_id) REFERENCES cities(id)
        );

        CREATE TABLE IF NOT EXISTS trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            description TEXT,
            cover_photo TEXT,
            public_slug TEXT UNIQUE,
            is_public INTEGER NOT NULL DEFAULT 0,
            transport_budget REAL DEFAULT 0,
            stay_budget REAL DEFAULT 0,
            meals_budget REAL DEFAULT 0,
            activities_budget REAL DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS stops (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER NOT NULL,
            city_id INTEGER,
            city_name TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 1,
            notes TEXT,
            FOREIGN KEY(trip_id) REFERENCES trips(id),
            FOREIGN KEY(city_id) REFERENCES cities(id)
        );

        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stop_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            activity_date TEXT,
            activity_time TEXT,
            cost REAL DEFAULT 0,
            duration_hours REAL DEFAULT 1,
            description TEXT,
            FOREIGN KEY(stop_id) REFERENCES stops(id)
        );

        CREATE TABLE IF NOT EXISTS checklist_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER NOT NULL,
            item TEXT NOT NULL,
            category TEXT NOT NULL,
            packed INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(trip_id) REFERENCES trips(id)
        );

        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER NOT NULL,
            stop_id INTEGER,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(trip_id) REFERENCES trips(id),
            FOREIGN KEY(stop_id) REFERENCES stops(id)
        );

        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            booking_type TEXT NOT NULL,
            provider TEXT NOT NULL,
            location TEXT,
            start_date TEXT,
            end_date TEXT,
            confirmation_no TEXT,
            cost REAL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Planned',
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(trip_id) REFERENCES trips(id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        """
    )

    city_count = cur.execute("SELECT COUNT(*) FROM cities").fetchone()[0]
    if city_count == 0:
        cities = [
            ("Chennai", "India", "South India", 45, 88, "Coastal metro famous for temples, Marina Beach, food and culture."),
            ("Bengaluru", "India", "South India", 58, 92, "Garden city with cafes, tech hubs, parks and nearby hill trips."),
            ("Mysuru", "India", "South India", 38, 81, "Heritage city known for Mysore Palace, markets and peaceful streets."),
            ("Goa", "India", "West India", 62, 96, "Beach destination with nightlife, Portuguese heritage and water sports."),
            ("Delhi", "India", "North India", 55, 93, "Capital city with historic monuments, museums, markets and food walks."),
            ("Jaipur", "India", "North India", 48, 90, "Pink City with forts, palaces, textiles and cultural experiences."),
            ("Singapore", "Singapore", "Southeast Asia", 85, 95, "Modern island city with gardens, theme parks, shopping and clean transport."),
            ("Dubai", "UAE", "Middle East", 90, 94, "Luxury city with skyscrapers, desert safari, malls and beaches."),
            ("Paris", "France", "Europe", 88, 97, "Romantic city with art, architecture, cafes and iconic landmarks."),
            ("Tokyo", "Japan", "East Asia", 82, 98, "High-energy city with technology, temples, anime culture and food."),
        ]
        cur.executemany(
            "INSERT INTO cities (name, country, region, cost_index, popularity, description) VALUES (?, ?, ?, ?, ?, ?)",
            cities,
        )

        city_ids = {row["name"]: row["id"] for row in cur.execute("SELECT id, name FROM cities").fetchall()}
        activity_templates = [
            (city_ids["Chennai"], "Marina Beach Walk", "Sightseeing", 2, 0, "Evening beach walk with snacks and local views.", ""),
            (city_ids["Chennai"], "Kapaleeshwarar Temple Visit", "Culture", 1.5, 100, "Historic temple experience in Mylapore.", ""),
            (city_ids["Bengaluru"], "Cubbon Park Morning", "Nature", 2, 0, "Relaxing nature walk in the city center.", ""),
            (city_ids["Bengaluru"], "Cafe Hopping", "Food", 3, 1200, "Explore popular cafes and street food spots.", ""),
            (city_ids["Mysuru"], "Mysore Palace Tour", "Culture", 2.5, 250, "Visit the famous palace and evening lights.", ""),
            (city_ids["Goa"], "Beach Water Sports", "Adventure", 3, 2500, "Try parasailing, banana boat or jet ski.", ""),
            (city_ids["Goa"], "Old Goa Churches", "Culture", 2, 150, "Explore heritage churches and Portuguese architecture.", ""),
            (city_ids["Delhi"], "India Gate & Museum Trail", "Sightseeing", 4, 500, "Cover India Gate, museums and nearby landmarks.", ""),
            (city_ids["Jaipur"], "Amber Fort Visit", "Culture", 3, 350, "Fort tour with city views and photo spots.", ""),
            (city_ids["Singapore"], "Gardens by the Bay", "Sightseeing", 3, 1800, "Visit Supertree Grove and indoor gardens.", ""),
            (city_ids["Dubai"], "Desert Safari", "Adventure", 5, 4500, "Evening dunes, dinner and cultural show.", ""),
            (city_ids["Paris"], "Eiffel Tower Area Walk", "Sightseeing", 3, 2500, "Explore the Eiffel Tower, river views and cafes.", ""),
            (city_ids["Tokyo"], "Shibuya & Harajuku Tour", "Culture", 4, 1800, "Experience city crossings, fashion streets and food.", ""),
        ]
        cur.executemany(
            """
            INSERT INTO activity_templates
            (city_id, title, category, duration_hours, cost, description, image_url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            activity_templates,
        )

    admin = cur.execute("SELECT id FROM users WHERE email = ?", ("admin@traveloop.local",)).fetchone()
    if not admin:
        cur.execute(
            """
            INSERT INTO users (name, email, password_hash, role, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                "Traveloop Admin",
                "admin@traveloop.local",
                generate_password_hash("admin123"),
                "admin",
                datetime.now().isoformat(timespec="seconds"),
            ),
        )

    conn.commit()
    conn.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login to continue.", "warning")
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("dashboard"))
        return view(*args, **kwargs)
    return wrapped


def current_user():
    if "user_id" not in session:
        return None
    return query_db("SELECT * FROM users WHERE id = ?", (session["user_id"],), one=True)


@app.context_processor
def inject_user():
    return {"current_user": current_user(), "today": date.today().isoformat()}


def user_can_access_trip(trip_id):
    trip = query_db("SELECT * FROM trips WHERE id = ?", (trip_id,), one=True)
    if not trip:
        return None
    if trip["user_id"] != session.get("user_id") and session.get("role") != "admin":
        return None
    return trip


def calculate_trip_budget(trip_id):
    trip = query_db("SELECT * FROM trips WHERE id = ?", (trip_id,), one=True)
    activity_total = query_db(
        """
        SELECT COALESCE(SUM(a.cost), 0) AS total
        FROM activities a
        JOIN stops s ON a.stop_id = s.id
        WHERE s.trip_id = ?
        """,
        (trip_id,),
        one=True,
    )["total"]
    base_transport = float(trip["transport_budget"] or 0)
    base_stay = float(trip["stay_budget"] or 0)
    base_meals = float(trip["meals_budget"] or 0)
    planned_activities = float(trip["activities_budget"] or 0) + float(activity_total or 0)
    total = base_transport + base_stay + base_meals + planned_activities
    days = max(1, (datetime.fromisoformat(trip["end_date"]).date() - datetime.fromisoformat(trip["start_date"]).date()).days + 1)
    return {
        "transport": round(base_transport, 2),
        "stay": round(base_stay, 2),
        "meals": round(base_meals, 2),
        "activities": round(planned_activities, 2),
        "total": round(total, 2),
        "average_per_day": round(total / days, 2),
        "days": days,
    }


def calculate_booking_total(trip_id):
    row = query_db(
        "SELECT COALESCE(SUM(cost), 0) AS total FROM bookings WHERE trip_id = ?",
        (trip_id,),
        one=True,
    )
    return round(float(row["total"] or 0), 2)


@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not name or not email or not password:
            flash("Name, email and password are required.", "danger")
            return render_template("signup.html")
        if password != confirm:
            flash("Passwords do not match.", "danger")
            return render_template("signup.html")
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template("signup.html")
        try:
            execute_db(
                """
                INSERT INTO users (name, email, password_hash, role, created_at)
                VALUES (?, ?, ?, 'user', ?)
                """,
                (name, email, generate_password_hash(password), datetime.now().isoformat(timespec="seconds")),
            )
            flash("Account created. Please login.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("This email is already registered.", "danger")
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = query_db("SELECT * FROM users WHERE email = ?", (email,), one=True)
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for("admin_dashboard" if user["role"] == "admin" else "dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        flash("Local demo mode: password reset email is not enabled. Please contact the admin or create a new account.", "info")
        return redirect(url_for("login"))
    return render_template("forgot_password.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    trips = query_db(
        """
        SELECT t.*, COUNT(s.id) AS destination_count
        FROM trips t
        LEFT JOIN stops s ON s.trip_id = t.id
        WHERE t.user_id = ?
        GROUP BY t.id
        ORDER BY t.start_date ASC
        LIMIT 6
        """,
        (session["user_id"],),
    )
    cities = query_db("SELECT * FROM cities ORDER BY popularity DESC LIMIT 5")
    total_budget = sum(calculate_trip_budget(t["id"])["total"] for t in trips)
    booking_count = query_db(
        "SELECT COUNT(*) AS total FROM bookings WHERE user_id = ?",
        (session["user_id"],),
        one=True,
    )["total"]
    upcoming_bookings = query_db(
        """
        SELECT b.*, t.name AS trip_name
        FROM bookings b
        JOIN trips t ON t.id = b.trip_id
        WHERE b.user_id = ?
        ORDER BY COALESCE(b.start_date, b.created_at) ASC
        LIMIT 4
        """,
        (session["user_id"],),
    )
    return render_template(
        "dashboard.html",
        trips=trips,
        cities=cities,
        total_budget=total_budget,
        booking_count=booking_count,
        upcoming_bookings=upcoming_bookings,
    )


@app.route("/trips")
@login_required
def trips():
    trip_rows = query_db(
        """
        SELECT t.*, COUNT(s.id) AS destination_count
        FROM trips t
        LEFT JOIN stops s ON s.trip_id = t.id
        WHERE t.user_id = ?
        GROUP BY t.id
        ORDER BY t.created_at DESC
        """,
        (session["user_id"],),
    )
    budgets = {t["id"]: calculate_trip_budget(t["id"]) for t in trip_rows}
    return render_template("trips.html", trips=trip_rows, budgets=budgets)


@app.route("/trips/new", methods=["GET", "POST"])
@login_required
def create_trip():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        start_date = request.form.get("start_date")
        end_date = request.form.get("end_date")
        description = request.form.get("description", "").strip()
        budgets = [float(request.form.get(key, 0) or 0) for key in ["transport_budget", "stay_budget", "meals_budget", "activities_budget"]]
        cover_photo = None
        file = request.files.get("cover_photo")
        if file and file.filename and allowed_file(file.filename):
            filename = f"{uuid4().hex}_{secure_filename(file.filename)}"
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            cover_photo = filename
        if not name or not start_date or not end_date:
            flash("Trip name, start date and end date are required.", "danger")
            return render_template("create_trip.html")
        if start_date > end_date:
            flash("End date must be after or same as start date.", "danger")
            return render_template("create_trip.html")
        slug = uuid4().hex[:10]
        trip_id = execute_db(
            """
            INSERT INTO trips
            (user_id, name, start_date, end_date, description, cover_photo, public_slug,
             transport_budget, stay_budget, meals_budget, activities_budget, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session["user_id"],
                name,
                start_date,
                end_date,
                description,
                cover_photo,
                slug,
                budgets[0],
                budgets[1],
                budgets[2],
                budgets[3],
                datetime.now().isoformat(timespec="seconds"),
            ),
        )
        flash("Trip created. Now add cities and activities.", "success")
        return redirect(url_for("trip_detail", trip_id=trip_id))
    return render_template("create_trip.html")


@app.route("/trips/<int:trip_id>")
@login_required
def trip_detail(trip_id):
    trip = user_can_access_trip(trip_id)
    if not trip:
        flash("Trip not found or access denied.", "danger")
        return redirect(url_for("trips"))
    stops = query_db(
        """
        SELECT s.*, c.country, c.region, c.cost_index, c.popularity
        FROM stops s
        LEFT JOIN cities c ON c.id = s.city_id
        WHERE s.trip_id = ?
        ORDER BY s.position ASC, s.start_date ASC
        """,
        (trip_id,),
    )
    stop_data = []
    for stop in stops:
        acts = query_db("SELECT * FROM activities WHERE stop_id = ? ORDER BY activity_date, activity_time", (stop["id"],))
        stop_data.append({"stop": stop, "activities": acts})
    checklist = query_db("SELECT * FROM checklist_items WHERE trip_id = ? ORDER BY category, item", (trip_id,))
    notes = query_db("SELECT * FROM notes WHERE trip_id = ? ORDER BY updated_at DESC", (trip_id,))
    bookings = query_db("SELECT * FROM bookings WHERE trip_id = ? ORDER BY COALESCE(start_date, created_at), booking_type", (trip_id,))
    booking_total = calculate_booking_total(trip_id)
    cities = query_db("SELECT * FROM cities ORDER BY popularity DESC")
    templates = query_db(
        """
        SELECT at.*, c.name AS city_name, c.country
        FROM activity_templates at
        LEFT JOIN cities c ON c.id = at.city_id
        ORDER BY c.popularity DESC, at.category, at.title
        """
    )
    budget = calculate_trip_budget(trip_id)
    return render_template(
        "trip_detail.html",
        trip=trip,
        stop_data=stop_data,
        checklist=checklist,
        notes=notes,
        bookings=bookings,
        booking_total=booking_total,
        cities=cities,
        templates=templates,
        budget=budget,
    )


@app.route("/trips/<int:trip_id>/update-budget", methods=["POST"])
@login_required
def update_budget(trip_id):
    trip = user_can_access_trip(trip_id)
    if not trip:
        flash("Trip not found or access denied.", "danger")
        return redirect(url_for("trips"))
    execute_db(
        """
        UPDATE trips SET transport_budget = ?, stay_budget = ?, meals_budget = ?, activities_budget = ?
        WHERE id = ?
        """,
        (
            float(request.form.get("transport_budget", 0) or 0),
            float(request.form.get("stay_budget", 0) or 0),
            float(request.form.get("meals_budget", 0) or 0),
            float(request.form.get("activities_budget", 0) or 0),
            trip_id,
        ),
    )
    flash("Budget updated.", "success")
    return redirect(url_for("trip_detail", trip_id=trip_id, _anchor="budget"))


@app.route("/bookings")
@login_required
def bookings():
    booking_rows = query_db(
        """
        SELECT b.*, t.name AS trip_name, t.start_date AS trip_start, t.end_date AS trip_end
        FROM bookings b
        JOIN trips t ON t.id = b.trip_id
        WHERE b.user_id = ?
        ORDER BY COALESCE(b.start_date, b.created_at) ASC, b.created_at DESC
        """,
        (session["user_id"],),
    )
    trips_for_user = query_db(
        "SELECT id, name, start_date, end_date FROM trips WHERE user_id = ? ORDER BY start_date ASC",
        (session["user_id"],),
    )
    total_booking_cost = round(sum(float(b["cost"] or 0) for b in booking_rows), 2)
    return render_template(
        "bookings.html",
        bookings=booking_rows,
        trips=trips_for_user,
        total_booking_cost=total_booking_cost,
    )


@app.route("/trips/<int:trip_id>/bookings", methods=["POST"])
@login_required
def add_booking(trip_id):
    trip = user_can_access_trip(trip_id)
    if not trip:
        flash("Trip not found or access denied.", "danger")
        return redirect(url_for("trips"))
    booking_type = request.form.get("booking_type", "Hotel").strip()
    provider = request.form.get("provider", "").strip()
    location = request.form.get("location", "").strip()
    start_date = request.form.get("start_date") or None
    end_date = request.form.get("end_date") or None
    confirmation_no = request.form.get("confirmation_no", "").strip()
    cost = float(request.form.get("cost", 0) or 0)
    status = request.form.get("status", "Planned").strip()
    notes = request.form.get("notes", "").strip()
    if not provider:
        flash("Provider / booking name is required.", "danger")
        return redirect(url_for("trip_detail", trip_id=trip_id, _anchor="bookings"))
    execute_db(
        """
        INSERT INTO bookings
        (trip_id, user_id, booking_type, provider, location, start_date, end_date, confirmation_no, cost, status, notes, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            trip_id,
            session["user_id"],
            booking_type,
            provider,
            location,
            start_date,
            end_date,
            confirmation_no,
            cost,
            status,
            notes,
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    flash("Booking added successfully.", "success")
    return redirect(url_for("trip_detail", trip_id=trip_id, _anchor="bookings"))


@app.route("/bookings/<int:booking_id>/delete", methods=["POST"])
@login_required
def delete_booking(booking_id):
    booking = query_db("SELECT * FROM bookings WHERE id = ?", (booking_id,), one=True)
    if not booking or not user_can_access_trip(booking["trip_id"]):
        flash("Booking not found or access denied.", "danger")
        return redirect(url_for("bookings"))
    execute_db("DELETE FROM bookings WHERE id = ?", (booking_id,))
    flash("Booking deleted.", "success")
    return redirect(request.referrer or url_for("bookings"))


@app.route("/trips/<int:trip_id>/add-stop", methods=["POST"])
@login_required
def add_stop(trip_id):
    trip = user_can_access_trip(trip_id)
    if not trip:
        flash("Trip not found or access denied.", "danger")
        return redirect(url_for("trips"))
    city_id = request.form.get("city_id")
    city = query_db("SELECT * FROM cities WHERE id = ?", (city_id,), one=True) if city_id else None
    custom_city = request.form.get("custom_city", "").strip()
    city_name = city["name"] if city else custom_city
    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")
    position = int(request.form.get("position", 1) or 1)
    notes = request.form.get("notes", "").strip()
    if not city_name or not start_date or not end_date:
        flash("City and stop dates are required.", "danger")
        return redirect(url_for("trip_detail", trip_id=trip_id))
    execute_db(
        """
        INSERT INTO stops (trip_id, city_id, city_name, start_date, end_date, position, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (trip_id, city["id"] if city else None, city_name, start_date, end_date, position, notes),
    )
    flash("Stop added to itinerary.", "success")
    return redirect(url_for("trip_detail", trip_id=trip_id, _anchor="itinerary"))


@app.route("/stops/<int:stop_id>/delete", methods=["POST"])
@login_required
def delete_stop(stop_id):
    stop = query_db("SELECT * FROM stops WHERE id = ?", (stop_id,), one=True)
    if not stop or not user_can_access_trip(stop["trip_id"]):
        flash("Stop not found or access denied.", "danger")
        return redirect(url_for("trips"))
    execute_db("DELETE FROM activities WHERE stop_id = ?", (stop_id,))
    execute_db("DELETE FROM notes WHERE stop_id = ?", (stop_id,))
    execute_db("DELETE FROM stops WHERE id = ?", (stop_id,))
    flash("Stop deleted.", "success")
    return redirect(url_for("trip_detail", trip_id=stop["trip_id"], _anchor="itinerary"))


@app.route("/stops/<int:stop_id>/add-activity", methods=["POST"])
@login_required
def add_activity(stop_id):
    stop = query_db("SELECT * FROM stops WHERE id = ?", (stop_id,), one=True)
    if not stop or not user_can_access_trip(stop["trip_id"]):
        flash("Stop not found or access denied.", "danger")
        return redirect(url_for("trips"))
    template_id = request.form.get("template_id")
    if template_id:
        template = query_db("SELECT * FROM activity_templates WHERE id = ?", (template_id,), one=True)
        title = template["title"]
        category = template["category"]
        cost = template["cost"]
        duration = template["duration_hours"]
        description = template["description"]
    else:
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "Sightseeing").strip()
        cost = float(request.form.get("cost", 0) or 0)
        duration = float(request.form.get("duration_hours", 1) or 1)
        description = request.form.get("description", "").strip()
    if not title:
        flash("Activity title is required.", "danger")
        return redirect(url_for("trip_detail", trip_id=stop["trip_id"]))
    execute_db(
        """
        INSERT INTO activities
        (stop_id, title, category, activity_date, activity_time, cost, duration_hours, description)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            stop_id,
            title,
            category,
            request.form.get("activity_date"),
            request.form.get("activity_time"),
            cost,
            duration,
            description,
        ),
    )
    flash("Activity added.", "success")
    return redirect(url_for("trip_detail", trip_id=stop["trip_id"], _anchor="activities"))


@app.route("/activities/<int:activity_id>/delete", methods=["POST"])
@login_required
def delete_activity(activity_id):
    activity = query_db(
        """
        SELECT a.*, s.trip_id
        FROM activities a
        JOIN stops s ON s.id = a.stop_id
        WHERE a.id = ?
        """,
        (activity_id,),
        one=True,
    )
    if not activity or not user_can_access_trip(activity["trip_id"]):
        flash("Activity not found or access denied.", "danger")
        return redirect(url_for("trips"))
    execute_db("DELETE FROM activities WHERE id = ?", (activity_id,))
    flash("Activity removed.", "success")
    return redirect(url_for("trip_detail", trip_id=activity["trip_id"], _anchor="activities"))


@app.route("/trips/<int:trip_id>/checklist", methods=["POST"])
@login_required
def add_checklist_item(trip_id):
    trip = user_can_access_trip(trip_id)
    if not trip:
        flash("Trip not found or access denied.", "danger")
        return redirect(url_for("trips"))
    item = request.form.get("item", "").strip()
    category = request.form.get("category", "General").strip()
    if item:
        execute_db("INSERT INTO checklist_items (trip_id, item, category) VALUES (?, ?, ?)", (trip_id, item, category))
        flash("Checklist item added.", "success")
    return redirect(url_for("trip_detail", trip_id=trip_id, _anchor="checklist"))


@app.route("/checklist/<int:item_id>/toggle", methods=["POST"])
@login_required
def toggle_checklist_item(item_id):
    item = query_db("SELECT * FROM checklist_items WHERE id = ?", (item_id,), one=True)
    if not item or not user_can_access_trip(item["trip_id"]):
        flash("Checklist item not found or access denied.", "danger")
        return redirect(url_for("trips"))
    execute_db("UPDATE checklist_items SET packed = ? WHERE id = ?", (0 if item["packed"] else 1, item_id))
    return redirect(url_for("trip_detail", trip_id=item["trip_id"], _anchor="checklist"))


@app.route("/checklist/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_checklist_item(item_id):
    item = query_db("SELECT * FROM checklist_items WHERE id = ?", (item_id,), one=True)
    if not item or not user_can_access_trip(item["trip_id"]):
        flash("Checklist item not found or access denied.", "danger")
        return redirect(url_for("trips"))
    execute_db("DELETE FROM checklist_items WHERE id = ?", (item_id,))
    flash("Checklist item deleted.", "success")
    return redirect(url_for("trip_detail", trip_id=item["trip_id"], _anchor="checklist"))


@app.route("/trips/<int:trip_id>/reset-checklist", methods=["POST"])
@login_required
def reset_checklist(trip_id):
    trip = user_can_access_trip(trip_id)
    if not trip:
        flash("Trip not found or access denied.", "danger")
        return redirect(url_for("trips"))
    execute_db("UPDATE checklist_items SET packed = 0 WHERE trip_id = ?", (trip_id,))
    flash("Checklist reset for reuse.", "success")
    return redirect(url_for("trip_detail", trip_id=trip_id, _anchor="checklist"))


@app.route("/trips/<int:trip_id>/notes", methods=["POST"])
@login_required
def add_note(trip_id):
    trip = user_can_access_trip(trip_id)
    if not trip:
        flash("Trip not found or access denied.", "danger")
        return redirect(url_for("trips"))
    title = request.form.get("title", "").strip()
    body = request.form.get("body", "").strip()
    stop_id = request.form.get("stop_id") or None
    if title and body:
        now = datetime.now().isoformat(timespec="seconds")
        execute_db(
            "INSERT INTO notes (trip_id, stop_id, title, body, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (trip_id, stop_id, title, body, now, now),
        )
        flash("Note saved.", "success")
    return redirect(url_for("trip_detail", trip_id=trip_id, _anchor="notes"))


@app.route("/notes/<int:note_id>/delete", methods=["POST"])
@login_required
def delete_note(note_id):
    note = query_db("SELECT * FROM notes WHERE id = ?", (note_id,), one=True)
    if not note or not user_can_access_trip(note["trip_id"]):
        flash("Note not found or access denied.", "danger")
        return redirect(url_for("trips"))
    execute_db("DELETE FROM notes WHERE id = ?", (note_id,))
    flash("Note deleted.", "success")
    return redirect(url_for("trip_detail", trip_id=note["trip_id"], _anchor="notes"))


@app.route("/trips/<int:trip_id>/share", methods=["POST"])
@login_required
def toggle_share(trip_id):
    trip = user_can_access_trip(trip_id)
    if not trip:
        flash("Trip not found or access denied.", "danger")
        return redirect(url_for("trips"))
    new_state = 0 if trip["is_public"] else 1
    execute_db("UPDATE trips SET is_public = ? WHERE id = ?", (new_state, trip_id))
    flash("Public sharing enabled." if new_state else "Public sharing disabled.", "success")
    return redirect(url_for("trip_detail", trip_id=trip_id, _anchor="share"))


@app.route("/public/<slug>")
def public_trip(slug):
    trip = query_db(
        """
        SELECT t.*, u.name AS owner_name
        FROM trips t
        JOIN users u ON u.id = t.user_id
        WHERE t.public_slug = ? AND t.is_public = 1
        """,
        (slug,),
        one=True,
    )
    if not trip:
        flash("This itinerary is not public or does not exist.", "danger")
        return redirect(url_for("index"))
    stops = query_db("SELECT * FROM stops WHERE trip_id = ? ORDER BY position, start_date", (trip["id"],))
    stop_data = []
    for stop in stops:
        acts = query_db("SELECT * FROM activities WHERE stop_id = ? ORDER BY activity_date, activity_time", (stop["id"],))
        stop_data.append({"stop": stop, "activities": acts})
    budget = calculate_trip_budget(trip["id"])
    return render_template("public_trip.html", trip=trip, stop_data=stop_data, budget=budget)


@app.route("/public/<slug>/copy", methods=["POST"])
@login_required
def copy_trip(slug):
    original = query_db("SELECT * FROM trips WHERE public_slug = ? AND is_public = 1", (slug,), one=True)
    if not original:
        flash("Trip cannot be copied.", "danger")
        return redirect(url_for("dashboard"))
    new_slug = uuid4().hex[:10]
    new_id = execute_db(
        """
        INSERT INTO trips
        (user_id, name, start_date, end_date, description, cover_photo, public_slug, transport_budget,
         stay_budget, meals_budget, activities_budget, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session["user_id"],
            f"Copy of {original['name']}",
            original["start_date"],
            original["end_date"],
            original["description"],
            original["cover_photo"],
            new_slug,
            original["transport_budget"],
            original["stay_budget"],
            original["meals_budget"],
            original["activities_budget"],
            datetime.now().isoformat(timespec="seconds"),
        ),
    )
    old_stops = query_db("SELECT * FROM stops WHERE trip_id = ? ORDER BY position", (original["id"],))
    for old_stop in old_stops:
        new_stop_id = execute_db(
            "INSERT INTO stops (trip_id, city_id, city_name, start_date, end_date, position, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (new_id, old_stop["city_id"], old_stop["city_name"], old_stop["start_date"], old_stop["end_date"], old_stop["position"], old_stop["notes"]),
        )
        old_activities = query_db("SELECT * FROM activities WHERE stop_id = ?", (old_stop["id"],))
        for old_act in old_activities:
            execute_db(
                "INSERT INTO activities (stop_id, title, category, activity_date, activity_time, cost, duration_hours, description) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (new_stop_id, old_act["title"], old_act["category"], old_act["activity_date"], old_act["activity_time"], old_act["cost"], old_act["duration_hours"], old_act["description"]),
            )
    flash("Public itinerary copied to your trips.", "success")
    return redirect(url_for("trip_detail", trip_id=new_id))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        language = request.form.get("language", "English").strip()
        saved_destinations = request.form.get("saved_destinations", "").strip()
        photo = user["photo"]
        file = request.files.get("photo")
        if file and file.filename and allowed_file(file.filename):
            filename = f"{uuid4().hex}_{secure_filename(file.filename)}"
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            photo = filename
        try:
            execute_db(
                "UPDATE users SET name = ?, email = ?, language = ?, saved_destinations = ?, photo = ? WHERE id = ?",
                (name, email, language, saved_destinations, photo, session["user_id"]),
            )
            session["name"] = name
            flash("Profile updated.", "success")
        except sqlite3.IntegrityError:
            flash("Email already used by another account.", "danger")
        return redirect(url_for("profile"))
    return render_template("profile.html", user=user)


@app.route("/profile/delete", methods=["POST"])
@login_required
def delete_account():
    if session.get("role") == "admin":
        flash("Admin demo account cannot be deleted.", "danger")
        return redirect(url_for("profile"))
    user_id = session["user_id"]
    trips_to_delete = query_db("SELECT id FROM trips WHERE user_id = ?", (user_id,))
    for trip in trips_to_delete:
        stops_to_delete = query_db("SELECT id FROM stops WHERE trip_id = ?", (trip["id"],))
        for stop in stops_to_delete:
            execute_db("DELETE FROM activities WHERE stop_id = ?", (stop["id"],))
        execute_db("DELETE FROM notes WHERE trip_id = ?", (trip["id"],))
        execute_db("DELETE FROM checklist_items WHERE trip_id = ?", (trip["id"],))
        execute_db("DELETE FROM bookings WHERE trip_id = ?", (trip["id"],))
        execute_db("DELETE FROM stops WHERE trip_id = ?", (trip["id"],))
        execute_db("DELETE FROM trips WHERE id = ?", (trip["id"],))
    execute_db("DELETE FROM users WHERE id = ?", (user_id,))
    session.clear()
    flash("Account deleted.", "success")
    return redirect(url_for("index"))


@app.route("/admin")
@admin_required
def admin_dashboard():
    stats = {
        "users": query_db("SELECT COUNT(*) AS total FROM users", one=True)["total"],
        "trips": query_db("SELECT COUNT(*) AS total FROM trips", one=True)["total"],
        "stops": query_db("SELECT COUNT(*) AS total FROM stops", one=True)["total"],
        "activities": query_db("SELECT COUNT(*) AS total FROM activities", one=True)["total"],
        "bookings": query_db("SELECT COUNT(*) AS total FROM bookings", one=True)["total"],
    }
    users = query_db(
        """
        SELECT u.id, u.name, u.email, u.role, u.created_at, COUNT(t.id) AS trip_count
        FROM users u
        LEFT JOIN trips t ON t.user_id = u.id
        GROUP BY u.id
        ORDER BY u.created_at DESC
        """
    )
    top_cities = query_db(
        """
        SELECT city_name, COUNT(*) AS count
        FROM stops
        GROUP BY city_name
        ORDER BY count DESC, city_name ASC
        LIMIT 8
        """
    )
    top_activities = query_db(
        """
        SELECT title, COUNT(*) AS count
        FROM activities
        GROUP BY title
        ORDER BY count DESC, title ASC
        LIMIT 8
        """
    )
    trip_rows = query_db(
        """
        SELECT t.*, u.name AS owner_name, COUNT(s.id) AS destination_count
        FROM trips t
        JOIN users u ON u.id = t.user_id
        LEFT JOIN stops s ON s.trip_id = t.id
        GROUP BY t.id
        ORDER BY t.created_at DESC
        LIMIT 20
        """
    )
    return render_template(
        "admin.html",
        stats=stats,
        users=users,
        top_cities=top_cities,
        top_activities=top_activities,
        trips=trip_rows,
    )


@app.route("/admin/users/<int:user_id>/toggle-role", methods=["POST"])
@admin_required
def toggle_user_role(user_id):
    user = query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin_dashboard"))
    if user["email"] == "admin@traveloop.local":
        flash("Default admin role cannot be changed.", "warning")
        return redirect(url_for("admin_dashboard"))
    new_role = "admin" if user["role"] == "user" else "user"
    execute_db("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    flash("User role updated.", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/trips/<int:trip_id>/delete", methods=["POST"])
@login_required
def delete_trip(trip_id):
    trip = user_can_access_trip(trip_id)
    if not trip:
        flash("Trip not found or access denied.", "danger")
        return redirect(url_for("trips"))
    stops = query_db("SELECT id FROM stops WHERE trip_id = ?", (trip_id,))
    for stop in stops:
        execute_db("DELETE FROM activities WHERE stop_id = ?", (stop["id"],))
    execute_db("DELETE FROM notes WHERE trip_id = ?", (trip_id,))
    execute_db("DELETE FROM checklist_items WHERE trip_id = ?", (trip_id,))
    execute_db("DELETE FROM bookings WHERE trip_id = ?", (trip_id,))
    execute_db("DELETE FROM stops WHERE trip_id = ?", (trip_id,))
    execute_db("DELETE FROM trips WHERE id = ?", (trip_id,))
    flash("Trip deleted.", "success")
    return redirect(url_for("trips" if session.get("role") != "admin" else "admin_dashboard"))


if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    init_db()
    app.run(debug=True, host="0.0.0.0", port=5000)
