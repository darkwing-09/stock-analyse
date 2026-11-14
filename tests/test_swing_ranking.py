# -*- coding: utf-8 -*-
"""Ranking engine + risk rules (seam: rank_universe / select_portfolio / position_size)."""

import numpy as np

from src.swing.config import SwingConfig
from src.swing.ranking import SignalEngine
from tests.swing_fixtures import panel, series, trading_days

DAYS = trading_days(400)
SECTORS = {"UP.NS": "NIFTYIT", "UP2.NS": "NIFTYAUTO", "FLAT.NS": "NIFTYFMCG", "DOWN.NS": "NIFTYMETAL"}


def _engine(frames, sectors=SECTORS, config=None, benchmark=None):
    bench = benchmark if benchmark is not None else series(DAYS, daily_drift=0.0003, noise=0.006, seed=99)["close"]
    return SignalEngine(panel(frames), benchmark=bench, sector_of=sectors, config=config or SwingConfig())


def _frames():
    return {
        "UP.NS": series(DAYS, daily_drift=0.0025, noise=0.008, seed=1),
        "UP2.NS": series(DAYS, daily_drift=0.0015, noise=0.008, seed=2),
        "FLAT.NS": series(DAYS, daily_drift=0.0, noise=0.008, seed=3),
        "DOWN.NS": series(DAYS, daily_drift=-0.002, noise=0.008, seed=4),
    }


def test_strong_uptrend_ranks_first_and_downtrend_is_excluded():
    ranked = _engine(_frames()).rank()
    symbols = [c.symbol for c in ranked]

    assert symbols[0] == "UP.NS"
    assert "DOWN.NS" not in symbols  # fails the trend filter (close > SMA50 > SMA200)
    scores = [c.score for c in ranked]
    assert scores == sorted(scores, reverse=True)
    assert all(0 <= c.score <= 100 for c in ranked)


def test_every_candidate_has_a_valid_trade_plan():
    config = SwingConfig()
    for c in _engine(_frames(), config=config).rank():
        assert c.stop < c.entry < c.target
        assert c.reward_risk >= config.min_reward_risk
        assert c.entry - c.stop >= c.atr * 0.99  # stop at least 1 ATR away
        assert c.sector == SECTORS[c.symbol]


def test_limited_upside_below_resistance_is_filtered_out():
    # Rises to 200, falls to 120, then recovers in a fresh uptrend to 197: the old 200 high
    # sits closer than 2R above entry, so the trade has poor reward:risk and must be skipped.
    n = len(DAYS)
    leg1 = np.linspace(100, 200, 150)
    leg2 = np.linspace(200, 120, 60)
    leg3 = np.linspace(120, 197, n - 210)
    capped = series(DAYS, closes=np.concatenate([leg1, leg2, leg3]))
    frames = {"CAPPED.NS": capped, "UP.NS": series(DAYS, daily_drift=0.0025, noise=0.008, seed=1)}
    ranked = _engine(frames, sectors={"CAPPED.NS": "NIFTYIT", "UP.NS": "NIFTYAUTO"}).rank()

    assert "CAPPED.NS" not in [c.symbol for c in ranked]
    assert "UP.NS" in [c.symbol for c in ranked]


def test_ranking_never_uses_future_data():
    frames = _frames()
    as_of = DAYS[320]
    before = [(c.symbol, round(c.score, 6), round(c.stop, 6)) for c in _engine(frames).rank(as_of)]

    tampered = {s: df.copy() for s, df in frames.items()}
    for df in tampered.values():
        df.loc[df.index > as_of, ["open", "high", "low", "close"]] *= 3.0
    after = [(c.symbol, round(c.score, 6), round(c.stop, 6)) for c in _engine(tampered).rank(as_of)]

    assert before == after


def test_selection_skips_correlated_duplicates_and_caps_sectors():
    base = series(DAYS, daily_drift=0.0025, noise=0.01, seed=7)
    twin = base.copy()
    twin[["open", "high", "low", "close"]] *= 1.001  # moves identically (corr ~ 1)
    frames = {
        "A.NS": base,
        "A_TWIN.NS": twin,
        "B.NS": series(DAYS, daily_drift=0.0022, noise=0.01, seed=8),
        "C.NS": series(DAYS, daily_drift=0.0021, noise=0.01, seed=9),
        "D.NS": series(DAYS, daily_drift=0.0020, noise=0.004, seed=10),  # clean uptrend
    }
    sectors = {"A.NS": "NIFTYIT", "A_TWIN.NS": "NIFTYAUTO", "B.NS": "NIFTYIT", "C.NS": "NIFTYIT", "D.NS": "NIFTYFMCG"}
    # risk_off_max_positions=5 isolates selection from the market-regime rule.
    config = SwingConfig(max_positions=5, max_per_sector=2, max_correlation=0.7, risk_off_max_positions=5)
    engine = _engine(frames, sectors=sectors, config=config)
    picks = engine.select(engine.rank())
    symbols = [c.symbol for c in picks]

    assert not {"A.NS", "A_TWIN.NS"} <= set(symbols)
    assert sum(1 for c in picks if c.sector == "NIFTYIT") <= 2
    assert "D.NS" in symbols


def test_position_size_risks_a_fixed_fraction_and_caps_exposure():
    from src.swing.risk import position_size

    config = SwingConfig(risk_per_trade=0.01, max_position_pct=0.15)
    # Risk ₹5,000 (1% of ₹5L) with ₹100/share risk -> 50 shares (₹50k = 10%, under the 15% cap).
    assert position_size(equity=500_000, entry=1000.0, stop=900.0, config=config) == 50
    # Tight ₹5 stop would mean 1,000 shares (₹10L); capped at 15% of equity -> 75 shares.
    assert position_size(equity=500_000, entry=1000.0, stop=995.0, config=config) == 75
    assert position_size(equity=500_000, entry=1000.0, stop=1000.0, config=config) == 0
    assert position_size(equity=1_000, entry=5000.0, stop=4900.0, config=config) == 0


def test_position_size_never_exceeds_available_cash():
    from src.swing.risk import position_size

    config = SwingConfig(risk_per_trade=0.01, max_position_pct=0.15)
    # Risk and exposure rules allow 50 shares (₹50k), but only ₹20k cash is left -> 20 shares.
    assert position_size(equity=500_000, entry=1000.0, stop=900.0, config=config, cash=20_000) == 20
    assert position_size(equity=500_000, entry=1000.0, stop=900.0, config=config, cash=999) == 0
