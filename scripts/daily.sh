#!/usr/bin/env bash
# Daily after-close routine (schedule for ~16:45 IST, Mon-Fri):
#   1. paper trader: fill today's simulated orders, rank the Nifty 100, queue tomorrow's orders
#   2. AI reports: India market review + deep-dive on your watchlist and today's suggested picks
# Holidays are skipped automatically (NSE calendar). Logs: data/swing/daily.log
set -euo pipefail
cd "$(dirname "$0")/.."
# shellcheck disable=SC1091
source .venv/bin/activate

echo "=== $(date '+%F %T') daily run ==="
python swing.py paper run

PICKS=$(python - <<'PY'
import json
try:
    data = json.load(open("data/swing/latest_rank.json"))
    print(",".join(p["symbol"] for p in data.get("portfolio", [])))
except Exception:
    print("")
PY
)
WATCH=$(grep -E '^STOCK_LIST=' .env | cut -d= -f2- || true)
STOCKS=$(printf '%s,%s' "$WATCH" "$PICKS" | tr ',' '\n' | sed '/^$/d' | awk '!seen[$0]++' | paste -sd, -)
if [ -n "$STOCKS" ]; then
  python main.py --stocks "$STOCKS"
fi
echo "=== done $(date '+%T') ==="
