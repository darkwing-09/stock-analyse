# -*- coding: utf-8 -*-
"""Indian equity-delivery cost model (Fyers charges list, verified 2026-11-15).

Expected values are worked by hand from the published rates:
  brokerage min(₹20, 0.3%) | STT 0.1% buy+sell | NSE txn 0.0030699% | SEBI ₹10/cr
  IPFT ₹0.01/cr | stamp 0.015% buy | GST 18% on (brokerage+txn+SEBI+IPFT)
  DP ₹12.50 + 18% GST per scrip on sell
"""

import pytest

from src.swing.costs import IndianDeliveryCosts


def test_buy_of_one_lakh():
    costs = IndianDeliveryCosts()
    # 20 + 100 + 3.0699 + 0.1 + 0.0001 + 15 + 0.18 * (20 + 3.0699 + 0.1 + 0.0001)
    assert costs.buy(100_000) == pytest.approx(142.340518, abs=1e-4)


def test_sell_of_one_point_one_lakh_includes_dp_charge():
    costs = IndianDeliveryCosts()
    # 20 + 110 + 3.37689 + 0.11 + 0.00011 + 0.18 * (20 + 3.37689 + 0.11 + 0.00011) + 14.75
    assert costs.sell(110_000) == pytest.approx(152.46464, abs=1e-4)


def test_small_orders_pay_percentage_brokerage():
    costs = IndianDeliveryCosts()
    # ₹5,000 buy: brokerage 0.3% = ₹15 (< ₹20)
    breakdown = costs.breakdown(5_000, side="buy")
    assert breakdown["brokerage"] == pytest.approx(15.0)
    assert breakdown["stt"] == pytest.approx(5.0)
    assert breakdown["stamp_duty"] == pytest.approx(0.75)


def test_round_trip_cost_percentage_shows_the_hurdle():
    costs = IndianDeliveryCosts()
    # ₹50,000 round trip, by hand: buy 20+50+1.535+0.05+7.5+3.885 = 82.97;
    # sell 20+50+1.535+0.05+3.885+14.75 = 90.22; total ₹173.19 = 0.346% before slippage.
    # This is the hurdle every trade must clear.
    assert costs.buy(50_000) + costs.sell(50_000) == pytest.approx(173.19, abs=0.01)
