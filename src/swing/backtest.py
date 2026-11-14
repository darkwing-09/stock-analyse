# -*- coding: utf-8 -*-
"""Day-by-day swing-trading backtester with Indian costs, slippage and tax.

Daily sequence (decisions use the close; orders fill the next session):
  1. at the open: exit positions flagged yesterday (time stop / trend break),
     then fill yesterday's buy orders at open + slippage (skipped if the open
     gaps below the stop or above the target);
  2. intraday: a low at/below the stop exits at the stop (or the open, if it
     gapped through); otherwise a high at/above the target exits at the
     target. A bar touching both is assumed to hit the stop first;
  3. at the close: raise trailing stops, flag time/trend exits, rank the
     universe and queue buy orders for tomorrow;
  4. mark equity at the close.

``PortfolioState`` holds everything that changes day to day, so the paper
trader can persist it and advance one session at a time with ``step``.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from src.swing.config import SwingConfig
from src.swing.costs import IndianDeliveryCosts
from src.swing.ranking import Candidate, SignalEngine
from src.swing.risk import position_size

STCG_TAX_RATE = 0.20          # listed equity held < 12 months (from 23 Jul 2024)
RISK_FREE_RATE = 0.065        # approx. Indian T-bill yield, for Sharpe


@dataclass
class Position:
    symbol: str
    qty: int
    entry_price: float
    entry_date: pd.Timestamp
    stop: float
    target: float
    initial_stop: float
    sector: str
    buy_costs: float
    highest_close: float
    bars_held: int = 0


@dataclass
class PendingEntry:
    symbol: str
    qty: int
    stop: float
    target: float
    sector: str
    signal_date: pd.Timestamp
    score: float = 0.0
    ref_price: float = 0.0     # signal-day close, used for live limit prices


@dataclass
class Trade:
    symbol: str
    sector: str
    qty: int
    entry_date: pd.Timestamp
    entry_price: float
    exit_date: pd.Timestamp
    exit_price: float
    exit_reason: str
    costs: float
    gross_pnl: float
    net_pnl: float
    r_multiple: float
    bars_held: int

    def to_dict(self) -> Dict[str, object]:
        d = asdict(self)
        d["entry_date"] = self.entry_date.date().isoformat()
        d["exit_date"] = self.exit_date.date().isoformat()
        return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}


@dataclass
class PortfolioState:
    cash: float
    positions: Dict[str, Position] = field(default_factory=dict)
    pending_entries: List[PendingEntry] = field(default_factory=list)
    pending_exits: Dict[str, str] = field(default_factory=dict)
    trades: List[Trade] = field(default_factory=list)
    equity_curve: Dict[pd.Timestamp, float] = field(default_factory=dict)
    last_day: Optional[pd.Timestamp] = None


SignalFn = Callable[[pd.Timestamp, "Backtester"], List[Candidate]]


class Backtester:
    def __init__(
        self,
        engine: SignalEngine,
        *,
        config: Optional[SwingConfig] = None,
        costs: Optional[IndianDeliveryCosts] = None,
        signal_fn: Optional[SignalFn] = None,
    ):
        self.engine = engine
        self.config = config or engine.config
        self.costs = costs or IndianDeliveryCosts()
        self.signal_fn = signal_fn or self._default_signals
        self.state = PortfolioState(cash=self.config.capital)

    # -- convenience views used by signal functions --------------------
    @property
    def positions(self) -> Dict[str, Position]:
        return self.state.positions

    @property
    def pending_entries(self) -> List[PendingEntry]:
        return self.state.pending_entries

    def _default_signals(self, day: pd.Timestamp, bt: "Backtester") -> List[Candidate]:
        held = list(self.state.positions) + [p.symbol for p in self.state.pending_entries]
        slots = self.engine.max_positions(day) - len(held)
        if slots <= 0:
            return []
        return self.engine.select(self.engine.rank(day), held=held, slots=slots)

    # -- helpers -------------------------------------------------------
    def _bar(self, day: pd.Timestamp, sym: str):
        e = self.engine
        try:
            o, h, lo, c = (float(e.open.at[day, sym]), float(e.high.at[day, sym]),
                           float(e.low.at[day, sym]), float(e.close.at[day, sym]))
        except KeyError:
            return None
        if any(math.isnan(x) for x in (o, h, lo, c)):
            return None
        return o, h, lo, c

    def _equity_at(self, day: pd.Timestamp) -> float:
        value = self.state.cash
        for pos in self.state.positions.values():
            px = self.engine.close.at[day, pos.symbol] if pos.symbol in self.engine.close.columns else np.nan
            value += pos.qty * (float(px) if not pd.isna(px) else pos.entry_price)
        return value

    def _close_position(self, pos: Position, day: pd.Timestamp, raw_price: float, reason: str) -> None:
        slip = self.config.slippage_bps / 10_000
        price = raw_price * (1 - slip)
        proceeds = pos.qty * price
        sell_costs = self.costs.sell(proceeds)
        self.state.cash += proceeds - sell_costs
        gross = pos.qty * (price - pos.entry_price)
        total_costs = pos.buy_costs + sell_costs
        risk = (pos.entry_price - pos.initial_stop) * pos.qty
        self.state.trades.append(
            Trade(
                symbol=pos.symbol, sector=pos.sector, qty=pos.qty,
                entry_date=pos.entry_date, entry_price=pos.entry_price,
                exit_date=day, exit_price=price, exit_reason=reason,
                costs=total_costs, gross_pnl=gross, net_pnl=gross - total_costs,
                r_multiple=(gross / risk) if risk > 0 else 0.0, bars_held=pos.bars_held,
            )
        )
        del self.state.positions[pos.symbol]

    # -- one session ---------------------------------------------------
    def is_rebalance_day(self, day: pd.Timestamp, next_day: Optional[pd.Timestamp]) -> bool:
        if self.config.rebalance != "weekly" or next_day is None:
            return True
        return pd.Timestamp(next_day).isocalendar().week != pd.Timestamp(day).isocalendar().week

    def step(self, day: pd.Timestamp, next_day: Optional[pd.Timestamp] = None) -> None:
        cfg, st, e = self.config, self.state, self.engine
        slip = cfg.slippage_bps / 10_000

        # 1a. exits flagged at yesterday's close fill at today's open
        for sym, reason in list(st.pending_exits.items()):
            pos = st.positions.get(sym)
            bar = self._bar(day, sym)
            if pos is not None and bar is not None:
                self._close_position(pos, day, bar[0], reason)
        st.pending_exits = {s: r for s, r in st.pending_exits.items() if s in st.positions}

        # 1b. buy orders queued yesterday fill at today's open
        pending, st.pending_entries = st.pending_entries, []
        for order in pending:
            bar = self._bar(day, order.symbol)
            if bar is None or order.symbol in st.positions:
                continue
            open_px = bar[0]
            if open_px <= order.stop or (cfg.use_target_exit and open_px >= order.target):
                continue
            price = open_px * (1 + slip)
            qty = order.qty
            while qty > 0 and qty * price + self.costs.buy(qty * price) > st.cash:
                qty -= 1
            if qty <= 0:
                continue
            value = qty * price
            buy_costs = self.costs.buy(value)
            st.cash -= value + buy_costs
            st.positions[order.symbol] = Position(
                symbol=order.symbol, qty=qty, entry_price=price, entry_date=day,
                stop=order.stop, target=order.target, initial_stop=order.stop,
                sector=order.sector, buy_costs=buy_costs, highest_close=price,
            )

        # 2. intraday stop / target
        for pos in list(st.positions.values()):
            bar = self._bar(day, pos.symbol)
            if bar is None:
                continue
            o, h, lo, _c = bar
            if lo <= pos.stop:
                self._close_position(pos, day, min(o, pos.stop), "stop")
            elif cfg.use_target_exit and h >= pos.target:
                self._close_position(pos, day, max(o, pos.target), "target")

        # 3. end of day: trailing stops and exit flags
        for pos in st.positions.values():
            bar = self._bar(day, pos.symbol)
            if bar is None:
                continue
            close = bar[3]
            pos.bars_held += 1
            pos.highest_close = max(pos.highest_close, close)
            atr = e.atr.at[day, pos.symbol]
            if not pd.isna(atr):
                pos.stop = max(pos.stop, pos.highest_close - cfg.trail_atr * float(atr))
            if pos.bars_held >= cfg.max_hold_days:
                st.pending_exits[pos.symbol] = "time"
            elif cfg.exit_below_sma50:
                sma = e.sma50.at[day, pos.symbol]
                if not pd.isna(sma) and close < float(sma):
                    st.pending_exits[pos.symbol] = "trend"

        # 3b. new signals -> orders for tomorrow
        equity = self._equity_at(day)
        free_cash = st.cash
        candidates = self.signal_fn(day, self) if self.is_rebalance_day(day, next_day) else []
        for cand in candidates:
            if cand.symbol in st.positions:
                continue
            qty = position_size(equity=equity, entry=cand.entry, stop=cand.stop, config=cfg, cash=free_cash)
            if qty <= 0:
                continue
            free_cash -= qty * cand.entry * (1 + slip)
            st.pending_entries.append(
                PendingEntry(cand.symbol, qty, cand.stop, cand.target, cand.sector, day, cand.score, cand.entry)
            )

        # 4. mark to market
        st.equity_curve[day] = self._equity_at(day)
        st.last_day = day

    def run(self, start=None, end=None) -> "BacktestResult":
        index = self.engine.close.index
        days = index[(index >= pd.Timestamp(start or index[0])) & (index <= pd.Timestamp(end or index[-1]))]
        for i, day in enumerate(days):
            self.step(day, days[i + 1] if i + 1 < len(days) else None)
        return BacktestResult.from_state(self.state, self.engine.benchmark, self.config)


# -- results -----------------------------------------------------------
def _max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return 0.0
    return float((equity / equity.cummax() - 1).min())


def _cagr(equity: pd.Series) -> float:
    if len(equity) < 2 or equity.iloc[0] <= 0:
        return 0.0
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    if years <= 0:
        return 0.0
    return float((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1)


def _sharpe(equity: pd.Series) -> float:
    rets = equity.pct_change().dropna()
    if rets.std() == 0 or len(rets) < 20:
        return 0.0
    excess = rets - RISK_FREE_RATE / 252
    return float(excess.mean() / rets.std() * np.sqrt(252))


def _indian_fy(day: pd.Timestamp) -> str:
    year = day.year if day.month >= 4 else day.year - 1
    return f"FY{year % 100:02d}-{(year + 1) % 100:02d}"


def estimate_stcg_tax(trades: List[Trade]) -> Dict[str, float]:
    """20% STCG per financial year on net realised gains, carrying losses forward."""
    by_fy: Dict[str, float] = {}
    for t in sorted(trades, key=lambda tr: tr.exit_date):
        fy = _indian_fy(t.exit_date)
        by_fy[fy] = by_fy.get(fy, 0.0) + t.net_pnl
    tax, carry = {}, 0.0
    for fy in sorted(by_fy):
        taxable = by_fy[fy] + carry
        if taxable > 0:
            tax[fy], carry = taxable * STCG_TAX_RATE, 0.0
        else:
            tax[fy], carry = 0.0, taxable
    return tax


def _period_stats(equity: pd.Series, bench: pd.Series) -> Dict[str, float]:
    b = bench.reindex(equity.index).ffill().dropna()
    return {
        "cagr": _cagr(equity),
        "max_drawdown": _max_drawdown(equity),
        "sharpe": _sharpe(equity),
        "benchmark_cagr": _cagr(b),
        "benchmark_max_drawdown": _max_drawdown(b),
    }


@dataclass
class BacktestResult:
    equity: pd.Series
    benchmark: pd.Series
    trades: List[Trade]
    open_positions: List[Position]
    config: SwingConfig

    @classmethod
    def from_state(cls, state: PortfolioState, benchmark: pd.Series, config: SwingConfig) -> "BacktestResult":
        equity = pd.Series(state.equity_curve, dtype=float).sort_index()
        return cls(equity, benchmark, list(state.trades), list(state.positions.values()), config)

    def summary(self, oos_fraction: float = 0.3) -> Dict[str, object]:
        eq = self.equity
        trades = self.trades
        wins = [t for t in trades if t.net_pnl > 0]
        losses = [t for t in trades if t.net_pnl <= 0]
        gross_win = sum(t.net_pnl for t in wins)
        gross_loss = -sum(t.net_pnl for t in losses)
        tax = estimate_stcg_tax(trades)
        total_tax = sum(tax.values())
        exposure = 0.0
        if trades and len(eq) > 1:
            exposure = sum(t.bars_held for t in trades) / (len(eq) * max(1, self.config.max_positions))
        split = int(len(eq) * (1 - oos_fraction))
        out: Dict[str, object] = {
            "start": eq.index[0].date().isoformat() if len(eq) else None,
            "end": eq.index[-1].date().isoformat() if len(eq) else None,
            "initial_capital": self.config.capital,
            "final_equity": float(eq.iloc[-1]) if len(eq) else self.config.capital,
            "total_return": float(eq.iloc[-1] / eq.iloc[0] - 1) if len(eq) else 0.0,
            **_period_stats(eq, self.benchmark),
            "trades": len(trades),
            "win_rate": len(wins) / len(trades) if trades else 0.0,
            "avg_win": gross_win / len(wins) if wins else 0.0,
            "avg_loss": -gross_loss / len(losses) if losses else 0.0,
            "profit_factor": gross_win / gross_loss if gross_loss > 0 else float("inf") if gross_win else 0.0,
            "avg_r": float(np.mean([t.r_multiple for t in trades])) if trades else 0.0,
            "avg_bars_held": float(np.mean([t.bars_held for t in trades])) if trades else 0.0,
            "total_costs": sum(t.costs for t in trades),
            "estimated_tax": total_tax,
            "tax_by_fy": tax,
            "post_tax_final_equity": (float(eq.iloc[-1]) if len(eq) else self.config.capital) - total_tax,
            "exposure": exposure,
            "exit_reasons": pd.Series([t.exit_reason for t in trades]).value_counts().to_dict() if trades else {},
            "open_positions": len(self.open_positions),
        }
        if 30 < split < len(eq) - 30:
            out["in_sample"] = _period_stats(eq.iloc[:split], self.benchmark)
            out["out_of_sample"] = _period_stats(eq.iloc[split:], self.benchmark)
        yearly = {}
        b = self.benchmark.reindex(eq.index).ffill()
        for year, chunk in eq.groupby(eq.index.year):
            bc = b.loc[chunk.index].dropna()
            prev_eq = eq[eq.index < chunk.index[0]]
            start_val = prev_eq.iloc[-1] if len(prev_eq) else chunk.iloc[0]
            prev_b = b[b.index < chunk.index[0]].dropna()
            b_start = prev_b.iloc[-1] if len(prev_b) else (bc.iloc[0] if len(bc) else np.nan)
            yearly[int(year)] = {
                "strategy": float(chunk.iloc[-1] / start_val - 1),
                "benchmark": float(bc.iloc[-1] / b_start - 1) if len(bc) else None,
            }
        out["yearly"] = yearly
        return out
