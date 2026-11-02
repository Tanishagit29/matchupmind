const BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
async function call(path, body) {
  let r;
  try {
    r = await fetch(BASE + path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : undefined);
  } catch { throw new Error("Cannot reach the backend. Is uvicorn running on " + BASE + "?"); }
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof j.detail === "string" ? j.detail : "Request failed (" + r.status + ")");
  return j;
}
export const api = {
  health: () => call("/health"),
  players: (q) => call("/players?limit=15&q=" + encodeURIComponent(q || "")),
  predict: (s) => call("/predict", s),
  whatif: (baseline, changes) => call("/whatif", { baseline, changes }),
  stats: (n, role) => call("/players/" + encodeURIComponent(n) + "/stats?role=" + role),
  metrics: () => call("/model/metrics"),
};
