from flask import Flask, render_template, request, redirect, session, jsonify, flash
import pickle
import sqlite3
import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEY")

if not API_KEY:
    raise ValueError("API_KEY not found. Check your.env file")
app = Flask(__name__)
app.secret_key = "secret123"

DB_NAME = "database.db"

# ---------------- DATABASE ----------------
def get_db():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )
    """)

    # Predictions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        city TEXT,
        temp REAL,
        humidity REAL,
        aqi REAL,
        rain REAL,
        pop REAL,
        risk TEXT,
        category TEXT
    )
    """)

    # Default user
    cursor.execute("SELECT * FROM users WHERE username=?", ("admin",))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users(username, password) VALUES(?, ?)",
            ("admin", "admin")
        )

    conn.commit()
    conn.close()

init_db()

# ---------------- LOAD MODEL ----------------
model = pickle.load(open("disease_model.pkl", "rb"))

# ---------------- API ----------------
def get_live_data(city):

    weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    weather_res = requests.get(weather_url).json()

    if "main" not in weather_res:
        return 0,0,0

    temp = weather_res["main"]["temp"]
    humidity = weather_res["main"]["humidity"]

    lat = weather_res["coord"]["lat"]
    lon = weather_res["coord"]["lon"]

    aqi_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
    aqi_res = requests.get(aqi_url).json()

    aqi = aqi_res["list"][0]["main"]["aqi"]

    return temp, humidity, aqi

# ---------------- PRECAUTIONS ----------------
def get_precautions(risk):
    if risk == "High":
        return ["Avoid polluted areas", "Use protection", "Maintain hygiene"]
    elif risk == "Medium":
        return ["Stay cautious", "Maintain cleanliness"]
    else:
        return ["Maintain basic hygiene"]

# ---------------- URBAN RISK ----------------
def get_urban_risk(temp, humidity, aqi, rain, pop, category):
    if category == "Skin Disease":
        return ("Slum Areas", "High humidity causes infections") if humidity > 70 else ("Residential Areas", "Normal conditions")
    elif category == "Water-Borne Disease":
        return ("Flood Areas", "Water contamination") if rain > 50 else ("Sanitation Areas", "Unsafe water")
    elif category == "Air-Borne Disease":
        return ("Traffic Zones", "High AQI") if aqi > 3 else ("Urban Areas", "Moderate AQI")
    elif category == "Insect-Borne Disease":
        return ("Stagnant Water Areas", "Mosquito breeding") if rain > 20 else ("Green Areas", "Insects present")
    else:
        return ("Mixed Urban Area", "General risk")

# ---------------- SAVE ----------------
def save_prediction(city, temp, humidity, aqi, rain, pop, risk, category):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO predictions (city, temp, humidity, aqi, rain, pop, risk, category)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (city, temp, humidity, aqi, rain, pop, risk, category))

    conn.commit()
    conn.close()

# ---------------- HOME ----------------
@app.route('/')
def home():
    if 'user' not in session:
        return redirect('/login')
    return render_template("index.html")

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        conn = get_db()
        cursor = conn.cursor()

        username = request.form['username']
        password = request.form['password']

        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()

        conn.close()

        if user:
            session['user'] = username
            return redirect('/')
        else:
            return "Invalid login"

    return render_template("login.html")

# ---------------- SIGNUP ----------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        conn = get_db()
        cursor = conn.cursor()

        username = request.form['username']
        password = request.form['password']

        cursor.execute("INSERT INTO users(username,password) VALUES(?,?)", (username, password))
        conn.commit()
        conn.close()
        flash("Signup successful! Please login.")

        return redirect('/login')

    return render_template("signup.html")

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

# ---------------- GENERAL ----------------
@app.route('/predict', methods=['POST'])
def predict():
    city = request.form['city']
    temp, humidity, aqi = get_live_data(city)

    rain, pop = 0, 0

    risk = model.predict([[temp, humidity, aqi, rain, pop]])[0]
    advice = get_precautions(risk)

    save_prediction(city, temp, humidity, aqi, rain, pop, risk, "General Disease")

    area, reason = get_urban_risk(temp, humidity, aqi, rain, pop, "General Disease")

    return render_template("result.html", city=city, temp=temp, humidity=humidity,
                           aqi=aqi, rain=rain, pop=pop, prediction=risk,
                           advice=advice, category="General Disease",
                           area=area, reason=reason)

