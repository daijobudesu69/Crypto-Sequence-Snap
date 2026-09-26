"""Sequence Snap -- terjemahan langsung dari Pine Script v6.

Source: "Sequence Snap | RSI-Confirmed Reversal Scalper", @version=6.
Diterjemahkan PERSIS, tidak diperbaiki (brief 3). Loop di bawah sengaja ditulis
dengan bentuk yang sama seperti Pine-nya, bukan divektorisasi, supaya bisa diadu
baris per baris dengan source aslinya.

Pemetaan index: di Pine `close[i]` artinya i bar ke belakang dari bar sekarang.
Di sini bar sekarang adalah `t`, jadi `close[i]` Pine = `close[t - i]` di array.

Yang SENGAJA berbeda dari Pine, dan alasannya (brief 3.5):
  - sizing. Pine memakai percent_of_equity 20% dari initial_capital 50.000 dengan
    margin 5%. Project ini memakai risiko tetap 1% equity awal per trade, supaya
    hasil dilaporkan dalam R dan bisa dibandingkan antar simbol tanpa efek
    compounding. Sizing tidak mempengaruhi JUMLAH trade maupun win rate, jadi
    perbandingan replikasi 5.1 tetap sah untuk dua angka itu.

Yang TIDAK diterjemahkan karena tidak mempengaruhi hasil: visual (bgcolor,
plotshape, plot, table dashboard), input tooltip, dan pemilihan posisi dashboard.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

import indicators as I
from engine import Signal


@dataclass(frozen=True)
class StrategyConfig:
    run_length: int = 5
    tolerance_pct: float = 0.05
    rsi_length: int = 14
    rsi_min_long: int = 40
    rsi_max_short: int = 60
    use_rsi_filter: bool = True
    take_profit_r: float = 1.5
    allow_long: bool = True
    allow_short: bool = False


def _setups(df: pd.DataFrame, cfg: StrategyConfig) -> tuple[np.ndarray, np.ndarray]:
    """Kembalikan (long_setup, short_setup) per bar. Belum memperhatikan posisi.

    Sama seperti Pine: `longSetup`/`shortSetup` dihitung di setiap bar tanpa
    memandang posisi. Guard `strategy.position_size == 0` ada di blok entry, yang
    di project ini dikerjakan engine.
    """
    o = df["open"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    c = df["close"].to_numpy(float)
    n = len(df)
    L = cfg.run_length

    rsi = I.rsi(df["close"], cfg.rsi_length).to_numpy(float)
    rsi_prev = np.concatenate([[np.nan], rsi[:-1]])

    with np.errstate(invalid="ignore"):
        rsi_rising = rsi > rsi_prev
        rsi_falling = rsi < rsi_prev
        if cfg.use_rsi_filter:
            rsi_ok_long = (rsi > cfg.rsi_min_long) & rsi_rising
            rsi_ok_short = (rsi < cfg.rsi_max_short) & rsi_falling
        else:
            rsi_ok_long = np.ones(n, dtype=bool)
            rsi_ok_short = np.ones(n, dtype=bool)
        # NaN RSI (bar-bar awal) membuat perbandingan bernilai False, jadi otomatis
        # tidak lolos filter -- sama seperti Pine, yang tidak menembak sebelum RSI
        # punya nilai. Saat filter mati, Pine memang membolehkan semua bar.

    long_setup = np.zeros(n, dtype=bool)
    short_setup = np.zeros(n, dtype=bool)

    for t in range(L, n):
        # ── Reversal candle: the one the run breaks away from ──────────────
        reversal_was_down = c[t - L] < o[t - L]
        reversal_was_up = c[t - L] > o[t - L]

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

        # ── Check the run holds together, bearish direction ────────────────
        run_is_bearish = True
        for i in range(0, L):
            if c[t - i] >= o[t - i]:
                run_is_bearish = False
            if h[t - i] >= h[t - L]:
                run_is_bearish = False
            if i < L - 1:
                ceil_close = c[t - (i + 1)] * (1 + cfg.tolerance_pct / 100)
                if c[t - i] >= ceil_close:
                    run_is_bearish = False

        long_setup[t] = reversal_was_down and run_is_bullish and bool(rsi_ok_long[t])
        short_setup[t] = reversal_was_up and run_is_bearish and bool(rsi_ok_short[t])

    return long_setup, short_setup


def signals(df: pd.DataFrame, cfg: StrategyConfig) -> list[Signal]:
    """Setup yang memenuhi syarat, lengkap dengan stop dan target dari close bar sinyal.

    Pine:
        stopLossPrice   = low[runLength]                    (long)
        riskPts         = close - stopLossPrice
        takeProfitPrice = close + riskPts * rrMultiple
    """
    long_setup, short_setup = _setups(df, cfg)
    l = df["low"].to_numpy(float)
    h = df["high"].to_numpy(float)
    c = df["close"].to_numpy(float)
    L = cfg.run_length

    out: list[Signal] = []
    for t in range(L, len(df)):
        if cfg.allow_long and long_setup[t]:
            stop = l[t - L]
            risk = c[t] - stop
            out.append(Signal(bar=t, side="long", signal_close=c[t], stop_price=stop,
                              target_price=c[t] + risk * cfg.take_profit_r))
        elif cfg.allow_short and short_setup[t]:
            stop = h[t - L]
            risk = stop - c[t]
            out.append(Signal(bar=t, side="short", signal_close=c[t], stop_price=stop,
                              target_price=c[t] - risk * cfg.take_profit_r))
    return out


def from_yaml(d: dict) -> StrategyConfig:
    s = d["strategy"]
    return StrategyConfig(
        run_length=s["run_length"],
        tolerance_pct=s["tolerance_pct"],
        rsi_length=s["rsi_length"],
        rsi_min_long=s["rsi_min_long"],
        rsi_max_short=s["rsi_max_short"],
        use_rsi_filter=s["use_rsi_filter"],
        take_profit_r=s["take_profit_r"],
        allow_long=s["allow_long"],
        allow_short=s["allow_short"],
    )
