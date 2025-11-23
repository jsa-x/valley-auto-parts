from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import timedelta
from collections import Counter
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

orders_db = {}      # {username: [order, order, ...]}
next_order_id = 1   # simple auto-increment for order IDs

app = Flask(__name__)
app.secret_key = "valleyautoparts_secret_key"
app.permanent_session_lifetime = timedelta(days=1)


# Temporary DB for parts on main page
parts_db = [
    {
        "id": "brakepads-ceramic-front",
        "name": "Ceramic Brake Pads",
        "category": "Brakes",
        "fitment": "2010 Honda Civic",
        "price": 54.99,
        "img": "https://m.media-amazon.com/images/I/61Nhezi-FhL.jpg",
        "description": "Low dust ceramic pads for quieter braking and longer rotor life."
    },
    {
        "id": "serpentine-belt-6pk",
        "name": "Serpentine Drive Belt",
        "category": "Belts",
        "fitment": "2010 Honda Civic – 1.8L engine",
        "price": 24.50,
        "img": "https://m.media-amazon.com/images/I/51Do-9yc1xL._AC_UF894%2C1000_QL80_.jpg",
        "description": "High temp EPDM replacement belt for alternator, A/C, and power steering."
    },
    {
        "id": "alternator-110amp",
        "name": "110A Alternator",
        "category": "Electrical",
        "fitment": "2015 Toyota Corolla – 1.8L",
        "price": 129.99,
        "img": "https://m.media-amazon.com/images/I/91oO1pOORjL._AC_UF894%2C1000_QL80_.jpg",
        "description": "OEM output with internal voltage regulator. Core charge may apply."
    },
    {
        "id": "oil-filter-synthetic",
        "name": "High Mileage Oil Filter",
        "category": "Filters",
        "fitment": "2015 Toyota Corolla – spin-on filter",
        "price": 9.99,
        "img": "https://www.rockauto.com/info/915/PH4967_Front.jpg",
        "description": "Synthetic media filter rated for 10,000 mile protection."
    },
    {
        "id": "full-synthetic-5w30",
        "name": "5W-30 Full Synthetic Motor Oil (1 Qt)",
        "category": "Fluids",
        "fitment": "2012 Ford F-150 – 5.0L / 3.5L (meets spec)",
        "price": 8.99,
        "img": "https://www.rockauto.com/info/267/103535-02.jpg",
        "description": "Protects against sludge and thermal breakdown in all conditions."
    },
    {
        "id": "spark-plug-iridium",
        "name": "Iridium Spark Plug",
        "category": "Ignition",
        "fitment": "2012 Ford F-150 – V8/V6 applications",
        "price": 11.49,
        "img": "https://www.rockauto.com/info/341/19185432_Primary.jpg",
        "description": "Iridium tip for long life and improved ignition efficiency."
    },
    {
        "id": "cv-axle-front-left",
        "name": "Front Left CV Axle Shaft",
        "category": "Drivetrain",
        "fitment": "2014 Chevy Silverado – 4WD front left",
        "price": 89.99,
        "img": "https://www.rockauto.com/info/165/165_TO88079A1_4.jpg",
        "description": "Remanufactured OE replacement half shaft with new joints."
    },
    {
        "id": "rear-shock-absorber",
        "name": "Rear Shock Absorber",
        "category": "Suspension",
        "fitment": "2014 Chevy Silverado – rear suspension",
        "price": 49.99,
        "img": "https://www.rockauto.com/info/1145/1145_314065_1.jpg",
        "description": "Restores ride comfort and stability on rough or uneven roads."
    },
    {
        "id": "cabin-air-filter-charcoal",
        "name": "Charcoal Cabin Air Filter",
        "category": "Filters",
        "fitment": "2016 Nissan Altima – HVAC cabin filter",
        "price": 15.99,
        "img": "https://www.rockauto.com/info/39/24871.jpg",
        "description": "Activated carbon filter for improved HVAC air quality."
    },
    {
        "id": "led-headlight-h11",
        "name": "LED Headlight Kit",
        "category": "Lighting",
        "fitment": "2016 Nissan Altima – H11 low beam",
        "price": 59.99,
        "img": "https://www.rockauto.com/info/1161/T2_GM2502238_Fro.jpg",
        "description": "High output LED bulbs with cooling fan and weather sealed design."
    }
]
@app.route("/api/products")
def api_products():
    return jsonify(parts_db)

