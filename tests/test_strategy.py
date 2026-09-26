"""Tes strategi: offline, deterministik. Kalau merah, repo sudah menyimpang dari
strategi yang divalidasi -- JANGAN jalankan forward test.

Jalankan: python tests/test_strategy.py
"""
import importlib.util
import sys
import types
from dataclasses import dataclass, replace

from _helpers import ROOT, frame, run_all, uptrend_with_pattern

import numpy as np
import pandas as pd

from snap import indicators
from snap.strategy import (Position, StrategyConfig, compute_features, setups, step,
                           trade_result)

V2 = StrategyConfig()
V1 = replace(V2, use_trend_filter=False)
PATTERN_ONLY = replace(V1, use_rsi_filter=False)

# Report Bagian 3 -- ETHUSDT 4H, bar 5 .. bar 0.
REPORT_BARS = [
    (2295.28, 2298.16, 2238.88, 2244.67),   # bar 5 merah
    (2244.68, 2282.59, 2242.17, 2270.63),   # bar 4
    (2270.64, 2333.98, 2266.46, 2295.89),   # bar 3
    (2295.90, 2320.00, 2286.59, 2303.34),   # bar 2
    (2303.33, 2315.95, 2281.04, 2313.03),   # bar 1
    (2313.03, 2338.74, 2308.00, 2314.10),   # bar 0
]
FILLER = [(2300.0, 2301.0, 2299.0, 2300.5)] * 30   # hijau datar, tanpa lilin merah


def _last_setup(rows, cfg=PATTERN_ONLY):
    f = compute_features(frame(rows), cfg)
    return bool(f["long_setup"][-1]), f


# ── Syarat entry, Report 2.2 ────────────────────────────────────────────────
def test_contoh_report_bagian3_lolos_pola():
    ok, f = _last_setup(FILLER + REPORT_BARS)
    assert ok, "contoh Report Bagian 3 harus lolos syarat pola 1-4"


def test_contoh_report_level_stop_target():
    from snap.strategy import make_pending
    rows = FILLER + REPORT_BARS
    df = frame(rows)
    f = compute_features(df, PATTERN_ONLY)
    p = make_pending(f, pd.DatetimeIndex(df["ts"]), len(df) - 1, PATTERN_ONLY)
    assert p["stop"] == 2238.88
    assert abs(p["target"] - 2426.93) < 0.005, p["target"]
    assert abs(p["risk_pct_of_price"] - 3.25) < 0.01


def test_syarat1_lilin_merah_ketat():
    rows = FILLER + REPORT_BARS
    o, h, l, c = rows[-6]
    rows[-6] = (o, h, l, o)                       # close == open -> bukan merah
    assert not _last_setup(rows)[0]


def test_syarat2_semua_hijau():
    rows = FILLER + REPORT_BARS
    o, h, l, c = rows[-3]
    rows[-3] = (o, h, l, o)                       # bar 2 doji
    assert not _last_setup(rows)[0]


def test_syarat3_low_sama_persis_gagal():
    rows = FILLER + REPORT_BARS
    o, h, l, c = rows[-5]
    rows[-5] = (o, h, 2238.88, c)                 # low bar 4 == low bar 5
    assert not _last_setup(rows)[0]


def test_syarat4_batas_toleransi_persis_gagal():
    rows = FILLER + REPORT_BARS
    c1 = rows[-2][3]
    edge = c1 * (1 - 0.05 / 100)                  # close0 == floor -> gagal (<=)
    o, h, l, _ = rows[-1]
    rows[-1] = (min(o, edge - 1), h, min(l, edge - 1), edge)
    assert not _last_setup(rows)[0]
    rows[-1] = (min(o, edge - 1), h, min(l, edge - 1), edge + 0.01)
    assert _last_setup(rows)[0]


def test_syarat4_hanya_empat_pasang():
    """Bar 4 vs bar 5 TIDAK PERNAH diperiksa: close bar 4 boleh jauh di bawah close bar 5."""
    rows = FILLER + REPORT_BARS
    o5, h5, l5, c5 = rows[-6]
    rows[-6] = (2400.0, 2401.0, l5, 2350.0)       # merah, close 2350 > close bar 4
    assert rows[-5][3] < rows[-6][3]
    assert _last_setup(rows)[0]


