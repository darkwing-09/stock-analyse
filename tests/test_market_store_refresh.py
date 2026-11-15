# -*- coding: utf-8 -*-
"""Store round-trips and the refresh pipeline (seams: MarketStore, run_refresh) with a fake source."""

import json

import numpy as np
import pandas as pd
import pytest

from src.market.refresh import run_refresh
from src.market.store import MarketStore
from src.swing.data import Stock

N = 320
DAYS = pd.bdate_range("2025-01-01", periods=N)
SYMS = ["AAA.NS", "BBB.NS", "CCC.NS"]


def _panel():
    i = np.arange(N, dtype=float)
    close = pd.DataFrame({"AAA.NS": 100 + i, "BBB.NS": 200 - 0.2 * i, "CCC.NS": 50 + np.sin(i / 9)}, index=DAYS)
    vol = pd.DataFrame({c: np.full(N, 2e6) for c in close}, index=DAYS)
    return {"open": close, "high": close * 1.01, "low": close * 0.99, "close": close, "volume": vol,
            "benchmark": pd.DataFrame({"^NSEI": 20000 + 5 * i}, index=DAYS)}


def _statement(items, periods=4, scale=1e9):
    cols = pd.to_datetime(["2026-09-30", "2026-06-30", "2026-03-31", "2025-12-31"][:periods])
    return pd.DataFrame({c: [scale * (k + 1) * (1 + 0.1 * j) for k in range(len(items))] for j, c in enumerate(cols)}, index=items)


class FakeSource:
    def __init__(self, fail=()):
        self.fail = set(fail)
        self.calls = []

    def prices(self, symbols, start):
        return _panel()

    def indices(self, symbols, start):
        i = np.arange(N, dtype=float)
        return pd.DataFrame({s: 1000 + i * (k + 1) for k, s in enumerate(symbols)}, index=DAYS)

    def bundle(self, symbol):
        self.calls.append(symbol)
        if symbol in self.fail:
            raise RuntimeError("boom")
        return {
            "info": {"longName": f"{symbol} Ltd", "marketCap": 3e12, "trailingPE": 18.0, "returnOnEquity": 0.18,
                     "debtToEquity": 30.0, "dividendYield": 1.2, "freeCashflow": 5e9, "recommendationKey": "buy",
                     "numberOfAnalystOpinions": 12, "targetMeanPrice": 500.0, "currentPrice": 400.0},
            "quarterly_income": _statement(["Total Revenue", "Operating Income", "Net Income", "Diluted EPS"]),
            "annual_income": _statement(["Total Revenue", "Net Income"], periods=3),
            "quarterly_balance": _statement(["Total Assets", "Total Debt", "Stockholders Equity"]),
            "annual_balance": _statement(["Total Assets"], periods=3),
            "quarterly_cashflow": _statement(["Operating Cash Flow", "Free Cash Flow"]),
            "annual_cashflow": _statement(["Free Cash Flow"], periods=3),
            "dividends": pd.Series([5.0, 5.5], index=pd.to_datetime(["2025-08-14", "2026-06-05"])),
            "splits": pd.Series([2.0], index=pd.to_datetime(["2024-10-28"])),
            "news": [{"id": f"n-{symbol}", "content": {"title": f"{symbol} wins order", "pubDate": "2026-11-14T10:00:00Z",
                       "provider": {"displayName": "Wire"}, "canonicalUrl": {"url": "https://example.com/n"}}}],
            "calendar": {"Earnings Date": [pd.Timestamp("2027-01-20").date()], "Ex-Dividend Date": pd.Timestamp("2026-06-05").date()},
        }


UNIVERSE = [Stock("AAA.NS", "AAA Ltd", "Information Technology", "NIFTYIT"),
            Stock("BBB.NS", "BBB Ltd", "Financial Services", "FINNIFTY"),
            Stock("CCC.NS", "CCC Ltd", "Information Technology", "NIFTYIT")]


