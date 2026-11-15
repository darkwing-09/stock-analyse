# -*- coding: utf-8 -*-
"""Screener (seam: parse_filters / run_screen / PRESETS) on a small metrics frame."""

import numpy as np
import pandas as pd
import pytest

from src.market.screener import PRESETS, METRICS, parse_filters, run_screen

FRAME = pd.DataFrame.from_dict(
    {
        "A.NS": dict(name="Alpha", sector="NIFTYIT", industry="IT", market_cap=5e12, pe=12.0, roe=0.22, ret_1m=0.08,
                     rsi14=55.0, above_sma200=True, golden_cross=True, momentum_score=80.0, quality_score=70.0, value_score=65.0,
                     pct_from_52w_high=-0.03, volume_ratio=1.2, dividend_yield=0.01, debt_to_equity=0.3, fcf_positive=True,
                     analyst_rating="buy", analyst_upside=0.2, change_1d_pct=0.02, ret_1y=0.4, bench_ret_1y=0.1, beta=1.0,
                     revenue_growth=0.1, earnings_growth=0.2, promoter_holding=0.6, pb=3.0, ev_ebitda=10.0, peg=1.0),
        "B.NS": dict(name="Beta", sector="FINNIFTY", industry="Banks", market_cap=8e11, pe=35.0, roe=0.08, ret_1m=-0.05,
                     rsi14=28.0, above_sma200=False, golden_cross=False, momentum_score=20.0, quality_score=30.0, value_score=25.0,
                     pct_from_52w_high=-0.35, volume_ratio=3.5, dividend_yield=0.0, debt_to_equity=2.5, fcf_positive=False,
                     analyst_rating="hold", analyst_upside=-0.1, change_1d_pct=-0.06, ret_1y=-0.2, bench_ret_1y=0.1, beta=1.5,
                     revenue_growth=-0.1, earnings_growth=-0.3, promoter_holding=0.2, pb=0.8, ev_ebitda=25.0, peg=np.nan),
        "C.NS": dict(name="Gamma", sector="NIFTYIT", industry="IT", market_cap=2e11, pe=np.nan, roe=0.16, ret_1m=0.01,
                     rsi14=65.0, above_sma200=True, golden_cross=False, momentum_score=55.0, quality_score=60.0, value_score=50.0,
                     pct_from_52w_high=-0.12, volume_ratio=0.9, dividend_yield=0.03, debt_to_equity=0.0, fcf_positive=True,
                     analyst_rating="strong_buy", analyst_upside=0.3, change_1d_pct=0.005, ret_1y=0.15, bench_ret_1y=0.1, beta=0.8,
                     revenue_growth=0.2, earnings_growth=0.1, promoter_holding=0.5, pb=2.0, ev_ebitda=8.0, peg=0.9),
    },
    orient="index",
)


def test_parse_filters_accepts_the_documented_grammar():
    f = parse_filters(["pe:lt:20", "roe:gte:0.15", "sector:eq:NIFTYIT", "above_sma200:is:true"])
    assert [(x.metric, x.op) for x in f] == [("pe", "lt"), ("roe", "gte"), ("sector", "eq"), ("above_sma200", "is")]
    assert f[0].value == 20.0 and f[3].value is True


@pytest.mark.parametrize("bad", ["pe:between:1", "nope:lt:1", "pe:lt:abc", "pe"])
def test_parse_filters_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        parse_filters([bad])


def test_run_screen_filters_sorts_and_limits():
    res = run_screen(FRAME, parse_filters(["sector:eq:NIFTYIT"]), sort="momentum_score", descending=True)
    assert [r["symbol"] for r in res["rows"]] == ["A.NS", "C.NS"] and res["total"] == 2
    res = run_screen(FRAME, parse_filters(["pe:lt:20"]))
    assert [r["symbol"] for r in res["rows"]] == ["A.NS"]            # NaN never matches
    res = run_screen(FRAME, [], sort="market_cap", descending=False, limit=2)
    assert [r["symbol"] for r in res["rows"]] == ["C.NS", "B.NS"] and res["total"] == 3
    assert res["rows"][0]["name"] == "Gamma" and "momentum_score" in res["rows"][0]


def test_every_preset_runs_and_is_described():
    for key, preset in PRESETS.items():
        assert preset["name"] and preset["description"] and preset["group"]
        out = run_screen(FRAME, parse_filters(preset["filters"]), sort=preset.get("sort"))
        assert out["total"] >= 0
    assert "momentum-leaders" in PRESETS and "oversold" in PRESETS


def test_metric_catalogue_covers_filters_used_by_presets():
    used = {f.split(":")[0] for p in PRESETS.values() for f in p["filters"]}
    assert used <= set(METRICS)
    assert all({"label", "kind", "group"} <= set(m) for m in METRICS.values())
