# -*- coding: utf-8 -*-
"""Fyers API v3 data provider, tested against recorded responses (no account needed).

Endpoints and auth verified from the official fyers-apiv3 3.2.1 SDK:
  GET https://api-t1.fyers.in/data/history   Authorization: "<client_id>:<access_token>"
  GET https://api-t1.fyers.in/data/quotes
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from data_provider.base import DataFetchError
from data_provider.fyers_fetcher import FyersFetcher, to_fyers_symbol

IST = ZoneInfo("Asia/Kolkata")


def _epoch(day: str) -> int:
    return int(datetime.strptime(day, "%Y-%m-%d").replace(tzinfo=IST).timestamp())


class _Resp:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _Session:
    """Records requests and replays queued responses."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append({"url": url, "params": dict(params or {}), "headers": dict(headers or {})})
        return _Resp(self.responses.pop(0))


def _fetcher(session):
    return FyersFetcher(client_id="ABCD1234-100", access_token="tok123", session=session)


def test_to_fyers_symbol_maps_nse_codes_only():
    assert to_fyers_symbol("RELIANCE.NS") == "NSE:RELIANCE-EQ"
    assert to_fyers_symbol("m&m.ns") == "NSE:M&M-EQ"
    assert to_fyers_symbol("BAJAJ-AUTO.NS") == "NSE:BAJAJ-AUTO-EQ"
    # BSE series codes vary by group, so BSE and non-India codes fall back to other sources.
    assert to_fyers_symbol("RELIANCE.BO") is None
    assert to_fyers_symbol("AAPL") is None
    assert to_fyers_symbol("600519") is None


def test_daily_history_is_parsed_and_authorised():
    session = _Session(
        {
            "s": "ok",
            "code": 200,
            "candles": [
                [_epoch("2026-11-12"), 1320.0, 1335.0, 1310.0, 1330.0, 9_000_000],
                [_epoch("2026-11-13"), 1331.0, 1350.7, 1324.0, 1339.7, 13_756_247],
            ],
        }
    )
    df = _fetcher(session).get_daily_data("RELIANCE.NS", start_date="2026-11-01", end_date="2026-11-14")

    call = session.calls[0]
    assert call["url"] == "https://api-t1.fyers.in/data/history"
    assert call["headers"]["Authorization"] == "ABCD1234-100:tok123"
    assert call["params"]["symbol"] == "NSE:RELIANCE-EQ"
    assert call["params"]["resolution"] == "D"
    assert call["params"]["date_format"] == 1
    assert [str(d.date()) for d in pd.to_datetime(df["date"])] == ["2026-11-12", "2026-11-13"]
    assert list(df["close"]) == [1330.0, 1339.7]
    assert round(float(df["pct_chg"].iloc[-1]), 2) == round((1339.7 / 1330.0 - 1) * 100, 2)


def test_long_ranges_are_split_into_366_day_requests():
    session = _Session(
        {"s": "ok", "candles": [[_epoch("2025-01-02"), 1, 1, 1, 1, 1]]},
        {"s": "ok", "candles": [[_epoch("2026-01-02"), 2, 2, 2, 2, 2]]},
    )
    df = _fetcher(session).get_daily_data("TCS.NS", start_date="2025-01-01", end_date="2026-06-30")

    assert len(session.calls) == 2
    first, second = (c["params"] for c in session.calls)
    assert first["range_from"] == "2025-01-01"
    assert second["range_to"] == "2026-06-30"
    assert first["range_to"] < second["range_from"]
    assert len(df) == 2


def test_api_error_raises_data_fetch_error():
    session = _Session({"s": "error", "code": -16, "message": "Could not authenticate the user"})
    with pytest.raises(DataFetchError, match="authenticate"):
        _fetcher(session).get_daily_data("INFY.NS", start_date="2026-11-01", end_date="2026-11-14")


def test_unconfigured_fetcher_refuses_without_network():
    session = _Session()
    fetcher = FyersFetcher(client_id="", access_token="", session=session)
    assert fetcher.is_configured() is False
    with pytest.raises(DataFetchError):
        fetcher.get_daily_data("INFY.NS", start_date="2026-11-01", end_date="2026-11-14")
    assert session.calls == []


def _quote_item(symbol, lp, chp, description="RELIANCE INDUSTRIES LTD"):
    return {
        "n": symbol,
        "s": "ok",
        "v": {
            "lp": lp, "ch": round(lp * chp / 100, 2), "chp": chp,
            "open_price": lp - 5, "high_price": lp + 10, "low_price": lp - 15, "prev_close_price": lp - 8,
            "volume": 13_756_247, "atp": lp - 1, "short_name": symbol.split(":")[1],
            "description": description, "exchange": "NSE", "tt": str(_epoch("2026-11-13") + 15 * 3600),
        },
    }


