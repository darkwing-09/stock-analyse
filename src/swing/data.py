# -*- coding: utf-8 -*-
"""Universe and price-panel loading for the swing engine.

Prices are daily OHLCV from Yahoo Finance, split- and bonus-adjusted
(``auto_adjust=True``) so corporate actions don't create fake gaps in
backtests. Panels are cached on disk for a few hours to avoid re-downloading
100 stocks on every command.
"""

from __future__ import annotations

import logging
import pickle
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from data_provider.india_indices import IN_BENCHMARK_SYMBOL, NSE_INDUSTRY_TO_SECTOR

logger = logging.getLogger(__name__)

PACKAGE_DATA = Path(__file__).resolve().parent / "data"
UNIVERSE_FILES = {"nifty100": PACKAGE_DATA / "nifty100.csv", "nifty500": PACKAGE_DATA / "nifty500.csv"}
NSE_UNIVERSE_URLS = {
    "nifty100": "https://archives.nseindia.com/content/indices/ind_nifty100list.csv",
    "nifty500": "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
}
DEFAULT_CACHE_DIR = Path("data/swing_cache")
FIELDS = ("open", "high", "low", "close", "volume")


@dataclass(frozen=True)
class Stock:
    symbol: str      # Yahoo form, e.g. RELIANCE.NS
    name: str
    industry: str
    sector: str      # sector index code from data_provider.india_indices


def load_universe(name: str = "nifty100", path: Optional[Path] = None) -> List[Stock]:
    """Constituents from the bundled NSE snapshot (refresh with ``refresh_universe``)."""
    frame = pd.read_csv(path or UNIVERSE_FILES[name])
    stocks = []
    for _, row in frame.iterrows():
        industry = str(row["Industry"]).strip()
        stocks.append(
            Stock(
                symbol=f"{str(row['Symbol']).strip().upper()}.NS",
                name=str(row["Company Name"]).strip(),
                industry=industry,
                sector=NSE_INDUSTRY_TO_SECTOR.get(industry, "OTHER"),
            )
        )
    return stocks


def stocks_from_symbols(symbols: List[str], universe: Optional[List[Stock]] = None) -> List[Stock]:
    """Build Stock entries for an ad-hoc list, borrowing names/sectors from the universe."""
    known = {s.symbol: s for s in (universe or load_universe())}
    out = []
    for raw in symbols:
        sym = raw.strip().upper()
        if not sym:
            continue
        out.append(known.get(sym, Stock(symbol=sym, name=sym, industry="", sector="OTHER")))
    return out


def refresh_universe(name: str = "nifty100") -> int:
    """Download the latest constituent CSV from NSE archives into the package snapshot."""
    import requests

    resp = requests.get(NSE_UNIVERSE_URLS[name], headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
    resp.raise_for_status()
    text = resp.text
    if "Symbol" not in text.splitlines()[0]:
        raise ValueError("unexpected NSE response")
    UNIVERSE_FILES[name].write_text(text, encoding="utf-8")
    return len(text.strip().splitlines()) - 1


def _download(symbols: List[str], start: str, end: Optional[str]) -> Dict[str, pd.DataFrame]:
    import yfinance as yf

    raw = yf.download(
        symbols,
        start=start,
        end=end,
        interval="1d",
        auto_adjust=True,
        group_by="ticker",
        threads=True,
        progress=False,
    )
    panel: Dict[str, pd.DataFrame] = {}
    for field in FIELDS:
        cols = {}
        for sym in symbols:
            try:
                cols[sym] = raw[sym][field.capitalize()]
            except KeyError:
                continue
        frame = pd.DataFrame(cols)
        frame.index = pd.to_datetime(frame.index).tz_localize(None).normalize()
        panel[field] = frame.sort_index()
    return panel


def load_prices(
    symbols: List[str],
    *,
    start: str,
    end: Optional[str] = None,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    max_age_hours: float = 6.0,
    refresh: bool = False,
) -> Dict[str, pd.DataFrame]:
    """Wide panels per field plus ``panel['benchmark']`` (Nifty 50 close as a 1-column frame)."""
    wanted = sorted(set(symbols) | {IN_BENCHMARK_SYMBOL})
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = f"{start}_{end or 'latest'}_{len(wanted)}_{abs(hash(tuple(wanted))) % 10**8}.pkl"
    cache_file = cache_dir / key
    if not refresh and cache_file.exists() and (time.time() - cache_file.stat().st_mtime) < max_age_hours * 3600:
        with cache_file.open("rb") as fh:
            return pickle.load(fh)

    logger.info("[swing] downloading %d symbols from %s", len(wanted), start)
    panel = _download(wanted, start, end)
    close = panel["close"]
    panel["benchmark"] = close[[IN_BENCHMARK_SYMBOL]].copy()
    for field in FIELDS:
        panel[field] = panel[field].drop(columns=[IN_BENCHMARK_SYMBOL], errors="ignore")
    with cache_file.open("wb") as fh:
        pickle.dump(panel, fh)
    return panel
