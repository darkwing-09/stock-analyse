# -*- coding: utf-8 -*-
"""Regression tests for India (NSE/BSE) suffix-only market support.

India stocks use the Yahoo Finance suffix forms ``SYMBOL.NS`` (NSE) and
``SYMBOL.BO`` (BSE). Unlike JP/KR/TW, NSE symbols are alphanumeric and may
contain ``&`` or ``-`` (``M&M.NS``, ``BAJAJ-AUTO.NS``); BSE also accepts the
6-digit scrip code (``500325.BO``). Both fold into one ``in`` market label.
Bare symbols keep their existing semantics (``RELIANCE`` is not India).
"""

from unittest.mock import patch

import pandas as pd
from data_provider.base import BaseFetcher, DataFetchError, DataFetcherManager, normalize_stock_code
from src.core.trading_calendar import get_market_for_stock
from src.market_context import detect_market
from src.services.stock_code_utils import is_code_like, normalize_code


class _FakeFetcher(BaseFetcher):
    def __init__(self, name: str, should_fail: bool = False):
        self.name = name
        self.priority = 0 if name != "YfinanceFetcher" else 4
        self.calls = []
        self.should_fail = should_fail

    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        raise NotImplementedError

    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        raise NotImplementedError

    def get_daily_data(self, stock_code, start_date=None, end_date=None, days=30):
        self.calls.append(stock_code)
        if self.should_fail:
            raise DataFetchError(f"{self.name} should not be called for {stock_code}")
        return pd.DataFrame(
            {
                "date": [pd.Timestamp("2026-11-13")],
                "open": [1.0],
                "high": [1.0],
                "low": [1.0],
                "close": [1.0],
                "volume": [100],
                "amount": [100.0],
                "pct_chg": [0.0],
            }
        )


def test_normalize_and_detect_in_suffix_codes() -> None:
    assert normalize_stock_code("reliance.ns") == "RELIANCE.NS"
    assert normalize_stock_code("m&m.ns") == "M&M.NS"
    assert normalize_stock_code("BAJAJ-AUTO.NS") == "BAJAJ-AUTO.NS"
    assert normalize_stock_code("500325.bo") == "500325.BO"

    # ITC.NS / IDEA.BO would otherwise match the US ``ABC.XY`` share-class pattern.
    for code in ("RELIANCE.NS", "TCS.NS", "ITC.NS", "IDEA.BO", "M&M.NS", "BAJAJ-AUTO.NS", "NIFTYBEES.NS", "500325.BO", "RELIANCE.BO"):
        assert detect_market(code) == "in", code
        assert get_market_for_stock(code) == "in", code
        assert is_code_like(code) is True, code
        assert normalize_code(code) == code, code

    # Opt-in by suffix only: bare symbols must not become India.
    assert detect_market("ITC") != "in"
    assert get_market_for_stock("500325") != "in"
    # Garbage after the suffix dot must not be accepted.
    assert detect_market("RELI ANCE.NS") != "in"
    assert detect_market(".NS") != "in"


def test_data_fetcher_manager_routes_in_daily_only_to_yfinance() -> None:
    efinance = _FakeFetcher("EfinanceFetcher", should_fail=True)
    akshare = _FakeFetcher("AkshareFetcher", should_fail=True)
    yfinance = _FakeFetcher("YfinanceFetcher")
    manager = DataFetcherManager(fetchers=[efinance, akshare, yfinance])

    with patch("data_provider.base.record_provider_run_started"), patch("data_provider.base.record_provider_run"):
        ns_df, ns_source = manager.get_daily_data("m&m.ns")
        bo_df, bo_source = manager.get_daily_data("500325.BO")

    assert (ns_source, bo_source) == ("YfinanceFetcher", "YfinanceFetcher")
    assert not ns_df.empty and not bo_df.empty
    assert efinance.calls == [] and akshare.calls == []
    assert yfinance.calls == ["M&M.NS", "500325.BO"]


def test_yfinance_keeps_in_suffix_codes_and_indices() -> None:
    from data_provider.yfinance_fetcher import YfinanceFetcher

    fetcher = YfinanceFetcher()
    assert fetcher._convert_stock_code("RELIANCE.NS") == "RELIANCE.NS"
    assert fetcher._convert_stock_code("M&M.NS") == "M&M.NS"
    assert fetcher._convert_stock_code("500325.BO") == "500325.BO"

    captured = []

    def fake_fetch(_yf, yf_code, name, return_code):
        captured.append((yf_code, return_code))
        return {"code": return_code, "name": name, "current": 1.0}

    fetcher._fetch_yf_ticker_data = fake_fetch  # type: ignore[method-assign]
    in_indices = fetcher.get_main_indices("in") or []

    assert {item["code"] for item in in_indices} == {"NIFTY50", "SENSEX", "BANKNIFTY", "INDIAVIX"}
    assert ("^NSEI", "NIFTY50") in captured
    assert ("^BSESN", "SENSEX") in captured
    assert ("^NSEBANK", "BANKNIFTY") in captured


