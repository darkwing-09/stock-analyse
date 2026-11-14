# -*- coding: utf-8 -*-
"""Live order placement through Fyers, locked behind safety gates.

Nothing is sent unless EVERY gate passes:
  1. ``LIVE_TRADING_ENABLED=true`` in the environment (off by default);
  2. no kill-switch file (``data/swing/KILL_SWITCH``): create it to halt;
  3. the order was approved for today with ``swing.py live approve``;
  4. new BUYs only while the day's loss is within ``daily_loss_limit_pct``;
     risk-reducing SELLs (stops, exits) are always allowed;
  5. order value <= ``max_order_value_pct`` of equity, and at most
     ``max_orders_per_day`` orders;
  6. orders are paced ``min_seconds_between_orders`` apart (default 1s),
     far below SEBI's 10 orders/second retail-algo threshold.

Orders are after-market (AMO) CNC orders for the next session: limit buys
capped a little above the signal close (no chasing gap-ups), SL-M protective
stops re-placed each evening as trailing stops rise, and market sells for
time/trend exits. SEBI's 2026 retail-algo rules require API orders from a
static IP registered with your broker; Fyers rejects orders from other IPs.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from src.swing.backtest import PortfolioState

TICK = 0.05
DEFAULT_KILL_SWITCH = Path("data/swing/KILL_SWITCH")
DEFAULT_APPROVALS = Path("data/swing/live_approvals.json")
FYERS_ORDER_URL = "https://api-t1.fyers.in/api/v3/orders/sync"


def round_tick(price: float, tick: float = TICK) -> float:
    return round(round(price / tick) * tick, 2)


@dataclass
class OrderIntent:
    id: str
    symbol: str
    side: str            # BUY / SELL
    qty: int
    order_type: str      # LIMIT / MARKET / SL-M
    limit_price: float = 0.0
    stop_price: float = 0.0
    reason: str = ""

    @property
    def reduces_risk(self) -> bool:
        return self.side == "SELL"

    def value(self, ref_price: Optional[float] = None) -> float:
        price = self.limit_price or self.stop_price or (ref_price or 0.0)
        return self.qty * price


def build_intents(state: PortfolioState, *, limit_buffer: float = 0.005) -> List[OrderIntent]:
    """Tomorrow's orders from the paper/strategy state."""
    intents: List[OrderIntent] = []
    for p in state.pending_entries:
        ref = p.ref_price or p.stop
        intents.append(OrderIntent(
            id=f"BUY-{p.symbol}-{p.signal_date.date().isoformat()}", symbol=p.symbol, side="BUY", qty=p.qty,
            order_type="LIMIT", limit_price=round_tick(ref * (1 + limit_buffer)), reason="entry",
        ))
    for sym, reason in state.pending_exits.items():
        pos = state.positions.get(sym)
        if pos:
            intents.append(OrderIntent(id=f"EXIT-{sym}", symbol=sym, side="SELL", qty=pos.qty,
                                       order_type="MARKET", reason=f"exit:{reason}"))
    for sym, pos in state.positions.items():
        if sym in state.pending_exits:
            continue
        intents.append(OrderIntent(id=f"STOP-{sym}", symbol=sym, side="SELL", qty=pos.qty,
                                   order_type="SL-M", stop_price=round_tick(pos.stop), reason="protective_stop"))
    return intents


@dataclass(frozen=True)
class GateConfig:
    enabled_env: str = "LIVE_TRADING_ENABLED"
    kill_switch_path: Path = DEFAULT_KILL_SWITCH
    daily_loss_limit_pct: float = 0.02
    max_order_value_pct: float = 0.20
    max_orders_per_day: int = 12
    min_seconds_between_orders: float = 1.0


@dataclass
class SubmissionReport:
    sent: List[Tuple[OrderIntent, Dict[str, Any]]] = field(default_factory=list)
    blocked: List[Tuple[OrderIntent, str]] = field(default_factory=list)


