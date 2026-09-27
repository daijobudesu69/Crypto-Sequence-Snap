"""Driver sinyal. Dipanggil tiap ~10 menit dan ~45 detik setelah tiap lilin 4H tutup.

Diadaptasi dari Crypto-MEX (run_signal.py). Pola intinya dipertahankan karena
tiap bagiannya lahir dari insiden nyata di MEX:

* DIGERAKKAN OLEH BAR, BUKAN JAM. Tiap run bertanya "bar tutup mana yang belum
  saya proses?" lalu memprosesnya berurutan. Run yang telat atau terlewat
  mengejar di run berikutnya, dan bar yang sudah diproses dilewati -- jadi
  aman dipanggil sesering apa pun, pesan tidak pernah berulang.

* ANTRE-LALU-KIRIM. Tiap pesan masuk state["outbox"] dulu dan baru dihapus
  setelah Telegram menerimanya; kuncinya disimpan di state["sent_ids"]. Kirim
  yang gagal dicoba ulang di run berikutnya, dan run yang mati setelah kirim
  tapi sebelum commit tidak mengirim dua kali saat diputar ulang.

* last_bar HANYA MAJU. Feed cadangan bisa berhenti satu-dua bar di belakang
  yang utama; memundurkan last_bar akan memutar ulang bar yang sudah dipakai
  step(), dan pending yang diputar ulang terisi di harga yang salah.
"""
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import snap.compat  # noqa: F401,E402

import pandas as pd  # noqa: E402

from snap import datafeed, ledger, notify, state, stats  # noqa: E402
from snap.config import ENGINE_VERSION, load  # noqa: E402
from snap.strategy import (compute_features, pos_from_dict, pos_to_dict,  # noqa: E402
                           step, trade_result)

STATE = "state/position.json"
RUN_ID = os.environ.get("GITHUB_RUN_ID", "local")
SHA = os.environ.get("GITHUB_SHA", "")[:8]

# Sinyal masih layak dibaca sampai entry-nya basi. Entry di open berikutnya, dan
# sinyal yang datang berjam-jam kemudian tidak bisa diikuti -- tapi tetap dicatat.
SIGNAL_TTL = pd.Timedelta(os.environ.get("SNAP_SIGNAL_TTL", "4h"))
# ENTRY dan EXIT adalah catatan, bukan instruksi: sehari masih layak dibaca.
CONFIRM_TTL = pd.Timedelta("24h")
SENT_IDS_KEPT = 300
IDLE_LOG_EVERY = pd.Timedelta(os.environ.get("SNAP_IDLE_LOG_EVERY", "60min"))

QUEUE_NOTE = ("\n\n⚠️ <b>Tertahan {mins:.0f} menit di antrean kirim</b> "
              "— cek harga masih di antara stop dan target.")


def _fingerprint(st) -> str:
    """Isi state tanpa updated_at, supaya file hanya ditulis ulang kalau ada yang berubah."""
    return json.dumps({k: v for k, v in st.items() if k != "updated_at"},
                      sort_keys=True, default=str)


def _should_log_run(run) -> bool:
    """Run yang memproses bar, memunculkan event, atau gagal SELALU dicatat;
    run kosong dibatasi supaya runs.csv tidak bertambah 144 baris sehari."""
    if run["bars_processed"] or run["events_emitted"] or run["status"] != "ok":
        return True
    if os.environ.get("SNAP_QUIET_IDLE") != "1":
        return True
    last = ledger.last_run_at()
    if not last:
        return True
    try:
        return pd.Timestamp.now(tz="UTC") - pd.Timestamp(last) >= IDLE_LOG_EVERY
    except Exception:  # noqa: BLE001
        return True


def _delay_minutes(bar_ts) -> float:
    """Menit antara lilin tutup dan pesan dibuat."""
    closed = pd.Timestamp(bar_ts) + datafeed.BAR
    return max(0.0, (pd.Timestamp.now(tz="UTC") - closed).total_seconds() / 60.0)


def _queued_minutes(m) -> float:
    try:
        return max(0.0, (pd.Timestamp.now(tz="UTC")
                         - pd.Timestamp(m["queued_at"])).total_seconds() / 60.0)
    except Exception:  # noqa: BLE001
        return 0.0


def _mark_unnotified(st, m) -> None:
    """SIGNAL yang dibuang dari outbox tidak pernah terbaca -- bungkam ENTRY/EXIT-nya.

    Tanpa ini, pesan pertama yang diterima pengguna adalah "ENTRY TERCATAT" untuk
    sinyal yang tidak pernah ia lihat (insiden MEX).
    """
    sl = (st.get("symbols") or {}).get(m.get("symbol"))
    if not sl:
        return
    for name in ("pending", "position"):
        held = sl.get(name)
        if held and held.get("signal_id") == m.get("signal_id"):
            held["notified"] = False


