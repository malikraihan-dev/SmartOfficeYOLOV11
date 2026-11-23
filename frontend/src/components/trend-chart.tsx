"use client";
import { useId } from "react";
import { number } from "@/lib/api";

export function TrendChart({ values, unit, label, start, end, illustrative = false }: {
  values: number[]; unit: string; label: string; start: string; end: string; illustrative?: boolean;
}) {
  const id = useId().replace(/:/g, "");
  const low = values.length ? Math.floor(Math.min(...values) * .95) : 0;
  const high = values.length ? Math.ceil(Math.max(...values) * 1.05) : 1;
  const span = Math.max(high - low, 1);
  const points = values.map((value, index) => `${40 + index * 420 / Math.max(values.length - 1, 1)},${150 - (value - low) / span * 120}`).join(" ");
  return <div className="telemetry-chart">
    <svg viewBox="0 0 480 185" role="img" aria-label={`${label}${illustrative ? ", data ilustrasi" : ", data tersimpan"}. ${values.length ? values.map(value => `${number(value, 1)} ${unit}`).join(", ") : "Belum ada riwayat."}`}>
      <defs><linearGradient id={`area-${id}`} x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="currentColor" stopOpacity=".22" /><stop offset="100%" stopColor="currentColor" stopOpacity="0" /></linearGradient></defs>
      {[30, 70, 110, 150].map((y, i) => <g key={y}><line x1="40" x2="460" y1={y} y2={y} className="telemetry-grid" /><text x="0" y={y + 4} className="telemetry-axis">{values.length ? number(high - i * span / 3, 0) : "--"}</text></g>)}
      {values.length > 1 && <><polygon points={`40,150 ${points} 460,150`} fill={`url(#area-${id})`} /><polyline points={points} className="telemetry-line" /><circle cx="460" cy={150 - (values.at(-1)! - low) / span * 120} r="4" fill="currentColor" /></>}
      {values.length === 1 && <circle cx="40" cy={150 - (values[0] - low) / span * 120} r="4" fill="currentColor" />}
      <text x="40" y="179" className="telemetry-axis">{start}</text><text x="460" y="179" textAnchor="end" className="telemetry-axis">{end}</text>
      {!values.length && <text x="250" y="90" textAnchor="middle" className="telemetry-empty">Menunggu riwayat sensor</text>}
    </svg>
  </div>;
}
