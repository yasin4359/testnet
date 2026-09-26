"""Instagram Reels otomasyonu - komut satırı.

Örnekler:
  python main.py uret                       # rastgele tema/stil ile video üret
  python main.py uret --tema anne --stil sicak_illustrasyon
  python main.py uret --senaryo ornek_senaryo.json   # Claude'suz, hazır metinle
  python main.py onayla cikti/20260926-...  # videoyu yayın sırasına al
  python main.py yayinla cikti/20260926-... # belirli videoyu hemen paylaş
  python main.py siradaki                   # onaylı en eski videoyu paylaş
  python main.py otomatik                   # üret + (onay gerekmiyorsa) paylaş
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from otomasyon import akis
from otomasyon.config import yukle
from otomasyon.stiller import STILLER


def main() -> int:
    p = argparse.ArgumentParser(description="Instagram Reels otomasyonu")
    p.add_argument("--config", help="config.yaml yolu")
    alt = p.add_subparsers(dest="komut", required=True)

    u = alt.add_parser("uret", help="yeni video üret")
    u.add_argument("--tema")
    u.add_argument("--stil", choices=list(STILLER))
    u.add_argument("--senaryo", type=Path, help="Claude yerine hazır senaryo JSON dosyası")

    for ad, yardim in (("onayla", "videoyu onayla"), ("yayinla", "videoyu hemen paylaş")):
        a = alt.add_parser(ad, help=yardim)
        a.add_argument("klasor", type=Path)

    alt.add_parser("siradaki", help="onaylı en eski videoyu paylaş")
    o = alt.add_parser("otomatik", help="üret, onay gerekmiyorsa paylaş")
    o.add_argument("--tema")
    o.add_argument("--stil", choices=list(STILLER))

    arg = p.parse_args()
    ayar = yukle(arg.config)

    if arg.komut == "uret":
        akis.video_uret(ayar, arg.tema, arg.stil, arg.senaryo)
    elif arg.komut == "onayla":
        akis.onayla(ayar, arg.klasor.resolve())
    elif arg.komut == "yayinla":
        akis.yayinla(ayar, arg.klasor.resolve())
    elif arg.komut == "siradaki":
        akis.siradakini_yayinla(ayar)
    elif arg.komut == "otomatik":
        klasor = akis.video_uret(ayar, arg.tema, arg.stil)
        if ayar.onay_gerekli:
            print(f"Onay bekliyor. Kontrol edip onaylayın: python main.py onayla {klasor}")
        else:
            akis.yayinla(ayar, klasor)
    return 0


if __name__ == "__main__":
    sys.exit(main())
