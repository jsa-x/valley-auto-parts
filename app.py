from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import timedelta
from collections import Counter
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
import secrets
from dotenv import load_dotenv
import stripe

# -------------------------------------------------
# SQLite configuration (single DB for users+products)
# -------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), "store.db")


def get_db():
    """Open a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dicts
    return conn


# -------------------------------------------------
# Seed products (used only if products table is empty)
# -------------------------------------------------
VEHICLE_OPTIONS = [
    "2010 Honda Civic",
    "2015 Toyota Corolla",
    "2012 Ford F-150",
    "2014 Chevy Silverado",
    "2016 Nissan Altima",
]

SEED_PRODUCTS = [
    {
        "id": "brakepads-ceramic-front",
        "name": "Ceramic Brake Pads",
        "category": "Brakes",
        "fitment": "2010 Honda Civic",
        "price": 54.99,
        "img": "https://m.media-amazon.com/images/I/61Nhezi-FhL.jpg",
        "description": "Low dust ceramic pads for quieter braking and longer rotor life.",
    },
    {
        "id": "serpentine-belt-6pk",
        "name": "Serpentine Drive Belt",
        "category": "Belts",
        "fitment": "2010 Honda Civic – 1.8L engine",
        "price": 24.50,
        "img": "https://m.media-amazon.com/images/I/51Do-9yc1xL._AC_UF894%2C1000_QL80_.jpg",
        "description": "High temp EPDM replacement belt for alternator, A/C, and power steering.",
    },
    {
        "id": "alternator-110amp",
        "name": "110A Alternator",
        "category": "Electrical",
        "fitment": "2015 Toyota Corolla – 1.8L",
        "price": 129.99,
        "img": "https://m.media-amazon.com/images/I/91oO1pOORjL._AC_UF894%2C1000_QL80_.jpg",
        "description": "OEM output with internal voltage regulator. Core charge may apply.",
    },
    {
        "id": "oil-filter-synthetic",
        "name": "High Mileage Oil Filter",
        "category": "Filters",
        "fitment": "2015 Toyota Corolla – spin-on filter",
        "price": 9.99,
        "img": "https://www.rockauto.com/info/915/PH4967_Front.jpg",
        "description": "Synthetic media filter rated for 10,000 mile protection.",
    },
    {
        "id": "full-synthetic-5w30",
        "name": "5W-30 Full Synthetic Motor Oil (1 Qt)",
        "category": "Fluids",
        "fitment": "2012 Ford F-150 – 5.0L / 3.5L (meets spec)",
        "price": 8.99,
        "img": "https://www.rockauto.com/info/267/103535-02.jpg",
        "description": "Protects against sludge and thermal breakdown in all conditions.",
    },
    {
        "id": "spark-plug-iridium",
        "name": "Iridium Spark Plug",
        "category": "Ignition",
        "fitment": "2012 Ford F-150 – V8/V6 applications",
        "price": 11.49,
        "img": "https://www.rockauto.com/info/341/19185432_Primary.jpg",
        "description": "Iridium tip for long life and improved ignition efficiency.",
    },
    {
        "id": "cv-axle-front-left",
        "name": "Front Left CV Axle Shaft",
        "category": "Drivetrain",
        "fitment": "2014 Chevy Silverado – 4WD front left",
        "price": 89.99,
        "img": "https://www.rockauto.com/info/165/165_TO88079A1_4.jpg",
        "description": "Remanufactured OE replacement half shaft with new joints.",
    },
    {
        "id": "rear-shock-absorber",
        "name": "Rear Shock Absorber",
        "category": "Suspension",
        "fitment": "2014 Chevy Silverado – rear suspension",
        "price": 49.99,
        "img": "https://www.rockauto.com/info/1145/1145_314065_1.jpg",
        "description": "Restores ride comfort and stability on rough or uneven roads.",
    },
    {
        "id": "cabin-air-filter-charcoal",
        "name": "Charcoal Cabin Air Filter",
        "category": "Filters",
        "fitment": "2016 Nissan Altima – HVAC cabin filter",
        "price": 15.99,
        "img": "https://www.rockauto.com/info/39/24871.jpg",
        "description": "Activated carbon filter for improved HVAC air quality.",
    },
    {
        "id": "led-headlight-h11",
        "name": "LED Headlight Kit",
        "category": "Lighting",
        "fitment": "2016 Nissan Altima – H11 low beam",
        "price": 59.99,
        "img": "https://www.rockauto.com/info/1161/T2_GM2502238_Fro.jpg",
        "description": "High output LED bulbs with cooling fan and weather sealed design.",
    },
]


def init_products_table():
    """Create products table if needed and seed with default parts."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            fitment TEXT,
            price REAL NOT NULL,
            img TEXT,
            description TEXT
        );
        """
    )
    conn.commit()

    # If empty, seed with our default products
    cur.execute("SELECT COUNT(*) AS c FROM products;")
    count = cur.fetchone()["c"]
    if count == 0:
        for p in SEED_PRODUCTS:
            cur.execute(
                """
                INSERT INTO products (id, name, category, fitment, price, img, description)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    p["id"],
                    p["name"],
                    p["category"],
                    p["fitment"],
                    p["price"],
                    p["img"],
                    p["description"],
                ),
        )
        conn.commit()

    conn.close()


