"""Bar 4H live untuk kelima simbol, dari sumber yang bisa dijangkau GitHub Actions.

Diadaptasi dari Crypto-MEX (mex/datafeed.py), yang sudah berjalan di produksi.

Backtest memakai arsip Binance USD-M PERP. API perp Binance (fapi.binance.com)
menjawab HTTP 451 dari runner GitHub (IP AS diblokir), jadi forward test ini
memakai dua pengganti -- persis seperti MEX:

  1. data-api.binance.vision -- mirror publik Binance SPOT. Utama.
  2. api.gateio.ws           -- Gate.io perp. Cadangan otomatis.

Ini TRACKING ERROR NYATA terhadap backtest. Di MEX, kecocokan sinyal spot vs
perp terukur 94-97% untuk ETH/XRP/DOGE (dengan aturan MEX, bukan Sequence Snap).
Untuk Sequence Snap -- dan untuk BNB dan AVAX sama sekali -- belum diukur;
tools/measure_spot_vs_perp.py (workflow "Ukur spot vs perp") yang mengukurnya.
Sumber yang menjawab dicatat di setiap baris log supaya bisa dipisah saat evaluasi.

KENAPA 1.500 BAR, BUKAN 1.000
EMA200 punya ekor panjang. Sisa pengaruh nilai awal setelah k bar adalah
(1 - 2/201)^k: di 1.000 bar masih 0,005%, di 1.500 bar 0,00003%. Syarat #8
membandingkan close dengan EMA200 secara ketat, jadi di dekat persilangan beda
sekecil itu pun bisa membalik sinyal. Binance membatasi 1.000 bar per
permintaan, jadi diambil dua halaman.
"""
from . import compat  # noqa: F401
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd
import requests

BINANCE_SPOT = "https://data-api.binance.vision/api/v3/klines"
GATE_FUTURES = "https://api.gateio.ws/api/v4/futures/usdt/candlesticks"

UA = {"User-Agent": "Crypto-Sequence-Snap-forward-test/1.0 "
                    "(+github.com/daijobudesu69/Crypto-Sequence-Snap)"}

# Watchlist dikunci di sini -- satu-satunya sumber kebenaran. Label di CSV dan
# Telegram dibaca dari sini, jadi label tidak mungkin berbeda dari data yang
# benar-benar diunduh (pelajaran MEX: kunci `symbol` di config pernah hanya
# mengganti label sementara datanya tetap ETH).
SYMBOLS = ["ETHUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "AVAXUSDT"]
# Kontrak Gate.io perp untuk tiap simbol yang pernah dipertimbangkan -- termasuk
# kandidat yang belum masuk SYMBOLS, supaya tools/measure_spot_vs_perp.py bisa
# mengukurnya dengan pemetaan yang sama persis dengan yang akan dipakai bot.
GATE = {
    "ETHUSDT": "ETH_USDT",
    "BNBUSDT": "BNB_USDT",
    "XRPUSDT": "XRP_USDT",
    "DOGEUSDT": "DOGE_USDT",
    "AVAXUSDT": "AVAX_USDT",
    "TRXUSDT": "TRX_USDT",
    "XMRUSDT": "XMR_USDT",
    "NEARUSDT": "NEAR_USDT",
    "TAOUSDT": "TAO_USDT",
}
INTERVAL = "4h"
BAR = pd.Timedelta(INTERVAL)
N_BARS = 1500
MIN_BARS = 1000

_missing = [s for s in SYMBOLS if s not in GATE]
if _missing:
    raise RuntimeError(f"GATE tidak memetakan {_missing}; failover tidak ada")

# Tidak ada gunanya diulang: geo-block, simbol salah, request cacat selalu
# menjawab sama, dan mengulang 429 adalah cara mendapat ban 418 dari Binance.
NO_RETRY_STATUS = frozenset({400, 401, 403, 404, 418, 429, 451})


@dataclass
class Feed:
    df: pd.DataFrame
    source: str
    fetched_at: pd.Timestamp
    symbol: str


def _get(url, params, timeout=30, retries=3):
    last = None
    for i in range(retries):
        try:
            r = requests.get(url, params=params, timeout=timeout, headers=UA)
            if r.status_code in NO_RETRY_STATUS:
                raise RuntimeError(f"HTTP {r.status_code} (tidak diulang)")
            r.raise_for_status()
            return r.json()
        except RuntimeError:
            raise
        except Exception as e:  # noqa: BLE001
            last = e
            if i < retries - 1:
                time.sleep(1.5 * (i + 1))
    # Tipe saja: pesan exception requests memuat URL lengkap.
    raise RuntimeError(f"{url}: {type(last).__name__}")


def _binance_frame(raw) -> pd.DataFrame:
    df = pd.DataFrame(raw, columns=[
        "ot", "open", "high", "low", "close", "volume",
        "ct", "qv", "n", "tb", "tq", "ig"])
    return pd.DataFrame({
        "ts": pd.to_datetime(df["ot"].astype("int64"), unit="ms", utc=True),
        **{c: df[c].astype(float) for c in ("open", "high", "low", "close", "volume")},
    })


def _from_binance_spot(symbol, n=N_BARS):
    """Dua halaman: 1.000 bar terbaru, lalu sisanya mundur dari sana."""
    first = _get(BINANCE_SPOT, dict(symbol=symbol, interval=INTERVAL, limit=1000))
    if not first:
        raise RuntimeError("binance spot mirror tidak mengembalikan baris")
    frames = [_binance_frame(first)]
    rest = n - len(first)
    if rest > 0:
        end = int(first[0][0]) - 1
        older = _get(BINANCE_SPOT, dict(symbol=symbol, interval=INTERVAL,
                                        limit=min(rest, 1000), endTime=end))
        if older:
            frames.insert(0, _binance_frame(older))
    out = pd.concat(frames, ignore_index=True)
    return out.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)


