"use client";
import { useState, type ReactNode } from "react";
import { CircleHelp, Download, RefreshCw, TriangleAlert } from "lucide-react";

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: "green" | "amber" | "red" | "neutral" }) {
  return <span className={`badge badge-${tone}`}><span className="status-dot" aria-hidden="true" />{children}</span>;
}
export function PageHeader({ eyebrow, title, description, children }: { eyebrow: string; title: string; description: string; children?: ReactNode }) {
  return <header className="page-header"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div><div className="header-actions">{children}</div></header>;
}
export function Panel({ title, description, action, children, className = "" }: { title: string; description?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}><div className="panel-head"><div><h2>{title}</h2>{description && <p>{description}</p>}</div>{action}</div>{children}</section>;
}
export function EmptyState({ title, children }: { title: string; children: ReactNode }) {
  return <div className="empty-state"><CircleHelp size={28} aria-hidden="true" /><h3>{title}</h3><p>{children}</p></div>;
}
export function ConnectionNotice({ error, retry }: { error: string | null; retry: () => void }) {
  if (!error) return null;
  return <div className="connection-notice" role="alert"><TriangleAlert size={20} aria-hidden="true" /><div><strong>Koneksi server terputus</strong><p>{error} Data terakhir, jika ada, bukan status terkini.</p></div><button className="button secondary" onClick={retry}><RefreshCw size={16} aria-hidden="true" />Coba lagi</button></div>;
}
export function DownloadLink({ href, children, secondary = true }: { href: string; children: ReactNode; secondary?: boolean }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  return <span className="download-action"><a className={`button ${secondary ? "secondary" : ""}`} href={href} aria-disabled={busy} onClick={async event => {
    event.preventDefault(); if (busy) return;
    setBusy(true); setError("");
    try {
      const response = await fetch(href, { cache: "no-store", signal: AbortSignal.timeout(60000) });
      if (!response.ok) { const body = await response.json().catch(() => null); throw new Error(body?.message ?? `Unduhan gagal (HTTP ${response.status}). Coba lagi.`); }
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a"); link.href = url;
      link.download = response.headers.get("Content-Disposition")?.match(/filename="?([^";]+)"?/)?.[1] ?? "smartoffice-export";
      document.body.appendChild(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 30000);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unduhan gagal. Periksa koneksi dan coba lagi."); }
    finally { setBusy(false); }
  }}><Download size={16} aria-hidden="true" />{busy ? "Menyiapkan unduhan…" : children}</a>{error && <span className="download-error" role="alert">{error}</span>}</span>;
}
export function MetricCard({ label, value, unit, icon, note, badge }: { label: string; value: string; unit?: string; icon: ReactNode; note: string; badge?: ReactNode }) {
  return <section className="metric-card"><div className="metric-top"><span>{label}</span><span className="metric-icon" aria-hidden="true">{icon}</span></div><div className="metric-value">{value}<span>{unit}</span></div><div className="metric-bottom"><small>{note}</small>{badge}</div></section>;
}
export function LoadingState() { return <div className="loading-state" role="status"><span className="spinner" />Memuat data dari server…</div>; }
