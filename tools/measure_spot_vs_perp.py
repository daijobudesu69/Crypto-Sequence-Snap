"""Ukur tracking error: sinyal V2 di data SPOT (yang dipakai bot) vs PERP (backtest).

Bot tidak bisa membaca API perp Binance dari runner GitHub (HTTP 451), jadi ia
memakai mirror spot. Pertanyaannya: berapa sinyal yang berbeda karena itu? MEX
mengukur 94-97% untuk ETH/XRP/DOGE dengan aturan MEX; untuk Sequence Snap, dan
untuk BNB dan AVAX sama sekali, belum pernah diukur. Skrip ini mengukurnya.

Juga dua cek replikasi terhadap Report, supaya mesin di repo ini terbukti sama
dengan mesin riset SEBELUM forward test dimulai:

  1. Report Bagian 3: sinyal ETHUSDT 9 Sep 2024 08:00 UTC (Versi 1), RSI 48,52
     vs 48,33, stop 2238,88, target 2426,93.
  2. Jumlah trade Versi 1 per koin 2024-01..2026-08 vs tabel MIN_NOTIONAL di
     setup V1 (43/42/39/37/25 trade s/d 19 Sep 2026 -- jadi angka di sini boleh
     sedikit lebih kecil karena September 2026 tidak ikut).

Sumber: arsip bulanan resmi data.binance.vision (futures/um dan spot), 4H.
Keluaran: docs/SPOT_VS_PERP.md dan ringkasan di stdout.

Dijalankan lewat workflow "Ukur spot vs perp" (manual). Butuh ~2-5 menit.
"""
import io
import os
import sys
import zipfile
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import snap.compat  # noqa: F401,E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import requests  # noqa: E402

from snap.config import load  # noqa: E402
from snap.datafeed import SYMBOLS  # noqa: E402
from snap.strategy import compute_features, step, trade_result  # noqa: E402

BASE = "https://data.binance.vision/data"
START, END = "2024-01", "2026-08"
EVAL_FROM = pd.Timestamp("2024-07-01", tz="UTC")   # 6 bulan pemanasan EMA200
CACHE = ".cache/klines"
OUT = "docs/SPOT_VS_PERP.md"


def _months():
    return [p.strftime("%Y-%m") for p in pd.period_range(START, END, freq="M")]


def _download(market: str, sym: str, month: str) -> pd.DataFrame | None:
    path = (f"{BASE}/futures/um/monthly/klines/{sym}/4h/{sym}-4h-{month}.zip"
            if market == "perp" else
            f"{BASE}/spot/monthly/klines/{sym}/4h/{sym}-4h-{month}.zip")
    local = os.path.join(CACHE, market, f"{sym}-{month}.zip")
    if not os.path.exists(local):
        r = requests.get(path, timeout=60)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        os.makedirs(os.path.dirname(local), exist_ok=True)
        with open(local, "wb") as fh:
            fh.write(r.content)
    with zipfile.ZipFile(local) as z:
        raw = z.read(z.namelist()[0]).decode()
    df = pd.read_csv(io.StringIO(raw), header=None)
    # Arsip perp punya baris header sejak 2022; arsip spot tidak.
    df = df[pd.to_numeric(df[0], errors="coerce").notna()].astype(float)
    ot = df[0].astype("int64")
    # Arsip spot sejak 2025-01 memakai MIKROdetik, perp tetap milidetik.
    ms = np.where(ot > 10**14, ot // 1000, ot)
    ts = pd.to_datetime(ms, unit="ms", utc=True)
    return pd.DataFrame({"ts": ts, "open": df[1].values, "high": df[2].values,
                         "low": df[3].values, "close": df[4].values,
                         "volume": df[5].values})


def series(market: str, sym: str) -> pd.DataFrame:
    frames = [d for m in _months() if (d := _download(market, sym, m)) is not None]
    df = pd.concat(frames, ignore_index=True)
    return df.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)


def simulate(df: pd.DataFrame, cfg_params, paper: dict):
    """Jalankan mesin forward test yang SAMA di seluruh sejarah. (sinyal, trade)."""
    f = compute_features(df, cfg_params)
    ts = pd.DatetimeIndex(df["ts"])
    pos = pending = None
    signals, trades = [], []
    for i in range(len(df)):
        pos, pending, events = step(f, ts, i, cfg_params, pos, pending,
                                    paper["capital_usd"], paper["risk_pct"])
        for ev in events:
            if ev["event"] == "SIGNAL":
                signals.append((ts[i], ev["pending"]))
            elif ev["event"] == "EXIT":
                res = trade_result(ev["pos"], ev["exit_price"], paper["commission_pct"])
                trades.append((pd.Timestamp(ev["pos"].signal_bar), res["R_net"]))
    return f, ts, signals, trades


