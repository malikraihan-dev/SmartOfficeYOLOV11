export async function requestJSON<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(path, {
    ...init, cache: "no-store", signal: init.signal ?? AbortSignal.timeout(8000),
    headers: { ...(init.body ? { "Content-Type": "application/json" } : {}), ...init.headers },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && path !== "/api/auth/login" && typeof window !== "undefined" && window.location.pathname !== "/login") window.location.replace("/login?reason=session");
    throw new Error(body?.message ?? `Server merespons HTTP ${response.status}.`);
  }
  if (!body || typeof body !== "object") throw new Error("Respons server tidak dapat dibaca.");
  return body as T;
}
export async function postJSON<T>(path: string, body?: unknown) {
  const session = await requestJSON<{ csrf_token?: string }>("/api/auth/session");
  return requestJSON<T>(path, { method: "POST", headers: { "X-CSRF-Token": session.csrf_token ?? "" }, body: body === undefined ? undefined : JSON.stringify(body) });
}
export function number(value: number | null | undefined, digits = 0) {
  return value == null || !Number.isFinite(value) ? "--" : new Intl.NumberFormat("id-ID", { maximumFractionDigits: digits }).format(value);
}
export function timestamp(value: string | null | undefined, compact = false) {
  if (!value || Number.isNaN(Date.parse(value))) return "Belum ada pembacaan";
  return new Intl.DateTimeFormat("id-ID", {
    day: "2-digit", month: "short", ...(compact ? {} : { year: "numeric" }),
    hour: "2-digit", minute: "2-digit", second: "2-digit", timeZoneName: "short",
  }).format(new Date(value));
}
export function sensorState(status: { sensor_updated_at: string | null; sensor_status: string } | null, connected: boolean) {
  if (!connected) return "TERPUTUS";
  if (!status) return "MENUNGGU";
  if (!status.sensor_updated_at) return "DEMO";
  const age = Date.now() - Date.parse(status.sensor_updated_at);
  return !Number.isFinite(age) || age > 30000 || /kedaluwarsa|tidak valid/.test(status.sensor_status) ? "KEDALUWARSA" : "LIVE";
}
export function cameraLive(status: { camera_status: string; last_frame_at: string | null } | null, connected: boolean) {
  if (!connected || status?.camera_status !== "Kamera terhubung" || !status.last_frame_at) return false;
  const age = Date.now() - Date.parse(status.last_frame_at);
  return Number.isFinite(age) && age < 15000;
}