@app.route('/predict/skin', methods=['GET', 'POST'])
def predict_skin():

    if request.method == 'POST':
        city = request.form['city']
        temp, humidity, aqi = get_live_data(city)

        risk = model.predict([[temp, humidity, aqi, 0, 0]])[0]
        advice = get_precautions(risk)

        save_prediction(city, temp, humidity, aqi, 0, 0, risk, "Skin Disease")

        area, reason = get_urban_risk(temp, humidity, aqi, 0, 0, "Skin Disease")

        return render_template(
            "result.html",
            city=city,
            temp=temp,
            humidity=humidity,
            aqi=aqi,
            rain=0,
            pop=0,
            prediction=risk,
            advice=advice,
            category="Skin Disease",
            area=area,
            reason=reason
        )
    return render_template("skin.html")

@app.route('/predict/water', methods=['GET', 'POST'])
def predict_water():

    if request.method == 'POST':
        city = request.form['city']
        temp, humidity, aqi = get_live_data(city)

        rain = 10
        pop = 1000

        risk = model.predict([[temp, humidity, aqi, rain, pop]])[0]
        advice = get_precautions(risk)

        save_prediction(city, temp, humidity, aqi, rain, pop, risk, "Water-Borne Disease")

        area, reason = get_urban_risk(temp, humidity, aqi, rain, pop, "Water-Borne Disease")

        return render_template(
            "result.html",
            city=city,
            temp=temp,
            humidity=humidity,
            aqi=aqi,
            rain=rain,
            pop=pop,
            prediction=risk,
            advice=advice,
            category="Water-Borne Disease",
            area=area,
            reason=reason
        )

    return render_template("water.html")

@app.route('/predict/air', methods=['GET', 'POST'])
def predict_air():

    if request.method == 'POST':
        city = request.form['city']
        temp, humidity, aqi = get_live_data(city)

        risk = model.predict([[temp, humidity, aqi, 0, 0]])[0]
        advice = get_precautions(risk)

        save_prediction(city, temp, humidity, aqi, 0, 0, risk, "Air-Borne Disease")

        area, reason = get_urban_risk(temp, humidity, aqi, 0, 0, "Air-Borne Disease")

        return render_template(
            "result.html",
            city=city,
            temp=temp,
            humidity=humidity,
            aqi=aqi,
            rain=0,
            pop=0,
            prediction=risk,
            advice=advice,
            category="Air-Borne Disease",
            area=area,
            reason=reason
        )

    return render_template("air.html")

@app.route('/predict/insect', methods=['GET', 'POST'])
def predict_insect():

    if request.method == 'POST':
        city = request.form['city']
        temp, humidity, aqi = get_live_data(city)

        rain = 5

        risk = model.predict([[temp, humidity, aqi, rain, 0]])[0]
        advice = get_precautions(risk)

        save_prediction(city, temp, humidity, aqi, rain, 0, risk, "Insect-Borne Disease")

        area, reason = get_urban_risk(temp, humidity, aqi, rain, 0, "Insect-Borne Disease")

        return render_template(
            "result.html",
            city=city,
            temp=temp,
            humidity=humidity,
            aqi=aqi,
            rain=rain,
            pop=0,
            prediction=risk,
            advice=advice,
            category="Insect-Borne Disease",
            area=area,
            reason=reason
        )

    return render_template("insect.html")

# ---------------- HISTORY ----------------
@app.route('/history')
def history():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM predictions")
    data = cursor.fetchall()

    conn.close()
    return render_template("history.html", data=data)

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT risk, COUNT(*) FROM predictions GROUP BY risk")
    result = cursor.fetchall()

    conn.close()

    labels = [row[0] for row in result]
    values = [row[1] for row in result]

    return render_template("dashboard.html", labels=labels, values=values)

# ---------------- CHATBOT ----------------
@app.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.get_json()
    message = data["message"].lower()

    responses = {
        "dengue": "Dengue is spread by mosquitoes.",
        "malaria": "Malaria spreads through mosquito bites.",
        "symptoms": "Fever, headache, nausea.",
        "prevention": "Keep surroundings clean."
    }

    reply = "I can help with health queries."

    for key in responses:
        if key in message:
            reply = responses[key]
            break

    return jsonify({"reply": reply})

@app.route('/chat')
def chat():
    return render_template("chatbot.html")

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)