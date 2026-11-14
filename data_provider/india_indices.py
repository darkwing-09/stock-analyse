# -*- coding: utf-8 -*-
"""India (NSE/BSE) index catalogue shared by the market review and the
swing-trading ranking engine.

Yahoo Finance symbols were verified live on 2026-11-15. Keep this module
dependency-free so any layer can import it.
"""

from __future__ import annotations

from typing import Dict, Tuple

# code -> (Yahoo symbol, display name). Order is the display order.
IN_MAIN_INDICES: Dict[str, Tuple[str, str]] = {
    "NIFTY50": ("^NSEI", "Nifty 50"),
    "SENSEX": ("^BSESN", "BSE Sensex"),
    "BANKNIFTY": ("^NSEBANK", "Nifty Bank"),
    "INDIAVIX": ("^INDIAVIX", "India VIX"),
}

# Benchmark used for relative strength.
IN_BENCHMARK_SYMBOL = "^NSEI"

# Sector index code -> (Yahoo symbol, display name).
IN_SECTOR_INDICES: Dict[str, Tuple[str, str]] = {
    "NIFTYIT": ("^CNXIT", "Nifty IT"),
    "BANKNIFTY": ("^NSEBANK", "Nifty Bank"),
    "FINNIFTY": ("NIFTY_FIN_SERVICE.NS", "Nifty Financial Services"),
    "NIFTYAUTO": ("^CNXAUTO", "Nifty Auto"),
    "NIFTYPHARMA": ("^CNXPHARMA", "Nifty Pharma"),
    "NIFTYFMCG": ("^CNXFMCG", "Nifty FMCG"),
    "NIFTYMETAL": ("^CNXMETAL", "Nifty Metal"),
    "NIFTYENERGY": ("^CNXENERGY", "Nifty Energy"),
    "NIFTYREALTY": ("^CNXREALTY", "Nifty Realty"),
    "NIFTYPSUBANK": ("^CNXPSUBANK", "Nifty PSU Bank"),
    "NIFTYINFRA": ("^CNXINFRA", "Nifty Infrastructure"),
    "NIFTYCONSUMPTION": ("^CNXCONSUM", "Nifty Consumption"),
}

# NSE "Industry" (as published in the index constituent CSVs) -> sector index code.
NSE_INDUSTRY_TO_SECTOR: Dict[str, str] = {
    "Information Technology": "NIFTYIT",
    "Financial Services": "FINNIFTY",
    "Automobile and Auto Components": "NIFTYAUTO",
    "Healthcare": "NIFTYPHARMA",
    "Fast Moving Consumer Goods": "NIFTYFMCG",
    "Metals & Mining": "NIFTYMETAL",
    "Oil Gas & Consumable Fuels": "NIFTYENERGY",
    "Power": "NIFTYENERGY",
    "Realty": "NIFTYREALTY",
    "Construction": "NIFTYINFRA",
    "Construction Materials": "NIFTYINFRA",
    "Capital Goods": "NIFTYINFRA",
    "Telecommunication": "NIFTYINFRA",
    "Services": "NIFTYINFRA",
    "Consumer Durables": "NIFTYCONSUMPTION",
    "Consumer Services": "NIFTYCONSUMPTION",
    "Textiles": "NIFTYCONSUMPTION",
    "Media Entertainment & Publication": "NIFTYCONSUMPTION",
    "Chemicals": "NIFTYPHARMA",
    "Diversified": "NIFTYENERGY",
}
