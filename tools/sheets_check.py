"""Periksa Google Sheets dari ujung ke ujung: tulis, lalu baca balik.

Dijalankan oleh workflow "Kirim pesan tes". Langkah:
  1. konfigurasi lengkap? (kunci JSON + spreadsheet id; email yang harus diberi akses)
  2. spreadsheet bisa dibaca?
  3. sinkron events/trades/runs dari CSV + tulis ulang tab ringkasan
  4. BACA BALIK tiap tab dan pastikan semua kolom wajib ada:
       - trades  memuat setiap kolom forward_test_log.csv (template setup §5)
       - events  memuat RSI bar 0/1, EMA200, stop, target (Report 10.2)
       - runs    memuat status Telegram dan status cermin Sheets
       - jumlah baris data di tab >= jumlah baris CSV
  5. cetak isi tab ringkasan

Keluar 1 kalau ada yang gagal. Tidak pernah mencetak isi secret.
"""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import snap.compat  # noqa: F401,E402

from snap import ledger, report, sheets  # noqa: E402
from snap.config import load  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _template_cols() -> list[str]:
    with open(os.path.join(ROOT, "forward_test_log.csv"), encoding="utf-8") as fh:
        return next(csv.reader(fh))


REQUIRED = {
    "trades": _template_cols() + ["signal_id", "data_source", "R_kotor", "mae_pct", "mfe_pct"],
    "events": ["event", "symbol", "bar_time_utc", "signal_close", "stop", "target",
               "entry_price", "exit_price", "exit_reason", "R_net", "rsi_bar0", "rsi_bar1",
               "ema200_bar0", "close_vs_ema200_pct", "low_bar5", "data_source",
               "signal_to_send_minutes"],
    "runs": ["run_at_utc", "status", "data_source", "last_bar_utc", "telegram", "sheet"],
}
CSV = {"events": ledger.EVENTS, "trades": ledger.TRADES, "runs": ledger.RUNS}


def main() -> int:
    problems = []
    print("== 1. konfigurasi")
    hint = sheets.missing()
    if not sheets.configured():
        print(f"   BELUM LENGKAP: {hint or 'GOOGLE_SERVICE_ACCOUNT_JSON dan GSHEET_SPREADSHEET_ID kosong'}")
        return 1
    print(f"   lengkap · service account: {sheets.client_email()}")

    print("== 2. akses")
    if not sheets.reachable():
        print(f"   GAGAL membaca spreadsheet. Bagikan ke {sheets.client_email()} dengan akses Editor.")
        return 1
    print("   spreadsheet bisa dibaca")

    print("== 3. sinkron + ringkasan")
    cfg = load()
    st = ledger.read_json("state/position.json", {})
    res = report.sync_all(cfg, st)
    for k, v in res.items():
        print(f"   {k:<10} {v}")
        if v is None or v is False:
            problems.append(f"sinkron {k} gagal")

    print("== 4. baca balik")
    for tab, need in REQUIRED.items():
        vals = sheets.read(tab)
        if not vals:
            problems.append(f"tab {tab} kosong / tidak terbaca")
            print(f"   {tab}: TIDAK TERBACA")
            continue
        head, body = vals[0], vals[1:]
        miss = [c for c in need if c not in head]
        n_csv = len(ledger.read_history(CSV[tab]))
        print(f"   {tab}: {len(head)} kolom, {len(body)} baris data (CSV: {n_csv})")
        if miss:
            problems.append(f"{tab} tidak punya kolom {miss}")
            print(f"      KOLOM HILANG: {miss}")
        if len(body) < n_csv:
            problems.append(f"{tab} kurang {n_csv - len(body)} baris dari CSV")
        if body:
            last = dict(zip(head, body[-1]))
            brief = {k: last.get(k) for k in list(need)[:6]}
            print(f"      baris terakhir: {brief}")

    print("== 5. isi tab ringkasan")
    for row in sheets.read("ringkasan") or []:
        cells = [c for c in row if str(c).strip()]
        if cells:
            print("   " + " | ".join(str(c) for c in cells))

    print()
    if problems:
        print("HASIL: ADA MASALAH -> " + "; ".join(problems))
        return 1
    print("HASIL: SEMUA OK -- spreadsheet mencatat semua kolom yang dibutuhkan forward test")
    return 0


if __name__ == "__main__":
    sys.exit(main())