def test_store_round_trips_frames_rows_and_meta(tmp_path):
    store = MarketStore(tmp_path / "m.db")
    frame = pd.DataFrame({"pe": [10.0, np.nan], "above_sma200": [True, False], "name": ["A", "B"]}, index=pd.Index(["A.NS", "B.NS"], name="symbol"))
    store.replace_frame("metrics", frame)
    back = store.load_frame("metrics")
    assert list(back.index) == ["A.NS", "B.NS"] and np.isnan(back.loc["B.NS", "pe"]) and back.loc["A.NS", "above_sma200"] == True  # noqa: E712
    store.set_meta("last_refresh", {"at": "2026-11-15T17:00:00+05:30", "n": 2})
    assert store.get_meta("last_refresh")["n"] == 2 and store.get_meta("missing") is None
    store.upsert("news", [{"id": "x", "symbol": "A.NS", "title": "t", "publisher": "p", "url": "u", "published_at": "2026-11-14T10:00:00Z"}])
    store.upsert("news", [{"id": "x", "symbol": "A.NS", "title": "t2", "publisher": "p", "url": "u", "published_at": "2026-11-14T10:00:00Z"}])
    assert [n["title"] for n in store.news("A.NS")] == ["t2"]


def test_refresh_populates_every_table_and_survives_one_failure(tmp_path):
    store = MarketStore(tmp_path / "m.db")
    src = FakeSource(fail={"BBB.NS"})
    report = run_refresh(store, UNIVERSE, src, workers=2, years=1.0)
    assert report["symbols"] == 3 and report["failed"] == ["BBB.NS"] and report["prices_rows"] > 0
    m = store.load_frame("metrics")
    assert set(m.index) == set(SYMS)
    assert m.loc["AAA.NS", "ret_1m"] == pytest.approx((100 + N - 1) / (100 + N - 1 - 22) - 1)
    assert m.loc["AAA.NS", "pe"] == 18.0 and np.isnan(m.loc["BBB.NS", "pe"])          # failed bundle leaves fundamentals blank
    assert m.loc["AAA.NS", "debt_to_equity"] == pytest.approx(0.30)
    assert m["quality_score"].between(0, 100).all() and m["overall"].isin(["Strong", "Mixed", "Weak"]).all()
    assert m.loc["AAA.NS", "checklist_passed"] >= 1 and m.loc["AAA.NS", "checklist_total"] >= 15
    assert m.loc["AAA.NS", "sector"] == "NIFTYIT" and m.loc["AAA.NS", "name"] == "AAA Ltd"
    px = store.prices("AAA.NS")
    assert len(px) == N and list(px.columns) == ["open", "high", "low", "close", "volume"] and px["close"].iloc[-1] == 100 + N - 1
    fin = store.financials("AAA.NS")
    assert fin["quarterly"]["income"]["Total Revenue"][0]["period_end"] == "2026-09-30"
    assert len(fin["annual"]["cashflow"]["Free Cash Flow"]) == 3
    assert [a["kind"] for a in store.actions("AAA.NS")] == ["split", "dividend", "dividend"]
    assert store.news("AAA.NS")[0]["title"] == "AAA.NS wins order"
    stock = store.stock("CCC.NS")
    assert stock["industry"] == "Information Technology" and stock["next_earnings"] == "2027-01-20"
    meta = store.get_meta("last_refresh")
    assert meta["universe"] == "nifty500" and meta["failed"] == ["BBB.NS"]
    assert store.get_meta("sector_medians")["NIFTYIT"]["pe"] == 18.0
    idx = store.indices_latest()
    assert {i["code"] for i in idx} >= {"NIFTY50", "SENSEX"} and all("change_pct" in i for i in idx)
    assert store.search("aaa")[0]["symbol"] == "AAA.NS" and store.search("ltd", limit=2).__len__() == 2
    assert json.loads(json.dumps(store.checklist("AAA.NS")))["items"][0]["id"] == "roe"


def test_symbols_without_prices_are_reported_not_scored(tmp_path):
    store = MarketStore(tmp_path / "m.db")
    universe = UNIVERSE + [Stock("GONE.NS", "Gone Ltd", "Realty", "NIFTYREALTY")]
    report = run_refresh(store, universe, FakeSource(), workers=1, years=1.0)
    assert report["no_prices"] == ["GONE.NS"] and report["symbols"] == 3
    assert "GONE.NS" not in store.load_frame("metrics").index


def test_prices_only_refresh_keeps_fundamentals(tmp_path):
    store = MarketStore(tmp_path / "m.db")
    run_refresh(store, UNIVERSE, FakeSource(), workers=1, years=1.0)
    src = FakeSource()
    run_refresh(store, UNIVERSE, src, prices_only=True, years=1.0)
    assert src.calls == []                                            # no per-ticker calls
    m = store.load_frame("metrics")
    assert m.loc["AAA.NS", "pe"] == 18.0 and m.loc["AAA.NS", "price"] == 100 + N - 1
