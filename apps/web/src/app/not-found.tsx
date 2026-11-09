import Link from "next/link";
export default function NotFound() { return <div className="empty-state"><h1>Halaman tidak ditemukan</h1><p>Pilih halaman dari navigasi atau kembali ke monitoring.</p><Link href="/monitoring" className="button">Buka monitoring</Link></div>; }
