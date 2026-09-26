"""FFmpeg ile Reels montajı.

Örnek videolardaki yapı:
  - her sahne: tek görsel + hafif yakınlaşma/uzaklaşma (Ken Burns)
  - üstte el yazısı fontlu metin, yumuşakça belirir, altında küçük bir kalp
  - sahneler arası yumuşak geçiş (fade)
  - sonda görüntü kararır, Instagram logosu + @hesap adı çıkar
  - arkada duygusal müzik, sonda yavaşça kısılır
"""

from __future__ import annotations

import math
import random
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .config import Ayarlar
from .gorsel import GENISLIK, YUKSEKLIK

FPS = 30
GECIS = 0.5  # sahneler arası geçiş süresi (sn)
KAPANIS = 2.2  # sondaki logo ekranı süresi (sn)
MUZIK_UZANTILARI = {".mp3", ".m4a", ".aac", ".wav", ".ogg"}


def ffmpeg_yolu() -> str:
    yol = shutil.which("ffmpeg")
    if yol:
        return yol
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as e:
        raise RuntimeError("ffmpeg bulunamadı. Kurun ya da `pip install imageio-ffmpeg` çalıştırın.") from e


def _calistir(args: list[str]) -> None:
    sonuc = subprocess.run([ffmpeg_yolu(), "-hide_banner", "-loglevel", "error", "-y", *args], capture_output=True, text=True)
    if sonuc.returncode != 0:
        raise RuntimeError(f"ffmpeg hatası:\n{sonuc.stderr[-2000:]}")


def sahne_suresi(metin: str) -> float:
    """Okuma süresine göre sahne süresi: kısa cümle ~3 sn, uzun cümle ~7 sn."""
    return round(min(7.0, max(3.0, 2.4 + 0.06 * len(metin))), 2)


# ---------------------------------------------------------------- yazı katmanı

def _kalp(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int, renk, kalinlik: int = 4) -> None:
    noktalar = []
    for i in range(0, 361, 4):
        t = math.radians(i)
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        noktalar.append((cx + x * r / 16, cy - y * r / 16))
    d.line(noktalar, fill=renk, width=kalinlik, joint="curve")


def _sar(metin: str, font: ImageFont.FreeTypeFont, genislik: int) -> list[str]:
    satirlar: list[str] = []
    for paragraf in metin.split("\n"):
        kelimeler, satir = paragraf.split(), ""
        for k in kelimeler:
            aday = f"{satir} {k}".strip()
            if font.getlength(aday) <= genislik or not satir:
                satir = aday
            else:
                satirlar.append(satir)
                satir = k
        satirlar.append(satir)
    return satirlar


