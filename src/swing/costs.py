# -*- coding: utf-8 -*-
"""Indian equity-delivery (CNC) trading costs.

Defaults follow the Fyers charges list (https://fyers.in/charges-list), checked
2026-11-15. Statutory rates change, so every rate is a field you can override.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class IndianDeliveryCosts:
    brokerage_flat: float = 20.0          # ₹ per executed order...
    brokerage_pct: float = 0.003          # ...or 0.3% of value, whichever is lower
    stt_pct: float = 0.001                # 0.1% on buy and sell
    exchange_txn_pct: float = 0.000030699  # NSE transaction charge
    sebi_fee_pct: float = 1e-6            # ₹10 per crore
    ipft_pct: float = 1e-9                # ₹0.01 per crore
    stamp_duty_buy_pct: float = 0.00015   # 0.015% on buy value
    gst_pct: float = 0.18
    dp_charge_sell: float = 12.5          # ₹ per scrip per sell day, before GST

    def breakdown(self, value: float, *, side: str) -> Dict[str, float]:
        value = abs(float(value))
        brokerage = min(self.brokerage_flat, self.brokerage_pct * value)
        txn = self.exchange_txn_pct * value
        sebi = self.sebi_fee_pct * value
        ipft = self.ipft_pct * value
        parts = {
            "brokerage": brokerage,
            "stt": self.stt_pct * value,
            "exchange_txn": txn,
            "sebi_fee": sebi,
            "ipft": ipft,
            "stamp_duty": self.stamp_duty_buy_pct * value if side == "buy" else 0.0,
            "gst": self.gst_pct * (brokerage + txn + sebi + ipft),
            "dp_charge": self.dp_charge_sell * (1 + self.gst_pct) if side == "sell" else 0.0,
        }
        parts["total"] = sum(parts.values())
        return parts

    def buy(self, value: float) -> float:
        return self.breakdown(value, side="buy")["total"]

    def sell(self, value: float) -> float:
        return self.breakdown(value, side="sell")["total"]
