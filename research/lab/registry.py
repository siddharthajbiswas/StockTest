"""Config kinds: a config is a JSON dict {"kind": ..., **params}.

Built-in kinds
--------------
"combo"    Anything the website can run today: a picker + timer (+ menu or
           universe, top_n, rebalance, trade_rule standard|tax_managed,
           gain_budget, wash_days). Built from the same classes the site's
           reference service builds, so results are the site's.
             {"kind": "combo", "picker": "momentum",
              "picker_params": {"lookback": 252, "skip": 21},
              "timer": "buy_hold", "timer_params": {}, "top_n": 5,
              "rebalance": "Q", "menu": [...], "trade_rule": "tax_managed",
              "gain_budget": 0.01, "wash_days": 31}
           Manual mode (site's "pick stocks yourself"): "tickers": [...]
           instead of picker/menu. Universe mode: "universe": "sp500-pit" or
           "all" instead of a menu (heavy: loads every stock).
"buyhold"  Buy fixed weights on the first day and never trade again.
             {"kind": "buyhold", "weights": {"SPY": 0.5, "QQQ": 0.5}}
"weights"  A research WeightStrategy driven by a registered signal:
             {"kind": "weights", "signal": "<name>", "params": {...},
              "rebalance": "M", "execution": "standard"|"tax",
              "gain_budget": 0.01, "wash_days": 31, "band": 0.0, ...}

Families register signals with `register_signal(name, factory, tickers_fn)`
or whole new kinds with `register_kind(name, build, tickers, heavy, universe)`.
Each family lives in research/lab/families/<family>.py and is auto-imported.
"""
from __future__ import annotations

import hashlib
import importlib
import inspect
import pkgutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from backtester import Combo, Strategy, TaxManagedCombo

LAB = Path(__file__).resolve().parent


@dataclass
class Kind:
    build: Callable[[dict], Strategy]
    tickers: Callable[[dict], list]
    heavy: Callable[[dict], bool]
    universe: Callable[[dict], str]
    source: str                      # file whose content versions the cache


KINDS: dict[str, Kind] = {}
SIGNALS: dict[str, tuple] = {}       # name -> (factory(params)->Signal, tickers(params)->list, source)


def _src(fn) -> str:
    try:
        return inspect.getsourcefile(fn) or ""
    except TypeError:
        return ""


def register_kind(name, build, tickers, heavy=lambda c: False, universe=lambda c: "menu"):
    KINDS[name] = Kind(build, tickers, heavy, universe, _src(build))


def register_signal(name, factory, tickers):
    SIGNALS[name] = (factory, tickers, _src(factory))


# ---------------------------------------------------------------- "combo"
def _combo_build(c: dict) -> Strategy:
    from strategies.pickers import PICKERS
    from strategies.timers import TIMERS

    timer = TIMERS[c.get("timer", "buy_hold")](**c.get("timer_params", {}))
    rule = c.get("trade_rule", "standard")
    cls = TaxManagedCombo if rule == "tax_managed" else Combo
    kw = {}
    if rule == "tax_managed":
        kw = dict(gain_budget=c.get("gain_budget", 0.01), wash_days=c.get("wash_days", 31))
    if c.get("tickers"):
        import sys
        sys.path.insert(0, str(LAB.parents[1] / "reference"))
        from service import FixedListPicker  # the site's manual-mode picker
        return cls(FixedListPicker(c["tickers"]), timer, top_n=max(1, len(c["tickers"])),
                   rebalance=c.get("rebalance", "M"), **kw)
    picker = PICKERS[c["picker"]](**c.get("picker_params", {}))
    menu = c.get("menu")
    if menu:
        from . import data
        menu = [t for t in menu if data.path_for(t) is not None]
    return cls(picker, timer, top_n=c.get("top_n", 15), rebalance=c.get("rebalance", "M"),
               menu=menu, **kw)


def _combo_tickers(c: dict) -> list:
    base = c.get("tickers") or c.get("menu") or []
    return list(dict.fromkeys(list(base) + ["SPY"]))


register_kind(
    "combo", _combo_build, _combo_tickers,
    heavy=lambda c: not (c.get("tickers") or c.get("menu")),
    universe=lambda c: "menu" if (c.get("tickers") or c.get("menu")) else c.get("universe", "sp500-pit"),
)


