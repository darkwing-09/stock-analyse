# Market Platform — Task Breakdown

Status: `[ ]` not started · `[~]` in progress · `[x]` done · `[-]` dropped.
IDs are `v<version>-P<phase>-T<nn>`. Estimates are focused working hours.
Update this file in the same commit as the work.

## v0.1 — Foundation — [x] shipped 2026-11-15

- [x] India market detection, data routing, XBOM calendar, prompt context
- [x] India market review and FyersFetcher
- [x] Swing engine: ranking, costs, backtester, paper trading, live gates
- [x] Dashboard (four tabs) and its redesign on the Aceternity/Skiper world
- [x] Daily routine, README, quickstart, changelog

## v1.0 — Research platform core

### Phase 1 — Data layer (est. 14 h)

| ID | Task | Acceptance | Depends | Est | Status |
|---|---|---|---|---|---|
| v1-P1-T01 | Bundle Nifty 500 constituents and register `nifty500` universe (`load_universe`, `--refresh` from NSE) | `load_universe("nifty500")` returns 500 stocks with sector mapping; `swing.py universe --name nifty500` lists them | — | 0.5 | [x] CSV bundled; loader pending |
| v1-P1-T02 | Write failing tests for metrics, scores, checklist (`tests/test_market_metrics.py`) | Tests collect and fail on missing module | — | 1 | [x] |
| v1-P1-T03 | Write failing tests for screener grammar and presets (`tests/test_market_screener.py`) | Same | — | 0.5 | [x] |
| v1-P1-T04 | `src/market/metrics.py`: `compute_technicals(panel)` (returns, 52w range, SMAs/EMAs, RSI, MACD, ATR, beta, volume ratio, relative strength, flags) | T02 technical assertions green on the synthetic panel | T02 | 2 | [ ] |
| v1-P1-T05 | `fundamentals_frame(info_by_symbol)` with unit normalisation (Yahoo percents → ratios) | T02 fundamentals assertions green | T02 | 1 | [ ] |
| v1-P1-T06 | `score_universe(frame)`: Quality / Value / Momentum percentiles and overall label (SPEC §4) | T02 score assertions green, NaN-tolerant | T04, T05 | 1.5 | [ ] |
| v1-P1-T07 | `checklist(row, sector_medians)` (SPEC §5) | T02 checklist assertions green | T05 | 1 | [ ] |
| v1-P1-T08 | `src/market/screener.py`: `METRICS` catalogue, `parse_filters`, `run_screen`, `PRESETS` (SPEC §7) | T03 green | T04–T06 | 1.5 | [ ] |
| v1-P1-T09 | `src/market/store.py`: SQLite schema, `save_frame/load_frame`, upserts, `meta` | Round-trip test on a temp DB | — | 1 | [ ] |
| v1-P1-T10 | `src/market/refresh.py`: batch price download (3y), per-ticker fetch with 3 threads + retry/backoff, statements, actions, news, calendar, indices; computes metrics, sector medians, checklist counts; `--prices-only` | Dry run on 10 symbols writes every table; failures logged per symbol; full Nifty 500 run ≤ 20 min | T04–T09 | 3 | [ ] |
| v1-P1-T11 | CLI: `swing.py market refresh [--universe] [--prices-only] [--symbols]`, `market status` | Commands documented in `--help`; status prints last refresh, counts, oldest price date | T10 | 0.5 | [ ] |
| v1-P1-T12 | Refresh fixture test: recorded yfinance responses for 3 symbols → full pipeline offline | Test green without network | T10 | 1 | [ ] |

### Phase 2 — API (est. 6 h)

| ID | Task | Acceptance | Depends | Est | Status |
|---|---|---|---|---|---|
| v1-P2-T01 | `src/market/api.py` router mounted in `create_app()`; in-memory metrics frame with reload on DB change | `/api/market/status` answers; frame reloads after a refresh without restart | P1 | 1 | [ ] |
| v1-P2-T02 | `/api/market/today` (SPEC §1.1 data) | Contract test with fixture DB | T01 | 1 | [ ] |
| v1-P2-T03 | `/api/market/search`, `/api/market/metrics`, `/api/market/screens`, `/api/market/screener` (+ `.csv`) | Contract tests; bad filter → 400 with message | T01 | 1.5 | [ ] |
| v1-P2-T04 | `/api/market/stock/{symbol}` and `/prices` | Contract test; unknown symbol → `available:false` | T01 | 1.5 | [ ] |
| v1-P2-T05 | User store (`user.json`) and `/api/market/user*` with live valuation | Round-trip test; invalid holding → 422 | T01 | 1 | [ ] |

### Phase 3 — Markets today (est. 6 h)

| ID | Task | Acceptance | Depends | Est | Status |
|---|---|---|---|---|---|
| v1-P3-T01 | Index strip with sparklines and regime sentence | Matches DESIGN.md; sparkline palette validated | P2-T02 | 1.5 | [ ] |
| v1-P3-T02 | Breadth panel and sector heatmap (click → screener) | Heatmap colours from the validated diverging pair | P2-T02 | 1.5 | [ ] |
| v1-P3-T03 | Movers lists (gainers, losers, volume shockers, 52w highs/lows) | Each list links to its preset | P2-T02 | 1 | [ ] |
| v1-P3-T04 | Upcoming events and news feed | Dates in IST; symbol chips link to stock page | P2-T02 | 1 | [ ] |
| v1-P3-T05 | Empty / loading / error states; mobile layout; screenshots | 1440 and 390 captures reviewed | T01–T04 | 1 | [ ] |

### Phase 4 — Screener (est. 7 h)

