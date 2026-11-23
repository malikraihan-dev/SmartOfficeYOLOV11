"use client";
import { useState } from "react";
import { postJSON } from "./api";
export function useAction() {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [failed, setFailed] = useState(false);
  async function run<T>(path: string, body?: unknown, success = "Perubahan berhasil disimpan."): Promise<T | null> {
    if (busy) return null;
    setBusy(true); setMessage(""); setFailed(false);
    try { const result = await postJSON<T>(path, body); setMessage(success); return result; }
    catch (error) { setFailed(true); setMessage(error instanceof Error ? error.message : "Server belum dapat dihubungi."); return null; }
    finally { setBusy(false); }
  }
  return { busy, message, failed, run };
}