def main() -> int:
    cfg = load()
    v2, paper = cfg["params"], cfg["paper"]
    v1 = replace(v2, use_trend_filter=False)
    lines = ["# Spot vs perp — tracking error sinyal Sequence Snap", "",
             f"Diukur {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M} UTC oleh "
             "`tools/measure_spot_vs_perp.py`. Arsip bulanan resmi "
             f"data.binance.vision, {START} .. {END}, dievaluasi sejak "
             f"{EVAL_FROM:%Y-%m-%d} (sebelumnya pemanasan EMA200).", ""]

    # ── 1. Replikasi Report Bagian 3 ───────────────────────────────────────
    eth = series("perp", "ETHUSDT")
    f1, ts1, sig1, _ = simulate(eth, v1, paper)
    target_bar = pd.Timestamp("2024-09-09 08:00", tz="UTC")
    hit = [p for t, p in sig1 if t == target_bar]
    i = int(ts1.get_loc(target_bar))
    rep_ok = bool(hit) and abs(hit[0]["stop"] - 2238.88) < 1e-6 \
        and abs(hit[0]["target"] - 2426.93) < 0.01 \
        and abs(f1["rsi"][i] - 48.52) < 0.01 and abs(f1["rsi_prev"][i] - 48.33) < 0.01
    lines += ["## 1. Replikasi contoh Report Bagian 3 (ETHUSDT perp, Versi 1)", "",
              "| | Report | Repo ini |", "|---|---:|---:|",
              f"| Sinyal 2024-09-09 08:00 UTC | ada | {'ada' if hit else '**TIDAK ADA**'} |",
              f"| RSI bar 0 | 48,52 | {f1['rsi'][i]:.2f} |",
              f"| RSI bar 1 | 48,33 | {f1['rsi_prev'][i]:.2f} |",
              f"| Stop | 2238,88 | {hit[0]['stop'] if hit else float('nan'):.2f} |",
              f"| Target | 2426,93 | {hit[0]['target'] if hit else float('nan'):.2f} |",
              f"| close vs EMA200 | — | {f1['close'][i] / f1['ma'][i] * 100 - 100:+.2f}% "
              f"({'lolos' if f1['close'][i] > f1['ma'][i] else 'DIBLOKIR'} filter V2) |",
              "", f"**Hasil: {'COCOK' if rep_ok else 'TIDAK COCOK — jangan mulai forward test'}**",
              ""]

    # ── 2. Per simbol ──────────────────────────────────────────────────────
    rows = []
    v1_rows = []
    for sym in SYMBOLS:
        print(f"[measure] {sym} ...", flush=True)
        perp, spot = series("perp", sym), series("spot", sym)
        common = perp["ts"][perp["ts"].isin(spot["ts"])]
        _, _, sp, tp = simulate(perp, v2, paper)
        _, _, ss, tsp = simulate(spot, v2, paper)
        P = {t for t, _ in sp if t >= EVAL_FROM}
        S = {t for t, _ in ss if t >= EVAL_FROM}
        both = P & S
        m = perp.merge(spot, on="ts", suffixes=("_p", "_s"))
        close_err = (m["close_s"] / m["close_p"] - 1).abs().median() * 100
        rp = [r for t, r in tp if t >= EVAL_FROM]
        rs = [r for t, r in tsp if t >= EVAL_FROM]
        rows.append((sym, len(P), len(S), len(both), len(P - S), len(S - P),
                     (len(both) / len(P) * 100) if P else float("nan"), close_err,
                     len(rp), sum(rp), len(rs), sum(rs), len(common)))
        _, _, _, t1 = simulate(perp, v1, paper)
        v1_rows.append((sym, len(t1)))

    lines += ["## 2. Sinyal Versi 2: spot (bot) vs perp (backtest)", "",
              "| Koin | Sinyal perp | Sinyal spot | Cocok | Hilang di spot | Palsu di spot "
              "| Kecocokan | Beda close (median) | Trade perp | ΣR perp | Trade spot | ΣR spot |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | "
                     f"**{r[6]:.1f}%** | {r[7]:.3f}% | {r[8]} | {r[9]:+.2f} | "
                     f"{r[10]} | {r[11]:+.2f} |")
    tot_p = sum(r[1] for r in rows)
    tot_b = sum(r[3] for r in rows)
    lines += ["", f"**Gabungan: {tot_b}/{tot_p} sinyal perp muncul juga di spot "
              f"({(tot_b / tot_p * 100) if tot_p else float('nan'):.1f}%).**", "",
              "Kecocokan = sinyal perp yang juga muncul di spot. \"Palsu di spot\" = "
              "sinyal yang hanya ada di spot, jadi tidak pernah ada di backtest. "
              "ΣR = R bersih komisi dari mesin paper repo ini, tanpa funding.", ""]

    lines += ["## 3. Cek jumlah trade Versi 1 vs setup V1 (perp, 2024-01..2026-08)", "",
              "| Koin | Repo ini | Setup V1 (s/d 19 Sep 2026) |", "|---|---:|---:|"]
    ref = {"ETHUSDT": 43, "BNBUSDT": 42, "XRPUSDT": 39, "DOGEUSDT": 37, "AVAXUSDT": 25}
    for sym, n in v1_rows:
        lines.append(f"| {sym} | {n} | {ref[sym]} |")
    lines += ["", "Repo ini boleh sedikit di bawah angka setup (September 2026 tidak ikut). "
              "Selisih besar berarti mesin repo ini tidak sama dengan mesin riset.", ""]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0 if rep_ok else 1


if __name__ == "__main__":
    sys.exit(main())
