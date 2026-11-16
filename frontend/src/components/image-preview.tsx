"use client";
import { useId, useRef, useState } from "react";

export function ImagePreview({ src, label }: { src: string; label: string }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const id = useId();
  const [opened, setOpened] = useState(false);
  const [failed, setFailed] = useState(false);
  return <><button type="button" className="image-preview-trigger" aria-label={`Pratinjau ${label}`} onClick={() => { setOpened(true); setFailed(false); dialog.current?.showModal(); }}><img src={src} alt={label} loading="lazy" /><span>Perbesar gambar</span></button>
    <dialog ref={dialog} className="image-preview-dialog" aria-labelledby={id} onClick={event => { if (event.target === event.currentTarget) dialog.current?.close(); }}>
      <header><h2 id={id}>{label}</h2><button type="button" className="button secondary" autoFocus onClick={() => dialog.current?.close()}>Tutup gambar</button></header>
      {opened && (failed ? <p role="status">Gambar belum dapat dimuat. Tutup lalu buka kembali untuk mencoba lagi.</p> : <img src={src} alt={label} onError={() => setFailed(true)} />)}
      <p>Tekan Escape untuk menutup. <a href={src} target="_blank" rel="noreferrer">Buka gambar asli</a></p>
    </dialog>
  </>;
}
