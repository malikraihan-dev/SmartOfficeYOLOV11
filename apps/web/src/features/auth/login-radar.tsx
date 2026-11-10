"use client";

import { useEffect, useState } from "react";
import { Pause, Play } from "lucide-react";

export function LoginRadar() {
  const [paused, setPaused] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => setReducedMotion(media.matches);
    sync();
    media.addEventListener("change", sync);
    return () => media.removeEventListener("change", sync);
  }, []);

  return <section className="login-radar" aria-label="Ilustrasi radar pemantauan ruang">
    <div className="radar-heading"><span>PEMANTAUAN RUANG</span><span className="radar-demo">ILUSTRASI</span></div>
    <div className="radar-field" data-paused={paused || reducedMotion} aria-hidden="true">
      <div className="radar-ring radar-ring-inner" /><div className="radar-ring radar-ring-middle" /><div className="radar-ring radar-ring-outer" />
      <div className="radar-cross radar-cross-horizontal" /><div className="radar-cross radar-cross-vertical" />
      <div className="radar-sweep" /><span className="radar-center" />
      <span className="radar-point radar-point-one" /><span className="radar-point radar-point-two" /><span className="radar-point radar-point-three" />
      <span className="radar-angle">90°</span>
    </div>
    <div className="radar-footer"><p>{reducedMotion ? "Tampilan statis sesuai preferensi gerak." : "Sapuan 90° · ilustrasi, bukan data perangkat."}</p>
      <button type="button" disabled={reducedMotion} aria-label={paused ? "Lanjutkan animasi radar" : "Jeda animasi radar"} onClick={() => setPaused(value => !value)}>
        {paused || reducedMotion ? <Play size={16} aria-hidden="true" /> : <Pause size={16} aria-hidden="true" />}<span>{reducedMotion ? "Statis" : paused ? "Lanjutkan" : "Jeda"}</span>
      </button>
    </div>
  </section>;
}