def logged_in():
    return "username" in session

def current_user():
    return session.get("username")

def register_user(username, email, password):
    # hash the password
    password_hash = generate_password_hash(password)

    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username, email, password_hash),
        )
        conn.commit()
        conn.close()
        return (True, "Account created successfully.")
    except sqlite3.IntegrityError:
        # username needs to be unqie
        return (False, "Username already exists.")


def authenticate(username, password):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT username, password_hash FROM users WHERE username = ?",
        (username,),
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        return False

    # check the entered password against the stored hash
    return check_password_hash(row["password_hash"], password)


@app.route("/")
def shop():
    # pull one time banner message from session if present
    banner = session.pop("flash_msg", None)

    return render_template(
        "shop.html",
        parts=parts_db,
        logged_in=logged_in(),
        username=current_user(),
        banner=banner
    )

@app.route("/register", methods=["GET", "POST"])
def register():
    msg, ok = "", False
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if not username or not email or not password:
            msg = "All fields are required."
        else:
            ok, msg = register_user(username, email, password)
    return render_template("register.html", msg=msg, ok=ok)

@app.route("/login", methods=["GET", "POST"])
def login():
    msg, ok = "", False
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if authenticate(username, password):
            session["username"] = username
            msg = "Login Successful"
            ok = True
            # no redirect yet show message first confirming succesful login
        else:
            msg = "Invalid username or password."
    return render_template("login.html", msg=msg, ok=ok)

@app.route("/cart")
def cart():
    username = session.get("username")
    if not username:
        # you can also flash a message if you want
        return redirect(url_for("login"))

    return render_template(
        "cart.html",
        logged_in=True,
        username=username
    )

@app.route("/api/orders", methods=["GET", "POST"])
def api_orders():
    global next_order_id

    username = session.get("username")
    if not username:
        return jsonify({"error": "not_logged_in"}), 401

    # GET: return JSON list of this user's orders
    if request.method == "GET":
        return jsonify(orders_db.get(username, []))

    # POST: create a new order from a list of product IDs
    data = request.get_json() or {}
    item_ids = data.get("items", [])
    if not item_ids:
        return jsonify({"error": "empty_cart"}), 400

    counts = Counter(item_ids)
    order_items = []
    total = 0.0

    for pid, qty in counts.items():
        part = next((p for p in parts_db if p["id"] == pid), None)
        if not part:
            continue

        line_total = part["price"] * qty
        total += line_total
        order_items.append({
            "id": pid,
            "name": part["name"],
            "qty": qty,
            "unit_price": part["price"],
            "line_total": round(line_total, 2),
        })

    order = {
        "order_id": next_order_id,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "items": order_items,
        "total": round(total, 2),
    }

    orders_db.setdefault(username, []).append(order)
    next_order_id += 1

    # one-time success message for /orders page
    session["order_flash"] = f"Order #{order['order_id']} placed successfully."

    return jsonify({"ok": True, "order": order})
@app.route("/orders")
def orders():
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))

    user_orders = orders_db.get(username, [])
    banner = session.pop("order_flash", None)  # read and clear one-time message
    return render_template(
        "orders.html",
        logged_in=True,
        username=username,
        orders=user_orders,
        banner=banner,
    )

@app.route("/payment")
def payment():
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))

    return render_template(
        "payment.html",
        logged_in=True,
        username=username
    )

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("shop"))

@app.route("/api/session")
def api_session():
    return jsonify({"logged_in": logged_in(), "username": current_user()})

@app.route("/api/parts")
def api_parts():
    return jsonify(parts_db)

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)
