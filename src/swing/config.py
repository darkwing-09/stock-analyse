# -*- coding: utf-8 -*-
"""Tunable parameters for the India swing-trading engine.

Every number here is a documented default, not an optimised value. Change them
only with a backtest that shows the effect out of sample.

Exit defaults (wide stops, trailing exit, no fixed target) were chosen from an
in-sample study on 2021-09..2025-05 where they won across every other setting.
The risk-off rule (no new entries below Nifty's 200-day average) is standard
trend-following practice; note that the 2025-05..2026-11 hold-out period was
seen before it was adopted. None of these settings showed a reliable edge out
of sample, which is why paper trading comes before real money.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Dict


@dataclass(frozen=True)
class SwingConfig:
    # Account
    capital: float = 500_000.0
    risk_per_trade: float = 0.01          # fraction of equity lost if the stop is hit
    max_position_pct: float = 0.15        # cap on one position's value vs equity
    max_positions: int = 8
    max_per_sector: int = 2
    max_correlation: float = 0.70         # skip picks this correlated with an existing one
    correlation_window: int = 60

    # Eligibility
    min_history: int = 252
    min_traded_value: float = 10e7        # ₹10 crore average daily value traded (20 days)
    max_atr_pct: float = 0.06             # skip extremely volatile names

    # Trade plan
    atr_period: int = 14
    stop_atr_max: float = 3.0             # initial stop never more than this many ATRs away
    stop_atr_min: float = 1.5             # ...and never closer than this
    swing_low_window: int = 10
    target_r: float = 3.0                 # target = entry + target_r x risk (open sky)
    min_reward_risk: float = 2.0
    recent_high_window: int = 30          # highs this recent count as "already broken out"

    # Exits (used by the backtester and paper trader)
    trail_atr: float = 4.0                # chandelier trailing stop below the highest close
    max_hold_days: int = 60
    exit_below_sma50: bool = True
    use_target_exit: bool = False         # False: the target only gates R:R; the trailing stop runs winners
    rebalance: str = "daily"              # "daily" or "weekly" (last session of each week)

    # Market regime: when Nifty is below its 200-day average, hold fewer positions
    regime_sma: int = 200
    risk_off_max_positions: int = 0       # no new entries while Nifty < 200-day average

    # Score weights (sum to 1)
    weights: Dict[str, float] = field(
        default_factory=lambda: {
            "relative_strength": 0.35,
            "trend_quality": 0.20,
            "sector_strength": 0.15,
            "near_high": 0.15,
            "volume_trend": 0.10,
            "low_volatility": 0.05,
        }
    )

    # Execution
    slippage_bps: float = 10.0            # 0.10% worse than the reference price on every fill

    def with_overrides(self, **overrides) -> "SwingConfig":
        return replace(self, **overrides)
