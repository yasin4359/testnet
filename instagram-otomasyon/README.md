# Instagram Reels Otomasyonu

Fikirden paylaşıma kadar otomatik çalışan Reels üretim sistemi. Örnek alınan sayfalar:
@fenamontaj, @kahvekaresi, @dronemredikmen, @mekanikruh.co.

```
Tema seç ─► Claude: metin + sahne tarifleri + açıklama/hashtag
        ─► Gemini: her sahne için 9:16 görsel (aynı karakter)
        ─► FFmpeg: hareket + el yazısı metin + geçiş + müzik + kapanış logosu
        ─► (isteğe bağlı onay) ─► Instagram Graph API ile Reels paylaşımı
```

## Örnek videolardan çıkarılan format

| Özellik | Örneklerde | Sistemde |
|---|---|---|
| Süre | 17–60 sn, çoğu 18–27 sn | Metin uzunluğuna göre ~15–30 sn |
| Yapı | 3–7 sahne, her sahnede tek cümle; ilk cümle kanca ("Bazı zamanlar anneme bakınca;") | Claude aynı kalıpla yazar |
| Görsel | Yapay zekâ çizimi, yuvarlak beyaz kafalı sevimli karakter, üst kısım boş | `otomasyon/stiller.py` |
| Hareket | Görseller hafifçe canlandırılmış (PixVerse filigranı var) | Ken Burns yakınlaşma/uzaklaşma (ücretsiz) |
| Yazı | Üstte, ortalı, el yazısı font, altında küçük kalp | Patrick Hand fontu + çizilmiş kalp |
| Ses | Sadece müzik, seslendirme yok | `assets/muzik` klasöründen rastgele parça |
| Kapanış | Görüntü kararır, Instagram logosu ve @hesap | Otomatik |

Stiller: `sicak_illustrasyon` (anne/dua videoları), `karakalem` ("Şunu unutma;" videosu),
`kil_figur` ("Kendimden özür diliyorum" videosu), `metafor` (@mekanikruh tarzı).

## Kurulum

```bash
cd instagram-otomasyon
pip install -r requirements.txt        # ffmpeg ayrıca kurulu değilse imageio-ffmpeg kullanılır
cp config.example.yaml config.yaml     # hesap adınızı, temaları, stilleri düzenleyin
cp .env.example .env                   # anahtarları girin
```

`.env` içinde gerekenler:

| Değişken | Nereden |
|---|---|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com → API Keys |
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey |
| `IG_USER_ID`, `IG_ACCESS_TOKEN` | Aşağıdaki "Instagram bağlantısı" bölümü |

**Müzik:** `assets/muzik/` klasörüne telifsiz müzikler (mp3/m4a/wav) koyun. Telifli şarkı kullanmak
videonun sessize alınmasına veya kaldırılmasına yol açabilir. Instagram'ın uygulama içi müziği API ile eklenemez.

**Karakter tutarlılığı (önerilir):** Beğendiğiniz bir karakter görselini `assets/karakter.png` olarak kaydedin.
Her sahnede bu görsel referans verilir; böylece tüm videolarda aynı karakter görünür ve sayfa bir "marka" kazanır.

## Kullanım

```bash
python main.py uret                                   # rastgele tema + stil
python main.py uret --tema "anne sevgisi" --stil sicak_illustrasyon
python main.py uret --senaryo ornek_senaryo.json      # Claude'suz, kendi metninizle
python main.py onayla cikti/20260926-101500_konu      # kontrol ettiğiniz videoyu sıraya alın
python main.py siradaki                               # onaylı en eski videoyu paylaş
python main.py yayinla cikti/20260926-101500_konu     # belirli videoyu hemen paylaş
python main.py otomatik                               # üret, onay_gerekli: false ise paylaş
```

Her video `cikti/<tarih>_<konu>/` altında durur: `video.mp4`, `aciklama.txt`, `senaryo.json`,
sahne görselleri ve kullanılan görsel promptları. `cikti/gecmis.json` işlenen konuları tutar;
Claude aynı konuyu tekrar yazmaz.

**API'siz deneme:** `config.yaml` içinde `gorsel_saglayici: yerel` yapıp
`python main.py uret --senaryo ornek_senaryo.json` çalıştırın. Montaj hattının tamamını hiçbir anahtar olmadan test eder.

## Instagram bağlantısı (bir kerelik)

1. Instagram hesabını **Profesyonel hesap** (İşletme veya İçerik Üreticisi) yapın.
2. https://developers.facebook.com → **Uygulama oluştur** → "Instagram API" ürününü ekleyin.
3. "Instagram girişi ile API" kurulumunda hesabınızı bağlayın, `instagram_business_basic` ve
   `instagram_business_content_publish` izinlerini verin, **uzun ömürlü token** oluşturun.
   - Bu yolu kullanıyorsanız `config.yaml` içinde `instagram_api_host: graph.instagram.com` yapın.
   - Facebook sayfası üzerinden bağladıysanız `graph.facebook.com` olarak kalsın.
4. Token'ı `IG_ACCESS_TOKEN`, hesap kimliğini `IG_USER_ID` olarak `.env`'e yazın.
5. Uzun ömürlü token 60 gün geçerlidir; süresi dolmadan yenileyin.

Paylaşım resmî API ile yapılır, hesap şifresi kullanılmaz; bot tespiti ve hesap kapanma riski yoktur.
API ile günde en fazla 50 gönderi paylaşılabilir.

## Zamanlama

Bilgisayarınızda veya bir sunucuda her gün otomatik çalıştırmak için:

**Linux/macOS (cron):** `crontab -e`
```
0 9  * * * cd /yol/instagram-otomasyon && python main.py uret      >> log.txt 2>&1
0 19 * * * cd /yol/instagram-otomasyon && python main.py siradaki  >> log.txt 2>&1
```
Sabah video üretilir, siz gün içinde bakıp `onayla` dersiniz, akşam 19:00'da paylaşılır.
Tam otomatik için `onay_gerekli: false` yapıp tek satır `python main.py otomatik` yeterli.

**Windows:** Görev Zamanlayıcı → Temel görev → Program: `python`, Bağımsız değişken: `main.py otomatik`,
Başlangıç konumu: bu klasör.

## Maliyet (yaklaşık, video başına)

| Kalem | Tutar |
|---|---|
| Claude (senaryo) | ~0,03–0,10 $ |
| Gemini görsel (4–6 sahne) | ~0,15–0,25 $ |
| Montaj, yayın | Ücretsiz |

Günde 2 video ≈ ayda 15–20 $.

## Geliştirme fikirleri

- Görselleri gerçek animasyona çevirme (PixVerse/Kling image-to-video API'si), örneklerdeki gibi.
- Instagram Insights'tan izlenme verilerini çekip en iyi performans gösteren temaları öne alma.
- Telegram botu ile telefondan onay verme.
