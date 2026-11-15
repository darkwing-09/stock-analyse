# -*- coding: utf-8 -*-
"""Metric catalogue for the research platform: technicals from the price panel,
fundamentals normalised from Yahoo ``info``, Quality / Value / Momentum scores
and the "check before you buy" checklist.

Everything here is pure: frames in, frames out, no network. See
docs/market-platform/SPEC.md §3–§5 for the definitions.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Mapping, Optional

import numpy as np
import pandas as pd

RETURN_BARS = {"ret_1w": 5, "ret_1m": 22, "ret_3m": 63, "ret_6m": 126, "ret_1y": 252, "ret_3y": 756}
YEAR = 252

# Yahoo ``info`` key -> (our column, scale). Percent-style Yahoo fields are divided by 100.
INFO_FIELDS: Dict[str, tuple] = {
    "longName": ("long_name", None),
    "marketCap": ("market_cap", 1.0),
    "trailingPE": ("pe", 1.0),
    "forwardPE": ("forward_pe", 1.0),
    "priceToBook": ("pb", 1.0),
    "enterpriseToEbitda": ("ev_ebitda", 1.0),
    "trailingPegRatio": ("peg", 1.0),
    "returnOnEquity": ("roe", 1.0),
    "returnOnAssets": ("roa", 1.0),
    "operatingMargins": ("operating_margin", 1.0),
    "profitMargins": ("profit_margin", 1.0),
    "revenueGrowth": ("revenue_growth", 1.0),
    "earningsGrowth": ("earnings_growth", 1.0),
    "debtToEquity": ("debt_to_equity", 0.01),
    "currentRatio": ("current_ratio", 1.0),
    "dividendYield": ("dividend_yield", 0.01),
    "freeCashflow": ("fcf", 1.0),
    "bookValue": ("book_value", 1.0),
    "trailingEps": ("eps_ttm", 1.0),
    "forwardEps": ("eps_forward", 1.0),
    "totalCash": ("total_cash", 1.0),
    "totalDebt": ("total_debt", 1.0),
    "beta": ("beta", 1.0),
    "heldPercentInsiders": ("promoter_holding", 1.0),
    "heldPercentInstitutions": ("institutional_holding", 1.0),
    "numberOfAnalystOpinions": ("analyst_count", 1.0),
    "recommendationKey": ("analyst_rating", None),
    "targetMeanPrice": ("target_price", 1.0),
    "currentPrice": ("info_price", 1.0),
    "fullTimeEmployees": ("employees", 1.0),
    "website": ("website", None),
    "longBusinessSummary": ("summary", None),
}
NUMERIC_FUNDAMENTALS = [col for col, scale in INFO_FIELDS.values() if scale is not None]
TEXT_FUNDAMENTALS = [col for col, scale in INFO_FIELDS.values() if scale is None]

CAP_LARGE, CAP_MID = 20_000e7, 5_000e7      # ₹20,000 cr and ₹5,000 cr


# ----------------------------------------------------------------------------- technicals

def _rsi(close: pd.DataFrame, n: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
    last_gain, last_loss = gain.iloc[-1], loss.iloc[-1]
    rsi = 100 - 100 / (1 + last_gain / last_loss.replace(0, np.nan))
    rsi = rsi.where(last_loss != 0, 100.0)          # no losses at all -> 100
    rsi = rsi.where(~((last_gain == 0) & (last_loss == 0)), 50.0)
    return rsi.clip(0, 100)


def _back(close: pd.DataFrame, n: int) -> pd.Series:
    if len(close) <= n:
        return pd.Series(np.nan, index=close.columns)
    return close.iloc[-1] / close.iloc[-1 - n] - 1


def compute_technicals(panel: Mapping[str, pd.DataFrame]) -> pd.DataFrame:
    """One row per symbol with price, returns, range, trend, oscillators, volume and relative strength."""
    close, high, low, volume = panel["close"], panel["high"], panel["low"], panel["volume"]
    bench = panel["benchmark"].iloc[:, 0].reindex(close.index).ffill()
    out = pd.DataFrame(index=close.columns)
    out.index.name = "symbol"

    last = close.iloc[-1]
    out["price"] = last
    out["change_1d_pct"] = _back(close, 1)
    for col, n in RETURN_BARS.items():
        out[col] = _back(close, n)
    bench_frame = bench.to_frame("b")
    for col, n in (("bench_ret_1m", 22), ("bench_ret_3m", 63), ("bench_ret_6m", 126), ("bench_ret_1y", 252)):
        out[col] = float(_back(bench_frame, n).iloc[0]) if len(bench_frame) > n else np.nan
    for h in ("1m", "3m", "6m"):
        out[f"rs_{h}"] = out[f"ret_{h}"] - out[f"bench_ret_{h}"]

    yr_high, yr_low = high.iloc[-YEAR:], low.iloc[-YEAR:]
    out["high_52w"] = yr_high.max()
    out["low_52w"] = yr_low.min()
    out["pct_from_52w_high"] = last / out["high_52w"] - 1
    out["pct_from_52w_low"] = last / out["low_52w"] - 1
    yr_close = close.iloc[-YEAR:]
    out["new_52w_high"] = last >= yr_close.max() - 1e-9
    out["new_52w_low"] = last <= yr_close.min() + 1e-9
    running_max = yr_close.cummax()
    out["max_drawdown_1y"] = (yr_close / running_max - 1).min()

    for n in (20, 50, 200):
        out[f"sma{n}"] = close.rolling(n, min_periods=n).mean().iloc[-1]
        out[f"above_sma{n}"] = last > out[f"sma{n}"]
    for n in (20, 50):
        out[f"ema{n}"] = close.ewm(span=n, min_periods=n, adjust=False).mean().iloc[-1]
    out["golden_cross"] = out["sma50"] > out["sma200"]

    out["rsi14"] = _rsi(close, 14)
    ema12, ema26 = close.ewm(span=12, adjust=False).mean(), close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    out["macd_hist"] = (macd - macd.ewm(span=9, adjust=False).mean()).iloc[-1]

    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()]).groupby(level=0).max()
    out["atr14_pct"] = tr.rolling(14, min_periods=14).mean().iloc[-1] / last

    rets = close.pct_change().iloc[-YEAR:]
    out["volatility_1y"] = rets.std() * math.sqrt(YEAR)
    brets = bench.pct_change().iloc[-YEAR:]
    bvar = brets.var()
    out["beta_1y"] = rets.apply(lambda s: s.cov(brets) / bvar if bvar and bvar > 0 else np.nan)

    prev_vol = volume.iloc[-21:-1]
    out["avg_volume_20"] = prev_vol.mean()
    out["volume_ratio"] = volume.iloc[-1] / out["avg_volume_20"].replace(0, np.nan)
    out["turnover_20"] = (close.iloc[-21:-1] * prev_vol).mean()
    out["as_of"] = close.index[-1].date().isoformat()
    return out


# ----------------------------------------------------------------------------- fundamentals

def _num(v) -> float:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return np.nan
    return f if math.isfinite(f) else np.nan


def fundamentals_frame(info_by_symbol: Mapping[str, Mapping[str, Any]]) -> pd.DataFrame:
    """Normalise Yahoo ``info`` dicts: ratios as decimals, blanks as NaN, text as str or None."""
    rows = []
    for symbol, info in info_by_symbol.items():
        info = info or {}
        row: Dict[str, Any] = {"symbol": symbol}
        for key, (col, scale) in INFO_FIELDS.items():
            raw = info.get(key)
            if scale is None:
                row[col] = str(raw) if raw not in (None, "") else None
            else:
                row[col] = _num(raw) * scale if raw is not None else np.nan
        if np.isnan(row["peg"]) and info.get("pegRatio") is not None:
            row["peg"] = _num(info.get("pegRatio"))
        rows.append(row)
    cols = ["symbol"] + [c for c, _ in INFO_FIELDS.values()]
    f = pd.DataFrame(rows, columns=cols).set_index("symbol")
    f.index.name = "symbol"
    for col in NUMERIC_FUNDAMENTALS:
        f[col] = pd.to_numeric(f[col], errors="coerce")
    f["analyst_count"] = f["analyst_count"].fillna(0).astype(int)
    f["fcf_positive"] = f["fcf"].where(f["fcf"].notna()).gt(0).where(f["fcf"].notna())
    f["fcf_yield"] = f["fcf"] / f["market_cap"].replace(0, np.nan)
    f["analyst_upside"] = f["target_price"] / f["info_price"].replace(0, np.nan) - 1
    f["cap_bucket"] = pd.cut(f["market_cap"], [-np.inf, CAP_MID, CAP_LARGE, np.inf], labels=["small", "mid", "large"]).astype(object)
    f.loc[f["market_cap"].isna(), "cap_bucket"] = None
    return f


# ----------------------------------------------------------------------------- scores

QUALITY_INPUTS = [("roe", 1), ("operating_margin", 1), ("debt_to_equity", -1), ("fcf_positive", 1), ("earnings_growth", 1), ("revenue_growth", 1)]
VALUE_INPUTS = [("pe", -1, "sector"), ("pb", -1, "sector"), ("ev_ebitda", -1, None), ("dividend_yield", 1, None), ("peg", -1, None)]
MOMENTUM_INPUTS = [("ret_6m", 1), ("ret_3m", 1), ("rs_3m", 1), ("pct_from_52w_high", 1), ("above_sma200", 1), ("rsi_comp", 1)]


def _pct_rank(series: pd.Series, direction: int, by: Optional[pd.Series] = None) -> pd.Series:
    s = pd.to_numeric(series, errors="coerce").astype(float)
    if by is not None:
        return s.groupby(by.fillna("—")).rank(pct=True, ascending=direction > 0) * 100
    return s.rank(pct=True, ascending=direction > 0) * 100


def _combine(parts: List[pd.Series]) -> tuple:
    stack = pd.concat(parts, axis=1)
    known = stack.notna().sum(axis=1)
    score = stack.mean(axis=1).where(known > 0, 50.0)        # nothing known -> neutral
    return score.clip(0, 100).round(1), known


def score_universe(frame: pd.DataFrame) -> pd.DataFrame:
    """Add quality_score, value_score, momentum_score (0–100 percentiles) and the overall label."""
    f = frame.copy()
    for col in {c for c, *_ in QUALITY_INPUTS + VALUE_INPUTS + MOMENTUM_INPUTS if c != "rsi_comp"}:
        if col not in f:
            f[col] = np.nan
    if "sector" not in f:
        f["sector"] = None
    f["rsi_comp"] = -(pd.to_numeric(f["rsi14"], errors="coerce") - 57.5).abs() if "rsi14" in f else np.nan

    f["quality_score"], f["quality_inputs"] = _combine([_pct_rank(f[c], d) for c, d in QUALITY_INPUTS])
    f["value_score"], f["value_inputs"] = _combine([_pct_rank(f[c], d, f["sector"] if by == "sector" else None) for c, d, by in VALUE_INPUTS])
    f["momentum_score"], f["momentum_inputs"] = _combine([_pct_rank(f[c], d) for c, d in MOMENTUM_INPUTS])

    scores = f[["quality_score", "value_score", "momentum_score"]]
    strong = ((scores >= 60).sum(axis=1) >= 2) & ((scores < 35).sum(axis=1) == 0)
    weak = (scores < 40).sum(axis=1) >= 2
    f["overall"] = np.where(strong, "Strong", np.where(weak, "Weak", "Mixed"))
    return f.drop(columns=["rsi_comp"])


# ----------------------------------------------------------------------------- checklist

def _pct(x: float, digits: int = 1) -> str:
    return f"{x * 100:.{digits}f}%"


def _get(row: Mapping[str, Any], key: str):
    v = row.get(key) if hasattr(row, "get") else None
    if v is None:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    if isinstance(v, (np.floating, np.integer)):
        return None if np.isnan(v) else v.item()
    if isinstance(v, np.bool_):
        return bool(v)
    return v


def checklist(row: Mapping[str, Any], sector_medians: Optional[Mapping[str, Mapping[str, float]]] = None) -> List[Dict[str, Any]]:
    """SPEC §5: each rule -> {id, group, label, passed (True/False/None), detail}."""
    sector = _get(row, "sector")
    med = (sector_medians or {}).get(sector, {}) if sector else {}
    items: List[Dict[str, Any]] = []

    def add(id_: str, group: str, label: str, value, test, detail_fn):
        if value is None:
            items.append({"id": id_, "group": group, "label": label, "passed": None, "detail": "Not enough data"})
        else:
            items.append({"id": id_, "group": group, "label": label, "passed": bool(test(value)), "detail": detail_fn(value)})

    g = "Financial health"
    add("roe", g, "Return on equity at least 15%", _get(row, "roe"), lambda v: v >= 0.15, lambda v: f"ROE {_pct(v)}")
    add("debt", g, "Debt to equity at most 1", _get(row, "debt_to_equity"), lambda v: v <= 1.0, lambda v: f"Debt/equity {v:.2f}")
    add("fcf", g, "Free cash flow positive", _get(row, "fcf_positive"), lambda v: bool(v), lambda v: "Positive" if v else "Negative")
    add("margin", g, "Operating margin at least 10%", _get(row, "operating_margin"), lambda v: v >= 0.10, lambda v: f"Operating margin {_pct(v)}")

    g = "Growth"
    add("revenue_growth", g, "Revenue growing at least 10%", _get(row, "revenue_growth"), lambda v: v >= 0.10, lambda v: f"Revenue growth {_pct(v)}")
    add("earnings_growth", g, "Earnings growing at least 10%", _get(row, "earnings_growth"), lambda v: v >= 0.10, lambda v: f"Earnings growth {_pct(v)}")

    g = "Valuation"
    pe, sector_pe = _get(row, "pe"), med.get("pe")
    if pe is None or sector_pe is None or (isinstance(sector_pe, float) and math.isnan(sector_pe)):
        items.append({"id": "pe_vs_sector", "group": g, "label": "PE below the sector median", "passed": None, "detail": "Not enough data"})
    else:
        items.append({"id": "pe_vs_sector", "group": g, "label": "PE below the sector median", "passed": bool(pe < sector_pe),
                      "detail": f"PE {pe:.1f} vs sector median {sector_pe:.1f}"})
    add("peg", g, "PEG at most 1.5", _get(row, "peg"), lambda v: v <= 1.5, lambda v: f"PEG {v:.2f}")
    add("pb", g, "Price to book at most 5", _get(row, "pb"), lambda v: v <= 5.0, lambda v: f"PB {v:.2f}")

    g = "Technicals"
    add("above_200", g, "Price above the 200-day average", _get(row, "above_sma200"), lambda v: bool(v), lambda v: "Above" if v else "Below")
    add("above_50", g, "Price above the 50-day average", _get(row, "above_sma50"), lambda v: bool(v), lambda v: "Above" if v else "Below")
    add("rsi", g, "RSI between 35 and 70", _get(row, "rsi14"), lambda v: 35 <= v <= 70, lambda v: f"RSI {v:.0f}")
    add("near_high", g, "Within 20% of the 52-week high", _get(row, "pct_from_52w_high"), lambda v: v >= -0.20, lambda v: f"{_pct(-v)} below the high")
    r1y, b1y = _get(row, "ret_1y"), _get(row, "bench_ret_1y")
    if r1y is None or b1y is None:
        items.append({"id": "beats_nifty", "group": g, "label": "One-year return above Nifty 50", "passed": None, "detail": "Not enough data"})
    else:
        items.append({"id": "beats_nifty", "group": g, "label": "One-year return above Nifty 50", "passed": bool(r1y > b1y),
                      "detail": f"Stock {_pct(r1y)} vs Nifty {_pct(b1y)}"})

    g = "Ownership"
    add("promoter", g, "Promoter or insider holding at least 40%", _get(row, "promoter_holding"), lambda v: v >= 0.40, lambda v: f"Insiders hold {_pct(v)}")
    add("institutions", g, "Institutions hold at least 15%", _get(row, "institutional_holding"), lambda v: v >= 0.15, lambda v: f"Institutions hold {_pct(v)}")
    add("dividend", g, "Pays a dividend", _get(row, "dividend_yield"), lambda v: v > 0, lambda v: f"Yield {_pct(v, 2)}")

    add("beta", "Risk", "Beta at most 1.2", _get(row, "beta"), lambda v: v <= 1.2, lambda v: f"Beta {v:.2f}")
    add("analyst", "Street view", "Analyst consensus is buy", _get(row, "analyst_rating"),
        lambda v: str(v).lower() in ("buy", "strong_buy"), lambda v: str(v).replace("_", " ").title())
    return items


def checklist_summary(items: Iterable[Mapping[str, Any]]) -> Dict[str, int]:
    items = list(items)
    return {
        "passed": sum(1 for i in items if i["passed"] is True),
        "failed": sum(1 for i in items if i["passed"] is False),
        "unknown": sum(1 for i in items if i["passed"] is None),
        "total": len(items),
    }


def sector_medians(frame: pd.DataFrame, columns: Iterable[str] = ("pe", "pb", "ev_ebitda", "roe", "dividend_yield", "debt_to_equity", "operating_margin", "revenue_growth")) -> Dict[str, Dict[str, float]]:
    cols = [c for c in columns if c in frame]
    if "sector" not in frame or not cols:
        return {}
    med = frame.groupby("sector")[cols].median(numeric_only=True)
    return {sector: {c: (None if pd.isna(v) else float(v)) for c, v in row.items()} for sector, row in med.iterrows()}