def test_syarat8_ema200_ketat():
    rows = uptrend_with_pattern()
    df = frame(rows)
    f = compute_features(df, V2)
    t = 392 + 5
    assert f["long_setup"][t], "pola di uptrend harus lolos V2"
    assert f["long_setup"].sum() == 1
    # Paksa close <= EMA200 di bar 0 lewat array -> harus diblokir.
    f2 = dict(f)
    f2["ma"] = f["ma"].copy()
    f2["ma"][t] = f["close"][t]
    assert not setups(f2, V2)[t]


def test_versi2_memblokir_contoh_report_di_bawah_ema():
    """Seri turun lalu pola: V1 menembak, V2 tidak (close < EMA200)."""
    down = []
    prev = 3000.0
    for _ in range(300):
        o = prev
        c = o * 0.999
        down.append((o, o * 1.0005, c * 0.9995, c))
        prev = c
    scale = prev / 2300.0
    pat = [tuple(x * scale for x in b) for b in REPORT_BARS]
    df = frame(down + pat)
    assert compute_features(df, PATTERN_ONLY)["long_setup"][-1]
    f2 = compute_features(df, replace(V2, use_rsi_filter=False))
    assert f2["close"][-1] < f2["ma"][-1]
    assert not f2["long_setup"][-1]


