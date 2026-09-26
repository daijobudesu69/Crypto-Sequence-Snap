"""Kirim satu pesan TES ke Telegram -- untuk memastikan token dan chat id benar.

Merender sinyal contoh dari Report Bagian 3 (ETHUSDT, 9 Sep 2024) dengan
template sinyal sungguhan, diberi penanda TES supaya tidak pernah tertukar
dengan sinyal aktif. Dijalankan lewat workflow "Kirim pesan tes".
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import snap.compat  # noqa: F401,E402

from snap import notify  # noqa: E402
from snap.config import load  # noqa: E402

SAMPLE = {
    "signal_id": "20240909T0800-L", "signal_bar": "2024-09-09T08:00:00+00:00",
    "signal_close": 2314.10, "stop": 2238.88, "target": 2426.93,
    "risk_pct_of_price": 3.25,
    "sig_ctx": {"rsi_bar0": 48.52, "rsi_bar1": 48.33,
                "ema200_bar0": None, "close_vs_ema200_pct": None},
}


def main() -> int:
    if not notify.configured():
        print("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID belum diisi di repository secrets.")
        return 1
    cfg = load()
    text = ("🧪 <b>PESAN TES — BUKAN SINYAL</b>\n"
            "Contoh dari Report Bagian 3 (ETHUSDT 9 Sep 2024). Kalau pesan ini "
            "sampai, pengiriman Telegram sudah benar.\n\n"
            + notify.signal_message(SAMPLE, "ETHUSDT", "contoh", 0, cfg["paper"]))
    ok = notify.send(text)
    print("terkirim" if ok else "GAGAL -- lihat pesan error di atas")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
