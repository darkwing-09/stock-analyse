# Stock Analyse: AI Swing-Trading Research for Indian Markets

AI-assisted stock research for **NSE and BSE**. Every trading day after the market closes, it pulls fresh prices, technical indicators, fundamentals and news for your watchlist. A large language model (Gemini, OpenAI, DeepSeek, Claude or a local model) then writes a decision report for each stock: **buy / hold / sell, a 0–100 score, entry, stop-loss and target levels**, plus the risks and catalysts behind the call.

The goal is a disciplined, data-driven process for **swing trading** (holding positions for days to weeks). Ideas are generated and ranked by AI, checked against history, and paper-traded before any real money is used.

> ⚠️ **Not investment advice.** This is a research tool. It does not place orders, and no system can guarantee profits. See [Disclaimer](#disclaimer).

---

## Contents

- [What it does](#what-it-does)
- [Swing engine: rank, backtest, paper trade](#swing-engine-rank-backtest-paper-trade)
- [Example output](#example-output)
- [Quick start](#quick-start)
- [Daily usage](#daily-usage)
- [Configuration](#configuration)
- [India support details](#india-support-details)
- [Roadmap](#roadmap)
- [Project structure](#project-structure)
- [Development and testing](#development-and-testing)
- [Credits and license](#credits-and-license)
- [Disclaimer](#disclaimer)

---

## What it does

| Capability | Details |
|---|---|
| **AI decision report** | One-line verdict, score, trend, ideal and secondary entry, stop-loss, target, position-size suggestion, risk alerts, catalysts and a pre-trade checklist |
| **Indian market data** | NSE `.NS` and BSE `.BO` tickers, daily price history, quotes in ₹, fundamentals, and the Nifty 50, Sensex and Nifty Bank indices |
| **Technical analysis** | Moving-average alignment (MA5/10/20), bias from the MA, support and resistance, RSI, volume behaviour, and 15 built-in strategy templates (MA crossover, volume breakout, pullback, wave and others) |
| **India-aware AI context** | Prompts use Indian concepts: INR, RBI policy, SEBI, FII/DII flows, crude oil and the monsoon, promoter holding, T+1 settlement and circuit limits |
| **Trading calendar** | Runs are skipped on NSE/BSE holidays and weekends |
| **Safety guardrails** | Buy and sell calls are rechecked against price structure: a buy near resistance or mid-range is downgraded to "watch", and missing data is flagged in every report |
| **Backtesting** | Replays past AI calls against what the price did next, reporting how often the direction was right and the simulated return (`--backtest`) |
| **Delivery** | Markdown reports in `reports/`, a local web dashboard, and optional Telegram, Discord, Slack or email notifications |
| **Scheduling** | Runs automatically every trading day at a time you choose, e.g. 16:30 IST after the 15:30 close |

---

## Swing engine: rank, backtest, paper trade

`swing.py` is a rules-based engine that scans the **Nifty 100** every evening. It runs alongside the AI reports.

| Command | What it does |
|---|---|
| `python swing.py rank` | Ranks every Nifty 100 stock on strength vs Nifty, trend smoothness, sector strength, proximity to its 52-week high, volume and calmness. Gives each an entry, ATR-based stop and target, keeps those with **at least 2:1 reward-to-risk**, then suggests a portfolio: at most 2 per sector, no two picks that move together (correlation < 0.7), and each position sized to risk 1% of capital |
| `python swing.py backtest --years 10` | Replays the exact same rules day by day with next-open fills, 0.10% slippage, every Fyers delivery charge (brokerage, STT, stamp duty, exchange and SEBI fees, GST, DP charge) and 20% short-term gains tax, compared with buying and holding Nifty |
| `python swing.py paper run` | Paper trading. Run it after each close: it fills yesterday's simulated orders at today's open, manages stops, and queues tomorrow's orders. Catches up on missed days |
| `python swing.py serve` | Animated dashboard at http://127.0.0.1:8600 showing the portfolio, signals, backtest and market review. Build it once with `cd apps/swing-dashboard && npm install && npm run build` |
| `python swing.py live plan / approve / submit / reconcile` | Real orders through Fyers. **Off by default.** See [Live trading safety](#live-trading-safety) |
| `scripts/daily.sh` | The whole evening routine: paper trade, then AI reports on your watchlist plus today's picks. Schedule it for 16:45 IST |

**Honest backtest (Nifty 100, Sep 2016 to Nov 2026, ₹5L start):** CAGR **+12.7%** vs Nifty +11.0%; worst drawdown **−26.8%** vs Nifty −38.4%; 638 trades, 37% win rate, profit factor 1.59; ₹1.89L paid in charges. After the estimated 20% tax it ends roughly level with buy-and-hold. The edge is modest and comes mainly from sitting out downtrends. In a separate study, the hold-out period from May 2025 to Nov 2026 showed no reliable edge. Today's index members are used throughout (survivorship bias), so treat all of this as optimistic.

### Live trading safety

Nothing reaches your broker unless **every** gate passes:

1. `LIVE_TRADING_ENABLED=true` is set in the environment. It is off by default.
2. No kill switch: create `data/swing/KILL_SWITCH` to halt everything instantly.
3. You approved today's exact orders by typing `APPROVE` (`python swing.py live approve`).
4. Daily loss limit (2%): once breached, new buys are blocked. Protective sells always go through.
5. Caps: each order at most 20% of equity, at most 12 orders a day, sent at most 1 per second (far below SEBI's 10/s retail-algo threshold).

Orders are after-market (AMO) CNC orders: limit buys at most 0.5% above the signal close, SL-M protective stops renewed each evening, and market sells for exits. SEBI's 2026 rules require API orders to come from a **static IP registered with Fyers**. Run `python swing.py live reconcile` to compare your real holdings with the strategy.

---

## Example output

```
🎯 2026-11-15 Decision Dashboard
Analyzed 1 stocks | 🟢 Buy: 1  🟡 Watch: 0  🔴 Sell: 0

🟢 RELIANCE INDUSTRIES LTD (RELIANCE.NS): Buy | Score 67 | Bullish

📌 One-line decision: Buy near ₹1,331.84 (MA5 support); price is in a strong
   bullish alignment with low bias (+0.59%).

🎯 Action levels
   Ideal entry      ₹1,331.84  (MA5)
   Secondary entry  ₹1,305.64  (MA10)
   Stop-loss        ₹1,249.58  (below MA20)
   Target           ₹1,400.00  (previous high / resistance)

🚨 Risks:  RSI overbought (74.7); sensitive to crude oil and FII flows
✨ Catalysts:  MA5 > MA10 > MA20 alignment; TTM P/E 22.1 for a market leader
```

---

## Quick start

### Requirements

- Linux, macOS or WSL
- **Python 3.11**. Python 3.14 is not supported yet because some dependencies have no prebuilt packages for it.
- One AI API key. Gemini has a free tier; DeepSeek is very cheap.

### Install

```bash
git clone https://github.com/darkwing-09/stock-analyse.git
cd stock-analyse

# Option A: uv (recommended)
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r requirements.txt

# Option B: plain venv
python3.11 -m venv .venv
.venv/bin/pip install -r requirements.txt

source .venv/bin/activate
cp .env.example .env
```

### Minimal `.env`

```ini
# Your watchlist: always include the exchange suffix
STOCK_LIST=RELIANCE.NS,TCS.NS,HDFCBANK.NS,ICICIBANK.NS,INFY.NS,BHARTIARTL.NS,ITC.NS,LT.NS,SBIN.NS,M&M.NS

# One AI provider is enough
GEMINI_API_KEY=your-key-here
# DEEPSEEK_API_KEY=
# OPENAI_API_KEY=

REPORT_LANGUAGE=en
SCHEDULE_TIME=16:30

# The built-in market review covers China/HK/US/Asia only; an India review is on the roadmap
MARKET_REVIEW_ENABLED=false

# Optional but recommended: news for each stock (free tier at tavily.com)
TAVILY_API_KEYS=
```

### Check the setup

```bash
python main.py --dry-run --force-run   # fetch data only, no AI call
python main.py --force-run             # full AI report
```

`--force-run` skips the trading-day check, which is useful for testing on weekends.

---

## Daily usage

| Command | What it does |
|---|---|
| `python main.py` | Analyse every stock in `STOCK_LIST` and save the report to `reports/` |
| `python main.py --stocks TATAMOTORS.NS,SUNPHARMA.NS` | One-off analysis of specific stocks |
| `python main.py --schedule` | Stay running and analyse automatically every trading day at `SCHEDULE_TIME` |
| `python main.py --webui` | Web dashboard at http://127.0.0.1:8000 (history, reports, settings) |
| `python main.py --backtest` | Score past AI calls against what the price did next |
| `python main.py --no-notify` | Run without sending notifications |
| `python main.py --dry-run` | Fetch and store data without calling the AI |
| `python main.py --debug` | Verbose logging |

A suggested routine for the research phase:

1. After **16:30 IST** each trading day, run `python main.py`, or leave `--schedule` running.
2. Read the reports and record which calls work. Don't trade on them yet.
3. Every week, run `python main.py --backtest` to see the hit rate.

---

## Configuration

All settings live in `.env`. The full annotated list is in [`.env.example`](.env.example). The most useful ones:

| Setting | Purpose |
|---|---|
| `STOCK_LIST` | Comma-separated tickers (`RELIANCE.NS`, `TCS.NS`, ...) |
| `GEMINI_API_KEY` / `DEEPSEEK_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | AI provider. One is enough. See [docs/LLM_CONFIG_GUIDE_EN.md](docs/LLM_CONFIG_GUIDE_EN.md) for model routing |
| `REPORT_LANGUAGE` | `en` for English reports |
| `SCHEDULE_TIME` | Daily run time in local time (e.g. `16:30`) |
| `TAVILY_API_KEYS` / `SERPAPI_API_KEYS` / `BRAVE_API_KEYS` | News search used in the analysis |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` | Send reports to Telegram |
| `DISCORD_WEBHOOK_URL`, `SLACK_BOT_TOKEN`, `EMAIL_SENDER` + `EMAIL_PASSWORD` | Other notification channels |

More detail is in [docs/india-quickstart.md](docs/india-quickstart.md) and [docs/full-guide_EN.md](docs/full-guide_EN.md).

---

## India support details

| Area | Behaviour |
|---|---|
| **Ticker format** | NSE `RELIANCE.NS`, `M&M.NS`, `BAJAJ-AUTO.NS`, `NIFTYBEES.NS`; BSE `RELIANCE.BO`. Bare `RELIANCE` is not treated as an Indian stock. |
| **Data source** | Yahoo Finance: free, about 15 minutes delayed. Numeric BSE codes (`500325.BO`) are recognised, but Yahoo has no data for them, so prefer `.NS`. |
| **Indices** | Nifty 50 (`^NSEI`), Sensex (`^BSESN`), Nifty Bank (`^NSEBANK`) |
| **Calendar** | `XBOM` exchange calendar, `Asia/Kolkata` timezone. The current `exchange-calendars` release covers holidays through 2026-12-31, so upgrade it each January. |
| **Currency** | Amounts labelled in ₹ / INR |
| **Not yet available** | India market review, daily FII/DII flow data, ticker autocomplete in the web UI, INR portfolio valuation |

---

## Roadmap

| Stage | Goal | Status |
|---|---|---|
| **1. India support** | NSE/BSE tickers, data, calendar, India-aware AI prompts | ✅ Done |
| **2. Better data** | India market review (Nifty, Sensex, Bank Nifty, India VIX, sector rotation); [Fyers](https://fyers.in) API data source with daily login | ✅ Done |
| **3. Ranking engine** | Nifty 100 cross-sectional scoring, ATR stops, ≥ 2:1 reward-to-risk filter, sector cap, correlation filter, risk-based sizing | ✅ Done |
| **4. Honest backtesting** | Day-by-day replay with Fyers charges, slippage, gaps and 20% STCG; in-sample vs hold-out split; yearly vs Nifty | ✅ Done |
| **5. Paper trading** | Same rules on real sessions every evening, plus the animated dashboard | ✅ Done, now running |
| **6. Live, small capital** | Fyers AMO orders behind safety gates (off by default). Switch on only after months of paper results | ✅ Built, off |

The stages above are **v0.1**. The next versions turn this into a full research platform (markets today, screener, per-stock pages with Quality/Value/Momentum scores and a buy checklist, watchlists and a portfolio tracker on the Nifty 500). The plan, specification and task list live in [docs/market-platform/](docs/market-platform/README.md): [ROADMAP](docs/market-platform/ROADMAP.md) · [SPEC](docs/market-platform/SPEC.md) · [TASKS](docs/market-platform/TASKS.md).

---

## Project structure

```
main.py                 CLI entry point (analysis, schedule, web UI, backtest)
server.py               FastAPI server entry
data_provider/          Market data adapters (Yahoo Finance and others) with fallback routing
src/
  analyzer.py           LLM analysis, report parsing and decision guardrails
  market_context.py     Market-specific AI prompt context (incl. India)
  core/                 Pipeline orchestration, trading calendar, backtest engine
  services/             Business logic: signals, portfolio, alerts, history
  agent/                Multi-turn "ask about a stock" agent and strategies
src/swing/              Swing engine: ranking, costs, backtest, paper trading, live gates, dashboard API
swing.py                Swing engine CLI
apps/swing-dashboard/   Animated dashboard (React, Tailwind, Framer Motion)
strategies/             Built-in strategy templates (YAML)
api/                    REST API (FastAPI)
apps/dsa-web/           Web dashboard (React)
docs/                   Guides (india-quickstart.md, full-guide_EN.md, ...)
tests/                  pytest suite
```

---

## Development and testing

```bash
source .venv/bin/activate

# Offline test suite (about 8,600 tests, about 10–13 minutes)
python -m pytest -m "not network"

# India + swing engine tests only
python -m pytest tests/test_in_market_*.py tests/test_swing_*.py tests/test_fyers_fetcher.py

# Live data smoke test (needs internet)
python -m pytest -m network tests/test_in_market_network.py
```

Move `.env` aside before running the full suite. A few upstream tests read local settings such as `REPORT_LANGUAGE` and fail when it is set to `en`.

---

## Credits and license

Built on the MIT-licensed [daily_stock_analysis](https://github.com/ZhuLinsen/daily_stock_analysis) project, extended here for Indian markets and a swing-trading workflow. Released under the [MIT License](LICENSE). Third-party notices are in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

---

## Disclaimer

This project is for research and educational purposes only. AI-generated analysis can be wrong, outdated or incomplete, and past performance does not predict future results. It is **not investment advice** and not a recommendation to buy or sell any security. Trading involves the risk of losing money. Do your own research, and consult a SEBI-registered investment adviser before making investment decisions. The authors accept no liability for any losses.
