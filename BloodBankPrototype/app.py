from flask import Flask, render_template, request, jsonify
import sqlite3
import heapq
from pathlib import Path

app = Flask(__name__)
DB_PATH = Path(__file__).with_name("bloodbank.db")

# Simplified academic demo only. Real blood compatibility requires qualified clinical verification.
DEMO_INVENTORY = [
    ("A+", 12, 4), ("A-", 5, 2), ("B+", 10, 3), ("B-", 4, 1),
    ("AB+", 6, 2), ("AB-", 3, 1), ("O+", 15, 5), ("O-", 7, 2)
]
# Weighted roads between sample locations (distance units are illustrative kilometres).
ROADS = {
    "Central Blood Bank": {"City Hospital": 5, "North Hospital": 8, "East Hospital": 6},
    "City Hospital": {"Central Blood Bank": 5, "North Hospital": 4, "South Hospital": 7},
    "North Hospital": {"Central Blood Bank": 8, "City Hospital": 4, "East Hospital": 3},
    "East Hospital": {"Central Blood Bank": 6, "North Hospital": 3, "South Hospital": 4},
    "South Hospital": {"City Hospital": 7, "East Hospital": 4}
}

def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            blood_group TEXT UNIQUE NOT NULL,
            units INTEGER NOT NULL DEFAULT 0,
            min_stock INTEGER NOT NULL DEFAULT 0
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            units INTEGER NOT NULL,
            urgency TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""")
        count = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO inventory (blood_group, units, min_stock) VALUES (?, ?, ?)",
                DEMO_INVENTORY
            )

def shortest_path(start, end):
    if start not in ROADS or end not in ROADS:
        return None, None
    distances = {node: float("inf") for node in ROADS}
    previous = {}
    distances[start] = 0
    queue = [(0, start)]
    while queue:
        dist, node = heapq.heappop(queue)
        if dist != distances[node]:
            continue
        if node == end:
            break
        for neighbour, weight in ROADS[node].items():
            new_dist = dist + weight
            if new_dist < distances[neighbour]:
                distances[neighbour] = new_dist
                previous[neighbour] = node
                heapq.heappush(queue, (new_dist, neighbour))
    if distances[end] == float("inf"):
        return None, None
    path = [end]
    while path[-1] != start:
        path.append(previous[path[-1]])
    path.reverse()
    return path, distances[end]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/dashboard")
def dashboard():
    with connect() as conn:
        inventory = [dict(r) for r in conn.execute("SELECT * FROM inventory ORDER BY blood_group")]
        requests_data = [dict(r) for r in conn.execute("SELECT * FROM requests ORDER BY id DESC")]
    return jsonify({
        "inventory": inventory,
        "requests": requests_data,
        "total_units": sum(x["units"] for x in inventory),
        "pending_requests": sum(1 for r in requests_data if r["status"] == "Pending"),
        "low_stock": sum(1 for x in inventory if x["units"] <= x["min_stock"])
    })

@app.route("/api/inventory", methods=["POST"])
def update_inventory():
    data = request.get_json(force=True)
    group = str(data.get("blood_group", "")).strip().upper()
    try:
        units = int(data.get("units", -1))
    except (TypeError, ValueError):
        return jsonify({"error": "Units must be a whole number."}), 400
    if group not in [x[0] for x in DEMO_INVENTORY] or units < 0:
        return jsonify({"error": "Choose a valid blood group and non-negative unit count."}), 400
    with connect() as conn:
        conn.execute("UPDATE inventory SET units = ? WHERE blood_group = ?", (units, group))
    return jsonify({"message": f"{group} inventory updated."})

@app.route("/api/requests", methods=["POST"])
def create_request():
    data = request.get_json(force=True)
    hospital = str(data.get("hospital", "")).strip()
    group = str(data.get("blood_group", "")).strip().upper()
    urgency = str(data.get("urgency", "Normal")).strip().title()
    try:
        units = int(data.get("units", 0))
    except (TypeError, ValueError):
        units = 0
    if hospital not in ROADS or hospital == "Central Blood Bank":
        return jsonify({"error": "Choose a listed hospital."}), 400
    if group not in [x[0] for x in DEMO_INVENTORY] or units < 1:
        return jsonify({"error": "Choose a valid blood group and request at least one unit."}), 400
    if urgency not in ["Critical", "High", "Normal"]:
        urgency = "Normal"
    with connect() as conn:
        conn.execute(
            "INSERT INTO requests (hospital, blood_group, units, urgency) VALUES (?, ?, ?, ?)",
            (hospital, group, units, urgency)
        )
    return jsonify({"message": "Hospital request added."})

@app.route("/api/allocate/<int:request_id>", methods=["POST"])
def allocate(request_id):
    with connect() as conn:
        req = conn.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()
        if req is None:
            return jsonify({"error": "Request not found."}), 404
        if req["status"] != "Pending":
            return jsonify({"error": "This request has already been processed."}), 400
        stock = conn.execute("SELECT * FROM inventory WHERE blood_group = ?", (req["blood_group"],)).fetchone()
        if stock is None or stock["units"] < req["units"]:
            return jsonify({"error": "Insufficient exact-group stock for this demo allocation."}), 400
        path, distance = shortest_path("Central Blood Bank", req["hospital"])
        if path is None:
            return jsonify({"error": "No route found."}), 400
        conn.execute("UPDATE inventory SET units = units - ? WHERE blood_group = ?",
                     (req["units"], req["blood_group"]))
        conn.execute("UPDATE requests SET status = 'Allocated' WHERE id = ?", (request_id,))
    return jsonify({
        "message": "Allocation completed in the prototype.",
        "blood_group": req["blood_group"],
        "units": req["units"],
        "path": path,
        "distance": distance
    })

@app.route("/api/route", methods=["POST"])
def route():
    data = request.get_json(force=True)
    hospital = data.get("hospital", "")
    path, distance = shortest_path("Central Blood Bank", hospital)
    if path is None:
        return jsonify({"error": "Choose a valid hospital."}), 400
    return jsonify({"path": path, "distance": distance, "algorithm": "Dijkstra's shortest-path algorithm"})

@app.route("/api/reset", methods=["POST"])
def reset():
    with connect() as conn:
        conn.execute("DELETE FROM requests")
        conn.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'requests'")
        conn.executemany("UPDATE inventory SET units = ?, min_stock = ? WHERE blood_group = ?",
                         [(u, m, g) for g, u, m in DEMO_INVENTORY])
    return jsonify({"message": "Demo data reset."})

init_db()

if __name__ == "__main__":
    app.run(debug=True)