def _flush(st) -> tuple[int, int, int]:
    """Coba kirim semua yang antre. Mengembalikan (terkirim, gagal, dibuang)."""
    now = pd.Timestamp.now(tz="UTC")
    sent_ids = st.setdefault("sent_ids", [])
    keep, sent, failed, dropped = [], 0, 0, 0
    orphaned = set()
    for m in st.get("outbox", []):
        if m["key"] in sent_ids:
            continue
        if now > pd.Timestamp(m["expires_at"]):
            dropped += 1
            if m.get("kind") == "SIGNAL":
                _mark_unnotified(st, m)
                orphaned.add((m.get("symbol"), m.get("signal_id")))
            print(f"[outbox] {m['key']} basi sebelum sempat terkirim, dibuang")
            continue
        if (m.get("symbol"), m.get("signal_id")) in orphaned:
            dropped += 1
            continue
        text = m["text"]
        waited = _queued_minutes(m)
        if m.get("kind") == "SIGNAL" and waited > 10:
            text += QUEUE_NOTE.format(mins=waited)
        # Tanpa token: cetak dan anggap beres, supaya pipa bisa diuji sebelum bot
        # Telegram ada. Mengantre di sini akan membuat setiap run merah selamanya.
        if not notify.configured():
            notify.send(text)
            sent_ids.append(m["key"])
            sent += 1
            continue
        if notify.send(text):
            sent_ids.append(m["key"])
            sent += 1
        else:
            m["attempts"] = m.get("attempts", 0) + 1
            keep.append(m)
            failed += 1
            print(f"[outbox] {m['key']} gagal terkirim (percobaan ke-{m['attempts']})")
    st["outbox"] = keep
    del sent_ids[:-SENT_IDS_KEPT]
    return sent, failed, dropped


def _summary(cfg) -> dict:
    return stats.summarize(ledger.read_rows(ledger.TRADES), cfg["paper"]["capital_usd"])


