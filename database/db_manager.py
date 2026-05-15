"""
Database Manager - SQLite backend for the Campus Navigation System.
Handles all persistent storage: rooms, paths, Wi-Fi fingerprints, logs.
"""

import sqlite3
import json
import os
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "campus.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database():
    """Create all tables and seed initial campus data."""
    conn = get_connection()
    cur = conn.cursor()

    # ── Rooms / Nodes ──────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            code        TEXT UNIQUE NOT NULL,
            name        TEXT NOT NULL,
            building    TEXT NOT NULL,
            floor       INTEGER NOT NULL DEFAULT 1,
            room_type   TEXT NOT NULL DEFAULT 'classroom',
            x           REAL NOT NULL DEFAULT 0,
            y           REAL NOT NULL DEFAULT 0,
            description TEXT,
            capacity    INTEGER DEFAULT 30,
            is_accessible INTEGER DEFAULT 1
        )
    """)

    # ── Edges / Paths ──────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS edges (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            from_room   TEXT NOT NULL,
            to_room     TEXT NOT NULL,
            weight      REAL NOT NULL DEFAULT 1.0,
            path_type   TEXT NOT NULL DEFAULT 'corridor',
            is_accessible INTEGER DEFAULT 1,
            FOREIGN KEY(from_room) REFERENCES rooms(code),
            FOREIGN KEY(to_room)   REFERENCES rooms(code)
        )
    """)

    # ── Wi-Fi Fingerprints ─────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS wifi_fingerprints (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            room_code   TEXT NOT NULL,
            bssid       TEXT NOT NULL,
            ssid        TEXT,
            rssi_avg    REAL NOT NULL,
            rssi_std    REAL DEFAULT 0,
            frequency   REAL DEFAULT 2400,
            timestamp   TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(room_code) REFERENCES rooms(code)
        )
    """)

    # ── Navigation Logs ────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS navigation_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            from_room   TEXT,
            to_room     TEXT,
            path_json   TEXT,
            distance    REAL,
            timestamp   TEXT DEFAULT CURRENT_TIMESTAMP,
            user_rating INTEGER
        )
    """)

    # ── Map Sync Metadata ──────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sync_log (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            sync_time   TEXT DEFAULT CURRENT_TIMESTAMP,
            server_ip   TEXT,
            status      TEXT,
            records_updated INTEGER DEFAULT 0
        )
    """)

    # ── AI Query Cache ─────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ai_cache (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            query_hash  TEXT UNIQUE NOT NULL,
            query_text  TEXT,
            response    TEXT,
            created_at  TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    _seed_campus_data(cur, conn)
    conn.close()
    logger.info("Database initialised at %s", DB_PATH)


# ── Seed Data ──────────────────────────────────────────────────────────────────

def _seed_campus_data(cur: sqlite3.Cursor, conn: sqlite3.Connection):
    """Insert demo campus layout if tables are empty."""
    cur.execute("SELECT COUNT(*) FROM rooms")
    if cur.fetchone()[0] > 0:
        return  # already seeded

    rooms = [
        # code,       name,                        building,   floor, type,         x,    y,   desc,                      cap
        ("MAIN_ENT",  "Main Entrance",              "Admin",    0, "entrance",      400,  750, "Campus main gate",         0),
        ("ADMIN_01",  "Admin Office",               "Admin",    1, "office",        400,  620, "Registrar & admin staff",  20),
        ("LIB_GF",    "Library Ground Floor",       "Library",  1, "library",       180,  500, "Books & study area",      120),
        ("LIB_1F",    "Library First Floor",        "Library",  2, "library",       180,  380, "Reference section",        80),
        ("CS_LAB1",   "CS Lab 1",                   "Science",  1, "lab",           620,  480, "50 PCs, Python/Java",      50),
        ("CS_LAB2",   "CS Lab 2",                   "Science",  1, "lab",           620,  380, "Networking Lab",           40),
        ("CS_LAB3",   "CS Lab 3",                   "Science",  2, "lab",           620,  280, "AI & Machine Learning",    30),
        ("LECT_A",    "Lecture Hall A",             "Main",     1, "classroom",     400,  480, "Large lecture theatre",   200),
        ("LECT_B",    "Lecture Hall B",             "Main",     1, "classroom",     400,  380, "Medium lecture hall",     100),
        ("ROOM_101",  "Room 101",                   "Main",     1, "classroom",     280,  380, "General classroom",        40),
        ("ROOM_102",  "Room 102",                   "Main",     1, "classroom",     280,  480, "General classroom",        40),
        ("ROOM_201",  "Room 201",                   "Main",     2, "classroom",     280,  280, "Seminar room",             25),
        ("ROOM_202",  "Room 202",                   "Main",     2, "classroom",     400,  280, "Seminar room",             25),
        ("CAFE",      "Cafeteria",                  "Student",  1, "cafeteria",     180,  650, "Food & beverages",        150),
        ("HEALTH",    "Health Center",              "Student",  1, "health",        180,  750, "First aid & clinic",       20),
        ("TOILET_GF", "Washroom (Ground Floor)",    "Main",     1, "washroom",      520,  620, "Male & Female",             0),
        ("TOILET_1F", "Washroom (First Floor)",     "Main",     2, "washroom",      520,  480, "Male & Female",             0),
        ("PARK",      "Parking Area",               "Outdoor",  0, "parking",       700,  700, "Student & staff parking",   0),
        ("SPORTS",    "Sports Complex",             "Outdoor",  0, "sports",        700,  550, "Gym, courts",               0),
        ("PROF_CS",   "CS Department Office",       "Science",  1, "office",        700,  380, "Faculty offices",           15),
    ]

    cur.executemany(
        "INSERT INTO rooms(code,name,building,floor,room_type,x,y,description,capacity) VALUES(?,?,?,?,?,?,?,?,?)",
        rooms
    )

    edges = [
        ("MAIN_ENT", "ADMIN_01",   20, "corridor", 1),
        ("MAIN_ENT", "CAFE",       25, "path",      1),
        ("MAIN_ENT", "HEALTH",     15, "path",      1),
        ("MAIN_ENT", "PARK",       30, "outdoor",   1),
        ("ADMIN_01", "LIB_GF",     30, "corridor",  1),
        ("ADMIN_01", "LECT_A",     25, "corridor",  1),
        ("ADMIN_01", "TOILET_GF",  10, "corridor",  1),
        ("LIB_GF",   "LIB_1F",    15, "stairs",    1),
        ("LIB_GF",   "CAFE",       20, "path",      1),
        ("LIB_GF",   "ROOM_102",   15, "corridor",  1),
        ("LECT_A",   "LECT_B",     10, "corridor",  1),
        ("LECT_A",   "ROOM_102",   15, "corridor",  1),
        ("LECT_A",   "CS_LAB1",    30, "corridor",  1),
        ("LECT_B",   "ROOM_101",   10, "corridor",  1),
        ("LECT_B",   "ROOM_201",   15, "stairs",    1),
        ("ROOM_101", "ROOM_102",   10, "corridor",  1),
        ("ROOM_101", "ROOM_201",   15, "stairs",    1),
        ("ROOM_201", "ROOM_202",   10, "corridor",  1),
        ("ROOM_201", "CS_LAB3",    20, "corridor",  1),
        ("ROOM_202", "TOILET_1F",  10, "corridor",  1),
        ("CS_LAB1",  "CS_LAB2",    10, "corridor",  1),
        ("CS_LAB1",  "PROF_CS",    15, "corridor",  1),
        ("CS_LAB2",  "CS_LAB3",    15, "stairs",    1),
        ("CS_LAB3",  "ROOM_201",   20, "corridor",  1),
        ("SPORTS",   "PARK",       25, "outdoor",   1),
        ("SPORTS",   "CS_LAB1",    30, "path",      1),
        ("TOILET_GF","CS_LAB1",    25, "corridor",  1),
    ]

    cur.executemany(
        "INSERT INTO edges(from_room,to_room,weight,path_type,is_accessible) VALUES(?,?,?,?,?)",
        edges
    )

    # Wi-Fi fingerprints (simulated RSSI values for demo)
    import random
    random.seed(42)
    access_points = [
        ("AA:BB:CC:DD:EE:01", "CampusNet-A", 2412),
        ("AA:BB:CC:DD:EE:02", "CampusNet-B", 2437),
        ("AA:BB:CC:DD:EE:03", "CampusNet-C", 5180),
        ("AA:BB:CC:DD:EE:04", "CampusNet-D", 5200),
    ]
    room_codes = [r[0] for r in rooms]
    fps = []
    for room in room_codes:
        for bssid, ssid, freq in access_points:
            rssi = random.uniform(-80, -40)
            std  = random.uniform(1, 5)
            fps.append((room, bssid, ssid, rssi, std, freq))
    cur.executemany(
        "INSERT INTO wifi_fingerprints(room_code,bssid,ssid,rssi_avg,rssi_std,frequency) VALUES(?,?,?,?,?,?)",
        fps
    )

    conn.commit()
    logger.info("Campus data seeded: %d rooms, %d edges, %d Wi-Fi fingerprints",
                len(rooms), len(edges), len(fps))


# ── CRUD helpers ───────────────────────────────────────────────────────────────

def get_all_rooms() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM rooms ORDER BY building, floor, code").fetchall()
        return [dict(r) for r in rows]


def get_room(code: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM rooms WHERE code=?", (code,)).fetchone()
        return dict(row) if row else None


def get_all_edges() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM edges").fetchall()
        return [dict(r) for r in rows]


def get_wifi_fingerprints(room_code: str) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM wifi_fingerprints WHERE room_code=?", (room_code,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_fingerprints() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM wifi_fingerprints").fetchall()
        return [dict(r) for r in rows]


def log_navigation(from_room: str, to_room: str, path: list, distance: float):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO navigation_logs(from_room,to_room,path_json,distance) VALUES(?,?,?,?)",
            (from_room, to_room, json.dumps(path), distance)
        )
        conn.commit()


def log_sync(server_ip: str, status: str, records: int = 0):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO sync_log(server_ip,status,records_updated) VALUES(?,?,?)",
            (server_ip, status, records)
        )
        conn.commit()


def cache_ai_response(query_hash: str, query: str, response: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO ai_cache(query_hash,query_text,response) VALUES(?,?,?)",
            (query_hash, query, response)
        )
        conn.commit()


def get_cached_ai_response(query_hash: str) -> Optional[str]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT response FROM ai_cache WHERE query_hash=?", (query_hash,)
        ).fetchone()
        return row["response"] if row else None


def search_rooms(query: str) -> list[dict]:
    q = f"%{query}%"
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM rooms
               WHERE name LIKE ? OR code LIKE ? OR room_type LIKE ? OR building LIKE ?
               ORDER BY name""",
            (q, q, q, q)
        ).fetchall()
        return [dict(r) for r in rows]


def get_navigation_history(limit: int = 20) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM navigation_logs ORDER BY timestamp DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
