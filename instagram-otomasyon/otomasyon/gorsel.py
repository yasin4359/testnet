"""Sahne görsellerinin üretimi.

- "gemini": Google Gemini görsel modeli. Karakter referans görseli verilirse her
  sahnede aynı karakteri korumak için isteğe eklenir.
- "yerel": API kullanmadan test için basit yer tutucu görsel çizer.
"""

from __future__ import annotations

import io
import random
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from .config import Ayarlar
from .stiller import gorsel_prompt

GENISLIK, YUKSEKLIK = 1080, 1920


def _dikey_kirp(img: Image.Image) -> Image.Image:
    """Görseli 1080x1920'ye (9:16) ortadan kırparak oturtur."""
    img = img.convert("RGB")
    hedef = GENISLIK / YUKSEKLIK
    w, h = img.size
    if w / h > hedef:
        yeni_w = int(h * hedef)
        img = img.crop(((w - yeni_w) // 2, 0, (w - yeni_w) // 2 + yeni_w, h))
    else:
        yeni_h = int(w / hedef)
        img = img.crop((0, (h - yeni_h) // 2, w, (h - yeni_h) // 2 + yeni_h))
    return img.resize((GENISLIK, YUKSEKLIK), Image.LANCZOS)


def _gemini(ayar: Ayarlar, prompt: str, referans: Image.Image | None) -> Image.Image:
    from google import genai
    from google.genai import types

    if not ayar.gemini_key:
        raise RuntimeError("GEMINI_API_KEY tanımlı değil (.env dosyasına ekleyin).")
    client = genai.Client(api_key=ayar.gemini_key)
    icerik: list = []
    if referans is not None:
        buf = io.BytesIO()
        referans.save(buf, format="PNG")
        icerik.append(types.Part.from_bytes(data=buf.getvalue(), mime_type="image/png"))
        prompt = "Use the character in the reference image exactly (same design and proportions). " + prompt
    icerik.append(prompt)

    son_hata: Exception | None = None
    for deneme in range(3):
        try:
            yanit = client.models.generate_content(
                model=ayar.gemini_model,
                contents=icerik,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio="9:16"),
                ),
            )
            for aday in yanit.candidates or []:
                for parca in aday.content.parts or []:
                    if parca.inline_data and parca.inline_data.data:
                        return Image.open(io.BytesIO(parca.inline_data.data))
            son_hata = RuntimeError("Gemini yanıtında görsel yok.")
        except Exception as e:  # ağ/kota hatalarında kısa bekleyip yeniden dene
            son_hata = e
        time.sleep(3 * (deneme + 1))
    raise RuntimeError(f"Görsel üretilemedi: {son_hata}")


def _yerel(prompt: str, sira: int) -> Image.Image:
    """API'siz test görseli: pastel degrade + yuvarlak kafalı basit karakter."""
    rnd = random.Random(prompt)
    ust = tuple(rnd.randint(200, 250) for _ in range(3))
    alt = tuple(rnd.randint(140, 210) for _ in range(3))
    img = Image.new("RGB", (GENISLIK, YUKSEKLIK))
    d = ImageDraw.Draw(img)
    for y in range(YUKSEKLIK):
        t = y / YUKSEKLIK
        d.line([(0, y), (GENISLIK, y)], fill=tuple(int(ust[i] * (1 - t) + alt[i] * t) for i in range(3)))
    cx, cy = GENISLIK // 2 + rnd.randint(-150, 150), 1150
    d.ellipse((cx - 170, cy - 170, cx + 170, cy + 170), fill="white", outline=(60, 60, 60), width=6)
    d.ellipse((cx - 70, cy - 20, cx - 40, cy + 30), fill="black")
    d.ellipse((cx + 40, cy - 20, cx + 70, cy + 30), fill="black")
    d.arc((cx - 40, cy + 40, cx + 40, cy + 90), 20, 160, fill="black", width=5)
    d.rounded_rectangle((cx - 120, cy + 170, cx + 120, cy + 520), 60, fill=(240, 240, 240), outline=(60, 60, 60), width=6)
    return img.filter(ImageFilter.SMOOTH)


def karakter_referansi(ayar: Ayarlar) -> Image.Image | None:
    if not ayar.karakter_referansi:
        return None
    yol = ayar.yol(ayar.karakter_referansi)
    return Image.open(yol).convert("RGB") if yol.exists() else None


def uret(ayar: Ayarlar, stil: str, sahne_tarifleri: list[str], klasor: Path) -> list[Path]:
    klasor.mkdir(parents=True, exist_ok=True)
    referans = karakter_referansi(ayar) if ayar.gorsel_saglayici == "gemini" and stil != "kil_figur" else None
    yollar = []
    for i, tarif in enumerate(sahne_tarifleri, 1):
        prompt = gorsel_prompt(stil, tarif)
        if ayar.gorsel_saglayici == "gemini":
            img = _gemini(ayar, prompt, referans)
        elif ayar.gorsel_saglayici == "yerel":
            img = _yerel(prompt, i)
        else:
            raise ValueError(f"Bilinmeyen görsel sağlayıcı: {ayar.gorsel_saglayici}")
        yol = klasor / f"sahne_{i:02d}.png"
        _dikey_kirp(img).save(yol)
        (klasor / f"sahne_{i:02d}.prompt.txt").write_text(prompt, encoding="utf-8")
        yollar.append(yol)
        print(f"  görsel {i}/{len(sahne_tarifleri)} hazır")
    return yollar
