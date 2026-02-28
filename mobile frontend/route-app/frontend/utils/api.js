// utils/api.js
// ─────────────────────────────────────────────────────────────
// Change API_BASE to your PC's local IP when running on device.
// e.g.  http://192.168.1.10:8000/api
// ─────────────────────────────────────────────────────────────

export const API_BASE = "http://172.20.10.2:8000/api"; // ← UPDATE THIS

export const DEFAULT_DEPOT = { lat: 6.9271, lng: 79.8612 };

async function request(method, path, body) {
  const options = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body) options.body = JSON.stringify(body);

  const res = await fetch(`${API_BASE}${path}`, options);
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`HTTP ${res.status}: ${txt}`);
  }
  return res.json();
}

export const api = {
  get: (path) => request("GET", path),
  post: (path, body) => request("POST", path, body),
};

// ─── Specific calls ───────────────────────────────────────────
export const classifyPriority = (item) =>
  api.post("/ml/classify-priority", item);

export const optimizeRoute = (payload) =>
  api.post("/ml/optimize-route", payload);

export const changeConditions = (payload) =>
  api.post("/ml/change-conditions-realtime", payload);

export const saveDeliveries = (sessionId, deliveries) =>
  api.post("/deliveries/save", { session_id: sessionId, deliveries });

export const saveRelocation = (payload) =>
  api.post("/relocations/save", payload);

export const newSession = () => api.post("/session/new", {});
