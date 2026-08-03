"""Phase 1: convert data/*.csv into a browser-loadable binary bundle.

The browser port can't parse 400 MB of CSV text. This emits a compact binary
form designed around what the engine actually reads:

  * **Strategies only ever read `Close`.** Every picker and timer goes through
    `ctx.history(t, "Close", ...)`; nothing reads Open/High/Low, and Volume is
    used solely for the `volume > 0` tradability test in `market.py`. So the
    universe bundle carries Close plus a precomputed tradability bit, and
    nothing else. Full OHLCV lives in the lazily-fetched per-ticker files.

  * **Dense-over-span beats sparse.** A ticker trades on nearly every union
    calendar day inside its own span (measured: 123 wasted cells out of
    4.52M, 3 of 528 tickers have any interior gap). Storing a dense slice plus
    a start offset therefore costs ~0.003% overhead and avoids shipping a
    parallel Int32 date index, which would have doubled the payload.

  * **Tradability is precomputed.** `market.py` decides tradability from
    float64 CSV values as `close notna AND (volume isna OR volume > 0)`. That
    rule is evaluated here on the exact source and shipped as one bit per cell,
    so the port reads a decision rather than reimplementing a predicate.
    Measured: recomputing it from float32 volume would flip 0 of 4,521,651 bars
    (the smallest positive volume in the dataset is 20, and float32 cannot round
    a positive to zero), so this is defensive, not a fix for a live defect.

Layouts (little-endian throughout; bitmasks are LSB-first within each byte,
i.e. numpy packbits with bitorder="little"):

  calendar.bin      int32[n_cal]                  days since 1970-01-01 (UTC)

  tickers/<T>.bin   magic "STK1", uint32 version, uint32 first, uint32 n,
                    float32[n] x 5 (open, high, low, close, volume),
                    uint8[ceil(n/8)] tradable

  universe.bin      magic "STKU", uint32 version, uint32 n_tickers,
                    uint32 n_cal, (uint32 first, uint32 n) x n_tickers,
                    float32[sum n] close (ticker order),
                    per-ticker byte-aligned uint8 tradable masks (ticker order)

Ticker names, offsets, hashes and sizes all live in manifest.json so the
binaries stay purely numeric.

PRECISION (measured across all 528 tickers, 4.52M bars):

    field    max rel err   median      tickers > 1e-9
    Close      6.3e-14     2.8e-16       0 / 528
    Open       5.96e-08    5.88e-08    445 / 528
    High       5.96e-08    5.88e-08    445 / 528
    Low        5.96e-08    5.88e-08    444 / 528
    Volume     5.96e-08    0           230 / 528

Close is already float32-derived upstream (yfinance), so storing it as float32
is effectively lossless — which is what makes this format safe, because the
engine reads Close and nothing else. Open/High/Low genuinely lose ~6e-8; they
exist only in the per-ticker files for charting and are never read by the
simulation. `tools/measure_f32_drift.py` confirms the end-to-end effect on the
Phase 0 goldens is <=2.2e-15 on equity, ~500,000x inside the 1e-9 tolerance,
with every trade count identical.

Usage:
    .venv/bin/python tools/build_web_data.py            # build
    .venv/bin/python tools/build_web_data.py --verify   # build + round-trip checks
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import math
import struct
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backtester.data import DATA_DIR, FIELDS, available_tickers  # noqa: E402
from backtester.universe import CONSTITUENTS_PATH, _normalize  # noqa: E402

OUT = ROOT / "build" / "webdata"
FORMAT_VERSION = 1
EPOCH = np.datetime64("1970-01-01", "D")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def gz_size(b: bytes) -> int:
    """Size after gzip -9, computed in memory (mtime=0 so it's reproducible)."""
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9, mtime=0) as fh:
        fh.write(b)
    return len(buf.getvalue())


def write(path: Path, data: bytes, also_gzip: bool = False) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    info = {
        "file": str(path.relative_to(OUT)),
        "bytes": len(data),
        "sha256": sha256_bytes(data),
    }
    if also_gzip:
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9, mtime=0) as fh:
            fh.write(data)
        gz = buf.getvalue()
        (path.parent / (path.name + ".gz")).write_bytes(gz)
        info["gzip_bytes"] = len(gz)
    return info