def test_trading_calendar_registers_in_exchange_and_holidays() -> None:
    from datetime import date

    from src.core.trading_calendar import MARKET_EXCHANGE, MARKET_TIMEZONE, is_market_open

    assert MARKET_EXCHANGE["in"] == "XBOM"
    assert MARKET_TIMEZONE["in"] == "Asia/Kolkata"
    # NSE/BSE holidays: Republic Day and Diwali (Laxmi Pujan) 2026.
    assert is_market_open("in", date(2026, 1, 26)) is False
    assert is_market_open("in", date(2026, 11, 10)) is False
    assert is_market_open("in", date(2026, 11, 13)) is True
    assert is_market_open("in", date(2026, 11, 14)) is False  # Saturday


def test_market_guidelines_for_in_use_indian_market_context() -> None:
    from src.market_context import get_market_guidelines, get_market_role

    assert get_market_role("RELIANCE.NS", "en") == "India stock"
    assert get_market_role("500325.BO", "zh") == "印度股"

    en = get_market_guidelines("RELIANCE.NS", "en")
    for concept in ("India", "NSE", "INR", "RBI", "SEBI", "FII", "DII", "circuit", "T+1"):
        assert concept in en, concept
    # China A-share-only concepts may only appear as an explicit exclusion.
    assert "do not apply China A-share" in en
    assert "Northbound" in en and "Dragon Tiger" in en

    zh = get_market_guidelines("TCS.NS", "zh")
    assert "印度" in zh and "卢比" in zh and "北向资金" in zh


def test_stock_name_lookup_skips_a_share_sources_for_in() -> None:
    baostock = _FakeFetcher("BaostockFetcher")
    yfinance = _FakeFetcher("YfinanceFetcher")
    name_calls = []
    baostock.get_stock_name = lambda code: name_calls.append(code) or "深市默认"  # type: ignore[attr-defined]
    manager = DataFetcherManager(fetchers=[baostock, yfinance])

    manager.get_stock_name("TCS.NS", allow_realtime=False)

    assert name_calls == []


def test_in_is_first_class_on_write_paths() -> None:
    """India analyses must produce DecisionSignals (used by backtesting) and be
    accepted by portfolio / intelligence, matching the other yfinance markets."""
    from src.services.decision_signal_service import DecisionSignalService
    from src.services.intelligence_service import _ALLOWED_MARKETS
    from src.services.portfolio_service import VALID_MARKETS

    assert DecisionSignalService._normalize_market("in") == "in"
    assert "in" in VALID_MARKETS
    assert "in" in _ALLOWED_MARKETS


def _in_buy_result(current_price: float):
    from src.analyzer import AnalysisResult

    return AnalysisResult(
        code="RELIANCE.NS",
        name="RELIANCE INDUSTRIES LTD",
        sentiment_score=67,
        trend_prediction="Bullish",
        operation_advice="Buy",
        decision_type="buy",
        report_language="en",
        current_price=current_price,
        dashboard={
            "core_conclusion": {"one_sentence": "raw"},
            "data_perspective": {
                "price_position": {"current_price": current_price, "support_level": 1300.0, "resistance_level": 1400.0}
            },
        },
    )


def test_in_buy_is_not_vetoed_by_structurally_missing_a_share_capital_flow() -> None:
    """A-share capital flow never exists for India, so its absence must not veto
    every India buy; the price-structure guards still apply."""
    from types import SimpleNamespace

    from src.analyzer import stabilize_decision_with_structure

    levels = SimpleNamespace(support_levels=[1300.0], resistance_levels=[1400.0])
    unsupported = {"capital_flow": {"status": "not_supported", "data": {}}}

    near_support = _in_buy_result(1310.0)
    stabilize_decision_with_structure(near_support, levels, unsupported)
    assert near_support.decision_type == "buy"
    assert near_support.operation_advice == "Buy"

    mid_range = _in_buy_result(1350.0)
    stabilize_decision_with_structure(mid_range, levels, unsupported)
    assert mid_range.decision_type == "hold"
    assert "capital-flow confirmation" not in mid_range.dashboard["decision_stability"]["reason"]


def test_chip_distribution_is_not_requested_from_a_share_sources_for_in() -> None:
    akshare = _FakeFetcher("AkshareFetcher")
    chip_calls = []
    akshare.get_chip_distribution = lambda code: chip_calls.append(code)  # type: ignore[attr-defined]
    manager = DataFetcherManager(fetchers=[akshare])

    assert manager.get_chip_distribution("RELIANCE.NS") is None
    assert chip_calls == []
