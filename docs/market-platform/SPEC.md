# Market Platform — Specification (v1.0)

This is the contract the v1.0 tasks implement. Later versions extend it; they
do not silently change it. Field names here are the field names in code, the
API and the dashboard.

## 1. Pages

### 1.1 Markets today — `/`

Answer in one screen: *what did the market do, where is the money moving, what
stands out today?*

| Section | Content | Source |
|---|---|---|
| Index strip | Nifty 50, Sensex, Nifty Bank, India VIX, Nifty Midcap 100, Nifty Smallcap 100: last, change, % change, 1-year sparkline | `indices` table |
| Breadth | Advances / declines / unchanged across Nifty 500; % above 50-day and 200-day averages; new 52-week highs vs lows | `metrics` |
| Sector heatmap | One tile per sector (NSE macro industry): median 1-day change, 1-week and 1-month change, stock count; click → screener filtered to the sector | `metrics` |
| Movers | Top gainers, top losers, volume shockers (volume ≥ 3× 20-day average), new 52-week highs, new 52-week lows — each a 10-row list with "View all in screener" | `metrics` |
| Market regime | Nifty vs its 200-day average, India VIX level, breadth trend, in one sentence | `indices` + `metrics` |
| Market review | The AI market review (existing) | `reports/` |
| Upcoming | Earnings dates in the next 14 days; ex-dividend dates | `meta` (calendar) |
| News | Latest 20 headlines across the universe, with symbol chip | `news` |

### 1.2 Screener — `/screener` and `/screener/:preset`

- Left: preset groups (Momentum, Value, Quality, Technical, Shareholding,
  Analyst, Red flags) with stock counts.
- Top: active filter chips, add-filter control (metric, operator, value),
  universe size, sort.
- Table: symbol, name, sector, price, 1-day %, market cap, the three scores,
  and the metrics used by the active filters; sortable; click → stock page.
- URL carries the filters (`?f=pe:lt:20&f=roe:gte:0.15&sort=momentum_score`).
- Export: CSV download of the current result.

### 1.3 Stock page — `/stock/:symbol`

Sections in order (each is a panel; the first three sit in the first viewport):

1. **Header:** name, NSE symbol, sector › industry, price, change, 52-week
   range bar, volume vs average, "data to" date, watchlist and portfolio
   buttons, "Ask AI" (v1.2).
2. **Scores:** Quality, Value, Momentum (0–100 gauges with the percentile
   breakdown on hover/expand) and the overall label.
3. **Checklist:** "Check before you buy": ~18 pass/fail rules grouped into
   Financial health, Growth, Valuation, Technicals, Ownership, Street view;
   pass count and percentage.
4. **Price:** 1y / 3y chart with SMA 50/200 and volume; returns table (1d, 1w,
   1m, 3m, 6m, 1y, 3y) against Nifty 50 and the sector.
5. **Key ratios:** market cap, PE, forward PE, PB, EV/EBITDA, PEG, ROE, ROCE,
   debt/equity, dividend yield, beta, free-cash-flow yield, each with the
   sector median beside it.
6. **Financials:** quarterly (last 8) and annual (last 5) revenue, operating
   profit, margin, net profit, EPS; balance-sheet summary; cash-flow summary;
   bar charts for revenue and profit.
7. **Technicals:** SMA/EMA 5–200 signals, RSI, MACD, ATR, pivot points,
   support/resistance from recent highs/lows, delivery (v1.1).
8. **Ownership:** insiders (promoter) %, institutions %, analyst count; full
   shareholding pattern history (v1.1).
9. **Peers:** same industry, by market cap: price, 1y return, PE, ROE, scores.
10. **Corporate actions:** dividends (ex-date, amount, yield), splits/bonus;
    next earnings date.
11. **News:** latest headlines for the symbol.
12. **About:** business summary, website, employees.

### 1.4 Watchlist — `/watchlist`

Multiple named lists; add from any stock page or the search box; table with
price, change, scores, distance from 52-week high, next earnings; reorder;
notes per stock (v1.1); alerts (v1.1).

