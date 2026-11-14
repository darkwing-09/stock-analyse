# -*- coding: utf-8 -*-
"""Position sizing: risk a fixed fraction of equity per trade."""

from __future__ import annotations

import math
from typing import Optional

from src.swing.config import SwingConfig


def position_size(
    *, equity: float, entry: float, stop: float, config: SwingConfig, cash: Optional[float] = None
) -> int:
    """Shares to buy so that hitting ``stop`` loses ``risk_per_trade`` of equity.

    Also capped so one position never exceeds ``max_position_pct`` of equity,
    and (when ``cash`` is given) never costs more than the cash available.
    Returns 0 when the plan is invalid or the account is too small.
    """
    risk_per_share = entry - stop
    if entry <= 0 or risk_per_share <= 0 or equity <= 0:
        return 0
    by_risk = math.floor(equity * config.risk_per_trade / risk_per_share)
    by_exposure = math.floor(equity * config.max_position_pct / entry)
    qty = min(by_risk, by_exposure)
    if cash is not None:
        qty = min(qty, math.floor(max(cash, 0.0) / entry))
    return max(0, qty)
