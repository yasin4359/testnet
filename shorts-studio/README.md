# Shorts Studio: Dr. Linde & Mika

Konuşan bitkiler + uzman açıklaması formatında, **Almanca ve İngilizce** dikey Shorts üretim hattı.

```
episodes/*.json  ──prompts──▶  Google Flow (Veo) promptları  ──▶  klipler (shot başına 1)
                                                                      │
                               yayına hazır MP4 + başlık/açıklama ◀──build──┘
```

## Karakterler (kendi markamız, Dr.bota'dan farklı)
- **Dr. Linde**: 50'lerinde botanikçi kadın, gümüş kısa saç, yuvarlak yeşil gözlük, hardal kazak + koyu yeşil bahçe önlüğü.
- **Mika**: Kıvırcık kızıl saçlı, çilli, sarı yağmurluklu, mavi çizmeli, elinde büyüteç olan çocuk.
- Bölüme özel bitki karakterleri episode dosyasındaki `cast` alanında tanımlanır.

Tanımlar ve ses tarifleri `characters.json` içinde. Flow'da her karakter için bir kez avatar/"ingredient" oluşturup her shotta aynısını kullanın. Sesi de orada sabitleyin.

## Kurulum
Python 3.9+ ve ffmpeg yeterli (ffmpeg yoksa: `pip install imageio-ffmpeg`).
İsteğe bağlı, daha isabetli altyazı zamanlaması için: `pip install faster-whisper`

## Bir bölüm nasıl üretilir
1. **Promptları al**
   ```
   python studio.py prompts episodes/ep001_tomaten.json --lang de
   python studio.py prompts episodes/ep001_tomaten.json --lang en
   ```
   `out/ep001/flow_prompts_de.txt` dosyasında her shot için hazır bir prompt ve kayıt adı bulunur.
2. **Flow'da üret**: Dikey (9:16) ve sesli üretin. Her shotu verilen adla kaydedin:
   `clips/ep001/de/01.mp4`, `02.mp4`, … (İngilizce için `clips/ep001/en/…`).
   Görüntü iki dilde aynı olabilir; sadece konuşma dili değişir.
3. **Montaj**
   ```
   python studio.py build episodes/ep001_tomaten.json --lang de
   python studio.py build episodes/ep001_tomaten.json --lang en --music music/bg.mp3
   ```
   Çıktılar (`out/ep001/`):
   - `ep001_de.mp4`: 1080×1920, 30 fps, kelime kelime altyazı, filigran, -14 LUFS ses. Doğrudan yüklenebilir.
   - `ep001_de_upload.txt`: başlık, açıklama, hashtagler.
   - `ep001_de.srt`: YouTube'a ayrıca altyazı olarak yüklenebilir.

### Seçenekler
| Seçenek | Anlamı |
|---|---|
| `--align whisper` | Altyazı zamanlarını gerçek konuşmadan alır (faster-whisper gerekir). Varsayılan yöntem sessizlik algılamasına göre tahmin eder. |
| `--fit blur` | Yatay klipleri bulanık arka planla dikeye oturtur. Varsayılan `crop` ortadan kırpar. |
| `--music dosya` | Arka plan müziği; kısık seste eklenir ve süre boyunca döngüye alınır. |
| shotta `"trim": [1.2, 7.5]` | Klibin sadece o aralığını kullanır (baştaki/sondaki boşlukları kesmek için). |

Font, altyazı konumu, vurgu rengi ve filigran `studio.py` içindeki `CONFIG` bölümünden değişir.
Özel bir font (ör. *Luckiest Guy*, *Anton*) kullanmak için `.ttf` dosyasını `fonts/` klasörüne koyun ve adını `CONFIG["font"]` alanına yazın.
Senaryoda `*kelime*` yazılan kelimeler altyazıda sarı görünür.

## Yeni bölüm yazma kuralları
- 3 perde: **tartışma** (inatçı ve akıllı karakter) → **sonuç** (inatçı olan bedel öder) → **Mika sorar, Dr. Linde açıklar**.
- Shot başına tek konuşmacı, en fazla ~15–17 kelime (Veo klibi 8 sn). `prompts` komutu uzun satırlarda uyarı verir.
- Toplam süre 60 saniyenin altında kalmalı.
- Bilgi doğru ve her bölümde farklı olmalı. Konu listesi `topics.md` içinde.

## Notlar
- Veo'nun Almanca telaffuzunu ilk bölümlerde mutlaka dinleyin. Sorun olursa ses ElevenLabs ile üretilip klibe eklenebilir; bu durumda dudak senkronu için klibi sessiz üretin.
- YouTube'un "altered or synthetic content" beyanı gerçekçi görünen içerik için zorunlu; açıkça çizgi film olan videolarda genelde gerekmez.
