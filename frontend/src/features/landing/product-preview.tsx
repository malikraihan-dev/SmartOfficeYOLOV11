"use client";
import { useState } from "react";
import { Activity, ArrowUpRight, Droplets, MoreHorizontal, Thermometer, Wind } from "lucide-react";
import { TrendChart } from "@/components/trend-chart";
const series = {
  co2: { values: [510, 530, 522, 555, 610, 588, 640, 622, 680, 648, 690, 720], label: "Karbon dioksida", unit: "ppm", value: "720" },
  temperature: { values: [24.1, 24.3, 24.2, 24.5, 24.6, 24.4, 24.8, 24.7, 25, 25.2, 25.1, 25.4], label: "Suhu ruangan", unit: "°C", value: "25,4" },
};
export function ProductPreview({ compact = false }: { compact?: boolean }) {
  const [metric, setMetric] = useState<keyof typeof series>("co2");
  const selected = series[metric];
  return <div className={`product-preview ${compact ? "preview-compact" : ""}`}>
    <div className="preview-toolbar"><span><Activity size={17} aria-hidden="true" />Workspace analytics</span><span className="preview-demo">DEMO · ILUSTRASI</span></div>
    <div className="preview-main"><div className="preview-title"><div><span>RINGKASAN LINGKUNGAN</span><h3>Ruang kerja, dalam angka.</h3></div><MoreHorizontal size={20} aria-hidden="true" /></div>
      <div className="preview-metrics"><div><span><Wind size={14} aria-hidden="true" />CO₂</span><strong>720<small>ppm</small></strong></div><div><span><Thermometer size={14} aria-hidden="true" />Suhu</span><strong>25,4<small>°C</small></strong></div><div><span><Droplets size={14} aria-hidden="true" />Kelembapan</span><strong>52,3<small>%</small></strong></div></div>
      <div className="preview-chart-header"><div><span>{selected.label}</span><strong>{selected.value} <small>{selected.unit}</small></strong></div><div className="preview-tabs" aria-label="Metrik pratinjau"><button type="button" aria-pressed={metric === "co2"} onClick={() => setMetric("co2")}>CO₂</button><button type="button" aria-pressed={metric === "temperature"} onClick={() => setMetric("temperature")}>Suhu</button></div></div>
      <TrendChart values={selected.values} unit={selected.unit} label={selected.label} start="09.00" end="10.00" illustrative />
      <div className="preview-foot"><span><span className="status-dot" />Contoh tampilan · bukan pembacaan perangkat</span><ArrowUpRight size={16} aria-hidden="true" /></div>
    </div>
  </div>;
}
