"""Download the research-only instruments into research/lab/data/.

The site's own data/ directory is never touched: these files exist so the strategy
search can (a) use instruments the site does not ship yet (cash/bond ladders,
factor ETFs, leveraged ETFs, country funds), (b) read signal series (VIX, the
Treasury yield curve), and (c) test strategies on decades the ETF era does not
cover, through index and sector mutual funds that go back to the 1980s.

Same file format as download_data.py (Date,Open,High,Low,Close,Volume, total-
return adjusted). Mutual funds and indices report zero volume, which the engine
would treat as "untradable"; research/lab/data.py drops their Volume column on
load, so nothing here is rewritten.

    .venv/bin/python research/lab/fetch_extra.py            # skip existing
    .venv/bin/python research/lab/fetch_extra.py --force
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd
import yfinance as yf

OUT = Path(__file__).resolve().parent / "data"

GROUPS: dict[str, list[str]] = {
    "cash_bonds": [
        "BIL", "SHV", "SGOV", "SHY", "IEI", "IEF", "TLH", "GOVT", "BND", "TIP", "LQD",
        "HYG", "JNK", "MUB", "EMB", "MBB", "VGSH", "VGIT", "VGLT", "EDV", "ZROZ",
        "SCHO", "SCHR", "FLOT", "BSV", "BIV", "BLV", "VCIT", "VCSH", "STIP",
    ],
    "us_equity": [
        "IVV", "IJH", "IJS", "IJT", "IWN", "IWO", "IWB", "IWV", "IWR", "IWS", "IWP",
        "VUG", "VTV", "VB", "VO", "VBR", "VBK", "VXF", "VV", "SCHD", "DVY", "VIG",
        "SPLV", "USMV", "MTUM", "QUAL", "VLUE", "SIZE", "RPV", "RPG", "RZV", "RZG",
        "OEF", "MGK", "MGC", "XLG", "SPYG", "SPYV", "ONEQ", "QQQE", "SPHB", "SPHQ",
        "SDY", "FDN", "IGV", "SMH", "SOXX", "IBB", "XBI", "KBE", "KRE", "XHB", "XRT",
        "ITB", "IYT", "XOP", "XME", "IYR", "VNQ", "RWR", "ICF", "IYW", "IYF", "IYH",
        "IYE", "IYC", "IYK", "IYJ", "IYM", "IDU", "IYZ", "VGT", "VHT", "VFH", "VDE",
        "VCR", "VDC", "VIS", "VAW", "VPU", "VOX", "RSPT", "SCHG", "SCHX", "SCHB",
        "SCHA", "SCHV", "VYM", "NOBL", "MOAT", "PKW", "QDF", "DGRO", "COWZ", "SPMO",
        "XMMO", "PDP", "FVD", "IUSG", "IUSV", "IVW", "IVE", "IWY", "IWX",
    ],
    "intl": [
        "EWJ", "EWG", "EWU", "EWC", "EWA", "EWH", "EWS", "EWZ", "EWT", "EWY", "EWW",
        "EWL", "EWP", "EWQ", "EWI", "EWN", "EWD", "EWK", "EWO", "EWM", "FXI", "INDA",
        "EZU", "IEV", "EPP", "ILF", "VGK", "VPL", "VEU", "VXUS", "ACWI", "IEFA",
        "IEMG", "SCZ", "VSS", "EFV", "EFG", "IDV", "DLS", "EWX", "VT", "IXUS",
    ],
    "real_assets": ["IAU", "DBC", "GSG", "DBA", "PDBC", "GLDM", "DBB", "UNG", "IGF", "VNQI"],
    "leveraged": [
        "SSO", "UPRO", "SPXL", "QLD", "TQQQ", "ROM", "UWM", "SAA", "MVV", "DDM",
        "UBT", "TMF", "UGL", "TNA", "URTY", "SPUU", "USD", "UYG", "DIG", "URE",
    ],
    "inverse": ["SH", "PSQ", "SDS", "DOG", "RWM"],
    "index": [
        "^GSPC", "^SP500TR", "^VIX", "^VIX3M", "^VXV", "^IRX", "^FVX", "^TNX", "^TYX",
        "^NDX", "^IXIC", "^RUT", "^DJI", "^SP400", "^SP600", "^XAU",
    ],
    "mutual_funds": [
        # broad index funds (decades of total-return history)
        "VFINX", "VFIAX", "VTSMX", "NAESX", "VIVAX", "VIGRX", "VEXMX", "VMVIX",
        "VGTSX", "VEIEX", "VEURX", "VPACX", "VTRIX", "VWIGX", "PRITX", "FOSFX",
        # bonds / cash proxies
        "VBMFX", "VUSTX", "VFITX", "VFISX", "VWESX", "VWEHX", "VFIIX", "VBISX",
        "VBIIX", "VBLTX", "VIPSX", "VWSTX", "VWITX", "VWLTX", "FGOVX", "FSTGX",
        # balanced / multi-asset / classic active
        "VWELX", "VWINX", "PRPFX", "FMAGX", "FCNTX", "PRGFX", "AGTHX", "VWUSX",
        "VWNDX", "VPMCX", "DODGX", "SGENX", "FPURX", "FBALX", "VGSTX",
        # Vanguard sector funds
        "VGENX", "VGHCX", "VGPMX", "VGSIX",
        # Fidelity Select sector funds (1980s inception)
        "FSPTX", "FSELX", "FSCSX", "FBIOX", "FSPHX", "FSMEX", "FSENX", "FSESX",
        "FSUTX", "FSRBX", "FSLBX", "FSPCX", "FSCPX", "FDFAX", "FSRPX", "FSDAX",
        "FSAIX", "FSCHX", "FSAGX", "FSRFX", "FSHOX", "FIDSX", "FSTCX", "FBSOX",
        "FDCPX", "FSAVX", "FSNGX", "FSDPX", "FCYIX", "FSLSX", "FBMPX", "FSHCX",
        "FSVLX", "FDLSX", "FWRLX", "FSCGX", "FPHAX", "FNARX", "FSLEX", "FSENX",
    ],
}


def download(ticker: str, force: bool) -> str:
    safe = ticker.replace("^", "IDX_")
    out = OUT / f"{safe}.csv"
    if out.exists() and not force:
        return "skip"
    for attempt in range(3):
        try:
            df = yf.download(ticker, period="max", auto_adjust=True, progress=False,
                             threads=False)
            break
        except Exception as e:  # noqa: BLE001
            if attempt == 2:
                return f"error: {e}"
            time.sleep(2 + 3 * attempt)
    if df is None or df.empty:
        return "empty"
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df[[c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]]
    df = df.dropna(subset=["Close"])
    df = df[df["Close"] > 0]
    df.index.name = "Date"
    df.to_csv(out)
    return f"ok {len(df)} rows {df.index[0].date()} -> {df.index[-1].date()}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--groups", nargs="*", default=list(GROUPS))
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    for g in args.groups:
        for t in GROUPS[g]:
            if t in seen:
                continue
            seen.add(t)
            status = download(t, args.force)
            print(f"{g:13s} {t:9s} {status}", flush=True)
            if status != "skip":
                time.sleep(0.3)


if __name__ == "__main__":
    main()
