# -*- coding: utf-8 -*-
"""India (NSE/BSE) market review: Nifty/Sensex/Bank Nifty/India VIX plus
sector-index rankings, India-specific prompt context, IST dates and the
trading-day region filter."""

from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from src.config import Config
from src.core.trading_calendar import compute_effective_region
from src.market_analyzer import MarketAnalyzer, MarketIndex, MarketOverview


def _index(code="NIFTY50", name="Nifty 50", change_pct=0.8):
    return MarketIndex(code=code, name=name, current=25144.3, change=200.0, change_pct=change_pct, prev_close=24944.3)


def _sector(name, change_pct):
    return {"name": name, "change_pct": change_pct}


@pytest.mark.parametrize("language", ["zh", "en"])
def test_in_prompt_uses_indian_context(language):
    with patch("src.market_analyzer.DataFetcherManager"):
        analyzer = MarketAnalyzer(region="in", config=Config(report_language=language))
    overview = MarketOverview(
        date="2026-11-13",
        indices=[_index()],
        top_sectors=[_sector("Nifty IT", 2.1)],
        bottom_sectors=[_sector("Nifty Realty", -1.4)],
    )
    prompt = analyzer._build_review_prompt(overview, [])

    assert analyzer.profile.region == analyzer.strategy.region == "in"
    assert analyzer.profile.has_sector_rankings is True
    assert analyzer.profile.has_market_stats is False
    assert "Nifty IT" in prompt and "Nifty Realty" in prompt
    assert ("India market" in prompt) if language == "en" else ("印度" in prompt)
    for a_share_only in ("北向资金", "两市成交额", "SSE, SZSE"):
        assert a_share_only not in prompt
    assert analyzer._get_turnover_unit_label() == ("INR bn" if language == "en" else "十亿卢比")


def test_in_template_report_is_titled_india_and_never_a_share():
    with patch("src.market_analyzer.DataFetcherManager"):
        analyzer = MarketAnalyzer(region="in", config=Config(report_language="en"))
    report = analyzer.generate_market_review(MarketOverview(date="2026-11-13", indices=[_index()]), [])

    assert "India Market Recap" in report
    assert "A-share" not in report


def test_in_overview_uses_ist_date_indices_and_sector_indices_only():
    with patch("src.market_analyzer.DataFetcherManager") as manager, patch(
        "src.market_analyzer.get_market_now",
        return_value=datetime(2026, 11, 13, 16, 30, tzinfo=ZoneInfo("Asia/Kolkata")),
    ) as market_now:
        manager.return_value.get_main_indices.return_value = [
            {**_index().to_dict(), "prev_close": 24944.3, "volume": 0, "amount": 0, "amplitude": 0}
        ]
        manager.return_value.get_in_sector_rankings.return_value = (
            [_sector("Nifty IT", 2.1)],
            [_sector("Nifty Realty", -1.4)],
        )
        overview = MarketAnalyzer(region="in", config=Config()).get_market_overview()

    market_now.assert_called_once_with("in")
    assert overview.date == "2026-11-13"
    manager.return_value.get_main_indices.assert_called_once_with(region="in")
    assert [s["name"] for s in overview.top_sectors] == ["Nifty IT"]
    assert [s["name"] for s in overview.bottom_sectors] == ["Nifty Realty"]
    called = {call[0] for call in manager.return_value.method_calls}
    # Never touch the China-only breadth / sector / concept feeds.
    assert called == {"get_main_indices", "get_in_sector_rankings"}


@pytest.mark.parametrize(
    "configured,open_markets,expected",
    [
        ("in", {"in"}, "in"),
        ("in", {"cn"}, ""),
        ("cn,in", {"in"}, "in"),
        ("both", {"in"}, "in"),
    ],
)
def test_in_trading_day_filter(configured, open_markets, expected):
    assert compute_effective_region(configured, open_markets) == expected


def test_yfinance_ranks_india_sector_indices_by_change():
    from data_provider.yfinance_fetcher import YfinanceFetcher

    moves = {"^CNXIT": 2.1, "^CNXREALTY": -1.4, "^CNXAUTO": 0.3, "^NSEBANK": -0.2}
    fetcher = YfinanceFetcher()

    def fake_fetch(_yf, yf_code, name, return_code):
        if yf_code not in moves:
            return None
        return {"code": return_code, "name": name, "change_pct": moves[yf_code]}

    fetcher._fetch_yf_ticker_data = fake_fetch  # type: ignore[method-assign]
    top, bottom = fetcher.get_in_sector_rankings(2)

    assert [s["name"] for s in top] == ["Nifty IT", "Nifty Auto"]
    assert [s["name"] for s in bottom] == ["Nifty Realty", "Nifty Bank"]
    assert top[0]["change_pct"] == 2.1
