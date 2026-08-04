"""Ticker discovery for manual (self-pick) mode.

Builds an in-memory index of the fixed local universe (~530 tickers) once, at
startup, joined with whatever metadata the fundamentals snapshot happens to
carry. IMPORTANT: this is a *fixed* universe, not "any stock" — there is a row
here only if we have a local price CSV for it.

Company names come from `data/company_names.csv` (written by
`tools/fetch_company_names.py`). They are deliberately NOT a column of the
fundamentals snapshot: `tools/build_web_data.py` bundles every non-ticker
fundamentals column into the numeric factor matrix the pickers rank on, so a
string name column would ride along into data no strategy reads. As a fallback
the join still looks for a name column on the snapshot, so a future vendor file
that carries one lights up with no code change.
"""

from __future__ import annotations

import math
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

# Columns we'll treat as a human-readable company name if the snapshot has one.
_NAME_COLUMNS = ("name", "longName", "shortName", "companyName", "company")
# Default location of the dedicated names file (tools/fetch_company_names.py).
NAMES_PATH = Path(__file__).resolve().parents[1] / "data" / "company_names.csv"
_FUZZY_THRESHOLD = 0.6  # min SequenceMatcher ratio for a fuzzy symbol match


def _clean(x) -> float | None:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


class TickerIndex:
    def __init__(
        self,
        prices: dict[str, pd.DataFrame],
        fundamentals_path: Path | str,
        names_path: Path | str | None = None,
    ):
        fund = self._load_fundamentals(fundamentals_path)
        name_col = next((c for c in _NAME_COLUMNS if c in fund.columns), None)
        names = self._load_names(
            NAMES_PATH if names_path is None else names_path
        )

        self.records: list[dict] = []
        for symbol in sorted(prices):
            df = prices[symbol]
            row = fund.loc[symbol] if symbol in fund.index else None
            # The dedicated names file wins; the snapshot column is the fallback.
            name = names.get(symbol)
            market_cap = None
            if row is not None:
                if name is None and name_col is not None:
                    raw = row.get(name_col)
                    name = None if (raw is None or (isinstance(raw, float) and math.isnan(raw))) else str(raw)
                if "marketCap" in fund.columns:
                    market_cap = _clean(row.get("marketCap"))
            self.records.append(
                {
                    "symbol": symbol,
                    "name": name,
                    "has_fundamentals": row is not None,
                    "market_cap": market_cap,
                    "date_from": df.index[0].date().isoformat() if len(df) else None,
                    "date_to": df.index[-1].date().isoformat() if len(df) else None,
                }
            )
        self._by_symbol = {r["symbol"]: r for r in self.records}
        # True when any record actually carries a name, rather than merely when a
        # source was configured — the UI uses this to decide whether to offer
        # name-based search at all, and an empty names file should read as "no".
        self.has_name_data = any(r["name"] for r in self.records)

    @staticmethod
    def _load_fundamentals(path: Path | str) -> pd.DataFrame:
        path = Path(path)
        if not path.exists():
            return pd.DataFrame()
        return pd.read_csv(path, index_col="ticker")

    @staticmethod
    def _load_names(path: Path | str) -> dict[str, str]:
        """{symbol: company name}, empty when the file hasn't been fetched."""
        path = Path(path)
        if not path.exists():
            return {}
        df = pd.read_csv(path).dropna(subset=["name"])
        return {str(t): str(n) for t, n in zip(df["ticker"], df["name"])}

    # ---- API-facing views -----------------------------------------------
    def all(self) -> list[dict]:
        return self.records

    def count(self) -> int:
        return len(self.records)

    def search(self, q: str, limit: int = 20) -> list[dict]:
        """Prefix/substring/fuzzy match against symbol (and name when present).

        Ranking, best first: exact symbol > symbol prefix > symbol substring >
        name prefix > name substring > fuzzy symbol. Ties broken by symbol.
        """
        q = (q or "").strip()
        if not q:
            return []
        qu = q.upper()
        ql = q.lower()

        scored: list[tuple[float, str, dict]] = []
        for r in self.records:
            sym = r["symbol"]
            symu = sym.upper()
            name = r["name"]
            namel = name.lower() if name else None

            score = 0.0
            if symu == qu:
                score = 1000.0
            elif symu.startswith(qu):
                score = 900.0 - len(symu)  # shorter symbol = tighter match
            elif qu in symu:
                score = 700.0
            elif namel and namel.startswith(ql):
                score = 600.0
            elif namel and ql in namel:
                score = 500.0
            else:
                ratio = SequenceMatcher(None, ql, sym.lower()).ratio()
                if namel:
                    ratio = max(ratio, SequenceMatcher(None, ql, namel).ratio())
                if ratio >= _FUZZY_THRESHOLD:
                    score = 100.0 * ratio  # 60..100

            if score > 0:
                scored.append((score, sym, r))

        scored.sort(key=lambda t: (-t[0], t[1]))
        return [r for _, _, r in scored[:limit]]
