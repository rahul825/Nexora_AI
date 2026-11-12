// All calls to the FastAPI chat endpoints (venv/routes/chat.py)
const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new Error("Can't reach the API server. Is uvicorn running on port 8000?");
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) {
    const detail = data?.detail;
    throw new Error(typeof detail === "string" ? detail : `Request failed (${res.status})`);
  }
  return data;
}

export const api = {
  listSessions: () => request("/chat/sessions"),
  createSession: (source) =>
    request("/chat/sessions", { method: "POST", body: JSON.stringify({ source }) }),
  getSession: (id) => request(`/chat/sessions/${id}`),
  updateSession: (id, changes) =>
    request(`/chat/sessions/${id}`, { method: "PATCH", body: JSON.stringify(changes) }),
  deleteSession: (id) => request(`/chat/sessions/${id}`, { method: "DELETE" }),
  ask: (id, question, source) =>
    request(`/chat/sessions/${id}/ask`, {
      method: "POST",
      body: JSON.stringify({ question, source }),
    }),
};
