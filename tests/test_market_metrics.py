# -*- coding: utf-8 -*-
"""Market data layer (seam: metrics, scores, checklist) on hand-built prices.

Expected values are worked by hand from the synthetic series, not recomputed
with the code under test.
"""

import numpy as np
import pandas as pd
import pytest

from src.market.metrics import checklist, compute_technicals, fundamentals_frame, score_universe

N = 300
DAYS = pd.bdate_range("2025-01-01", periods=N)


def _panel():
    i = np.arange(N, dtype=float)
    close = pd.DataFrame(
        {
            "UP.NS": 100 + i,                                    # steady uptrend
            "FLAT.NS": np.full(N, 50.0) + np.where(i % 2 == 0, 0.2, -0.2),  # flat, tiny wiggle
            "DOWN.NS": 400 - i,                                  # steady downtrend
        },
        index=DAYS,
    )
    volume = pd.DataFrame({c: np.full(N, 1_000_000.0) for c in close.columns}, index=DAYS)
    volume.loc[DAYS[-1], "UP.NS"] = 5_000_000.0                  # volume spike on the last day
    bench = pd.DataFrame({"^NSEI": 10_000 + 2 * i}, index=DAYS)
    return {
        "open": close, "high": close * 1.01, "low": close * 0.99, "close": close,
        "volume": volume, "benchmark": bench,
    }


@pytest.fixture(scope="module")
def tech():
    return compute_technicals(_panel())


def test_price_and_returns_are_hand_computable(tech):
    up = tech.loc["UP.NS"]
    assert up["price"] == pytest.approx(399.0)
    assert up["change_1d_pct"] == pytest.approx(1 / 398)           # 399/398 - 1
    assert up["ret_1m"] == pytest.approx(399 / 377 - 1)              # 22 bars back
    assert up["ret_1y"] == pytest.approx(399 / (399 - 252) - 1)      # 252 bars back
    assert tech.loc["DOWN.NS", "ret_1y"] < 0
    assert tech.loc["FLAT.NS", "ret_1y"] == pytest.approx(0.0, abs=0.01)


def test_trend_and_range_fields(tech):
    assert tech.loc["UP.NS", "above_sma200"] and not tech.loc["DOWN.NS", "above_sma200"]
    assert tech.loc["UP.NS", "pct_from_52w_high"] == pytest.approx(399 / (399 * 1.01) - 1)
    assert tech.loc["DOWN.NS", "pct_from_52w_high"] < -0.5
    assert 0 <= tech["rsi14"].min() and tech["rsi14"].max() <= 100
    assert tech.loc["UP.NS", "rsi14"] > 70 > tech.loc["FLAT.NS", "rsi14"] > 30 > tech.loc["DOWN.NS", "rsi14"]
    assert tech.loc["UP.NS", "volume_ratio"] == pytest.approx(5.0, rel=0.05)
    # relative strength vs Nifty over 3 months: UP beats the index, DOWN trails it
    assert tech.loc["UP.NS", "rs_3m"] > 0 > tech.loc["DOWN.NS", "rs_3m"]
    assert tech.loc["UP.NS", "golden_cross"] and not tech.loc["DOWN.NS", "golden_cross"]


def test_fundamentals_frame_normalises_yahoo_units():
    info = {
        "X.NS": {"marketCap": 1e12, "trailingPE": 22.0, "priceToBook": 1.9, "returnOnEquity": 0.0876,
                 "debtToEquity": 44.3, "dividendYield": 0.45, "heldPercentInsiders": 0.518,
                 "revenueGrowth": 0.298, "targetMeanPrice": 1613.0, "currentPrice": 1339.7,
                 "recommendationKey": "strong_buy", "numberOfAnalystOpinions": 26},
        "Y.NS": {},                                                  # nothing known
    }
    f = fundamentals_frame(info)
    x = f.loc["X.NS"]
    assert x["pe"] == 22.0 and x["pb"] == 1.9
    assert x["roe"] == pytest.approx(0.0876)
    assert x["debt_to_equity"] == pytest.approx(0.443)              # Yahoo reports percent
    assert x["dividend_yield"] == pytest.approx(0.0045)             # Yahoo reports percent
    assert x["promoter_holding"] == pytest.approx(0.518)
    assert x["analyst_upside"] == pytest.approx(1613.0 / 1339.7 - 1)
    assert x["analyst_rating"] == "strong_buy" and x["analyst_count"] == 26
    assert np.isnan(f.loc["Y.NS", "pe"]) and f.loc["Y.NS", "analyst_count"] == 0


