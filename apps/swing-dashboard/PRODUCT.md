# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

One person: a self-directed Indian retail investor who runs the Stock Analyse
swing engine on their own machine. They open the dashboard in the evening after
the NSE close (15:30 IST), after `scripts/daily.sh` or `python swing.py paper run`
has updated the paper portfolio, and occasionally during the day to check a
position. They are the only viewer; there are no roles, accounts or sharing.

## Product Purpose

The dashboard is the read-only window onto the swing-trading engine: what the
simulated ₹5,00,000 portfolio holds and has earned, which Nifty 100 stocks rank
as swing candidates today and why, how the strategy performed in the backtest
(after every Indian charge and tax) against simply holding Nifty 50, and the
AI-written India market review. Success is a user who can answer "how am I
doing, what fills tomorrow, and should I trust this" in under a minute, and who
keeps paper trading for months before risking real money.

## Positioning

A personal quant desk for Indian swing trading that shows its working: every
pick comes with the percentile scores behind it, every backtest number includes
Fyers delivery charges, slippage and short-term capital-gains tax, and the
strategy is always shown beside the Nifty 50 benchmark over the same period.
Honesty about the edge (or its absence) is the product, not a disclaimer.

## Operating Context

- Served locally by `python swing.py serve` (FastAPI) at `http://127.0.0.1:8600`;
  reads JSON written by the engine under `data/swing/` and Markdown reports under
  `reports/`. The page never places orders; live trading is a separate, gated CLI.
- Data refreshes only when the user runs a command, so "data to <date>" matters.
- Four sections: Portfolio, Signals, Backtest, Market.
- Indian conventions: INR with lakh/crore grouping (en-IN), NSE tickers without
  the `.NS` suffix, trading days Monday to Friday, numbers in tabular figures.

## Capabilities and Constraints

- Stack: Vite + React 18 + TypeScript, Tailwind 3, framer-motion 11, recharts 2,
  react-markdown, lucide-react. Built to `dist/` and served as static files.
- No authentication, no backend writes, no websocket; plain fetch of
  `/api/portfolio`, `/api/signals`, `/api/backtest`, `/api/market`.
- Every section has loading, empty (with the exact command to run) and
  server-unreachable states, because the data files may not exist yet.
- Must work on a laptop and a phone (the user may glance at it on mobile).
- Dark interface: used at night on a personal machine.
- Terminology: "paper portfolio", "candidates", "setup" (breakout or trend),
  "stop", "target", "R" (risk multiple), "risk-on / risk-off" (Nifty 50 above or
  below its 200-day average), "trailing stop", "open risk".

## Brand Commitments

- Name: Stock Analyse. Repository: github.com/darkwing-09/stock-analyse.
- Binding visual references given by the user (2026-11-15): the component and
  motion language of https://ui.aceternity.com, https://skiper-ui.com and
  https://animmasterlib.dev; the user asked for "sleek and decent", animated,
  with colours taken from those palettes. The previous navy-and-amber look was
  rejected outright.
- Every frontend in this project is motion-rich and respects
  `prefers-reduced-motion`.

## Evidence on Hand

- Real data: `data/swing/paper_status.json`, `latest_rank.json`, `backtest.json`
  and `reports/market_review_*.md`, produced by the engine from Yahoo Finance
  prices. Backtest numbers are survivorship-biased (today's Nifty 100 members
  over the whole period); the out-of-sample window showed no reliable edge.
- No testimonials, logos, customer names or screenshots exist and none may be
  invented.

## Product Principles

1. Honest first: benchmark and caveats sit next to every headline number.
2. One-minute answer: holdings, tomorrow's fills and the regime are visible
   without scrolling on a laptop.
3. Show the working: every score and every trade can be expanded to its parts.
4. Read-only and calm: nothing on the page can move money, and the interface
   never pretends otherwise.
5. Motion explains state and continuity; it never delays the task.

## Accessibility & Inclusion

Keyboard-operable tables and tabs, visible focus, 4.5:1 body-text contrast on
the dark surface, status never conveyed by colour alone (icon plus label), and a
reduced-motion path for every animation.