def init_orders_table():
    """Create orders table to persist orders instead of in-memory."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            created_at TEXT NOT NULL,
            total REAL NOT NULL,
            card_brand TEXT,
            card_last4 TEXT,
            stripe_pid TEXT,
            shipping_name TEXT,
            shipping_line1 TEXT,
            shipping_line2 TEXT,
            shipping_city TEXT,
            shipping_state TEXT,
            shipping_zip TEXT
        );
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id TEXT NOT NULL,
            name TEXT NOT NULL,
            qty INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            line_total REAL NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        );
        """
    )

    # Add missing columns on older DBs
    cur.execute("PRAGMA table_info(orders);")
    cols = {row["name"] for row in cur.fetchall()}
    for col, col_type in [
        ("card_brand", "TEXT"),
        ("card_last4", "TEXT"),
        ("stripe_pid", "TEXT"),
        ("shipping_name", "TEXT"),
        ("shipping_line1", "TEXT"),
        ("shipping_line2", "TEXT"),
        ("shipping_city", "TEXT"),
        ("shipping_state", "TEXT"),
        ("shipping_zip", "TEXT"),
    ]:
        if col not in cols:
            cur.execute(f"ALTER TABLE orders ADD COLUMN {col} {col_type};")

    conn.commit()
    conn.close()

def init_users_table():
    """Create users table for authentication if it doesn't exist."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            card_brand TEXT,
            card_last4 TEXT,
            card_exp TEXT,
            preferred_vehicle TEXT,
            ship_name TEXT,
            ship_line1 TEXT,
            ship_line2 TEXT,
            ship_city TEXT,
            ship_state TEXT,
            ship_zip TEXT,
            reset_token TEXT,
            reset_token_expires TEXT
        );
        """
    )
    # add newer columns if an older DB exists
    cur.execute("PRAGMA table_info(users);")
    cols = {row["name"] for row in cur.fetchall()}
    for col, col_type in [
        ("display_name", "TEXT"),
        ("card_brand", "TEXT"),
        ("card_last4", "TEXT"),
        ("card_exp", "TEXT"),
        ("preferred_vehicle", "TEXT"),
        ("ship_name", "TEXT"),
        ("ship_line1", "TEXT"),
        ("ship_line2", "TEXT"),
        ("ship_city", "TEXT"),
        ("ship_state", "TEXT"),
        ("ship_zip", "TEXT"),
        ("reset_token", "TEXT"),
        ("reset_token_expires", "TEXT"),
    ]:
        if col not in cols:
            cur.execute(f"ALTER TABLE users ADD COLUMN {col} {col_type};")

    conn.commit()
    conn.close()


