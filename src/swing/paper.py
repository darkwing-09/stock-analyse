# -*- coding: utf-8 -*-
"""Paper trading: the backtester's daily step applied to real sessions.

Run once per trading day after the close (e.g. 16:30 IST). Each run:
  * replays every session since the last run (catching up missed days),
    filling yesterday's orders at today's open and checking stops/targets
    against today's high/low, exactly like the backtester;
  * queues tomorrow's orders from today's close;
  * saves everything to a human-readable JSON file.

Running twice on the same data changes nothing.
"""

from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from src.swing.backtest import (
    Backtester,
    PendingEntry,
    PortfolioState,
    Position,
    SignalFn,
    Trade,
    _cagr,
    _max_drawdown,
)
from src.swing.config import SwingConfig
from src.swing.costs import IndianDeliveryCosts
from src.swing.ranking import SignalEngine

DEFAULT_STATE_FILE = Path("data/swing/paper_state.json")


def _ts(value) -> Optional[str]:
    return None if value is None else pd.Timestamp(value).date().isoformat()


def _encode(obj) -> Dict[str, Any]:
    out = {}
    for f in fields(obj):
        v = getattr(obj, f.name)
        out[f.name] = _ts(v) if isinstance(v, pd.Timestamp) else v
    return out


def _decode(cls, data: Dict[str, Any]):
    kwargs = {}
    for f in fields(cls):
        if f.name not in data:
            continue
        v = data[f.name]
        if f.name.endswith("_date") and v is not None:
            v = pd.Timestamp(v)
        kwargs[f.name] = v
    return cls(**kwargs)


def save_state(state: PortfolioState, path: Path, *, started_on: Optional[str], capital: float) -> None:
    payload = {
        "version": 1,
        "capital": capital,
        "started_on": started_on,
        "cash": state.cash,
        "last_day": _ts(state.last_day),
        "positions": [_encode(p) for p in state.positions.values()],
        "pending_entries": [_encode(p) for p in state.pending_entries],
        "pending_exits": dict(state.pending_exits),
        "trades": [_encode(t) for t in state.trades],
        "equity_curve": [{"date": _ts(d), "equity": v} for d, v in sorted(state.equity_curve.items())],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def load_state(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    state = PortfolioState(cash=float(data["cash"]))
    state.positions = {p["symbol"]: _decode(Position, p) for p in data.get("positions", [])}
    state.pending_entries = [_decode(PendingEntry, p) for p in data.get("pending_entries", [])]
    state.pending_exits = dict(data.get("pending_exits", {}))
    state.trades = [_decode(Trade, t) for t in data.get("trades", [])]
    state.equity_curve = {pd.Timestamp(r["date"]): float(r["equity"]) for r in data.get("equity_curve", [])}
    state.last_day = pd.Timestamp(data["last_day"]) if data.get("last_day") else None
    return {"state": state, "started_on": data.get("started_on"), "capital": float(data.get("capital", state.cash))}


class PaperTrader:
    def __init__(
        self,
        state_path: Path = DEFAULT_STATE_FILE,
        *,
        config: Optional[SwingConfig] = None,
        costs: Optional[IndianDeliveryCosts] = None,
        signal_fn: Optional[SignalFn] = None,
    ):
        self.path = Path(state_path)
        self.config = config or SwingConfig()
        self.costs = costs or IndianDeliveryCosts()
        self.signal_fn = signal_fn
        loaded = load_state(self.path)
        if loaded:
            self.state: PortfolioState = loaded["state"]
            self.started_on = loaded["started_on"]
            self.capital = loaded["capital"]
        else:
            self.state = PortfolioState(cash=self.config.capital)
            self.started_on = None
            self.capital = self.config.capital
        self.engine: Optional[SignalEngine] = None

    def run(self, engine: SignalEngine, next_session: Optional[pd.Timestamp] = None) -> List[pd.Timestamp]:
        """Advance through every new session in ``engine``; returns the sessions processed."""
        self.engine = engine
        index = engine.close.index
        if self.state.last_day is None:
            sessions = list(index[-1:])                       # start today: no simulated history
            self.started_on = _ts(sessions[0]) if sessions else None
        else:
            sessions = list(index[index > self.state.last_day])
        if not sessions:
            return []
        bt = Backtester(engine, config=self.config, costs=self.costs, signal_fn=self.signal_fn)
        bt.state = self.state
        for i, day in enumerate(sessions):
            nxt = sessions[i + 1] if i + 1 < len(sessions) else next_session
            bt.step(day, nxt)
        save_state(self.state, self.path, started_on=self.started_on, capital=self.capital)
        return sessions

    def status(self) -> Dict[str, Any]:
        st = self.state
        engine = self.engine
        last = st.last_day
        positions = []
        market_value = 0.0
        for p in st.positions.values():
            price = p.entry_price
            if engine is not None and last is not None and p.symbol in engine.close.columns:
                px = engine.close.at[last, p.symbol]
                price = float(px) if not pd.isna(px) else price
            value = p.qty * price
            market_value += value
            positions.append(
                {
                    **_encode(p),
                    "last_price": price,
                    "market_value": value,
                    "unrealized_pnl": p.qty * (price - p.entry_price) - p.buy_costs,
                    "unrealized_pct": (price / p.entry_price - 1) if p.entry_price else 0.0,
                }
            )
        equity = st.cash + market_value
        curve = pd.Series({d: v for d, v in st.equity_curve.items()}, dtype=float).sort_index()
        realized = sum(t.net_pnl for t in st.trades)
        wins = [t for t in st.trades if t.net_pnl > 0]
        bench_curve = []
        if engine is not None and len(curve):
            b = engine.benchmark.reindex(curve.index).ffill()
            if len(b.dropna()):
                base = b.dropna().iloc[0]
                bench_curve = [round(float(v / base * self.capital), 2) for v in b.fillna(base)]
        return {
            "started_on": self.started_on,
            "last_session": _ts(last),
            "capital": self.capital,
            "cash": st.cash,
            "equity": equity,
            "total_return": equity / self.capital - 1 if self.capital else 0.0,
            "realized_pnl": realized,
            "max_drawdown": _max_drawdown(curve) if len(curve) else 0.0,
            "cagr": _cagr(curve) if len(curve) > 1 else 0.0,
            "win_rate": len(wins) / len(st.trades) if st.trades else 0.0,
            "positions": positions,
            "pending_orders": [_encode(p) for p in st.pending_entries],
            "pending_exits": dict(st.pending_exits),
            "trades": [t.to_dict() for t in st.trades],
            "equity_curve": [
                {"date": _ts(d), "equity": round(v, 2), **({"benchmark": bench_curve[i]} if bench_curve else {})}
                for i, (d, v) in enumerate(curve.items())
            ],
        }
