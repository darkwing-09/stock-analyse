# -*- coding: utf-8 -*-
"""Live-network smoke test for India (NSE) data via Yahoo Finance.

Gated by @pytest.mark.network (excluded from the offline CI gate). Run with:
    python -m pytest -m network tests/test_in_market_network.py
"""

import pytest

from data_provider.base import DataFetcherManager
from data_provider.yfinance_fetcher import YfinanceFetcher


@pytest.mark.network
def test_live_nse_daily_bars_and_quote() -> None:
    manager = DataFetcherManager(fetchers=[YfinanceFetcher()])

    df, source = manager.get_daily_data("RELIANCE.NS", days=30)
    assert source == "YfinanceFetcher"
    assert len(df) >= 10
    assert (df["close"] > 0).all()

    quote = manager.get_realtime_quote("RELIANCE.NS")
    assert quote is not None
    assert quote.currency == "INR"
    assert "RELIANCE" in (quote.name or "").upper()


@pytest.mark.network
def test_live_india_indices() -> None:
    indices = YfinanceFetcher().get_main_indices("in") or []
    codes = {item["code"] for item in indices}
    assert {"NIFTY50", "SENSEX"} <= codes
