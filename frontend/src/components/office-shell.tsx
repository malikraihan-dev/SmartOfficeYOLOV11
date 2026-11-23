"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Building2, Camera, ChevronRight, Cpu, Database, LayoutDashboard, Leaf, LogOut, Menu, PanelLeftClose, PanelLeftOpen, Settings2, ShieldCheck, X } from "lucide-react";
import { postJSON } from "@/lib/api";

const links = [
  { href: "/monitoring", label: "Monitoring", caption: "Aktivitas & kondisi ruang", icon: LayoutDashboard },
  { href: "/datasets/sensors", label: "Dataset sensor", caption: "Riwayat & ekspor SCD40", icon: Database },
  { href: "/datasets/vision", label: "Dataset kamera", caption: "Foto & evaluasi deteksi", icon: Camera },
  { href: "/models", label: "Model", caption: "Artefak & validasi", icon: Cpu },
  { href: "/settings", label: "Pengaturan", caption: "Perangkat & zona kerja", icon: Settings2 },
];

export function OfficeShell({ children, username }: { children: React.ReactNode; username: string }) {
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [mobile, setMobile] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState("");
  const sidebar = useRef<HTMLElement>(null);
  const menuButton = useRef<HTMLButtonElement>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const expandedRef = useRef(false);
  const keyboardMode = useRef(false);
  const pointerNear = useRef(false);
  function cancelClose() { if (closeTimer.current) clearTimeout(closeTimer.current); closeTimer.current = null; }
  function expand() { cancelClose(); expandedRef.current = true; setExpanded(true); }
  function collapse() { expandedRef.current = false; setExpanded(false); }
  function scheduleClose() {
    if (closeTimer.current) return;
    closeTimer.current = setTimeout(() => {
      closeTimer.current = null;
      if (!keyboardMode.current || !sidebar.current?.contains(document.activeElement)) collapse();
    }, 240);
  }
  useEffect(() => {
    const narrow = window.matchMedia("(max-width: 760px)");
    const hover = window.matchMedia("(hover: hover) and (pointer: fine)");
    const sync = () => { setMobile(narrow.matches); setOpen(false); collapse(); };
    const move = (event: PointerEvent) => {
      if (narrow.matches || !hover.matches || event.pointerType === "touch") return;
      pointerNear.current = event.clientX <= (expandedRef.current ? 292 : 108);
      if (pointerNear.current) expand(); else scheduleClose();
    };
    const key = (event: KeyboardEvent) => { if (event.key === "Tab") keyboardMode.current = true; };
    const pointerDown = () => { keyboardMode.current = false; };
    sync(); narrow.addEventListener("change", sync);
    window.addEventListener("pointermove", move, { passive: true });
    window.addEventListener("keydown", key); window.addEventListener("pointerdown", pointerDown);
    return () => { cancelClose(); narrow.removeEventListener("change", sync); window.removeEventListener("pointermove", move); window.removeEventListener("keydown", key); window.removeEventListener("pointerdown", pointerDown); };
  }, []);
  useEffect(() => { if (open && mobile) sidebar.current?.querySelector<HTMLButtonElement>("button")?.focus(); }, [open, mobile]);
  function closeMenu() { setOpen(false); menuButton.current?.focus(); }
  const current = links.find(link => path.startsWith(link.href));
  return <div className={`office-shell ${expanded ? "navigation-expanded" : ""}`}>
    <a className="skip-link" href="#main">Lewati navigasi</a>
    <aside ref={sidebar} className={`sidebar ${open ? "sidebar-open" : ""} ${expanded ? "is-expanded" : ""}`} data-expanded={expanded} aria-label="Navigasi utama" inert={mobile && !open} role={mobile ? "dialog" : undefined} aria-modal={mobile && open ? true : undefined}
      onFocusCapture={() => { if (!mobile && keyboardMode.current) expand(); }}
      onBlurCapture={event => { if (!mobile && !sidebar.current?.contains(event.relatedTarget as Node) && !pointerNear.current) scheduleClose(); }}
      onKeyDown={event => {
        if (event.key === "Escape") { event.preventDefault(); if (mobile) closeMenu(); else { keyboardMode.current = false; collapse(); } }
        if (!mobile || !open || event.key !== "Tab") return;
        const nodes = sidebar.current?.querySelectorAll<HTMLElement>("a[href], button");
        if (!nodes?.length) return;
        const first = nodes[0], last = nodes[nodes.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }}>
      <button className="sidebar-close icon-button" aria-label="Tutup navigasi" onClick={closeMenu}><X size={20} aria-hidden="true" /></button>
      <Link className="brand" href="/monitoring" aria-label="Smart Office — Monitoring" onClick={() => setOpen(false)}><span className="brand-symbol"><Leaf size={25} aria-hidden="true" /></span><span className="brand-wordmark">smart<span className="brand-light">office</span><small>WORKSPACE INTELLIGENCE</small></span></Link>
      <div className="workspace-label"><span>KENDALI RUANG</span><button className="rail-toggle" aria-label={expanded ? "Ringkas navigasi" : "Perluas navigasi"} aria-expanded={expanded} onClick={() => expanded ? collapse() : expand()}>{expanded ? <PanelLeftClose size={17} /> : <PanelLeftOpen size={17} />}</button></div>
      <nav>{links.map(({ href, label, caption, icon: Icon }, index) => <Link href={href} key={href} aria-label={label} title={!expanded && !mobile ? label : undefined} onClick={() => setOpen(false)} className={`nav-link ${path.startsWith(href) ? "active" : ""}`} aria-current={path.startsWith(href) ? "page" : undefined}><Icon size={21} aria-hidden="true" /><span className="nav-copy"><span>{label}</span><small>{caption}</small></span><span className="nav-number" aria-hidden="true">0{index + 1}</span></Link>)}</nav>
      <div className="sidebar-bottom"><div className="sidebar-note"><span className="sidebar-note-icon"><ShieldCheck size={20} aria-hidden="true" /></span><strong>Ruang kendali admin</strong><p>Akses perangkat, dataset, dan konfigurasi dalam satu tempat.</p></div><div className="installation"><span className="installation-icon"><Building2 size={19} aria-hidden="true" /></span><div className="installation-copy"><strong>Instalasi lokal</strong><small>Satu sensor · satu ruangan</small></div></div></div>
    </aside>
    {open && <div className="nav-scrim" aria-hidden="true" onClick={closeMenu} />}
    <div className="main-shell"><div className="topbar"><div className="breadcrumbs"><button ref={menuButton} className="icon-button menu-button" aria-label={open ? "Tutup menu" : "Buka menu"} aria-expanded={open} onClick={() => setOpen(!open)}>{open ? <X size={20} /> : <Menu size={20} />}</button><span>Ruang kerja</span><ChevronRight size={14} aria-hidden="true" /><strong>{current?.label ?? "Smart Office"}</strong></div><div className="admin-toolbar"><span className="local-context"><span className="status-dot" />KONSOL LOKAL</span><div className="admin-identity"><span className="admin-avatar" aria-hidden="true">{username.slice(0, 1).toUpperCase()}</span><div><strong>{username}</strong><small>Administrator</small></div></div><button className="logout-button" aria-label="Keluar dari akun admin" title="Keluar dari akun admin" disabled={loggingOut} onClick={async () => { setLoggingOut(true); setLogoutError(""); try { await postJSON("/api/auth/logout"); window.location.replace("/login"); } catch { setLogoutError("Belum dapat keluar. Periksa koneksi server lalu coba lagi."); setLoggingOut(false); } }}><LogOut size={18} aria-hidden="true" /></button></div></div>
      <main id="main" tabIndex={-1} inert={mobile && open}>{logoutError && <p className="action-feedback failed" role="alert">{logoutError}</p>}{children}</main>
      <footer className="page-footer"><span>Smart Office <span className="footer-dot">·</span> YOLOv11 & SCD40</span><span>Admin console <span className="footer-dot">/</span> Satu ruang, satu pusat kendali.</span></footer>
    </div>
  </div>;
}
