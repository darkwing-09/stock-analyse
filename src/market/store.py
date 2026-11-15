# -*- coding: utf-8 -*-
"""SQLite store for the research platform (SPEC §2).

One file, plain ``sqlite3``. The wide ``metrics`` table is written with pandas
and read back whole; everything else is small row tables with upserts.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

DEFAULT_DB = Path("data/market/market.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS stocks (
  symbol TEXT PRIMARY KEY, name TEXT, industry TEXT, sector TEXT, isin TEXT,
  website TEXT, summary TEXT, employees INTEGER, next_earnings TEXT, ex_dividend TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS prices (
  symbol TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, volume REAL,
  PRIMARY KEY (symbol, date));
CREATE TABLE IF NOT EXISTS financials (
  symbol TEXT, period_type TEXT, statement TEXT, item TEXT, period_end TEXT, value REAL,
  PRIMARY KEY (symbol, period_type, statement, item, period_end));
CREATE TABLE IF NOT EXISTS actions (
  symbol TEXT, date TEXT, kind TEXT, value REAL, PRIMARY KEY (symbol, date, kind));
CREATE TABLE IF NOT EXISTS news (
  id TEXT PRIMARY KEY, symbol TEXT, title TEXT, publisher TEXT, url TEXT, published_at TEXT);
CREATE INDEX IF NOT EXISTS news_symbol ON news(symbol, published_at);
CREATE TABLE IF NOT EXISTS indices (
  code TEXT, date TEXT, close REAL, PRIMARY KEY (code, date));
CREATE TABLE IF NOT EXISTS index_names (code TEXT PRIMARY KEY, symbol TEXT, name TEXT);
CREATE TABLE IF NOT EXISTS checklists (
  symbol TEXT PRIMARY KEY, items TEXT, passed INTEGER, failed INTEGER, unknown INTEGER, total INTEGER);
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
"""


def _rows(cur) -> List[Dict[str, Any]]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