def test_realtime_quote_is_parsed_as_inr_india_quote():
    session = _Session({"s": "ok", "code": 200, "d": [_quote_item("NSE:RELIANCE-EQ", 1339.7, 0.6)]})
    quote = _fetcher(session).get_realtime_quote("RELIANCE.NS")

    assert session.calls[0]["url"] == "https://api-t1.fyers.in/data/quotes"
    assert session.calls[0]["params"]["symbols"] == "NSE:RELIANCE-EQ"
    assert quote.price == 1339.7
    assert quote.change_pct == 0.6
    assert quote.name == "RELIANCE INDUSTRIES LTD"
    assert (quote.market, quote.currency) == ("in", "INR")
    assert quote.pre_close == 1331.7
    assert quote.provider_timestamp.startswith("2026-11-13T15:00")


def test_india_indices_come_from_one_batched_quote_call():
    items = [
        _quote_item("NSE:NIFTY50-INDEX", 25144.3, -0.61, "Nifty 50"),
        _quote_item("BSE:SENSEX-INDEX", 81592.45, -0.39, "Sensex"),
        _quote_item("NSE:NIFTYBANK-INDEX", 61034.1, -0.79, "Nifty Bank"),
        _quote_item("NSE:INDIAVIX-INDEX", 15.5, -6.74, "India VIX"),
    ]
    session = _Session({"s": "ok", "d": items})
    indices = _fetcher(session).get_main_indices("in")

    assert len(session.calls) == 1
    assert [i["code"] for i in indices] == ["NIFTY50", "SENSEX", "BANKNIFTY", "INDIAVIX"]
    assert indices[0]["current"] == 25144.3 and indices[0]["change_pct"] == -0.61
    assert _fetcher(_Session()).get_main_indices("cn") is None


def test_login_helpers_build_official_auth_flow():
    from data_provider.fyers_fetcher import build_login_url, build_token_request

    url = build_login_url("ABCD1234-100", "https://127.0.0.1/callback")
    assert url.startswith("https://api-t1.fyers.in/api/v3/generate-authcode?")
    assert "client_id=ABCD1234-100" in url and "response_type=code" in url

    token_url, body = build_token_request("ABCD1234-100", "SECRET", "AUTHCODE")
    assert token_url == "https://api-t1.fyers.in/api/v3/validate-authcode"
    # sha256("ABCD1234-100:SECRET") computed independently with `sha256sum`.
    assert body == {
        "grant_type": "authorization_code",
        "appIdHash": "f0b969bd36e6b38d6dbb5fa7084cbb59ff00b30e67edee3e4f156e23b6df5529",
        "code": "AUTHCODE",
    }


class _Named:
    """Minimal fetcher double for manager routing."""

    def __init__(self, name, priority, *, daily=None, quote=None):
        from data_provider.base import BaseFetcher  # noqa: F401  (protocol reference)

        self.name, self.priority = name, priority
        self._daily, self._quote = daily, quote
        self.daily_calls, self.quote_calls = [], []

    def get_daily_data(self, stock_code, start_date=None, end_date=None, days=30):
        self.daily_calls.append(stock_code)
        if self._daily is None:
            raise DataFetchError(f"{self.name} down")
        return self._daily

    def get_realtime_quote(self, stock_code, **_kw):
        self.quote_calls.append(stock_code)
        return self._quote


def _bars():
    return pd.DataFrame(
        {"date": [pd.Timestamp("2026-11-13")], "open": [1.0], "high": [1.0], "low": [1.0],
         "close": [1.0], "volume": [1], "amount": [1.0], "pct_chg": [0.0]}
    )


def test_manager_prefers_fyers_for_india_and_falls_back_to_yahoo():
    from unittest.mock import patch

    from data_provider.base import DataFetcherManager

    fyers = _Named("FyersFetcher", 1, daily=None)
    yahoo = _Named("YfinanceFetcher", 4, daily=_bars())
    manager = DataFetcherManager(fetchers=[yahoo, fyers])
    with patch("data_provider.base.record_provider_run_started"), patch("data_provider.base.record_provider_run"):
        _, source = manager.get_daily_data("TCS.NS")
    assert fyers.daily_calls == ["TCS.NS"]
    assert source == "YfinanceFetcher"

    fyers_ok = _Named("FyersFetcher", 1, daily=_bars())
    yahoo2 = _Named("YfinanceFetcher", 4, daily=_bars())
    manager = DataFetcherManager(fetchers=[yahoo2, fyers_ok])
    with patch("data_provider.base.record_provider_run_started"), patch("data_provider.base.record_provider_run"):
        _, source = manager.get_daily_data("TCS.NS")
    assert source == "FyersFetcher"
    assert yahoo2.daily_calls == []


def test_manager_realtime_india_tries_fyers_then_yahoo():
    from data_provider.base import DataFetcherManager
    from data_provider.realtime_types import UnifiedRealtimeQuote

    yahoo_quote = UnifiedRealtimeQuote(code="TCS.NS", name="TCS", price=3000.0, market="in", currency="INR")
    fyers = _Named("FyersFetcher", 1, quote=None)
    yahoo = _Named("YfinanceFetcher", 4, quote=yahoo_quote)
    manager = DataFetcherManager(fetchers=[yahoo, fyers])

    quote = manager.get_realtime_quote("TCS.NS")

    assert fyers.quote_calls == ["TCS.NS"]
    assert quote is not None and quote.price == 3000.0
