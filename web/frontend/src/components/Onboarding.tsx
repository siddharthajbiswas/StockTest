import { useEffect, useLayoutEffect, useState } from "react";

export interface TourStep {
  title: string;
  body: string;
  /** id of an element to spotlight; omit for a centered card. */
  targetId?: string;
}

interface Props {
  steps: TourStep[];
  onClose: () => void;
  onFinishExample?: () => void; // last step's CTA ("Try an example")
}

/** A dependency-free onboarding tour: dark overlay, an optional highlight ring
 *  around a target element, and a stepper card. */
export function Onboarding({ steps, onClose, onFinishExample }: Props) {
  const [i, setI] = useState(0);
  const step = steps[i];
  const [ring, setRing] = useState<DOMRect | null>(null);
  const isLast = i === steps.length - 1;

  useLayoutEffect(() => {
    const el = step.targetId ? document.getElementById(step.targetId) : null;
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      // Measure after the scroll settles.
      const t = setTimeout(() => setRing(el.getBoundingClientRect()), 260);
      return () => clearTimeout(t);
    }
    setRing(null);
  }, [step.targetId]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight" && !isLast) setI((n) => n + 1);
      if (e.key === "ArrowLeft" && i > 0) setI((n) => n - 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [i, isLast, onClose]);

  // Position the card near the ring, otherwise center it.
  let cardStyle: React.CSSProperties = {};
  let centered = true;
  if (ring) {
    centered = false;
    const below = ring.bottom + 320 < window.innerHeight;
    const top = below ? ring.bottom + 14 : Math.max(16, ring.top - 14 - 200);
    const left = Math.min(Math.max(16, ring.left), window.innerWidth - 396);
    cardStyle = { top, left };
  }

  return (
    <>
      <div className="tour-overlay" onClick={onClose} />
      {ring && (
        <div
          className="tour-ring"
          style={{
            top: ring.top - 6,
            left: ring.left - 6,
            width: ring.width + 12,
            height: ring.height + 12,
          }}
        />
      )}
      <div className={"tour-card" + (centered ? " centered" : "")} style={cardStyle}>
        <h4>{step.title}</h4>
        <p>{step.body}</p>
        <div className="tour-foot">
          <div className="tour-dots" aria-hidden>
            {steps.map((_, idx) => (
              <i key={idx} className={idx === i ? "on" : ""} />
            ))}
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {i > 0 && (
              <button className="btn" onClick={() => setI((n) => n - 1)}>
                Back
              </button>
            )}
            {!isLast && (
              <button className="btn primary" onClick={() => setI((n) => n + 1)}>
                Next
              </button>
            )}
            {isLast &&
              (onFinishExample ? (
                <button
                  className="btn primary"
                  onClick={() => {
                    onClose();
                    onFinishExample();
                  }}
                >
                  Try an example →
                </button>
              ) : (
                <button className="btn primary" onClick={onClose}>
                  Get started
                </button>
              ))}
          </div>
        </div>
        <button
          className="btn ghost"
          style={{ position: "absolute", top: 10, right: 10, padding: "4px 8px" }}
          onClick={onClose}
        >
          Skip
        </button>
      </div>
    </>
  );
}
