import { useEffect, useRef, useState } from "react";

/** A tiny "?" button that shows a positioned tooltip on hover/focus.
 *  No library — just a fixed-position bubble anchored to the button. */
export function InfoTip({ text, label = "More info" }) {
  const btnRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [pos, setPos] = useState({ top: 0, left: 0 });
  useEffect(() => {
    if (!open || !btnRef.current) return;
    const r = btnRef.current.getBoundingClientRect();
    setPos({
      top: r.bottom + 8,
      left: Math.min(r.left, window.innerWidth - 280),
    });
  }, [open]);
  return (
    <>
      <button
        ref={btnRef}
        type="button"
        className="info-btn"
        aria-label={label}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={(e) => e.preventDefault()}
      >
        ?
      </button>
      {open && (
        <div
          className="tooltip"
          role="tooltip"
          style={{ top: pos.top, left: pos.left }}
        >
          {text}
        </div>
      )}
    </>
  );
}
