"""Funding perp untuk ledger paper -- supaya R forward test sebanding dengan backtest.

Backtest (riset src/funding.py, p7_versi_forward.py) memotong tiap trade dengan
funding Binance USD-M yang benar-benar dibayar:

  biaya_usd = sum( rate_t x qty x close bar 4H yang memuat t )
              untuk tiap pembayaran t dengan  entry_bar < t <= exit_bar
  funding_R = biaya_usd / 1R            (positif = long membayar)

Rumus dan jendela di sini SAMA. Bedanya hanya sumber tarif:

  fapi.binance.com menjawab HTTP 451 dari runner GitHub, jadi tarif diambil dari
  riwayat funding Gate.io perp (kontrak di datafeed.GATE) -- bursa lain, pasar
  sejenis. Ini tracking error, sama seperti candle; sumbernya dicatat di tiap
  baris (`funding_source`). Gate membayar tiap 8 jam (00/08/16 UTC), Binance
  untuk koin ini juga 8 jam. Riwayat Gate bisa diambil MUNDUR (sampai 180 hari),
  jadi run yang telat atau terlewat tetap mendapat angka lengkap -- tidak perlu
  perekam yang harus hidup tepat di jam settlement.

Konvensi tanda sama dengan Binance: rate > 0 -> long membayar short.
"""
from . import compat  # noqa: F401
import time

import numpy as np
import pandas as pd
import requests

from . import datafeed

GATE_FUNDING = "https://api.gateio.ws/api/v4/futures/usdt/funding_rate"
SOURCE = "gate_io_perp"
MAX_LOOKBACK = pd.Timedelta(days=179)   # Gate menolak `from` > 180 hari lalu


class Unavailable(RuntimeError):
    """Riwayat funding tidak bisa diambil saat ini."""


def fetch_rates(symbol: str, start: pd.Timestamp, end: pd.Timestamp,
                retries: int = 3) -> list[tuple[pd.Timestamp, float]]:
    """[(waktu bayar, rate)] Gate.io untuk start <= t <= end (+ sedikit kelonggaran).

    Waktu dibulatkan ke menit: Gate kadang mencatat 16:00:01, dan satu detik itu
    tidak boleh memindahkan pembayaran ke sisi lain batas jendela.
    """
    contract = datafeed.GATE[symbol]
    now = pd.Timestamp.now(tz="UTC")
    lo = max(pd.Timestamp(start) - pd.Timedelta("1h"), now - MAX_LOOKBACK)
    hi = pd.Timestamp(end) + pd.Timedelta("1h")
    params = {"contract": contract, "from": int(lo.timestamp()),
              "to": int(hi.timestamp()), "limit": 1000}
    last = None
    for k in range(retries):
        try:
            r = requests.get(GATE_FUNDING, params=params, headers=datafeed.UA, timeout=20)
            r.raise_for_status()
            rows = r.json()
            if not isinstance(rows, list):
                raise ValueError(f"jawaban tak terduga: {str(rows)[:120]}")
            out = []
            for x in rows:
                t = pd.Timestamp(int(x["t"]), unit="s", tz="UTC").floor("min")
                out.append((t, float(x["r"])))
            return sorted(set(out))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (k + 1))
    raise Unavailable(f"{symbol} funding Gate gagal: {type(last).__name__}: {last}")


def charge(rates, entry_bar, exit_bar, ts: pd.DatetimeIndex, closes, qty: float) -> dict:
    """Funding yang dibayar posisi long ini. Murni, tanpa jaringan -- bisa dites.

    Jendela  entry_bar < t <= exit_bar  (waktu BUKA bar, seperti backtest): bayar
    tepat di open bar entry tidak kena (posisi baru dibuka saat itu), bayar di
    open bar exit kena (posisi masih dipegang). Notional dihitung ulang tiap
    pembayaran dari close bar 4H yang memuat t, bukan harga entry.
    """
    a, b = pd.Timestamp(entry_bar), pd.Timestamp(exit_bar)
    closes = np.asarray(closes, float)
    usd, n, paid = 0.0, 0, []
    for t, rate in rates:
        if not (a < t <= b):
            continue
        j = int(ts.searchsorted(t, side="right")) - 1
        if j < 0:
            continue
        px = float(closes[j])
        cost = rate * qty * px
        usd += cost
        n += 1
        paid.append({"t": t.isoformat(), "rate": rate, "px": px, "usd": round(cost, 6)})
    return {"usd": usd, "n": n, "payments": paid}
