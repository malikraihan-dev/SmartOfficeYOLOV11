"use client";
import { useState } from "react";
import { Activity, ArrowRight, RefreshCw } from "lucide-react";
import Link from "next/link";
import { Badge } from "@/components/ui";
import { TrendChart } from "@/components/trend-chart";
import { usePoll } from "@/lib/use-poll";
import { useOffice } from "@/components/office-provider";
import type { SensorDataset } from "@/lib/types";
import { number, sensorState } from "@/lib/api";

export function LiveTelemetry() {
  const { data: status, error: statusError, paused } = useOffice();
  const { data, error, refresh, loading } = usePoll<SensorDataset>("/api/sensors/dataset?limit=12", 10000, paused);
  const [metric, setMetric] = useState<"co2_ppm" | "temperature_c">("co2_ppm");
  const rows = [...(data?.rows ?? [])].reverse();
  const values = rows.map(row => row[metric]);
  const source = paused ? "DIJEDA" : sensorState(status, !!status && !statusError);
  const unit = metric === "co2_ppm" ? "ppm" : "°C";
  const time = (value: string | undefined) => value ? new Date(value).toLocaleTimeString("id-ID", { hour: "2-digit", minute: "2-digit" }) : "--";
  return <section className="live-telemetry" aria-labelledby="live-telemetry-title"><div className="live-telemetry-intro"><span className="saas-kicker"><Activity size={14} aria-hidden="true" />WORKSPACE ANALYTICS</span><h2 id="live-telemetry-title">Setiap pembacaan,<br /><span>lebih bermakna.</span></h2><p>{statusError ? "Koneksi terputus. Data historis tidak menunjukkan kondisi ruang saat ini." : source === "DEMO" ? "Angka terkini masih simulasi. Grafik hanya menampilkan riwayat SCD40 yang benar-benar tersimpan." : "Telusuri kondisi ruang melalui sumber, waktu pembaruan, dan riwayat pembacaan."}</p><Link href="/datasets/sensors">Jelajahi dataset <ArrowRight size={16} aria-hidden="true" /></Link><div className="telemetry-source"><span>Sumber saat ini</span><Badge tone={source === "LIVE" ? "green" : "amber"}>{source}</Badge></div></div>
    <div className="live-chart-card"><div className="live-chart-header"><div><span>RIWAYAT SCD40</span><h3>{metric === "co2_ppm" ? "Karbon dioksida" : "Suhu ruangan"}</h3></div><div className="preview-tabs" aria-label="Metrik grafik sensor"><button aria-pressed={metric === "co2_ppm"} onClick={() => setMetric("co2_ppm")}>CO₂</button><button aria-pressed={metric === "temperature_c"} onClick={() => setMetric("temperature_c")}>Suhu</button></div></div><div className="live-chart-value">{values.length ? number(values.at(-1), metric === "co2_ppm" ? 0 : 1) : "--"}<span>{unit}</span><small>{error ? "Riwayat terakhir · gagal memperbarui" : rows.length ? `${rows.length} pembacaan tersimpan` : loading ? "Memuat riwayat…" : "Belum ada riwayat asli"}</small></div><TrendChart values={values} label={metric === "co2_ppm" ? "Riwayat CO₂" : "Riwayat suhu"} unit={unit} start={time(rows[0]?.timestamp)} end={time(rows.at(-1)?.timestamp)} />
      <div className="live-chart-footer"><span>{error ? "Periksa koneksi dan coba perbarui." : "Riwayat tersimpan · bukan indikator perangkat online"}</span><button type="button" aria-label="Perbarui grafik sensor" disabled={loading || paused} onClick={refresh}><RefreshCw size={14} aria-hidden="true" /></button></div>
    </div></section>;
}
