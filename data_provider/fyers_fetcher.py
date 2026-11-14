# -*- coding: utf-8 -*-
"""
FyersFetcher - India (NSE) daily bars and realtime quotes via the Fyers API v3.

Endpoints and auth verified from the official ``fyers-apiv3`` 3.2.1 SDK:

- ``GET https://api-t1.fyers.in/data/history`` (daily candles, at most 366 days per request)
- ``GET https://api-t1.fyers.in/data/quotes`` (up to 50 symbols per request)
- header ``Authorization: <client_id>:<access_token>``

Credentials come from ``FYERS_CLIENT_ID`` + ``FYERS_ACCESS_TOKEN``, or from the
token file written by ``scripts/fyers_login.py`` (``FYERS_TOKEN_FILE``, default
``data/fyers_token.json``). Fyers access tokens expire daily, so run the login
script once per trading day. When unconfigured the fetcher is not registered and
India data keeps using Yahoo Finance.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import urllib.parse
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

import pandas as pd

from .base import STANDARD_COLUMNS, BaseFetcher, DataFetchError
from .realtime_types import RealtimeSource, UnifiedRealtimeQuote
from src.services.market_symbol_utils import split_suffix_symbol

logger = logging.getLogger(__name__)

FYERS_API = "https://api-t1.fyers.in/api/v3"
FYERS_DATA_API = "https://api-t1.fyers.in/data"
_IST = ZoneInfo("Asia/Kolkata")
_MAX_DAILY_SPAN_DAYS = 366
DEFAULT_TOKEN_FILE = "data/fyers_token.json"

# Fyers index symbols for the India market review.
FYERS_IN_INDICES: Dict[str, Tuple[str, str]] = {
    "NIFTY50": ("NSE:NIFTY50-INDEX", "Nifty 50"),
    "SENSEX": ("BSE:SENSEX-INDEX", "BSE Sensex"),
    "BANKNIFTY": ("NSE:NIFTYBANK-INDEX", "Nifty Bank"),
    "INDIAVIX": ("NSE:INDIAVIX-INDEX", "India VIX"),
}


def to_fyers_symbol(stock_code: str) -> Optional[str]:
    """Map ``RELIANCE.NS`` -> ``NSE:RELIANCE-EQ``; anything else -> ``None``.

    BSE (``.BO``) is intentionally unsupported: Fyers BSE symbols carry a
    group-dependent series suffix that cannot be derived from the ticker.
    """
    parts = split_suffix_symbol(stock_code)
    if parts is None:
        return None
    base, suffix = parts
    if suffix != "NS" or not base:
        return None
    return f"NSE:{base}-EQ"


def load_fyers_credentials(token_file: Optional[str] = None) -> Tuple[str, str]:
    """Return ``(client_id, access_token)`` from env vars or the login token file."""
    client_id = (os.getenv("FYERS_CLIENT_ID") or "").strip()
    access_token = (os.getenv("FYERS_ACCESS_TOKEN") or "").strip()
    if client_id and access_token:
        return client_id, access_token
    path = Path(token_file or os.getenv("FYERS_TOKEN_FILE") or DEFAULT_TOKEN_FILE)
    try:
        saved = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return client_id, access_token
    token_day = str(saved.get("date") or "")
    if token_day and token_day != datetime.now(_IST).date().isoformat():
        logger.warning("[Fyers] access token in %s is from %s; run scripts/fyers_login.py", path, token_day)
    return (client_id or str(saved.get("client_id") or "")).strip(), str(saved.get("access_token") or "").strip()


def build_login_url(client_id: str, redirect_uri: str, state: str = "stock-analyse") -> str:
    """Browser URL where the user logs in and receives an ``auth_code``."""
    query = urllib.parse.urlencode(
        {"client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code", "state": state}
    )
    return f"{FYERS_API}/generate-authcode?{query}"


def build_token_request(client_id: str, secret_key: str, auth_code: str) -> Tuple[str, Dict[str, str]]:
    """``(url, json_body)`` for exchanging an ``auth_code`` for an access token."""
    app_id_hash = hashlib.sha256(f"{client_id}:{secret_key}".encode()).hexdigest()
    body = {"grant_type": "authorization_code", "appIdHash": app_id_hash, "code": auth_code}
    return f"{FYERS_API}/validate-authcode", body


class FyersFetcher(BaseFetcher):
    """NSE equities and indices from Fyers; preferred over Yahoo Finance for India."""

    name = "FyersFetcher"
    priority = 1

    def __init__(
        self,
        client_id: Optional[str] = None,
        access_token: Optional[str] = None,
        session: Any = None,
    ):
        if client_id is None and access_token is None:
            client_id, access_token = load_fyers_credentials()
        self._client_id = (client_id or "").strip()
        self._access_token = (access_token or "").strip()
        if session is None:
            import requests

            session = requests.Session()
        self._session = session

    # -- configuration -------------------------------------------------
    @classmethod
    def has_configured_credentials(cls) -> bool:
        client_id, access_token = load_fyers_credentials()
        return bool(client_id and access_token)

    def is_configured(self) -> bool:
        return bool(self._client_id and self._access_token)

    def _headers(self) -> Dict[str, str]:
        return {"Authorization": f"{self._client_id}:{self._access_token}", "version": "3"}

    def _get(self, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_configured():
            raise DataFetchError("[Fyers] credentials not configured")
        try:
            resp = self._session.get(f"{FYERS_DATA_API}{path}", params=params, headers=self._headers(), timeout=15)
            payload = resp.json()
        except Exception as exc:
            raise DataFetchError(f"[Fyers] request {path} failed: {exc}") from exc
        if not isinstance(payload, dict) or payload.get("s") != "ok":
            message = payload.get("message") if isinstance(payload, dict) else payload
            raise DataFetchError(f"[Fyers] {path} error: {message}")
        return payload

    # -- daily bars ----------------------------------------------------
    @staticmethod
    def _date_chunks(start_date: str, end_date: str) -> List[Tuple[str, str]]:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
        chunks = []
        while start <= end:
            chunk_end = min(end, start + timedelta(days=_MAX_DAILY_SPAN_DAYS - 1))
            chunks.append((start.isoformat(), chunk_end.isoformat()))
            start = chunk_end + timedelta(days=1)
        return chunks

    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        symbol = to_fyers_symbol(stock_code)
        if symbol is None:
            raise DataFetchError(f"[Fyers] {stock_code} is not an NSE (.NS) symbol")
        candles: List[List[Any]] = []
        for range_from, range_to in self._date_chunks(start_date, end_date):
            payload = self._get(
                "/history",
                {
                    "symbol": symbol,
                    "resolution": "D",
                    "date_format": 1,
                    "range_from": range_from,
                    "range_to": range_to,
                    "cont_flag": 1,
                },
            )
            candles.extend(payload.get("candles") or [])
        return pd.DataFrame(candles, columns=["t", "open", "high", "low", "close", "volume"])

    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        if df.empty:
            return df
        df = df.copy()
        df["date"] = pd.to_datetime(df["t"], unit="s", utc=True).dt.tz_convert(_IST).dt.date
        df = df.drop_duplicates(subset="date", keep="last").sort_values("date").reset_index(drop=True)
        df["pct_chg"] = (df["close"].pct_change() * 100).fillna(0).round(2)
        df["amount"] = df["volume"] * df["close"]
        df["code"] = stock_code
        keep = ["code"] + STANDARD_COLUMNS
        return df[[col for col in keep if col in df.columns]]

    # -- quotes --------------------------------------------------------
    def _quote_values(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        payload = self._get("/quotes", {"symbols": ",".join(symbols)})
        values = {}
        for item in payload.get("d") or []:
            if item.get("s") == "ok" and isinstance(item.get("v"), dict):
                values[item.get("n")] = item["v"]
        return values

    def get_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        symbol = to_fyers_symbol(stock_code)
        if symbol is None or not self.is_configured():
            return None
        try:
            v = self._quote_values([symbol]).get(symbol)
        except DataFetchError as exc:
            logger.warning(f"[Fyers] quote {stock_code} failed: {exc}")
            return None
        if not v or not v.get("lp"):
            return None
        high, low, prev = v.get("high_price"), v.get("low_price"), v.get("prev_close_price")
        amplitude = round((high - low) / prev * 100, 2) if high and low and prev else None
        timestamp = v.get("tt")
        provider_ts = (
            datetime.fromtimestamp(int(timestamp), _IST).isoformat() if str(timestamp or "").isdigit() else None
        )
        volume = v.get("volume")
        return UnifiedRealtimeQuote(
            code=stock_code.strip().upper(),
            name=str(v.get("description") or v.get("short_name") or ""),
            source=RealtimeSource.FALLBACK,
            provider_timestamp=provider_ts,
            market="in",
            currency="INR",
            price=float(v["lp"]),
            change_pct=v.get("chp"),
            change_amount=v.get("ch"),
            volume=int(volume) if volume is not None else None,
            amount=(float(volume) * float(v["atp"])) if volume and v.get("atp") else None,
            amplitude=amplitude,
            open_price=v.get("open_price"),
            high=high,
            low=low,
            pre_close=prev,
        )

    def get_stock_name(self, stock_code: str) -> Optional[str]:
        quote = self.get_realtime_quote(stock_code)
        return quote.name if quote and quote.name else None

    def get_main_indices(self, region: str = "cn") -> Optional[List[Dict[str, Any]]]:
        if region != "in" or not self.is_configured():
            return None
        symbols = [symbol for symbol, _ in FYERS_IN_INDICES.values()]
        try:
            values = self._quote_values(symbols)
        except DataFetchError as exc:
            logger.warning(f"[Fyers] index quotes failed: {exc}")
            return None
        results = []
        for code, (symbol, name) in FYERS_IN_INDICES.items():
            v = values.get(symbol)
            if not v or v.get("lp") is None:
                continue
            high, low, prev = v.get("high_price"), v.get("low_price"), v.get("prev_close_price")
            results.append(
                {
                    "code": code,
                    "name": name,
                    "current": float(v["lp"]),
                    "change": float(v.get("ch") or 0.0),
                    "change_pct": float(v.get("chp") or 0.0),
                    "open": float(v.get("open_price") or 0.0),
                    "high": float(high or 0.0),
                    "low": float(low or 0.0),
                    "prev_close": float(prev or 0.0),
                    "volume": float(v.get("volume") or 0.0),
                    "amount": 0.0,
                    "amplitude": round((high - low) / prev * 100, 2) if high and low and prev else 0.0,
                }
            )
        return results or None
