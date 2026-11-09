"use client";
import { useState } from "react";
import { Camera, Pause, Play, RefreshCw, ScanLine } from "lucide-react";
import { useOffice } from "./office-provider";
import { Badge, Panel } from "./ui";
import { ActionFeedback } from "./action-feedback";
import { cameraLive, number, timestamp } from "@/lib/api";
import { useAction } from "@/lib/use-action";

export function CameraPanel({ captureMode = false }: { captureMode?: boolean }) {
  const { data, error, refresh } = useOffice();
  const [streamPaused, setStreamPaused] = useState(false);
  const [streamError, setStreamError] = useState(false);
  const [streamKey, setStreamKey] = useState(0);
  const [loaded, setLoaded] = useState(false);
  const action = useAction();
  const live = cameraLive(data, !error) && !streamPaused && !streamError;
  async function reconnect() {
    const result = await action.run("/api/camera/reconnect", undefined, "Permintaan dikirim. Kamera sedang mencoba terhubung kembali.");
    if (result) { setStreamError(false); setLoaded(false); setStreamPaused(false); setStreamKey(n => n + 1); refresh(); }
  }
  return <Panel title={captureMode ? "Siapkan gambar dataset" : "Kamera langsung"} description="YOLOv11 · deteksi orang & objek" className="camera-panel" action={<Badge tone={live ? "green" : "neutral"}>{live ? "LIVE" : streamPaused ? "DIJEDA" : "MENUNGGU"}</Badge>}>
    <div className="camera-stage">
      {!streamPaused && !streamError && <img key={streamKey} src={`/video_feed?session=${streamKey}`} alt="Video langsung kamera ruang kerja dengan hasil deteksi YOLOv11" className={loaded ? "camera-stream loaded" : "camera-stream"} onLoad={() => setLoaded(true)} onError={() => { setStreamError(true); setLoaded(false); }} />}
      {(!loaded || streamPaused || streamError) && <div className="camera-empty"><div className="camera-grid" aria-hidden="true" /><span className="camera-empty-icon"><ScanLine size={38} strokeWidth={1.3} aria-hidden="true" /></span><h3>{streamPaused ? "Pratinjau dijeda" : streamError ? "Kamera belum dapat ditampilkan" : "Menunggu kamera terhubung"}</h3><p>{streamPaused ? "Lanjutkan pratinjau untuk melihat aktivitas ruang." : "Pastikan kamera tersedia dan server Python berjalan."}</p>{streamError && <button className="button camera-retry" disabled={action.busy} onClick={reconnect}>Coba sambungkan ulang</button>}<span className="camera-corner corner-tl" aria-hidden="true" /><span className="camera-corner corner-br" aria-hidden="true" /></div>}
      <div className="camera-overlay"><span><span className={`status-dot ${live ? "live-dot" : ""}`} />{live ? "Kamera ruang kerja" : "Sumber kamera lokal"}</span><button className="camera-control" aria-label={streamPaused ? "Lanjutkan pratinjau kamera" : "Jeda pratinjau kamera"} onClick={() => { setStreamPaused(!streamPaused); setLoaded(false); setStreamError(false); }}>{streamPaused ? <Play size={16} /> : <Pause size={16} />}</button></div>
    </div>
    <div className="camera-toolbar"><span><i className="status-dot" />{data?.dark_frame ? "Frame gelap · deteksi dilewati" : data?.camera_status ?? "Menyiapkan koneksi"}</span><span>{live ? number(data?.camera_fps, 1) : "--"} FPS <span className="separator">/</span> {live ? number(data?.inference_ms, 1) : "--"} ms</span></div>
    <div className="camera-actions"><button className="button secondary" onClick={reconnect} disabled={action.busy}><RefreshCw size={16} aria-hidden="true" />Sambungkan ulang</button><button className="button" disabled={action.busy || !live} onClick={async () => {
      await action.run(captureMode ? "/api/training/capture" : "/api/snapshot", undefined, captureMode ? "Foto asli tersimpan untuk anotasi. Foto tidak memiliki blur atau overlay." : "Snapshot berhasil disimpan."); refresh();
    }}><Camera size={16} aria-hidden="true" />{action.busy ? "Memproses…" : captureMode ? "Simpan foto asli" : "Ambil snapshot"}</button></div>
    <ActionFeedback {...action} /><div className="camera-timestamp">Frame terakhir: {timestamp(data?.last_frame_at, true)}{captureMode && <p>Foto dataset disimpan tanpa blur wajah. Arahkan kamera hanya ke objek yang akan dianotasi.</p>}</div>
  </Panel>;
}