# -------------------------------------------------
# Helpers to read products from DB
# -------------------------------------------------
def get_all_products():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, category, fitment, price, img, description FROM products"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_product_by_id(pid: str):
    conn = get_db()
    row = conn.execute(
        "SELECT id, name, category, fitment, price, img, description FROM products WHERE id = ?",
        (pid,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# -------------------------------------------------
# In-memory cart store (orders are persisted)
# -------------------------------------------------
cart_db = {}        # {username: [product_id, product_id, ...]}

# Load environment variables from .env if present (explicit path to project root)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# -------------------------------------------------
# Flask app setup
# -------------------------------------------------
app = Flask(__name__)
app.secret_key = "valleyautoparts_secret_key"
app.permanent_session_lifetime = timedelta(days=1)
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
if stripe and STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY

# Initialize tables on startup
init_products_table()
init_users_table()
init_orders_table()


@app.context_processor
def inject_user_profile():
    """Expose basic user profile data to all templates for nav display."""
    uname = current_user()
    profile = get_user(uname) if uname else None
    display = None
    if profile:
        display = profile.get("display_name") or uname
    return {
        "nav_display_name": display or uname,
        "nav_profile": profile,
    }

# -------------------------------------------------
# Auth helpers
# -------------------------------------------------
def logged_in():
    return "username" in session


def current_user():
    return session.get("username")


def get_user(username):
    conn = get_db()
    row = conn.execute(
        """
        SELECT username, email, display_name, card_brand, card_last4, card_exp, preferred_vehicle,
               ship_name, ship_line1, ship_line2, ship_city, ship_state, ship_zip,
               reset_token, reset_token_expires
        FROM users
        WHERE username = ?
        """,
        (username,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_user_profile(
    username,
    email,
    display_name,
    card_brand,
    card_last4,
    card_exp,
    preferred_vehicle,
    ship_info=None,
):
    conn = get_db()
    cur = conn.cursor()
    ship_info = ship_info or {}
    cur.execute(
        """
        UPDATE users
        SET email = ?, display_name = ?, card_brand = ?, card_last4 = ?, card_exp = ?, preferred_vehicle = ?,
            ship_name = ?, ship_line1 = ?, ship_line2 = ?, ship_city = ?, ship_state = ?, ship_zip = ?
        WHERE username = ?
        """,
        (
            email,
            display_name,
            card_brand,
            card_last4,
            card_exp,
            preferred_vehicle,
            ship_info.get("name"),
            ship_info.get("line1"),
            ship_info.get("line2"),
            ship_info.get("city"),
            ship_info.get("state"),
            ship_info.get("zip"),
            username,
        ),
    )
    conn.commit()
    conn.close()


def find_user_by_email(email):
    conn = get_db()
    row = conn.execute(
        """
        SELECT username, email, reset_token, reset_token_expires
        FROM users WHERE email = ?
        """,
        (email,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def set_reset_token(email):
    user = find_user_by_email(email)
    if not user:
        return None
    token = secrets.token_urlsafe(24)
    expires = (datetime.utcnow() + timedelta(hours=1)).isoformat()
    conn = get_db()
    conn.execute(
        "UPDATE users SET reset_token = ?, reset_token_expires = ? WHERE email = ?",
        (token, expires, email),
    )
    conn.commit()
    conn.close()
    return token


def validate_reset_token(token):
    if not token:
        return None
    conn = get_db()
    row = conn.execute(
        """
        SELECT username, reset_token_expires
        FROM users
        WHERE reset_token = ?
        """,
        (token,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    expires = row["reset_token_expires"]
    try:
        exp_dt = datetime.fromisoformat(expires)
    except Exception:
        return None
    if datetime.utcnow() > exp_dt:
        return None
    return row["username"]


def clear_reset_token(username):
    conn = get_db()
    conn.execute(
        "UPDATE users SET reset_token = NULL, reset_token_expires = NULL WHERE username = ?",
        (username,),
    )
    conn.commit()
    conn.close()


def user_cart(username):
    """Return the cart list for a user (list of product IDs)."""
    return cart_db.setdefault(username, [])


def add_item_to_cart(username: str, pid: str):
    """Add one product ID to the user's cart if the product exists."""
    if not get_product_by_id(pid):
        return False
    user_cart(username).append(pid)
    return True


def remove_item_from_cart(username: str, pid: str):
    """Remove all instances of a product ID from the user's cart."""
    cart = user_cart(username)
    if not cart:
        return False
    new_cart = [item for item in cart if item != pid]
    cart_db[username] = new_cart
    return len(new_cart) != len(cart)


def build_order_lines(item_ids):
    """Return (items, total) for given product IDs."""
    counts = Counter(item_ids)
    order_items = []
    total = 0.0

    for pid, qty in counts.items():
        part = get_product_by_id(pid)
        if not part:
            continue

        line_total = part["price"] * qty
        total += line_total
        order_items.append(
            {
                "id": pid,
                "name": part["name"],
                "qty": qty,
                "unit_price": round(part["price"], 2),
                "line_total": round(line_total, 2),
            }
        )

    if not order_items:
        return [], 0.0

    return order_items, round(total, 2)


def create_order(username: str, item_ids, shipping=None, card_info=None, stripe_pid=None):
    """Persist an order to the database and return the created order dict."""
    order_items, total = build_order_lines(item_ids)
    if not order_items:
        return None

    shipping = shipping or {}
    card_info = card_info or {}
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO orders (
            username, created_at, total,
            card_brand, card_last4, stripe_pid,
            shipping_name, shipping_line1, shipping_line2,
            shipping_city, shipping_state, shipping_zip
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            username,
            created_at,
            total,
            card_info.get("brand"),
            card_info.get("last4"),
            stripe_pid,
            shipping.get("name"),
            shipping.get("line1"),
            shipping.get("line2"),
            shipping.get("city"),
            shipping.get("state"),
            shipping.get("zip"),
        ),
    )
    order_id = cur.lastrowid

    for item in order_items:
        cur.execute(
            """
            INSERT INTO order_items (order_id, product_id, name, qty, unit_price, line_total)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                order_id,
                item["id"],
                item["name"],
                item["qty"],
                item["unit_price"],
                item["line_total"],
            ),
        )

    conn.commit()
    conn.close()

    return {
        "order_id": order_id,
        "created_at": created_at,
        "items": order_items,
        "total": total,
        "card_brand": card_info.get("brand"),
        "card_last4": card_info.get("last4"),
        "stripe_pid": stripe_pid,
        "shipping": {
            "name": shipping.get("name"),
            "line1": shipping.get("line1"),
            "line2": shipping.get("line2"),
            "city": shipping.get("city"),
            "state": shipping.get("state"),
            "zip": shipping.get("zip"),
        },
    }

def stripe_enabled():
    return bool(stripe and STRIPE_SECRET_KEY)


def create_stripe_payment_intent(amount_cents, shipping, username):
    """Create a Stripe PaymentIntent using a test payment method."""
    if not stripe_enabled():
        return (None, None)
    try:
        intent = stripe.PaymentIntent.create(
            amount=int(amount_cents),
            currency="usd",
            description=f"Order for {username}",
            payment_method="pm_card_visa",  # Stripe test payment method
            confirm=True,
            shipping={
                "name": shipping.get("name") or username,
                "address": {
                    "line1": shipping.get("line1") or "123 Test St",
                    "line2": shipping.get("line2") or "",
                    "city": shipping.get("city") or "Test City",
                    "state": shipping.get("state") or "CA",
                    "postal_code": shipping.get("zip") or "00000",
                    "country": "US",
                },
            },
        )
        return (intent["id"], None)
    except Exception as e:
        return (None, str(e))


def create_stripe_checkout_session(username, item_ids, shipping):
    """Create a Stripe Checkout Session to show hosted payment page."""
    if not stripe_enabled():
        return (None, "Stripe not configured")

    order_items, total = build_order_lines(item_ids)
    if not order_items:
        return (None, "Cart is empty")

    line_items = []
    for item in order_items:
        line_items.append(
            {
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": item["name"]},
                    "unit_amount": int(item["unit_price"] * 100),
                },
                "quantity": item["qty"],
            }
        )

    try:
        session_obj = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=line_items,
            success_url=url_for("payment_success", _external=True, _scheme="http") + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=url_for("payment", _external=True, _scheme="http"),
            shipping_address_collection={"allowed_countries": ["US"]},
            metadata={
                "username": username,
                "cart_items": ",".join(item_ids),
            },
        )
        return (session_obj.url, None)
    except Exception as e:
        return (None, str(e))


def fetch_orders(username: str):
    """Return all orders (with items) for a user, newest first."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, created_at, total, card_brand, card_last4, stripe_pid,
               shipping_name, shipping_line1, shipping_line2,
               shipping_city, shipping_state, shipping_zip
        FROM orders
        WHERE username = ?
        ORDER BY id DESC
        """,
        (username,),
    )
    orders = cur.fetchall()

    results = []
    for order in orders:
        cur.execute(
            """
            SELECT product_id, name, qty, unit_price, line_total
            FROM order_items
            WHERE order_id = ?
            """,
            (order["id"],),
        )
        items = [
            {
                "id": row["product_id"],
                "name": row["name"],
                "qty": row["qty"],
                "unit_price": row["unit_price"],
                "line_total": row["line_total"],
            }
            for row in cur.fetchall()
        ]
        results.append(
            {
                "order_id": order["id"],
                "created_at": order["created_at"],
                "items": items,
                "total": order["total"],
                "card_brand": order["card_brand"],
                "card_last4": order["card_last4"],
                "stripe_pid": order["stripe_pid"],
                "shipping": {
                    "name": order["shipping_name"],
                    "line1": order["shipping_line1"],
                    "line2": order["shipping_line2"],
                    "city": order["shipping_city"],
                    "state": order["shipping_state"],
                    "zip": order["shipping_zip"],
                },
            }
        )

    conn.close()
    return results


def register_user(username, email, password):
    """Insert a new user with a hashed password into the users table."""
    password_hash = generate_password_hash(password)
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (username, email, password_hash, display_name, card_exp, preferred_vehicle)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (username, email, password_hash, username, None, None),
        )
        conn.commit()
        conn.close()
        return (True, "Account created successfully.")
    except sqlite3.IntegrityError:
        # Username must be unique
        return (False, "Username already exists.")


def authenticate(username, password):
    """Check username + password against stored hash."""
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

    return check_password_hash(row["password_hash"], password)


# -------------------------------------------------
# Routes
# -------------------------------------------------
@app.route("/")
def shop():
    """Main shop page, rendered on the server (no JS DOM building)."""
    banner = session.pop("flash_msg", None)
    query = request.args.get("q", "").strip()
    vehicle = request.args.get("vehicle", "").strip()

    # default to preferred vehicle if none selected
    if logged_in() and not vehicle:
        profile = get_user(current_user())
        if profile and profile.get("preferred_vehicle"):
            vehicle = profile["preferred_vehicle"]

    # Filter products server-side so the template can render directly
    parts = []
    for p in get_all_products():
        name = (p.get("name") or "").lower()
        category = (p.get("category") or "").lower()
        fitment = (p.get("fitment") or "").lower()
        q = query.lower()
        v = vehicle.lower()

        matches_text = not q or q in name or q in category or q in fitment
        matches_vehicle = not v or v in fitment

        if matches_text and matches_vehicle:
            parts.append(p)

    return render_template(
        "shop.html",
        parts=parts,
        logged_in=logged_in(),
        username=current_user(),
        query=query,
        vehicle=vehicle,
        vehicle_options=VEHICLE_OPTIONS,
        banner=banner,
    )


@app.route("/product/<pid>")
def product_detail(pid):
    part = get_product_by_id(pid)
    if not part:
        return redirect(url_for("shop"))
    banner = session.pop("flash_msg", None)
    return render_template(
        "product.html",
        part=part,
        logged_in=logged_in(),
        username=current_user(),
        banner=banner,
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
        else:
            msg = "Invalid username or password."
    return render_template("login.html", msg=msg, ok=ok)


@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("shop"))


@app.route("/reset", methods=["GET", "POST"])
def reset_request():
    msg, token = None, None
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if not email:
            msg = "Enter the email on your account."
        else:
            token = set_reset_token(email)
            if token:
                msg = "Reset link generated. Use the link below to set a new password."
            else:
                msg = "No account found with that email."
    return render_template("reset_request.html", msg=msg, token=token)


@app.route("/reset/<token>", methods=["GET", "POST"])
def reset_form(token):
    username = validate_reset_token(token)
    if not username:
        return render_template("reset_form.html", invalid=True, token=token)

    msg, ok = None, False
    if request.method == "POST":
        new_pw = request.form.get("password", "")
        if len(new_pw) < 6:
            msg = "Password must be at least 6 characters."
        else:
            pw_hash = generate_password_hash(new_pw)
            conn = get_db()
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE username = ?",
                (pw_hash, username),
            )
            conn.commit()
            conn.close()
            clear_reset_token(username)
            msg = "Password updated. You can now log in."
            ok = True
    return render_template("reset_form.html", invalid=False, token=token, msg=msg, ok=ok)


@app.route("/profile", methods=["GET", "POST"])
def profile():
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))

    user = get_user(username)
    if not user:
        session.pop("username", None)
        session["flash_msg"] = "Please log in again."
        return redirect(url_for("login"))

    msg, ok = None, False

    display_name = user.get("display_name") or username
    email = user.get("email") or ""
    card_brand = user.get("card_brand") or ""
    card_last4 = user.get("card_last4") or ""
    card_exp = user.get("card_exp") or ""
    preferred_vehicle = user.get("preferred_vehicle") or ""
    ship_name = user.get("ship_name") or ""
    ship_line1 = user.get("ship_line1") or ""
    ship_line2 = user.get("ship_line2") or ""
    ship_city = user.get("ship_city") or ""
    ship_state = user.get("ship_state") or ""
    ship_zip = user.get("ship_zip") or ""

    if request.method == "POST":
        display_name = request.form.get("display_name", "").strip() or username
        email = request.form.get("email", "").strip() or email
        card_brand = request.form.get("card_brand", "").strip()
        card_last4 = request.form.get("card_last4", "").strip()
        card_exp = request.form.get("card_exp", "").strip()
        preferred_vehicle = request.form.get("preferred_vehicle", "").strip()
        ship_name = request.form.get("ship_name", "").strip()
        ship_line1 = request.form.get("ship_line1", "").strip()
        ship_line2 = request.form.get("ship_line2", "").strip()
        ship_city = request.form.get("ship_city", "").strip()
        ship_state = request.form.get("ship_state", "").strip()
        ship_zip = request.form.get("ship_zip", "").strip()

        if not email:
            msg = "Email is required."
        elif card_last4 and (not card_last4.isdigit() or len(card_last4) != 4):
            msg = "Card last 4 must be 4 digits."
        else:
            update_user_profile(
                username,
                email,
                display_name,
                card_brand or None,
                card_last4 or None,
                card_exp or None,
                preferred_vehicle or None,
                {
                    "name": ship_name or None,
                    "line1": ship_line1 or None,
                    "line2": ship_line2 or None,
                    "city": ship_city or None,
                    "state": ship_state or None,
                    "zip": ship_zip or None,
                },
            )
            user = get_user(username)
            msg = "Profile updated."
            ok = True
        # reflect entered values even if validation fails
        user = user or {}
        user.update(
            {
                "display_name": display_name,
                "email": email,
                "card_brand": card_brand,
                "card_last4": card_last4,
                "card_exp": card_exp,
                "preferred_vehicle": preferred_vehicle,
                "ship_name": ship_name,
                "ship_line1": ship_line1,
                "ship_line2": ship_line2,
                "ship_city": ship_city,
                "ship_state": ship_state,
                "ship_zip": ship_zip,
            }
        )

    return render_template(
        "profile.html",
        logged_in=True,
        username=username,
        user=user,
        msg=msg,
        ok=ok,
        vehicle_options=VEHICLE_OPTIONS,
    )


@app.route("/cart")
def cart():
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))

    items = []
    total = 0.0
    counts = Counter(user_cart(username))

    for pid, qty in counts.items():
        part = get_product_by_id(pid)
        if not part:
            continue
        line_total = round(part["price"] * qty, 2)
        total += line_total
        items.append(
            {
                "id": pid,
                "name": part["name"],
                "fitment": part.get("fitment", ""),
                "qty": qty,
                "unit_price": round(part["price"], 2),
                "line_total": line_total,
            }
        )

    banner = session.pop("cart_flash", None)

    return render_template(
        "cart.html",
        logged_in=True,
        username=username,
        items=items,
        total=round(total, 2),
        item_count=sum(counts.values()),
        banner=banner,
    )


@app.route("/orders")
def orders():
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))

    user_orders = fetch_orders(username)
    banner = session.pop("order_flash", None)
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

    counts = Counter(user_cart(username))
    items = []
    total = 0.0
    for pid, qty in counts.items():
        part = get_product_by_id(pid)
        if not part:
            continue
        line_total = round(part["price"] * qty, 2)
        total += line_total
        items.append(
            {
                "id": pid,
                "name": part["name"],
                "fitment": part.get("fitment", ""),
                "qty": qty,
                "unit_price": round(part["price"], 2),
                "line_total": line_total,
            }
        )

    if not items:
        session["cart_flash"] = "Your cart is empty. Add items before paying."
        return redirect(url_for("cart"))

    user = get_user(username)

    return render_template(
        "payment.html",
        logged_in=True,
        username=username,
        items=items,
        total=round(total, 2),
        user=user,
        stripe_on=stripe_enabled(),
    )


@app.route("/payment", methods=["POST"])
def payment_submit():
    # Legacy endpoint now delegates to Stripe Checkout-only flow
    return payment_checkout()


@app.route("/payment/success")
def payment_success():
    username = session.get("username")
    session_id = request.args.get("session_id")
    if not username or not session_id or not stripe_enabled():
        return redirect(url_for("orders"))

    try:
        checkout_session = stripe.checkout.Session.retrieve(session_id)
        payment_intent_id = checkout_session.get("payment_intent")
        cart_items_meta = checkout_session.get("metadata", {}).get("cart_items", "")
        cart_items = [pid for pid in cart_items_meta.split(",") if pid]

        brand = None
        last4 = None
        if payment_intent_id:
            pi = stripe.PaymentIntent.retrieve(payment_intent_id)
            if pi.charges and pi.charges.data:
                charge = pi.charges.data[0]
                pm_details = charge.get("payment_method_details", {}).get("card", {})
                brand = pm_details.get("brand")
                last4 = pm_details.get("last4")
        shipping_details = checkout_session.get("shipping") or {}
        ship_addr = (shipping_details.get("address") or {})

        if cart_items:
            order = create_order(
                username,
                cart_items,
                shipping={
                    "name": shipping_details.get("name"),
                    "line1": ship_addr.get("line1"),
                    "line2": ship_addr.get("line2"),
                    "city": ship_addr.get("city"),
                    "state": ship_addr.get("state"),
                    "zip": ship_addr.get("postal_code"),
                },
                card_info={
                    "brand": brand,
                    "last4": last4,
                },
                stripe_pid=checkout_session.get("payment_intent"),
            )
            if order:
                cart_db[username] = []  # clear cart
                session["order_flash"] = f"Order #{order['order_id']} placed successfully."
    except Exception:
        return redirect(url_for("orders"))

    return render_template(
        "payment_success.html",
        logged_in=True,
        username=username,
    )


@app.route("/payment/checkout", methods=["POST"])
def payment_checkout():
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))

    cart_items = list(user_cart(username))
    if not cart_items:
        session["cart_flash"] = "Your cart is empty. Add items before paying."
        return redirect(url_for("cart"))

    # Shipping info (required for checkout session)
    ship_name = request.form.get("ship_name", "").strip()
    ship_line1 = request.form.get("ship_line1", "").strip()
    ship_line2 = request.form.get("ship_line2", "").strip()
    ship_city = request.form.get("ship_city", "").strip()
    ship_state = request.form.get("ship_state", "").strip()
    ship_zip = request.form.get("ship_zip", "").strip()

    if not stripe_enabled():
        session["cart_flash"] = "Stripe is not configured."
        return redirect(url_for("payment"))

    if not (ship_name and ship_line1 and ship_city and ship_state and ship_zip):
        session["cart_flash"] = "Please provide a full shipping address."
        return redirect(url_for("payment"))

    checkout_url, err = create_stripe_checkout_session(
        username,
        cart_items,
        {
            "name": ship_name,
            "line1": ship_line1,
            "line2": ship_line2,
            "city": ship_city,
            "state": ship_state,
            "zip": ship_zip,
        },
    )
    if err or not checkout_url:
        session["cart_flash"] = "Stripe checkout failed: " + str(err)
        return redirect(url_for("payment"))

    session["pending_cart_items"] = cart_items
    return redirect(checkout_url, code=303)


@app.route("/cart/add", methods=["POST"])
def cart_add():
    username = session.get("username")
    if not username:
        session["flash_msg"] = "Please log in to add items to your cart."
        return redirect(url_for("login"))

    pid = request.form.get("pid", "").strip()
    if not pid or not add_item_to_cart(username, pid):
        session["flash_msg"] = "Unable to add that item. Please try again."
    else:
        session["flash_msg"] = "Item added to your cart."
    return redirect(request.referrer or url_for("shop"))


@app.route("/cart/remove", methods=["POST"])
def cart_remove():
    username = session.get("username")
    if not username:
        session["flash_msg"] = "Please log in to manage your cart."
        return redirect(url_for("login"))

    pid = request.form.get("pid", "").strip()
    if pid and remove_item_from_cart(username, pid):
        session["cart_flash"] = "Item removed from your cart."
    else:
        session["cart_flash"] = "Could not remove that item."
    return redirect(url_for("cart"))


@app.route("/cart/clear", methods=["POST"])
def cart_clear():
    username = session.get("username")
    if not username:
        return redirect(url_for("login"))
    cart_db[username] = []
    session["cart_flash"] = "Cart cleared."
    return redirect(url_for("cart"))


# -------------------------------------------------
# JSON APIs
# -------------------------------------------------
@app.route("/api/session")
def api_session():
    return jsonify({"logged_in": logged_in(), "username": current_user()})


@app.route("/api/products")
def api_products():
    return jsonify(get_all_products())


@app.route("/api/parts")
def api_parts():
    # duplicate endpoint name for compatibility with earlier JS
    return jsonify(get_all_products())


@app.route("/api/orders", methods=["GET", "POST"])
def api_orders():
    username = session.get("username")
    if not username:
        return jsonify({"error": "not_logged_in"}), 401

    # GET: return JSON list of this user's orders
    if request.method == "GET":
        return jsonify(fetch_orders(username))

    # POST: create a new order from a list of product IDs
    data = request.get_json() or {}
    item_ids = data.get("items", [])
    if not item_ids:
        return jsonify({"error": "empty_cart"}), 400

    order = create_order(username, item_ids)
    if not order:
        return jsonify({"error": "invalid_items"}), 400

    # one-time success message for /orders page
    session["order_flash"] = f"Order #{order['order_id']} placed successfully."

    return jsonify({"ok": True, "order": order})


# -------------------------------------------------
# Main
# -------------------------------------------------
if __name__ == "__main__":
    # Tables already initialized above, but safe to call again if needed
    init_products_table()
    init_users_table()
    app.run(host="0.0.0.0", port=5000, debug=True)
