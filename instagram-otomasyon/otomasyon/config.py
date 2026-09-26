"""Ayarların (config.yaml) ve gizli anahtarların (.env) yüklenmesi."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from dotenv import load_dotenv

KOK = Path(__file__).resolve().parent.parent


@dataclass
class Ayarlar:
    hesap_adi: str = "hesabiniz"
    dil: str = "Türkçe"
    temalar: list[str] = field(default_factory=lambda: ["anne", "dua", "hayat dersi"])
    stiller: list[str] = field(default_factory=lambda: ["sicak_illustrasyon"])
    sahne_sayisi: tuple[int, int] = (3, 6)
    claude_model: str = "claude-opus-5"
    gorsel_saglayici: str = "gemini"  # "gemini" | "yerel" (API'siz test)
    gemini_model: str = "gemini-2.5-flash-image"
    karakter_referansi: str | None = "assets/karakter.png"
    muzik_klasoru: str = "assets/muzik"
    font: str = "assets/fonts/PatrickHand-Regular.ttf"
    cikti_klasoru: str = "cikti"
    onay_gerekli: bool = True
    instagram_api_surumu: str = "v23.0"
    # Facebook Login ile bağlı hesap: graph.facebook.com
    # "Instagram API with Instagram Login" ile: graph.instagram.com
    instagram_api_host: str = "graph.facebook.com"

    @property
    def anthropic_key(self) -> str | None:
        return os.getenv("ANTHROPIC_API_KEY")

    @property
    def gemini_key(self) -> str | None:
        return os.getenv("GEMINI_API_KEY")

    @property
    def ig_kullanici_id(self) -> str | None:
        return os.getenv("IG_USER_ID")

    @property
    def ig_token(self) -> str | None:
        return os.getenv("IG_ACCESS_TOKEN")

    def yol(self, goreli: str) -> Path:
        p = Path(goreli)
        return p if p.is_absolute() else KOK / p


def yukle(dosya: str | Path | None = None) -> Ayarlar:
    load_dotenv(KOK / ".env")
    dosya = Path(dosya) if dosya else KOK / "config.yaml"
    veri = {}
    if dosya.exists():
        veri = yaml.safe_load(dosya.read_text(encoding="utf-8")) or {}
    if "sahne_sayisi" in veri:
        veri["sahne_sayisi"] = tuple(veri["sahne_sayisi"])
    bilinen = Ayarlar.__dataclass_fields__.keys()
    bilinmeyen = set(veri) - set(bilinen)
    if bilinmeyen:
        raise ValueError(f"config.yaml içinde tanınmayan alan(lar): {', '.join(sorted(bilinmeyen))}")
    return Ayarlar(**veri)