# ---------------------------------------------------------------- "buyhold"
class BuyHoldWeights(Strategy):
    def __init__(self, weights: dict):
        self.weights = dict(weights)

    def initialize(self, ctx):
        self.done = False

    def on_day(self, ctx):
        if self.done:
            return
        live = {t: w for t, w in self.weights.items() if ctx.price(t) is not None}
        if not live:
            return
        s = sum(live.values())
        pv = ctx.portfolio_value
        for t, w in sorted(live.items()):
            px = ctx.price(t)
            ctx.order(t, pv * w / s / (px * (1 + ctx.slippage_pct) * (1 + ctx.commission_pct)) * 0.999999)
        self.done = True


register_kind("buyhold", lambda c: BuyHoldWeights(c["weights"]),
              lambda c: list(dict.fromkeys(list(c["weights"]) + ["SPY"])))


# ---------------------------------------------------------------- "weights"
_WS_KEYS = ("rebalance", "execution", "band", "gain_budget", "wash_days", "st_gains",
            "harvest", "harvest_freq", "substitutes", "min_trade_frac")


def _weights_build(c: dict) -> Strategy:
    from .blocks import WeightStrategy

    factory, _, _ = SIGNALS[c["signal"]]
    sig = factory(c.get("params", {}))
    kw = {k: c[k] for k in _WS_KEYS if k in c}
    return WeightStrategy(sig, **kw)


def _weights_tickers(c: dict) -> list:
    _, tick, _ = SIGNALS[c["signal"]]
    extra = list((c.get("substitutes") or {}).values())
    return list(dict.fromkeys(list(tick(c.get("params", {}))) + extra + ["SPY"]))


register_kind("weights", _weights_build, _weights_tickers)


# ---------------------------------------------------------------- families
_loaded = False
IMPORT_ERRORS: dict = {}


def load_families() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    pkg = importlib.import_module("research.lab.families")
    for m in pkgutil.iter_modules(pkg.__path__):
        if m.name.startswith("_"):
            continue
        # Fault isolation: one family's broken module must not break every
        # other family's sweeps (they all share this auto-import).
        try:
            importlib.import_module(f"research.lab.families.{m.name}")
        except Exception as e:  # noqa: BLE001
            import sys
            print(f"[registry] WARNING: family module {m.name!r} failed to import: "
                  f"{type(e).__name__}: {e}", file=sys.stderr, flush=True)
            IMPORT_ERRORS[m.name] = f"{type(e).__name__}: {e}"


def kind_of(cfg: dict) -> Kind:
    load_families()
    return KINDS[cfg["kind"]]


def tickers_of(cfg: dict) -> list:
    return kind_of(cfg).tickers(cfg)


def min_start(cfg: dict):
    """Earliest window start this config may be scored from.

    A window may only start once every instrument the config *requires* has
    traded for `require_days` calendar days -- otherwise a strategy that waits
    in cash for a fund's launch gets credit for dodging whatever happened
    before it (e.g. VUG, launched 2004, "missing" the 2000-02 crash).
      cfg["requires"]      tickers that must exist (buyhold: all its weights)
      cfg["require_days"]  extra days of history needed (e.g. 400 for a
                           12-month signal on a new fund); default 0
      cfg["min_start"]     an explicit date, overriding the above
    """
    import pandas as pd
    from . import data
    if cfg.get("min_start"):
        return pd.Timestamp(cfg["min_start"])
    req = cfg.get("requires")
    if req is None and cfg["kind"] == "buyhold":
        req = list(cfg["weights"])
    if not req:
        return None
    first = max(data.first_date(t) for t in req)
    return first + pd.Timedelta(days=int(cfg.get("require_days", 0)))


def code_version(cfg: dict) -> str:
    """Hash of the source files a config's result depends on, so editing a
    family's code (or the lab's execution blocks) invalidates its cache."""
    k = kind_of(cfg)
    files = [LAB / "core.py", LAB / "blocks.py", LAB / "registry.py", LAB / "data.py"]
    if k.source:
        files.append(Path(k.source))
    if cfg["kind"] == "weights" and cfg.get("signal") in SIGNALS:
        files.append(Path(SIGNALS[cfg["signal"]][2]))
    h = hashlib.sha1()
    for f in dict.fromkeys(files):
        try:
            h.update(Path(f).read_bytes())
        except OSError:
            pass
    return h.hexdigest()[:12]