def _scored():
    rows = {
        "A.NS": dict(pe=10, pb=1.0, roe=0.25, debt_to_equity=0.2, fcf_positive=True, revenue_growth=0.2,
                     earnings_growth=0.2, operating_margin=0.2, ret_6m=0.3, ret_3m=0.2, rs_3m=0.1,
                     pct_from_52w_high=-0.02, above_sma200=True, rsi14=60, dividend_yield=0.02, ev_ebitda=6, sector="NIFTYIT"),
        "B.NS": dict(pe=40, pb=8.0, roe=0.05, debt_to_equity=2.0, fcf_positive=False, revenue_growth=-0.1,
                     earnings_growth=-0.2, operating_margin=0.02, ret_6m=-0.3, ret_3m=-0.2, rs_3m=-0.1,
                     pct_from_52w_high=-0.4, above_sma200=False, rsi14=35, dividend_yield=0.0, ev_ebitda=30, sector="NIFTYIT"),
        "C.NS": dict(pe=20, pb=3.0, roe=0.15, debt_to_equity=0.8, fcf_positive=True, revenue_growth=0.05,
                     earnings_growth=0.05, operating_margin=0.1, ret_6m=0.05, ret_3m=0.0, rs_3m=0.0,
                     pct_from_52w_high=-0.15, above_sma200=True, rsi14=50, dividend_yield=0.01, ev_ebitda=12, sector="NIFTYIT"),
    }
    return score_universe(pd.DataFrame.from_dict(rows, orient="index"))


def test_scores_rank_the_obvious_cases_and_stay_in_range():
    s = _scored()
    for col in ("quality_score", "value_score", "momentum_score"):
        assert s[col].between(0, 100).all()
        assert s.loc["A.NS", col] > s.loc["C.NS", col] > s.loc["B.NS", col]
    assert s.loc["A.NS", "overall"] == "Strong" and s.loc["B.NS", "overall"] == "Weak"


def test_scores_tolerate_missing_values():
    frame = pd.DataFrame.from_dict({"A.NS": dict(pe=10, roe=0.2, sector="X"), "B.NS": dict(pe=np.nan, roe=np.nan, sector="X")}, orient="index")
    s = score_universe(frame)
    assert s["quality_score"].between(0, 100).all() and s["value_score"].between(0, 100).all()
    assert s.loc["A.NS", "value_score"] >= s.loc["B.NS", "value_score"]


def test_checklist_reports_each_rule_with_evidence():
    row = pd.Series(dict(roe=0.2, debt_to_equity=0.3, fcf_positive=True, revenue_growth=0.12, earnings_growth=0.05,
                         pe=30, peg=2.0, promoter_holding=0.55, institutional_holding=0.2, above_sma200=True,
                         above_sma50=False, rsi14=72, pct_from_52w_high=-0.1, ret_1y=0.2, bench_ret_1y=0.1,
                         dividend_yield=0.01, beta=0.9, analyst_rating="buy", sector="NIFTYIT"))
    items = checklist(row, sector_medians={"NIFTYIT": {"pe": 25.0}})
    by_id = {i["id"]: i for i in items}
    assert by_id["roe"]["passed"] and "20.0%" in by_id["roe"]["detail"]
    assert not by_id["pe_vs_sector"]["passed"] and "25.0" in by_id["pe_vs_sector"]["detail"]
    assert not by_id["rsi"]["passed"]                                 # 72 is overbought
    assert by_id["beats_nifty"]["passed"]
    assert len(items) >= 15 and all({"id", "label", "passed", "detail", "group"} <= set(i) for i in items)
    assert sum(i["passed"] for i in items) == sum(1 for i in items if i["passed"] is True)