def _handle(ev, symbol, source, cfg, st) -> list:
    """Catat satu event dan kembalikan pesan yang harus diantre (0 atau 1)."""
    kind, bar = ev["event"], ev["bar"]
    ctx = ev.get("ctx") or {}
    delay = _delay_minutes(bar)
    now = pd.Timestamp.now(tz="UTC")
    base = {
        "logged_at_utc": now.isoformat(), "event": kind, "symbol": symbol,
        "bar_time_utc": bar.isoformat(), "data_source": source,
        "engine_version": ENGINE_VERSION, "run_id": RUN_ID, "commit_sha": SHA,
        "signal_to_send_minutes": round(delay, 1), **ctx,
    }

    def msg(signal_id, text, expires_at):
        key = state.dedup_key(kind, symbol, signal_id)
        if key in st.get("sent_ids", []):
            print(f"[dedup] {key} sudah pernah terkirim, tidak diulang")
            return []
        return [{"key": key, "kind": kind, "signal_id": signal_id, "symbol": symbol,
                 "text": text, "expires_at": str(expires_at),
                 "queued_at": now.isoformat(), "attempts": 0}]

    if kind == "SIGNAL":
        p = ev["pending"]
        expires = pd.Timestamp(p["entry_due"]) + SIGNAL_TTL
        stale = now > expires
        ledger.log_event({
            **base, "signal_id": p["signal_id"],
            "send_status": "EXPIRED_BEFORE_SEND" if stale else "queued",
            "signal_close": p["signal_close"], "stop": p["stop"], "target": p["target"],
            "risk_pct_of_price": round(p["risk_pct_of_price"], 4),
        })
        if stale:
            # Mengejar bar lama: tetap masuk ledger supaya forward test lengkap,
            # tapi jangan kirim sinyal yang tidak bisa diikuti lagi.
            p["notified"] = False
            print(f"[skip] sinyal {symbol} {p['signal_id']} sudah basi, tidak dikirim")
            return []
        p["notified"] = True
        return msg(p["signal_id"],
                   notify.signal_message(p, symbol, source, delay, cfg["paper"]), expires)

    if kind == "ENTRY":
        pos = ev["pos"]
        ledger.log_event({
            **base, "signal_id": pos.signal_id,
            "signal_close": pos.signal_close, "stop": pos.stop, "target": pos.target,
            "entry_price": pos.entry_price, "qty": round(pos.qty, 8),
            "notional_usd": round(pos.qty * pos.entry_price, 4),
        })
        if not pos.notified:
            return []
        return msg(pos.signal_id, notify.entry_message(pos, symbol, source),
                   now + CONFIRM_TTL)

    if kind == "EXIT":
        pos, px = ev["pos"], ev["exit_price"]
        res = trade_result(pos, px, cfg["paper"]["commission_pct"])
        sc = pos.sig_ctx or {}
        notional = res["notional_usd"]
        ledger.log_trade({
            "koin": symbol,
            "waktu_sinyal_utc": pos.signal_bar, "waktu_entry_utc": pos.entry_bar,
            "close_bar0": pos.signal_close, "low_bar5": pos.stop,
            "rsi_bar0": sc.get("rsi_bar0"), "rsi_bar1": sc.get("rsi_bar1"),
            "ema200_bar0": sc.get("ema200_bar0"),
            "stop_rencana": pos.stop, "target_rencana": pos.target,
            "harga_entry_aktual": pos.entry_price, "qty": round(pos.qty, 8),
            "notional": round(notional, 4),
            "dilewati_min_notional": notional < ledger.min_notional(symbol),
            "harga_exit_aktual": px, "alasan_exit": ev["reason"],
            "waktu_exit_utc": bar.isoformat(), "bar_ditahan": pos.bars_held,
            "pnl_usd": round(res["pnl_usd"], 4), "R_realisasi": round(res["R_net"], 4),
            "catatan": "paper: fill = open/level, tanpa slippage & funding",
            "signal_id": pos.signal_id, "data_source": source,
            "engine_version": ENGINE_VERSION, "R_kotor": round(res["R_gross"], 4),
            "entry_vs_close_bar0_pct": round((pos.entry_price / pos.signal_close - 1) * 100, 4),
            "mae_pct": round(pos.mae_pct, 4), "mfe_pct": round(pos.mfe_pct, 4),
            "notified": pos.notified,
        })
        ledger.log_event({
            **base, "signal_id": pos.signal_id,
            "signal_close": pos.signal_close, "stop": pos.stop, "target": pos.target,
            "entry_price": pos.entry_price, "qty": round(pos.qty, 8),
            "notional_usd": round(notional, 4), "exit_price": px,
            "exit_reason": ev["reason"], "bars_held": pos.bars_held,
            "R_gross": round(res["R_gross"], 4), "R_net": round(res["R_net"], 4),
            "pnl_usd": round(res["pnl_usd"], 4),
        })
        if not pos.notified:
            return []
        t = {**res, "reason": ev["reason"], "exit_bar": bar.isoformat(),
             "entry_price": pos.entry_price, "exit_price": px,
             "bars_held": pos.bars_held, "mae_pct": pos.mae_pct,
             "mfe_pct": pos.mfe_pct, "signal_id": pos.signal_id}
        return msg(pos.signal_id, notify.exit_message(t, symbol, _summary(cfg)),
                   now + CONFIRM_TTL)
    return []


def _process(sym, cfg, st, run, queued) -> dict | None:
    """Majukan mesin state satu simbol. None kalau feed-nya gagal."""
    try:
        feed = datafeed.fetch(sym)
    except Exception as e:  # noqa: BLE001
        print(f"[data] {sym} GAGAL: {e}")
        return None

    df, source = feed.df, feed.source
    p = cfg["params"]
    f = compute_features(df, p)
    ts = pd.DatetimeIndex(df["ts"])
    sl = state.slot(st, sym)
    info = {"source": source, "last_bar": ts[-1].isoformat(),
            "last_close": float(df["close"].iloc[-1]), "bars": 0}

    if sl.get("last_bar") is None:
        # Run pertama simbol ini: ambil bar tutup terbaru dan mulai flat.
        # Memutar ulang sejarah di sini akan menembakkan setumpuk sinyal basi.
        sl.update(last_bar=ts[-1].isoformat(), position=None, pending=None)
        info["bootstrapped"] = True
        print(f"[bootstrap] {sym} mulai dari {ts[-1]}, posisi kosong")
        return info

    pos = pos_from_dict(sl.get("position"))
    pending = sl.get("pending")
    seen = pd.Timestamp(sl["last_bar"])
    if ts[-1] < seen:
        info.update(stale=True, last_bar=sl["last_bar"])
        print(f"[run] {sym} PERINGATAN: feed berhenti di {ts[-1]} padahal "
              f"{sl['last_bar']} sudah diproses -- tidak ada bar yang diputar ulang")
        return info
    start = int(ts.searchsorted(seen, side="right"))
    if start == 0:
        # Bar terakhir yang diproses sudah keluar dari jendela 1.500 bar (>250
        # hari mati). Melanjutkan akan melompati bar tanpa pernah menguji stop.
        raise RuntimeError(f"{sym}: last_bar {seen} di luar jendela data, "
                           "tidak bisa dilanjutkan dengan aman")
    print(f"[run] {sym} sumber={source} bar={len(df)} terakhir={sl['last_bar']} "
          f"-> {len(df) - start} bar baru")

    paper = cfg["paper"]
    for i in range(start, len(df)):
        pos, pending, events = step(f, ts, i, p, pos, pending,
                                    paper["capital_usd"], paper["risk_pct"])
        run["bars_processed"] += 1
        info["bars"] += 1
        for ev in events:
            run["events_emitted"] += 1
            queued += _handle(ev, sym, source, cfg, st)
        # Commit per bar: kalau bar berikutnya meledak, bar ini tidak diputar ulang
        # (events.csv / trades.csv tidak punya dedup sendiri).
        sl.update(last_bar=ts[i].isoformat(), position=pos_to_dict(pos), pending=pending)
    info["pos"] = pos
    return info


