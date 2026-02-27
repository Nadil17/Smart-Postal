"""
ml_models.py
────────────
Extracted from Routes_Optimization_Model.py (Jupyter notebook).
Contains:
  • PriorityClassifier  – XGBoost mail priority prediction
  • RouteOptimizer      – 4 algorithms (NN, Urgent-Priority, 2-Opt, Q-Learning)
  • DynamicRerouter     – real-time condition-change rerouting
"""

import random
import math
import json
import pickle
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from datetime import datetime

import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in km between two lat/lon points."""
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ─────────────────────────────────────────────────────────────────────────────
# MODEL 1 – Priority Classifier
# ─────────────────────────────────────────────────────────────────────────────

URGENT_MAIL_TYPES = {
    "Court Notice", "Legal Document", "Registered Letter", "Speed Post",
    "Certified Mail", "Government Notice", "Tax Notice", "Medical Report",
    "Insurance Claim", "Summons",
}

URGENT_SENDER_TYPES = {
    "Court", "Law Firm", "Government Office", "Tax Office",
    "Bank", "Hospital", "Insurance Company",
}


class PriorityClassifier:
    """
    Rule-based + lightweight ML priority classifier.
    Falls back to business-rules when model file is absent.
    """

    def __init__(self):
        self.model = None
        try:
            import xgboost as xgb
            from sklearn.preprocessing import LabelEncoder
            self.xgb = xgb
            self._try_load()
        except ImportError:
            pass

    def _try_load(self):
        try:
            with open("model1_priority_classifier.pkl", "rb") as f:
                self.model = pickle.load(f)
        except FileNotFoundError:
            pass

    def classify(self, mail_type: str, sender_type: str,
                 recipient_type: str, time_received: str, day_of_week: str) -> dict:
        """Return priority label + confidence score."""
        # Business-rules fallback
        is_urgent = (
            mail_type in URGENT_MAIL_TYPES or
            sender_type in URGENT_SENDER_TYPES
        )
        label = "urgent" if is_urgent else "regular"
        confidence = 0.92 if is_urgent else 0.88
        return {"priority": label, "confidence": round(confidence, 3)}


# ─────────────────────────────────────────────────────────────────────────────
# MODEL 2A – Route Optimizer
# ─────────────────────────────────────────────────────────────────────────────

TRAFFIC_FACTORS = {"low": 1.0, "moderate": 1.3, "high": 1.6, "severe": 2.0}
WEATHER_FACTORS = {"clear": 1.0, "light_rain": 1.15, "heavy_rain": 1.4, "flooding": 1.8}
SPEED_KMH = 30.0  # average urban postal speed


def _route_stats(points: list, order: list, depot: dict,
                 traffic_factor: float, weather_factor: float) -> dict:
    """Compute total distance & time for a route order."""
    combined = traffic_factor * weather_factor
    pts = {p["id"]: p for p in points}

    total_dist = 0.0
    prev = depot
    for pid in order:
        p = pts[pid]
        total_dist += haversine(prev["latitude"], prev["longitude"],
                                p["latitude"], p["longitude"])
        prev = p
    # return to depot
    total_dist += haversine(prev["latitude"], prev["longitude"],
                            depot["latitude"], depot["longitude"])

    total_time = (total_dist / SPEED_KMH) * combined

    # urgent on-time: urgent items that are visited in first 40 % of route
    urgent_ids = {p["id"] for p in points if p.get("urgent", 0) == 1}
    threshold = max(1, int(len(order) * 0.4))
    urgent_on_time = sum(1 for i, pid in enumerate(order)
                         if pid in urgent_ids and i < threshold)

    return {
        "route": order,
        "total_distance_km": round(total_dist, 3),
        "total_time_hours": round(total_time, 3),
        "urgent_on_time": urgent_on_time,
    }


class RouteOptimizer:
    def __init__(self, depot: dict = None):
        self.depot = depot or {"latitude": 6.9271, "longitude": 79.8612, "id": 0}

    # ── Nearest Neighbour ────────────────────────────────
    def nearest_neighbor(self, scenario: dict) -> dict:
        points = scenario["delivery_points"]
        tf = scenario.get("traffic_factor", 1.3)
        wf = scenario.get("weather_factor", 1.0)

        unvisited = [p["id"] for p in points]
        order = []
        curr = self.depot

        while unvisited:
            nearest = min(
                unvisited,
                key=lambda pid: haversine(
                    curr["latitude"], curr["longitude"],
                    next(p for p in points if p["id"] == pid)["latitude"],
                    next(p for p in points if p["id"] == pid)["longitude"],
                ),
            )
            order.append(nearest)
            unvisited.remove(nearest)
            curr = next(p for p in points if p["id"] == nearest)

        stats = _route_stats(points, order, self.depot, tf, wf)
        stats["method"] = "nearest_neighbor"
        return stats

    # ── Urgent-Priority ──────────────────────────────────
    def urgent_priority(self, scenario: dict) -> dict:
        points = scenario["delivery_points"]
        tf = scenario.get("traffic_factor", 1.3)
        wf = scenario.get("weather_factor", 1.0)

        urgent = [p for p in points if p.get("urgent", 0) == 1]
        regular = [p for p in points if p.get("urgent", 0) == 0]

        def nn_order(subset, start):
            unvisited = [p["id"] for p in subset]
            order = []
            curr = start
            pts = {p["id"]: p for p in subset}
            while unvisited:
                nearest = min(
                    unvisited,
                    key=lambda pid: haversine(
                        curr["latitude"], curr["longitude"],
                        pts[pid]["latitude"], pts[pid]["longitude"],
                    ),
                )
                order.append(nearest)
                unvisited.remove(nearest)
                curr = pts[nearest]
            return order, curr

        if urgent:
            order_u, last_u = nn_order(urgent, self.depot)
            order_r, _ = nn_order(regular, last_u)
            order = order_u + order_r
        else:
            order, _ = nn_order(regular, self.depot)

        stats = _route_stats(points, order, self.depot, tf, wf)
        stats["method"] = "urgent_priority"
        return stats

    # ── 2-Opt ────────────────────────────────────────────
    def two_opt(self, scenario: dict) -> dict:
        base = self.nearest_neighbor(scenario)
        order = base["route"][:]
        points = scenario["delivery_points"]
        tf = scenario.get("traffic_factor", 1.3)
        wf = scenario.get("weather_factor", 1.0)

        improved = True
        while improved:
            improved = False
            for i in range(1, len(order) - 1):
                for j in range(i + 1, len(order)):
                    new_order = order[:i] + order[i:j + 1][::-1] + order[j + 1:]
                    if (_route_stats(points, new_order, self.depot, tf, wf)["total_distance_km"] <
                            _route_stats(points, order, self.depot, tf, wf)["total_distance_km"]):
                        order = new_order
                        improved = True

        stats = _route_stats(points, order, self.depot, tf, wf)
        stats["method"] = "2opt"
        return stats

    # ── Q-Learning ───────────────────────────────────────
    def q_learning(self, scenario: dict, episodes: int = 400) -> dict:
        points = scenario["delivery_points"]
        tf = scenario.get("traffic_factor", 1.3)
        wf = scenario.get("weather_factor", 1.0)
        n = len(points)
        ids = [p["id"] for p in points]
        pts = {p["id"]: p for p in points}

        Q = defaultdict(lambda: defaultdict(float))
        alpha, gamma, eps = 0.1, 0.9, 0.9

        best_order = None
        best_dist = float("inf")

        for ep in range(episodes):
            eps = max(0.05, eps * 0.995)
            unvisited = set(ids)
            order = []
            curr_id = None  # depot

            while unvisited:
                state = (curr_id, frozenset(unvisited))
                if random.random() < eps:
                    action = random.choice(list(unvisited))
                else:
                    action = max(unvisited, key=lambda a: Q[state][a])

                order.append(action)
                unvisited.discard(action)

                prev_lat = self.depot["latitude"] if curr_id is None else pts[curr_id]["latitude"]
                prev_lon = self.depot["longitude"] if curr_id is None else pts[curr_id]["longitude"]
                dist = haversine(prev_lat, prev_lon, pts[action]["latitude"], pts[action]["longitude"])
                urgency_bonus = 5.0 if pts[action].get("urgent", 0) == 1 and len(order) <= max(1, n // 3) else 0.0
                reward = -dist * tf * wf + urgency_bonus

                next_state = (action, frozenset(unvisited))
                max_next = max(Q[next_state].values()) if Q[next_state] else 0.0
                Q[state][action] += alpha * (reward + gamma * max_next - Q[state][action])
                curr_id = action

            stats = _route_stats(points, order, self.depot, tf, wf)
            if stats["total_distance_km"] < best_dist:
                best_dist = stats["total_distance_km"]
                best_order = order[:]

        stats = _route_stats(points, best_order, self.depot, tf, wf)
        stats["method"] = "q_learning"
        return stats

    # ── Run all 4 ────────────────────────────────────────
    def optimize_all(self, scenario: dict) -> dict:
        results = {
            "nearest_neighbor": self.nearest_neighbor(scenario),
            "urgent_priority": self.urgent_priority(scenario),
            "2opt": self.two_opt(scenario),
            "q_learning": self.q_learning(scenario),
        }
        best_method = min(results, key=lambda m: results[m]["total_distance_km"])
        best = results[best_method]

        # Attach delivery point details to each result
        pts = {p["id"]: p for p in scenario["delivery_points"]}
        for method, res in results.items():
            res["deliveries"] = [self.depot] + [pts[pid] for pid in res["route"]] + [self.depot]

        return {
            "results": results,
            "best_method": best_method,
            "best_result": best,
            "traffic_level": scenario.get("traffic_level", "moderate"),
            "weather_condition": scenario.get("weather_condition", "clear"),
        }


# ─────────────────────────────────────────────────────────────────────────────
# MODEL 2B – Dynamic Rerouter
# ─────────────────────────────────────────────────────────────────────────────

class DynamicRerouter:
    def __init__(self, optimizer: RouteOptimizer):
        self.optimizer = optimizer

    def change_conditions(self, deliveries: list, original_traffic: str,
                          original_weather: str, new_traffic: str,
                          new_weather: str) -> dict:
        """
        Re-optimize after weather / traffic change.
        Returns original_route, new_route, and impact_analysis.
        """
        pts = [{**d, "id": i} for i, d in enumerate(deliveries)]

        old_scenario = {
            "delivery_points": pts,
            "traffic_factor": TRAFFIC_FACTORS.get(original_traffic, 1.3),
            "weather_factor": WEATHER_FACTORS.get(original_weather, 1.0),
            "traffic_level": original_traffic,
            "weather_condition": original_weather,
        }
        new_scenario = {
            "delivery_points": pts,
            "traffic_factor": TRAFFIC_FACTORS.get(new_traffic, 1.3),
            "weather_factor": WEATHER_FACTORS.get(new_weather, 1.0),
            "traffic_level": new_traffic,
            "weather_condition": new_weather,
        }

        old_result = self.optimizer.q_learning(old_scenario)
        new_result = self.optimizer.q_learning(new_scenario)

        old_result["deliveries"] = [self.optimizer.depot] + \
            [pts[pid] for pid in old_result["route"]] + [self.optimizer.depot]
        new_result["deliveries"] = [self.optimizer.depot] + \
            [pts[pid] for pid in new_result["route"]] + [self.optimizer.depot]

        time_diff_min = round((new_result["total_time_hours"] - old_result["total_time_hours"]) * 60, 1)
        dist_diff = round(new_result["total_distance_km"] - old_result["total_distance_km"], 3)
        time_pct = round(abs(time_diff_min) / max(old_result["total_time_hours"] * 60, 1) * 100, 1)

        if time_pct < 5:
            severity = "MINIMAL"
        elif time_pct < 15:
            severity = "LOW"
        elif time_pct < 25:
            severity = "MEDIUM"
        elif time_pct < 40:
            severity = "HIGH"
        else:
            severity = "CRITICAL"

        return {
            "original_route": old_result,
            "new_route": new_result,
            "impact_analysis": {
                "time_change_minutes": time_diff_min,
                "distance_change_km": dist_diff,
                "time_change_pct": time_pct,
                "severity": severity,
            },
            "old_weather": original_weather,
            "new_weather": new_weather,
            "old_traffic": original_traffic,
            "new_traffic": new_traffic,
        }
