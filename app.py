from flask import Flask, render_template, request, redirect, session, g
import sqlite3
import random
import string
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "zero_hunger_secret_2024"
DATABASE = "database.db"

# Database Helper Functions
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row  # Allows accessing columns by name
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        cur = db.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                name TEXT
            )""")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS donations(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                food TEXT, quantity TEXT, location TEXT, 
                time TEXT, quality TEXT, status TEXT, donor_id INTEGER,
                FOREIGN KEY(donor_id) REFERENCES users(id)
            )""")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS coupons(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE, value INTEGER, user_id INTEGER,
                donation_id INTEGER, status TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(donation_id) REFERENCES donations(id)
            )""")
        db.commit()

init_db()

# Routes
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        name = request.form.get("name")

        if not username or not password:
            return render_template("signup.html", error="Fields cannot be empty")

        hashed_pw = generate_password_hash(password)
        db = get_db()
        try:
            db.execute("INSERT INTO users(username, password, name) VALUES(?,?,?)", 
                       (username, hashed_pw, name))
            db.commit()
            return redirect("/login")
        except sqlite3.IntegrityError:
            return render_template("signup.html", error="Username already exists")
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["name"] = user["name"]
            return redirect("/donate")
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/donate", methods=["GET", "POST"])
def donate():
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        food = request.form.get("food")
        quality = request.form.get("quality", "Average")
        
        db = get_db()
        cur = db.cursor()
        cur.execute(
            "INSERT INTO donations(food, quantity, location, time, quality, status, donor_id) VALUES(?,?,?,?,?,?,?)",
            (food, request.form.get("quantity"), request.form.get("location"), 
             request.form.get("time"), quality, "Available", session["user_id"])
        )
        donation_id = cur.lastrowid

        # Logic for coupon values
        values = {"Best": 100, "Good": 50, "Average": 25}
        coupon_value = values.get(quality, 10)
        coupon_code = "ZH" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        cur.execute(
            "INSERT INTO coupons(code, value, user_id, donation_id, status) VALUES(?,?,?,?,?)",
            (coupon_code, coupon_value, session["user_id"], donation_id, "Active")
        )
        db.commit()
        return redirect("/success")

    return render_template("donate.html", name=session.get("name"))

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")
if __name__=="__main__":
    app.run(debug=True)

