"use client";
import Link from "next/link";
import { useRef, useState } from "react";
import { ArrowUpRight, Leaf, Menu, X } from "lucide-react";
export function PublicHeader() {
  const [open, setOpen] = useState(false);
  const button = useRef<HTMLButtonElement>(null);
  return <header className="public-header" onKeyDown={event => { if (event.key === "Escape") { setOpen(false); button.current?.focus(); } }}><Link className="public-brand" href="/" aria-label="Smart Office — Beranda"><span><Leaf size={23} aria-hidden="true" /></span>smart<span className="public-brand-light">office</span></Link><button ref={button} className="public-menu-button" aria-label={open ? "Tutup navigasi situs" : "Buka navigasi situs"} aria-expanded={open} aria-controls="public-navigation" onClick={() => setOpen(!open)}>{open ? <X size={20} /> : <Menu size={20} />}</button><nav id="public-navigation" className={`public-navigation ${open ? "public-navigation-open" : ""}`} aria-label="Navigasi situs"><a href="#fitur" onClick={() => setOpen(false)}>Fitur</a><a href="#cara-kerja" onClick={() => setOpen(false)}>Cara kerja</a><a href="#harga" onClick={() => setOpen(false)}>Harga</a><Link className="button" href="/login">Masuk admin <ArrowUpRight size={16} aria-hidden="true" /></Link></nav></header>;
}
