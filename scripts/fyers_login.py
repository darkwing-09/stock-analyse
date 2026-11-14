#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Daily Fyers login: exchange a browser auth_code for an access token.

Fyers access tokens expire every day. Run this once each trading morning:

    python scripts/fyers_login.py

Needs in .env: FYERS_CLIENT_ID (App ID such as ABCD1234-100), FYERS_SECRET_KEY
and FYERS_REDIRECT_URI (exactly as registered in the Fyers API dashboard).
The token is saved to FYERS_TOKEN_FILE (default data/fyers_token.json), which
is gitignored. Never commit or share it.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.parse
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402

from data_provider.fyers_fetcher import DEFAULT_TOKEN_FILE, build_login_url, build_token_request  # noqa: E402


def _extract_auth_code(pasted: str) -> str:
    pasted = pasted.strip()
    if "auth_code=" in pasted:
        query = urllib.parse.urlparse(pasted).query or pasted.split("?", 1)[-1]
        return urllib.parse.parse_qs(query).get("auth_code", [""])[0]
    return pasted


def main() -> int:
    load_dotenv()
    client_id = (os.getenv("FYERS_CLIENT_ID") or "").strip()
    secret_key = (os.getenv("FYERS_SECRET_KEY") or "").strip()
    redirect_uri = (os.getenv("FYERS_REDIRECT_URI") or "").strip()
    missing = [name for name, value in (
        ("FYERS_CLIENT_ID", client_id), ("FYERS_SECRET_KEY", secret_key), ("FYERS_REDIRECT_URI", redirect_uri)
    ) if not value]
    if missing:
        print(f"Missing in .env: {', '.join(missing)}")
        return 1

    print("1. Open this link, log in to Fyers and approve the app:\n")
    print("   " + build_login_url(client_id, redirect_uri) + "\n")
    print("2. You will be redirected to a URL containing auth_code=...")
    pasted = input("   Paste that full URL (or just the auth_code) here: ")
    auth_code = _extract_auth_code(pasted)
    if not auth_code:
        print("No auth_code found.")
        return 1

    import requests

    url, body = build_token_request(client_id, secret_key, auth_code)
    response = requests.post(url, json=body, timeout=20).json()
    token = response.get("access_token") if isinstance(response, dict) else None
    if not token:
        print(f"Token exchange failed: {response.get('message') if isinstance(response, dict) else response}")
        return 1

    path = Path(os.getenv("FYERS_TOKEN_FILE") or DEFAULT_TOKEN_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    path.write_text(json.dumps({"client_id": client_id, "access_token": token, "date": today}), encoding="utf-8")
    os.chmod(path, 0o600)
    print(f"\nSaved today's Fyers token to {path} (valid for {today}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
