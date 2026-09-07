#!/usr/bin/env bash
# Build the complete static site for GitHub Pages.
#
# StockTest has no backend. The engine is a JavaScript port running in a Web
# Worker, so a deploy is one directory of static files: the app bundle plus the
# binary price data it loads at runtime.
#
# Outputs a ready-to-publish tree at build/pages/. Copy that into your Pages
# repo under sid/stocktest/ (see DEPLOY.md).
#
# Usage:
#   bash deploy/build-pages.sh                 # base path /sid/stocktest/
#   BASE=/ bash deploy/build-pages.sh          # served at the domain root
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE="${BASE:-/sid/stocktest/}"
OUT="$ROOT/build/pages"
DATA_SRC="$ROOT/build/webdata"

if [[ ! -f "$DATA_SRC/universe.bin.gz" ]]; then
  echo "error: $DATA_SRC is missing or incomplete." >&2
  echo "Build the price bundle first:" >&2
  echo "  .venv/bin/python tools/build_web_data.py" >&2
  echo "  .venv/bin/python tools/gen_web_metadata.py" >&2
  exit 1
fi

echo "==> Building frontend (base=$BASE)"
cd "$ROOT/web/frontend"
npm ci --silent
VITE_BASE="$BASE" npm run build >/dev/null

echo "==> Assembling $OUT"
rm -rf "$OUT"
mkdir -p "$OUT"
cp -R dist/. "$OUT/"

# Ship only the .gz artifacts. The worker fetches those and inflates them with
# DecompressionStream, because static hosts do not compress
# application/octet-stream — see web/engine/src/worker/worker.js.
#
# search.json is a test fixture for the ticker-search port, not a runtime
# artifact, and precision_report.json is a build diagnostic. Neither ships.
mkdir -p "$OUT/data/tickers"
for f in manifest.json calendar.bin catalog.json tickers.json \
         fundamentals.json sp500-pit.json universe.bin; do
  cp "$DATA_SRC/$f.gz" "$OUT/data/$f.gz"
done
cp "$DATA_SRC"/tickers/*.bin.gz "$OUT/data/tickers/"

# Pages runs Jekyll by default, which ignores files and folders starting with
# an underscore and can rewrite others. Opt out.
touch "$OUT/.nojekyll"

app_bytes=$(du -sk "$OUT" --exclude=data 2>/dev/null | cut -f1 || \
            (du -sk "$OUT" | cut -f1))
total=$(du -sh "$OUT" | cut -f1)
universe=$(du -h "$OUT/data/universe.bin.gz" | cut -f1)
tickers=$(du -sh "$OUT/data/tickers" | cut -f1)
n_tickers=$(ls "$OUT/data/tickers" | wc -l | tr -d ' ')
# Median per-ticker transfer, derived rather than hardcoded — it changes
# whenever TICKER_FIELDS or the history window changes.
per_ticker_kb=$(ls -l "$OUT/data/tickers" | awk 'NR>1{print $5}' | sort -n \
  | awk '{a[NR]=$1} END{printf "%.0f", a[int(NR/2)]/1024}')
base_kb=$(du -sk "$OUT/data" --exclude=tickers 2>/dev/null | cut -f1 || \
  echo $(( $(du -sk "$OUT/data" | cut -f1) - $(du -sk "$OUT/data/tickers" | cut -f1) )))

cat <<EOF

==> Done: $OUT

  total on disk        $total
  universe.bin.gz      $universe   (strategy mode: fetched once)
  tickers/             $tickers   ($n_tickers files, lazily fetched in manual mode)

First load transfers roughly:
  manual mode     ~0.2 MB  + ~${per_ticker_kb} kB per ticker you pick
  strategy mode   ~$universe (the universe bundle, cached by the browser after)

Per-ticker files carry Close only (see TICKER_FIELDS in tools/build_web_data.py).
The engine reads nothing else, so shipping OHLCV tripled the payload for data no
strategy touches.

Publish with:
  PAGES=<path to your rahulbiswas.github.io checkout>
  rm -rf "\$PAGES/sid/stocktest"
  mkdir -p "\$PAGES/sid/stocktest"
  cp -R "$OUT/." "\$PAGES/sid/stocktest/"
  cd "\$PAGES" && git add sid/stocktest && git commit -m "Deploy StockTest" && git push
EOF
