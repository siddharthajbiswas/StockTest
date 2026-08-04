import { useCallback, useState } from "react";

/**
 * Pointer tracking shared by the equity and drawdown charts.
 *
 * Both are inline SVGs with a `viewBox` and `width="100%"`, so the element's CSS
 * pixels and its user units differ by whatever the layout happens to be. This
 * converts a pointer event into the nearest sample index in user units, which is
 * the only part either chart needs.
 *
 * Touch is handled through the same pointer events: on a phone the tooltip
 * follows a drag along the chart, which is the closest thing to hover available.
 */
export interface ChartHover {
  /** Index of the hovered sample, or null when the pointer is away. */
  index: number | null;
  /** Spread onto the <svg>. */
  handlers: {
    onPointerMove: (e: React.PointerEvent<SVGSVGElement>) => void;
    onPointerLeave: () => void;
    onPointerDown: (e: React.PointerEvent<SVGSVGElement>) => void;
  };
}

export function useChartHover(opts: {
  /** viewBox width. */
  width: number;
  /** Left and right padding, in user units. */
  padLeft: number;
  padRight: number;
  /** Number of samples. */
  n: number;
}): ChartHover {
  const { width, padLeft, padRight, n } = opts;
  const [index, setIndex] = useState<number | null>(null);

  const locate = useCallback(
    (e: React.PointerEvent<SVGSVGElement>) => {
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
export function tooltipStyle(xFrac: number): React.CSSProperties {
  const flip = xFrac > 0.55;
  return {
    left: `${xFrac * 100}%`,
    transform: flip ? "translateX(calc(-100% - 14px))" : "translateX(14px)",
  };
}