def main():
    cfg = load()
    symbols = cfg["symbols"]
    run = {"run_at_utc": pd.Timestamp.now(tz="UTC").isoformat(), "status": "ok",
           "engine_version": ENGINE_VERSION, "run_id": RUN_ID, "commit_sha": SHA,
           "bars_processed": 0, "events_emitted": 0, "message": ""}

    try:
        st = ledger.read_json(STATE, {})
    except ledger.StateCorrupt as e:
        run.update(status="state_error", message=str(e))
        ledger.log_run(run)
        notify.send(notify.alert_message("state rusak", e))
        print(traceback.format_exc())
        return 1
    st.setdefault("schema", state.SCHEMA)
    before = _fingerprint(st)

    sent, failed, dropped = _flush(st)

    queued, seen, down = [], {}, []
    for sym in symbols:
        # Satu simbol tidak boleh menjatuhkan empat lainnya.
        try:
            info = _process(sym, cfg, st, run, queued)
        except Exception as e:  # noqa: BLE001
            print(f"[run] {sym} ERROR: {type(e).__name__}: {e}")
            print(traceback.format_exc())
            info = None
        if info is None:
            down.append(sym)
        else:
            seen[sym] = info

    st.setdefault("outbox", []).extend(queued)
    s2, f2, d2 = _flush(st)
    sent, failed, dropped = sent + s2, f2, dropped + d2

    st["engine_version"] = ENGINE_VERSION
    if _fingerprint(st) != before:
        st["updated_at"] = pd.Timestamp.now(tz="UTC").isoformat()
        ledger.write_json(STATE, st)

    if failed:
        telegram = f"failed_{failed}" if not sent else f"partial_{sent}/{sent + failed}"
    else:
        telegram = "sent" if sent else "nothing_to_send"
    stale = [s for s, v in seen.items() if v.get("stale")]
    opens = state.open_positions(st)
    sources = sorted({v["source"] for v in seen.values()})
    run.update(
        data_source=(sources[0] if len(sources) == 1 else ",".join(sources)),
        last_bar_utc=max((v["last_bar"] for v in seen.values()), default=""),
        open_positions=",".join(s.replace("USDT", "") for s in opens),
        telegram=telegram)

    problems = []
    if down and len(down) == len(symbols):
        problems.append((5, "data_error", "semua simbol gagal: " + ",".join(down)))
        notify.send(notify.alert_message("data feed gagal",
                                         "semua simbol gagal: " + ", ".join(down)))
    elif down:
        # Satu simbol mati tidak boleh membangunkan Anda tiap 10 menit; heartbeat
        # harian melaporkannya, runs.csv mencatatnya.
        problems.append((2, "partial_data", "simbol gagal: " + ",".join(down)))
    if failed:
        problems.append((4, "delivery_error", f"{failed} pesan masih di outbox"))
    if stale:
        problems.append((1, "stale_feed", "feed tertinggal: " + ",".join(stale)))
    if problems:
        problems.sort(reverse=True)
        run["status"] = problems[0][1]
        run["message"] = "; ".join(m for _, _, m in problems)
    if _should_log_run(run):
        ledger.log_run(run)
    print(f"[run] selesai: {run['bars_processed']} bar, {run['events_emitted']} event, "
          f"posisi={len(opens)}, kirim={telegram}"
          + (f", dibuang={dropped}" if dropped else "")
          + (f", simbol gagal: {','.join(down)}" if down else ""))
    return 1 if (failed or len(down) == len(symbols)) else 0


if __name__ == "__main__":
    sys.exit(main())
