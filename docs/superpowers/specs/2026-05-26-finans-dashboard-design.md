# Finans Otomasyon Dashboard — Tasarım Spec

**Tarih:** 2026-05-26  
**Durum:** Onaylandı  

---

## Genel Bakış

Mevcut Hisse Analiz Motoru'nu; kişisel portföy yönetimi, otomatik sabah/haftalık raporlar, fiyat alarmları, döviz/makro takibi ve Telegram + Gmail bildirimleri ekleyerek tam bir finans otomasyon platformuna dönüştürme projesi.

---

## Kapsam

- **Borsalar:** ABD (NASDAQ/NYSE) + BIST  
- **Hisse sayısı:** 15 (8 ABD + 7 BIST) — kullanıcı değiştirebilir  
- **Başlangıç ABD listesi:** AAPL, MSFT, NVDA, AMZN, GOOGL, META, AMD, TSLA  
- **Başlangıç BIST listesi:** THYAO, GARAN, KCHOL, TUPRS, EREGL, SISE, ASELS  

---

## Mimari

```
GitHub Actions (cron: 09:00 TR / UTC 06:00)
    ↓
scripts/analyze.py
    ├── Finnhub API        → ABD hisseleri (tam 6 boyut analiz)
    ├── IsYatirim API      → BIST hisseleri (fiyat + temel veriler)
    └── ExchangeRate API   → USD/TRY, EUR/TRY, altın
    ↓
data/report.json           → GitHub Pages'e commit edilir
    ↓
index.html (Dashboard)
    ├── report.json        → Fiyatlar + skorlar (sunucudan)
    └── localStorage       → Portföy girişleri (tarayıcıda, özel)
        ↓ birleştirilir
    Portföy P&L + kişisel yorumlar (tamamen tarayıcıda hesaplanır)
    ↓
scripts/notify.py
    ├── Telegram Bot API   → Anlık + sabah + haftalık mesajlar
    └── Gmail SMTP         → Sabah + haftalık e-posta raporu

GitHub Actions (cron: her 30 dk)
    └── scripts/check_alarms.py → Fiyat alarmları kontrol + Telegram
```

**Not:** Portföy verisi (hisse adedi, alış fiyatı) yalnızca tarayıcının localStorage'ında saklanır — GitHub'a yüklenmez, sunucuya gönderilmez. report.json'daki güncel fiyatlarla tarayıcıda birleştirilir.

---

## Dashboard Bölümleri

### 1. Makro Şerit (en üst, sabit)
Her zaman görünür. Otomatik güncellenir.