# ── Parity dengan strategy.py riset ─────────────────────────────────────────
def _research_module():
    """Muat tests/reference/research_strategy.py APA ADANYA, dengan shim import-nya."""
    ind = types.ModuleType("indicators")
    ind.rsi = lambda s, n: pd.Series(indicators.rsi(s.to_numpy(float), n), index=s.index)
    eng = types.ModuleType("engine")

    @dataclass
    class Signal:
        bar: int
        side: str
        signal_close: float
        stop_price: float
        target_price: float
    eng.Signal = Signal
    sys.modules["indicators"], sys.modules["engine"] = ind, eng
    spec = importlib.util.spec_from_file_location(
        "research_strategy", f"{ROOT}/tests/reference/research_strategy.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["research_strategy"] = mod        # dataclass butuh modulnya terdaftar
    spec.loader.exec_module(mod)
    return mod


def _random_walk(n, seed):
    rng = np.random.default_rng(seed)
    rows, prev = [], 100.0
    for _ in range(n):
        o = prev
        # Langkah kecil dan bias naik supaya pola 5-hijau cukup sering muncul.
        c = o * (1 + rng.normal(0.0008, 0.006))
        h = max(o, c) * (1 + abs(rng.normal(0, 0.002)))
        l = min(o, c) * (1 - abs(rng.normal(0, 0.002)))
        rows.append((o, h, l, c))
        prev = c
    return rows


def test_parity_dengan_kode_riset():
    R = _research_module()
    rcfg = R.StrategyConfig()
    total = 0
    for seed in range(6):
        df = frame(_random_walk(1500, seed))
        ref_long, _ = R._setups(df, rcfg)
        f1 = compute_features(df, V1)
        assert np.array_equal(ref_long, f1["long_setup"]), f"V1 beda di seed {seed}"
        f2 = compute_features(df, V2)
        with np.errstate(invalid="ignore"):
            expect = ref_long & (f2["close"] > f2["ma"])
        assert np.array_equal(expect, f2["long_setup"]), f"V2 beda di seed {seed}"
        ref_sig = [s for s in R.signals(df, rcfg) if s.side == "long"]
        for s in ref_sig:
            assert f1["low"][s.bar - 5] == s.stop_price
        total += int(ref_long.sum())
    assert total > 20, f"data uji terlalu sedikit sinyal ({total}) untuk berarti"


# ── Indikator ───────────────────────────────────────────────────────────────
def test_rsi_pakai_rma_bukan_ema():
    x = np.array(_random_walk(300, 7))[:, 3]
    r = indicators.rsi(x, 14)
    d = np.diff(x)
    up, dn = np.maximum(d, 0), np.maximum(-d, 0)
    au, ad = up[:14].mean(), dn[:14].mean()
    for k in range(14, len(d)):
        au = (au * 13 + up[k]) / 14
        ad = (ad * 13 + dn[k]) / 14
    assert abs(r[-1] - (100 - 100 / (1 + au / ad))) < 1e-9


def test_ema_seed_sma():
    x = np.arange(1, 401, dtype=float)
    e = indicators.ema(x, 200)
    assert np.isnan(e[198]) and e[199] == x[:200].mean()


# ── Mesin posisi ────────────────────────────────────────────────────────────
def _pos(entry=100.0, stop=95.0, target=107.5, close0=100.0):
    return Position(signal_id="x", signal_bar="2026-01-01T00:00:00+00:00",
                    entry_bar="2026-01-01T04:00:00+00:00", signal_close=close0,
                    entry_price=entry, stop=stop, target=target,
                    qty=3.0 / (entry - stop), risk_usd=3.0)


def _one_bar(o, h, l, c, pos):
    df = frame([(100, 101, 99, 100)] * 10 + [(o, h, l, c)])
    f = compute_features(df, V2)
    ts = pd.DatetimeIndex(df["ts"])
    return step(f, ts, len(df) - 1, V2, pos, None, 300.0, 1.0)


def test_stop_kena():
    pos, _, ev = _one_bar(99, 100, 94, 96, _pos())
    assert pos is None and ev[0]["reason"] == "stop" and ev[0]["exit_price"] == 95.0


def test_target_kena():
    pos, _, ev = _one_bar(101, 108, 100, 107, _pos())
    assert pos is None and ev[0]["reason"] == "target" and ev[0]["exit_price"] == 107.5


def test_stop_dan_target_satu_lilin_stop_duluan():
    pos, _, ev = _one_bar(100, 110, 90, 105, _pos())
    assert ev[0]["reason"] == "stop" and ev[0]["exit_price"] == 95.0


def test_gap_di_bawah_stop_terisi_di_open():
    pos, _, ev = _one_bar(93, 94, 92, 93.5, _pos())
    assert ev[0]["reason"] == "stop" and ev[0]["exit_price"] == 93.0


def test_gap_di_atas_target_terisi_di_open():
    pos, _, ev = _one_bar(110, 111, 109, 110, _pos())
    assert ev[0]["reason"] == "target" and ev[0]["exit_price"] == 110.0


def test_tidak_kena_apa_apa_tahan_terus():
    pos, _, ev = _one_bar(100, 106, 96, 105, _pos())
    assert pos is not None and not ev and pos.bars_held == 1


def test_alur_lengkap_sinyal_entry_exit():
    rows = uptrend_with_pattern(n=420, red_at=392, pump_at=405)
    df = frame(rows)
    f = compute_features(df, V2)
    ts = pd.DatetimeIndex(df["ts"])
    pos = pending = None
    log = []
    for i in range(len(df)):
        pos, pending, evs = step(f, ts, i, V2, pos, pending, 300.0, 1.0)
        log += [(i, e["event"]) for e in evs]
    assert log[0] == (397, "SIGNAL")
    assert log[1] == (398, "ENTRY")
    # Entry di OPEN bar 398 = close bar 397 (seri kontinu).
    assert log[2] == (405, "EXIT")
    assert len(log) == 3, "tidak boleh ada sinyal lain di seri ini"


def test_entry_di_open_bar_berikutnya_dan_qty():
    rows = uptrend_with_pattern(n=420, red_at=392)
    df = frame(rows)
    f = compute_features(df, V2)
    ts = pd.DatetimeIndex(df["ts"])
    pos = pending = None
    for i in range(399):
        pos, pending, evs = step(f, ts, i, V2, pos, pending, 300.0, 1.0)
        for e in evs:
            if e["event"] == "ENTRY":
                p = e["pos"]
                assert p.entry_price == f["open"][398]
                assert p.stop == f["low"][392]
                assert abs(p.qty * (p.entry_price - p.stop) - 3.0) < 1e-9


def test_hasil_trade_contoh_report():
    """Report Bagian 3: entry 2314,09, target kena -> R = +1,468 (setelah komisi)."""
    p = _pos(entry=2314.09, stop=2238.88, target=2426.93, close0=2314.10)
    r = trade_result(p, 2426.93, 0.05)
    assert abs(r["R_gross"] - 1.5003) < 0.001, r
    assert abs(r["R_net"] - 1.468) < 0.002, r


if __name__ == "__main__":
    sys.exit(run_all(globals()))