### 1.5 Portfolio — `/portfolio`

Holdings entered by hand (symbol, quantity, average price, date) or imported
from a broker CSV (v1.1). Shows current value, invested, unrealised P&L
(absolute and %), day change, allocation by sector and by stock, portfolio vs
Nifty since the earliest purchase, realised P&L on sells, and the same
checklist/score view per holding. This is separate from the swing engine's
paper portfolio, which stays under `/swing`.

### 1.6 Swing engine — `/swing/*`

The existing four tabs move under `/swing/portfolio`, `/swing/signals`,
`/swing/backtest`, `/swing/market`; nothing else changes.

### 1.7 Search

A search box in the top bar (⌘K) that matches symbol and company name across
the universe, with recent searches; Enter opens the stock page.

## 2. Data model (SQLite, `data/market/market.db`)

| Table | Key | Columns |
|---|---|---|
| `stocks` | symbol | name, industry, sector, isin, website, summary, employees, updated_at |
| `metrics` | symbol | the full metric catalogue (§3) as a wide table, replaced on every refresh |
| `prices` | symbol, date | open, high, low, close, volume (adjusted), 3 years |
| `financials` | symbol, period_type, period_end, item | value; period_type ∈ {quarterly, annual}; item is the Yahoo line name |
| `actions` | symbol, date, kind | value; kind ∈ {dividend, split} |
| `news` | id | symbol, title, publisher, url, published_at |
| `indices` | code, date | close; plus a `latest` view with change fields |
| `meta` | key | value (JSON): last_refresh, universe, counts, earnings calendar, sector medians |

`data/market/user.json`: `{ "watchlists": {name: [symbol]}, "holdings": [{symbol, qty, avg_price, bought_on, note}], "sells": [...] }`.

## 3. Metric catalogue (`metrics` columns)

Identity: `symbol, name, sector, industry, market_cap, cap_bucket` (large ≥ ₹20,000 cr, mid ≥ ₹5,000 cr, else small).

Price and returns: `price, change_1d_pct, ret_1w, ret_1m, ret_3m, ret_6m, ret_1y, ret_3y, high_52w, low_52w, pct_from_52w_high, pct_from_52w_low, bench_ret_1m, bench_ret_3m, bench_ret_1y, rs_1m, rs_3m, rs_6m` (relative strength = stock return − Nifty return).

Trend and technicals: `sma20, sma50, sma200, ema20, ema50, above_sma20, above_sma50, above_sma200, golden_cross` (SMA50 > SMA200), `rsi14, macd_hist, atr14_pct, volatility_1y, beta_1y, avg_volume_20, volume_ratio` (today / 20-day average), `new_52w_high, new_52w_low, max_drawdown_1y`.

Fundamentals (from Yahoo `info`, units normalised to ratios): `pe, forward_pe, pb, ev_ebitda, peg, roe, roa, operating_margin, profit_margin, revenue_growth, earnings_growth, debt_to_equity, current_ratio, dividend_yield, fcf, fcf_positive, fcf_yield, book_value, eps_ttm, eps_forward, total_cash, total_debt`.

Ownership and street: `promoter_holding` (insiders % held), `institutional_holding, analyst_count, analyst_rating, target_price, analyst_upside, next_earnings`.

Scores and labels: `quality_score, value_score, momentum_score, overall` (Strong / Mixed / Weak), `checklist_passed, checklist_total`.

## 4. Scores

All three are percentile ranks (0–100) within the universe, computed each
refresh, with missing inputs ignored (a stock is ranked on what is known;
fewer than two known inputs → score left blank).

- **Quality** = mean percentile of: `roe` ↑, `operating_margin` ↑,
  `debt_to_equity` ↓, `fcf_positive` ↑, `earnings_growth` ↑, `revenue_growth` ↑.
- **Value** = mean percentile of: `pe` ↓ (within sector), `pb` ↓ (within
  sector), `ev_ebitda` ↓, `dividend_yield` ↑, `peg` ↓.
