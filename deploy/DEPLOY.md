# Deploying StockTest to biswas.net/sid/stocktest

StockTest is a **static site**. There is no backend, no VM, no database and no
API. The engine is a TypeScript port of `backtester/` that runs in a Web Worker
in the browser, and the price data ships as a binary bundle the worker fetches.

A deploy is therefore: build one directory, copy it into the Pages repo, push.

> **Previously** this app ran a FastAPI backend on a Google Cloud VM behind
> Caddy at `stocktest-api.biswas.net`. That is all gone — see
> [Retiring the old backend](#retiring-the-old-backend) for the teardown steps,
> which are **not** automatic.

---

## Prerequisites

You need the price data locally. It is not in git (large, and the provider's
terms don't permit redistributing it — see [Data](#data)).

```bash
cd <this repo>
.venv/bin/python download_data.py          # per-ticker OHLCV CSVs -> data/
.venv/bin/python fetch_fundamentals.py     # fundamentals snapshot
```

Then build the browser bundle from it:

```bash
.venv/bin/python tools/build_web_data.py   # binary price bundle -> build/webdata/
.venv/bin/python tools/gen_web_metadata.py # catalog + ticker index
```

`build_web_data.py --verify` round-trips every file back and checks it against
the source CSVs; worth running after a data refresh.

---

## Build and publish

```bash
bash deploy/build-pages.sh                 # -> build/pages/
```

That builds the frontend with `VITE_BASE=/sid/stocktest/`, copies in the
gzipped data bundle, and prints the exact publish commands. Then:

```bash
PAGES=<path to your rahulbiswas.github.io checkout>
rm -rf "$PAGES/sid/stocktest"
mkdir -p "$PAGES/sid/stocktest"
cp -R build/pages/. "$PAGES/sid/stocktest/"
cd "$PAGES" && git add sid/stocktest && git commit -m "Deploy StockTest" && git push
```

Open <https://biswas.net/sid/stocktest/>.

### What gets served

| Artifact | Size (gzip) | When it loads |
|---|---|---|
| App bundle (JS/CSS/HTML) | ~68 kB | Always |
| `manifest`, `calendar`, `catalog`, `tickers`, `fundamentals`, `sp500-pit` | ~150 kB | Always |
| `universe.bin.gz` | 12.6 MB | Strategy mode only |
| `tickers/<SYM>.bin.gz` | ~25 kB each | Manual mode, per ticker picked |

So picking your own stocks costs well under a megabyte; letting a strategy pick
downloads the 12.6 MB universe once, after which the browser caches it.

**Only closing prices are published.** The engine reads `Close` and nothing else
— Volume is used solely for a tradability test, which is precomputed into a bit
at build time, and Open/High/Low were only ever there for a chart that does not
exist. Dropping them took the published tree from 79 MB to 27 MB and changed no
backtest result (the golden suite verifies this). See `TICKER_FIELDS` in
`tools/build_web_data.py`; the file format is self-describing, so adding a field
back is a rebuild, not a code change.

**Compression is done by us, not the host.** GitHub Pages compresses by content
type and leaves `application/octet-stream` alone, so the worker fetches the
`.gz` files and inflates them with `DecompressionStream`
(`web/engine/src/worker/worker.ts`). Nothing needs configuring server-side; this
is what makes a purely static deploy viable.

`.nojekyll` is written into the output so Pages serves the tree verbatim.

---

## Maintenance

**App change:** re-run `deploy/build-pages.sh`, copy, push.

**Refresh price data:** re-run the two data scripts and the two build scripts
above, then redeploy. There is no cron and no server — it happens when you
choose to do it.

Refreshing the data changes `universe.bin`'s hash, which invalidates the
browser-side result cache automatically (cache keys are namespaced by that
hash), so users won't see stale numbers computed from prices that no longer
exist.

**Saved strategies** live in each visitor's own browser (IndexedDB). There is
nothing to back up, and nothing of theirs on your infrastructure.

---

## Retiring the old backend

These are live resources; the repo cleanup does not touch them. Do these once
the Pages deploy is confirmed working.

1. **Delete the Compute Engine VM** (stops the ~$13–25/mo charge):
   ```bash
   gcloud compute instances delete stocktest --zone=<zone>
   ```
   Or Console → Compute Engine → VM instances → select → Delete.

2. **Release the static IP**, or it keeps billing while unattached:
   ```bash
   gcloud compute addresses list
   gcloud compute addresses delete <name> --region=<region>
   ```

3. **Delete the `stocktest-api` DNS A record** at your registrar for
   `biswas.net`. Do this *after* the VM is gone.

4. **Delete the firewall rules** opened for ports 80/443 if they were created
   just for this.

5. **Remove the GitHub deploy key** used by the VM to clone this repo:
   repo → Settings → Deploy keys.

6. **Cancel the budget alert** if it was specific to this project.

Nothing in the app depends on any of the above; it is purely cost cleanup.

---

## Data

`data/` and `build/` are gitignored. The price data comes from Yahoo Finance via
`yfinance`, whose terms restrict redistribution.

**Publishing this app publicly redistributes that data** — the bundle is
downloaded by every visitor, which is the point of a client-side engine. That is
a licensing question, not a technical one.

What is published has been narrowed to closing prices only (see above), which
removes the bulk-OHLCV shape that most resembles redistributing a market-data
product, and cuts the payload by two thirds. Researched alternatives, none of
which is a drop-in: yfinance, Stooq, Tiingo-free and Alpha-Vantage-free are all
terms-of-service rather than open-data licences, so changing provider mostly
changes whose terms apply. Databento grants explicit redistribution rights but
supplies raw exchange data with no dividend adjustment, and this engine depends
on `auto_adjust=True` total-return prices — `backtester/tax.py` relies on
dividends showing up as price appreciation.

Remaining options if the residual risk matters: keep the deploy private, or have
the app fetch prices per-user at runtime from a provider the visitor is
themselves entitled to use.

---

## Notes

- **Cost:** $0. GitHub Pages is free for public repos; there is no compute.
- **Bandwidth:** Pages has a soft limit of 100 GB/month. At 12.9 MB per
  strategy-mode first load that is roughly 7,700 cold sessions/month, and
  browser caching means repeat visits cost nothing.
- **Repo size:** the published tree is ~27 MB. Pages' published-site limit is
  1 GB, so there is plenty of headroom — but the Pages repo grows by that much
  on each data refresh unless you squash or use a separate branch.
- **Privacy:** every backtest runs on the visitor's own machine. No request
  leaves the browser after the initial asset load, and nothing is logged.
