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

## v1.5 — Real-time feed (est. 30 h; needs a Fyers account)

| ID | Task | Acceptance | Est | Status |
|---|---|---|---|---|
| v15-P1-T01 | `src/feed/fyers_ws.py`: websocket client, reconnect with backoff, daily token refresh hook | Survives a forced disconnect; logs gaps | 3 | [ ] |
| v15-P1-T02 | Subscription manager: watchlist ∪ scanner shortlist ∪ open positions, ≤ 200 symbols/socket, multiple sockets | Set changes apply without reconnect | 2 | [ ] |
| v15-P1-T03 | Tick normaliser + Parquet recorder (one file per symbol-day) | A recorded session replays bit-identical | 2 | [ ] |
| v15-P2-T01 | Bar builder (1 s, 1 m), VWAP, session high/low/open, volume profile basics | Matches broker 1-m candles within 1 tick on a recorded day | 3 | [ ] |
| v15-P2-T02 | DuckDB store over Parquet; query helpers; retention | Range queries < 50 ms | 2 | [ ] |
| v15-P2-T03 | Minute-bar backfill from Fyers history (100 days/call), resumable, nightly | 2 years for Nifty 500 within a week of nights | 3 | [ ] |
| v15-P3-T01 | SSE endpoints for quotes and bars; last-value cache; heartbeat | 50 tabs on localhost without lag | 3 | [ ] |
| v15-P4-T01 | Ticking numbers (index strip, watchlist, stock header) with reduced-motion path | No flashing; colour only on icons | 2 | [ ] |
| v15-P4-T02 | Live candle chart (1 m / 5 m), VWAP, volume, session clock | Renders at 390 px | 4 | [ ] |
| v15-P5-T01 | Replay engine (1×/10×/max) feeding the same pipeline; CLI `swing.py replay <day>` | Used by tests | 3 | [ ] |
| v15-P5-T02 | Docs, tests with a recorded fixture day, tag `v1.5.0` | Fresh clone replays the fixture | 3 | [ ] |

## v2.0 — Agents (est. 60 h)

| ID | Task | Acceptance | Est | Status |
|---|---|---|---|---|
| v2-P1-T01 | Event schema (pydantic), asyncio bus, topic routing, backpressure | Property test: every event delivered once, in order per symbol | 3 | [ ] |
| v2-P1-T02 | Decision ledger store (SQLite, Postgres-ready), indices by symbol/time/agent, parent links | Query the chain for one hypothesis in one call | 3 | [ ] |
| v2-P2-T01 | Scanner agent: quick features on 1-m bars, ranking, one-line reasons | Nifty 500 cycle < 1 s | 4 | [ ] |
| v2-P2-T02 | Scanner page: live ranked table, sparklines, filters by setup/horizon | Updates without re-render jank | 3 | [ ] |
| v2-P3-T01 | Feature engine for a symbol (multi-timeframe) with point-in-time guarantees | Leakage test green | 4 | [ ] |
| v2-P3-T02 | Pattern similarity: window normalisation, index (sklearn/FAISS), neighbour outcomes | Query < 50 ms over 2 years of minute windows | 4 | [ ] |
| v2-P3-T03 | Setup classifier (breakout, pullback, opening range, mean reversion, trend) with drawn levels | Each setup has a fixture day where it fires | 3 | [ ] |
| v2-P3-T04 | Hypothesis records (direction, expected move, probability, stop, target, validity) | Schema matches AGENTS.md §3.2 | 2 | [ ] |
| v2-P3-T05 | Verification job and calibration chart per setup/horizon | Brier score reported | 3 | [ ] |
| v2-P4-T01 | Risk agent: sizing, sector/correlation caps, daily loss, orders/minute, kill switch, market hours | Every veto carries a reason code | 4 | [ ] |
| v2-P4-T02 | Execution agent, paper mode: fills from live quotes with slippage model, partial fills, cancels | Replayed day → traceable paper P&L | 4 | [ ] |
| v2-P4-T03 | Agents page: heartbeats, queues, last decisions, limits, kill switch | Operable from the browser | 3 | [ ] |
| v2-P5-T01 | Report agent: assembled verdict + LLM summary with per-sentence sources | < 5 s; citations resolve | 4 | [ ] |
| v2-P6-T01 | Stock page live: hypothesis on chart, analogue overlay, decision timeline (SSE) | Chain visible end to end | 5 | [ ] |
| v2-P6-T02 | Portfolio live P&L and open risk | Matches ledger fills | 2 | [ ] |
| v2-P7-T01 | Agent backtest over recorded history with costs; scorecards per agent/horizon/setup | Published in the dashboard | 5 | [ ] |
| v2-P7-T02 | Docs, fixtures, tag `v2.0.0` | — | 4 | [ ] |

## v2.5 — Learning (est. 30 h)

| ID | Task | Acceptance | Est | Status |
|---|---|---|---|---|
| v25-P1-T01 | Point-in-time feature store (Parquet), leakage tests | Any past timestamp reproducible | 5 | [ ] |
| v25-P2-T01 | Walk-forward LightGBM per horizon; calibration; registry | Three OOS folds reported | 8 | [ ] |
| v25-P2-T02 | Feature importance and model version written to each hypothesis | Visible on the stock page | 2 | [ ] |
| v25-P3-T01 | Shadow mode (model proposes, baseline trades) and promotion rule | Promotion decision in ledger | 4 | [ ] |
| v25-P4-T01 | Live small capital: Execution → Fyers on the earned horizon, daily approval, static IP, order tags | Months of paper record; approvals logged | 6 | [ ] |
| v25-P4-T02 | Docs, tag `v2.5.0` | — | 2 | [ ] |

## v3.0 — Production (est. 50 h)

| ID | Task | Est | Status |
|---|---|---|---|
| v3-P1-T01 | Docker Compose (api, ingest, agents, redis, duckdb/timescale, postgres, nginx TLS); Redis Streams bus adapter | 8 | [ ] |
| v3-P2-T01 | Prometheus metrics, Grafana dashboards, Alertmanager → Telegram, structured logs | 6 | [ ] |
| v3-P3-T01 | Accounts, per-user data, sessions; vendor/broker agreements checklist | 10 | [ ] |
| v3-P4-T01 | US feed (Alpaca/Polygon), currency handling, cross-market pages | 8 | [ ] |
| v3-P5-T01 | PWA, push alerts | 6 | [ ] |
| v3-P6-T01 | Research depth: NSE filings parsers, statement pages, saved screens + alerts, compare, broker CSV import, F&O, MF | 12 | [ ] |
