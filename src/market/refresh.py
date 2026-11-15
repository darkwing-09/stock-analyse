# -*- coding: utf-8 -*-
"""Nightly refresh: universe → prices → per-ticker fundamentals → metrics, scores,
checklist, sector medians → store.

The network lives behind ``Source``; tests inject a fake. Per-symbol failures
are logged and reported, never fatal.
"""

from __future__ import annotations

import json
import logging
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Protocol

import pandas as pd

from data_provider.india_indices import IN_MAIN_INDICES, IN_SECTOR_INDICES
from src.market.metrics import checklist, checklist_summary, compute_technicals, fundamentals_frame, score_universe, sector_medians
from src.market.store import MarketStore
from src.swing.data import Stock, load_prices

logger = logging.getLogger(__name__)

# Yahoo symbols verified live on 2026-11-15.
EXTRA_INDICES = {
    "NIFTY100": ("^CNX100", "Nifty 100"),
    "NIFTYMIDCAP100": ("NIFTY_MIDCAP_100.NS", "Nifty Midcap 100"),
    "NIFTYSMALLCAP100": ("^CNXSC", "Nifty Smallcap 100"),
    "NIFTY500": ("^CRSLDX", "Nifty 500"),
}
ALL_INDICES = {**IN_MAIN_INDICES, **{k: v for k, v in IN_SECTOR_INDICES.items() if k not in IN_MAIN_INDICES}, **EXTRA_INDICES}

STATEMENT_ITEMS = {
    "income": ["Total Revenue", "Operating Revenue", "Gross Profit", "Operating Income", "EBITDA", "Interest Expense",
               "Pretax Income", "Tax Provision", "Net Income", "Diluted EPS", "Basic EPS"],
    "balance": ["Total Assets", "Current Assets", "Cash And Cash Equivalents", "Total Debt", "Net Debt", "Current Liabilities",
                "Total Liabilities Net Minority Interest", "Stockholders Equity", "Retained Earnings", "Ordinary Shares Number"],
    "cashflow": ["Operating Cash Flow", "Capital Expenditure", "Free Cash Flow", "Cash Dividends Paid", "Investing Cash Flow",
                 "Financing Cash Flow", "End Cash Position"],
}


class Source(Protocol):
    def prices(self, symbols: List[str], start: str) -> Dict[str, pd.DataFrame]: ...
    def indices(self, symbols: List[str], start: str) -> pd.DataFrame: ...
    def bundle(self, symbol: str) -> Dict[str, Any]: ...


class YahooSource:
    """Live data from Yahoo Finance via yfinance."""

    def __init__(self, retries: int = 3):
        self.retries = retries

    def prices(self, symbols, start):
        return load_prices(symbols, start=start, refresh=True)

    def indices(self, symbols, start):
        import yfinance as yf

        raw = yf.download(symbols, start=start, interval="1d", auto_adjust=False, group_by="ticker", threads=True, progress=False)
        cols = {}
        for sym in symbols:
            try:
                cols[sym] = raw[sym]["Close"]
            except KeyError:
                continue
        frame = pd.DataFrame(cols)
        frame.index = pd.to_datetime(frame.index).tz_localize(None).normalize()
        return frame.sort_index()

    def bundle(self, symbol):
        import yfinance as yf

        last_err: Optional[Exception] = None
        for attempt in range(self.retries):
            try:
                t = yf.Ticker(symbol)
                return {
                    "info": t.info or {},
                    "quarterly_income": t.quarterly_income_stmt,
                    "annual_income": t.income_stmt,
                    "quarterly_balance": t.quarterly_balance_sheet,
                    "annual_balance": t.balance_sheet,
                    "quarterly_cashflow": t.quarterly_cashflow,
                    "annual_cashflow": t.cashflow,
                    "dividends": t.dividends,
                    "splits": t.splits,
                    "news": t.news or [],
                    "calendar": t.calendar or {},
                }
            except Exception as e:  # rate limits, transient HTTP errors
                last_err = e
                time.sleep((2 ** attempt) + random.random())
        raise RuntimeError(f"{symbol}: {last_err}")


