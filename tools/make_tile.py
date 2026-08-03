"""Generate the /sid project tile for StockTest.

The tiles on biswas.net/sid are a consistent poster series: 720x840, a cream
frame around a navy panel, an uppercase cream title over an orange subtitle, a
central two-colour illustration, and small marks in the bottom corners, with a
light paper grain over everything.

Palette and geometry are sampled from the existing tiles rather than guessed:

    navy    #294354      cream   #ECE3CB      orange  #D87641
    canvas  720 x 840    frame   ~27 px

Needs Pillow (in requirements-dev.txt; nothing else uses it).

Usage:
    .venv/bin/python tools/make_tile.py [out.png]

The output belongs in the Pages repo as sid/stocktest.png, not here — this
script is kept so the tile can be regenerated to match if the series style
changes.
"""

from __future__ import annotations

import math
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

FONT_DIR = Path("/System/Library/Fonts/Supplemental")


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
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
        d.text(((W - w) / 2, y), text, font=f, fill=fill)
        return
    widths = [d.textbbox((0, 0), ch, font=f)[2] for ch in text]
    total = sum(widths) + tracking * (len(text) - 1)
    x = (W - total) / 2
    for ch, cw in zip(text, widths):
        d.text((x, y), ch, font=f, fill=fill)
        x += cw + tracking


def fit(d: ImageDraw.ImageDraw, text: str, target: int, start: int) -> ImageFont.FreeTypeFont:
    """Largest font size whose rendered width fits `target`."""
    size = start
    while size > 10:
        f = font(size)
        if d.textbbox((0, 0), text, font=f)[2] <= target:
            return f
        size -= 2
    return font(10)


def main() -> int:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "stocktest.png")

    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    d.rectangle([FRAME, FRAME, W - FRAME - 1, H - FRAME - 1], fill=NAVY)

    inner = W - 2 * FRAME

    # ---- title + subtitle ------------------------------------------------
    title_f = fit(d, "STOCKTEST", inner - 70, 130)
    centered(d, 62, "STOCKTEST", title_f, CREAM)
    sub_f = fit(d, "AFTER-TAX BACKTESTING", inner - 90, 52)
    centered(d, 62 + title_f.size + 24, "AFTER-TAX BACKTESTING", sub_f, ORANGE, tracking=1)

    # ---- illustration: a strategy curve against a benchmark --------------
    # The project's whole question is "does this beat the index, after tax?",
    # so the tile is two equity curves diverging. The strategy line is filled
    # underneath: the neighbouring tiles all carry a bold solid shape, and thin
    # strokes alone read as much lighter than they do.
    px0, px1 = 86, W - 86
    py0, py1 = 292, 690
    d.rectangle([px0, py0, px1, py1], outline=CREAM, width=3)

    for i in range(1, 5):
        y = py0 + (py1 - py0) * i / 5
        d.line([(px0 + 3, y), (px1 - 3, y)], fill=(68, 94, 110), width=2)
    for i in range(1, 6):
        x = px0 + (px1 - px0) * i / 6
        d.line([(x, py0 + 3), (x, py1 - 3)], fill=(68, 94, 110), width=2)

    def curve(seed: int, vol: float, top: float, dip: tuple[float, float, float] | None):
        """Jagged upward equity curve. `dip` = (start, end, depth) drawdown."""
        rnd = random.Random(seed)
        n = 120
        vals, v = [], 0.0
        for i in range(n):
            f = i / (n - 1)
            step = 1.0 + rnd.uniform(-vol, vol)
            if dip and dip[0] <= f <= dip[1]:
                step -= dip[2]
            v += step
            vals.append(v)
        lo, hi = min(vals), max(vals)
        pts = []
        for i, val in enumerate(vals):
            x = px0 + (px1 - px0) * i / (n - 1)
            t = (val - lo) / (hi - lo or 1)
            pts.append((x, py1 - 16 - t * (py1 - py0 - 46) * top))
        return pts

    benchmark = curve(7, 0.9, 0.55, None)
    strategy = curve(5, 1.6, 1.0, (0.42, 0.56, 3.2))

    # Filled area under the strategy, in a darker orange so the stroke still reads.
    d.polygon([(px0 + 2, py1 - 2)] + strategy + [(px1 - 2, py1 - 2)], fill=(126, 74, 52))
    d.line(benchmark, fill=CREAM, width=7, joint="curve")
    d.line(strategy, fill=ORANGE, width=9, joint="curve")

    ex, ey = strategy[-1]
    d.ellipse([ex - 13, ey - 13, ex + 13, ey + 13], fill=ORANGE)
    d.ellipse([ex - 5, ey - 5, ex + 5, ey + 5], fill=CREAM)

    # ---- bottom marks ----------------------------------------------------
    # Left: a small bar row, echoing the data-project tiles.
    bx, by = 86, H - 92
    for i, (hgt, col) in enumerate([(20, ORANGE), (34, BLUE), (46, CREAM), (28, ORANGE), (38, BLUE)]):
        d.rectangle([bx + i * 26, by + (46 - hgt), bx + i * 26 + 17, by + 46], fill=col)

    # Right: a percent mark in a ring — the after-tax verdict.
    cx, cy, r = W - 116, H - 70, 29
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=CREAM, width=5)
    pf = font(34)
    pw = d.textbbox((0, 0), "%", font=pf)[2]
    ph = d.textbbox((0, 0), "%", font=pf)[3]
    d.text((cx - pw / 2, cy - ph / 2 - 4), "%", font=pf, fill=CREAM)

    # ---- paper grain -----------------------------------------------------
    # The existing tiles have a subtle print texture; without it the flat fills
    # read as noticeably cleaner than their neighbours.
    rnd = random.Random(11)
    noise = Image.new("L", (W, H))
    noise.putdata([rnd.randint(0, 255) for _ in range(W * H)])
    noise = noise.filter(ImageFilter.GaussianBlur(0.4))
    img = Image.blend(img, Image.composite(Image.new("RGB", (W, H), CREAM), img, noise), 0.045)

    img.save(out, "PNG", optimize=True)
    print(f"wrote {out} ({out.stat().st_size / 1024:.0f} kB, {W}x{H})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
