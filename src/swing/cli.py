# -*- coding: utf-8 -*-
"""Command line for the India swing-trading engine: ``python swing.py <command>``."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import List, Optional

import pandas as pd

from src.swing.config import SwingConfig

STATE_DIR = Path("data/swing")


def _universe_stocks(args):
    from src.swing.data import load_universe, stocks_from_symbols

    if getattr(args, "symbols", None):
        return stocks_from_symbols(args.symbols.split(","))
    return load_universe(args.universe)


def build_engine(stocks, *, years: float, config: SwingConfig, refresh: bool = False, end: Optional[str] = None):
    from src.swing.data import load_prices
    from src.swing.ranking import SignalEngine

    start = (date.today() - timedelta(days=int(365 * years) + 30)).isoformat()
    panel = load_prices([s.symbol for s in stocks], start=start, end=end, refresh=refresh)
    benchmark = panel["benchmark"].iloc[:, 0]
    prices = {f: panel[f] for f in ("open", "high", "low", "close", "volume")}
    sector_of = {s.symbol: s.sector for s in stocks}
    return SignalEngine(prices, benchmark=benchmark, sector_of=sector_of, config=config)


def _fmt_inr(value: float) -> str:
    return f"₹{value:,.2f}"


def cmd_rank(args) -> int:
    from src.swing.risk import position_size

    config = SwingConfig(capital=args.capital)
    stocks = _universe_stocks(args)
    names = {s.symbol: s.name for s in stocks}
    engine = build_engine(stocks, years=2, config=config, refresh=args.refresh)
    ranked = engine.rank()
    picks = engine.select(ranked)
    day = engine.close.index[-1].date()
    regime = "RISK-ON (Nifty above 200-day average)" if engine.risk_on() else "RISK-OFF (Nifty below 200-day average)"

    print(f"\nSwing candidates as of {day}  |  universe: {len(stocks)} stocks  |  market: {regime}")
    print(f"Eligible with >= {config.min_reward_risk:.0f}:1 reward-to-risk: {len(ranked)}\n")
    header = f"{'#':>2}  {'Symbol':<14} {'Sector':<17} {'Score':>5}  {'Setup':<8} {'Entry':>10} {'Stop':>10} {'Target':>10} {'R:R':>4}"
    print(header)
    print("-" * len(header))
    for i, c in enumerate(ranked[: args.top], 1):
        print(
            f"{i:>2}  {c.symbol:<14} {c.sector:<17} {c.score:5.1f}  {c.setup:<8} "
            f"{c.entry:10.2f} {c.stop:10.2f} {c.target:10.2f} {c.reward_risk:4.1f}"
        )

    print(f"\nSuggested portfolio (max {engine.max_positions()} positions, <= {config.max_per_sector} per sector, "
          f"correlation < {config.max_correlation}) for {_fmt_inr(config.capital)}:")
    plan = []
    cash = config.capital
    for c in picks:
        qty = position_size(equity=config.capital, entry=c.entry, stop=c.stop, config=config, cash=cash)
        if qty <= 0:
            continue
        cash -= qty * c.entry
        risk = qty * c.risk_per_share
        print(f"  BUY {qty:>5} x {c.symbol:<14} ~{_fmt_inr(c.entry):>12}  stop {c.stop:9.2f}  target {c.target:9.2f}"
              f"  (risk {_fmt_inr(risk)}, value {_fmt_inr(qty * c.entry)})")
        plan.append({**c.to_dict(), "name": names.get(c.symbol, c.symbol), "qty": qty})
    if not plan:
        print("  (no trades today)")
    else:
        print(f"  Cash left: {_fmt_inr(cash)}")

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    out = {
        "as_of": day.isoformat(),
        "risk_on": engine.risk_on(),
        "universe_size": len(stocks),
        "candidates": [{**c.to_dict(), "name": names.get(c.symbol, c.symbol)} for c in ranked],
        "portfolio": plan,
    }
    (STATE_DIR / "latest_rank.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nSaved to {STATE_DIR / 'latest_rank.json'}.  Research only, not investment advice.")
    return 0


def _pct(x) -> str:
    return "n/a" if x is None else f"{x * 100:+.1f}%"


def print_backtest_summary(summary) -> None:
    s = summary
    print(f"\nBacktest {s['start']} -> {s['end']}  |  capital {_fmt_inr(s['initial_capital'])}")
    print("-" * 64)
    rows = [
        ("Final equity (pre-tax)", _fmt_inr(s["final_equity"])),
        ("Final equity (after est. 20% STCG)", _fmt_inr(s["post_tax_final_equity"])),
        ("CAGR  strategy / Nifty 50", f"{_pct(s['cagr'])} / {_pct(s['benchmark_cagr'])}"),
        ("Max drawdown  strategy / Nifty 50", f"{_pct(s['max_drawdown'])} / {_pct(s['benchmark_max_drawdown'])}"),
        ("Sharpe (rf 6.5%)", f"{s['sharpe']:.2f}"),
        ("Trades / win rate", f"{s['trades']} / {s['win_rate'] * 100:.0f}%"),
        ("Avg win / avg loss", f"{_fmt_inr(s['avg_win'])} / {_fmt_inr(s['avg_loss'])}"),
        ("Profit factor / avg R", f"{s['profit_factor']:.2f} / {s['avg_r']:+.2f}R"),
        ("Avg holding (days)", f"{s['avg_bars_held']:.1f}"),
        ("Total costs paid", _fmt_inr(s["total_costs"])),
        ("Exit reasons", ", ".join(f"{k} {v}" for k, v in s["exit_reasons"].items())),
    ]
    for label, value in rows:
        print(f"  {label:<38} {value}")
    if "out_of_sample" in s:
        ins, oos = s["in_sample"], s["out_of_sample"]
        print(f"\n  First 70%: CAGR {_pct(ins['cagr'])} vs Nifty {_pct(ins['benchmark_cagr'])}, "
              f"max DD {_pct(ins['max_drawdown'])}")
        print(f"  Last 30%:  CAGR {_pct(oos['cagr'])} vs Nifty {_pct(oos['benchmark_cagr'])}, "
              f"max DD {_pct(oos['max_drawdown'])}")
    print("\n  Year    Strategy    Nifty 50")
    for year, row in s["yearly"].items():
        print(f"  {year}    {_pct(row['strategy']):>8}    {_pct(row['benchmark']):>8}")
    print("\nCaveat: today's Nifty 100 members are used for the whole period (survivorship bias),")
    print("so results are likely optimistic. Past results do not predict future returns.")


def cmd_backtest(args) -> int:
    from src.swing.backtest import Backtester

    config = SwingConfig(capital=args.capital)
    stocks = _universe_stocks(args)
    engine = build_engine(stocks, years=args.years + 1.1, config=config, refresh=args.refresh)
    start = engine.close.index[0] + pd.Timedelta(days=380)
    result = Backtester(engine, config=config).run(start=start)
    summary = result.summary()
    print_backtest_summary(summary)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    bench = result.benchmark.reindex(result.equity.index).ffill()
    payload = {
        "summary": summary,
        "equity": [
            {"date": d.date().isoformat(), "equity": round(v, 2),
             "benchmark": round(float(bench.loc[d] / bench.iloc[0] * config.capital), 2)}
            for d, v in result.equity.items()
        ],
        "trades": [t.to_dict() for t in result.trades],
    }
    (STATE_DIR / "backtest.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved full results to {STATE_DIR / 'backtest.json'}.")
    return 0


def cmd_universe(args) -> int:
    from src.swing.data import load_universe, refresh_universe

    if args.refresh:
        print(f"Downloaded {refresh_universe(args.universe)} constituents from NSE.")
    stocks = load_universe(args.universe)
    for s in stocks:
        print(f"{s.symbol:<16} {s.sector:<17} {s.name}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="swing.py", description="India swing-trading research engine")
    sub = parser.add_subparsers(dest="command", required=True)

    def universe_args(p):
        p.add_argument("--universe", default="nifty100", choices=["nifty100"])
        p.add_argument("--symbols", help="comma-separated tickers instead of the universe, e.g. TCS.NS,INFY.NS")

    p = sub.add_parser("rank", help="rank today's swing candidates and suggest a portfolio")
    universe_args(p)
    p.add_argument("--top", type=int, default=15)
    p.add_argument("--capital", type=float, default=SwingConfig().capital)
    p.add_argument("--refresh", action="store_true", help="ignore the price cache")
    p.set_defaults(func=cmd_rank)

    p = sub.add_parser("backtest", help="replay the strategy over past years with Indian costs and tax")
    universe_args(p)
    p.add_argument("--years", type=float, default=5)
    p.add_argument("--capital", type=float, default=SwingConfig().capital)
    p.add_argument("--refresh", action="store_true", help="ignore the price cache")
    p.set_defaults(func=cmd_backtest)

    p = sub.add_parser("universe", help="list (or --refresh from NSE) the stock universe")
    p.add_argument("--universe", default="nifty100", choices=["nifty100"])
    p.add_argument("--refresh", action="store_true")
    p.set_defaults(func=cmd_universe)
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    for noisy in ("yfinance", "urllib3", "peewee"):
        logging.getLogger(noisy).setLevel(logging.CRITICAL)
    args = build_parser().parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    sys.exit(main())
