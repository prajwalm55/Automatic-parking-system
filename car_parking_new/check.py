import urllib.request
import json
import ssl
import time
from flask import Flask, render_template, redirect, request, flash, url_for, session

app = Flask(__name__)
app.secret_key = "your_secret_key"

# Initialize parking status
parking_status = {
    'one': {'booked': False, 'status': 'Available'},
    'two': {'booked': False, 'status': 'Available'},
    'three': {'booked': False, 'status': 'Available'},
    'four': {'booked': False, 'status': 'Available'}
}

def fetch_parking_data():
    url = "http://aislyntech.com/crop/parkcheck.php"
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
    if isinstance(data, list) and len(data) > 0:
        return data[0]
    return {}

def update_parking_status():
    data = fetch_parking_data()
    if data:
        values = extract_values(data)
        slots = ['one', 'two', 'three', 'four']
        for slot in slots:
            value = values.get(slot, 'Key not found')
            status = "Booked" if value == "0" else "Available" if value == "1" else "Unknown"
            parking_status[slot]['status'] = status
            parking_status[slot]['booked'] = (status == "Booked")

@app.route('/check', methods=['GET', 'POST'])
def check():
    if 'username' not in session:
        flash("Please login to access this page", "info")
        return redirect(url_for('login'))
    
    update_parking_status()
    return render_template('check.html', parking_status=parking_status)

if __name__ == "__main__":
    app.run(debug=True)
