"""Emit the static metadata the browser needs in place of the API (Phase 5).

Several backend endpoints return data that never changes at runtime:
`/pickers`, `/timers`, `/universe/options` are literal catalog tables, and
`/tickers` is an index derived from the price files plus the fundamentals
snapshot. With the engine running in a Web Worker there is no server to ask, so
these are extracted at build time and shipped alongside the price bundle.

Both are produced by importing the backend modules rather than re-listing their
contents, so they cannot drift from `catalog.py` / `tickers.py`. catalog.py
also self-checks against the engine registries at import, which means a picker
added to the engine but missing from the catalog fails this build.

Outputs (into build/webdata/, next to the Phase 1 artifacts):
    catalog.json   {pickers, timers, universes}
    tickers.json   {records, has_name_data, count}
    search.json    difflib.SequenceMatcher fixtures for the TS search port

Usage:
    .venv/bin/python tools/gen_web_metadata.py
"""

from __future__ import annotations

import gzip
import io
import json
import sys
import time
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "reference"))

OUT = ROOT / "build" / "webdata"


def dumps(o) -> str:
    return json.dumps(o, indent=1, sort_keys=True, allow_nan=False) + "\n"


def write(path: Path, text: str) -> None:
    """Write the artifact and a gzipped twin.

    The browser fetches the .gz and inflates it with DecompressionStream:
    GitHub Pages does not compress application/octet-stream, so without a
    pre-compressed copy the bundle would transfer at full size.
    """
    path.write_text(text)
    raw = text.encode()
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=9, mtime=0) as fh:
        fh.write(raw)
    (path.parent / (path.name + ".gz")).write_bytes(buf.getvalue())


def main() -> int:
    from catalog import PICKER_CATALOG, TIMER_CATALOG, UNIVERSE_OPTIONS
    from strategies.pickers import FUNDAMENTALS_PATH
    from tickers import TickerIndex
    from backtester.data import load_prices

    OUT.mkdir(parents=True, exist_ok=True)

    catalog = {
        "pickers": PICKER_CATALOG,
        "timers": TIMER_CATALOG,
        "universes": UNIVERSE_OPTIONS,
    }
    write(OUT / "catalog.json", dumps(catalog))
    print(f"catalog.json     {len(PICKER_CATALOG)} pickers, {len(TIMER_CATALOG)} timers, "
          f"{len(UNIVERSE_OPTIONS)} universes")

    t0 = time.time()
    prices = load_prices(None)
    idx = TickerIndex(prices, FUNDAMENTALS_PATH)
    payload = {
        "records": idx.records,
        "has_name_data": idx.has_name_data,
        "count": idx.count(),
        "data_start": min(df.index[0] for df in prices.values()).strftime("%Y-%m-%d"),
        "data_end": max(df.index[-1] for df in prices.values()).strftime("%Y-%m-%d"),
    }
    write(OUT / "tickers.json", dumps(payload))
    print(f"tickers.json     {idx.count()} records, has_name_data={idx.has_name_data} "
          f"({time.time() - t0:.1f}s)")

    # ---- search fixtures -------------------------------------------------
    # TickerIndex.search falls back to difflib.SequenceMatcher.ratio() for fuzzy
    # symbol matches. The TS port reimplements that algorithm, so pin it against
    # real symbol pairs plus edge cases.
    symbols = [r["symbol"] for r in idx.records]
    pairs = []
    for q in ["aapl", "appl", "msf", "gogl", "brk", "xyzzy", "a", "tesla", "amzn", "nvda"]:
        for s in symbols[:60] + ["AAPL", "MSFT", "GOOGL", "BRK-B", "AMZN", "NVDA", "TSLA"]:
            pairs.append((q, s.lower()))
    seen = set()
    fixtures = []
    for a, b in pairs:
        if (a, b) in seen:
            continue
        seen.add((a, b))
        fixtures.append({"a": a, "b": b, "ratio": SequenceMatcher(None, a, b).ratio()})
    for a, b in [("", ""), ("", "abc"), ("abc", ""), ("abc", "abc"),
                 ("ab", "ba"), ("abcd", "abed"), ("aaaa", "aa"), ("kitten", "sitting")]:
        fixtures.append({"a": a, "b": b, "ratio": SequenceMatcher(None, a, b).ratio()})

    # A handful of full search queries, so ranking and tie-breaks are pinned too.
    queries = [
        {"q": q, "limit": 12, "results": [r["symbol"] for r in idx.search(q, 12)]}
        for q in ["AAPL", "aa", "micro", "brk", "x", "zzz", "nvd", "T"]
    ]
    # search.json is a TEST FIXTURE, not a runtime artifact — no .gz, and
    # deploy/build-pages.sh excludes it from the published bundle.
    (OUT / "search.json").write_text(dumps({"ratios": fixtures, "queries": queries}))
    print(f"search.json      {len(fixtures)} ratio fixtures, {len(queries)} query fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
