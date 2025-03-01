import secrets
from flask import Flask, render_template, redirect, request, flash, url_for, session, jsonify
import sqlite3
from datetime import datetime, timedelta
import requests
import numpy as np
import cv2
import time
import threading
import urllib.request
import json

# Initialize Flask app
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Generates a secure, random 16-byte key

THINGSPEAK_API_KEY = 'M64NHBJ8ZQMTD15B'  # Your API key

# Define a function to update all slots based on their current status (booked or available)
def update_slots_to_thingSpeak():
    # Generate the slot status based on the current parking_status dictionary
    slot_status = ''
    for slot, data in parking_status.items():
        # If the slot is booked, append '0' (Booked)
        if data['booked']:
            slot_status += '0'
        else:
            # If the slot is available, append '1' (Available)
            slot_status += '1'

    # Send the status to ThingSpeak for all slots
    url = f'https://api.thingspeak.com/update?api_key={THINGSPEAK_API_KEY}&field1={slot_status}'
    response = requests.post(url)
    if response.status_code == 200:
        print(f"Slot status successfully updated to {slot_status}.")
    else:
        print(f"Failed to update slot status. Status code: {response.status_code}")


# Initialize the parking slots with booking status and time
parking_status = {
    1: {'booked': False, 'booking_time': None, 'registration_number': None, 'selected_date': None, 'selected_time': None, 'status': 'Available', 'end_time': None},
    2: {'booked': False, 'booking_time': None, 'registration_number': None, 'selected_date': None, 'selected_time': None, 'status': 'Available', 'end_time': None},
    3: {'booked': False, 'booking_time': None, 'registration_number': None, 'selected_date': None, 'selected_time': None, 'status': 'Available', 'end_time': None},
    4: {'booked': False, 'booking_time': None, 'registration_number': None, 'selected_date': None, 'selected_time': None, 'status': 'Available', 'end_time': None},
}

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/ourteam')
def ourteam():
    return render_template('ourteam.html')

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


# Route to update all slots to "booked"
@app.route('/update_all_slots', methods=['GET'])
def update_all_slots():
    # All slots are booked, so set the status to '0000' (booked)
    slot_status = '0000'  # All slots booked, each slot is '0' (booked)

    # Send the status to ThingSpeak for each of the 4 slots
    url = f'https://api.thingspeak.com/update?api_key={THINGSPEAK_API_KEY}&field1={slot_status}'
    response = requests.post(url)
    if response.status_code == 200:
        print(f"All slots status successfully updated to {slot_status}.")
    else:
        print(f"Failed to update all slots. Status code: {response.status_code}")

    # Return a success message and redirect back to the check page
    flash("All parking slots are now marked as booked.", "success")
    return redirect(url_for('check'))


@app.route('/check', methods=['GET', 'POST'])
def check():
    current_time = datetime.now()

    # Check if the end time is reached, if so reset the slot to available
    for slot, data in parking_status.items():
        if data['booked'] and data['end_time']:
            if current_time >= data['end_time']:
                parking_status[slot]['booked'] = False  # Reset to available after end time
                parking_status[slot]['status'] = 'Available'
                parking_status[slot]['end_time'] = None
                flash(f"Slot {slot} has been freed up.")
                
        # If From Time and Date match current system time, update status to "Booking Started"
        if data['booked'] and data['selected_date'] and data['selected_time']:
            user_date = datetime.strptime(data['selected_date'], '%Y-%m-%d')
            user_time = datetime.strptime(data['selected_time'], '%H:%M')
            user_datetime = datetime.combine(user_date, user_time.time())

            # If the user selected date and time match the system time or have passed, update status
            if user_datetime <= current_time and data['status'] != "Booking Started":
                parking_status[slot]['status'] = 'Booking Started'
                flash(f"Slot {slot} booking started!")

    if request.method == 'POST':
        selected_slot = int(request.form.get('selected_slot'))
        registration_number = request.form.get('registration_number')
        selected_date = request.form.get('selected_date')
        selected_time = request.form.get('from_time')  # User's selected "From Time"
        end_time = request.form.get('end_time')  # User's selected "End Time"

        # Get the user-entered "From Time" and "Selected Date"
        user_date = datetime.strptime(selected_date, '%Y-%m-%d')
        user_time = datetime.strptime(selected_time, '%H:%M')

        # Combine date and time to compare with current system time
        user_datetime = datetime.combine(user_date, user_time.time())

        # Parse end time if given
        if end_time:
            end_time_datetime = datetime.strptime(end_time, '%H:%M')
            end_time_full = datetime.combine(user_date, end_time_datetime.time())

        # Check if the user-entered datetime matches the current system time
        if not parking_status[selected_slot]['booked']:
            parking_status[selected_slot]['booked'] = True
            parking_status[selected_slot]['registration_number'] = registration_number
            parking_status[selected_slot]['selected_date'] = selected_date
            parking_status[selected_slot]['selected_time'] = selected_time
            parking_status[selected_slot]['booking_time'] = current_time  # Store the booking time

            if end_time:
                parking_status[selected_slot]['end_time'] = end_time_full

            flash(f"Slot {selected_slot} booked successfully!")

            # Update the slot status to ThingSpeak
            update_slots_to_thingSpeak()

        else:
            flash(f"Slot {selected_slot} is already booked.")

        return redirect(url_for('check'))

    return render_template('check.html', parking_status=parking_status)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
