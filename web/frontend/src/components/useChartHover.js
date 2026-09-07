import { useCallback, useState } from "react";
export function useChartHover(opts) {
  const { width, padLeft, padRight, n } = opts;
  const [index, setIndex] = useState(null);
  const locate = useCallback(
    (e) => {
      const rect = e.currentTarget.getBoundingClientRect();
      if (rect.width === 0 || n < 2) return;
      // CSS pixels -> user units.
      const x = ((e.clientX - rect.left) / rect.width) * width;
      const innerW = width - padLeft - padRight;
      const frac = (x - padLeft) / innerW;
      const i = Math.round(frac * (n - 1));
      setIndex(i < 0 ? 0 : i > n - 1 ? n - 1 : i);
    },
    [width, padLeft, padRight, n],
  );
  return {
    index,
    handlers: {
      onPointerMove: locate,
      onPointerDown: locate,
      onPointerLeave: () => setIndex(null),
    },
  };
}

/**
 * Horizontal placement for a tooltip anchored at `xFrac` (0..1) of the chart.
 *
 * Past the midpoint the bubble flips to the left of the crosshair so it never
 * runs off the right edge of the results sheet.
 */
export function tooltipStyle(xFrac) {
  const flip = xFrac > 0.55;
  return {
    left: `${xFrac * 100}%`,
    transform: flip ? "translateX(calc(-100% - 14px))" : "translateX(14px)",
  };
}
