"""Uçtan uca akış: senaryo -> görseller -> montaj -> (onay) -> yayın."""

from __future__ import annotations

import json
import random
import re
import unicodedata
from datetime import datetime
from pathlib import Path

from . import gorsel, montaj, senaryo, yayin
from .config import Ayarlar
from .stiller import STILLER


def _gecmis_yolu(ayar: Ayarlar) -> Path:
    return ayar.yol(ayar.cikti_klasoru) / "gecmis.json"


def gecmis_oku(ayar: Ayarlar) -> list[dict]:
    yol = _gecmis_yolu(ayar)
    return json.loads(yol.read_text(encoding="utf-8")) if yol.exists() else []


def _gecmis_yaz(ayar: Ayarlar, kayitlar: list[dict]) -> None:
    yol = _gecmis_yolu(ayar)
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(kayitlar, ensure_ascii=False, indent=2), encoding="utf-8")


def _kisa_ad(metin: str) -> str:
    tablo = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    metin = unicodedata.normalize("NFKD", metin.translate(tablo)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", metin.lower()).strip("-")[:40] or "video"


def video_uret(ayar: Ayarlar, tema: str | None = None, stil: str | None = None, senaryo_dosyasi: Path | None = None) -> Path:
    tema = tema or random.choice(ayar.temalar)
    stil = stil or random.choice(ayar.stiller)
    if stil not in STILLER:
        raise ValueError(f"Bilinmeyen stil '{stil}'. Seçenekler: {', '.join(STILLER)}")
    gecmis = gecmis_oku(ayar)

    if senaryo_dosyasi:
        tema = "(senaryo dosyasından)"
    print(f"[1/3] Senaryo (tema: {tema}, stil: {stil})")
    if senaryo_dosyasi:
        sen = senaryo.Senaryo.model_validate_json(Path(senaryo_dosyasi).read_text(encoding="utf-8"))
    else:
        sen = senaryo.uret(ayar, tema, stil, [k["konu"] for k in gecmis])
    for i, s in enumerate(sen.sahneler, 1):
        print(f"  {i}. {s.metin}")

    klasor = ayar.yol(ayar.cikti_klasoru) / f"{datetime.now():%Y%m%d-%H%M%S}_{_kisa_ad(sen.konu)}"
    klasor.mkdir(parents=True, exist_ok=True)
    (klasor / "senaryo.json").write_text(sen.model_dump_json(indent=2), encoding="utf-8")
    aciklama = f"{sen.aciklama}\n\n{' '.join(sen.hashtagler)}"
    (klasor / "aciklama.txt").write_text(aciklama, encoding="utf-8")

    print(f"[2/3] Görseller ({ayar.gorsel_saglayici})")
    gorseller = gorsel.uret(ayar, stil, [s.gorsel for s in sen.sahneler], klasor / "gorseller")

    print("[3/3] Montaj")
    montaj.birlestir(ayar, gorseller, [s.metin for s in sen.sahneler], STILLER[stil], klasor / "video.mp4")

    gecmis.append({
        "klasor": klasor.name, "konu": sen.konu, "tema": tema, "stil": stil,
        "tarih": datetime.now().isoformat(timespec="seconds"),
        "onaylandi": not ayar.onay_gerekli, "yayin_id": None,
    })
    _gecmis_yaz(ayar, gecmis)
    print(f"Hazır: {klasor}")
    return klasor


def _kayit(gecmis: list[dict], klasor: Path) -> dict:
    for k in gecmis:
        if k["klasor"] == klasor.name:
            return k
    raise ValueError(f"{klasor.name} geçmişte bulunamadı.")


def onayla(ayar: Ayarlar, klasor: Path) -> None:
    gecmis = gecmis_oku(ayar)
    _kayit(gecmis, klasor)["onaylandi"] = True
    _gecmis_yaz(ayar, gecmis)
    print(f"Onaylandı: {klasor.name}")


def yayinla(ayar: Ayarlar, klasor: Path) -> str:
    gecmis = gecmis_oku(ayar)
    kayit = _kayit(gecmis, klasor)
    if kayit.get("yayin_id"):
        raise RuntimeError(f"{klasor.name} zaten yayınlanmış ({kayit['yayin_id']}).")
    aciklama = (klasor / "aciklama.txt").read_text(encoding="utf-8")
    kayit["yayin_id"] = yayin.reels_paylas(ayar, klasor / "video.mp4", aciklama)
    kayit["yayin_tarihi"] = datetime.now().isoformat(timespec="seconds")
    _gecmis_yaz(ayar, gecmis)
    return kayit["yayin_id"]


def siradakini_yayinla(ayar: Ayarlar) -> str | None:
    """Onaylanmış ama henüz paylaşılmamış en eski videoyu yayınlar."""
    kok = ayar.yol(ayar.cikti_klasoru)
    for k in gecmis_oku(ayar):
        if k.get("onaylandi") and not k.get("yayin_id") and (kok / k["klasor"] / "video.mp4").exists():
            return yayinla(ayar, kok / k["klasor"])
    print("Yayınlanacak onaylı video yok.")
    return None
