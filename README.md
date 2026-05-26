# 📊 Hisse Analiz Motoru

Hisse senetlerini **6 boyutta** puanlayıp **AL / TUT / SAT** kararı üreten, tamamen tarayıcıda çalışan statik bir web uygulaması. Verileri [Finnhub.io](https://finnhub.io) ücretsiz API'sinden çeker.

> ⚠️ **Yatırım tavsiyesi değildir.** Eğitim ve karşılaştırma amaçlı, kural tabanlı bir hesaplama aracıdır.

---

## 🔐 Güvenlik — Public repo için önemli

**Bu projede hiçbir API anahtarı veya hassas bilgi YOKTUR.**

- API anahtarı koda gömülü değildir. Kullanıcı arayüzden kendi anahtarını girer ve anahtar yalnızca **tarayıcının `localStorage`** alanında, o kişinin cihazında saklanır.
- Yani bu repoyu gönül rahatlığıyla **public** yayınlayabilirsiniz; deponun içinde sızdırılacak bir sır bulunmaz.
- Repoyu kullanan herkes kendi ücretsiz anahtarını girer.

`.gitignore`, yanlışlıkla anahtar içeren dosyaların (`.env`, `secrets.*` vb.) commit'lenmesini engeller.

---

## 🚀 Çalıştırma

### Seçenek 1 — Çift tıkla aç
`index.html` dosyasına çift tıklayın. Hiçbir kurulum gerekmez (tüm scriptler klasik `<script>` ile yüklenir, `file://` üzerinden çalışır).

### Seçenek 2 — Yerel sunucu (önerilir)
```bash
# Python ile
python3 -m http.server 8000
# sonra: http://localhost:8000

# veya Node ile
npx serve .
```

---

## 🔑 Finnhub anahtarı alma

1. [finnhub.io/register](https://finnhub.io/register) adresinden ücretsiz kayıt olun.
2. Panelden API anahtarınızı kopyalayın.
3. Uygulamada sağ üstteki kutuya yapıştırıp **Kaydet**'e basın.

---

## 📁 Proje yapısı

```
finans/
├── index.html              Arayüz iskeleti
├── README.md               Bu dosya
├── .gitignore
└── assets/
    ├── css/style.css       Tüm stiller
    └── js/
        ├── config.js       Ayarlar + skor ağırlıkları/eşikleri
        ├── api.js          Finnhub API istemcisi
        ├── analysis.js     Analiz motoru (saf hesaplama)
        ├── ui.js           Görselleştirme + biçimlendirme
        └── app.js          Olay yönetimi / orkestrasyon
```

---

## 🧠 Analiz nasıl çalışır?

Her hisse 6 boyutta 0–100 puanlanır; ağırlıklı ortalama genel skoru verir.

| Boyut | Ağırlık | Bakılan veriler |
|-------|---------|-----------------|
| Değerleme | %20 | F/K, PD/DD, P/S |
| Kârlılık | %20 | ROE, ROA, net marj, brüt marj |
| Büyüme | %20 | Gelir & EPS büyümesi (YoY + 5 yıl) |
| Finansal Sağlık | %15 | Cari oran, borç/özkaynak, likidite |
| Teknik / Momentum | %15 | 52H getiri, 3 ay getiri, banttaki konum, beta |
| Analist Görüşü | %10 | Al/Tut/Sat konsensüsü |

Bir boyutun verisi eksikse o boyut atlanır ve kalan ağırlıklar yeniden normalize edilir.

**Karar bantları:** ≥75 Güçlü Al · 60–74 Al · 45–59 Tut · 32–44 Sat · <32 Güçlü Sat

Eşik ve ağırlıkları `assets/js/config.js` dosyasından değiştirebilirsiniz.

---

## 🔗 Paylaşılabilir link

`?symbol=AAPL` parametresiyle açılırsa o hisse otomatik analiz edilir:
```
.../index.html?symbol=NVDA
```

---

## 🌐 Yayınlama (deploy)

Statik olduğu için herhangi bir yere atılabilir:

- **GitHub Pages:** repo ayarlarından Pages'i açın, kaynak olarak ana dalı seçin.
- **Netlify / Vercel:** klasörü sürükleyip bırakın ya da repoyu bağlayın.

---

## 📝 Lisans

MIT — dilediğiniz gibi kullanın, değiştirin, paylaşın.