GATE_PAGE = 1000   # bar per permintaan; Gate membatasi 2.000 titik per query


def gate_history(contract, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    """Bar 4H Gate.io perp dalam [start, end], diambil per halaman 1.000 bar.

    Gate menolak `limit` bila `from`/`to` diisi, jadi jumlah bar diatur lewat
    rentang waktu. Halaman kosong (sebelum kontrak listing) dilewati.
    """
    span = int(BAR.total_seconds())
    t0, t1 = int(start.timestamp()), int(end.timestamp())
    frames = []
    while t0 <= t1:
        hi = min(t0 + (GATE_PAGE - 1) * span, t1)
        raw = _get(GATE_FUTURES, {"contract": contract, "interval": INTERVAL,
                                  "from": t0, "to": hi})
        if raw:
            df = pd.DataFrame(raw)
            frames.append(pd.DataFrame({
                "ts": pd.to_datetime(df["t"].astype("int64"), unit="s", utc=True),
                "open": df["o"].astype(float), "high": df["h"].astype(float),
                "low": df["l"].astype(float), "close": df["c"].astype(float),
                "volume": df["v"].astype(float),
            }))
        t0 = hi + span
    if not frames:
        raise RuntimeError("gate.io tidak mengembalikan baris")
    out = pd.concat(frames, ignore_index=True)
    return out.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)


def _from_gate(contract, n=N_BARS):
    now = pd.Timestamp.now(tz="UTC")
    return gate_history(contract, now - n * BAR, now)


SOURCES = ["binance_spot_mirror", "gate_io_perp"]


def fetch(symbol: str, prefer: str | None = None) -> Feed:
    """Bar 4H yang sudah TUTUP untuk `symbol`. Sumber pertama yang lolos sanity_check menang."""
    if symbol not in GATE:
        raise RuntimeError(f"{symbol} tidak ada di watchlist")
    order = sorted(SOURCES, key=lambda s: s != prefer) if prefer else SOURCES
    errors = []
    for name in order:
        try:
            df = (_from_binance_spot(symbol) if name == "binance_spot_mirror"
                  else _from_gate(GATE[symbol]))
            df = drop_unclosed(df)
            sanity_check(df)
            return Feed(df=df, source=name, fetched_at=pd.Timestamp.now(tz="UTC"),
                        symbol=symbol)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{name}: {e}")
    raise RuntimeError(f"{symbol}: semua sumber data gagal -> " + " | ".join(errors))


def drop_unclosed(df: pd.DataFrame, now: pd.Timestamp | None = None) -> pd.DataFrame:
    """Hanya bar yang sudah tutup: bar yang buka di t tutup di t + BAR."""
    now = now or pd.Timestamp.now(tz="UTC")
    return df[df["ts"] + BAR <= now].reset_index(drop=True)


def sanity_check(df: pd.DataFrame, min_bars: int = MIN_BARS,
                 now: pd.Timestamp | None = None) -> None:
    """Tolak seri yang pendek, bolong, basi, atau cacat. Jangan pernah trading di atasnya."""
    if len(df) < min_bars:
        raise RuntimeError(f"hanya {len(df)} bar, butuh >= {min_bars} untuk EMA200")
    # Duplikat duluan: date_range().difference() membandingkan himpunan, jadi
    # timestamp ganda bersembunyi di balik himpunan yang tampak lengkap.
    dup = df["ts"].duplicated()
    if dup.any():
        raise RuntimeError(f"{int(dup.sum())} bar duplikat, pertama di {df['ts'][dup].iloc[0]}")
    gaps = pd.date_range(df["ts"].iloc[0], df["ts"].iloc[-1], freq=BAR).difference(
        pd.DatetimeIndex(df["ts"]))
    if len(gaps):
        raise RuntimeError(f"{len(gaps)} bar hilang, pertama di {gaps[0]}")
    now = now or pd.Timestamp.now(tz="UTC")
    age = now - df["ts"].iloc[-1]
    if age > 3 * BAR:
        raise RuntimeError(f"feed basi: bar tutup terbaru sudah {age}")
    bad = df[(df["high"] < df["low"]) | (df["high"] < df["open"]) | (df["high"] < df["close"])
             | (df["low"] > df["open"]) | (df["low"] > df["close"])
             | (df[["open", "high", "low", "close"]] <= 0).any(axis=1)]
    if len(bad):
        raise RuntimeError(f"{len(bad)} bar OHLC cacat, pertama di {bad['ts'].iloc[0]}")
    if not np.isfinite(df[["open", "high", "low", "close", "volume"]].to_numpy(float)).all():
        raise RuntimeError("ada nilai non-finite di OHLCV")
