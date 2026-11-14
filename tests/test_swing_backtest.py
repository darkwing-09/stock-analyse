# -*- coding: utf-8 -*-
"""Backtester trade mechanics on hand-built bars (seam: Backtester.run)."""

import numpy as np
import pytest

from src.swing.backtest import Backtester
from src.swing.config import SwingConfig
from src.swing.costs import IndianDeliveryCosts
from src.swing.ranking import Candidate, SignalEngine
from tests.swing_fixtures import panel, series, trading_days

DAYS = trading_days(40)
ZERO_COSTS = IndianDeliveryCosts(
    brokerage_flat=0, brokerage_pct=0, stt_pct=0, exchange_txn_pct=0, sebi_fee_pct=0,
    ipft_pct=0, stamp_duty_buy_pct=0, gst_pct=0, dp_charge_sell=0,
)
# Trailing stop, time stop and SMA exit switched off so each test isolates one rule.
CFG = SwingConfig(
    capital=100_000, risk_per_trade=0.05, max_position_pct=1.0, slippage_bps=10,
    trail_atr=1e9, max_hold_days=10_000, exit_below_sma50=False, use_target_exit=True,
)


def _bars(overrides=None):
    """Flat ₹100 stock; ``overrides`` maps day index -> (open, high, low, close)."""
    df = series(DAYS, closes=np.full(len(DAYS), 100.0))
    df["open"], df["high"], df["low"] = 100.0, 100.5, 99.5
    for i, (o, h, lo, c) in (overrides or {}).items():
        df.iloc[i, df.columns.get_indexer(["open", "high", "low", "close"])] = [o, h, lo, c]
    return df


def _run(df, *, signal_day=5, stop=95.0, target=115.0, costs=ZERO_COSTS, config=CFG):
    engine = SignalEngine(panel({"X.NS": df}), benchmark=df["close"], sector_of={"X.NS": "NIFTYIT"}, config=config)
    signal_on = DAYS[signal_day]

    def signals(day, bt):
        if day != signal_on:
            return []
        return [Candidate("X.NS", 90.0, 100.0, stop, target, 3.0, 1.0, "NIFTYIT", "breakout", day)]

    return Backtester(engine, config=config, costs=costs, signal_fn=signals).run(start=DAYS[0])


def test_entry_fills_at_next_open_with_slippage_never_on_signal_day():
    result = _run(_bars({10: (99.0, 99.2, 94.0, 96.0)}))
    trade = result.trades[0]
    assert trade.entry_date == DAYS[6]
    assert trade.entry_price == pytest.approx(100.0 * 1.001)


def test_stop_hit_exits_at_stop_less_slippage():
    result = _run(_bars({10: (99.0, 99.2, 94.0, 96.0)}))
    trade = result.trades[0]
    assert (trade.exit_date, trade.exit_reason) == (DAYS[10], "stop")
    assert trade.exit_price == pytest.approx(95.0 * 0.999)


def test_gap_below_stop_exits_at_the_open_not_the_stop():
    result = _run(_bars({10: (90.0, 91.0, 89.0, 90.5)}))
    trade = result.trades[0]
    assert trade.exit_reason == "stop"
    assert trade.exit_price == pytest.approx(90.0 * 0.999)


def test_target_hit_exits_at_target():
    result = _run(_bars({12: (101.0, 116.0, 100.5, 114.0)}))
    trade = result.trades[0]
    assert (trade.exit_date, trade.exit_reason) == (DAYS[12], "target")
    assert trade.exit_price == pytest.approx(115.0 * 0.999)
    assert trade.r_multiple == pytest.approx((115.0 * 0.999 - 100.1) / (100.1 - 95.0), rel=1e-6)


def test_bar_touching_both_stop_and_target_assumes_the_stop():
    result = _run(_bars({12: (100.0, 116.0, 94.0, 100.0)}))
    assert result.trades[0].exit_reason == "stop"


def test_entry_skipped_when_next_open_gaps_below_stop():
    result = _run(_bars({6: (94.0, 94.5, 93.0, 94.0)}))
    assert result.trades == []


def test_cash_and_costs_reconcile_to_final_equity():
    costs = IndianDeliveryCosts()
    result = _run(_bars({12: (101.0, 116.0, 100.5, 114.0)}), costs=costs)
    trade = result.trades[0]
    assert trade.costs == pytest.approx(costs.buy(trade.qty * trade.entry_price) + costs.sell(trade.qty * trade.exit_price))
    assert result.equity.iloc[-1] == pytest.approx(CFG.capital + trade.net_pnl)
    assert trade.net_pnl == pytest.approx(trade.qty * (trade.exit_price - trade.entry_price) - trade.costs)


def test_results_before_a_date_ignore_bars_after_it():
    base = _bars({12: (101.0, 116.0, 100.5, 114.0)})
    tampered = base.copy()
    tampered.iloc[20:, :4] *= 0.5
    a, b = _run(base), _run(tampered)
    assert a.trades[0].__dict__ == b.trades[0].__dict__
    assert a.equity.iloc[:20].equals(b.equity.iloc[:20])


def test_without_target_exits_winners_run_until_another_exit():
    config = CFG.with_overrides(use_target_exit=False)
    result = _run(_bars({12: (101.0, 116.0, 100.5, 114.0), 20: (99.0, 99.5, 94.0, 96.0)}), config=config)
    trade = result.trades[0]
    assert trade.exit_reason == "stop"
    assert trade.exit_date == DAYS[20]


def test_weekly_rebalancing_only_queues_orders_on_the_last_session_of_a_week():
    config = CFG.with_overrides(rebalance="weekly")
    df = _bars()
    engine = SignalEngine(panel({"X.NS": df}), benchmark=df["close"], sector_of={"X.NS": "NIFTYIT"}, config=config)
    asked = []

    def signals(day, bt):
        asked.append(day)
        return []

    Backtester(engine, config=config, costs=ZERO_COSTS, signal_fn=signals).run(start=DAYS[0])
    assert asked, "signals were never requested"
    for day in asked[:-1]:
        nxt = DAYS[DAYS.get_loc(day) + 1]
        assert nxt.isocalendar().week != day.isocalendar().week
