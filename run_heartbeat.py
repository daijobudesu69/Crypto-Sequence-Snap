"""Heartbeat harian. Tepat satu pesan per hari, ada sinyal atau tidak.

Tugasnya menjawab "bot ini masih jalan?" tanpa pernah tertukar dengan sinyal,
sekaligus menghitung progres forward test dan memeriksa aturan berhenti.
Dipanggil dari loop pemantau tiap 10 menit; 143 dari 144 panggilan berhenti
di _due() sebelum menyentuh jaringan.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snap.compat  # noqa: F401,E402

import pandas as pd  # noqa: E402

from snap import datafeed, ledger, notify, stats  # noqa: E402
from snap.config import ENGINE_VERSION, load  # noqa: E402

STATE = "state/position.json"
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
SHA = os.environ.get("GITHUB_SHA", "")[:8]

# 00:00 UTC = 07:00 WIB.
TARGET_UTC = os.environ.get("SNAP_HEARTBEAT_UTC", "00:00")


def _due(st) -> tuple[bool, str]:
    if os.environ.get("SNAP_FORCE_HEARTBEAT") == "1":
        return True, "dipaksa (SNAP_FORCE_HEARTBEAT=1)"
    now = pd.Timestamp.now(tz="UTC")
    today = now.strftime("%Y-%m-%d")
    if st.get("last_heartbeat_date") == today:
        return False, f"sudah dikirim hari ini ({today})"
    try:
        hh, mm = (int(x) for x in TARGET_UTC.split(":"))
        target = now.normalize() + pd.Timedelta(hours=hh, minutes=mm)
    except Exception:  # noqa: BLE001
        target = now.normalize()
    if now < target:
        return False, f"belum waktunya (target {TARGET_UTC} UTC)"
    return True, f"jatuh tempo untuk {today}"


def _last30():
    cut = pd.Timestamp.now(tz="UTC") - pd.Timedelta("30D")
    n_sig = n_tr = 0
    for r in ledger.read_rows(ledger.EVENTS):
        try:
            if r.get("event") == "SIGNAL" and pd.Timestamp(r["bar_time_utc"]) >= cut:
                n_sig += 1
        except Exception:  # noqa: BLE001
            continue
    for r in ledger.read_rows(ledger.TRADES):
        try:
            if pd.Timestamp(r["waktu_exit_utc"]) >= cut:
                n_tr += 1
        except Exception:  # noqa: BLE001
            continue
    return n_sig, n_tr


def main():
    cfg = load()
    try:
        st = ledger.read_json(STATE, {})
    except ledger.StateCorrupt as e:
        notify.send(notify.alert_message("state rusak", e))
        print(f"[heartbeat] {e}")
        return 1

    due, why = _due(st)
    if not due:
        print(f"[heartbeat] dilewati -- {why}")
        return 0
    print(f"[heartbeat] {why}")

    slots = st.get("symbols") or {}
    positions, down, sources = {}, [], []
    for sym in cfg["symbols"]:
        pos = (slots.get(sym) or {}).get("position")
        last_close = None
        try:
            feed = datafeed.fetch(sym)
            sources.append(feed.source)
            last_close = float(feed.df["close"].iloc[-1])
        except Exception as e:  # noqa: BLE001
            down.append(sym)
            print(f"[heartbeat] {sym}: {e}")
        positions[sym] = {"position": pos, "last_close": last_close}

    uniq = sorted(set(sources))
    bars = [v.get("last_bar") for v in slots.values() if v.get("last_bar")]
    n_sig, n_tr = _last30()
    s = {
        "now": pd.Timestamp.now(tz="UTC").isoformat(),
        "last_bar": max(bars) if bars else None,
        "source": ",".join(uniq) if uniq else "-",
        "positions": positions, "symbols_down": down,
        "outbox_pending": len(st.get("outbox", [])),
        "signals_30d": n_sig, "trades_30d": n_tr,
        "summary": stats.summarize(ledger.read_rows(ledger.TRADES),
                                   cfg["paper"]["capital_usd"]),
    }
    ok = notify.send(notify.heartbeat_message(s))
    # Hari ini baru diklaim kalau pesannya benar-benar terkirim; kalau gagal,
    # tick 10 menit berikutnya mencoba lagi.
    if ok or not notify.configured():
        st["last_heartbeat_date"] = pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d")
        ledger.write_json(STATE, st)
    else:
        print("[heartbeat] gagal terkirim; hari ini belum ditandai, akan dicoba lagi")

    ledger.log_run({
        "run_at_utc": s["now"], "status": "heartbeat" if not down else "heartbeat_data_error",
        "data_source": s["source"], "last_bar_utc": s["last_bar"] or "",
        "open_positions": ",".join(k.replace("USDT", "") for k, v in positions.items()
                                   if v["position"]),
        "telegram": "sent" if ok else ("not_configured" if not notify.configured() else "failed"),
        "engine_version": ENGINE_VERSION, "run_id": RUN_ID, "commit_sha": SHA,
        "message": ("simbol gagal: " + ",".join(down)) if down else "",
    })
    # Feed yang rusak tidak boleh menggagalkan job: heartbeat paling berharga
    # justru di hari ada yang rusak.
    return 0


if __name__ == "__main__":
    sys.exit(main())
