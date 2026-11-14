# -*- coding: utf-8 -*-
"""Synthetic OHLCV generators with known behaviour for swing-engine tests."""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd


def trading_days(n: int = 400, start: str = "2024-01-01") -> pd.DatetimeIndex:
    return pd.bdate_range(start=start, periods=n)


def series(
    days: pd.DatetimeIndex,
    *,
    start: float = 100.0,
    daily_drift: float = 0.0,
    noise: float = 0.01,
    seed: int = 0,
    closes: Optional[np.ndarray] = None,
    volume: float = 2_000_000,
) -> pd.DataFrame:
    """OHLCV frame. ``closes`` overrides the random walk when given."""
    rng = np.random.default_rng(seed)
    if closes is None:
        rets = daily_drift + noise * rng.standard_normal(len(days))
        closes = start * np.exp(np.cumsum(rets))
    closes = np.asarray(closes, dtype=float)
    opens = np.concatenate([[closes[0]], closes[:-1]])
    spread = np.maximum(np.abs(closes - opens), closes * 0.004)
    highs = np.maximum(opens, closes) + spread * 0.5
    lows = np.minimum(opens, closes) - spread * 0.5
    return pd.DataFrame(
        {"open": opens, "high": highs, "low": lows, "close": closes, "volume": np.full(len(days), volume)},
        index=days,
    )


def panel(frames: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Wide (date x symbol) frames per field, as consumed by the engine."""
    fields = ("open", "high", "low", "close", "volume")
    return {f: pd.DataFrame({sym: df[f] for sym, df in frames.items()}) for f in fields}