# ----------------------------------------------------------------------------- helpers

def _statement_rows(symbol: str, period_type: str, statement: str, frame: Optional[pd.DataFrame]) -> List[Dict[str, Any]]:
    if frame is None or getattr(frame, "empty", True):
        return []
    rows = []
    wanted = STATEMENT_ITEMS[statement]
    for item in wanted:
        if item not in frame.index:
            continue
        for period, value in frame.loc[item].items():
            if value is None or pd.isna(value):
                continue
            rows.append({"symbol": symbol, "period_type": period_type, "statement": statement, "item": item,
                         "period_end": pd.Timestamp(period).date().isoformat(), "value": float(value)})
    return rows


def _action_rows(symbol: str, dividends, splits) -> List[Dict[str, Any]]:
    rows = []
    for kind, series in (("dividend", dividends), ("split", splits)):
        if series is None or len(series) == 0:
            continue
        for date, value in series.items():
            rows.append({"symbol": symbol, "date": pd.Timestamp(date).tz_localize(None).date().isoformat() if getattr(pd.Timestamp(date), "tzinfo", None) else pd.Timestamp(date).date().isoformat(), "kind": kind, "value": float(value)})
    return rows


def _news_rows(symbol: str, items) -> List[Dict[str, Any]]:
    rows = []
    for n in items or []:
        c = n.get("content") or n
        title = c.get("title")
        if not title:
            continue
        url = ((c.get("canonicalUrl") or {}).get("url")) or ((c.get("clickThroughUrl") or {}).get("url")) or n.get("link")
        rows.append({"id": n.get("id") or c.get("id") or f"{symbol}-{hash(title)}", "symbol": symbol, "title": title,
                     "publisher": ((c.get("provider") or {}).get("displayName")) or n.get("publisher"),
                     "url": url, "published_at": c.get("pubDate") or n.get("providerPublishTime")})
    return rows


def _date_str(v) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, (list, tuple)):
        return _date_str(v[0]) if v else None
    try:
        return pd.Timestamp(v).date().isoformat()
    except Exception:
        return None


# ----------------------------------------------------------------------------- pipeline