def yazi_katmani(ayar: Ayarlar, metin: str, renk, hedef: Path) -> None:
    n = len(metin)
    boyut = 92 if n < 30 else 80 if n < 55 else 68
    font = ImageFont.truetype(str(ayar.yol(ayar.font)), boyut)
    img = Image.new("RGBA", (GENISLIK, YUKSEKLIK), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    satirlar = _sar(metin, font, 900)
    satir_y = int(boyut * 1.18)
    y = 200
    # Açık renkli, yazının okunmasını kolaylaştıran çok hafif bir hale
    for s in satirlar:
        w = font.getlength(s)
        x = (GENISLIK - w) / 2
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            d.text((x + dx, y + dy), s, font=font, fill=(255, 255, 255, 90))
        d.text((x, y), s, font=font, fill=(*renk, 255), stroke_width=2, stroke_fill=(*renk, 255))
        y += satir_y
    _kalp(d, GENISLIK // 2, y + 40, 26, (*renk, 255))
    img.save(hedef)


def kapanis_katmani(ayar: Ayarlar, hedef: Path) -> None:
    img = Image.new("RGBA", (GENISLIK, YUKSEKLIK), (0, 0, 0, 150))
    d = ImageDraw.Draw(img)
    cx, cy, r = GENISLIK // 2, 1400, 70
    # Basit Instagram simgesi: yuvarlatılmış kare + daire + nokta
    d.rounded_rectangle((cx - r, cy - r, cx + r, cy + r), radius=40, outline="white", width=11)
    d.ellipse((cx - 33, cy - 33, cx + 33, cy + 33), outline="white", width=11)
    d.ellipse((cx + 37, cy - 50, cx + 51, cy - 36), fill="white")
    font = ImageFont.truetype(str(ayar.yol(ayar.font)), 58)
    etiket = f"@{ayar.hesap_adi.upper()}"
    d.text(((GENISLIK - font.getlength(etiket)) / 2, cy + r + 30), etiket, font=font, fill="white")
    img.save(hedef)


# ---------------------------------------------------------------- video

def _sahne_klibi(gorsel: Path, yazi: Path, sure: float, yakinlas: bool, kapanis: Path | None, hedef: Path) -> None:
    kare = int(round(sure * FPS))
    z = f"min(1+0.10*on/{kare},1.10)" if yakinlas else f"max(1.10-0.10*on/{kare},1.0)"
    girdiler = ["-i", str(gorsel), "-loop", "1", "-t", f"{sure}", "-i", str(yazi)]
    filtre = (
        f"[0:v]scale={GENISLIK * 2}:{YUKSEKLIK * 2},"
        f"zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={kare}:s={GENISLIK}x{YUKSEKLIK}:fps={FPS}[bg];"
        f"[1:v]format=rgba,fade=in:st=0.2:d=0.6:alpha=1[tx];"
        f"[bg][tx]overlay=0:0[v0]"
    )
    son = "v0"
    if kapanis is not None:
        girdiler += ["-loop", "1", "-t", f"{sure}", "-i", str(kapanis)]
        filtre += f";[2:v]format=rgba,fade=in:st={sure - KAPANIS}:d=0.5:alpha=1[ks];[v0][ks]overlay=0:0[v1]"
        son = "v1"
    _calistir([
        *girdiler, "-filter_complex", filtre + f";[{son}]format=yuv420p[out]", "-map", "[out]",
        "-t", f"{sure}", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "18", str(hedef),
    ])


def _muzik_sec(ayar: Ayarlar) -> Path | None:
    klasor = ayar.yol(ayar.muzik_klasoru)
    if not klasor.exists():
        return None
    parcalar = [p for p in klasor.iterdir() if p.suffix.lower() in MUZIK_UZANTILARI]
    return random.choice(parcalar) if parcalar else None


def birlestir(ayar: Ayarlar, gorseller: list[Path], metinler: list[str], stil_bilgisi: dict, hedef: Path) -> Path:
    gecici = hedef.parent / "_parcalar"
    gecici.mkdir(parents=True, exist_ok=True)
    kapanis = gecici / "kapanis.png"
    kapanis_katmani(ayar, kapanis)

    sureler, klipler = [], []
    for i, (gorsel, metin) in enumerate(zip(gorseller, metinler)):
        sure = sahne_suresi(metin)
        son_sahne = i == len(gorseller) - 1
        if son_sahne:
            sure += KAPANIS
        yazi = gecici / f"yazi_{i:02d}.png"
        yazi_katmani(ayar, metin, stil_bilgisi["yazi_rengi"], yazi)
        klip = gecici / f"klip_{i:02d}.mp4"
        _sahne_klibi(gorsel, yazi, sure, yakinlas=i % 2 == 0, kapanis=kapanis if son_sahne else None, hedef=klip)
        sureler.append(sure)
        klipler.append(klip)
        print(f"  sahne {i + 1}/{len(gorseller)} kurgulandı ({sure} sn)")

    toplam = sum(sureler) - GECIS * (len(sureler) - 1)
    girdiler: list[str] = []
    for k in klipler:
        girdiler += ["-i", str(k)]

    # Geçişleri zincirle: [0][1]xfade -> [x1]; [x1][2]xfade -> [x2] ...
    parcalar, onceki, zaman = [], "0:v", 0.0
    for i in range(1, len(klipler)):
        zaman += sureler[i - 1] - GECIS
        etiket = f"x{i}"
        parcalar.append(f"[{onceki}][{i}:v]xfade=transition={stil_bilgisi['gecis']}:duration={GECIS}:offset={zaman:.3f}[{etiket}]")
        onceki = etiket
    video_etiketi = onceki if len(klipler) > 1 else "0:v"

    muzik = _muzik_sec(ayar)
    ses_idx = len(klipler)
    if muzik:
        girdiler += ["-stream_loop", "-1", "-i", str(muzik)]
        parcalar.append(
            f"[{ses_idx}:a]atrim=0:{toplam:.3f},asetpts=PTS-STARTPTS,"
            f"afade=t=in:d=0.5,afade=t=out:st={max(0, toplam - 1.8):.3f}:d=1.8,volume=0.9[a]"
        )
    else:
        girdiler += ["-f", "lavfi", "-t", f"{toplam:.3f}", "-i", "anullsrc=r=44100:cl=stereo"]
        parcalar.append(f"[{ses_idx}:a]anull[a]")

    video_map = f"[{video_etiketi}]" if len(klipler) > 1 else "0:v"
    _calistir([
        *girdiler, "-filter_complex", ";".join(parcalar), "-map", video_map, "-map", "[a]",
        "-t", f"{toplam:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-ar", "44100", "-movflags", "+faststart", str(hedef),
    ])
    shutil.rmtree(gecici, ignore_errors=True)
    print(f"  video: {hedef} ({toplam:.1f} sn, müzik: {muzik.name if muzik else 'yok'})")
    return hedef