- **Momentum** = mean percentile of: `ret_6m` ↑, `ret_3m` ↑, `rs_3m` ↑,
  `pct_from_52w_high` ↑ (closer is better), `above_sma200` ↑, `rsi14` (distance
  from 50, penalising < 40 and > 75).
- **Overall:** Strong if two or more scores ≥ 60 and none < 35; Weak if two or
  more < 40; otherwise Mixed.

## 5. Checklist ("Check before you buy")

| id | Group | Rule |
|---|---|---|
| roe | Financial health | ROE ≥ 15% |
| debt | Financial health | Debt/equity ≤ 1 |
| fcf | Financial health | Free cash flow positive |
| margin | Financial health | Operating margin ≥ 10% |
| revenue_growth | Growth | Revenue growth ≥ 10% |
| earnings_growth | Growth | Earnings growth ≥ 10% |
| pe_vs_sector | Valuation | PE below sector median |
| peg | Valuation | PEG ≤ 1.5 |
| pb | Valuation | PB ≤ 5 |
| above_200 | Technicals | Price above 200-day average |
| above_50 | Technicals | Price above 50-day average |
| rsi | Technicals | RSI between 35 and 70 |
| near_high | Technicals | Within 20% of 52-week high |
| beats_nifty | Technicals | 1-year return above Nifty 50 |
| promoter | Ownership | Promoter/insider holding ≥ 40% |
| institutions | Ownership | Institutional holding ≥ 15% |
| dividend | Ownership | Pays a dividend |
| beta | Risk | Beta ≤ 1.2 |
| analyst | Street view | Consensus buy or strong buy |

Each item returns `{id, group, label, passed (true/false/null when unknown), detail}`.

## 6. API

All endpoints return `{ "available": bool, "data": ... }` like the existing ones.

| Method, path | Returns |
|---|---|
| `GET /api/market/today` | indices, breadth, sectors, movers, regime, upcoming, news |
| `GET /api/market/search?q=` | up to 10 `{symbol, name, sector}` |
| `GET /api/market/metrics` | the metric catalogue (labels, kinds, groups) for the filter builder |
| `GET /api/market/screens` | presets with live counts |
| `GET /api/market/screener?f=&sort=&dir=&limit=&offset=` | `{total, rows}` |
| `GET /api/market/screener.csv?…` | same, as CSV |
| `GET /api/market/stock/{symbol}` | everything the stock page needs except prices |
| `GET /api/market/stock/{symbol}/prices?range=1y\|3y` | OHLCV + SMA50/200 |
| `GET /api/market/user` | watchlists and holdings with live valuation |
| `PUT /api/market/user/watchlists` | replace watchlists |
| `PUT /api/market/user/holdings` | replace holdings |
| `GET /api/market/status` | last refresh time, universe, counts, data delay notice |

## 7. Screener grammar

`metric:op:value`, repeated with `f=`; all filters are ANDed.

- Numeric ops: `lt, lte, gt, gte, eq`; value is a number (ratios as decimals: 15% → 0.15).
- Text ops: `eq, in` (comma list); for `sector, industry, cap_bucket, analyst_rating, overall`.
- Boolean op: `is` with `true|false`; for flags (`above_sma200`, `golden_cross`, `fcf_positive`, `new_52w_high`, …).
- Relative ops (v1.1): `gt_sector, lt_sector` compare against the sector median.
- Blank values never match.

Presets (v1.0): momentum-leaders, near-52w-high, golden-cross, oversold,
volume-shockers, quality-compounders, value-picks, dividend-payers,
analyst-favourites, smallcap-breakouts, red-flags, strong-overall.

## 8. Non-functional

- Refresh ≤ 20 minutes for Nifty 500 on a home connection; resumable; partial
  failures logged per symbol, never fatal.
- API p95 < 100 ms for screener and stock page from the in-memory frame.
- Dashboard: first paint < 1 s on localhost; every page works at 390 px.
- Tests: metrics, scores, checklist, screener grammar, API contract, refresh
  against recorded fixtures (no network in tests).
