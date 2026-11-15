# Stock Analyse — Market Platform

The plan to grow Stock Analyse from a swing-trading engine into a full Indian
stock-research platform of the Trendlyne kind: one page per stock with scores,
a checklist, financials, technicals and shareholding; a screener; a
markets-today page; watchlists and a portfolio tracker.

| Document | What it holds |
|---|---|
| [README.md](README.md) (this file) | Vision, principles, architecture, data sources, legal position |
| [SPEC.md](SPEC.md) | Product specification: pages, data model, metrics catalogue, scores, checklist, API, screener grammar |
| [ROADMAP.md](ROADMAP.md) | Versions and phases, in order, with the exit criteria for each |
| [TASKS.md](TASKS.md) | The task breakdown: every task with an ID, acceptance criteria, dependencies and status |

Related: [../india-quickstart.md](../india-quickstart.md) (running the current
engine), [../../apps/swing-dashboard/DESIGN.md](../../apps/swing-dashboard/DESIGN.md)
(the visual system every new page follows), [../../apps/swing-dashboard/PRODUCT.md](../../apps/swing-dashboard/PRODUCT.md).

## Vision

A personal research desk for Indian equities that **shows its working**. Every
number carries its source and its date; every score decomposes into the
percentile ranks behind it; every claim about a stock can be traced to a
filing, a price series or a formula in this repository. It runs on the user's
own machine from free data, refreshes itself every evening, and never places an
order unless the user turns live trading on.

Reference for breadth and information architecture: trendlyne.com. We copy the
*kind* of product (what a stock page answers, how a screener is organised),
never their data, scores, names or text.

## Principles

1. **Own data, own scores.** Prices and fundamentals from Yahoo Finance and NSE
   public files; scores computed here from documented formulas. Nothing is
   fetched from Trendlyne or any other paid or ToS-protected source.
2. **Honest numbers.** Benchmarks beside every return, caveats beside every
   backtest, "data to <date>" on every page, blanks shown as blanks.
3. **One system.** Every page uses the dashboard's design system (DESIGN.md),
   the same API shape (`{available, data}`), the same loading/empty/error states.
4. **Nightly, not real-time (for now).** One refresh after the close is the unit
   of work. Real-time arrives with the Fyers websocket in v2.
5. **Tests at the seams.** Pure metric/score functions, the screener grammar
   and the API contract each have tests before the page that uses them.

## Architecture (target for v1.0)

```
scripts/daily.sh  ──►  swing.py market refresh  ──►  data/market/market.db (SQLite)
                         │  universe (Nifty 500)         ├─ stocks, metrics (wide), prices,
                         │  yfinance prices (3y)         │  financials, holders, actions,
                         │  yfinance info / statements   │  news, indices, meta
                         │  compute technicals, scores,  └─ user.json (watchlists, holdings)
                         │  checklist, sector medians
                         ▼
src/market/              src/swing/server.py (FastAPI)          apps/swing-dashboard (React)
  universe.py              /api/market/*  ◄────────────────────  /            Markets today
  store.py                 /api/portfolio, /api/signals, …       /screener    Screener
  metrics.py                                                     /stock/:sym  Stock page
  scores.py                                                      /watchlist   Watchlist
  checklist.py                                                   /portfolio   Holdings
  screener.py                                                    /swing/*     Swing engine (existing)
  refresh.py
  api.py
```

- **Universe:** Nifty 500 (NSE constituent CSV, bundled snapshot plus `--refresh`).
- **Store:** one SQLite file; the wide `metrics` table (one row per stock, ~90
  columns) is loaded into memory by the server, so screener queries are pandas
  filters, not SQL.
- **Refresh budget:** prices for 500 symbols in one batch download (~2 min);
  per-ticker fundamentals with 3 worker threads and retry on 429 (~10–15 min).
  `--prices-only` for a quick post-close update.

## Data sources and what each gives us

| Source | Used for | Notes |
|---|---|---|
| Yahoo Finance (`yfinance`) | Daily OHLCV (adjusted), `info` fundamentals, quarterly/annual income statement, balance sheet, cash flow, dividends, splits, earnings calendar, analyst targets, news headlines, insider/institution % held | 15-minute delayed; some small caps have gaps; Indian shareholding pattern (promoter / FII / DII / MF) is **not** available beyond insiders % and institutions % |
| NSE archives | Index constituent lists (Nifty 100, Nifty 500) | Public CSV |
| NSE / BSE filings (v1.1+) | Shareholding pattern, bulk/block deals, SAST, corporate actions, results calendar | Public but rate-limited and format-fragile; each parser ships with a fixture test |
| Fyers API v3 (optional, v2) | Real-time quotes, order placement | Needs an account and daily login |
| Gemini (LLM) | Market review, stock report, "ask about this stock" | Already wired through LiteLLM |

## Legal position

Trendlyne's terms (section 6) prohibit copying its information or loading it
into a machine-readable database. We therefore:

- do not fetch anything from trendlyne.com in code, tests or scripts;
- do not use their trademarked names (DVM, Starfolio, MarketMind, Forecaster);
- name our scores **Quality / Value / Momentum** and publish the formulas;
- credit Yahoo Finance and NSE on the page footer, with the delay notice.

## Status

See [TASKS.md](TASKS.md). v0.1 (swing engine + dashboard) is shipped; v1.0
Phase 1 (data layer) is in progress: the metric and screener tests are
written and failing, the implementation comes next.
