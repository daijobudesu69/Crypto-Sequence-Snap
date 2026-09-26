"""Log append-only: bukti forward test. Semua di-commit ke repo ini.

  state/events.csv -- satu baris per SIGNAL / ENTRY / EXIT, dengan snapshot
                      indikator di bar itu. Untuk menjawab "kenapa sinyal ini
                      muncul", bukan cuma "sinyal muncul".
  state/trades.csv -- satu baris per trade selesai. Kolomnya MENGIKUTI
                      forward_test_log.csv (template di Report/setup), jadi
                      hasil bot dan catatan manual bisa diadu kolom per kolom.
  state/runs.csv   -- satu baris per run: bukti hidup, latensi, sumber data.

Diadaptasi dari Crypto-MEX (mex/ledger.py). Mirror Google Sheets belum ada --
menyusul setelah repo jalan.
"""
from . import compat  # noqa: F401
import csv
import json
import os

EVENTS = "state/events.csv"
TRADES = "state/trades.csv"
RUNS = "state/runs.csv"

# Report 6.1 -- snapshot exchangeInfo 7 Sep 2026, berstatus ASUMSI.
MIN_NOTIONAL = {"ETHUSDT": 20.0}
MIN_NOTIONAL_DEFAULT = 5.0

EVENT_COLS = [
    "logged_at_utc", "event", "signal_id", "symbol", "bar_time_utc",
    "data_source", "engine_version", "run_id", "commit_sha",
    "signal_to_send_minutes", "send_status",
    # level rencana (dibekukan di close bar sinyal)
    "signal_close", "stop", "target", "risk_pct_of_price",
    # paper fill / hasil
    "entry_price", "qty", "notional_usd", "exit_price", "exit_reason",
    "bars_held", "R_gross", "R_net", "pnl_usd",
    # snapshot bar ini
    "open", "high", "low", "close", "volume",
    "rsi_bar0", "rsi_bar1", "ema200_bar0", "close_vs_ema200_pct", "low_bar5",
]

# Nama kolom sama dengan forward_test_log.csv, ditambah provenance di belakang.
TRADE_COLS = [
    "no", "koin", "waktu_sinyal_utc", "waktu_entry_utc", "close_bar0", "low_bar5",
    "rsi_bar0", "rsi_bar1", "ema200_bar0", "stop_rencana", "target_rencana",
    "harga_entry_aktual", "qty", "notional", "dilewati_min_notional",
    "harga_exit_aktual", "alasan_exit", "waktu_exit_utc", "bar_ditahan",
    "slippage_entry_tick", "slippage_exit_tick", "funding_dibayar_usd",
    "pnl_usd", "R_realisasi", "catatan",
    # provenance -- tidak ada di template manual
    "signal_id", "data_source", "engine_version", "R_kotor",
    "entry_vs_close_bar0_pct", "mae_pct", "mfe_pct", "notified",
]

RUN_COLS = [
    "run_at_utc", "status", "data_source", "last_bar_utc", "bars_processed",
    "events_emitted", "open_positions", "telegram", "engine_version",
    "run_id", "commit_sha", "message",
]


def min_notional(symbol: str) -> float:
    return MIN_NOTIONAL.get(symbol, MIN_NOTIONAL_DEFAULT)


def _rotate(path, cols):
    """Arsipkan log yang header-nya tidak lagi cocok, jangan tulis di atasnya.

    DictWriter menulis posisional; baris baru di bawah header lama menghasilkan
    file yang tidak bisa dibaca pandas -- permanen, karena log ini append-only.
    """
    with open(path, encoding="utf-8", newline="") as fh:
        head = next(csv.reader(fh), None)
    if head == list(cols):
        return
    stem, ext = os.path.splitext(path)
    n = 1
    while os.path.exists(f"{stem}.v{n}{ext}"):
        n += 1
    os.replace(path, f"{stem}.v{n}{ext}")
    print(f"[ledger] header {os.path.basename(path)} berubah; "
          f"log lama diarsipkan ke {os.path.basename(stem)}.v{n}{ext}")


def _append(path, cols, row):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    if os.path.exists(path) and os.path.getsize(path):
        _rotate(path, cols)
    new = not os.path.exists(path) or os.path.getsize(path) == 0
    with open(path, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow({k: ("" if row.get(k) is None else row.get(k, "")) for k in cols})


def read_rows(path) -> list[dict]:
    if not (os.path.exists(path) and os.path.getsize(path)):
        return []
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            return list(csv.DictReader(fh))
    except Exception as e:  # noqa: BLE001
        print(f"[ledger] gagal membaca {os.path.basename(path)}: {type(e).__name__}")
        return []


def log_event(row):
    _append(EVENTS, EVENT_COLS, row)


def log_trade(row):
    row = dict(row)
    row.setdefault("no", len(read_rows(TRADES)) + 1)
    _append(TRADES, TRADE_COLS, row)


def log_run(row):
    _append(RUNS, RUN_COLS, row)


def last_run_at() -> str | None:
    rows = read_rows(RUNS)
    return rows[-1]["run_at_utc"] if rows else None


class StateCorrupt(RuntimeError):
    """position.json ada tapi tidak bisa dibaca."""


def read_json(path, default):
    """File tidak ada -> default. File rusak -> raise, JANGAN default.

    Kembali ke default saat file rusak akan terlihat seperti run pertama: bot
    bootstrap, mengambil bar terbaru dan menyatakan diri flat -- diam-diam
    meninggalkan posisi terbuka beserta stop-nya.
    """
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return default
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise StateCorrupt(f"{path} rusak dan tidak bisa dibaca: {e}") from e


def write_json(path, obj):
    """Atomik: tulis file sementara lalu rename. Job yang dibunuh di tengah jalan
    tidak pernah meninggalkan setengah file."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, default=str)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)
