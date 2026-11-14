# -*- coding: utf-8 -*-
"""Paper trader (seam: PaperTrader.run / status) on hand-built bars."""

import json

import numpy as np
import pytest

from src.swing.config import SwingConfig
from src.swing.costs import IndianDeliveryCosts
from src.swing.paper import PaperTrader
from src.swing.ranking import Candidate, SignalEngine
from tests.swing_fixtures import panel, series, trading_days

DAYS = trading_days(30)
CFG = SwingConfig(
    capital=100_000, risk_per_trade=0.05, max_position_pct=1.0, slippage_bps=10,
    trail_atr=1e9, max_hold_days=10_000, exit_below_sma50=False, use_target_exit=True,
)


def _engine(upto: int, overrides=None):
    df = series(DAYS, closes=np.full(len(DAYS), 100.0))
    df["open"], df["high"], df["low"] = 100.0, 100.5, 99.5
    for i, (o, h, lo, c) in (overrides or {}).items():
        df.iloc[i, df.columns.get_indexer(["open", "high", "low", "close"])] = [o, h, lo, c]
    df = df.iloc[: upto + 1]
    return SignalEngine(panel({"X.NS": df}), benchmark=df["close"], sector_of={"X.NS": "NIFTYIT"}, config=CFG)


def _signal_on(day_index):
    def signals(day, bt):
        if day != DAYS[day_index]:
            return []
        return [Candidate("X.NS", 90.0, 100.0, 95.0, 115.0, 3.0, 1.0, "NIFTYIT", "breakout", day)]
    return signals


def _trader(tmp_path, signal_day=10):
    return PaperTrader(tmp_path / "paper.json", config=CFG, costs=IndianDeliveryCosts(), signal_fn=_signal_on(signal_day))


def test_first_run_starts_today_and_only_queues_orders(tmp_path):
    trader = _trader(tmp_path)
    trader.run(_engine(10))
    status = trader.status()

    assert status["last_session"] == DAYS[10].date().isoformat()
    assert status["positions"] == []
    assert [o["symbol"] for o in status["pending_orders"]] == ["X.NS"]
    assert status["cash"] == pytest.approx(100_000)
    assert status["equity_curve"][0]["date"] == DAYS[10].date().isoformat()


def test_next_session_fills_at_open_and_state_survives_restart(tmp_path):
    _trader(tmp_path).run(_engine(10))
    reloaded = _trader(tmp_path)  # fresh process, state read back from disk
    reloaded.run(_engine(11))
    status = reloaded.status()

    pos = status["positions"][0]
    assert pos["symbol"] == "X.NS"
    assert pos["entry_date"] == DAYS[11].date().isoformat()
    assert pos["entry_price"] == pytest.approx(100.1)
    assert status["pending_orders"] == []
    json.loads((tmp_path / "paper.json").read_text())  # human-readable JSON on disk


def test_missed_days_are_caught_up_once_and_reruns_are_idempotent(tmp_path):
    trader = _trader(tmp_path)
    trader.run(_engine(10))
    trader.run(_engine(16, {14: (101.0, 116.0, 100.5, 114.0)}))  # 6 sessions later; target hit on day 14
    once = trader.status()
    trader.run(_engine(16, {14: (101.0, 116.0, 100.5, 114.0)}))  # same data again
    twice = trader.status()

    assert [t["exit_reason"] for t in once["trades"]] == ["target"]
    assert once["trades"][0]["exit_date"] == DAYS[14].date().isoformat()
    assert len(once["equity_curve"]) == 7
    assert once == twice


def test_status_reports_pnl_against_starting_capital(tmp_path):
    trader = _trader(tmp_path)
    trader.run(_engine(10))
    trader.run(_engine(16, {14: (101.0, 116.0, 100.5, 114.0)}))
    status = trader.status()

    trade = status["trades"][0]
    assert status["equity"] == pytest.approx(100_000 + trade["net_pnl"], abs=0.01)
    assert status["total_return"] == pytest.approx(trade["net_pnl"] / 100_000, abs=1e-6)
