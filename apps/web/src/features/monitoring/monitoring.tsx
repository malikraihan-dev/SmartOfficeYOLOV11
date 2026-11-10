"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { ArrowDownToLine, ArrowRight, AudioLines, Droplets, Leaf, Pause, Play, Thermometer, Users, Wind } from "lucide-react";
import { useOffice } from "@/components/office-provider";
import { Badge, ConnectionNotice, EmptyState, LoadingState, MetricCard, PageHeader, Panel } from "@/components/ui";
import { CameraPanel } from "@/components/camera-panel";
import { LiveTelemetry } from "./live-telemetry";
import { cameraLive, number, sensorState, timestamp } from "@/lib/api";

export function Monitoring() {
  const { data, error, loading, updatedAt, refresh, paused, setPaused } = useOffice();
  const source = paused ? "DIJEDA" : sensorState(data, !error && !!data);
  const live = cameraLive(data, !error && !paused);
  const [points, setPoints] = useState<{ count: number; at: string }[]>([]);
  const [activityHistory, setActivityHistory] = useState<{ label: string; at: string }[]>([]);
  useEffect(() => {
    if (data && updatedAt && cameraLive(data, !error && !paused) && !data.dark_frame) {
      setPoints(previous => previous.at(-1)?.at === updatedAt ? previous : [...previous.slice(-29), { count: data.person_count, at: updatedAt }]);
      setActivityHistory(previous => previous[0]?.label === data.visual_activity ? previous : [{ label: data.visual_activity, at: updatedAt }, ...previous].slice(0, 6));
    }
  }, [data, updatedAt, error, paused]);
  const sensorNote = source === "DEMO" ? "Simulasi · bukan data alat" : source === "LIVE" ? "Pembacaan SCD40 terbaru" : "Pembacaan belum dapat dipercaya";
  const sensorValue = (value: number | null | undefined, digits = 0) => !error && data ? number(value, digits) : "--";
  return <div className="monitoring-page">
    <PageHeader eyebrow="PUSAT KENDALI / MONITORING" title="Monitoring ruang kerja" description="Pantau okupansi, aktivitas, dan kondisi ruang dari sumber yang jelas.">
      <button className="button secondary" onClick={() => setPaused(!paused)}>{paused ? <Play size={16} aria-hidden="true" /> : <Pause size={16} aria-hidden="true" />}{paused ? "Lanjutkan pembaruan" : "Jeda pembaruan"}</button>
    </PageHeader>
    <ConnectionNotice error={error} retry={refresh} />
    {paused && <div className="info-notice" role="status">Pembaruan status dijeda. Angka yang terlihat adalah pembacaan terakhir; pratinjau kamera memiliki kontrol jeda terpisah.</div>}
    <div className="section-label"><h2>Ringkasan ruang</h2><span>{loading && !data ? "Mengambil status…" : updatedAt ? `Diperiksa ${timestamp(updatedAt, true)}` : "Menunggu server"}</span></div>
    <div className="metrics-grid">
      <MetricCard label="Okupansi ruang" value={live ? number(data?.person_count) : "--"} unit="orang" icon={<Users size={21} />} note={live ? "Terdeteksi dari kamera" : "Menunggu frame terbaru"} badge={<Badge tone={live ? "green" : "neutral"}>{live ? "LIVE" : "MENUNGGU"}</Badge>} />
      <MetricCard label="Karbon dioksida" value={sensorValue(data?.co2_ppm)} unit="ppm" icon={<Wind size={21} />} note={sensorNote} badge={<Badge tone={source === "LIVE" ? "green" : "amber"}>{source}</Badge>} />
      <MetricCard label="Suhu ruangan" value={sensorValue(data?.temperature_c, 1)} unit="°C" icon={<Thermometer size={21} />} note={sensorNote} />
      <MetricCard label="Kelembapan" value={sensorValue(data?.humidity_percent, 1)} unit="%" icon={<Droplets size={21} />} note={sensorNote} />
    </div>
    {loading && !data && <LoadingState />}
    <div className="monitoring-grid"><div className="stack"><CameraPanel />
      <Panel title="Snapshot terbaru" description="Cuplikan otomatis dan manual" action={<Badge>{number(data?.snapshots?.length ?? 0)} tersimpan</Badge>}>
        {data?.snapshots?.length ? <div className="snapshot-grid">{data.snapshots.slice(0, 4).map(snapshot => <a className="snapshot" href={snapshot.url} key={snapshot.url} target="_blank" rel="noreferrer"><img src={snapshot.url} alt={`Snapshot ${snapshot.person_count} orang, ${timestamp(snapshot.captured_at)}`} loading="lazy" /><div><strong>{snapshot.person_count} orang <span>{snapshot.trigger}</span></strong><small>{timestamp(snapshot.captured_at, true)}</small><span className="snapshot-open">Lihat gambar <ArrowRight size={13} aria-hidden="true" /></span></div></a>)}</div> : <EmptyState title="Belum ada snapshot">Cuplikan akan muncul saat kamera mendeteksi orang atau Anda mengambil snapshot.</EmptyState>}
      </Panel><Panel title="Riwayat aktivitas" description="Perubahan yang teramati selama halaman dibuka">{activityHistory.length ? <ol className="activity-history">{activityHistory.map(item => <li key={item.at}><span className="status-dot" aria-hidden="true" /><div><strong>{item.label}</strong><small>{timestamp(item.at, true)}</small></div></li>)}</ol> : <p className="muted">Belum ada aktivitas dari frame kamera terbaru.</p>}</Panel></div><div className="stack">
      <section className="activity-card"><div className="activity-icon"><Leaf size={22} aria-hidden="true" /></div><span className="eyebrow">AKTIVITAS SAAT INI</span><h2>{live ? data?.visual_activity : "Menunggu kamera"}</h2><p>{live ? data?.final_validation : "Aktivitas akan terbaca setelah frame kamera terbaru tersedia."}</p><div className="activity-stats"><div><strong>{live ? number(data?.zone_duration_sec) : "--"}<small> dtk</small></strong><span>Durasi di zona</span></div><div><strong>{data && !error ? number(data.zone_entries_today) : "--"}</strong><span>Masuk hari ini</span></div><div><strong>{data && !error ? number(data.zone_exits_today) : "--"}</strong><span>Keluar hari ini</span></div></div></section>
      <Panel title="Tren okupansi" description="Maksimum 30 pembacaan selama halaman dibuka">
        {points.length > 1 ? <OccupancyChart points={points} /> : <div className="chart-empty"><span className="chart-guide" /><span className="chart-guide" /><span className="chart-guide" /><p>Grafik menunggu dua pembacaan kamera.</p></div>}
      </Panel>
      <Panel title="Sumber pembacaan" description="Status perangkat, bukan penilaian kenyamanan">
        <div className="source-row"><span className="source-icon"><Wind size={19} aria-hidden="true" /></span><div><strong>Sensor SCD40</strong><small>{timestamp(data?.sensor_updated_at, true)}</small></div><Badge tone={source === "LIVE" ? "green" : "amber"}>{source}</Badge></div>
        <div className="source-row"><span className="source-icon"><AudioLines size={19} aria-hidden="true" /></span><div><strong>Audio ruangan</strong><small>{!error && data ? `${data.audio_label} · ${number(data.audio_level_dbfs, 1)} dBFS` : "Menunggu pembacaan"}</small></div><Badge tone={data?.audio_available && !error ? "green" : "neutral"}>{data?.audio_available && !error ? "TERSEDIA" : "BELUM ADA"}</Badge></div>
        <Link className="text-link" href="/settings">Pengaturan perangkat <ArrowRight size={15} aria-hidden="true" /></Link>
      </Panel>
      <Panel title="Objek terdeteksi" description="Dari frame kamera terbaru">{live && data?.desk_objects.length ? <div className="object-tags">{data.desk_objects.map((object, index) => <span key={`${object}-${index}`}>{object}</span>)}</div> : <p className="muted">Belum ada objek dari frame terbaru.</p>}</Panel>
    </div></div>
    <LiveTelemetry />
    <div className="dataset-callout"><span className="callout-icon"><ArrowDownToLine size={22} aria-hidden="true" /></span><div><h2>Dari pembacaan menjadi pengetahuan.</h2><p>Kelola riwayat sensor dan siapkan data untuk training di Colab.</p></div><Link className="button secondary" href="/datasets/sensors">Buka dataset sensor <ArrowRight size={16} aria-hidden="true" /></Link></div>
  </div>;
}
function OccupancyChart({ points }: { points: { count: number; at: string }[] }) {
  const max = Math.max(2, ...points.map(point => point.count));
  const line = points.map((point, i) => `${i * 400 / (points.length - 1)},${100 - point.count / max * 85}`).join(" ");
  return <div className="occupancy-chart"><svg viewBox="0 0 400 110" role="img" aria-label={`Tren okupansi dari ${points[0].count} ke ${points.at(-1)?.count} orang; maksimum ${max} orang.`}><path d="M0 15H400M0 57H400M0 100H400" className="chart-grid" /><polygon points={`0,100 ${line} 400,100`} className="chart-area" /><polyline points={line} className="chart-line" /></svg><div className="chart-caption"><span>{timestamp(points[0].at, true)}</span><strong>{points.at(-1)?.count} orang</strong></div><details><summary>Data grafik</summary><ol className="chart-data">{points.map(point => <li key={point.at}>{timestamp(point.at, true)}: {point.count} orang</li>)}</ol></details></div>;
}
