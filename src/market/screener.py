# -*- coding: utf-8 -*-
"""Screener grammar, metric catalogue and preset screens (SPEC §7).

Filters are ``metric:op:value`` strings, ANDed. They run as pandas masks over
the in-memory metrics frame; blanks never match.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

# kind: number | percent | money | score | text | bool
METRICS: Dict[str, Dict[str, str]] = {
    # identity
    "sector": {"label": "Sector", "kind": "text", "group": "Identity"},
    "industry": {"label": "Industry", "kind": "text", "group": "Identity"},
    "cap_bucket": {"label": "Market-cap bucket", "kind": "text", "group": "Identity"},
    "market_cap": {"label": "Market cap", "kind": "money", "group": "Identity"},
    "overall": {"label": "Overall label", "kind": "text", "group": "Scores"},
    # scores
    "quality_score": {"label": "Quality score", "kind": "score", "group": "Scores"},
    "value_score": {"label": "Value score", "kind": "score", "group": "Scores"},
    "momentum_score": {"label": "Momentum score", "kind": "score", "group": "Scores"},
    "checklist_passed": {"label": "Checklist rules passed", "kind": "number", "group": "Scores"},
    # price and returns
    "price": {"label": "Price", "kind": "money", "group": "Price"},
    "change_1d_pct": {"label": "1-day change", "kind": "percent", "group": "Price"},
    "ret_1w": {"label": "1-week return", "kind": "percent", "group": "Price"},
    "ret_1m": {"label": "1-month return", "kind": "percent", "group": "Price"},
    "ret_3m": {"label": "3-month return", "kind": "percent", "group": "Price"},
    "ret_6m": {"label": "6-month return", "kind": "percent", "group": "Price"},
    "ret_1y": {"label": "1-year return", "kind": "percent", "group": "Price"},
    "ret_3y": {"label": "3-year return", "kind": "percent", "group": "Price"},
    "pct_from_52w_high": {"label": "Distance from 52-week high", "kind": "percent", "group": "Price"},
    "pct_from_52w_low": {"label": "Distance from 52-week low", "kind": "percent", "group": "Price"},
    "rs_1m": {"label": "Relative strength vs Nifty, 1 month", "kind": "percent", "group": "Price"},
    "rs_3m": {"label": "Relative strength vs Nifty, 3 months", "kind": "percent", "group": "Price"},
    "rs_6m": {"label": "Relative strength vs Nifty, 6 months", "kind": "percent", "group": "Price"},
    "max_drawdown_1y": {"label": "Worst drawdown, 1 year", "kind": "percent", "group": "Price"},
    # technicals
    "above_sma20": {"label": "Above 20-day average", "kind": "bool", "group": "Technicals"},
    "above_sma50": {"label": "Above 50-day average", "kind": "bool", "group": "Technicals"},
    "above_sma200": {"label": "Above 200-day average", "kind": "bool", "group": "Technicals"},
    "golden_cross": {"label": "Golden cross (50 over 200)", "kind": "bool", "group": "Technicals"},
    "new_52w_high": {"label": "New 52-week high today", "kind": "bool", "group": "Technicals"},
    "new_52w_low": {"label": "New 52-week low today", "kind": "bool", "group": "Technicals"},
    "rsi14": {"label": "RSI (14)", "kind": "number", "group": "Technicals"},
    "macd_hist": {"label": "MACD histogram", "kind": "number", "group": "Technicals"},
    "atr14_pct": {"label": "ATR (14) as % of price", "kind": "percent", "group": "Technicals"},
    "volatility_1y": {"label": "Volatility, 1 year", "kind": "percent", "group": "Technicals"},
    "beta_1y": {"label": "Beta vs Nifty, 1 year", "kind": "number", "group": "Technicals"},
    "beta": {"label": "Beta (Yahoo)", "kind": "number", "group": "Technicals"},
    "volume_ratio": {"label": "Volume vs 20-day average", "kind": "number", "group": "Technicals"},
    "avg_volume_20": {"label": "Average volume, 20 days", "kind": "number", "group": "Technicals"},
    # fundamentals
    "pe": {"label": "PE (trailing)", "kind": "number", "group": "Valuation"},
    "forward_pe": {"label": "PE (forward)", "kind": "number", "group": "Valuation"},
    "pb": {"label": "Price to book", "kind": "number", "group": "Valuation"},
    "ev_ebitda": {"label": "EV / EBITDA", "kind": "number", "group": "Valuation"},
    "peg": {"label": "PEG", "kind": "number", "group": "Valuation"},
    "dividend_yield": {"label": "Dividend yield", "kind": "percent", "group": "Valuation"},
    "fcf_yield": {"label": "Free-cash-flow yield", "kind": "percent", "group": "Valuation"},
    "roe": {"label": "Return on equity", "kind": "percent", "group": "Quality"},
    "roa": {"label": "Return on assets", "kind": "percent", "group": "Quality"},
    "operating_margin": {"label": "Operating margin", "kind": "percent", "group": "Quality"},
    "profit_margin": {"label": "Net margin", "kind": "percent", "group": "Quality"},
    "debt_to_equity": {"label": "Debt to equity", "kind": "number", "group": "Quality"},
    "current_ratio": {"label": "Current ratio", "kind": "number", "group": "Quality"},
    "fcf_positive": {"label": "Free cash flow positive", "kind": "bool", "group": "Quality"},
    "revenue_growth": {"label": "Revenue growth (y/y)", "kind": "percent", "group": "Growth"},
    "earnings_growth": {"label": "Earnings growth (y/y)", "kind": "percent", "group": "Growth"},
    # ownership and street
    "promoter_holding": {"label": "Promoter / insider holding", "kind": "percent", "group": "Ownership"},
    "institutional_holding": {"label": "Institutional holding", "kind": "percent", "group": "Ownership"},
    "analyst_count": {"label": "Analysts covering", "kind": "number", "group": "Street view"},
    "analyst_rating": {"label": "Analyst consensus", "kind": "text", "group": "Street view"},
    "analyst_upside": {"label": "Upside to analyst target", "kind": "percent", "group": "Street view"},
}

NUMERIC_OPS = {"lt", "lte", "gt", "gte", "eq"}
TEXT_OPS = {"eq", "in"}
BOOL_OPS = {"is"}
NUMERIC_KINDS = {"number", "percent", "money", "score"}

DEFAULT_COLUMNS = ["symbol", "name", "sector", "industry", "cap_bucket", "price", "change_1d_pct", "market_cap",
                   "quality_score", "value_score", "momentum_score", "overall", "pe", "roe", "ret_1y"]


@dataclass(frozen=True)
class Filter:
    metric: str
    op: str
    value: Any

    def as_string(self) -> str:
        v = ",".join(self.value) if isinstance(self.value, list) else str(self.value).lower() if isinstance(self.value, bool) else self.value
        return f"{self.metric}:{self.op}:{v}"


def parse_filters(raw: Iterable[str]) -> List[Filter]:
    out: List[Filter] = []
    for text in raw:
        parts = str(text).split(":", 2)
        if len(parts) != 3:
            raise ValueError(f"filter '{text}' must look like metric:op:value")
        metric, op, value = (p.strip() for p in parts)
        spec = METRICS.get(metric)
        if spec is None:
            raise ValueError(f"unknown metric '{metric}'")
        kind = spec["kind"]
        if kind in NUMERIC_KINDS:
            if op not in NUMERIC_OPS:
                raise ValueError(f"operator '{op}' is not valid for {metric}; use one of {sorted(NUMERIC_OPS)}")
            try:
                parsed: Any = float(value)
            except ValueError:
                raise ValueError(f"value '{value}' for {metric} must be a number") from None
        elif kind == "text":
            if op not in TEXT_OPS:
                raise ValueError(f"operator '{op}' is not valid for {metric}; use eq or in")
            parsed = [v.strip() for v in value.split(",") if v.strip()] if op == "in" else value
        else:  # bool
            if op not in BOOL_OPS or value.lower() not in ("true", "false"):
                raise ValueError(f"{metric} takes 'is:true' or 'is:false'")
            parsed = value.lower() == "true"
        out.append(Filter(metric, op, parsed))
    return out


def _mask(frame: pd.DataFrame, f: Filter) -> pd.Series:
    if f.metric not in frame:
        return pd.Series(False, index=frame.index)
    col = frame[f.metric]
    if f.op == "is":
        return col.map(lambda v: v is True or v is np.True_ or v == 1.0 if f.value else v is False or v is np.False_ or v == 0.0).fillna(False).astype(bool) if col.dtype == object else (col.astype("boolean") == f.value).fillna(False).astype(bool)
    if f.op == "in":
        return col.isin(f.value)
    if METRICS[f.metric]["kind"] == "text":
        return col == f.value
    num = pd.to_numeric(col, errors="coerce")
    return {"lt": num < f.value, "lte": num <= f.value, "gt": num > f.value, "gte": num >= f.value, "eq": num == f.value}[f.op]


def _clean(v):
    if isinstance(v, (np.floating, float)):
        return None if np.isnan(v) else float(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    if v is pd.NaT or (v is not None and v != v):
        return None
    return v


def run_screen(
    frame: pd.DataFrame,
    filters: List[Filter],
    *,
    sort: Optional[str] = None,
    descending: bool = True,
    limit: Optional[int] = None,
    offset: int = 0,
    columns: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Apply filters, sort, page; rows carry the default columns plus every filtered/sorted metric."""
    mask = pd.Series(True, index=frame.index)
    for f in filters:
        mask &= _mask(frame, f)
    hits = frame[mask]
    sort_col = sort if sort in hits.columns else ("market_cap" if "market_cap" in hits.columns else None)
    if sort_col:
        hits = hits.sort_values(sort_col, ascending=not descending, na_position="last", kind="mergesort")
    total = int(len(hits))
    page = hits.iloc[offset: offset + limit if limit else None]
    wanted = list(dict.fromkeys((columns or DEFAULT_COLUMNS) + [f.metric for f in filters] + ([sort_col] if sort_col else [])))
    rows = []
    for symbol, row in page.iterrows():
        rec = {"symbol": symbol}
        for c in wanted:
            if c == "symbol":
                continue
            rec[c] = _clean(row[c]) if c in page.columns else None
        rows.append(rec)
    return {"total": total, "rows": rows, "columns": wanted, "sort": sort_col, "descending": descending}


