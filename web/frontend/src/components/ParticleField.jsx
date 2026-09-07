import { useEffect, useRef } from "react";
const COLORS = ["#8b7bff", "#a855f7", "#d63cf0", "#c084fc", "#6d8bff"];
export function ParticleField() {
  const ref = useRef(null);
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const reduce = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let W = 0;
    let H = 0;
    let particles = [];
    let raf = 0;
    let t = 0;
    // Spawn at the bottom edge (fresh) or scattered across the field (initial fill).
    const spawn = (fresh) => ({
      x: Math.random() * W,
      y: fresh ? H + Math.random() * 30 : Math.random() * H,
      r: Math.random() * 1.6 + 0.6,
      vy: Math.random() * 0.4 + 0.15,
      phase: Math.random() * Math.PI * 2,
      amp: Math.random() * 0.5 + 0.15,
      color: COLORS[(Math.random() * COLORS.length) | 0],
      alpha: Math.random() * 0.5 + 0.25,
    });
    const resize = () => {
      W = canvas.clientWidth;
      H = canvas.clientHeight;
      canvas.width = Math.max(1, Math.round(W * dpr));
      canvas.height = Math.max(1, Math.round(H * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = Math.min(240, Math.round((W * H) / 8500));
      particles = Array.from({ length: count }, () => spawn(false));
    };
    const drawParticle = (p) => {
      // Rise from the bottom: fully visible low, fading out over the top ~22%.
      const topFade = Math.min(1, p.y / (H * 0.22));
      ctx.globalAlpha = Math.max(0, p.alpha * topFade);
      ctx.fillStyle = p.color;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fill();
    };
    const frame = () => {
      t += 0.016;
      ctx.clearRect(0, 0, W, H);
      for (const p of particles) {
        p.y -= p.vy;
        p.x += Math.sin(t + p.phase) * p.amp * 0.35;
        if (p.y < -8) Object.assign(p, spawn(true));
        drawParticle(p);
      }
      ctx.globalAlpha = 1;
      raf = requestAnimationFrame(frame);
    };
    resize();
    window.addEventListener("resize", resize);
    if (reduce) {
      particles.forEach(drawParticle);
      ctx.globalAlpha = 1;
      return () => window.removeEventListener("resize", resize);
    }
    raf = requestAnimationFrame(frame);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
    };
  }, []);
  return <canvas ref={ref} className="particle-field" aria-hidden="true" />;
}
