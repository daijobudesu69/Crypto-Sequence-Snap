"""Tes pipa: run_signal.py dan run_heartbeat.py sungguhan, dengan feed dan
Telegram palsu, di direktori sementara. Offline.

Jalankan: python tests/test_infra.py
"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile

os.environ["SNAP_SIGNAL_TTL"] = "30d"        # data sintetis lebih tua dari TTL asli

from _helpers import ROOT, frame, run_all, uptrend_with_pattern

import pandas as pd

import run_heartbeat
import run_signal
from snap import datafeed, ledger, notify, stats
from snap.config import load
sys.path.insert(0, os.path.join(ROOT, "tools"))
import merge_state  # noqa: E402

FULL = frame(uptrend_with_pattern(n=420, red_at=392, pump_at=405))
SENT = []


@contextlib.contextmanager
def sandbox(n_bars=None, telegram_ok=True, configured=True, feed=None):
    """Direktori kerja sementara + feed dan Telegram palsu."""
    old_cwd = os.getcwd()
    tmp = tempfile.mkdtemp()
    shutil.copy(os.path.join(ROOT, "config.yaml"), tmp)
    os.chdir(tmp)
    saved = (datafeed.fetch, notify.send, notify.configured)
    state = {"n": n_bars, "ok": telegram_ok}

    def fake_fetch(symbol, prefer=None):
        if feed is not None:
            return feed(symbol, state)
        if symbol != "ETHUSDT":
            raise RuntimeError("simbol lain dimatikan di tes")
        df = FULL.iloc[:state["n"]].reset_index(drop=True)
        return datafeed.Feed(df=df, source="fake", fetched_at=pd.Timestamp.now(tz="UTC"),
                             symbol=symbol)

    def fake_send(text):
        if not state["ok"]:
            return False
        SENT.append(text)
        return True

    datafeed.fetch = fake_fetch
    notify.send = fake_send
    notify.configured = lambda: configured
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            yield state
    finally:
        datafeed.fetch, notify.send, notify.configured = saved
        os.chdir(old_cwd)
        shutil.rmtree(tmp, ignore_errors=True)


def _state():
    with open("state/position.json", encoding="utf-8") as fh:
        return json.load(fh)


def _events(kind=None):
    rows = ledger.read_rows(ledger.EVENTS)
    return [r for r in rows if kind is None or r["event"] == kind]


def _signals_sent():
    return [t for t in SENT if "SEQUENCE SNAP v2" in t]


def test_bootstrap_flat_tanpa_sinyal_basi():
    SENT.clear()
    with sandbox(n_bars=399):
        run_signal.main()
        st = _state()
        eth = st["symbols"]["ETHUSDT"]
        assert eth["last_bar"] == FULL["ts"][398].isoformat()
        assert eth["position"] is None and eth["pending"] is None
        assert not _events() and not SENT


def test_sinyal_entry_exit_terkirim_sekali():
    SENT.clear()
    with sandbox(n_bars=390) as s:
        run_signal.main()                          # bootstrap di bar 389
        s["n"] = 398
        run_signal.main()                          # bar 390..397 -> SIGNAL
        assert len(_events("SIGNAL")) == 1 and len(_signals_sent()) == 1
        run_signal.main()                          # data sama -> tidak ada apa-apa
        assert len(_events("SIGNAL")) == 1 and len(_signals_sent()) == 1
        s["n"] = 420
        run_signal.main()                          # ENTRY di 398, EXIT target di 405
        assert [r["event"] for r in _events()] == ["SIGNAL", "ENTRY", "EXIT"]
        trades = ledger.read_rows(ledger.TRADES)
        assert len(trades) == 1 and trades[0]["alasan_exit"] == "target"
        # Entry = open bar 398 = close bar sinyal (seri kontinu) -> R kotor tepat 1,5.
        assert abs(float(trades[0]["R_kotor"]) - 1.5) < 1e-6
        assert 0 < float(trades[0]["R_realisasi"]) < 1.5       # dikurangi komisi
        assert trades[0]["koin"] == "ETHUSDT" and trades[0]["no"] == "1"
        assert sum("ENTRY TERCATAT" in t for t in SENT) == 1
        assert sum("EXIT — TARGET" in t for t in SENT) == 1
        run_signal.main()
        assert len(ledger.read_rows(ledger.TRADES)) == 1


def test_telegram_gagal_tetap_di_outbox_lalu_terkirim_sekali():
    SENT.clear()
    with sandbox(n_bars=390, telegram_ok=False) as s:
        run_signal.main()
        s["n"] = 398
        rc = run_signal.main()
        assert rc == 1, "kirim gagal harus membuat job merah"
        assert len(_state()["outbox"]) == 1 and not SENT
        rc = run_signal.main()                     # masih gagal, jangan dobel antre
        assert len(_state()["outbox"]) == 1
        s["ok"] = True
        assert run_signal.main() == 0
        assert len(_signals_sent()) == 1 and not _state()["outbox"]
        run_signal.main()
        assert len(_signals_sent()) == 1


def test_feed_mundur_last_bar_tidak_mundur():
    SENT.clear()
    with sandbox(n_bars=398) as s:
        run_signal.main()
        before = _state()["symbols"]["ETHUSDT"]["last_bar"]
        s["n"] = 395
        run_signal.main()
        assert _state()["symbols"]["ETHUSDT"]["last_bar"] == before
        assert ledger.read_rows(ledger.RUNS)[-1]["status"] in ("stale_feed", "partial_data")


def test_satu_simbol_mati_tidak_menjatuhkan_lainnya():
    SENT.clear()
    with sandbox(n_bars=398):
        assert run_signal.main() == 0
        st = _state()
        assert "ETHUSDT" in st["symbols"] and "BNBUSDT" not in st["symbols"]
        assert ledger.read_rows(ledger.RUNS)[-1]["status"] == "partial_data"


def test_semua_feed_mati_job_merah():
    SENT.clear()

    def dead(symbol, _s):
        raise RuntimeError("mati")
    with sandbox(feed=dead):
        assert run_signal.main() == 1
        assert ledger.read_rows(ledger.RUNS)[-1]["status"] == "data_error"


def test_state_rusak_tidak_ditimpa():
    SENT.clear()
    with sandbox(n_bars=398):
        os.makedirs("state", exist_ok=True)
        with open("state/position.json", "w") as fh:
            fh.write("{rusak")
        assert run_signal.main() == 1
        with open("state/position.json") as fh:
            assert fh.read() == "{rusak"


def test_sinyal_basi_dicatat_tapi_tidak_dikirim():
    SENT.clear()
    old = run_signal.SIGNAL_TTL
    run_signal.SIGNAL_TTL = pd.Timedelta("1h")
    try:
        with sandbox(n_bars=390) as s:
            run_signal.main()
            s["n"] = 420
            run_signal.main()
            ev = _events()
            assert ev[0]["event"] == "SIGNAL" and ev[0]["send_status"] == "EXPIRED_BEFORE_SEND"
            assert not SENT, "sinyal basi dan entry/exit-nya tidak boleh diumumkan"
            assert len(ledger.read_rows(ledger.TRADES)) == 1
    finally:
        run_signal.SIGNAL_TTL = old


def test_heartbeat_sekali_sehari():
    SENT.clear()
    with sandbox(n_bars=398):
        run_signal.main()
        os.environ["SNAP_HEARTBEAT_UTC"] = "00:00"
        run_heartbeat.TARGET_UTC = "00:00"
        run_heartbeat.main()
        run_heartbeat.main()
        beats = [t for t in SENT if "hidup" in t]
        assert len(beats) == 1
        assert "BNB" in beats[0] and "data tidak terjangkau" in beats[0]


def test_merge_state_isi_bukan_sisi():
    a = {"symbols": {"ETHUSDT": {"last_bar": "2026-09-26T08:00:00+00:00", "position": None},
                     "BNBUSDT": {"last_bar": "2026-09-26T00:00:00+00:00", "position": {"x": 1}}},
         "sent_ids": ["a"], "outbox": [{"key": "b"}, {"key": "c"}],
         "last_heartbeat_date": "2026-09-25"}
    b = {"symbols": {"ETHUSDT": {"last_bar": "2026-09-26T04:00:00+00:00", "position": {"y": 1}},
                     "BNBUSDT": {"last_bar": "2026-09-26T04:00:00+00:00", "position": None}},
         "sent_ids": ["b"], "outbox": [{"key": "c"}],
         "last_heartbeat_date": "2026-09-26"}
    with contextlib.redirect_stdout(io.StringIO()):
        m = merge_state.merge(a, b)
    assert m["symbols"]["ETHUSDT"]["position"] is None      # a lebih baru
    assert m["symbols"]["BNBUSDT"]["position"] is None      # b lebih baru
    assert m["sent_ids"] == ["a", "b"]
    assert [x["key"] for x in m["outbox"]] == ["c"]          # b sudah terkirim
    assert m["last_heartbeat_date"] == "2026-09-26"


def test_stats_aturan_berhenti():
    rows = [{"waktu_exit_utc": f"2026-01-{i + 1:02d}", "R_realisasi": -1.03,
             "pnl_usd": -3.09} for i in range(15)]
    s = stats.summarize(rows, 300.0)
    assert s["losing_streak"] == 15 and s["n"] == 15
    assert any("beruntun" in r for r in s["stop_rules"])
    assert abs(s["max_drawdown_pct"] - (-15.45)) < 0.01
    rows = [{"waktu_exit_utc": "2026-01-01", "R_realisasi": 1.47, "pnl_usd": 4.4}] + rows[:3]
    s = stats.summarize(rows, 300.0)
    assert s["losing_streak"] == 3 and s["longest_losing_streak"] == 3
    assert not s["stop_rules"]


def test_format_harga_koin_murah():
    assert notify.f(0.123456) != notify.f(0.123999)
    assert notify.f(2314.1) == "2,314.10"


def test_config_menolak_kunci_asing_dan_short():
    tmp = tempfile.mkdtemp()
    try:
        for extra in ("strategy:\n  allow_short: true\n", "symbols: [BTCUSDT]\n",
                      "prefer_source: gate_io_perp\n",
                      "strategy:\n  rsi_min_lng: 40\n"):
            p = os.path.join(tmp, "c.yaml")
            with open(p, "w") as fh:
                fh.write(extra)
            try:
                load(p)
            except ValueError:
                continue
            raise AssertionError(f"config harus ditolak: {extra!r}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_config_default_sama_dengan_report():
    cfg = load(os.path.join(ROOT, "config.yaml"))
    p = cfg["params"]
    assert (p.run_length, p.tolerance_pct, p.rsi_length, p.rsi_min_long,
            p.take_profit_r, p.ma_length, p.ma_type) == (5, 0.05, 14, 40, 1.5, 200, "EMA")
    assert p.use_rsi_filter and p.use_trend_filter
    assert cfg["paper"] == {"capital_usd": 300.0, "risk_pct": 1.0, "commission_pct": 0.05}
    assert cfg["symbols"] == ["ETHUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT", "AVAXUSDT",
                              "NEARUSDT"]


def test_tiap_koin_punya_sumber_utama_yang_sah():
    assert set(datafeed.PRIMARY) == set(datafeed.SYMBOLS)
    assert set(datafeed.PRIMARY.values()) <= set(datafeed.SOURCES)
    assert all(s in datafeed.GATE for s in datafeed.SYMBOLS)
    for s in ("XMRUSDT", "TRXUSDT", "TAOUSDT"):
        assert s not in datafeed.SYMBOLS, f"{s} dikeluarkan: kecocokan sinyal < 70%"


def test_fetch_mencoba_sumber_utama_dulu():
    calls = []
    long_ = frame(uptrend_with_pattern(n=1100, red_at=900))
    saved = (datafeed._from_binance_spot, datafeed._from_gate)
    datafeed._from_binance_spot = lambda sym: calls.append("spot") or long_.copy()
    datafeed._from_gate = lambda c: calls.append("gate") or long_.copy()
    try:
        assert datafeed.fetch("DOGEUSDT").source == "gate_io_perp" and calls == ["gate"]
        calls.clear()
        assert datafeed.fetch("ETHUSDT").source == "binance_spot_mirror" and calls == ["spot"]
        calls.clear()
        datafeed._from_gate = lambda c: calls.append("gate") or long_.iloc[:10]  # terlalu pendek
        assert datafeed.fetch("DOGEUSDT").source == "binance_spot_mirror"
        assert calls == ["gate", "spot"], "gagal di sumber utama -> cadangan"
    finally:
        datafeed._from_binance_spot, datafeed._from_gate = saved


def test_sanity_check_menolak_bolong_dan_basi():
    df = FULL.copy()
    datafeed.sanity_check(df, min_bars=100)
    try:
        datafeed.sanity_check(df.drop(index=200).reset_index(drop=True), min_bars=100)
        raise AssertionError("bar hilang harus ditolak")
    except RuntimeError:
        pass
    try:
        datafeed.sanity_check(df.iloc[:-5], min_bars=100)
        raise AssertionError("feed basi harus ditolak")
    except RuntimeError:
        pass


if __name__ == "__main__":
    sys.exit(run_all(globals()))
