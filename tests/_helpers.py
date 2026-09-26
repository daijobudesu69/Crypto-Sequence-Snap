"""Alat bantu tes: data sintetis dan runner kecil tanpa pytest."""
import os
import sys
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import snap.compat  # noqa: F401,E402

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


def frame(rows, end=None):
    """rows = [(open, high, low, close), ...] -> DataFrame 4H berurutan.

    `end` = open time bar terakhir. Default: bar yang paling baru tutup.
    """
    if end is None:
        end = pd.Timestamp.now(tz="UTC").floor("4h") - pd.Timedelta("4h")
    ts = pd.date_range(end=end, periods=len(rows), freq="4h", tz="UTC")
    o, h, l, c = (np.array(x, float) for x in zip(*rows))
    return pd.DataFrame({"ts": ts, "open": o, "high": h, "low": l, "close": c,
                         "volume": np.full(len(rows), 100.0)})


def uptrend_with_pattern(n=400, red_at=392, pump_at=None, pump=1.10):
    """Seri naik pelan, semua lilin hijau, kecuali SATU lilin merah di `red_at`.

    Hasilnya tepat satu pola Sequence Snap: bar 0 = red_at + 5. Close selalu di
    atas EMA200 dan RSI naik di bar 0, jadi Versi 2 menembak di sana saja.
    `pump_at` membuat satu lilin dengan high melonjak (untuk menguji target).
    """
    rows, prev = [], 100.0
    for i in range(n):
        o = prev
        if i == red_at:
            c = o * 0.99
            rows.append((o, o * 1.001, c * 0.998, c))
        else:
            c = o * 1.001
            hi = c * (pump if i == pump_at else 1.001)
            rows.append((o, hi, o * 0.999, c))
        prev = c
    return rows


def run_all(module_globals) -> int:
    tests = [(k, v) for k, v in sorted(module_globals.items())
             if k.startswith("test_") and callable(v)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ok   {name}")
        except Exception:  # noqa: BLE001
            failed += 1
            print(f"  FAIL {name}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} lulus")
    return 1 if failed else 0
