import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests
import json

# --- Flask App Configuration ---
app = Flask(__name__, template_folder='.')

# --- Supabase Configuration ---
SUPABASE_URL = "https://nirfwbsweyurafpifkst.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
SUPABASE_TABLE = "greetings"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# --- Helper: Geolocation ---
def get_geolocation(ip_address):
    """Get approximate location of a visitor using their IP."""
    if ip_address in ('127.0.0.1', '::1'):
        return "Local Development"
    try:
        response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                city = data.get("city", "Unknown City")
                region = data.get("regionName", "Unknown Region")
                country = data.get("country", "Unknown Country")
                return f"{city}, {region}, {country}"
    except requests.RequestException:
        pass
    return "Location not found"

# --- Routes ---
@app.route('/')
def index():
    """Homepage to start the greeting chain."""
    return render_template('index.html')

@app.route('/greet')
def greet():
    """Greeting page for the receiver."""
    sender_name = request.args.get('sender')
    if not sender_name:
        return redirect(url_for('index'))

    share_url = url_for('greet', _external=True, sender=sender_name)
    return render_template('greet.html', sender_name=sender_name, share_url=share_url)

@app.route('/dashboard')
def dashboard():
    """Dashboard showing all greetings."""
    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}?select=*&order=timestamp.desc"
    response = requests.get(url, headers=HEADERS)
    greetings = response.json() if response.status_code == 200 else []

    total = len(greetings)
    return render_template('dashboard.html', greetings=greetings, total=total)

@app.route('/api/submit', methods=['POST'])
def submit_greeting():
    """Store a new greeting and return the next link."""
    data = request.get_json()
    sender_name = data.get("sender_name")
    receiver_name = data.get("receiver_name")

    if not receiver_name:
        return jsonify({"error": "Receiver name is required."}), 400

    timestamp = datetime.utcnow().isoformat()
    ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
    location = get_geolocation(ip_address)
    user_agent = request.headers.get("User-Agent")

    # Insert into Supabase
    payload = {
        "sender_name": sender_name,
        "receiver_name": receiver_name,
        "timestamp": timestamp,
        "ip_address": ip_address,
        "location": location,
        "user_agent": user_agent
    }

    url = f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}"
    response = requests.post(url, headers=HEADERS, data=json.dumps(payload))

    if response.status_code not in (200, 201):
        return jsonify({"error": "Failed to save greeting."}), 500

    next_link = url_for('greet', _external=True, sender=receiver_name)
    return jsonify({"message": "Greeting sent successfully!", "next_link": next_link})

# --- Run App ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
