from flask import Flask, render_template, request, redirect, session, jsonify
import pickle
import sqlite3
import requests

import sqlite3

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Create table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )
    """)

    # Insert default user
    cursor.execute("SELECT * FROM users WHERE username='admin'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO users(username, password) VALUES(?, ?)",
            ("admin", "admin")
        )

    conn.commit()
    conn.close()

# Call this function
init_db()

def get_live_data(city):

    API_KEY = "c4bde06fec07d889a99939c5ce835ff2"

    # -------- WEATHER --------
    weather_url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    weather_res = requests.get(weather_url).json()

    temp = weather_res["main"]["temp"]
    humidity = weather_res["main"]["humidity"]

    # -------- AQI --------
    lat = weather_res["coord"]["lat"]
    lon = weather_res["coord"]["lon"]

    aqi_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}"
    aqi_res = requests.get(aqi_url).json()

    aqi = aqi_res["list"][0]["main"]["aqi"]

    return temp, humidity, aqi

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- LOAD MODEL ----------------
model = pickle.load(open("disease_model.pkl", "rb"))

# ---------------- DATABASE ----------------
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
id INTEGER PRIMARY KEY AUTOINCREMENT,
username TEXT,
password TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS predictions(
temp REAL,
humidity REAL,
aqi REAL,
rain REAL,
pop REAL,
risk TEXT,
category TEXT
)
""")

conn.commit()

# ---------------- PRECAUTIONS ----------------
def get_precautions(risk):
    if risk == "High":
        return [
            "Use mosquito nets",
            "Avoid stagnant water",
            "Wear full sleeve clothes",
            "Use mosquito repellent",
            "Keep surroundings clean"
        ]
    elif risk == "Medium":
        return [
            "Keep environment clean",
            "Avoid dirty water",
            "Use mosquito protection"
        ]
    else:
        return [
            "Maintain hygiene",
            "Drink clean water",
            "Keep surroundings clean"
        ]


def get_urban_risk(temp, humidity, aqi, rain, pop, category):

    # -------- SKIN --------
    if category == "Skin Disease":
        if humidity > 70 and temp > 30:
            return "Slum Areas", "High humidity and heat cause skin infections"
        elif aqi > 150:
            return "Industrial Areas", "Pollution causes skin irritation"
        else:
            return "Residential Areas", "Moderate environmental conditions"

    # -------- WATER --------
    elif category == "Water-Borne Disease":
        if rain > 100 and pop > 1000:
            return "Flood-Prone Areas", "Heavy rain + dense population spreads contamination"
        else:
            return "Poor Sanitation Areas", "Unsafe water sources"

    # -------- AIR --------
    elif category == "Air-Borne Disease":
        if aqi > 200:
            return "Traffic Zones", "Very poor air quality causes respiratory diseases"
        elif humidity > 80:
            return "Damp Areas", "High humidity spreads airborne infections"
        else:
            return "Urban Areas", "Moderate air quality"

    # -------- INSECT --------
    elif category == "Insect-Borne Disease":
        if rain > 80 and humidity > 60:
            return "Stagnant Water Areas", "Mosquito breeding due to water accumulation"
        else:
            return "Green Areas", "Insects thrive in vegetation zones"

    # -------- GENERAL --------
    else:
        if aqi > 150 and temp > 30:
            return "Industrial + Dense Areas", "Heat and pollution increase disease risk"
        else:
            return "Mixed Urban Area", "General environmental risk"
        
# ---------------- HOME ----------------
@app.route('/')
def home():
    if 'user' not in session:
        return redirect('/login')
    return render_template("index.html")

# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = cursor.fetchone()

        if user:
            session['user'] = username
            return redirect('/')
        else:
            return "Invalid login"

    return render_template("login.html")

# ---------------- SIGNUP ----------------
@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        cursor.execute("INSERT INTO users(username,password) VALUES(?,?)", (username, password))
        conn.commit()

        return redirect('/login')

    return render_template("signup.html")

# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')

