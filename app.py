import os
import psycopg2
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify
import requests

# --- Flask App Configuration ---
app = Flask(__name__, template_folder='.')

# --- Database Configuration ---
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_db():
    """Connect to Supabase PostgreSQL."""
    return psycopg2.connect(DATABASE_URL, sslmode='require')

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
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id, sender_name, receiver_name, timestamp, location FROM greetings ORDER BY timestamp DESC")
    rows = cur.fetchall()
    greetings = [
        {
            "id": r[0],
            "sender_name": r[1],
            "receiver_name": r[2],
            "timestamp": r[3],
            "location": r[4]
        } for r in rows
    ]
    cur.execute("SELECT COUNT(*) FROM greetings")
    total = cur.fetchone()[0]
    cur.close()
    conn.close()
    return render_template('dashboard.html', greetings=greetings, total=total)

@app.route('/api/submit', methods=['POST'])
def submit_greeting():
    """Store a new greeting and return the next link."""
    data = request.get_json()
    sender_name = data.get("sender_name")
    receiver_name = data.get("receiver_name")

    if not receiver_name:
        return jsonify({"error": "Receiver name is required."}), 400

    timestamp = datetime.utcnow()
    ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
    location = get_geolocation(ip_address)
    user_agent = request.headers.get("User-Agent")

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO greetings (sender_name, receiver_name, timestamp, ip_address, location, user_agent)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (sender_name, receiver_name, timestamp, ip_address, location, user_agent))
    conn.commit()
    cur.close()
    conn.close()

    next_link = url_for('greet', _external=True, sender=receiver_name)
    return jsonify({"message": "Greeting sent successfully!", "next_link": next_link})

# --- Run App ---
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
