"""Hitung ulang trade lama (engine <= 1.3.0) dengan biaya 1.4.0: slippage + funding.

Sampai 1.3.0 ledger paper mencatat fill = open/level persis, tanpa slippage dan
tanpa funding -- jadi R-nya tidak sebanding dengan backtest (yang memotong
keduanya). Alat ini menerapkan rumus yang SAMA dengan run_signal.py 1.4.0 ke
baris lama, supaya seluruh state/trades.csv memakai satu definisi R:

  entry  = open bar entry (harga_entry_aktual lama) + slippage
  qty    = 1R / (entry - stop)
  exit   = level/open (harga_exit_aktual lama)       - slippage
  funding Gate.io perp, jendela entry_bar < t <= exit_bar, notional = qty x close

Kolom asli lain (sinyal, stop, target, waktu, MAE/MFE) tidak disentuh. Baris yang
sudah punya funding_source dilewati, jadi aman dijalankan dua kali. Header ditulis
ulang ke TRADE_COLS 1.4.0 supaya ledger._rotate tidak mengarsipkan file ini.

Dipakai SEKALI, manual: python tools/restate_costs.py [--dry-run]
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import snap.compat  # noqa: F401,E402

import pandas as pd  # noqa: E402

from snap import datafeed, funding, ledger  # noqa: E402
from snap.config import load  # noqa: E402
from snap.strategy import Position, trade_result  # noqa: E402


def restate(row: dict, cfg: dict, feeds: dict) -> dict:
    sym = row["koin"]
    paper = cfg["paper"]
    tick = datafeed.TICK[sym]
    slip = paper["slippage_ticks"] * tick
    stop = float(row["stop_rencana"])
    open_raw = float(row["harga_entry_aktual"])
    exit_raw = float(row["harga_exit_aktual"])
    risk_usd = paper["capital_usd"] * paper["risk_pct"] / 100.0
    entry = open_raw + slip
    dist = entry - stop
    pos = Position(signal_id=row["signal_id"], signal_bar=row["waktu_sinyal_utc"],
                   entry_bar=row["waktu_entry_utc"], signal_close=float(row["close_bar0"]),
                   entry_price=entry, stop=stop, target=float(row["target_rencana"]),
                   qty=risk_usd / dist if dist > 0 else 0.0, risk_usd=risk_usd,
                   slip=slip, tick=tick, entry_open=open_raw)
    px = exit_raw - slip

    if sym not in feeds:
        feeds[sym] = datafeed.fetch(sym).df
    df = feeds[sym]
    ts = pd.DatetimeIndex(df["ts"])
    exit_bar = pd.Timestamp(row["waktu_exit_utc"])
    if pd.Timestamp(pos.entry_bar) < ts[0]:
        raise RuntimeError(f"{sym}: entry {pos.entry_bar} di luar jendela data")
    rates = funding.fetch_rates(sym, pd.Timestamp(pos.entry_bar), exit_bar)
    fund = funding.charge(rates, pos.entry_bar, exit_bar, ts, df["close"].to_numpy(float),
                          pos.qty)
    res = trade_result(pos, px, paper["commission_pct"], funding_usd=fund["usd"])
    old_r = row["R_realisasi"]
    return {
        **row,
        "harga_entry_aktual": round(entry, 10), "qty": round(pos.qty, 8),
        "notional": round(res["notional_usd"], 4),
        "dilewati_min_notional": res["notional_usd"] < ledger.min_notional(sym),
        "harga_exit_aktual": round(px, 10),
        "slippage_entry_tick": float(paper["slippage_ticks"]),
        "slippage_exit_tick": float(paper["slippage_ticks"]),
        "funding_dibayar_usd": round(fund["usd"], 6),
        "pnl_usd": round(res["pnl_usd"], 4), "R_realisasi": round(res["R_net"], 4),
        "R_kotor": round(res["R_gross"], 4),
        "entry_vs_close_bar0_pct": round((entry / pos.signal_close - 1) * 100, 4),
        "funding_R": round(res["funding_R"], 6), "funding_n": fund["n"],
        "funding_source": funding.SOURCE, "tick_size": tick,
        "komisi_R": round(res["fee_R"], 6),
        "catatan": (f"paper: fill = open/level, slippage {paper['slippage_ticks']}/"
                    f"{paper['slippage_ticks']} tick; funding {fund['n']}x dari "
                    f"{funding.SOURCE}; DIHITUNG ULANG 1.4.0 dari rekaman "
                    f"{row.get('engine_version') or '?'} (R lama {old_r})"),
    }


def main() -> int:
    dry = "--dry-run" in sys.argv
    cfg = load()
    rows = ledger.read_rows(ledger.TRADES)
    if not rows:
        print("[restate] trades.csv kosong")
        return 0
    feeds, out, n = {}, [], 0
    for r in rows:
        if r.get("funding_source"):
            out.append(r)
            continue
        new = restate(r, cfg, feeds)
        n += 1
        print(f"[restate] #{r['no']} {r['koin']} {r['signal_id']}: R {r['R_realisasi']} -> "
              f"{new['R_realisasi']}  (funding {new['funding_n']}x ${new['funding_dibayar_usd']:+.4f}"
              f" = {new['funding_R']:+.4f} R, pnl {r['pnl_usd']} -> {new['pnl_usd']})")
        out.append(new)
    if dry or not n:
        print(f"[restate] {n} baris {'akan ' if dry else ''}dihitung ulang"
              + (" (dry-run, file tidak diubah)" if dry else ""))
        return 0
    tmp = ledger.TRADES + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=ledger.TRADE_COLS, extrasaction="ignore")
        w.writeheader()
        for r in out:
            w.writerow({k: ("" if r.get(k) is None else r.get(k, "")) for k in ledger.TRADE_COLS})
    os.replace(tmp, ledger.TRADES)
    print(f"[restate] {n} baris dihitung ulang, header -> TRADE_COLS 1.4.0")
    return 0


if __name__ == "__main__":
    sys.exit(main())
