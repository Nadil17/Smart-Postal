"""
database.py - MySQL connection using PyMySQL + XAMPP
"""

import mysql.connector
from mysql.connector import Error
import os

# ── XAMPP default settings ──────────────────────────────
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 3306)),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),          # XAMPP default = empty
    "database": os.getenv("DB_NAME", "postal_route_db"),
    "charset": "utf8mb4",
    "autocommit": True,
}


def get_connection():
    """Return a new MySQL connection."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"[DB ERROR] {e}")
        raise


def execute_query(sql: str, params: tuple = (), fetch: bool = False):
    """Helper – run a query and optionally return rows."""
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params)
        if fetch:
            return cursor.fetchall()
        return cursor.lastrowid
    finally:
        cursor.close()
        conn.close()


# ── Delivery helpers ────────────────────────────────────
def save_deliveries(session_id: str, deliveries: list) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    sql = """
        INSERT INTO deliveries
          (session_id, address, latitude, longitude, mail_type, priority,
           sender_type, recipient_type, parcels)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """
    rows = [(
        session_id,
        d["address"],
        d["latitude"],
        d["longitude"],
        d.get("mail_type", "Regular Letter"),
        d.get("priority", "regular"),
        d.get("sender_type", "Individual"),
        d.get("recipient_type", "Individual"),
        d.get("parcels", 1),
    ) for d in deliveries]
    cursor.executemany(sql, rows)
    conn.commit()
    last_id = cursor.lastrowid
    cursor.close()
    conn.close()
    return last_id


def get_deliveries(session_id: str) -> list:
    return execute_query(
        "SELECT * FROM deliveries WHERE session_id=%s ORDER BY id",
        (session_id,), fetch=True
    )


# ── Route-session helpers ───────────────────────────────
def save_route_session(session_id: str, result: dict):
    import json
    best = result.get("best_method", "")
    best_res = result.get("results", {}).get(best, {})
    execute_query(
        """INSERT INTO route_sessions
           (session_id, best_method, total_distance_km, total_time_hours,
            urgent_on_time, weather_condition, traffic_level, results_json)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            session_id, best,
            best_res.get("total_distance_km"),
            best_res.get("total_time_hours"),
            best_res.get("urgent_on_time"),
            result.get("weather_condition", "clear"),
            result.get("traffic_level", "moderate"),
            json.dumps(result),
        )
    )


# ── Rerouting event helpers ─────────────────────────────
def save_rerouting_event(session_id: str, event: dict):
    import json
    ia = event.get("impact_analysis", {})
    execute_query(
        """INSERT INTO rerouting_events
           (session_id, old_weather, new_weather, old_traffic, new_traffic,
            time_change_minutes, distance_change_km, severity,
            original_route_json, new_route_json)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            session_id,
            event.get("old_weather"), event.get("new_weather"),
            event.get("old_traffic"), event.get("new_traffic"),
            ia.get("time_change_minutes"),
            ia.get("distance_change_km"),
            ia.get("severity"),
            json.dumps(event.get("original_route", {})),
            json.dumps(event.get("new_route", {})),
        )
    )


# ── Relocation helpers ──────────────────────────────────
def save_relocation(session_id: str, rel: dict):
    import json
    execute_query(
        """INSERT INTO relocations
           (session_id, delivery_id, old_address, new_address,
            old_latitude, old_longitude, new_latitude, new_longitude,
            distance_change_km, before_route_json, after_route_json)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (
            session_id,
            rel.get("delivery_id"),
            rel.get("old_address"), rel.get("new_address"),
            rel.get("old_latitude"), rel.get("old_longitude"),
            rel.get("new_latitude"), rel.get("new_longitude"),
            rel.get("distance_change_km"),
            json.dumps(rel.get("before_route", {})),
            json.dumps(rel.get("after_route", {})),
        )
    )
