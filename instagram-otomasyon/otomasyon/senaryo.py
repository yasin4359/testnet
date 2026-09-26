"""Claude ile video metni, sahne tarifleri, açıklama ve hashtag üretimi."""

from __future__ import annotations

import anthropic
from pydantic import BaseModel, Field

from .config import Ayarlar


class Sahne(BaseModel):
    metin: str = Field(description="Ekrana yazılacak kısa Türkçe cümle (en fazla ~14 kelime).")
    gorsel: str = Field(description="Bu sahnenin görselinin İngilizce tarifi (karakterin ne yaptığı, ortam, duygu).")


class Senaryo(BaseModel):
    konu: str = Field(description="Videonun konusu, 3-6 kelime.")
    sahneler: list[Sahne]
    aciklama: str = Field(description="Instagram gönderi açıklaması: 1-3 samimi cümle, soru veya harekete çağrı ile biten.")
    hashtagler: list[str] = Field(description="8-15 adet Türkçe hashtag, # işaretiyle.")


SISTEM = """Sen Türkiye'de büyük kitlelere ulaşan duygusal/manevi Instagram Reels sayfaları için içerik yazıyorsun.
Örnek aldığımız sayfalar: @fenamontaj, @kahvekaresi, @dronemredikmen, @mekanikruh.co.

FORMAT (örnek videolardan çıkarıldı):
- 15-30 saniyelik, müzikli, seslendirmesiz video. Her sahnede tek bir görsel ve üstte el yazısı fontlu kısa bir cümle var.
- Metin tüm sahnelere bölünmüş TEK bir akıcı düşünce/şiir gibidir; cümleler bir sonrakine bağlanır.
- 1. sahne KANCA'dır: merak uyandırır, yarım bırakır ("Bazı zamanlar anneme bakınca;", "Şunu unutma;", "Bugün çok güzel bir duaya denk geldim, diyor ki:", "Kendimden özür diliyorum...").
- Son sahne vurucu kapanıştır; izleyeni kaydetmeye/paylaşmaya iter.
- Dil sade, samimi, içten; klişe ama güçlü duygular: anne sevgisi, dua ve şükür, kırgınlık, kendini sevmek, sabır, dürüstlük, hayat dersi, atasözü/özdeyiş yorumları.
- Noktalama örneklerdeki gibi: ";" ile açılış, "..." ile hüzün, "," ile devam.

GÖRSEL TARİFLERİ:
- İngilizce yaz. Her sahnede aynı ana karakter (yuvarlak beyaz kafalı sevimli çizgi karakter) yer alır; karakteri tarif etmene gerek yok, sadece ne yaptığını, ortamı, nesneleri ve duyguyu anlat.
- Metni birebir resmetme, metaforla güçlendir (örn. "ödeyemeyeceğim tek şey" -> karakter annesine sarıldığını hayal ediyor, düşünce balonunda).
- Görselde yazı OLMAMALI.

Dini içerikte saygılı ol; ayet/hadis uydurma, genel dua ifadeleri kullan. Siyaset, nefret ve kişisel hedefleme yok."""


def uret(ayar: Ayarlar, tema: str, stil: str, gecmis_konular: list[str]) -> Senaryo:
    if not ayar.anthropic_key:
        raise RuntimeError("ANTHROPIC_API_KEY tanımlı değil (.env dosyasına ekleyin).")
    client = anthropic.Anthropic(api_key=ayar.anthropic_key)
    en_az, en_cok = ayar.sahne_sayisi
    son = "\n".join(f"- {k}" for k in gecmis_konular[-40:]) or "(henüz yok)"
    istek = (
        f"Tema: {tema}\nGörsel stil: {stil}\nDil: {ayar.dil}\n"
        f"Sahne sayısı: {en_az}-{en_cok} arası.\n\n"
        f"Daha önce işlenen konular (TEKRARLAMA, farklı bir açı bul):\n{son}\n\n"
        "Yeni bir video senaryosu yaz."
    )
    # Güvenlik filtresi isteği yanlışlıkla reddederse sunucu otomatik olarak
    # yedek modele geçer (server-side fallback).
    yanit = client.beta.messages.parse(
        model=ayar.claude_model,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=SISTEM,
        messages=[{"role": "user", "content": istek}],
        output_format=Senaryo,
    )
    if yanit.stop_reason == "refusal":
        raise RuntimeError(f"Claude isteği reddetti: {yanit.stop_details}")
    senaryo = yanit.parsed_output
    if not senaryo or not senaryo.sahneler:
        raise RuntimeError("Claude geçerli bir senaryo döndürmedi.")
    return senaryo
