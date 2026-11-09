"use client";
export default function ErrorPage({ reset }: { reset: () => void }) { return <div className="empty-state" role="alert"><h1>Halaman belum dapat ditampilkan</h1><p>Coba muat ulang halaman. Data tersimpan tetap dikelola oleh server Python.</p><button className="button" onClick={reset}>Coba lagi</button></div>; }
