"""Örnek videolardan çıkarılan görsel stiller.

Her stil, görsel üreticiye her sahnede aynen eklenen sabit bir tarif içerir;
böylece karakter ve atmosfer videolar arasında tutarlı kalır.
"""

KARAKTER = (
    "a cute minimalist cartoon character with a big perfectly round white head, "
    "two small black oval dot eyes, a few thin hair strands on top, tiny simple smile, "
    "small body, simple clothes"
)

ORTAK = (
    "vertical 9:16 composition, the character placed in the lower two thirds, "
    "leave the TOP THIRD of the image calm and empty (plain background area) for a caption, "
    "absolutely no text, no letters, no words, no captions, no watermark, no logo"
)

STILLER: dict[str, dict] = {
    # @fenamontaj / anne ve dua videoları: sıcak renkli, samimi ev ortamı
    "sicak_illustrasyon": {
        "tarif": (
            "warm cozy hand-drawn illustration, soft pencil lines with watercolor coloring, "
            "golden hour sunlight through a window, wooden furniture, plants, candles, "
            "a sleeping tabby cat, gentle emotional atmosphere, storybook style"
        ),
        "yazi_rengi": (40, 34, 30),
        "gecis": "fade",
    },
    # "Şunu unutma; suyu ateş ile buhar ederler" tarzı: karakalem, beyaz fon
    "karakalem": {
        "tarif": (
            "black and white pencil sketch on clean white paper, minimal line art, "
            "subtle graphite shading, only small accents of color allowed (like fire), "
            "lots of white empty space, thoughtful melancholic mood"
        ),
        "yazi_rengi": (25, 25, 25),
        "gecis": "fade",
    },
    # "Kendimden özür diliyorum" tarzı: kraft kâğıt üzerinde kil/ahşap figürler
    "kil_figur": {
        "tarif": (
            "3D miniature clay and wooden figurine diorama photographed on crumpled beige kraft paper, "
            "the character is a wooden bead head doll with a sleepy face and thin black wire limbs, "
            "soft studio light, shallow depth of field, symbolic props, emotional and poetic"
        ),
        "yazi_rengi": (45, 38, 30),
        "gecis": "fadeblack",
    },
    # @mekanikruh tarzı: krem fon, sembolik/metaforik sahneler
    "metafor": {
        "tarif": (
            "hand-drawn colored pencil illustration on cream old paper background, "
            "symbolic metaphorical scene with dark silhouette figures contrasting the bright main character, "
            "surreal but simple, fable-like"
        ),
        "yazi_rengi": (30, 30, 30),
        "gecis": "fade",
    },
}


def gorsel_prompt(stil: str, sahne_tarifi: str) -> str:
    s = STILLER[stil]
    karakter = "" if stil == "kil_figur" else f"Main character: {KARAKTER}. "
    return f"{sahne_tarifi}. {karakter}Style: {s['tarif']}. {ORTAK}."