# ---------------- GENERAL PREDICTION ----------------
@app.route('/predict', methods=['GET','POST'])
def predict():
    if request.method == 'POST':
        city = request.form['city']
        temp, humidity, aqi = get_live_data(city)
        rain=0
        pop=0

        prediction = model.predict([[temp, humidity, aqi, rain, pop]])
        risk = prediction[0]
        advice = get_precautions(risk)

        area, reason = get_urban_risk(temp, humidity, aqi, rain, pop, "General Disease")

        return render_template("result.html",
                               city = city,
                               temp=temp,
                               humidity=humidity,
                               aqi=aqi,
                               rain=rain,
                               pop=pop,
                               prediction=risk,
                               advice=advice,
                               category="General Disease",
                               area=area,
                               reason=reason)

    return render_template("index.html")

# ---------------- SKIN ----------------
@app.route('/predict/skin', methods=['GET','POST'])
def predict_skin():
    if request.method == 'POST':
        city = request.form['city']
        temp, humidity, aqi = get_live_data(city)

        prediction = model.predict([[temp, humidity, aqi, 0, 0]])
        risk = prediction[0]
        advice = get_precautions(risk)

        area, reason = get_urban_risk(temp, humidity, aqi, 0, 0, "Skin Disease")

        return render_template("result.html",
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
                               reason=reason)

    return render_template("skin.html")

# ---------------- WATER ----------------
@app.route('/predict/water', methods=['GET','POST'])
def predict_water():
    if request.method == 'POST':

        city = request.form['city']
        temp, humidity, aqi = get_live_data(city)

        # Water diseases depend more on rain + population
        rain = 10   # you can keep fixed OR take input later
        pop = 1000

        prediction = model.predict([[temp, humidity, aqi, rain, pop]])
        risk = prediction[0]
        advice = get_precautions(risk)

        area, reason = get_urban_risk(temp, humidity, aqi, rain, pop, "Water-Borne Disease")

        return render_template("result.html",
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
                               reason=reason)

    return render_template("water.html")

# ---------------- AIR ----------------
@app.route('/predict/air', methods=['GET','POST'])
def predict_air():
    if request.method == 'POST':

        city = request.form['city']
        temp, humidity, aqi = get_live_data(city)

        prediction = model.predict([[temp, humidity, aqi, 0, 0]])
        risk = prediction[0]
        advice = get_precautions(risk)

        area, reason = get_urban_risk(temp, humidity, aqi, 0, 0, "Air Borne Disease")

        return render_template("result.html",
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
                               reason=reason)

    return render_template("air.html")

# -------- INSECT DISEASE --------
@app.route('/predict/insect', methods=['GET','POST'])
def predict_insect():
    if request.method == 'POST':

        city = request.form['city']
        temp, humidity, aqi = get_live_data(city)

        # Insect diseases depend on temp + humidity + rain
        rain = 5

        prediction = model.predict([[temp, humidity, aqi, rain, 0]])
        risk = prediction[0]
        advice = get_precautions(risk)

        area, reason = get_urban_risk(temp, humidity, aqi, rain, 0, "Skin-Borne Disease")

        return render_template("result.html",
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
                               reason=reason)

    return render_template("insect.html")
# ---------------- HISTORY ----------------
@app.route('/history')
def history():
    cursor.execute("SELECT * FROM predictions")
    rows = cursor.fetchall()
    return render_template("history.html", rows=rows)

# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    cursor.execute("SELECT risk, COUNT(*) FROM predictions GROUP BY risk")
    data = cursor.fetchall()

    labels = [row[0] for row in data]
    values = [row[1] for row in data]

    return render_template("dashboard.html", labels=labels, values=values)

# ---------------- CHATBOT ----------------
@app.route('/chatbot', methods=['POST'])
def chatbot():
    data = request.get_json()
    message = data["message"].lower()

    responses = {
        "dengue": "Dengue is spread by mosquitoes.",
        "malaria": "Malaria spreads through infected mosquito bites.",
        "symptoms": "Common symptoms include fever, headache and nausea.",
        "prevention": "Keep surroundings clean and avoid stagnant water."
    }

    reply = "I can help with health-related questions."

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