class MarketStore:
    def __init__(self, path: Path = DEFAULT_DB):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    # ------------------------------------------------------------ frames and meta
    def replace_frame(self, name: str, frame: pd.DataFrame) -> None:
        out = frame.copy()
        for col in out.columns:
            if out[col].dtype == bool or str(out[col].dtype) == "boolean":
                out[col] = out[col].astype(object).where(out[col].notna(), None).map(lambda v: None if v is None else int(bool(v)))
            elif out[col].dtype == object:
                out[col] = out[col].map(lambda v: json.dumps(v) if isinstance(v, (list, dict)) else v)
        with self._conn() as c:
            out.to_sql(name, c, if_exists="replace", index=True, index_label="symbol")
            c.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {name}_symbol ON {name}(symbol)")

    def load_frame(self, name: str, bool_columns: Optional[Iterable[str]] = None) -> pd.DataFrame:
        with self._conn() as c:
            try:
                frame = pd.read_sql(f"SELECT * FROM {name}", c, index_col="symbol")
            except Exception:
                return pd.DataFrame()
        for col in (bool_columns or [c for c in frame.columns if c.startswith(("above_", "new_52w", "golden", "fcf_positive"))]):
            if col in frame:
                frame[col] = frame[col].map(lambda v: None if pd.isna(v) else bool(v)).astype(object)
        return frame

    def set_meta(self, key: str, value: Any) -> None:
        with self._conn() as c:
            c.execute("INSERT INTO meta(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(value, default=str)))

    def get_meta(self, key: str, default: Any = None) -> Any:
        with self._conn() as c:
            row = c.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    # ------------------------------------------------------------ generic rows
    def upsert(self, table: str, rows: List[Dict[str, Any]]) -> int:
        if not rows:
            return 0
        cols = list(rows[0].keys())
        sql = f"INSERT OR REPLACE INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})"
        with self._conn() as c:
            c.executemany(sql, [tuple(r.get(k) for k in cols) for r in rows])
        return len(rows)

    def delete_where(self, table: str, where: str, params: tuple = ()) -> None:
        with self._conn() as c:
            c.execute(f"DELETE FROM {table} WHERE {where}", params)

    # ------------------------------------------------------------ prices
    def write_prices(self, panel: Dict[str, pd.DataFrame]) -> int:
        close = panel["close"]
        rows = []
        for sym in close.columns:
            frame = pd.DataFrame({f: panel[f][sym] for f in ("open", "high", "low", "close", "volume") if sym in panel[f]}).dropna(subset=["close"])
            for date, r in frame.iterrows():
                rows.append((sym, date.date().isoformat(), r.get("open"), r.get("high"), r.get("low"), r.get("close"), r.get("volume")))
        with self._conn() as c:
            c.executemany("INSERT OR REPLACE INTO prices VALUES (?,?,?,?,?,?,?)", rows)
        return len(rows)

    def prices(self, symbol: str, start: Optional[str] = None) -> pd.DataFrame:
        with self._conn() as c:
            q = "SELECT date, open, high, low, close, volume FROM prices WHERE symbol=?" + (" AND date>=?" if start else "") + " ORDER BY date"
            frame = pd.read_sql(q, c, params=(symbol, start) if start else (symbol,), index_col="date", parse_dates=["date"])
        return frame

    # ------------------------------------------------------------ per-stock reads
    def stock(self, symbol: str) -> Optional[Dict[str, Any]]:
        with self._conn() as c:
            rows = _rows(c.execute("SELECT * FROM stocks WHERE symbol=?", (symbol,)))
        return rows[0] if rows else None

    def search(self, q: str, limit: int = 10) -> List[Dict[str, Any]]:
        like = f"%{q.strip().upper()}%"
        with self._conn() as c:
            cur = c.execute(
                "SELECT symbol, name, sector, industry FROM stocks WHERE UPPER(symbol) LIKE ? OR UPPER(name) LIKE ? "
                "ORDER BY CASE WHEN UPPER(symbol) LIKE ? THEN 0 ELSE 1 END, symbol LIMIT ?",
                (like, like, f"{q.strip().upper()}%", limit))
            return _rows(cur)

    def financials(self, symbol: str) -> Dict[str, Dict[str, Dict[str, List[Dict[str, Any]]]]]:
        out: Dict[str, Dict[str, Dict[str, List[Dict[str, Any]]]]] = {"quarterly": {}, "annual": {}}
        with self._conn() as c:
            cur = c.execute("SELECT period_type, statement, item, period_end, value FROM financials WHERE symbol=? ORDER BY period_end DESC", (symbol,))
            for pt, st, item, pe, val in cur.fetchall():
                out.setdefault(pt, {}).setdefault(st, {}).setdefault(item, []).append({"period_end": pe, "value": val})
        return out

    def actions(self, symbol: str) -> List[Dict[str, Any]]:
        with self._conn() as c:
            return _rows(c.execute("SELECT date, kind, value FROM actions WHERE symbol=? ORDER BY date", (symbol,)))

    def news(self, symbol: Optional[str] = None, limit: int = 20) -> List[Dict[str, Any]]:
        with self._conn() as c:
            if symbol:
                cur = c.execute("SELECT * FROM news WHERE symbol=? ORDER BY published_at DESC LIMIT ?", (symbol, limit))
            else:
                cur = c.execute("SELECT * FROM news ORDER BY published_at DESC LIMIT ?", (limit,))
            return _rows(cur)

    def checklist(self, symbol: str) -> Optional[Dict[str, Any]]:
        with self._conn() as c:
            rows = _rows(c.execute("SELECT * FROM checklists WHERE symbol=?", (symbol,)))
        if not rows:
            return None
        r = rows[0]
        r["items"] = json.loads(r["items"])
        return r

    # ------------------------------------------------------------ indices
    def write_indices(self, closes: pd.DataFrame, names: Dict[str, tuple]) -> None:
        """``closes`` columns are Yahoo symbols; ``names`` maps code -> (symbol, display name)."""
        by_symbol = {sym: code for code, (sym, _) in names.items()}
        rows, name_rows = [], []
        for code, (sym, label) in names.items():
            name_rows.append((code, sym, label))
            if sym not in closes:
                continue
            for date, v in closes[sym].dropna().items():
                rows.append((code, pd.Timestamp(date).date().isoformat(), float(v)))
        with self._conn() as c:
            c.executemany("INSERT OR REPLACE INTO indices VALUES (?,?,?)", rows)
            c.executemany("INSERT OR REPLACE INTO index_names VALUES (?,?,?)", name_rows)
        _ = by_symbol

    def indices_latest(self, spark_days: int = 60) -> List[Dict[str, Any]]:
        out = []
        with self._conn() as c:
            names = {r["code"]: r for r in _rows(c.execute("SELECT * FROM index_names"))}
            for code, meta in names.items():
                hist = c.execute("SELECT date, close FROM indices WHERE code=? ORDER BY date DESC LIMIT ?", (code, max(spark_days, 260))).fetchall()
                if not hist:
                    continue
                hist = hist[::-1]
                last, prev = hist[-1][1], (hist[-2][1] if len(hist) > 1 else None)
                closes = [h[1] for h in hist]
                def back(n):
                    return closes[-1] / closes[-1 - n] - 1 if len(closes) > n else None
                out.append({
                    "code": code, "name": meta["name"], "symbol": meta["symbol"], "date": hist[-1][0], "close": last,
                    "change": (last - prev) if prev else None, "change_pct": (last / prev - 1) if prev else None,
                    "ret_1m": back(22), "ret_1y": back(252),
                    "spark": closes[-spark_days:],
                })
        return out

    def index_history(self, code: str, days: int = 260) -> List[Dict[str, Any]]:
        with self._conn() as c:
            rows = _rows(c.execute("SELECT date, close FROM indices WHERE code=? ORDER BY date DESC LIMIT ?", (code, days)))
        return rows[::-1]

    def counts(self) -> Dict[str, int]:
        with self._conn() as c:
            return {t: c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ("stocks", "prices", "financials", "actions", "news", "indices", "checklists")}
