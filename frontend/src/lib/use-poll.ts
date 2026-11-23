"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { requestJSON } from "./api";

export function usePoll<T>(path: string, interval = 5000, paused = false) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);
  const [generation, setGeneration] = useState(0);
  const previousPath = useRef(path);
  const refresh = useCallback(() => setGeneration(n => n + 1), []);
  useEffect(() => {
    if (previousPath.current !== path) { setData(null); setError(null); setUpdatedAt(null); setLoading(true); previousPath.current = path; }
    let disposed = false;
    let running = false;
    let timer: ReturnType<typeof setTimeout>;
    let controller: AbortController | null = null;
    async function poll() {
      if (disposed) return;
      if (running) return;
      if (document.hidden || paused) { timer = setTimeout(poll, interval); return; }
      running = true;
      controller = new AbortController();
      const timeout = setTimeout(() => controller?.abort(), 8000);
      setLoading(true);
      try {
        const result = await requestJSON<T>(path, { signal: controller.signal });
        if (!disposed) { setData(result); setError(null); setUpdatedAt(new Date().toISOString()); }
      } catch (cause) {
        if (!disposed) setError(cause instanceof Error && cause.name !== "AbortError" ? cause.message : "Server tidak merespons dalam 8 detik.");
      } finally {
        clearTimeout(timeout);
        running = false;
        if (!disposed) { setLoading(false); timer = setTimeout(poll, interval); }
      }
    }
    function resume() { if (!document.hidden) { clearTimeout(timer); void poll(); } }
    void poll();
    document.addEventListener("visibilitychange", resume);
    return () => { disposed = true; clearTimeout(timer); controller?.abort(); document.removeEventListener("visibilitychange", resume); };
  }, [path, interval, paused, generation]);
  return { data, error, loading, updatedAt, refresh };
}
