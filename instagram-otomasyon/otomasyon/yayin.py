"""Instagram Graph API (resmî yol) ile Reels paylaşımı.

Gereken: Business veya Creator Instagram hesabı, IG_USER_ID ve
instagram_content_publish izinli uzun ömürlü IG_ACCESS_TOKEN.
Video, "resumable upload" ile doğrudan bilgisayardan yüklenir;
ayrıca bir sunucuya/URL'ye koymanıza gerek yoktur.
"""

from __future__ import annotations

import time
from pathlib import Path

import requests

from .config import Ayarlar


def _kontrol(yanit: requests.Response) -> dict:
    try:
        veri = yanit.json()
    except ValueError:
        veri = {"ham": yanit.text}
    if not yanit.ok or "error" in veri:
        raise RuntimeError(f"Instagram API hatası ({yanit.status_code}): {veri}")
    return veri


def reels_paylas(ayar: Ayarlar, video: Path, aciklama: str, kapak_ms: int = 1500) -> str:
    if not (ayar.ig_kullanici_id and ayar.ig_token):
        raise RuntimeError("IG_USER_ID ve IG_ACCESS_TOKEN .env dosyasında tanımlı olmalı.")
    taban = f"https://{ayar.instagram_api_host}/{ayar.instagram_api_surumu}"
    token = ayar.ig_token

    # 1) Medya kabı oluştur (resumable)
    kap = _kontrol(requests.post(
        f"{taban}/{ayar.ig_kullanici_id}/media",
        data={
            "media_type": "REELS",
            "upload_type": "resumable",
            "caption": aciklama,
            "share_to_feed": "true",
            "thumb_offset": str(kapak_ms),
            "access_token": token,
        },
        timeout=60,
    ))
    kap_id, yukleme_adresi = kap["id"], kap["uri"]
    print(f"  medya kabı: {kap_id}")

    # 2) Videoyu yükle
    veri = video.read_bytes()
    _kontrol(requests.post(
        yukleme_adresi,
        headers={"Authorization": f"OAuth {token}", "offset": "0", "file_size": str(len(veri))},
        data=veri,
        timeout=600,
    ))
    print("  video yüklendi, Instagram işliyor...")

    # 3) İşlenmesini bekle
    for _ in range(60):
        durum = _kontrol(requests.get(
            f"{taban}/{kap_id}", params={"fields": "status_code,status", "access_token": token}, timeout=30
        ))
        kod = durum.get("status_code")
        if kod == "FINISHED":
            break
        if kod in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Instagram videoyu işleyemedi: {durum}")
        time.sleep(10)
    else:
        raise RuntimeError("Instagram işleme zaman aşımına uğradı (10 dk).")

    # 4) Yayınla
    sonuc = _kontrol(requests.post(
        f"{taban}/{ayar.ig_kullanici_id}/media_publish",
        data={"creation_id": kap_id, "access_token": token},
        timeout=60,
    ))
    print(f"  yayınlandı! medya id: {sonuc['id']}")
    return sonuc["id"]