| ID | Task | Acceptance | Depends | Est | Status |
|---|---|---|---|---|---|
| v1-P4-T01 | Preset browser with groups and live counts | Counts match API | P2-T03 | 1 | [ ] |
| v1-P4-T02 | Filter builder (metric picker grouped by catalogue, operator, value with unit hints), filter chips | Invalid input explained inline | P2-T03 | 2 | [ ] |
| v1-P4-T03 | Result table: dynamic columns, sorting, pagination, row → stock page | Sort on every column; 500 rows paginate | P2-T03 | 1.5 | [ ] |
| v1-P4-T04 | URL state (`?f=…&sort=…`) and share link; CSV export button | Reload reproduces the screen | T02, T03 | 1 | [ ] |
| v1-P4-T05 | States, mobile layout (filters collapse into a sheet), screenshots | Captures reviewed | T01–T04 | 1.5 | [ ] |

### Phase 5 — Stock page (est. 10 h)

| ID | Task | Acceptance | Depends | Est | Status |
|---|---|---|---|---|---|
| v1-P5-T01 | Route `/stock/:symbol`, header, 52-week range bar, watchlist/portfolio buttons | Works for every universe symbol | P2-T04 | 1.5 | [ ] |
| v1-P5-T02 | Score gauges with percentile breakdown; overall label | Gauges animate once; reduced-motion static | P2-T04 | 1.5 | [ ] |
| v1-P5-T03 | Checklist panel grouped, with pass count | Unknown rules shown as "not enough data", not failed | P2-T04 | 1 | [ ] |
| v1-P5-T04 | Price chart (1y/3y, SMA 50/200, volume) and returns-vs-benchmark table | Tooltip crosshair; palette validated | P2-T04 | 1.5 | [ ] |
| v1-P5-T05 | Key ratios with sector medians; financials tables and bars | Quarterly 8, annual 5; blanks as blanks | P2-T04 | 1.5 | [ ] |
| v1-P5-T06 | Technicals, ownership, peers, corporate actions, news, about panels | All sections render or show their own empty note | P2-T04 | 2 | [ ] |
| v1-P5-T07 | Mobile layout, in-page section nav, screenshots | Captures reviewed | T01–T06 | 1 | [ ] |

### Phase 6 — Watchlist & portfolio (est. 6 h)

| ID | Task | Acceptance | Depends | Est | Status |
|---|---|---|---|---|---|
| v1-P6-T01 | Watchlist page: multiple lists, add/remove/reorder, table with live metrics | Survives restart | P2-T05 | 2 | [ ] |
| v1-P6-T02 | Add-to-watchlist from stock page and search | One click; toast confirms | T01 | 0.5 | [ ] |
| v1-P6-T03 | Portfolio page: holdings form, valuation, P&L, day change | Hand-checked arithmetic test | P2-T05 | 2 | [ ] |
| v1-P6-T04 | Allocation (sector, stock) and portfolio-vs-Nifty chart | Palette validated | T03 | 1 | [ ] |
| v1-P6-T05 | States, mobile, screenshots | Captures reviewed | T01–T04 | 0.5 | [ ] |

### Phase 7 — Shell (est. 4 h)

| ID | Task | Acceptance | Depends | Est | Status |
|---|---|---|---|---|---|
| v1-P7-T01 | `react-router-dom`, routes, swing tabs under `/swing/*`, redirects from old hashes | Old `#portfolio` links still land | P3–P6 | 1 | [ ] |
| v1-P7-T02 | New navigation (Markets, Screener, Watchlist, Portfolio, Swing) with the spring pill; mobile menu | Keyboard operable | T01 | 1 | [ ] |
| v1-P7-T03 | ⌘K search with results and recents | Enter opens stock page; Esc closes | P2-T03 | 1.5 | [ ] |
| v1-P7-T04 | Footer: sources, data delay notice, last refresh | Present on every page | P2-T01 | 0.5 | [ ] |

### Phase 8 — Release (est. 4 h)

| ID | Task | Acceptance | Depends | Est | Status |
|---|---|---|---|---|---|
| v1-P8-T01 | `scripts/daily.sh` runs `market refresh` before the swing steps; cron line in docs | Runs end to end on a weekday evening | P1-T11 | 0.5 | [ ] |
| v1-P8-T02 | README, quickstart, CHANGELOG, this folder updated; DESIGN.md additions for new components | Fresh-clone walkthrough works | all | 1.5 | [ ] |
| v1-P8-T03 | Full test suite, impeccable detector, Playwright capture pass at 1440/390 for every route | No console errors; no overflow | all | 1.5 | [ ] |
| v1-P8-T04 | Tag `v1.0.0`, push | Tag on GitHub | all | 0.5 | [ ] |

## v1.1 — Depth (outline; detailed when v1.0 ships)

- P1 NSE filings: shareholding history, bulk/block deals, SAST/insider, actions and results calendars (fixture-tested parsers)
- P2 Statement pages and ratio history with charts
- P3 Technicals: delivery, pivots, candlestick patterns, multi-timeframe oscillators, technical screener group
- P4 Saved custom screens, sector-relative operators, alerts via Telegram/email
- P5 Compare up to five stocks
- P6 Broker CSV import, realised P&L, dividends, XIRR

## v1.2 — Intelligence (outline)

- P1 AI stock report · P2 Ask about a stock · P3 Sector pages · P4 Results season · P5 Superstar holdings

## v2.0 — Live and multi-user (outline)

- P1 Fyers websocket real-time · P2 Accounts and hosting · P3 PWA with push · P4 F&O and MF · P5 Data downloader