def run_refresh(
    store: MarketStore,
    universe: List[Stock],
    source: Source,
    *,
    universe_name: str = "nifty500",
    prices_only: bool = False,
    workers: int = 3,
    years: float = 3.0,
    progress: Optional[Callable[[str], None]] = None,
) -> Dict[str, Any]:
    say = progress or (lambda msg: logger.info("[market] %s", msg))
    started = time.time()
    symbols = [s.symbol for s in universe]
    start = (datetime.now() - timedelta(days=int(365.25 * years) + 30)).date().isoformat()
    by_symbol = {s.symbol: s for s in universe}

    say(f"downloading prices for {len(symbols)} symbols since {start}")
    panel = source.prices(symbols, start)
    prices_rows = store.write_prices(panel)
    have = [s for s in symbols if s in panel["close"] and panel["close"][s].notna().any()]
    no_prices = sorted(set(symbols) - set(have))
    if no_prices:
        say(f"no price data (delisted or renamed?): {', '.join(no_prices)}")
    symbols = have
    tech = compute_technicals({k: (v[[c for c in v.columns if c in have]] if k != "benchmark" else v) for k, v in panel.items()})

    say("downloading indices")
    try:
        idx_symbols = [sym for sym, _ in ALL_INDICES.values()]
        closes = source.indices(idx_symbols, start)
        store.write_indices(closes, ALL_INDICES)
    except Exception as e:
        logger.warning("[market] indices failed: %s", e)

    failed: List[str] = []
    if prices_only:
        previous = store.load_frame("metrics")
        fund_cols = [c for c in previous.columns if c not in tech.columns and c not in ("name", "industry", "sector", "isin")]
        fund = previous[fund_cols] if len(previous) else fundamentals_frame({s: {} for s in symbols})
        fund = fund.reindex(symbols)
        for col in ("fcf_positive",):
            if col in fund:
                fund[col] = fund[col].astype(object)
    else:
        say(f"fetching fundamentals for {len(symbols)} symbols with {workers} workers")
        infos: Dict[str, Dict[str, Any]] = {}
        stock_rows: List[Dict[str, Any]] = []
        now = datetime.now().isoformat(timespec="seconds")

        def work(sym: str):
            return sym, source.bundle(sym)

        done = 0
        with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
            futures = {pool.submit(work, s): s for s in symbols}
            for fut in as_completed(futures):
                sym = futures[fut]
                try:
                    _, b = fut.result()
                except Exception as e:
                    failed.append(sym)
                    logger.warning("[market] %s failed: %s", sym, e)
                    continue
                info = b.get("info") or {}
                infos[sym] = info
                rows: List[Dict[str, Any]] = []
                for pt in ("quarterly", "annual"):
                    for st in ("income", "balance", "cashflow"):
                        rows += _statement_rows(sym, pt, st, b.get(f"{pt}_{st}"))
                if rows:
                    store.delete_where("financials", "symbol=?", (sym,))
                    store.upsert("financials", rows)
                store.upsert("actions", _action_rows(sym, b.get("dividends"), b.get("splits")))
                store.upsert("news", _news_rows(sym, b.get("news")))
                cal = b.get("calendar") or {}
                meta = by_symbol[sym]
                stock_rows.append({
                    "symbol": sym, "name": meta.name, "industry": meta.industry, "sector": meta.sector, "isin": None,
                    "website": info.get("website"), "summary": info.get("longBusinessSummary"), "employees": info.get("fullTimeEmployees"),
                    "next_earnings": _date_str(cal.get("Earnings Date")), "ex_dividend": _date_str(cal.get("Ex-Dividend Date")), "updated_at": now,
                })
                done += 1
                if done % 25 == 0:
                    say(f"  {done}/{len(symbols)} fundamentals")
        for sym in failed:
            infos.setdefault(sym, {})
            meta = by_symbol[sym]
            if not store.stock(sym):
                stock_rows.append({"symbol": sym, "name": meta.name, "industry": meta.industry, "sector": meta.sector, "isin": None,
                                   "website": None, "summary": None, "employees": None, "next_earnings": None, "ex_dividend": None, "updated_at": now})
        store.upsert("stocks", stock_rows)
        fund = fundamentals_frame({s: infos.get(s, {}) for s in symbols})

    say("computing metrics, scores and checklists")
    ident = pd.DataFrame({"name": [by_symbol[s].name for s in symbols], "industry": [by_symbol[s].industry for s in symbols],
                          "sector": [by_symbol[s].sector for s in symbols]}, index=pd.Index(symbols, name="symbol"))
    frame = ident.join(tech, how="left").join(fund.drop(columns=[c for c in ("long_name",) if c in fund]), how="left")
    frame = score_universe(frame)
    medians = sector_medians(frame)

    check_rows, passed, totals = [], [], []
    for sym, row in frame.iterrows():
        items = checklist(row, medians)
        summary = checklist_summary(items)
        check_rows.append({"symbol": sym, "items": json.dumps(items), **summary})
        passed.append(summary["passed"])
        totals.append(summary["total"])
    frame["checklist_passed"] = passed
    frame["checklist_total"] = totals
    store.upsert("checklists", check_rows)
    frame = frame.drop(columns=[c for c in ("summary", "website") if c in frame])
    store.replace_frame("metrics", frame)
    store.set_meta("sector_medians", medians)

    report = {
        "at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "universe": universe_name, "symbols": len(symbols), "failed": sorted(failed), "no_prices": no_prices, "prices_rows": prices_rows,
        "as_of": str(tech["as_of"].iloc[0]) if len(tech) else None, "prices_only": prices_only,
        "seconds": round(time.time() - started, 1),
    }
    store.set_meta("last_refresh", report)
    say(f"done in {report['seconds']}s; {len(failed)} symbols failed")
    return report