class LiveExecutor:
    def __init__(
        self,
        broker,
        *,
        gates: Optional[GateConfig] = None,
        approvals_path: Path = DEFAULT_APPROVALS,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.broker = broker
        self.gates = gates or GateConfig()
        self.approvals_path = Path(approvals_path)
        self.sleep = sleep

    # -- approvals -----------------------------------------------------
    def _approvals(self) -> Dict[str, List[str]]:
        try:
            return json.loads(self.approvals_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def approve(self, intents: List[OrderIntent], day: str) -> None:
        approvals = self._approvals()
        approvals.setdefault(day, [])
        approvals[day] = sorted(set(approvals[day]) | {i.id for i in intents})
        self.approvals_path.parent.mkdir(parents=True, exist_ok=True)
        self.approvals_path.write_text(json.dumps(approvals, indent=2), encoding="utf-8")

    # -- gates ---------------------------------------------------------
    def global_block_reason(self) -> Optional[str]:
        if os.getenv(self.gates.enabled_env, "").strip().lower() != "true":
            return f"{self.gates.enabled_env} is not set to true"
        if Path(self.gates.kill_switch_path).exists():
            return f"kill switch present at {self.gates.kill_switch_path}"
        return None

    def submit(self, intents: List[OrderIntent], *, day: str, equity: float, day_pnl: float) -> SubmissionReport:
        report = SubmissionReport()
        blocked_all = self.global_block_reason()
        if blocked_all:
            report.blocked = [(i, blocked_all) for i in intents]
            return report

        approved = set(self._approvals().get(day, []))
        loss_breached = equity > 0 and (-day_pnl / equity) > self.gates.daily_loss_limit_pct
        sent_count = 0
        # Risk-reducing orders first so a cap never leaves a position unprotected.
        for intent in sorted(intents, key=lambda i: not i.reduces_risk):
            if intent.id not in approved:
                report.blocked.append((intent, "not approved"))
                continue
            if intent.qty <= 0:
                report.blocked.append((intent, "zero quantity"))
                continue
            if not intent.reduces_risk:
                if loss_breached:
                    report.blocked.append((intent, "daily loss limit reached; new buys blocked"))
                    continue
                if intent.value() > equity * self.gates.max_order_value_pct:
                    report.blocked.append((intent, "order value above cap"))
                    continue
            if sent_count >= self.gates.max_orders_per_day:
                report.blocked.append((intent, "max orders per day reached"))
                continue
            if sent_count:
                self.sleep(self.gates.min_seconds_between_orders)
            response = self.broker.place(intent)
            report.sent.append((intent, response))
            sent_count += 1
        return report


class FyersBroker:
    """Places orders with Fyers API v3 (payload per the official fyers-apiv3 SDK)."""

    TYPES = {"LIMIT": 1, "MARKET": 2, "SL-M": 3}

    def __init__(self, client_id: str, access_token: str, session: Any = None):
        if session is None:
            import requests

            session = requests.Session()
        self.client_id, self.access_token, self.session = client_id, access_token, session

    @staticmethod
    def payload(intent: OrderIntent) -> Dict[str, Any]:
        from data_provider.fyers_fetcher import to_fyers_symbol

        symbol = to_fyers_symbol(intent.symbol)
        if symbol is None:
            raise ValueError(f"{intent.symbol} cannot be traded through Fyers (NSE .NS symbols only)")
        return {
            "symbol": symbol,
            "qty": int(intent.qty),
            "type": FyersBroker.TYPES[intent.order_type],
            "side": 1 if intent.side == "BUY" else -1,
            "productType": "CNC",
            "limitPrice": intent.limit_price if intent.order_type == "LIMIT" else 0,
            "stopPrice": intent.stop_price if intent.order_type == "SL-M" else 0,
            "validity": "DAY",
            "disclosedQty": 0,
            "offlineOrder": True,  # AMO: queued for the next session's open
        }

    def place(self, intent: OrderIntent) -> Dict[str, Any]:
        headers = {"Authorization": f"{self.client_id}:{self.access_token}", "Content-Type": "application/json"}
        resp = self.session.post(FYERS_ORDER_URL, json=self.payload(intent), headers=headers, timeout=20)
        return resp.json()


def intents_to_json(intents: List[OrderIntent]) -> List[Dict[str, Any]]:
    return [asdict(i) for i in intents]
