
from flask import Flask, render_template, redirect, request, flash, url_for, session
import threading
import urllib.request
import json
from datetime import datetime,timedelta
import time
import sqlite3
import urllib.request
import json
import ssl

app = Flask(__name__)
app.secret_key = "your_secret_key"


@app.route('/')
def home():
    return render_template('home.html')

@app.route('/ourteam')
def ourteam():
    return render_template('ourteam.html')

def login_required(f):
    def wrap(*args, **kwargs):
        if 'username' not in session:
            flash("You need to log in first.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrap

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if not username or not password:
            flash("Username and password are required", "danger")
            return redirect(url_for('login'))

        conn = sqlite3.connect("parking.db")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM customer WHERE name=? AND password=?", (username, password))
        data = cur.fetchone()
        conn.close()

        if data:
            session["username"] = data["name"]
            flash("Login Successful", "success")
            return redirect(url_for('check'))
        else:
            flash("Incorrect username or password", "danger")
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully", "info")
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']

            conn = sqlite3.connect("parking.db")
            cur = conn.cursor()
            cur.execute("INSERT INTO customer (name, email, password) VALUES (?, ?, ?)", (name, email, password))
            conn.commit()
            flash("Record Added Successfully", "success")
        except Exception as e:
            flash("Error Insert Operation: " + str(e), "danger")
        finally:
            conn.close()
            return redirect(url_for("login"))
    return render_template('register.html')


# Initialize parking status
parking_status = {
    'one': {'booked': False, 'status': 'Available', 'end_time': None},
    'two': {'booked': False, 'status': 'Available', 'end_time': None},
    'three': {'booked': False, 'status': 'Available', 'end_time': None},
    'four': {'booked': False, 'status': 'Available', 'end_time': None}
}

def fetch_parking_data():
    """Fetches parking slot data from the API."""
    url = "https://aislyntech.com/crop/parkcheck.php"
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    
    try:
        response = urllib.request.urlopen(url, context=context)
        data = json.load(response)
        return data
    except urllib.error.URLError as e:
        print("Error fetching parking data:", e)
        return None
    except json.JSONDecodeError:
        print("Error decoding JSON response. The response may not be valid JSON.")
        return None
    except Exception as e:
        print("An unexpected error occurred:", e)
        return None

def extract_values(data):
    """Extracts values from API response."""
    if isinstance(data, list) and len(data) > 0:
        return data[0]
    return {}

def update_parking_status():
    """Updates parking status based on API data while preserving manual bookings."""
    data = fetch_parking_data()
    if data:
        values = extract_values(data)
        slots = ['one', 'two', 'three', 'four']
        current_time = datetime.now()

        for slot in slots:
            value = values.get(slot, 'Key not found')

            # Auto-release expired manual bookings (only when system time >= end_time)
            if parking_status[slot]['booked'] and parking_status[slot]['end_time']:
                if parking_status[slot]['end_time'] <= current_time:
                    parking_status[slot]['booked'] = False
                    parking_status[slot]['status'] = "Available"
                    parking_status[slot]['end_time'] = None
                    print(f"Slot {slot} is now automatically released due to timeout.")

            # Handle API-based bookings (Only affect API bookings, not manual)
            if value == "0":
                if not parking_status[slot]['booked']:  # Only book if it's available
                    parking_status[slot]['status'] = "Booked"
                    parking_status[slot]['booked'] = True
                    parking_status[slot]['api_booked'] = True  # Mark this as API booking
            
            elif value == "1":
                # Only release if it was booked via API, not manually
                if parking_status[slot].get('api_booked', False):
                    parking_status[slot]['status'] = "Available"
                    parking_status[slot]['booked'] = False
                    parking_status[slot]['api_booked'] = False  # Remove API booking flag
                    parking_status[slot]['end_time'] = None

def check_and_release_bookings():
    """Checks for expired bookings and releases them."""
    current_time = datetime.now()
    for slot in parking_status:
        if parking_status[slot]['booked'] and parking_status[slot]['end_time']:
            if parking_status[slot]['end_time'] <= current_time:
                parking_status[slot]['booked'] = False
                parking_status[slot]['status'] = "Available"
                parking_status[slot]['end_time'] = None

@app.route('/check', methods=['GET', 'POST'])
def check():
    """Handles parking slot checking and manual booking."""
    if 'username' not in session:
        flash("Please login to access this page", "info")
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        selected_slot = request.form.get('selected_slot')
        registration_number = request.form.get('registration_number')
        selected_date = request.form.get('selected_date')
        from_time = request.form.get('from_time')
        end_time = request.form.get('end_time')
        
        slot_mapping = {"1": "one", "2": "two", "3": "three", "4": "four"}
        slot_key = slot_mapping.get(selected_slot, "one")
        
        if parking_status[slot_key]['booked']:
            flash(f"Slot {selected_slot} is already booked.", "danger")
        else:
            try:
                end_datetime = datetime.strptime(f"{selected_date} {end_time}", "%Y-%m-%d %H:%M")
                parking_status[slot_key]['booked'] = True
                parking_status[slot_key]['status'] = 'Booked'
                parking_status[slot_key]['end_time'] = end_datetime
                session[f"booking_{slot_key}"] = {
                    "registration_number": registration_number,
                    "end_time": end_datetime.strftime("%Y-%m-%d %H:%M")
                }
                flash(f"Slot {selected_slot} booked successfully from {from_time} to {end_time}.", "success")
            except ValueError as ve:
                flash(f"Error parsing end time: {ve}", "danger")
        
        return redirect(url_for('check'))
    
    update_parking_status()
    check_and_release_bookings()
    return render_template('check.html', parking_status=parking_status)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
