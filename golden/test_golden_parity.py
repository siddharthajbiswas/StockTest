"""Parity tests against the frozen reference oracle.

These re-run every case in `tools/gen_golden.py` through the live Python engine
and diff the result against the committed JSON in this directory. Two jobs:

  1. **Now (pure Python).** Catch silent behaviour changes in the engine — a
     refactor of the tax netting or the portfolio lot accounting that changes
     numbers without breaking a unit test.
  2. **During the TS port.** These same JSON files are the contract the
     JavaScript implementation must reproduce. `compare_payloads` below is
     deliberately written as a spec of *what* must match and *how closely*, so
     the TS-side checker can mirror it.

Run:  .venv/bin/python -m pytest golden -q
Regenerate (only when a change to the numbers is intended and reviewed):
      .venv/bin/python tools/gen_golden.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
GOLDEN_DIR = ROOT / "golden"

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "reference"))
sys.path.insert(0, str(ROOT / "tools"))

# Python-vs-Python should be exact; this leaves headroom for a libm difference
# across machines without letting real drift through.
REL_TOL = 1e-12
ABS_TOL = 1e-9


def _cases():
    from gen_golden import CASES
    return CASES


@pytest.fixture(scope="module")
def svc():
    from service import EngineService
    return EngineService()


def approx_equal(a, b, path: str, errors: list[str]) -> None:
    """Structural + numeric comparison, collecting every mismatch.

    Reports all differences rather than dying on the first one — when a port
    drifts you want the whole picture, not a single line.
    """
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                errors.append(f"{path}.{k}: missing in actual")
            elif k not in b:
                errors.append(f"{path}.{k}: unexpected in actual")
            else:
                approx_equal(a[k], b[k], f"{path}.{k}", errors)
        return
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            errors.append(f"{path}: length {len(b)} != golden {len(a)}")
            return
        for i, (x, y) in enumerate(zip(a, b)):
            approx_equal(x, y, f"{path}[{i}]", errors)
        return
    if isinstance(a, bool) or isinstance(b, bool):
        if a != b:
            errors.append(f"{path}: {b!r} != golden {a!r}")
        return
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if a == b:
            return
        diff = abs(a - b)
        if diff <= ABS_TOL or diff <= REL_TOL * max(abs(a), abs(b)):
            return
        errors.append(f"{path}: {b!r} != golden {a!r} (diff {diff:g})")
        return
    if a != b:
        errors.append(f"{path}: {b!r} != golden {a!r}")


def compare_payloads(golden: dict, actual: dict) -> list[str]:
    """The contract. Returns a list of human-readable mismatches (empty = pass).

    Everything under `result` is compared: metrics, both equity curves, the
    benchmark, the full trade blotter, and the round trips. Trade dates,
    tickers and sides are compared exactly (they are strings); shares, prices
    and values numerically.
    """
    errors: list[str] = []
    approx_equal(golden["result"], actual["result"], "result", errors)
    return errors


@pytest.mark.parametrize("case", _cases(), ids=lambda c: c["id"])
def test_case_matches_golden(svc, case):
    from gen_golden import build_payload

    path = GOLDEN_DIR / f"{case['id']}.json"
    assert path.exists(), (
        f"missing golden {path.name} — run: .venv/bin/python tools/gen_golden.py"
    )
    golden = json.loads(path.read_text())
    actual = build_payload(svc, case)

    errors = compare_payloads(golden, actual)
    assert not errors, (
        f"{case['id']}: {len(errors)} mismatch(es) vs frozen oracle\n"
        + "\n".join(f"  {e}" for e in errors[:25])
        + ("\n  ..." if len(errors) > 25 else "")
    )


def test_manifest_matches_files():
    """The manifest's per-case hashes must match the files on disk, so a
    hand-edited golden can't quietly become the new truth."""
    import hashlib

    manifest = json.loads((GOLDEN_DIR / "manifest.json").read_text())
    for entry in manifest["cases"]:
        path = GOLDEN_DIR / entry["file"]
        assert path.exists(), f"manifest lists missing file {entry['file']}"
        actual = hashlib.sha256(path.read_text().encode()).hexdigest()
        assert actual == entry["sha256"], (
            f"{entry['file']} was modified after generation "
            f"(sha256 {actual[:12]}… != manifest {entry['sha256'][:12]}…)"
        )


def test_tax_toggle_isolates_tax_engine():
    """manual_buyhold_tax and manual_buyhold_notax differ only in the tax flag.

    With taxes off, pretax and aftertax curves must be identical and there must
    be no tax charged. With taxes on, tax must be strictly positive over a
    winning window. This is the assertion that would catch a port wiring the
    tax policy through but never applying it.
    """
    off = json.loads((GOLDEN_DIR / "manual_buyhold_notax.json").read_text())["result"]
    on = json.loads((GOLDEN_DIR / "manual_buyhold_tax.json").read_text())["result"]

    assert off["equity_curve"]["pretax"] == off["equity_curve"]["aftertax"]
    assert not off["metrics"].get("total_tax")

    assert on["metrics"]["total_tax"] > 0
    # Taxes are a drag: the after-tax final value must trail the pre-tax one.
    assert on["metrics"]["final_value_pretax"] > on["metrics"]["final_value"] - 1e-9

    # Same strategy, same window, so the pre-tax lines must agree exactly —
    # turning taxes on must not perturb the gross simulation.
    assert on["equity_curve"]["pretax"] == off["equity_curve"]["pretax"]
