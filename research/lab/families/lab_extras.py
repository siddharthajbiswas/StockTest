"""Lab additions made during verification (kept out of core.py so existing
cache keys stay valid).

* VFINXR (research/lab/data/VFINXR.csv): VFINX with its 1980-86 unadjusted
  capital-gain distribution days (1980-12-30, 1981-12-29, 1983-12-28,
  1984-12-28, 1985-12-27, 1986-12-09: e.g. -7.0% vs the S&P's -0.75%) replaced
  by the S&P 500's return that day; identical to VFINX from 1987 on.
* Protocols "long_r" / "long_r_screen": the long protocols benchmarked on
  VFINXR. Use them (and VFINXR as the S&P asset) for any 1986+ result.
"""
from .. import core as _core

_core.PROTOCOLS.setdefault("long_r", _core._mk("long_r", "1986-01-01", "2023-07-01", "1986-04-01",
                                                benchmark="VFINXR"))
_core.PROTOCOLS.setdefault("long_r_screen", _core._mk("long_r_screen", "1986-01-01", "2023-01-01",
                                                       "1986-04-01", benchmark="VFINXR", step="YS"))


# --------------------------------------------------------------------------
# Cache-poisoning fix (critic P0). registry.code_version used to read source
# files from disk at call time, while forked sweep workers execute the module
# imported when the pool started; a mid-sweep edit stored OLD-code results
# under the NEW hash. Snapshot every lab/family source file the first time it
# is seen (all family modules are imported together by load_families, so the
# snapshot is the imported code), and hash the snapshots. Hashes of unchanged
# files are byte-identical to before, so existing cache entries stay valid.
# --------------------------------------------------------------------------
import hashlib as _hashlib
from pathlib import Path as _Path

from .. import registry as _registry

_SNAP: dict = {}
_FAMDIR = _Path(__file__).resolve().parent
_LABDIR = _FAMDIR.parent


def _snap(path) -> bytes:
    key = str(path)
    b = _SNAP.get(key)
    if b is None:
        try:
            b = _Path(path).read_bytes()
        except OSError:
            b = b""
        _SNAP[key] = b
    return b


for _f in list(_FAMDIR.glob("*.py")) + [_LABDIR / n for n in ("core.py", "blocks.py", "registry.py", "data.py")]:
    _snap(_f)


def _code_version(cfg: dict) -> str:
    k = _registry.kind_of(cfg)
    files = [_LABDIR / "core.py", _LABDIR / "blocks.py", _LABDIR / "registry.py", _LABDIR / "data.py"]
    if k.source:
        files.append(_Path(k.source))
    if cfg["kind"] == "weights" and cfg.get("signal") in _registry.SIGNALS:
        files.append(_Path(_registry.SIGNALS[cfg["signal"]][2]))
    h = _hashlib.sha1()
    for f in dict.fromkeys(files):
        b = _snap(f)
        if b:
            h.update(b)
    return h.hexdigest()[:12]


_registry.code_version = _code_version
