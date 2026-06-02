/* ============================================================
   config.js — Uygulama ayarları ve analiz parametreleri
   Skor eşiklerini buradan değiştirerek motorun davranışını
   tek yerden ayarlayabilirsiniz.
   ============================================================ */
const CONFIG = {
  API_BASE: "https://finnhub.io/api/v1",

  // Hızlı erişim çipleri
  POPULAR: ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META", "AMD", "NFLX", "KO"],

  // Boyut ağırlıkları (toplam 1.00). Eksik veri olan boyut otomatik atlanır
  // ve kalan ağırlıklar yeniden normalize edilir.
  WEIGHTS: {
    valuation: 0.18,   // Değerleme
    profit:    0.17,   // Kârlılık
    growth:    0.15,   // Büyüme
    health:    0.15,   // Finansal sağlık
    technical: 0.25,   // Teknik / momentum — fiyat hareketine duyarlılık için artırıldı
    analyst:   0.10,   // Analist görüşü
  },

  // Skor -> karar bantları (alt sınır dahil)
  VERDICT_BANDS: [
    { min: 75, label: "GÜÇLÜ AL",   color: "var(--green)"   },
    { min: 60, label: "AL",          color: "var(--green-d)" },
    { min: 45, label: "TUT / NÖTR",  color: "var(--yellow)"  },
    { min: 32, label: "SAT",         color: "var(--orange)"  },
    { min: 0,  label: "GÜÇLÜ SAT",   color: "var(--red)"     },
  ],

  // Skorlama eşikleri: [çok iyi, iyi, orta, zayıf]
  // "up"  -> yüksek değer iyi (eşikten büyük/eşitse puan artar)
  // "down"-> düşük değer iyi (eşikten küçük/eşitse puan artar)
  THRESHOLDS: {
    pe:        { dir: "down", t: [15, 25, 40, 60]  },
    pb:        { dir: "down", t: [1.5, 3, 6, 10]   },
    ps:        { dir: "down", t: [2, 5, 10, 18]    },
    roe:       { dir: "up",   t: [20, 12, 5, 0]    },
    roa:       { dir: "up",   t: [12, 7, 3, 0]     },
    netMargin: { dir: "up",   t: [20, 10, 3, 0]    },
    grossMargin:{ dir: "up",  t: [50, 35, 20, 10]  },
    revGrowth: { dir: "up",   t: [20, 8, 2, -5]    },
    epsGrowth: { dir: "up",   t: [20, 8, 0, -10]   },
    rev5y:     { dir: "up",   t: [15, 8, 3, 0]     },
    currentRatio:{ dir: "up", t: [2, 1.5, 1, 0.8]  },
    debtEquity:{ dir: "down", t: [0.5, 1, 2, 3]    },
    quickRatio:{ dir: "up",   t: [1.5, 1, 0.7, 0.4]},
    ret52:     { dir: "up",   t: [25, 8, -5, -25]  },
    ret13:     { dir: "up",   t: [15, 3, -5, -15]  },
    ret_1m:    { dir: "up",   t: [10, 3, -3, -10]  },
    ret_1w:    { dir: "up",   t: [4, 1, -1, -4]    },
    rangePos:  { dir: "up",   t: [60, 40, 20, 5]   },
  },

  // report.json URL (GitHub Pages'te mutlak URL olur, lokalda relative çalışır)
  REPORT_URL: "./data/report.json",

  // BIST hisseleri hızlı erişim
  BIST_POPULAR: ["THYAO", "GARAN", "KCHOL", "TUPRS", "EREGL", "SISE", "ASELS"],
};
