"""Sequence Snap Versi 2 -- aturan sinyal dan mesin posisi paper trading.

Dua bagian, dengan dua sumber kebenaran yang berbeda:

1. setups() -- DETEKSI POLA. Loop-nya disalin baris per baris dari
   `strategy.py` riset (tests/reference/research_strategy.py), yang sendiri
   terjemahan langsung Pine v6 dan sudah lolos 65 test + replikasi TradingView.
   Satu-satunya tambahan adalah syarat #8 Versi 2: `close > EMA200`, persis
   seperti pine/SequenceSnap_v2.pine. tests/test_strategy.py mengadu fungsi ini
   dengan kode riset aslinya, jadi keduanya tidak bisa menyimpang diam-diam.

   Pemetaan index: `close[i]` di Pine = `c[t - i]` di sini. `close[i + 1]` adalah
   lilin yang LEBIH LAMA (lihat PROJECT_LOG insiden I4).

2. step() -- MESIN POSISI untuk forward test, bar demi bar:

     A. sinyal dari bar sebelumnya -> entry di OPEN bar ini (market order)
     B. stop dan target diuji di bar ini, termasuk bar entry itu sendiri
        (di Pine, strategy.exit sudah aktif begitu entry terisi)
     C. sinyal baru dievaluasi di CLOSE bar ini, hanya kalau posisi kosong

   Stop = low[5] dan target = close[0] + 1,5 x (close[0] - low[5]) dihitung dari
   CLOSE bar sinyal dan dibekukan -- tidak ada trailing (Report Bagian 2.3).
   Kalau stop dan target tersentuh di lilin yang sama, stop dianggap duluan
   (pesimis, Report 4.1). Tidak ada batas waktu tahan.
"""
from . import compat  # noqa: F401
from dataclasses import asdict, dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from .indicators import ema, rsi, sma

BAR = pd.Timedelta("4h")


@dataclass(frozen=True)
class StrategyConfig:
    """Parameter Versi 2. Default = nilai yang dikunci di Report Bagian 4.3.

    Sisi short sengaja TIDAK ada di sini: t = 0,51 di 432 trade, dan Report 4.2
    melarangnya. Tidak ada kunci config yang bisa menyalakannya.
    """
    run_length: int = 5
    tolerance_pct: float = 0.05
    rsi_length: int = 14
    rsi_min_long: float = 40
    use_rsi_filter: bool = True
    use_trend_filter: bool = True       # False = Versi 1. Jangan dimatikan.
    ma_length: int = 200
    ma_type: str = "EMA"                # Report menguji EMA; SMA belum pernah diuji
    take_profit_r: float = 1.5


