"use client";
import { useEffect, useState } from "react";
import { useOffice } from "./office-provider";
import { cameraLive, sensorState } from "@/lib/api";

export function DeviceStatus() {
  const { data, error, paused, updatedAt } = useOffice();
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => { setNow(Date.now()); const timer = setInterval(() => setNow(Date.now()), 1000); return () => clearInterval(timer); }, []);
  const age = (at: string | null | undefined) => {
    if (!at || now === null || !Number.isFinite(Date.parse(at))) return "Belum ada pembacaan";
    const seconds = Math.max(0, Math.floor((now - Date.parse(at)) / 1000));
    return seconds < 60 ? `${seconds} dtk lalu` : seconds < 3600 ? `${Math.floor(seconds / 60)} mnt lalu` : `${Math.floor(seconds / 3600)} jam lalu`;
  };
  return <section className="device-status-strip" aria-label="Status perangkat dan umur pembacaan">
    <div><strong>Kamera</strong><span>{error ? "TERPUTUS" : cameraLive(data, !!data) ? "LIVE" : "MENUNGGU"}</span><small>{age(data?.last_frame_at)}</small></div>
    <div><strong>Sensor SCD40</strong><span>{sensorState(data, !!data && !error)}</span><small>{age(data?.sensor_updated_at)}</small></div>
    <div><strong>Audio</strong><span>{error ? "TERPUTUS" : data?.audio_available ? "TERSEDIA" : "BELUM ADA"}</span><small>Tersedia bukan berarti sedang bersuara</small></div>
    <p>{paused ? "Pembaruan dijeda" : "Pemeriksaan server"}<small>{age(updatedAt)}</small></p>
  </section>;
}
