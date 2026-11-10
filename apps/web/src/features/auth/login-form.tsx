"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, ArrowRight, Check, Eye, EyeOff, Leaf, LockKeyhole, ShieldCheck, UserRound } from "lucide-react";
import { LoginRadar } from "./login-radar";
import type { AdminSession } from "@/lib/types";
import { requestJSON } from "@/lib/api";

export function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [checking, setChecking] = useState(true);
  const [configured, setConfigured] = useState(true);
  const [error, setError] = useState("");
  const errorRef = useRef<HTMLDivElement>(null);
  const reason = params.get("reason");
  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);
    requestJSON<AdminSession>("/api/auth/session", { signal: controller.signal }).then(session => {
      if (!active) return;
      setConfigured(session.configured);
      if (session.authenticated) router.replace("/monitoring");
    }).catch(() => { if (active) setError("Server belum dapat dihubungi. Pastikan backend Python berjalan, lalu coba masuk lagi."); })
      .finally(() => { clearTimeout(timeout); if (active) setChecking(false); });
    return () => { active = false; clearTimeout(timeout); controller.abort(); };
  }, [router]);
  useEffect(() => { if (error) errorRef.current?.focus(); }, [error]);
  return <main className="login-page"><section className="login-story" aria-label="Smart Office"><a className="brand login-brand" href="/"><span className="brand-symbol"><Leaf size={25} aria-hidden="true" /></span><span>smart<span className="brand-light">office</span><small>WORKSPACE INTELLIGENCE</small></span></a><div className="login-story-content"><span className="login-kicker"><span className="status-dot" />SMART WORKSPACE ANALYTICS</span><h1>Semua data ruang.<br /><em>Satu pandangan jelas.</em></h1><p>Masuk untuk memantau aktivitas ruang, membaca kondisi lingkungan, dan menelusuri riwayat data.</p><LoginRadar /></div><div className="login-story-footer"><ShieldCheck size={19} aria-hidden="true" /><p>AKSES ADMIN <span>/</span> PEMROSESAN LOKAL</p></div></section>
    <section className="login-form-side"><a className="login-backlink" href="/"><ArrowLeft size={15} aria-hidden="true" />Kembali ke beranda</a><div className="login-card"><span className="login-lock"><LockKeyhole size={25} aria-hidden="true" /></span><div className="eyebrow">SELAMAT DATANG KEMBALI</div><h2>Masuk ke ruang kendali.</h2><p>Gunakan akun admin untuk mengelola Smart Office.</p>
      {reason && !error && <div className="login-notice" role="status">{reason === "server" ? "Server belum dapat memverifikasi sesi. Periksa backend, lalu coba masuk kembali." : "Sesi Anda telah berakhir. Silakan masuk kembali."}</div>}
      {!configured && <div className="login-notice"><strong>Siapkan akun admin pertama</strong><p>Di komputer server, jalankan <code>python manage_admin.py</code>, lalu buat nama pengguna dan kata sandi. Setelah selesai, langsung masuk di sini.</p></div>}
      <form onSubmit={async event => {
        event.preventDefault(); if (busy) return; setBusy(true); setError("");
        try {
          await requestJSON("/api/auth/login", { method: "POST", headers: { "X-SmartOffice-Client": "web" }, body: JSON.stringify({ username, password }) });
          setPassword(""); window.location.replace("/monitoring");
        } catch (cause) { setError(cause instanceof Error ? cause.message : "Masuk gagal. Coba lagi."); }
        finally { setBusy(false); }
      }}><label htmlFor="admin-username">Nama pengguna</label><div className="login-input"><UserRound size={18} aria-hidden="true" /><input id="admin-username" name="username" autoComplete="username" placeholder="Masukkan nama pengguna" maxLength={40} required value={username} onChange={event => setUsername(event.target.value)} /></div><label htmlFor="admin-password">Kata sandi</label><div className="login-input"><LockKeyhole size={18} aria-hidden="true" /><input id="admin-password" name="password" type={visible ? "text" : "password"} autoComplete="current-password" placeholder="Masukkan kata sandi" maxLength={128} required value={password} onChange={event => setPassword(event.target.value)} /><button type="button" aria-label={visible ? "Sembunyikan kata sandi" : "Tampilkan kata sandi"} aria-pressed={visible} onClick={() => setVisible(!visible)}>{visible ? <EyeOff size={18} aria-hidden="true" /> : <Eye size={18} aria-hidden="true" />}</button></div>
        {error && <div ref={errorRef} tabIndex={-1} className="action-feedback failed" role="alert">{error}</div>}
        <button className="button login-submit" disabled={busy}>{busy ? "Memverifikasi…" : "Masuk ke dashboard"}<ArrowRight size={18} aria-hidden="true" /></button>
      </form><div className="login-security"><Check size={15} aria-hidden="true" /><span>Sesi admin berakhir otomatis setelah 8 jam.</span></div><details className="login-help"><summary>Tidak bisa masuk?</summary><p>Pastikan server Python aktif. Untuk membuat akun atau mereset kata sandi, jalankan <code>python manage_admin.py</code> di komputer server. {checking && "Memeriksa konfigurasi server…"}</p></details></div><footer className="login-footer">Smart Office <span>YOLOv11 + SCD40</span></footer></section></main>;
}
