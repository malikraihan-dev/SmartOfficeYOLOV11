"use client";
import { useState } from "react";
import { Camera, Check, ImageIcon } from "lucide-react";
import { CameraPanel } from "@/components/camera-panel";
import { ActionFeedback } from "@/components/action-feedback";
import { Badge, ConnectionNotice, DownloadLink, EmptyState, LoadingState, MetricCard, PageHeader, Panel } from "@/components/ui";
import { usePoll } from "@/lib/use-poll";
import { useAction } from "@/lib/use-action";
import { number, timestamp } from "@/lib/api";
import type { VisionEvaluation, VisionSample } from "@/lib/types";

export function VisionDatasetPage() {
  const { data, error, loading, refresh } = usePoll<VisionEvaluation>("/api/evaluation", 10000);
  const [filter, setFilter] = useState("pending");
  const samples = data?.samples.filter(sample => filter === "all" || sample.actual_count === null) ?? [];
  return <><PageHeader eyebrow="DATA & TRAINING / KAMERA" title="Dataset kamera" description="Kumpulkan foto untuk anotasi dan tinjau jumlah orang hasil deteksi." />
    <ConnectionNotice error={error} retry={refresh} />
    <div className="metrics-grid dataset-metrics"><MetricCard label="Sampel ditinjau" value={data ? number(data.reviewed_samples) : "--"} unit="sampel" icon={<Check size={20} />} note="Konfirmasi jumlah secara manual" /><MetricCard label="Ketepatan hitung" value={data ? number(data.count_accuracy_percent, 1) : "--"} unit="%" icon={<Camera size={20} />} note="Jumlah prediksi sama dengan aktual" /><MetricCard label="Menunggu ulasan" value={data ? number(data.pending_count) : "--"} unit="sampel" icon={<ImageIcon size={20} />} note="Pada maksimum 25 sampel yang dimuat" /></div>
    <div className="two-columns"><CameraPanel captureMode /><Panel title="Siapkan anotasi & analisis" description="Dua ekspor untuk kebutuhan yang berbeda"><div className="export-option"><span className="step-label">01 / FOTO ASLI</span><h3>Anotasi objek sebelum training</h3><p>Foto tanpa blur atau overlay. Buat bounding box dan kelas di alat anotasi, lalu ekspor format YOLO untuk notebook training.</p><DownloadLink href="/api/training/export">Unduh ZIP foto asli</DownloadLink></div><div className="export-option"><span className="step-label">02 / DATA EVALUASI</span><h3>Analisis perilaku deteksi</h3><p>Ekspor okupansi, lintasan, kunjungan zona, evaluasi, kualitas frame, dan fitur audio tereduksi. Data ini bukan label bounding box YOLO.</p><DownloadLink href="/api/export/colab">Unduh ZIP analisis Colab</DownloadLink></div></Panel></div>
    <Panel title="Tinjau hasil deteksi" description="Bandingkan prediksi dengan jumlah orang yang benar-benar terlihat." action={<div className="segmented" aria-label="Filter sampel"><button aria-pressed={filter === "pending"} onClick={() => setFilter("pending")}>Belum ditinjau</button><button aria-pressed={filter === "all"} onClick={() => setFilter("all")}>Semua</button></div>}>
      <p className="subtle-note">{data?.metric_note ?? "Ketepatan hitung tersedia setelah sampel memiliki jumlah aktual. Metrik ini bukan mAP model YOLO."}</p>
      {loading && !data ? <LoadingState /> : samples.length ? <div className="review-list">{samples.map(sample => <ReviewSample key={sample.id} sample={sample} refresh={refresh} />)}</div> : <EmptyState title={error ? "Sampel belum dapat dimuat" : "Belum ada sampel untuk ditinjau"}>{error ? "Periksa koneksi ke server Python, lalu coba lagi." : "Sampel evaluasi akan muncul setelah kamera aktif. Gunakan filter Semua untuk melihat sampel yang sudah ditinjau."}</EmptyState>}
    </Panel></>;
}
function ReviewSample({ sample, refresh }: { sample: VisionSample; refresh: () => void }) {
  const [count, setCount] = useState(String(sample.actual_count ?? sample.predicted_count));
  const action = useAction();
  return <form className="review-sample" onSubmit={async event => { event.preventDefault(); if (await action.run(`/api/evaluation/${sample.id}/review`, { actual_count: Number(count) }, "Ulasan tersimpan.")) refresh(); }}>
    <a href={sample.image_url} target="_blank" rel="noreferrer"><img src={sample.image_url} alt={`Sampel deteksi nomor ${sample.id}. Buka gambar penuh untuk meninjau jumlah orang.`} loading="lazy" /></a><div className="sample-info"><h3>Sampel #{sample.id} <Badge tone={sample.actual_count === null ? "amber" : "green"}>{sample.actual_count === null ? "BELUM DITINJAU" : "DITINJAU"}</Badge></h3><p>{sample.predicted_count} orang diprediksi · confidence {number(sample.confidence, 1)}%</p><small>{timestamp(sample.captured_at)}</small><ActionFeedback {...action} /></div><div className="review-controls"><label htmlFor={`count-${sample.id}`}>Jumlah aktual</label><div><input id={`count-${sample.id}`} type="number" min={0} max={100} step={1} required value={count} onChange={event => setCount(event.target.value)} /><button className="button" disabled={action.busy}>{action.busy ? "Menyimpan…" : "Konfirmasi"}</button></div></div>
  </form>;
}
