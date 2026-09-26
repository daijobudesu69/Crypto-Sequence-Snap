"""Bentuk state/position.json.

    {"schema": 1,
     "symbols": {"ETHUSDT": {"last_bar": ..., "position": ..., "pending": ...}, ...},
     "sent_ids": [...], "outbox": [...], "last_heartbeat_date": ...}

Tiap simbol punya mesin state SENDIRI (last_bar terpisah), jadi satu feed yang
tertinggal tidak bisa menggeser simbol lain. Pengiriman tetap satu antrean
global: outbox adalah satu antrean ke Telegram, sent_ids satu catatan apa yang
sudah sampai.

Kunci dedup memuat simbol. Pelajaran MEX: id sinyal hanya dari waktu bar, dan
di backtest 148 dari 439 sinyal punya id yang sama dengan simbol lain. Tanpa
simbol di kunci, pesan simbol kedua dibuang diam-diam sebagai duplikat.
"""
from . import compat  # noqa: F401

SCHEMA = 1


def dedup_key(kind: str, symbol: str, signal_id: str) -> str:
    return f"{kind}:{symbol}:{signal_id}"


def slot(st: dict, symbol: str) -> dict:
    """Field mesin state simbol itu; slot kosong dibuat kalau belum ada."""
    return st.setdefault("symbols", {}).setdefault(
        symbol, {"last_bar": None, "position": None, "pending": None})


def open_positions(st: dict) -> dict:
    return {s: v["position"] for s, v in (st.get("symbols") or {}).items()
            if v.get("position")}
