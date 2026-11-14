# India (NSE/BSE) Quickstart

This fork adds India stock support to the daily AI stock analyser. Use it for research and to rank swing-trade candidates (holding for days to weeks). It never places orders. Nothing here is investment advice.

## 1. One-time setup

```bash
cd ~/Desktop/ai-trader
source .venv/bin/activate          # Python 3.11 env (already installed)
```

Open `.env` and fill in **one** AI key:

| Provider | Line in `.env` | Where to get it |
|---|---|---|
| Gemini (has a free tier) | `GEMINI_API_KEY=` | https://aistudio.google.com |
| DeepSeek (very cheap) | uncomment `DEEPSEEK_API_KEY=` | https://platform.deepseek.com |
| OpenAI | uncomment `OPENAI_API_KEY=` | https://platform.openai.com |

Optional but recommended:

- **News:** set `TAVILY_API_KEYS=` (free tier at https://tavily.com). Without a news key, reports use price data only.
- **Telegram alerts:** set `TELEGRAM_BOT_TOKEN=` and `TELEGRAM_CHAT_ID=`. Create the bot with @BotFather in Telegram.

Already set for you:

- `STOCK_LIST`: 10 Nifty stocks across sectors.
- `REPORT_LANGUAGE=en`: reports in English.
- `SCHEDULE_TIME=16:30` IST: after the 15:30 market close.
- `MARKET_REVIEW_ENABLED=false`: the built-in market review only covers China/HK/US/Asia markets, so it's off until an India review is added.

## 2. Ticker format

Every Indian ticker needs a suffix:

- NSE: `RELIANCE.NS`, `TCS.NS`, `M&M.NS`, `BAJAJ-AUTO.NS`, `NIFTYBEES.NS`
- BSE: `RELIANCE.BO`. Numeric BSE codes such as `500325.BO` are recognised but Yahoo has no data for them, so prefer `.NS`.

A bare `RELIANCE` won't be treated as an Indian stock.

## 3. Daily use

```bash
python main.py --dry-run                 # fetch data only, no AI (checks the setup)
python main.py                           # full AI report for STOCK_LIST
python main.py --stocks TATAMOTORS.NS,SUNPHARMA.NS   # one-off list
python main.py --schedule                # stay running; report every trading day at 16:30
python main.py --webui                   # web dashboard at http://127.0.0.1:8000
```

On NSE holidays and weekends the run is skipped automatically (exchange calendar `XBOM`). Add `--force-run` to run anyway.

## 4. Known limits

- Prices come from Yahoo Finance: free, but about 15 minutes delayed and sometimes patchy. A Fyers data source is the planned upgrade.
- The NSE holiday calendar in `exchange-calendars` 4.13 ends on 2026-12-31. Upgrade the package in January, or holidays will be treated as trading days.
- Not yet available for India: market review, FII/DII daily flows, stock-name autocomplete in the web UI, INR portfolio valuation.