# --------------------------------------------------------------------------- #
# indikator + pola
# --------------------------------------------------------------------------- #
def compute_features(df: pd.DataFrame, cfg: StrategyConfig) -> dict:
    """Semua array yang dibutuhkan setups() dan context(), dari bar yang sudah TUTUP."""
    f = {k: df[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume")}
    f["rsi"] = rsi(f["close"], cfg.rsi_length)
    f["rsi_prev"] = np.concatenate([[np.nan], f["rsi"][:-1]])
    if cfg.ma_type == "EMA":
        f["ma"] = ema(f["close"], cfg.ma_length)
    elif cfg.ma_type == "SMA":
        f["ma"] = sma(f["close"], cfg.ma_length)
    else:
        raise ValueError(f"ma_type harus EMA atau SMA, bukan {cfg.ma_type!r}")
    f["long_setup"] = setups(f, cfg)
    return f


def setups(f: dict, cfg: StrategyConfig) -> np.ndarray:
    """longSetup per bar -- belum memperhatikan posisi (guard ada di step()).

    Loop di bawah SENGAJA berbentuk sama dengan Pine dan strategy.py riset, bukan
    divektorisasi, supaya bisa diadu baris per baris. Hanya sisi bullish yang
    dihitung karena sisi short tidak pernah dipakai.
    """
    o, l, c = f["open"], f["low"], f["close"]
    rsi_v, rsi_prev, ma = f["rsi"], f["rsi_prev"], f["ma"]
    n = len(c)
    L = cfg.run_length

    with np.errstate(invalid="ignore"):
        rsi_rising = rsi_v > rsi_prev
        if cfg.use_rsi_filter:
            rsi_ok_long = (rsi_v > cfg.rsi_min_long) & rsi_rising
        else:
            rsi_ok_long = np.ones(n, dtype=bool)
        # Syarat #8 (Versi 2): Pine `close > maValue`. EMA yang masih NaN membuat
        # perbandingan False -- sama seperti Pine, yang tidak menembak sebelum
        # MA punya nilai.
        if cfg.use_trend_filter:
            trend_ok_long = c > ma
        else:
            trend_ok_long = np.ones(n, dtype=bool)

    long_setup = np.zeros(n, dtype=bool)
    for t in range(L, n):
        # ── Reversal candle: the one the run breaks away from ──────────────
        reversal_was_down = c[t - L] < o[t - L]

        # ── Check the run holds together, bullish direction ────────────────
        run_is_bullish = True
        for i in range(0, L):                      # Pine: for i = 0 to runLength - 1
            if c[t - i] <= o[t - i]:
                run_is_bullish = False
            if l[t - i] <= l[t - L]:
                run_is_bullish = False
            if i < L - 1:
                floor_close = c[t - (i + 1)] * (1 - cfg.tolerance_pct / 100)
                if c[t - i] <= floor_close:
                    run_is_bullish = False

        long_setup[t] = (reversal_was_down and run_is_bullish
                         and bool(rsi_ok_long[t]) and bool(trend_ok_long[t]))
    return long_setup


def context(f: dict, i: int, cfg: StrategyConfig) -> dict:
    """Snapshot bar i yang ikut dicatat -- supaya tiap sinyal bisa diverifikasi manual."""
    def g(k, j=i):
        v = f[k][j]
        return None if not np.isfinite(v) else round(float(v), 8)
    L = cfg.run_length
    ma = f["ma"][i]
    return {
        "open": g("open"), "high": g("high"), "low": g("low"), "close": g("close"),
        "volume": g("volume"),
        "rsi_bar0": None if not np.isfinite(f["rsi"][i]) else round(float(f["rsi"][i]), 4),
        "rsi_bar1": (None if not np.isfinite(f["rsi_prev"][i])
                     else round(float(f["rsi_prev"][i]), 4)),
        "ema200_bar0": g("ma"),
        "close_vs_ema200_pct": (round((f["close"][i] / ma - 1) * 100, 4)
                                if np.isfinite(ma) and ma else None),
        "low_bar5": g("low", i - L) if i >= L else None,
    }


# --------------------------------------------------------------------------- #
# mesin posisi
# --------------------------------------------------------------------------- #
@dataclass
class Position:
    signal_id: str
    signal_bar: str          # bar yang CLOSE-nya menghasilkan sinyal (bar 0)
    entry_bar: str           # bar yang OPEN-nya jadi harga entry referensi
    signal_close: float      # close bar 0 -- dasar stop/target
    entry_price: float       # open bar entry (paper fill, tanpa slippage)
    stop: float              # low[5], beku
    target: float            # close[0] + 1,5R, beku
    qty: float               # paper: (modal x risiko%) / (entry - stop)
    risk_usd: float          # modal awal x risiko% (tidak di-compound, PROJECT_LOG D4)
    bars_held: int = 0
    mae_pct: float = 0.0
    mfe_pct: float = 0.0
    notified: bool = True    # False kalau sinyalnya tidak pernah terkirim
    sig_ctx: dict = field(default_factory=dict)


def signal_id(bar: pd.Timestamp) -> str:
    return f"{bar:%Y%m%dT%H%M}-L"


def make_pending(f: dict, ts: pd.DatetimeIndex, i: int, cfg: StrategyConfig) -> dict:
    """Order yang akan dieksekusi di open bar berikutnya. Level persis rumus Pine."""
    L = cfg.run_length
    close0 = float(f["close"][i])
    stop = float(f["low"][i - L])
    risk = close0 - stop
    bar = ts[i]
    return {
        "signal_id": signal_id(bar), "signal_bar": bar.isoformat(),
        "signal_close": close0, "stop": stop,
        "target": close0 + risk * cfg.take_profit_r,
        "risk_pct_of_price": risk / close0 * 100.0,
        # Entry = open bar berikutnya = saat bar sinyal TUTUP.
        "entry_due": (bar + BAR).isoformat(),
        "sig_ctx": context(f, i, cfg),
        "notified": True,
    }


def _exit(pos: Position, bar, px: float, reason: str, f: dict, i: int, cfg) -> dict:
    return {"event": "EXIT", "bar": bar, "pos": pos, "exit_price": float(px),
            "reason": reason, "ctx": context(f, i, cfg)}


def step(f: dict, ts: pd.DatetimeIndex, i: int, cfg: StrategyConfig,
         pos: Optional[Position], pending: Optional[dict],
         capital: float, risk_pct: float):
    """Proses satu bar yang sudah tutup. Mengembalikan (position, pending, events)."""
    events = []
    o, h, l = f["open"], f["high"], f["low"]
    bar = ts[i]

    # --- A. sinyal bar sebelumnya dieksekusi di OPEN bar ini ------------------
    just_entered = False
    if pending is not None and pos is None:
        entry = float(o[i])
        risk_usd = capital * risk_pct / 100.0
        dist = entry - pending["stop"]
        pos = Position(
            signal_id=pending["signal_id"], signal_bar=pending["signal_bar"],
            entry_bar=bar.isoformat(), signal_close=pending["signal_close"],
            entry_price=entry, stop=pending["stop"], target=pending["target"],
            # Report 2.3: qty = (modal x 1%) / (harga entry - stop). Kalau open
            # sudah di bawah stop, jaraknya <= 0 dan qty tidak terdefinisi; posisi
            # itu langsung keluar di bawah (gap), jadi qty 0 cukup untuk mencatat.
            qty=risk_usd / dist if dist > 0 else 0.0,
            risk_usd=risk_usd,
            notified=bool(pending.get("notified", True)),
            sig_ctx=dict(pending.get("sig_ctx") or {}),
        )
        just_entered = True
        events.append({"event": "ENTRY", "bar": bar, "pos": pos, "pending": pending,
                       "ctx": context(f, i, cfg)})
        pending = None

    # --- B. stop / target, bar entry ikut diuji --------------------------------
    if pos is not None:
        pos.bars_held += 0 if just_entered else 1
        op, hi, lo = float(o[i]), float(h[i]), float(l[i])
        pos.mae_pct = min(pos.mae_pct, (lo / pos.entry_price - 1) * 100)
        pos.mfe_pct = max(pos.mfe_pct, (hi / pos.entry_price - 1) * 100)
        ev = None
        # Gap di open: order stop/limit yang sudah terlewati terisi di harga open,
        # bukan di level yang tidak pernah diperdagangkan (PROJECT_LOG asumsi F).
        if op <= pos.stop:
            ev = _exit(pos, bar, op, "stop", f, i, cfg)
        elif op >= pos.target:
            ev = _exit(pos, bar, op, "target", f, i, cfg)
        elif lo <= pos.stop:
            # Dua-duanya kena di lilin yang sama -> stop duluan (pesimis).
            ev = _exit(pos, bar, pos.stop, "stop", f, i, cfg)
        elif hi >= pos.target:
            ev = _exit(pos, bar, pos.target, "target", f, i, cfg)
        if ev:
            events.append(ev)
            pos = None

    # --- C. sinyal baru di CLOSE bar ini ----------------------------------------
    # Seperti Pine: posisi yang keluar di bar ini sudah flat saat script jalan di
    # close, jadi bar yang sama boleh menghasilkan sinyal baru.
    if pos is None and pending is None and bool(f["long_setup"][i]):
        pending = make_pending(f, ts, i, cfg)
        events.append({"event": "SIGNAL", "bar": bar, "pending": pending,
                       "ctx": pending["sig_ctx"]})

    return pos, pending, events


def trade_result(pos: Position, exit_price: float, commission_pct: float) -> dict:
    """Hasil trade dalam R dan USD kertas.

    R kotor  = (exit - entry) / (entry - stop)         -- satuan Report
    R bersih = R kotor dikurangi komisi dua sisi, dalam R
    Funding tidak dihitung: API funding Binance perp tidak terjangkau dari runner
    GitHub (HTTP 451). Report: rata-rata funding +0,012 R per trade.
    """
    dist = pos.entry_price - pos.stop
    # Posisi yang gap di bawah stop di open-nya sendiri tidak punya jarak risiko
    # nyata; R-nya diukur terhadap risiko rencana (close bar 0 - stop).
    base = dist if dist > 0 else (pos.signal_close - pos.stop)
    r_gross = (exit_price - pos.entry_price) / base if base > 0 else 0.0
    fee_frac = commission_pct / 100.0
    fee_r = fee_frac * (pos.entry_price + exit_price) / base if base > 0 else 0.0
    qty = pos.qty
    pnl = qty * (exit_price - pos.entry_price) - qty * fee_frac * (pos.entry_price + exit_price)
    return {
        "R_gross": r_gross, "R_net": r_gross - fee_r,
        "pnl_usd": pnl, "notional_usd": qty * pos.entry_price,
        "ret_pct": (exit_price / pos.entry_price - 1) * 100.0,
    }


def pos_to_dict(pos: Optional[Position]):
    return None if pos is None else asdict(pos)


def pos_from_dict(d) -> Optional[Position]:
    return None if not d else Position(**d)
