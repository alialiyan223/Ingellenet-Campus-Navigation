"""
Flask Server - Backend for the Web-based Campus Navigation System.
Exposes the Python Engine (Pathfinding, AI, Positioning) via REST API.
"""

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import logging
import threading
import time

from navigation.pathfinder import CampusGraph
from navigation.wifi_positioning import WifiLocaliser
from ai.agent import CampusAgent
from network.sync_manager import NetworkSyncManager
from database.db_manager import initialize_database

# Initialize Backend
initialize_database()
graph = CampusGraph()
localiser = WifiLocaliser()
agent = CampusAgent(graph)
sync_mgr = NetworkSyncManager()

# Start background services
localiser.start_background_scan()
sync_mgr.start_background_sync()

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status", methods=["GET"])
def get_status():
    room_code = localiser.current_room
    room_info = graph.get_room_info(room_code) if room_code else None
    
    return jsonify({
        "current_location": room_info if room_info else {"code": "UNKNOWN", "name": "Scanning Wi-Fi..."},
        "sync_status": sync_mgr.get_status(),
        "confidence": localiser.confidence
    })

@app.route("/api/query", methods=["POST"])
def handle_query():
    data = request.json
    query = data.get("query")
    current_loc = localiser.current_room
    
    if not query:
        return jsonify({"error": "No query provided"}), 400
        
    response = agent.process_query(query, current_loc)
    return jsonify(response)

@app.route("/api/map", methods=["GET"])
def get_map():
    return jsonify({
        "rooms": graph.all_rooms(),
        "edges": [
            {"from": u, "to": v, "data": d} 
            for u, v, d in graph.G.edges(data=True)
        ]
    })

@app.route("/api/navigation", methods=["POST"])
def get_navigation():
    data = request.json
    source = data.get("source")
    target = data.get("target")
    
    path_data = graph.shortest_path(source, target)
    if not path_data:
        return jsonify({"error": "Path not found"}), 404
        
    return jsonify(path_data)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host="0.0.0.0", port=5000, debug=False)
