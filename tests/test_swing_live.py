# -*- coding: utf-8 -*-
"""Live-order safety gates and Fyers order payloads (seam: LiveExecutor.submit / FyersBroker).

No real orders: the broker is a recording double, and FyersBroker is tested
against a recording HTTP session.
"""

import pandas as pd
import pytest

from src.swing.backtest import PendingEntry, PortfolioState, Position
from src.swing.live import FyersBroker, GateConfig, LiveExecutor, OrderIntent, build_intents

DAY = "2026-11-16"


class _Broker:
    def __init__(self):
        self.sent = []

    def place(self, intent):
        self.sent.append(intent)
        return {"s": "ok", "id": f"ord-{len(self.sent)}"}


class _Clock:
    def __init__(self):
        self.sleeps = []

    def sleep(self, seconds):
        self.sleeps.append(seconds)


def _intents():
    buy = OrderIntent("e1", "TCS.NS", "BUY", 20, "LIMIT", limit_price=3015.05, reason="entry")
    stop = OrderIntent("s1", "INFY.NS", "SELL", 30, "SL-M", stop_price=1450.0, reason="protective_stop")
    return [buy, stop]


def _executor(tmp_path, monkeypatch, *, enabled=True, gates=None):
    if enabled:
        monkeypatch.setenv("LIVE_TRADING_ENABLED", "true")
    else:
        monkeypatch.delenv("LIVE_TRADING_ENABLED", raising=False)
    broker, clock = _Broker(), _Clock()
    gates = gates or GateConfig(kill_switch_path=tmp_path / "KILL_SWITCH")
    ex = LiveExecutor(broker, gates=gates, approvals_path=tmp_path / "approvals.json", sleep=clock.sleep)
    return ex, broker, clock


def test_nothing_is_sent_unless_live_trading_is_explicitly_enabled(tmp_path, monkeypatch):
    ex, broker, _ = _executor(tmp_path, monkeypatch, enabled=False)
    ex.approve(_intents(), DAY)
    report = ex.submit(_intents(), day=DAY, equity=500_000, day_pnl=0)
    assert broker.sent == []
    assert all("LIVE_TRADING_ENABLED" in reason for _, reason in report.blocked)


def test_kill_switch_blocks_everything(tmp_path, monkeypatch):
    ex, broker, _ = _executor(tmp_path, monkeypatch)
    (tmp_path / "KILL_SWITCH").write_text("stop")
    ex.approve(_intents(), DAY)
    ex.submit(_intents(), day=DAY, equity=500_000, day_pnl=0)
    assert broker.sent == []


def test_only_orders_approved_for_today_are_sent(tmp_path, monkeypatch):
    ex, broker, _ = _executor(tmp_path, monkeypatch)
    buy, stop = _intents()
    ex.approve([buy], "2026-11-13")          # approved for a different day
    ex.approve([stop], DAY)
    report = ex.submit([buy, stop], day=DAY, equity=500_000, day_pnl=0)
    assert [i.id for i in broker.sent] == ["s1"]
    assert [(i.id, "not approved") for i, r in report.blocked if "approved" in r] == [("e1", "not approved")]


def test_daily_loss_limit_blocks_new_buys_but_not_protective_sells(tmp_path, monkeypatch):
    ex, broker, _ = _executor(tmp_path, monkeypatch)
    ex.approve(_intents(), DAY)
    ex.submit(_intents(), day=DAY, equity=500_000, day_pnl=-12_000)  # -2.4% > 2% limit
    assert [i.id for i in broker.sent] == ["s1"]


def test_order_value_and_daily_count_caps(tmp_path, monkeypatch):
    gates = GateConfig(kill_switch_path=tmp_path / "KILL_SWITCH", max_order_value_pct=0.10, max_orders_per_day=1)
    ex, broker, _ = _executor(tmp_path, monkeypatch, gates=gates)
    big = OrderIntent("e2", "MRF.NS", "BUY", 1, "LIMIT", limit_price=130_000.0, reason="entry")  # 26% of equity
    small_a = OrderIntent("e3", "ITC.NS", "BUY", 10, "LIMIT", limit_price=400.0, reason="entry")
    small_b = OrderIntent("e4", "SBIN.NS", "BUY", 10, "LIMIT", limit_price=800.0, reason="entry")
    ex.approve([big, small_a, small_b], DAY)
    report = ex.submit([big, small_a, small_b], day=DAY, equity=500_000, day_pnl=0)
    assert [i.id for i in broker.sent] == ["e3"]
    reasons = dict((i.id, r) for i, r in report.blocked)
    assert "value" in reasons["e2"] and "per day" in reasons["e4"]


def test_orders_are_paced_at_least_one_second_apart(tmp_path, monkeypatch):
    ex, broker, clock = _executor(tmp_path, monkeypatch)
    ex.approve(_intents(), DAY)
    ex.submit(_intents(), day=DAY, equity=500_000, day_pnl=0)
    assert len(broker.sent) == 2
    assert clock.sleeps and all(s >= 1.0 for s in clock.sleeps)


def test_build_intents_from_paper_state():
    state = PortfolioState(cash=100_000)
    state.pending_entries = [PendingEntry("TCS.NS", 20, 2900.0, 3300.0, "NIFTYIT", pd.Timestamp(DAY), 80.0, 3000.0)]
    state.positions = {
        "INFY.NS": Position("INFY.NS", 30, 1500.0, pd.Timestamp("2026-11-01"), 1450.0, 1800.0, 1440.0,
                            "NIFTYIT", 50.0, 1520.0),
        "ITC.NS": Position("ITC.NS", 100, 400.0, pd.Timestamp("2026-10-01"), 380.0, 460.0, 380.0,
                           "NIFTYFMCG", 30.0, 410.0),
    }
    state.pending_exits = {"ITC.NS": "time"}
    intents = {i.symbol: i for i in build_intents(state, limit_buffer=0.005)}

    buy = intents["TCS.NS"]
    assert (buy.side, buy.order_type, buy.qty) == ("BUY", "LIMIT", 20)
    assert buy.limit_price == pytest.approx(3015.0)          # 3000 x 1.005, on the 0.05 tick
    assert (intents["INFY.NS"].order_type, intents["INFY.NS"].stop_price) == ("SL-M", 1450.0)
    assert (intents["ITC.NS"].order_type, intents["ITC.NS"].side) == ("MARKET", "SELL")


class _Session:
    def __init__(self):
        self.posts = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.posts.append({"url": url, "json": json, "headers": headers})

        class R:
            @staticmethod
            def json():
                return {"s": "ok", "id": "2611160001"}

        return R()


def test_fyers_broker_sends_amo_cnc_orders():
    session = _Session()
    broker = FyersBroker(client_id="ABCD1234-100", access_token="tok", session=session)
    buy, stop = _intents()
    broker.place(buy)
    broker.place(stop)

    first, second = session.posts
    assert first["url"] == "https://api-t1.fyers.in/api/v3/orders/sync"
    assert first["headers"]["Authorization"] == "ABCD1234-100:tok"
    assert first["json"] == {
        "symbol": "NSE:TCS-EQ", "qty": 20, "type": 1, "side": 1, "productType": "CNC",
        "limitPrice": 3015.05, "stopPrice": 0, "validity": "DAY", "disclosedQty": 0,
        "offlineOrder": True,
    }
    assert second["json"]["type"] == 3 and second["json"]["side"] == -1
    assert second["json"]["stopPrice"] == 1450.0 and second["json"]["limitPrice"] == 0