PRESETS: Dict[str, Dict[str, Any]] = {
    "top-gainers": {"name": "Top gainers today", "group": "Today", "description": "Largest one-day rises in the universe.",
                    "filters": ["change_1d_pct:gt:0"], "sort": "change_1d_pct"},
    "top-losers": {"name": "Top losers today", "group": "Today", "description": "Largest one-day falls in the universe.",
                   "filters": ["change_1d_pct:lt:0"], "sort": "change_1d_pct", "descending": False},
    "volume-shockers": {"name": "Volume shockers", "group": "Today", "description": "Traded at least three times the 20-day average volume.",
                        "filters": ["volume_ratio:gte:3"], "sort": "volume_ratio"},
    "new-52w-highs": {"name": "New 52-week highs", "group": "Today", "description": "Closed at a new 52-week high today.",
                      "filters": ["new_52w_high:is:true"], "sort": "momentum_score"},
    "new-52w-lows": {"name": "New 52-week lows", "group": "Today", "description": "Closed at a new 52-week low today.",
                     "filters": ["new_52w_low:is:true"], "sort": "momentum_score", "descending": False},
    "momentum-leaders": {"name": "Momentum leaders", "group": "Momentum", "description": "Momentum score 70 or more and above the 200-day average.",
                         "filters": ["momentum_score:gte:70", "above_sma200:is:true"], "sort": "momentum_score"},
    "near-52w-high": {"name": "Near 52-week high", "group": "Momentum", "description": "Within 5% of the 52-week high.",
                      "filters": ["pct_from_52w_high:gte:-0.05"], "sort": "momentum_score"},
    "golden-cross": {"name": "Golden cross", "group": "Technical", "description": "50-day average above the 200-day and price above both.",
                     "filters": ["golden_cross:is:true", "above_sma200:is:true"], "sort": "ret_1m"},
    "oversold": {"name": "Oversold (RSI ≤ 30)", "group": "Technical", "description": "RSI (14) at or below 30: stretched to the downside.",
                 "filters": ["rsi14:lte:30"], "sort": "rsi14", "descending": False},
    "smallcap-breakouts": {"name": "Small-cap breakouts", "group": "Momentum", "description": "Small caps within 3% of their 52-week high on rising volume.",
                           "filters": ["cap_bucket:eq:small", "pct_from_52w_high:gte:-0.03", "volume_ratio:gte:1.5"], "sort": "momentum_score"},
    "quality-compounders": {"name": "Quality compounders", "group": "Quality", "description": "Quality score 70+, ROE at least 15%, debt to equity at most 1.",
                            "filters": ["quality_score:gte:70", "roe:gte:0.15", "debt_to_equity:lte:1"], "sort": "quality_score"},
    "value-picks": {"name": "Value picks", "group": "Value", "description": "Value score 70+, PE at most 20, ROE at least 12%.",
                    "filters": ["value_score:gte:70", "pe:lte:20", "roe:gte:0.12"], "sort": "value_score"},
    "dividend-payers": {"name": "Dividend payers", "group": "Value", "description": "Dividend yield of 2% or more.",
                        "filters": ["dividend_yield:gte:0.02"], "sort": "dividend_yield"},
    "analyst-favourites": {"name": "Analyst favourites", "group": "Street view", "description": "Consensus buy with at least 15% upside to the mean target.",
                           "filters": ["analyst_rating:in:buy,strong_buy", "analyst_upside:gte:0.15"], "sort": "analyst_upside"},
    "strong-overall": {"name": "Strong on all three scores", "group": "Scores", "description": "Overall label Strong: two or more scores at 60+ and none below 35.",
                       "filters": ["overall:eq:Strong"], "sort": "momentum_score"},
    "red-flags": {"name": "Red flags", "group": "Red flags", "description": "Negative free cash flow with debt to equity above 1.5.",
                  "filters": ["fcf_positive:is:false", "debt_to_equity:gte:1.5"], "sort": "debt_to_equity"},
}


def preset_counts(frame: pd.DataFrame) -> Dict[str, int]:
    return {key: run_screen(frame, parse_filters(p["filters"]))["total"] for key, p in PRESETS.items()}
