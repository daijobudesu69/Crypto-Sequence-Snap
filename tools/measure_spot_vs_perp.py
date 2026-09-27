"""Pilih sumber data per koin: mana yang paling dekat dengan Binance FUTURES.

Bot tidak bisa membaca API futures Binance dari runner GitHub (HTTP 451). Dua
pengganti yang bisa dijangkau:

  spot  -- data-api.binance.vision, Binance SPOT (bursa sama, pasar beda)
  gate  -- api.gateio.ws, Gate.io PERP (pasar sama jenisnya, bursa beda)

Keduanya diadu dengan arsip resmi Binance USD-M perp (data.binance.vision),
bar demi bar, per koin. "Real-time" dalam arti harfiah tidak bisa diukur dari
runner -- justru karena futures Binance yang diblokir -- jadi kedekatan
terkini diukur di 90 hari terakhir arsip.

ATURAN PILIH (ditetapkan sebelum hasil dilihat):
  1. Sumber dengan kecocokan SINYAL tertinggi, diukur sebagai
     cocok / (sinyal perp + sinyal palsu). Yang diperdagangkan adalah sinyal,
     bukan harga; di MEX, Gate punya harga lebih dekat tapi sinyal lebih jauh.
  2. Seri (beda < 1 poin persen) -> beda harga close 90 hari terakhir terkecil.
  3. Sumber yang tidak punya data koin itu (mis. XMR di spot) gugur.

Juga dua cek replikasi terhadap Report (mesin repo ini = mesin riset):
  - Report Bagian 3: sinyal ETHUSDT 9 Sep 2024 08:00 UTC (Versi 1)
  - jumlah trade Versi 1 per koin watchlist awal vs setup V1

Keluaran: docs/SPOT_VS_PERP.md dan ringkasan di stdout.
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
from snap.datafeed import BAR, GATE, gate_history  # noqa: E402
from snap.strategy import compute_features, step, trade_result  # noqa: E402

BASE = "https://data.binance.vision/data"
START, END = "2024-01", "2026-08"
EVAL_FROM = pd.Timestamp("2024-07-01", tz="UTC")
WARMUP_BARS = 1000                 # EMA200: sisa pengaruh nilai awal ~0,005%
RECENT = pd.Timedelta("90D")
CACHE = ".cache/klines"
OUT = "docs/SPOT_VS_PERP.md"

COINS = ["ETHUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "AVAXUSDT",
         "TRXUSDT", "XMRUSDT", "NEARUSDT", "TAOUSDT"]
V1_REF = {"ETHUSDT": 43, "BNBUSDT": 42, "XRPUSDT": 39, "DOGEUSDT": 37, "AVAXUSDT": 25}


# --------------------------------------------------------------------------- #
# data
# --------------------------------------------------------------------------- #
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


def binance(market: str, sym: str) -> pd.DataFrame | None:
    frames = [d for m in _months() if (d := _download(market, sym, m)) is not None]
    if not frames:
        return None
    df = pd.concat(frames, ignore_index=True)
    return df.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)


def gate(sym: str) -> tuple[pd.DataFrame | None, str]:
    end = pd.Period(END, freq="M").end_time.tz_localize("UTC").floor("4h")
    try:
        return gate_history(GATE[sym], pd.Timestamp(f"{START}-01", tz="UTC"), end), ""
    except Exception as e:  # noqa: BLE001
        return None, str(e)[:120]


# --------------------------------------------------------------------------- #
# mesin
# --------------------------------------------------------------------------- #
def simulate(df: pd.DataFrame, params, paper: dict):
    """Mesin forward test yang SAMA, di seluruh sejarah. -> (f, ts, sinyal, trade)."""
    f = compute_features(df, params)
    ts = pd.DatetimeIndex(df["ts"])
    pos = pending = None
    signals, trades = [], []
    for i in range(len(df)):
        pos, pending, events = step(f, ts, i, params, pos, pending,
                                    paper["capital_usd"], paper["risk_pct"])
        for ev in events:
            if ev["event"] == "SIGNAL":
                signals.append((ts[i], ev["pending"]))
            elif ev["event"] == "EXIT":
                res = trade_result(ev["pos"], ev["exit_price"], paper["commission_pct"])
                trades.append((pd.Timestamp(ev["pos"].signal_bar), res["R_net"]))
    return f, ts, signals, trades


def compare(perp: pd.DataFrame, alt: pd.DataFrame, v2, paper, eval_from) -> dict:
    """Satu sumber alternatif vs perp Binance: harga dan sinyal, di bar yang sama."""
    m = perp.merge(alt, on="ts", suffixes=("_p", "_a"))
    m = m[m["ts"] >= eval_from]
    rec = m[m["ts"] >= m["ts"].max() - RECENT]

    def err(frame, col):
        return float((frame[f"{col}_a"] / frame[f"{col}_p"] - 1).abs().median() * 100)

    # Sinyal dihitung di seri masing-masing (EMA dan RSI butuh riwayat sendiri),
    # lalu dibandingkan hanya di rentang yang dimiliki keduanya.
    lo, hi = max(eval_from, alt["ts"].min() + WARMUP_BARS * BAR), perp["ts"].max()
    _, _, sp, _ = simulate(perp, v2, paper)
    _, _, sa, ta = simulate(alt, v2, paper)
    P = {t for t, _ in sp if lo <= t <= hi}
    A = {t for t, _ in sa if lo <= t <= hi}
    both = P & A
    union = len(P) + len(A - P)
    return {
        "bars": len(m), "close_err": err(m, "close"), "hl_err": (err(m, "high") + err(m, "low")) / 2,
        "close_err_90d": err(rec, "close") if len(rec) else float("nan"),
        "perp": len(P), "alt": len(A), "match": len(both),
        "missed": len(P - A), "false": len(A - P),
        "agree": (len(both) / union * 100) if union else float("nan"),
        "recall": (len(both) / len(P) * 100) if P else float("nan"),
        "sumR": sum(r for t, r in ta if lo <= t <= hi),
        "ntr": sum(1 for t, _ in ta if lo <= t <= hi),
        "from": lo,
    }


def pick(res: dict) -> str:
    """Aturan pilih di docstring modul. `res` = {nama_sumber: hasil compare | None}."""
    ok = {k: v for k, v in res.items() if v and np.isfinite(v["agree"])}
    if not ok:
        return "-"
    best = max(ok.values(), key=lambda v: v["agree"])["agree"]
    tied = {k: v for k, v in ok.items() if best - v["agree"] < 1.0}
    return min(tied, key=lambda k: (tied[k]["close_err_90d"]
                                    if np.isfinite(tied[k]["close_err_90d"]) else 9e9))


# --------------------------------------------------------------------------- #
def main() -> int:
    cfg = load()
    v2, paper = cfg["params"], cfg["paper"]
    v1 = replace(v2, use_trend_filter=False)
    L = ["# Sumber data per koin — kedekatan dengan Binance futures", "",
         f"Diukur {pd.Timestamp.now(tz='UTC'):%Y-%m-%d %H:%M} UTC oleh "
         "`tools/measure_spot_vs_perp.py`. Acuan: arsip resmi Binance USD-M perp "
         f"(data.binance.vision), {START} .. {END}. Sinyal dibandingkan sejak "
         f"{EVAL_FROM:%Y-%m-%d} atau {WARMUP_BARS} bar setelah data sumber mulai "
         "(pemanasan EMA200), mana yang lebih akhir.", ""]

    # ── 1. Replikasi Report Bagian 3 ───────────────────────────────────────
    eth = binance("perp", "ETHUSDT")
    f1, ts1, sig1, _ = simulate(eth, v1, paper)
    target_bar = pd.Timestamp("2024-09-09 08:00", tz="UTC")
    hit = [p for t, p in sig1 if t == target_bar]
    i = int(ts1.get_loc(target_bar))
    rep_ok = (bool(hit) and abs(hit[0]["stop"] - 2238.88) < 1e-6
              and abs(hit[0]["target"] - 2426.93) < 0.01
              and abs(f1["rsi"][i] - 48.52) < 0.01 and abs(f1["rsi_prev"][i] - 48.33) < 0.01)
    L += ["## 1. Replikasi contoh Report Bagian 3 (ETHUSDT perp, Versi 1)", "",
          "| | Report | Repo ini |", "|---|---:|---:|",
          f"| Sinyal 2024-09-09 08:00 UTC | ada | {'ada' if hit else '**TIDAK ADA**'} |",
          f"| RSI bar 0 / bar 1 | 48,52 / 48,33 | {f1['rsi'][i]:.2f} / {f1['rsi_prev'][i]:.2f} |",
          f"| Stop / target | 2238,88 / 2426,93 | "
          f"{hit[0]['stop'] if hit else float('nan'):.2f} / "
          f"{hit[0]['target'] if hit else float('nan'):.2f} |",
          "", f"**Hasil: {'COCOK' if rep_ok else 'TIDAK COCOK — jangan mulai forward test'}**", ""]

    # ── 2. Per koin, per sumber ────────────────────────────────────────────
    rows, picks, v2stats, v1rows, notes = [], {}, [], [], []
    for sym in COINS:
        print(f"[measure] {sym} ...", flush=True)
        perp = binance("perp", sym)
        if perp is None:
            notes.append(f"- **{sym}**: tidak ada arsip Binance futures — tidak bisa diukur.")
            picks[sym] = "-"
            continue
        eval_from = max(EVAL_FROM, perp["ts"].min() + WARMUP_BARS * BAR)
        spot = binance("spot", sym)
        g, gerr = gate(sym)
        res = {"binance_spot_mirror": compare(perp, spot, v2, paper, eval_from) if spot is not None else None,
               "gate_io_perp": compare(perp, g, v2, paper, eval_from) if g is not None else None}
        if spot is None:
            notes.append(f"- **{sym}**: tidak ada data Binance spot (pasangan spot tidak/berhenti diperdagangkan).")
        if g is None:
            notes.append(f"- **{sym}**: Gate.io gagal — {gerr}")
        picks[sym] = pick(res)
        for name, r in res.items():
            if r is None:
                continue
            rows.append((sym, name, r, picks[sym] == name))
        _, _, _, tp = simulate(perp, v2, paper)
        rs = [r for t, r in tp if t >= eval_from]
        months = (perp["ts"].max() - eval_from).days / 30.44
        v2stats.append((sym, len(rs), sum(rs), (sum(rs) / len(rs)) if rs else 0.0,
                        (sum(1 for r in rs if r > 0) / len(rs) * 100) if rs else 0.0,
                        len(rs) / months if months > 0 else 0.0, eval_from))
        if sym in V1_REF:
            _, _, _, t1 = simulate(perp, v1, paper)
            v1rows.append((sym, len(t1)))

    L += ["## 2. Kedekatan tiap sumber dengan Binance futures", "",
          "| Koin | Sumber | Beda close | Beda close 90 hr | Beda high/low | Sinyal perp | "
          "Cocok | Hilang | Palsu | **Kecocokan** | Trade | ΣR (sumber ini) | Dipilih |",
          "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|"]
    for sym, name, r, chosen in rows:
        short = "spot Binance" if name == "binance_spot_mirror" else "Gate perp"
        L.append(f"| {sym} | {short} | {r['close_err']:.3f}% | {r['close_err_90d']:.3f}% | "
                 f"{r['hl_err']:.3f}% | {r['perp']} | {r['match']} | {r['missed']} | {r['false']} | "
                 f"**{r['agree']:.1f}%** | {r['ntr']} | {r['sumR']:+.2f} | {'✅' if chosen else ''} |")
    L += ["", "Kecocokan = cocok ÷ (sinyal perp + sinyal palsu): sinyal yang hilang DAN "
          "sinyal yang tidak pernah ada di backtest sama-sama dihitung sebagai meleset. "
          "Beda = median selisih absolut per bar terhadap Binance futures.", ""]
    if notes:
        L += notes + [""]
    L += ["### Pilihan", "", "```python",
          "PRIMARY = {"] + [f'    "{s}": "{p}",' for s, p in picks.items()] + ["}", "```", ""]

    # ── 3. V2 di Binance futures, per koin ─────────────────────────────────
    L += ["## 3. Versi 2 di Binance futures, per koin (acuan kasar, BUKAN validasi)", "",
          "| Koin | Sejak | Trade | Trade/bulan | Win rate | Expectancy | ΣR |",
          "|---|---|---:|---:|---:|---:|---:|"]
    for sym, n, sr, ex, wr, pm, ef in v2stats:
        L.append(f"| {sym} | {ef:%Y-%m-%d} | {n} | {pm:.2f} | {wr:.0f}% | {ex:+.3f} R | {sr:+.2f} |")
    L += ["", "Periode ini tumpang tindih dengan periode yang dipakai membangun strategi "
          "(2024–2026), jadi angkanya batas atas yang optimis. TRX, XMR, NEAR, TAO "
          "ditambahkan setelah riset; angka mereka di sini **tidak boleh** dipakai "
          "untuk memilih atau membuang koin — itu data snooping.", ""]

    # ── 4. Jumlah trade V1 vs setup V1 ─────────────────────────────────────
    L += ["## 4. Cek jumlah trade Versi 1 vs setup V1 (perp, 2024-01..2026-08)", "",
          "| Koin | Repo ini | Setup V1 (s/d 19 Sep 2026) |", "|---|---:|---:|"]
    for sym, n in v1rows:
        L.append(f"| {sym} | {n} | {V1_REF[sym]} |")
    L += ["", "Boleh sedikit di bawah angka setup (September 2026 tidak ikut).", ""]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("\n".join(L))
    return 0 if rep_ok else 1


if __name__ == "__main__":
    sys.exit(main())
