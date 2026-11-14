# -*- coding: utf-8 -*-
"""Cross-sectional swing-trade ranking for a stock universe.

All indicators are computed once as wide (date x symbol) frames using only
backward-looking windows, so ``rank(as_of)`` for any past date sees exactly the
data that existed at that day's close. The live ranking, the backtester and the
paper trader all use this one implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional

import numpy as np
import pandas as pd

from src.swing.config import SwingConfig


@dataclass
class Candidate:
    symbol: str
    score: float
    entry: float
    stop: float
    target: float
    reward_risk: float
    atr: float
    sector: str
    setup: str  # "breakout" (open sky above) or "trend" (prior high caps the target)
    as_of: pd.Timestamp
    components: Dict[str, float] = field(default_factory=dict)

    @property
    def risk_per_share(self) -> float:
        return self.entry - self.stop

    def to_dict(self) -> Dict[str, object]:
        return {
            "symbol": self.symbol,
            "score": round(self.score, 2),
            "entry": round(self.entry, 2),
            "stop": round(self.stop, 2),
            "target": round(self.target, 2),
            "reward_risk": round(self.reward_risk, 2),
            "atr": round(self.atr, 2),
            "sector": self.sector,
            "setup": self.setup,
            "as_of": self.as_of.date().isoformat(),
            "components": {k: round(v, 1) for k, v in self.components.items()},
        }


def _true_range(high: pd.DataFrame, low: pd.DataFrame, close: pd.DataFrame) -> pd.DataFrame:
    prev = close.shift(1)
    return pd.concat(
        [(high - low), (high - prev).abs(), (low - prev).abs()], keys=["hl", "hc", "lc"]
    ).groupby(level=1).max().reindex(close.index)


class SignalEngine:
    """Indicators, eligibility, scores and trade plans for a universe."""

    def __init__(
        self,
        prices: Mapping[str, pd.DataFrame],
        *,
        benchmark: pd.Series,
        sector_of: Mapping[str, str],
        config: Optional[SwingConfig] = None,
    ):
        self.config = config or SwingConfig()
        self.close = prices["close"].sort_index()
        index = self.close.index
        self.open = prices["open"].reindex(index)
        self.high = prices["high"].reindex(index)
        self.low = prices["low"].reindex(index)
        self.volume = prices["volume"].reindex(index)
        self.benchmark = benchmark.reindex(index).ffill()
        self.sector_of = {sym: sector_of.get(sym, "OTHER") for sym in self.close.columns}
        self._compute()

    # -- indicators ----------------------------------------------------
    def _compute(self) -> None:
        cfg = self.config
        c, h, lo = self.close, self.high, self.low

        self.sma50 = c.rolling(50, min_periods=50).mean()
        self.sma200 = c.rolling(200, min_periods=200).mean()
        tr = _true_range(h, lo, c)
        self.atr = tr.ewm(alpha=1 / cfg.atr_period, adjust=False, min_periods=cfg.atr_period).mean()
        self.history = c.notna().cumsum()

        def ret(frame, n):
            return frame / frame.shift(n) - 1

        b = self.benchmark
        rs = (
            0.2 * (ret(c, 21).sub(ret(b, 21), axis=0))
            + 0.5 * (ret(c, 63).sub(ret(b, 63), axis=0))
            + 0.3 * (ret(c, 126).sub(ret(b, 126), axis=0))
        )
        self.relative_strength = rs

        sectors = pd.Series(self.sector_of)
        sector_mean = rs.T.groupby(sectors).transform("mean").T
        self.sector_strength = sector_mean.reindex(columns=c.columns)

        t = pd.Series(np.arange(len(c), dtype=float), index=c.index)
        log_c = np.log(c)
        corr = log_c.rolling(63, min_periods=63).corr(t)
        self.trend_quality = (corr ** 2) * np.sign(corr)

        self.near_high = c / h.rolling(252, min_periods=126).max()
        self.volume_trend = (
            self.volume.rolling(10, min_periods=10).mean() / self.volume.rolling(50, min_periods=50).mean()
        ).clip(upper=3.0)
        self.atr_pct = self.atr / c
        self.traded_value = (c * self.volume).rolling(20, min_periods=20).mean()
        self.swing_low = lo.rolling(cfg.swing_low_window, min_periods=cfg.swing_low_window).min()
        recent = cfg.recent_high_window
        self.recent_high = h.rolling(recent, min_periods=recent).max()
        self.prior_high = h.shift(recent).rolling(252 - recent, min_periods=60).max()
        self.returns = c.pct_change()
        self.bench_sma = self.benchmark.rolling(cfg.regime_sma, min_periods=cfg.regime_sma).mean()

    # -- regime --------------------------------------------------------
    def risk_on(self, as_of: Optional[pd.Timestamp] = None) -> bool:
        day = self._resolve(as_of)
        sma = self.bench_sma.get(day)
        level = self.benchmark.get(day)
        if sma is None or pd.isna(sma) or pd.isna(level):
            return True
        return bool(level >= sma)

    def max_positions(self, as_of: Optional[pd.Timestamp] = None) -> int:
        cfg = self.config
        return cfg.max_positions if self.risk_on(as_of) else min(cfg.max_positions, cfg.risk_off_max_positions)

    # -- ranking -------------------------------------------------------
    def _resolve(self, as_of: Optional[pd.Timestamp]) -> pd.Timestamp:
        index = self.close.index
        if as_of is None:
            return index[-1]
        as_of = pd.Timestamp(as_of)
        pos = index.searchsorted(as_of, side="right") - 1
        if pos < 0:
            raise ValueError(f"no data on or before {as_of.date()}")
        return index[pos]

    def eligible(self, as_of: Optional[pd.Timestamp] = None) -> pd.Series:
        cfg = self.config
        day = self._resolve(as_of)
        c = self.close.loc[day]
        ok = (
            (self.history.loc[day] >= cfg.min_history)
            & (c > self.sma50.loc[day])
            & (self.sma50.loc[day] > self.sma200.loc[day])
            & (self.traded_value.loc[day] >= cfg.min_traded_value)
            & (self.atr_pct.loc[day] <= cfg.max_atr_pct)
            & self.atr.loc[day].notna()
            & self.relative_strength.loc[day].notna()
            & self.trend_quality.loc[day].notna()
        )
        return ok.fillna(False)

    def _plan(self, symbol: str, day: pd.Timestamp) -> Optional[Dict[str, float]]:
        cfg = self.config
        entry = float(self.close.at[day, symbol])
        atr = float(self.atr.at[day, symbol])
        swing_low = float(self.swing_low.at[day, symbol])
        stop = min(max(swing_low - 0.25 * atr, entry - cfg.stop_atr_max * atr), entry - cfg.stop_atr_min * atr)
        risk = entry - stop
        if risk <= 0:
            return None
        open_sky_target = entry + cfg.target_r * risk
        prior_high = self.prior_high.at[day, symbol]
        recent_high = self.recent_high.at[day, symbol]
        if pd.isna(prior_high) or recent_high >= prior_high:
            target, setup = open_sky_target, "breakout"
        else:
            target, setup = min(float(prior_high), open_sky_target), "trend"
        rr = (target - entry) / risk
        return {"entry": entry, "stop": stop, "target": target, "rr": rr, "atr": atr, "setup": setup}

    def rank(self, as_of: Optional[pd.Timestamp] = None) -> List[Candidate]:
        """Eligible stocks with a valid >= min R:R plan, best score first."""
        cfg = self.config
        day = self._resolve(as_of)
        mask = self.eligible(day)
        symbols = list(mask[mask].index)
        if not symbols:
            return []

        raw = pd.DataFrame(
            {
                "relative_strength": self.relative_strength.loc[day, symbols],
                "trend_quality": self.trend_quality.loc[day, symbols],
                "sector_strength": self.sector_strength.loc[day, symbols],
                "near_high": self.near_high.loc[day, symbols],
                "volume_trend": self.volume_trend.loc[day, symbols],
                "low_volatility": -self.atr_pct.loc[day, symbols],
            }
        )
        pct = raw.rank(pct=True).fillna(0.5)
        weights = pd.Series(cfg.weights)
        score = (pct[weights.index] * weights).sum(axis=1) / weights.sum() * 100

        out: List[Candidate] = []
        for sym in symbols:
            plan = self._plan(sym, day)
            if plan is None or plan["rr"] < cfg.min_reward_risk:
                continue
            out.append(
                Candidate(
                    symbol=sym,
                    score=float(score[sym]),
                    entry=plan["entry"],
                    stop=plan["stop"],
                    target=plan["target"],
                    reward_risk=plan["rr"],
                    atr=plan["atr"],
                    sector=self.sector_of[sym],
                    setup=plan["setup"],
                    as_of=day,
                    components={k: float(pct.at[sym, k] * 100) for k in weights.index},
                )
            )
        out.sort(key=lambda cand: cand.score, reverse=True)
        return out

    def select(
        self,
        candidates: List[Candidate],
        *,
        held: Optional[List[str]] = None,
        slots: Optional[int] = None,
    ) -> List[Candidate]:
        """Greedy pick: best score first, skipping sector overload and correlated duplicates."""
        cfg = self.config
        if not candidates:
            return []
        day = candidates[0].as_of
        held = list(held or [])
        limit = self.max_positions(day) - len(held) if slots is None else slots
        if limit <= 0:
            return []

        window = self.returns.loc[:day].tail(cfg.correlation_window)
        chosen: List[Candidate] = []
        portfolio = list(held)
        sector_count: Dict[str, int] = {}
        for sym in held:
            sector_count[self.sector_of.get(sym, "OTHER")] = sector_count.get(self.sector_of.get(sym, "OTHER"), 0) + 1

        for cand in candidates:
            if len(chosen) >= limit:
                break
            if cand.symbol in portfolio:
                continue
            if sector_count.get(cand.sector, 0) >= cfg.max_per_sector:
                continue
            if portfolio:
                corr = window[portfolio].corrwith(window[cand.symbol])
                if (corr > cfg.max_correlation).any():
                    continue
            chosen.append(cand)
            portfolio.append(cand.symbol)
            sector_count[cand.sector] = sector_count.get(cand.sector, 0) + 1
        return chosen
