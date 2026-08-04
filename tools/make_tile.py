"""Generate the /sid project tile for StockTest.

The tiles on biswas.net/sid are a consistent poster series: 720x840, a cream
frame around a navy panel, an uppercase cream title over an orange subtitle, a
central two-colour illustration, and small marks in the bottom corners, with a
light paper grain over everything.

Palette and geometry are sampled from the existing tiles rather than guessed:

    navy    #294354      cream   #ECE3CB      orange  #D87641
    canvas  720 x 840    frame   ~27 px

Two things matter for matching the series:

  * **Supersampling.** Pillow's draw primitives are not antialiased, so strokes
    and circles come out visibly jagged next to the existing artwork. Everything
    is drawn at SS times scale and downsampled with LANCZOS at the end.

  * **Deliberate polylines, not noise.** The illustration is a hand-placed
    sequence of points, so the curve reads as crisp angular segments the way the
    NOAA tile's arrow does. An earlier version used a 120-step random walk with
    a filled area underneath, which downsampled into a soft mountain silhouette.

Needs Pillow (in requirements-dev.txt; nothing else uses it).

Usage:
    .venv/bin/python tools/make_tile.py [out.png]

The output belongs in the Pages repo as sid/stocktest.png, not here — this
script is kept so the tile can be regenerated to match if the series style
changes.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 720, 840
FRAME = 27
NAVY = (41, 67, 84)
CREAM = (236, 227, 203)
ORANGE = (216, 118, 65)
BLUE = (58, 110, 150)
GRID = (63, 90, 107)

# Supersampling factor. 4x is enough to make strokes and circles read as clean
# as the vector-drawn tiles they sit beside.
SS = 4

FONT_DIR = Path("/System/Library/Fonts/Supplemental")


def font(size: int) -> ImageFont.FreeTypeFont:
    """Bold sans, closest match to the existing tiles."""
    for name in ("Arial Bold.ttf", "Helvetica.ttc"):
        p = FONT_DIR / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size)


def centered(d: ImageDraw.ImageDraw, y: int, text: str, f, fill, tracking: int = 0):
    """Draw text centred on the canvas, with optional letter-spacing."""
    if tracking == 0:
        w = d.textbbox((0, 0), text, font=f)[2]
        d.text(((W * SS - w) / 2, y), text, font=f, fill=fill)
        return
    widths = [d.textbbox((0, 0), ch, font=f)[2] for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = (W * SS - total) / 2
    for ch, cw in zip(text, widths):
        d.text((x, y), ch, font=f, fill=fill)
        x += cw + tracking


def fit(d: ImageDraw.ImageDraw, text: str, target: int, start: int) -> ImageFont.FreeTypeFont:
    """Largest font size whose rendered width fits `target`."""
    size = start
    while size > 10 * SS:
        f = font(size)
        if d.textbbox((0, 0), text, font=f)[2] <= target:
            return f
        size -= 2 * SS
    return font(10 * SS)


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "stocktest.png")
    s = SS  # shorthand: every geometry constant below is in final-image units

    img = Image.new("RGB", (W * s, H * s), CREAM)
    d = ImageDraw.Draw(img)
    d.rectangle([FRAME * s, FRAME * s, (W - FRAME) * s - 1, (H - FRAME) * s - 1], fill=NAVY)

    inner = (W - 2 * FRAME) * s

    # ---- title + subtitle ------------------------------------------------
    title_f = fit(d, "STOCKTEST", inner - 70 * s, 130 * s)
    centered(d, 62 * s, "STOCKTEST", title_f, CREAM)
    sub_f = fit(d, "AFTER-TAX BACKTESTING", inner - 90 * s, 52 * s)
    centered(d, 62 * s + title_f.size + 24 * s, "AFTER-TAX BACKTESTING", sub_f, ORANGE, tracking=s)

    # ---- illustration: strategy vs benchmark -----------------------------
    # The project's question is "does this beat the index, after tax?", so the
    # tile is two equity lines diverging: a volatile strategy that drops hard
    # and recovers past the index, and the index plodding upward beneath it.
    px0, px1 = 86 * s, (W - 86) * s
    py0, py1 = 292 * s, 690 * s
    pw, ph = px1 - px0, py1 - py0

    d.rectangle([px0, py0, px1, py1], outline=CREAM, width=3 * s)
    for i in range(1, 5):
        y = py0 + ph * i / 5
        d.line([(px0 + 3 * s, y), (px1 - 3 * s, y)], fill=GRID, width=2 * s)
    for i in range(1, 6):
        x = px0 + pw * i / 6
        d.line([(x, py0 + 3 * s), (x, py1 - 3 * s)], fill=GRID, width=2 * s)

    def path(pts):
        """(x fraction, height fraction) -> pixel coordinates inside the plot.

        Inset on both axes so the strokes and the endpoint marker sit clear of
        the plot border rather than colliding with it.
        """
        padx, pady = 30 * s, 26 * s
        return [
            (px0 + padx + (pw - 2 * padx) * fx, py1 - pady - (ph - 2 * pady) * fy)
            for fx, fy in pts
        ]

    # Hand-placed so the shape is legible: run up, sharp drawdown, recovery to
    # a new high. Few points, so the segments stay straight and sharp.
    strategy = path([
        (0.00, 0.05), (0.09, 0.20), (0.16, 0.15), (0.24, 0.34), (0.31, 0.28),
        (0.40, 0.52), (0.46, 0.44), (0.52, 0.16), (0.58, 0.26), (0.66, 0.21),
        (0.74, 0.47), (0.81, 0.41), (0.89, 0.66), (0.95, 0.60), (1.00, 0.86),
    ])
    benchmark = path([
        (0.00, 0.03), (0.18, 0.11), (0.34, 0.16), (0.50, 0.13),
        (0.66, 0.22), (0.84, 0.29), (1.00, 0.38),
    ])

    d.line(benchmark, fill=CREAM, width=7 * s, joint="curve")
    d.line(strategy, fill=ORANGE, width=11 * s, joint="curve")

    # Endpoint marker on the strategy line.
    ex, ey = strategy[-1]
    r = 15 * s
    d.ellipse([ex - r, ey - r, ex + r, ey + r], fill=ORANGE)
    d.ellipse([ex - r / 2.6, ey - r / 2.6, ex + r / 2.6, ey + r / 2.6], fill=CREAM)

    # ---- bottom marks ----------------------------------------------------
    # Left: a small bar row, echoing the data-project tiles.
    bx, by = 86 * s, (H - 92) * s
    for i, (hgt, col) in enumerate([(20, ORANGE), (34, BLUE), (46, CREAM), (28, ORANGE), (38, BLUE)]):
        d.rectangle([bx + i * 26 * s, by + (46 - hgt) * s, bx + i * 26 * s + 17 * s, by + 46 * s],
                    fill=col)

    # Right: a percent mark in a ring — the after-tax verdict.
    cx, cy, rr = (W - 116) * s, (H - 70) * s, 29 * s
    d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=CREAM, width=5 * s)
    pf = font(34 * s)
    box = d.textbbox((0, 0), "%", font=pf)
    d.text((cx - box[2] / 2, cy - box[3] / 2 - 4 * s), "%", font=pf, fill=CREAM)

    # ---- downsample, then grain -----------------------------------------
    img = img.resize((W, H), Image.LANCZOS)

    # The existing tiles have a subtle print texture; without it the flat fills
    # read as noticeably cleaner than their neighbours. Applied after the
    # downsample so it stays a fine grain rather than being averaged away.
    rnd = random.Random(11)
    noise = Image.new("L", (W, H))
    noise.putdata([rnd.randint(0, 255) for _ in range(W * H)])
    noise = noise.filter(ImageFilter.GaussianBlur(0.4))
    img = Image.blend(img, Image.composite(Image.new("RGB", (W, H), CREAM), img, noise), 0.04)

    img.save(out, "PNG", optimize=True)
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} kB, {W}x{H}, {SS}x supersampled)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