def pack_bits(mask: np.ndarray) -> bytes:
    """Bit-pack a boolean array, LSB-first within each byte."""
    return np.packbits(mask.astype(np.uint8), bitorder="little").tobytes()


def json_safe(v):
    """NaN/Inf are not valid JSON; map them to null so JSON.parse works."""
    if isinstance(v, float) and not math.isfinite(v):
        return None
    if isinstance(v, (np.floating,)):
        f = float(v)
        return f if math.isfinite(f) else None
    if isinstance(v, (np.integer,)):
        return int(v)
    return v


# ---------------------------------------------------------------------------
# load
# ---------------------------------------------------------------------------
def load_all() -> tuple[list[str], dict[str, pd.DataFrame], np.ndarray]:
    tickers = available_tickers()
    frames: dict[str, pd.DataFrame] = {}
    for t in tickers:
        df = pd.read_csv(DATA_DIR / f"{t}.csv", parse_dates=["Date"], index_col="Date")
        df = df[[c for c in FIELDS if c in df.columns]].sort_index()
        df.attrs["ticker"] = t
        frames[t] = df
    calendar = np.unique(np.concatenate([f.index.values for f in frames.values()]))
    return tickers, frames, calendar


def ticker_arrays(df: pd.DataFrame, calendar: np.ndarray):
    """Dense-over-span float32 arrays plus the exact tradability mask.

    Returns (first, n, {field: float32[n]}, tradable_bool[n]).
    Cells inside the span where this ticker has no bar are NaN and not tradable.
    """
    # INVARIANT: the dense encoding uses NaN to mean "no bar here", so a real
    # row must never carry NaN — otherwise the browser decoder cannot tell a
    # missing bar from a present one with missing data, and would silently drop
    # the row. True across all 528 tickers today; asserted so a future data
    # refresh fails loudly here instead of corrupting the port's history().
    for _f in FIELDS:
        if _f in df.columns and df[_f].isna().any():
            raise ValueError(
                f"{df.attrs.get('ticker', '?')}: {int(df[_f].isna().sum())} NaN "
                f"value(s) in {_f}. The dense format needs an explicit presence "
                f"mask before it can represent this."
            )

    pos = calendar.searchsorted(df.index.values)
    first, last = int(pos[0]), int(pos[-1])
    n = last - first + 1
    rel = pos - first

    out: dict[str, np.ndarray] = {}
    for f in FIELDS:
        dense = np.full(n, np.nan, dtype=np.float64)
        if f in df.columns:
            dense[rel] = df[f].to_numpy(dtype=np.float64)
        out[f] = dense.astype(np.float32)

    # Tradability from the EXACT float64 source, mirroring market.py.
    close64 = np.full(n, np.nan, dtype=np.float64)
    close64[rel] = df["Close"].to_numpy(dtype=np.float64)
    if "Volume" in df.columns:
        vol64 = np.full(n, np.nan, dtype=np.float64)
        vol64[rel] = df["Volume"].to_numpy(dtype=np.float64)
    else:
        vol64 = np.full(n, np.nan, dtype=np.float64)
    tradable = ~np.isnan(close64) & (np.isnan(vol64) | (vol64 > 0))
    return first, n, out, tradable


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------
def build(verify: bool) -> int:
    t0 = time.time()
    print("loading CSVs…")
    tickers, frames, calendar = load_all()
    print(f"  {len(tickers)} tickers, {len(calendar)} calendar days, "
          f"{time.time() - t0:.1f}s")

    if OUT.exists():
        for p in sorted(OUT.rglob("*"), reverse=True):
            p.unlink() if p.is_file() else p.rmdir()
    OUT.mkdir(parents=True, exist_ok=True)

    # ---- calendar ----
    days = ((calendar.astype("datetime64[D]") - EPOCH).astype(np.int32))
    cal_info = write(OUT / "calendar.bin", days.tobytes(), also_gzip=True)

    # ---- per-ticker + universe accumulation ----
    per_ticker: dict[str, dict] = {}
    table: list[tuple[int, int]] = []
    uni_close: list[bytes] = []
    uni_mask: list[bytes] = []
    total_cells = 0

    for t in tickers:
        first, n, arrs, tradable = ticker_arrays(frames[t], calendar)
        total_cells += n

        body = b"".join(arrs[f].tobytes() for f in FIELDS)
        blob = (b"STK1" + struct.pack("<III", FORMAT_VERSION, first, n)
                + body + pack_bits(tradable))
        info = write(OUT / "tickers" / f"{t}.bin", blob, also_gzip=True)
        idx = frames[t].index
        per_ticker[t] = {
            **info,
            "first": first,
            "n": n,
            "bars": int(len(idx)),
            "start": idx[0].date().isoformat(),
            "end": idx[-1].date().isoformat(),
        }

        table.append((first, n))
        uni_close.append(arrs["Close"].tobytes())
        uni_mask.append(pack_bits(tradable))

    # ---- universe bundle (Close + tradability only) ----
    head = (b"STKU" + struct.pack("<III", FORMAT_VERSION, len(tickers), len(calendar))
            + b"".join(struct.pack("<II", f, n) for f, n in table))
    uni = head + b"".join(uni_close) + b"".join(uni_mask)
    uni_info = write(OUT / "universe.bin", uni, also_gzip=True)

    # ---- fundamentals ----
    fdf = pd.read_csv(DATA_DIR / "fundamentals.csv")
    fundamentals = {
        "columns": [c for c in fdf.columns if c != "ticker"],
        # Explicit row order. The fundamental pickers rank with pandas'
        # sort_values, whose tie-breaking depends on the pre-sort row order, so
        # the port needs the CSV order as data — not as an accident of JSON key
        # ordering (this file is emitted with sort_keys=True).
        "order": [str(t) for t in fdf["ticker"]],
        "rows": {
            str(r["ticker"]): {k: json_safe(r[k]) for k in fdf.columns if k != "ticker"}
            for _, r in fdf.iterrows()
        },
    }
    f_info = write(OUT / "fundamentals.json",
                   (json.dumps(fundamentals, sort_keys=True, allow_nan=False) + "\n").encode(),
                   also_gzip=True)

    # ---- point-in-time S&P 500 membership ----
    # Normalized to the Yahoo-style symbols used by the price files, exactly as
    # backtester/universe.py does, so the port never has to redo that mapping.
    cdf = pd.read_csv(CONSTITUENTS_PATH, parse_dates=["date"]).sort_values("date")
    pit = {
        "note": "As-of membership: for a given day use the latest snapshot <= that day. "
                "Symbols normalized to Yahoo style (dots -> hyphens), matching "
                "backtester/universe.py::_normalize.",
        "dates": [d.date().isoformat() for d in cdf["date"]],
        "members": [
            sorted({_normalize(x) for x in str(row).split(",") if x})
            for row in cdf["tickers"]
        ],
    }
    p_info = write(OUT / "sp500-pit.json",
                   (json.dumps(pit, sort_keys=True, allow_nan=False) + "\n").encode(),
                   also_gzip=True)

    # ---- manifest ----
    manifest = {
        "format_version": FORMAT_VERSION,
        "generated_by": "tools/build_web_data.py",
        "endianness": "little",
        "bit_order": "lsb-first within each byte (numpy packbits bitorder='little')",
        "dtypes": {"prices": "float32", "calendar": "int32 days since 1970-01-01",
                   "tradable": "1 bit per cell"},
        "notes": [
            "Per-ticker cells are dense over [first, first+n) in calendar index "
            "space; cells with no bar are NaN and not tradable.",
            "universe.bin carries Close + tradability only — no strategy reads "
            "Open/High/Low, and Volume is used solely for the >0 tradable test.",
            "tradable bits are computed from the float64 source; read them rather "
            "than reimplementing the predicate (measured: recomputing from float32 "
            "volume flips 0 of 4,521,651 bars, so this is defensive only).",
            "Close is float32-derived upstream, so float32 storage is lossless for "
            "it (max rel err 6.3e-14) — and the engine reads only Close. "
            "Open/High/Low lose ~6e-8 and are for charting only. "
            "End-to-end effect on the Phase 0 goldens: <=2.2e-15. "
            "See precision_report.json.",
        ],
        "calendar": {**cal_info, "n": int(len(calendar)),
                     "start": str(calendar[0])[:10], "end": str(calendar[-1])[:10]},
        "universe": {**uni_info, "tickers": tickers, "n_tickers": len(tickers),
                     "total_cells": total_cells,
                     "layout": "header, (first,n) table, close float32 concat, "
                               "tradable bitmask concat (byte-aligned per ticker)"},
        "fundamentals": f_info,
        "sp500_pit": p_info,
        "tickers": per_ticker,
    }
    m_info = write(OUT / "manifest.json",
                   (json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n").encode(),
                   also_gzip=True)

    # ---- size report ----
    raw_all = sum(p.stat().st_size for p in OUT.rglob("*.bin")) \
        + sum(p.stat().st_size for p in OUT.rglob("*.json"))
    gz_all = sum(p.stat().st_size for p in OUT.rglob("*.gz"))
    tick_raw = sum(v["bytes"] for v in per_ticker.values())
    tick_gz = sum(v.get("gzip_bytes", 0) for v in per_ticker.values())
    median_gz = int(np.median([v.get("gzip_bytes", 0) for v in per_ticker.values()]))

    def mb(x):
        return f"{x / 1e6:8.2f} MB"

    print("\nsizes (raw -> gzip -9):")
    print(f"  universe.bin       {mb(uni_info['bytes'])} -> {mb(uni_info['gzip_bytes'])}")
    print(f"  calendar.bin       {mb(cal_info['bytes'])} -> {mb(cal_info['gzip_bytes'])}")
    print(f"  fundamentals.json  {mb(f_info['bytes'])} -> {mb(f_info['gzip_bytes'])}")
    print(f"  sp500-pit.json     {mb(p_info['bytes'])} -> {mb(p_info['gzip_bytes'])}")
    print(f"  manifest.json      {mb(m_info['bytes'])} -> {mb(m_info['gzip_bytes'])}")
    print(f"  tickers/*.bin      {mb(tick_raw)} -> {mb(tick_gz)}  ({len(tickers)} files)")
    print(f"  ---- strategy-mode payload (universe+calendar+manifest, gzip): "
          f"{mb(uni_info['gzip_bytes'] + cal_info['gzip_bytes'] + m_info['gzip_bytes'])}")
    print(f"  ---- median per-ticker file (gzip): {median_gz / 1e3:.0f} kB")
    print(f"  ---- everything on disk: raw {mb(raw_all)}, gz {mb(gz_all)}")
    print(f"\nbuilt in {time.time() - t0:.1f}s -> {OUT.relative_to(ROOT)}/")

    if verify:
        return verify_roundtrip(tickers, frames, calendar, per_ticker)
    return 0


# ---------------------------------------------------------------------------
# verification
# ---------------------------------------------------------------------------
def read_ticker(path: Path):
    b = path.read_bytes()
    assert b[:4] == b"STK1", f"bad magic in {path}"
    version, first, n = struct.unpack_from("<III", b, 4)
    off = 16
    arrs = {}
    for f in FIELDS:
        arrs[f] = np.frombuffer(b, dtype="<f4", count=n, offset=off)
        off += 4 * n
    mask_bytes = (n + 7) // 8
    bits = np.unpackbits(np.frombuffer(b, dtype=np.uint8, count=mask_bytes, offset=off),
                         count=n, bitorder="little").astype(bool)
    return version, first, n, arrs, bits


def read_universe(path: Path):
    b = path.read_bytes()
    assert b[:4] == b"STKU", "bad magic in universe.bin"
    version, n_t, n_cal = struct.unpack_from("<III", b, 4)
    off = 16
    table = []
    for _ in range(n_t):
        f, n = struct.unpack_from("<II", b, off)
        table.append((f, n)); off += 8
    closes = []
    for _, n in table:
        closes.append(np.frombuffer(b, dtype="<f4", count=n, offset=off)); off += 4 * n
    masks = []
    for _, n in table:
        nb = (n + 7) // 8
        masks.append(np.unpackbits(np.frombuffer(b, dtype=np.uint8, count=nb, offset=off),
                                   count=n, bitorder="little").astype(bool))
        off += nb
    assert off == len(b), f"universe.bin trailing bytes: {len(b) - off}"
    return table, closes, masks


def verify_roundtrip(tickers, frames, calendar, per_ticker) -> int:
    print("\n--- verify: binary round-trip vs source CSVs ---")
    errs: list[str] = []
    table, uni_closes, uni_masks = read_universe(OUT / "universe.bin")
    cal_days = np.frombuffer((OUT / "calendar.bin").read_bytes(), dtype="<i4")
    if len(cal_days) != len(calendar):
        errs.append(f"calendar length {len(cal_days)} != {len(calendar)}")
    elif not np.array_equal(cal_days,
                            (calendar.astype("datetime64[D]") - EPOCH).astype(np.int32)):
        errs.append("calendar values differ")

    worst_rel = 0.0
    for i, t in enumerate(tickers):
        version, first, n, arrs, bits = read_ticker(OUT / "tickers" / f"{t}.bin")
        df = frames[t]
        pos = calendar.searchsorted(df.index.values)
        rel = pos - first

        if (first, n) != table[i]:
            errs.append(f"{t}: universe table {(table[i])} != per-ticker {(first, n)}")

        # Prices must equal float32(source) EXACTLY at every real bar.
        for f in FIELDS:
            if f not in df.columns:
                continue
            src = df[f].to_numpy(dtype=np.float64)
            got = arrs[f][rel].astype(np.float64)
            exp = src.astype(np.float32).astype(np.float64)
            fin = np.isfinite(src)
            if not np.array_equal(got[fin], exp[fin]):
                errs.append(f"{t}.{f}: float32 round-trip mismatch")
            nz = fin & (src != 0)
            if nz.any():
                worst_rel = max(worst_rel, float(
                    np.max(np.abs(got[nz] - src[nz]) / np.abs(src[nz]))))

        # Cells outside real bars must be NaN.
        hole = np.ones(n, dtype=bool); hole[rel] = False
        if hole.any() and not np.all(np.isnan(arrs["Close"][hole])):
            errs.append(f"{t}: non-NaN in a gap cell")

        # Tradability must match market.py's rule computed on float64 source.
        close64 = np.full(n, np.nan); close64[rel] = df["Close"].to_numpy(dtype=np.float64)
        vol64 = np.full(n, np.nan)
        if "Volume" in df.columns:
            vol64[rel] = df["Volume"].to_numpy(dtype=np.float64)
        exp_tr = ~np.isnan(close64) & (np.isnan(vol64) | (vol64 > 0))
        if not np.array_equal(bits, exp_tr):
            errs.append(f"{t}: tradable mask mismatch ({int((bits != exp_tr).sum())} cells)")

        # The universe bundle must agree with the per-ticker file bit for bit.
        if not np.array_equal(uni_closes[i].view(np.uint32), arrs["Close"].view(np.uint32)):
            errs.append(f"{t}: universe close != per-ticker close")
        if not np.array_equal(uni_masks[i], bits):
            errs.append(f"{t}: universe mask != per-ticker mask")

    print(f"  worst price relative error vs float64 source: {worst_rel:.3e}")
    if errs:
        print(f"  {len(errs)} FAILURES:")
        for e in errs[:20]:
            print(f"    - {e}")
        return 1
    print(f"  all {len(tickers)} tickers round-trip exactly (float32 semantics), "
          f"tradability bit-exact")

    # JSON artifacts must be strict-parseable.
    for name in ("fundamentals.json", "sp500-pit.json", "manifest.json"):
        def boom(x):
            raise ValueError(f"{name}: non-standard constant {x}")
        json.loads((OUT / name).read_text(), parse_constant=boom)
    print("  fundamentals.json / sp500-pit.json / manifest.json: strict-JSON OK")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true",
                    help="Round-trip the binaries back and check against the CSVs.")
    raise SystemExit(build(ap.parse_args().verify))
