"""Konfigurasi runtime dari config.yaml, divalidasi ketat.

Kunci yang tidak dikenal DITOLAK, bukan diabaikan. Pelajaran dari MEX: kunci
yang tampak seperti kontrol tapi tidak tersambung ke apa pun lebih berbahaya
daripada tidak ada kunci sama sekali.
"""
from . import compat  # noqa: F401
import os

import yaml

from . import datafeed
from .strategy import StrategyConfig

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT = os.path.join(ROOT, "config.yaml")

# Dicatat di setiap baris log. Naikkan setiap kali perilaku pencatatan atau
# eksekusi berubah, supaya baris sebelum dan sesudahnya bisa dipisahkan.
ENGINE_VERSION = "snap-v2-fwd-1.2.0"

TOP_LEVEL = {"paper", "strategy"}
PAPER_KEYS = {"capital_usd", "risk_pct", "commission_pct"}
RETIRED = {
    "symbols": "watchlist dikunci di snap/datafeed.py (SYMBOLS). Hapus baris ini.",
    "symbol": "watchlist dikunci di snap/datafeed.py (SYMBOLS). Hapus baris ini.",
    "timeframe": "timeframe dikunci di snap/datafeed.py (INTERVAL). Hapus baris ini.",
    "prefer_source": "sumber data dipilih per koin di snap/datafeed.py (PRIMARY). Hapus baris ini.",
    "allow_short": "sisi short dilarang (t = 0,51, Report 4.2) dan tidak bisa dinyalakan.",
}


def load(path: str = DEFAULT) -> dict:
    with open(path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh) or {}

    for key, why in RETIRED.items():
        if key in cfg or key in (cfg.get("strategy") or {}):
            raise ValueError(f"config.yaml: '{key}' tidak dipakai -- {why}")
    unknown = set(cfg) - TOP_LEVEL
    if unknown:
        raise ValueError(f"config.yaml: kunci tidak dikenal {sorted(unknown)}")

    s = cfg.get("strategy") or {}
    bad = set(s) - set(StrategyConfig.__dataclass_fields__)
    if bad:
        raise ValueError(f"config.yaml: kunci strategy tidak dikenal {sorted(bad)}")
    cfg["params"] = StrategyConfig(**s)

    paper = cfg.get("paper") or {}
    bad = set(paper) - PAPER_KEYS
    if bad:
        raise ValueError(f"config.yaml: kunci paper tidak dikenal {sorted(bad)}")
    cfg["paper"] = {"capital_usd": float(paper.get("capital_usd", 300)),
                    "risk_pct": float(paper.get("risk_pct", 1.0)),
                    "commission_pct": float(paper.get("commission_pct", 0.05))}

    cfg["symbols"] = list(datafeed.SYMBOLS)
    return cfg
