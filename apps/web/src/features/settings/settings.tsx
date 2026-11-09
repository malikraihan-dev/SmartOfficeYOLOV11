"use client";
import { useEffect, useRef, useState } from "react";
import { AudioLines, Check, Radio, Settings2, Trash2 } from "lucide-react";
import { useOffice } from "@/components/office-provider";
import { ActionFeedback } from "@/components/action-feedback";
import { Badge, ConnectionNotice, EmptyState, LoadingState, PageHeader, Panel } from "@/components/ui";
import { number, sensorState, timestamp } from "@/lib/api";
import { useAction } from "@/lib/use-action";
import { usePoll } from "@/lib/use-poll";
import type { AudioEvaluation, OfficeStatus, Zone } from "@/lib/types";

export function SettingsPage() {
  const { data, error, refresh } = useOffice();
  return <><PageHeader eyebrow="PUSAT KENDALI / PENGATURAN" title="Pengaturan ruang kerja" description="Sesuaikan deteksi, zona kerja, koneksi perangkat, dan audio." /><ConnectionNotice error={error} retry={refresh} />
    <div className="two-columns"><DetectionSettings status={data} unavailable={!!error} refresh={refresh} /><div className="stack"><Panel title="Koneksi sensor" description="SCD40 melalui ESP32" action={<Radio size={20} aria-hidden="true" />}><div className="source-row"><div><strong>Sensor ruangan</strong><small>{timestamp(data?.sensor_updated_at, true)}</small></div><Badge tone={sensorState(data, !!data && !error) === "LIVE" ? "green" : "amber"}>{sensorState(data, !!data && !error)}</Badge></div><p className="muted">ESP32 dan server harus berada di jaringan yang sama. Ganti IP pada firmware dengan alamat komputer Python.</p><label className="code-label">Endpoint pada server Python</label><code className="endpoint">POST http://&lt;IP-server&gt;:5000/api/scd40</code><pre className="payload">{`{\n  "co2_ppm": 720,\n  "temperature_c": 25.4,\n  "humidity_percent": 52.3\n}`}</pre><p className="subtle-note">Satu sensor / satu ruangan. Autentikasi perangkat belum tersedia pada prototipe lokal.</p></Panel><AudioSettings status={data} unavailable={!!error} refresh={refresh} /></div></div>
    <AudioReview /><DataManagement refresh={refresh} />
  </>;
}
function DetectionSettings({ status, unavailable, refresh }: { status: OfficeStatus | null; unavailable: boolean; refresh: () => void }) {
  const [confidence, setConfidence] = useState(35);
  const [zone, setZone] = useState<Zone>({ x1: 12, y1: 15, x2: 88, y2: 92 });
  const [initialized, setInitialized] = useState(false);
  const [validation, setValidation] = useState("");
  const action = useAction();
  useEffect(() => {
    if (status && !initialized) { setConfidence(Math.round(status.detection_confidence_threshold * 100)); setZone(Object.fromEntries(Object.entries(status.zone_config).map(([key, value]) => [key, Math.round(value * 100)])) as Zone); setInitialized(true); }
  }, [status, initialized]);
  return <Panel title="Deteksi & zona kerja" description="Ambang confidence dan batas area pemantauan" action={<Settings2 size={20} aria-hidden="true" />}>
    <form onSubmit={async event => { event.preventDefault(); setValidation(""); if (zone.x2 - zone.x1 < 10 || zone.y2 - zone.y1 < 10) { setValidation("Lebar dan tinggi zona harus minimal 10%. Periksa batas kiri, kanan, atas, dan bawah."); return; } if (await action.run("/api/detection/settings", { confidence: confidence / 100, zone: Object.fromEntries(Object.entries(zone).map(([key, value]) => [key, value / 100])) })) refresh(); }}>
      <div className="zone-preview" aria-label={`Pratinjau zona: kiri ${zone.x1}%, atas ${zone.y1}%, kanan ${zone.x2}%, bawah ${zone.y2}%.`} role="img"><div className="zone-boundary" style={{ left: `${zone.x1}%`, top: `${zone.y1}%`, width: `${Math.max(0, zone.x2 - zone.x1)}%`, height: `${Math.max(0, zone.y2 - zone.y1)}%` }}><span>ZONA KERJA</span></div><span className="zone-caption">Batas relatif terhadap frame kamera</span></div>
      <div className="range-control"><label htmlFor="confidence">Ambang confidence <output>{confidence}%</output></label><input id="confidence" type="range" min={10} max={90} value={confidence} onChange={event => setConfidence(Number(event.target.value))} /></div>
      <div className="zone-fields">{([['x1', 'Batas kiri'], ['y1', 'Batas atas'], ['x2', 'Batas kanan'], ['y2', 'Batas bawah']] as const).map(([key, label]) => <div className="range-control" key={key}><label htmlFor={`zone-${key}`}>{label} <output>{zone[key]}%</output></label><input type="range" id={`zone-${key}`} min={0} max={100} value={zone[key]} onChange={event => setZone({ ...zone, [key]: Number(event.target.value) })} /></div>)}</div>
      {validation && <p className="action-feedback failed" role="alert">{validation}</p>}<ActionFeedback {...action} /><button className="button" disabled={!initialized || unavailable || action.busy}><Check size={16} aria-hidden="true" />{action.busy ? "Menyimpan…" : "Terapkan pengaturan"}</button><p className="subtle-note">Pengaturan berlaku pada proses server saat ini dan kembali ke default setelah server dimulai ulang.</p>
    </form>
  </Panel>;
}
function AudioSettings({ status, unavailable, refresh }: { status: OfficeStatus | null; unavailable: boolean; refresh: () => void }) {
  const [threshold, setThreshold] = useState(-42);
  const [initialized, setInitialized] = useState(false);
  const action = useAction();
  useEffect(() => { if (status && !initialized) { setThreshold(status.audio_threshold_dbfs); setInitialized(true); } }, [status, initialized]);
  return <Panel title="Audio ruangan" description="Energi suara · bukan pengenalan ucapan" action={<AudioLines size={20} aria-hidden="true" />}><p className="muted">{status?.audio_status ?? "Menunggu status mikrofon"} · segmen 10 detik. Audio mentah tidak disimpan.</p><form onSubmit={async event => { event.preventDefault(); await action.run("/api/audio/threshold", { threshold_dbfs: threshold }, "Ambang audio diperbarui."); refresh(); }}><div className="range-control"><label htmlFor="audio-threshold">Ambang audio <output>{threshold} dBFS</output></label><input id="audio-threshold" type="range" min={-80} max={-10} value={threshold} onChange={event => setThreshold(Number(event.target.value))} /></div><div className="button-row"><button className="button secondary" disabled={!initialized || unavailable || action.busy}>Simpan ambang</button><button type="button" className="button secondary" disabled={action.busy || unavailable || !status?.audio_available} onClick={async () => { await action.run("/api/audio/calibrate", undefined, "Kalibrasi diminta. Tunggu dua segmen 10 detik."); refresh(); }}>Kalibrasi ulang</button></div><ActionFeedback {...action} /></form></Panel>;
}
function AudioReview() {
  const { data, error, loading, refresh } = usePoll<AudioEvaluation>("/api/audio/evaluation", 10000);
  const action = useAction();
  return <Panel title="Evaluasi noise / hening" description="Bandingkan label prediksi dengan konfirmasi manual" action={<Badge>{data ? number(data.reviewed_samples) : "--"} ditinjau</Badge>}><ConnectionNotice error={error} retry={refresh} /><p className="muted">Akurasi label manual: <strong>{number(data?.accuracy_percent, 1)}{data?.accuracy_percent != null ? "%" : ""}</strong>. Noise menandai energi di atas ambang, bukan identitas atau isi ucapan.</p>
    {data && data.reviewed_samples > 0 && <div className="audio-metrics">{Object.entries(data.class_metrics).map(([label, metric]) => <span key={label}><strong>{label === "noise" ? "Noise" : "Hening"}</strong> P {number(metric.precision_percent, 1)}% · R {number(metric.recall_percent, 1)}% · F1 {number(metric.f1_percent, 1)}% · n={metric.support}</span>)}</div>}
    <ActionFeedback {...action} />{loading && !data ? <LoadingState /> : data?.samples.length ? <div className="audio-review-list">{data.samples.map(sample => <div key={sample.id} className="audio-review-row"><div><strong>{sample.predicted_label === "noise" ? "Noise" : "Hening"} · {number(sample.level_dbfs, 1)} dBFS</strong><small>{timestamp(sample.sampled_at, true)}</small></div>{sample.actual_label ? <Badge tone="green">Aktual: {sample.actual_label === "noise" ? "noise" : "hening"}</Badge> : <div className="button-row">{([['noise', 'Noise'], ['quiet', 'Hening']] as const).map(([label, text]) => <button key={label} className="button secondary small" disabled={action.busy || !!error} aria-label={`Tandai sampel audio ${sample.id} sebagai ${text}`} onClick={async () => { if (await action.run(`/api/audio/review/${sample.id}`, { actual_label: label }, "Label audio tersimpan.")) refresh(); }}>{text}</button>)}</div>}</div>)}</div> : <EmptyState title="Belum ada segmen audio">{data?.available ? "Tunggu segmen mikrofon berikutnya." : "Pastikan sounddevice dan perangkat input audio tersedia pada server Python."}</EmptyState>}
  </Panel>;
}
function DataManagement({ refresh }: { refresh: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const action = useAction();
  const [confirmation, setConfirmation] = useState("");
  return <section className="danger-panel"><div><h2>Kelola data kamera & audio</h2><p>Hapus riwayat evaluasi, lintasan, kunjungan zona, sampel audio, snapshot, dan foto dataset kamera. Riwayat sensor SCD40 tidak ikut dihapus.</p><ActionFeedback {...action} /></div><button className="button danger" onClick={() => { setConfirmation(""); dialog.current?.showModal(); }}><Trash2 size={16} aria-hidden="true" />Hapus data kamera & audio</button><dialog ref={dialog} className="confirm-dialog" aria-labelledby="delete-title"><form onSubmit={async event => { event.preventDefault(); if (confirmation !== "HAPUS") return; if (await action.run("/api/data/clear", undefined, "Data kamera dan audio dihapus. Riwayat sensor tetap tersimpan.")) { dialog.current?.close(); refresh(); } }}><span className="danger-dialog-icon"><Trash2 size={24} aria-hidden="true" /></span><h2 id="delete-title">Hapus data kamera & audio?</h2><p>Tindakan ini tidak dapat dibatalkan. Unduh ZIP analisis dan foto sebelum menghapusnya. Pengumpulan baru berlanjut selama kamera atau audio aktif.</p><p><strong>Riwayat sensor SCD40 tetap tersimpan.</strong></p><label htmlFor="delete-confirm">Ketik HAPUS untuk mengonfirmasi</label><input id="delete-confirm" autoComplete="off" value={confirmation} onChange={event => setConfirmation(event.target.value)} required /><ActionFeedback {...action} /><div className="button-row"><button type="button" autoFocus className="button secondary" disabled={action.busy} onClick={() => dialog.current?.close()}>Batal</button><button className="button danger" disabled={confirmation !== "HAPUS" || action.busy}>{action.busy ? "Menghapus…" : "Hapus permanen"}</button></div></form></dialog></section>;
}
