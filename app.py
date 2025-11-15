from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "valleyautoparts_secret_key"
app.permanent_session_lifetime = timedelta(days=1)


# Temporary DB for users
users_db = {}

# Temporary DB for parts on main page
parts_db = [
    {
        "id": "brakepads-ceramic-front",
        "name": "Ceramic Brake Pads (Front Axle)",
        "category": "Brakes",
        "fitment": "Fits: Honda Civic, Toyota Corolla, Hyundai Elantra",
        "price": 54.99,
        "img": "https://via.placeholder.com/400x400?text=Ceramic+Brake+Pads",
        "description": "Low dust ceramic pads for quieter braking and longer rotor life."
    },
    {
        "id": "serpentine-belt-6pk",
        "name": "Serpentine Drive Belt 6PK",
        "category": "Belts",
        "fitment": "Fits: 1.8L–2.4L inline-4 engines",
        "price": 24.50,
        "img": "https://via.placeholder.com/400x400?text=Serpentine+Belt",
        "description": "High temp EPDM replacement belt for alternator, A/C, and power steering."
    },
    {
        "id": "alternator-110amp",
        "name": "110A Alternator",
        "category": "Electrical",
        "fitment": "Remanufactured for common 4-cyl/6-cyl models",
        "price": 129.99,
        "img": "https://via.placeholder.com/400x400?text=Alternator+110A",
        "description": "OEM output with internal voltage regulator. Core charge may apply."
    },
    {
        "id": "oil-filter-synthetic",
        "name": "High-Mileage Oil Filter",
        "category": "Filters",
        "fitment": "Universal fit for most spin-on adapters",
        "price": 9.99,
        "img": "https://via.placeholder.com/400x400?text=Oil+Filter",
        "description": "Synthetic media filter rated for 10,000 mile protection."
    },
    {
        "id": "full-synthetic-5w30",
        "name": "5W-30 Full Synthetic Motor Oil (1 Qt)",
        "category": "Fluids",
        "fitment": "Dexos / API SN+ compatible",
        "price": 8.99,
        "img": "https://via.placeholder.com/400x400?text=5W-30+Oil",
        "description": "Protects against sludge and thermal breakdown in all conditions."
    },
    {
        "id": "spark-plug-iridium",
        "name": "Iridium Spark Plug",
        "category": "Ignition",
        "fitment": "Fits: Various 4-cyl/6-cyl applications",
        "price": 11.49,
        "img": "https://via.placeholder.com/400x400?text=Spark+Plug",
        "description": "Iridium tip for long life and improved ignition efficiency."
    },
    {
        "id": "cv-axle-front-left",
        "name": "Front Left CV Axle Shaft",
        "category": "Drivetrain",
        "fitment": "Includes boot, grease, and clips — ready to install",
        "price": 89.99,
        "img": "https://via.placeholder.com/400x400?text=CV+Axle",
        "description": "Remanufactured OE replacement half shaft with new joints."
    },
    {
        "id": "rear-shock-absorber",
        "name": "Rear Shock Absorber",
        "category": "Suspension",
        "fitment": "Gas-charged twin-tube design",
        "price": 49.99,
        "img": "https://via.placeholder.com/400x400?text=Rear+Shock",
        "description": "Restores ride comfort and stability on rough or uneven roads."
    },
    {
        "id": "cabin-air-filter-charcoal",
        "name": "Charcoal Cabin Air Filter",
        "category": "Filters",
        "fitment": "Traps dust, pollen, and odor particles",
        "price": 15.99,
        "img": "https://via.placeholder.com/400x400?text=Cabin+Filter",
        "description": "Activated carbon filter for improved HVAC air quality."
    },
    {
        "id": "led-headlight-h11",
        "name": "LED Headlight Kit (H11 6000K)",
        "category": "Lighting",
        "fitment": "Plug-and-play for H11 sockets",
        "price": 59.99,
        "img": "https://via.placeholder.com/400x400?text=LED+Headlight",
        "description": "High output LED bulbs with cooling fan and weather sealed design."
    }
]

def logged_in():
    return "username" in session

def current_user():
    return session.get("username")

def register_user(username, email, password):
    if username in users_db:
        return (False, "Username already exists.")
    users_db[username] = {"email": email, "password": password}
    return (True, "Account created successfully.")

def authenticate(username, password):
    user = users_db.get(username)
    return user and user["password"] == password

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
    app.run(host="0.0.0.0", port=5000, debug=True)