| Gösterge | Kaynak |
|---|---|
| USD/TRY | ExchangeRate API |
| EUR/TRY | ExchangeRate API |
| Altın (USD/oz) | Finnhub (`/quote?symbol=OANDA:XAU_USD`) |
| BIST 100 | IsYatirim |
| S&P 500 | Finnhub |
| TR Faiz Oranı | Statik değer (GitHub Secrets'a elle girilir, değişince güncellenir) |

### 2. Fırsat Tarayıcı
- 15 hisse, puana göre sıralı tablo
- Sütunlar: Sıra, Hisse, Skor (0-100), Karar (AL/TUT/SAT), Boyut barları, Risk seviyesi, Günlük %, Borsa
- Satıra tıklayınca sağdan detay paneli açılır:
  - Genel skor + karar + gerekçe metni
  - Güçlü yönler / zayıf yönler (pro-con)
  - 6 boyut detayı: her biri için progress bar + metrikler + açıklama
- BIST verisinde eksik boyut varsa "Veri yok" gösterilir, skor normalize edilir

### 3. Kişisel Portföy
**Veri girişi** (tarayıcıda, localStorage'da saklanır):
- Hisse sembolü, adet, alış fiyatı, alış tarihi

**Göstergeler:**
- Toplam portföy değeri (TL)
- Toplam kâr/zarar (TL ve %)
- Her hisse: mevcut fiyat, toplam alış maliyeti, mevcut değer, P&L (TL + %)
- Her hisse için kişisel yorum: skor + P&L'yi birleştiren karar metni
  - Örnek: "NVDA'da +%45 kârdasınız, skor 89 — Tutun, yükseliş devam edebilir."
  - Örnek: "GARAN'da -%12 zarardayken SAT sinyali güçlendi — Zararı kesmek mantıklı."

**Kıyaslama:**
- Portföy getirisi vs S&P 500 aynı dönem getirisi
- Portföy getirisi vs BIST 100 aynı dönem getirisi
- Görsel: çizgi grafik veya yüzde karşılaştırma çubuğu

### 4. Fiyat Alarmları
**Kural tanımı** (kullanıcı girer):
- Hisse, yön (altına / üstüne), hedef fiyat
- Örnek: "NVDA < $900 olunca bildir"

**Kontrol mekanizması:**
- GitHub Action her 30 dakikada çalışır
- Kural tetiklenince Telegram'a anlık mesaj gider
- Tetiklenen alarm devre dışı kalır (tekrar etmez), kullanıcı yeniden açabilir

### 5. Temettü Takvimi
- Takip edilen hisselerin bir sonraki temettü tarihleri (Finnhub `/stock/dividend`)
- Tahmini gelir = adet × temettü/hisse
- Tarihten 3 gün önce Telegram + e-posta hatırlatıcısı gönderilir

---

## Bildirimler

| Zamanlama | Kanal | İçerik |
|---|---|---|
| Her gün 09:00 TR | Telegram + Gmail | Sabah raporu: Top 3 fırsat, portföy özeti, risk uyarıları |
| Pazartesi 09:00 TR | Telegram + Gmail | Haftalık performans özeti + S&P/BIST kıyaslaması |
| Alarm tetiklenince | Telegram | Fiyat alarm bildirimi |
| Temettü -3 gün | Telegram + Gmail | Temettü hatırlatıcısı |

**Sabah raporu formatı (Telegram):**
```
☀️ Sabah Raporu — 26 Mayıs 09:00

📈 Top 3 Fırsat:
1. NVDA — 89/100 GÜÇLÜ AL (+2.4%)
2. AAPL — 76/100 GÜÇLÜ AL (+0.8%)
3. THYAO — 71/100 AL (+1.2%)

💼 Portföyünüz:
Toplam değer: ₺42.500 (+%8.3)
NVDA: +%45 | GARAN: -%12 ⚠️

⚠️ Risk Uyarısı:
GARAN SAT bölgesinde (41/100)

💱 Döviz: USD/TRY 32.45 | Altın $2.318
```

---

## Veri Kaynakları

| Kaynak | Kullanım | Plan |
|---|---|---|
| Finnhub.io | ABD hisseleri — tam analiz | Ücretsiz (60 req/dk) |
| IsYatirim | BIST fiyat + temel veriler | Gayri resmi, kırılırsa uyarı göster |
| ExchangeRate-API | USD/TRY, EUR/TRY | Ücretsiz tier |
| Finnhub (XAU_USD) | Altın fiyatı | Ücretsiz tier |

**BIST veri politikası:** IsYatirim API yanıt vermezse ilgili hisseye "Veri alınamadı — manuel kontrol edin" uyarısı gösterilir, geri kalan hisseler etkilenmez.

---

## Güvenlik

Kod içinde hiçbir hassas bilgi saklanmaz. Tüm anahtarlar GitHub Secrets'a girilir:

| Secret | Açıklama |
|---|---|
| `FINNHUB_KEY` | Finnhub API anahtarı |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token |
| `TELEGRAM_CHAT_ID` | Kullanıcının Telegram chat ID'si |
| `GMAIL_ADDRESS` | Gönderen Gmail adresi |
| `GMAIL_APP_PASSWORD` | Gmail uygulama şifresi (2FA gerekli) |

Portföy verisi yalnızca tarayıcının localStorage'ında tutulur; adet, alış fiyatı ve alış tarihi hiçbir zaman GitHub'a yüklenmez veya sunucuya gönderilmez. Portföy hesaplamaları (P&L, kişisel yorumlar) tamamen tarayıcıda yapılır.

---

## Dosya Yapısı

```
finans/
├── index.html                  # Dashboard (genişletilmiş)
├── portfolio.json              # Boş şablon (gerçek veri localStorage'da)
├── data/
│   └── report.json             # Günlük analiz çıktısı (Actions tarafından commit edilir)
├── assets/
│   ├── css/style.css
│   └── js/
│       ├── config.js
│       ├── api.js
│       ├── analysis.js
│       ├── ui.js
│       ├── app.js
│       ├── portfolio.js        # YENİ: Portföy modülü
│       ├── alarms.js           # YENİ: Fiyat alarmları
│       └── macro.js            # YENİ: Makro şerit
├── scripts/
│   ├── analyze.py              # YENİ: Ana analiz scripti
│   ├── notify.py               # YENİ: Telegram + Gmail bildirimi
│   └── check_alarms.py         # YENİ: 30 dk'da bir fiyat alarm kontrolü
└── .github/
    └── workflows/
        ├── daily.yml           # YENİ: Sabah 09:00 TR analiz + bildirim
        ├── weekly.yml          # YENİ: Pazartesi haftalık rapor
        └── alarms.yml          # YENİ: Her 30 dk alarm kontrolü
```

---

## Kısıtlar & Riskler

| Risk | Önlem |
|---|---|
| IsYatirim API kırılırsa | Graceful fallback: hisse "Veri yok" olarak işaretlenir |
| Finnhub rate limit (60/dk) | 15 hisse × 5 endpoint = 75 req; 2 sn aralıkla çağrı |
| GitHub Actions gecikme | Cron ±5 dk sapabilir, kritik değil |
| Gmail şifre değişikliği | App password kullanılır, ana şifreden bağımsız |
