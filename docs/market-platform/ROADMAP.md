# Market Platform — Roadmap

Versions are shipped in order; each version is usable on its own. Phases
inside a version are built in order because each depends on the one before.
Task-level detail lives in [TASKS.md](TASKS.md).

## v0.1 — Foundation (shipped 2026-11-15)

India market support in the analysis engine; the swing engine (Nifty 100
ranking, Indian-cost backtester, paper trading, gated Fyers live execution);
the animated dashboard and its redesign; daily routine; docs.

## v1.0 — Research platform core

Goal: a Trendlyne-shaped site on our own data for the Nifty 500 — markets
today, screener, stock page, watchlist and portfolio — refreshed nightly.

| Phase | Name | Delivers | Exit criteria |
|---|---|---|---|
| 1 | Data layer | `src/market/`: Nifty 500 universe, SQLite store, nightly refresh (prices, fundamentals, statements, actions, news, indices), metric catalogue, Quality/Value/Momentum scores, checklist, sector medians; `swing.py market refresh` | `market refresh` completes for 500 stocks in ≤ 20 min; metric/score/checklist tests green; `market status` prints counts |
| 2 | API | `/api/market/*` endpoints from SPEC §6, screener grammar and presets, CSV export, user store | API contract tests green; p95 < 100 ms locally |
| 3 | Markets today | New home page: index strip, breadth, sector heatmap, movers, regime, upcoming, news | Renders from live DB at 1440 and 390 px; empty state when no refresh yet |
| 4 | Screener | Preset browser, filter builder, result table, URL state, CSV | Every preset opens in < 1 s; filters survive reload; sort works on every column |
| 5 | Stock page | All 12 sections of SPEC §1.3 with real data; price chart; peers | Opens for any Nifty 500 symbol; unknown symbol shows a clear empty state |
| 6 | Watchlist & portfolio | Named watchlists, holdings with valuation, allocation, vs Nifty | Data survives restarts (`user.json`); add/remove from stock page and search |
| 7 | Shell | Router, new navigation, ⌘K search, swing tabs moved under `/swing`, footer with sources and delay notice | No dead links; keyboard path for search and tabs; reduced-motion verified |
| 8 | Release | `daily.sh` runs the refresh; README/quickstart/changelog; screenshot pass; tag `v1.0.0` | All tests green; fresh clone → `npm run build` → `swing.py serve` works from the docs alone |

## v1.1 — Depth

Fill the gaps Yahoo leaves and make the pages comparable with the reference.

| Phase | Name | Delivers |
|---|---|---|
| 1 | NSE filings | Shareholding pattern history (promoter, FII, DII, MF, public), bulk/block deals, SAST and insider trades, corporate-actions and results calendars; each parser with a recorded fixture |
| 2 | Financial statements | Full quarterly/annual income statement, balance sheet, cash flow and ratio pages with charts; revenue mix where disclosed |
| 3 | Technicals | Delivery %, pivot/support/resistance, candlestick patterns, multi-timeframe RSI/MACD; a technicals screener group |
| 4 | Custom screens & alerts | Save/rename/delete screens; relative-to-sector operators; alerts on a screen or a stock evaluated at each refresh and delivered by Telegram/email |
| 5 | Compare | Side-by-side comparison of up to five stocks; peers table export |
| 6 | Portfolio import | Broker CSV import (Zerodha, Groww, Fyers), realised P&L, dividends received, XIRR |

## v1.2 — Intelligence

| Phase | Name | Delivers |
|---|---|---|
| 1 | Stock report | AI-written one-page report per stock from our metrics, financials and news, with every number linked to its source panel |
| 2 | Ask about a stock | Chat over a single stock's data (Gemini via LiteLLM), with the retrieved rows shown beside the answer |
| 3 | Sector pages | One page per sector: constituents, median ratios, rotation chart, leaders and laggards |
| 4 | Results season | Results dashboard: who reported, beats/misses against the prior year, reaction, upcoming |
| 5 | Superstar holdings | Public SAST/large-holder disclosures grouped by investor, with changes quarter on quarter |

## v2.0 — Live and multi-user

| Phase | Name | Delivers |
|---|---|---|
| 1 | Real-time | Fyers websocket quotes on the index strip, watchlist and stock header; intraday chart |
| 2 | Accounts | Login, per-user watchlists/portfolios/alerts, hosted deployment with HTTPS |
| 3 | Mobile | Installable PWA with push alerts |
| 4 | F&O and MF | Options chain and OI dashboard; mutual-fund pages and holdings overlap |
| 5 | Data downloader | Bulk export of any metric or statement history to CSV/Excel |

## Deliberately not planned

- Copying Trendlyne data, names or text (see README, Legal position).
- Automated live trading beyond the existing gated swing executor.
- Paid data feeds, until the free pipeline is exhausted.
