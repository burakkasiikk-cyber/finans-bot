# Finans Otomasyon Dashboard — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mevcut statik Hisse Analiz Motoru'nu; her sabah 09:00'da otomatik çalışan Python analiz scripti, Telegram + Gmail bildirimleri, kişisel portföy takibi, fiyat alarmları, döviz/makro şerit ve GitHub Pages deploy ile tam bir otomasyon platformuna dönüştür.

**Architecture:** GitHub Actions her gün 09:00 TR (06:00 UTC) ve Pazartesi'leri çalışır. Python scripti Finnhub (ABD hisseleri) + yfinance (BIST hisseleri) + ExchangeRate-API (döviz/makro) verilerini çekip `data/report.json` üretir ve main branch'e commit eder. GitHub Pages bu JSON'ı sunar; dashboard her açılışta okur. Portföy verisi yalnızca localStorage'da saklanır, hiçbir zaman sunucuya gitmez. Telegram Bot API + Gmail SMTP aynı Actions run'ında çağrılır. Alarm kontrolü ayrı bir workflow ile her 30 dakikada çalışır.

**Tech Stack:** Python 3.11, pytest, requests, yfinance 0.2+, GitHub Actions, GitHub Pages, Telegram Bot API, smtplib (stdlib), JavaScript ES6 modules

---

## Dosya Yapısı

```
finans/
├── data/
│   └── report.json              # YENİ — Python çıktısı, Actions tarafından commit edilir
├── scripts/
│   ├── __init__.py              # YENİ — boş, pytest için
│   ├── analyze.py               # YENİ — ana analiz scripti
│   ├── notify.py                # YENİ — Telegram + Gmail bildirimleri
│   └── check_alarms.py          # YENİ — 30 dk'da bir alarm kontrolü
├── tests/
│   ├── __init__.py              # YENİ — boş
│   ├── test_scoring.py          # YENİ — puanlama mantığı testleri
│   ├── test_analyze.py          # YENİ — analyze.py testleri (mock HTTP)
│   └── test_notify.py           # YENİ — notify.py testleri (mock)
├── assets/js/
│   ├── macro.js                 # YENİ — makro şerit modülü
│   ├── portfolio.js             # YENİ — portföy modülü
│   ├── alarms.js                # YENİ — fiyat alarmları UI
│   ├── dividend.js              # YENİ — temettü takvimi
│   ├── config.js                # DEĞİŞTİR — BIST semboller, report.json URL
│   ├── app.js                   # DEĞİŞTİR — yeni modülleri bağla
│   └── [mevcut dosyalar]        # api.js, analysis.js, ui.js — değişmez
├── assets/css/style.css         # DEĞİŞTİR — yeni bölümlerin stilleri
├── index.html                   # DEĞİŞTİR — makro şerit, portföy, alarmlar, temettü bölümleri
├── requirements.txt             # YENİ — Python bağımlılıkları
└── .github/workflows/
    ├── daily.yml                # YENİ — sabah 09:00 TR analiz + bildirim
    ├── weekly.yml               # YENİ — Pazartesi haftalık rapor
    └── alarms.yml               # YENİ — her 30 dk alarm kontrolü
```

---

## Task 1: report.json Şeması + Başlangıç Dosyası

**Files:**
- Create: `data/report.json`
- Create: `data/.gitkeep` (boş, dizini git'te tut)

- [ ] **Step 1: Veri şemasını belgele ve başlangıç dosyası oluştur**

```json
{
  "generated_at": "2026-05-26T06:03:00Z",
  "macro": {
    "usd_try": 32.45,
    "eur_try": 35.12,
    "gold_usd": 2318.50,
    "sp500": 5280.30,
    "sp500_change_pct": 0.42,
    "bist100": 9850.20,
    "bist100_change_pct": -0.18,
    "tr_interest_rate": 46.0
  },
  "stocks": [
    {
      "symbol": "NVDA",
      "name": "NVIDIA Corporation",
      "exchange": "NASDAQ",
      "price": 1125.40,
      "change_pct": 2.4,
      "score": 89,
      "verdict": "GÜÇLÜ AL",
      "verdict_key": "STRONG_BUY",
      "risk": "low",
      "dimensions": {
        "valuation": {
          "score": 78,
          "metrics": { "pe": 45.2, "pb": 28.1, "ps": 18.3 }
        },
        "profit": {
          "score": 92,
          "metrics": { "roe": 124.0, "roa": 55.0, "net_margin": 55.0, "gross_margin": 76.0 }
        },
        "growth": {
          "score": 95,
          "metrics": { "rev_growth": 77.0, "eps_growth": 85.0, "rev_5y": 42.0 }
        },
        "health": {
          "score": 65,
          "metrics": { "current_ratio": 4.2, "debt_equity": 0.42, "quick_ratio": 3.8 }
        },
        "technical": {
          "score": 88,
          "metrics": { "ret52": 210.0, "ret13": 38.0, "range_pos": 88.0 }
        },
        "analyst": {
          "score": 80,
          "metrics": { "buy": 38, "hold": 5, "sell": 1 }
        }
      },
      "pros": ["Gelir büyümesi YoY +77%", "Net marj %55", "Analist konsensüsü güçlü"],
      "cons": ["F/K oranı 45x — tarihsel ortalamanın üstü", "Beta 1.8"],
      "dividends": []
    }
  ],
  "top3": ["NVDA", "AAPL", "THYAO"],
  "risk_alerts": ["GARAN"],
  "weekly_summary": null
}
```

Dosyayı `data/report.json` olarak kaydet (gerçek değerlerle değil, bu şema ile).

- [ ] **Step 2: Commit**

```bash
mkdir -p data
touch data/.gitkeep
git add data/report.json data/.gitkeep
git commit -m "feat: add report.json schema"
```

---

## Task 2: Python Ortamı Kurulumu

**Files:**
- Create: `requirements.txt`
- Create: `scripts/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: requirements.txt oluştur**

```
requests==2.31.0
yfinance==0.2.38
pytest==8.1.0
pytest-mock==3.12.0
```

- [ ] **Step 2: Paket dosyaları oluştur**

```bash
touch scripts/__init__.py tests/__init__.py
```

- [ ] **Step 3: Bağımlılıkları yükle ve test et**

```bash
pip install -r requirements.txt
python -c "import requests, yfinance, pytest; print('OK')"
```

Beklenen çıktı: `OK`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt scripts/__init__.py tests/__init__.py
git commit -m "feat: add Python environment"
```

---

## Task 3: Puanlama Mantığı (Saf Python, TDD)

**Files:**
- Create: `scripts/scoring.py`
- Create: `tests/test_scoring.py`

- [ ] **Step 1: Testleri yaz**

`tests/test_scoring.py`:
```python
import pytest
from scripts.scoring import score_metric, verdict_of, dim_score, WEIGHTS

def test_score_pe_low_is_great():
    # PE < 15 → 92 (çok iyi, dir=down)
    assert score_metric(14, "pe") == 92

def test_score_pe_high_is_bad():
    # PE > 60 → 18 (çok kötü)
    assert score_metric(65, "pe") == 18

def test_score_roe_high_is_great():
    # ROE > 20 → 92 (çok iyi, dir=up)
    assert score_metric(25, "roe") == 92

def test_score_missing_value_returns_none():
    assert score_metric(None, "pe") is None

def test_verdict_strong_buy():
    assert verdict_of(80) == ("GÜÇLÜ AL", "strong_buy")

def test_verdict_sell():
    assert verdict_of(35) == ("SAT", "sell")

def test_dim_score_averages_valid_scores():
    metrics = {"pe": 92, "pb": 74, "ps": None}  # ps atlanır
    result = dim_score(metrics)
    assert result == round((92 + 74) / 2)

def test_weights_sum_to_one():
    assert abs(sum(WEIGHTS.values()) - 1.0) < 0.001
```

- [ ] **Step 2: Testlerin başarısız olduğunu doğrula**

```bash
pytest tests/test_scoring.py -v
```

Beklenen: 8 FAILED (scoring.py henüz yok)

- [ ] **Step 3: scoring.py'yi yaz**

`scripts/scoring.py`:
```python
from typing import Optional

THRESHOLDS = {
    "pe":           {"dir": "down", "t": [15, 25, 40, 60]},
    "pb":           {"dir": "down", "t": [1.5, 3, 6, 10]},
    "ps":           {"dir": "down", "t": [2, 5, 10, 18]},
    "roe":          {"dir": "up",   "t": [20, 12, 5, 0]},
    "roa":          {"dir": "up",   "t": [12, 7, 3, 0]},
    "net_margin":   {"dir": "up",   "t": [20, 10, 3, 0]},
    "gross_margin": {"dir": "up",   "t": [50, 35, 20, 10]},
    "rev_growth":   {"dir": "up",   "t": [20, 8, 2, -5]},
    "eps_growth":   {"dir": "up",   "t": [20, 8, 0, -10]},
    "rev_5y":       {"dir": "up",   "t": [15, 8, 3, 0]},
    "current_ratio":{"dir": "up",   "t": [2, 1.5, 1, 0.8]},
    "debt_equity":  {"dir": "down", "t": [0.5, 1, 2, 3]},
    "quick_ratio":  {"dir": "up",   "t": [1.5, 1, 0.7, 0.4]},
    "ret52":        {"dir": "up",   "t": [25, 8, -5, -25]},
    "ret13":        {"dir": "up",   "t": [15, 3, -5, -15]},
    "range_pos":    {"dir": "up",   "t": [60, 40, 20, 5]},
}

WEIGHTS = {
    "valuation": 0.20,
    "profit":    0.20,
    "growth":    0.20,
    "health":    0.15,
    "technical": 0.15,
    "analyst":   0.10,
}

VERDICT_BANDS = [
    (75, "GÜÇLÜ AL",  "strong_buy"),
    (60, "AL",         "buy"),
    (45, "TUT / NÖTR", "hold"),
    (32, "SAT",        "sell"),
    (0,  "GÜÇLÜ SAT",  "strong_sell"),
]


def score_metric(value: Optional[float], key: str) -> Optional[int]:
    """Tek bir metriği 0-100 arası puanlar. Veri yoksa None döner."""
    if value is None or (isinstance(value, float) and (value != value)):  # NaN
        return None
    cfg = THRESHOLDS.get(key)
    if not cfg:
        return None
    a, b, c, d = cfg["t"]
    if cfg["dir"] == "up":
        return 92 if value >= a else 74 if value >= b else 55 if value >= c else 38 if value >= d else 18
    else:  # down
        return 92 if value <= a else 74 if value <= b else 55 if value <= c else 38 if value <= d else 18


def dim_score(metric_scores: dict) -> Optional[int]:
    """Bir boyutun ortalama skorunu hesaplar (None değerleri atlanır)."""
    valid = [v for v in metric_scores.values() if v is not None]
    return round(sum(valid) / len(valid)) if valid else None


def verdict_of(score: Optional[int]) -> tuple[str, str]:
    """Skoru karar etiketi + key'e çevirir."""
    if score is None:
        return ("VERİ YETERSİZ", "insufficient")
    for min_score, label, key in VERDICT_BANDS:
        if score >= min_score:
            return (label, key)
    return VERDICT_BANDS[-1][1], VERDICT_BANDS[-1][2]


def risk_level(score: Optional[int]) -> str:
    """Skora göre risk seviyesi: low / medium / high"""
    if score is None:
        return "unknown"
    if score >= 60:
        return "low"
    if score >= 40:
        return "medium"
    return "high"


def analyst_score(buy: int, hold: int, sell: int) -> Optional[int]:
    """Buy/Hold/Sell oranından 0-100 puan üretir. %75+ AL → 92, %50+ → 74, %30+ → 55, %15+ → 38, else 18."""
    total = buy + hold + sell
    if total == 0:
        return None
    pct = buy / total * 100
    return 92 if pct >= 75 else 74 if pct >= 50 else 55 if pct >= 30 else 38 if pct >= 15 else 18
```

- [ ] **Step 4: Testlerin geçtiğini doğrula**

```bash
pytest tests/test_scoring.py -v
```

Beklenen: 8 PASSED

- [ ] **Step 5: Commit**

```bash
git add scripts/scoring.py tests/test_scoring.py
git commit -m "feat: add scoring engine (ported from JS)"
```

---

## Task 4: ABD Hisseleri — Finnhub Entegrasyonu

**Files:**
- Create: `scripts/fetch_us.py`
- Create: `tests/test_fetch_us.py`

- [ ] **Step 1: Testleri yaz (mock HTTP)**

`tests/test_fetch_us.py`:
```python
import pytest
from unittest.mock import patch, MagicMock
from scripts.fetch_us import fetch_us_stock

MOCK_QUOTE = {"c": 1125.40, "dp": 2.4, "h": 1130.0, "l": 1100.0}
MOCK_METRICS = {
    "metric": {
        "peTTM": 45.2, "pbAnnual": 28.1, "psTTM": 18.3,
        "roeTTM": 124.0, "roaTTM": 55.0,
        "netProfitMarginTTM": 55.0, "grossMarginTTM": 76.0,
        "revenueGrowthTTMYoy": 77.0, "epsGrowthTTMYoy": 85.0,
        "revenueGrowth5Y": 42.0,
        "currentRatioAnnual": 4.2, "totalDebt/totalEquityAnnual": 0.42,
        "quickRatioAnnual": 3.8,
        "52WeekPriceReturnDaily": 210.0, "13WeekPriceReturnDaily": 38.0,
        "52WeekHigh": 1200.0, "52WeekLow": 500.0,
    }
}
MOCK_REC = [{"buy": 38, "hold": 5, "sell": 1, "period": "2026-05-01"}]
MOCK_PROFILE = {"name": "NVIDIA Corporation"}

@patch("scripts.fetch_us.finnhub_get")
def test_fetch_us_stock_returns_expected_shape(mock_get):
    mock_get.side_effect = [MOCK_QUOTE, MOCK_PROFILE, MOCK_METRICS, MOCK_REC]
    result = fetch_us_stock("NVDA", api_key="test_key")
    assert result["symbol"] == "NVDA"
    assert result["price"] == 1125.40
    assert result["exchange"] == "NASDAQ"
    assert "score" in result
    assert result["score"] > 70  # yüksek kaliteli hisse
    assert result["dimensions"]["valuation"]["score"] is not None

@patch("scripts.fetch_us.finnhub_get")
def test_fetch_us_stock_handles_api_error(mock_get):
    mock_get.side_effect = Exception("API error")
    result = fetch_us_stock("NVDA", api_key="test_key")
    assert "error" in result
    assert result["symbol"] == "NVDA"
```

- [ ] **Step 2: Testlerin başarısız olduğunu doğrula**

```bash
pytest tests/test_fetch_us.py -v
```

Beklenen: 2 FAILED

- [ ] **Step 3: fetch_us.py'yi yaz**

`scripts/fetch_us.py`:
```python
import time
import requests
from scripts.scoring import score_metric, dim_score, verdict_of, risk_level, analyst_score, WEIGHTS

BASE = "https://finnhub.io/api/v1"


def finnhub_get(path: str, api_key: str) -> dict:
    sep = "&" if "?" in path else "?"
    r = requests.get(f"{BASE}{path}{sep}token={api_key}", timeout=10)
    r.raise_for_status()
    time.sleep(0.5)  # 60 req/dk limitine saygı
    return r.json()


def _range_pos(price: float, low52: float, high52: float) -> float | None:
    """Fiyatın 52 haftalık bant içindeki konumu (0-100)."""
    if not price or not low52 or not high52 or high52 == low52:
        return None
    return round((price - low52) / (high52 - low52) * 100, 1)


def fetch_us_stock(symbol: str, api_key: str) -> dict:
    try:
        quote   = finnhub_get(f"/quote?symbol={symbol}", api_key)
        profile = finnhub_get(f"/stock/profile2?symbol={symbol}", api_key)
        metrics = finnhub_get(f"/stock/metric?symbol={symbol}&metric=all", api_key)
        rec     = finnhub_get(f"/stock/recommendation?symbol={symbol}", api_key)
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}

    m = metrics.get("metric", {})
    price = quote.get("c")

    # --- Boyut metrikleri ---
    val_raw  = {"pe": m.get("peTTM"),    "pb": m.get("pbAnnual"),   "ps": m.get("psTTM")}
    prof_raw = {"roe": m.get("roeTTM"),  "roa": m.get("roaTTM"),
                "net_margin": m.get("netProfitMarginTTM"),
                "gross_margin": m.get("grossMarginTTM")}
    grow_raw = {"rev_growth": m.get("revenueGrowthTTMYoy"),
                "eps_growth": m.get("epsGrowthTTMYoy"),
                "rev_5y": m.get("revenueGrowth5Y")}
    hlth_raw = {"current_ratio": m.get("currentRatioAnnual"),
                "debt_equity": m.get("totalDebt/totalEquityAnnual"),
                "quick_ratio": m.get("quickRatioAnnual")}
    tech_raw = {"ret52":    m.get("52WeekPriceReturnDaily"),
                "ret13":    m.get("13WeekPriceReturnDaily"),
                "range_pos": _range_pos(price, m.get("52WeekLow"), m.get("52WeekHigh"))}

    # --- Skorlama ---
    def score_dim(raw: dict) -> dict:
        return {k: score_metric(v, k) for k, v in raw.items()}

    val_sc  = score_dim(val_raw)
    prof_sc = score_dim(prof_raw)
    grow_sc = score_dim(grow_raw)
    hlth_sc = score_dim(hlth_raw)
    tech_sc = score_dim(tech_raw)

    latest_rec = rec[0] if rec else {}
    an_sc = analyst_score(latest_rec.get("buy", 0),
                          latest_rec.get("hold", 0),
                          latest_rec.get("sell", 0))

    dims = {
        "valuation": {"score": dim_score(val_sc),  "metrics": val_raw},
        "profit":    {"score": dim_score(prof_sc),  "metrics": prof_raw},
        "growth":    {"score": dim_score(grow_sc),  "metrics": grow_raw},
        "health":    {"score": dim_score(hlth_sc),  "metrics": hlth_raw},
        "technical": {"score": dim_score(tech_sc),  "metrics": tech_raw},
        "analyst":   {"score": an_sc, "metrics": {"buy": latest_rec.get("buy", 0),
                                                   "hold": latest_rec.get("hold", 0),
                                                   "sell": latest_rec.get("sell", 0)}},
    }

    # --- Ağırlıklı ortalama ---
    weighted, total_w = 0.0, 0.0
    for key, w in WEIGHTS.items():
        s = dims[key]["score"]
        if s is not None:
            weighted += s * w
            total_w  += w
    overall = round(weighted / total_w) if total_w else None

    verdict_label, verdict_key = verdict_of(overall)

    # --- Güçlü/zayıf yönler ---
    scored_dims = [(k, v["score"]) for k, v in dims.items() if v["score"] is not None]
    scored_dims.sort(key=lambda x: x[1], reverse=True)
    DIM_NAMES = {"valuation":"Değerleme","profit":"Kârlılık","growth":"Büyüme",
                 "health":"Finansal Sağlık","technical":"Teknik/Momentum","analyst":"Analist Görüşü"}
    pros = [f"{DIM_NAMES[k]} skoru güçlü ({s}/100)" for k, s in scored_dims[:2] if s >= 70]
    cons = [f"{DIM_NAMES[k]} skoru zayıf ({s}/100)" for k, s in scored_dims[-2:] if s < 50]

    return {
        "symbol":     symbol,
        "name":       profile.get("name", symbol),
        "exchange":   "NASDAQ",
        "price":      price,
        "change_pct": quote.get("dp"),
        "score":      overall,
        "verdict":    verdict_label,
        "verdict_key": verdict_key,
        "risk":       risk_level(overall),
        "dimensions": dims,
        "pros":       pros,
        "cons":       cons,
        "dividends":  [],
    }
```

- [ ] **Step 4: Testlerin geçtiğini doğrula**

```bash
pytest tests/test_fetch_us.py -v
```

Beklenen: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch_us.py tests/test_fetch_us.py
git commit -m "feat: add Finnhub US stock fetcher"
```

---

## Task 5: BIST Hisseleri — yfinance Entegrasyonu

**Files:**
- Create: `scripts/fetch_bist.py`
- Create: `tests/test_fetch_bist.py`

- [ ] **Step 1: Testleri yaz**

`tests/test_fetch_bist.py`:
```python
from unittest.mock import patch, MagicMock
from scripts.fetch_bist import fetch_bist_stock

MOCK_INFO = {
    "longName": "Türk Hava Yolları A.O.",
    "currentPrice": 285.50,
    "regularMarketChangePercent": 1.2,
    "trailingPE": 8.2,
    "priceToBook": 1.4,
    "returnOnEquity": 0.22,   # yfinance yüzdeyi ondalık verir
    "revenueGrowth": 0.18,
    "debtToEquity": 85.0,     # yfinance 100x verir
    "currentRatio": 0.9,
    "fiftyTwoWeekHigh": 310.0,
    "fiftyTwoWeekLow": 180.0,
    "52WeekChange": 0.35,
}

@patch("scripts.fetch_bist.yf.Ticker")
def test_fetch_bist_returns_expected_shape(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker.info = MOCK_INFO
    mock_ticker_cls.return_value = mock_ticker

    result = fetch_bist_stock("THYAO")
    assert result["symbol"] == "THYAO"
    assert result["exchange"] == "BIST"
    assert result["price"] == 285.50
    assert "score" in result
    assert result["score"] is not None

@patch("scripts.fetch_bist.yf.Ticker")
def test_fetch_bist_handles_error(mock_ticker_cls):
    mock_ticker_cls.side_effect = Exception("network error")
    result = fetch_bist_stock("THYAO")
    assert "error" in result
```

- [ ] **Step 2: Testlerin başarısız olduğunu doğrula**

```bash
pytest tests/test_fetch_bist.py -v
```

Beklenen: 2 FAILED

- [ ] **Step 3: fetch_bist.py'yi yaz**

`scripts/fetch_bist.py`:
```python
import yfinance as yf
from scripts.scoring import score_metric, dim_score, verdict_of, risk_level, analyst_score, WEIGHTS


def fetch_bist_stock(symbol: str) -> dict:
    try:
        ticker = yf.Ticker(f"{symbol}.IS")
        info = ticker.info
    except Exception as e:
        return {"symbol": symbol, "error": str(e)}

    price = info.get("currentPrice") or info.get("regularMarketPrice")
    change_pct = info.get("regularMarketChangePercent")

    # yfinance ondalık verir (0.22 = %22), normalize et
    def pct(v): return round(v * 100, 2) if v is not None else None

    pe    = info.get("trailingPE")
    pb    = info.get("priceToBook")
    roe   = pct(info.get("returnOnEquity"))
    rev_g = pct(info.get("revenueGrowth"))
    de    = info.get("debtToEquity")
    # yfinance debtToEquity'yi 100x verir (85.0 = 0.85)
    debt_equity = round(de / 100, 2) if de is not None else None
    cur_ratio   = info.get("currentRatio")

    high52 = info.get("fiftyTwoWeekHigh")
    low52  = info.get("fiftyTwoWeekLow")
    ret52  = pct(info.get("52WeekChange"))

    range_pos = None
    if price and high52 and low52 and high52 != low52:
        range_pos = round((price - low52) / (high52 - low52) * 100, 1)

    val_raw  = {"pe": pe, "pb": pb}
    prof_raw = {"roe": roe}
    grow_raw = {"rev_growth": rev_g}
    hlth_raw = {"current_ratio": cur_ratio, "debt_equity": debt_equity}
    tech_raw = {"ret52": ret52, "range_pos": range_pos}

    def score_dim(raw):
        return {k: score_metric(v, k) for k, v in raw.items()}

    dims = {
        "valuation": {"score": dim_score(score_dim(val_raw)),  "metrics": val_raw},
        "profit":    {"score": dim_score(score_dim(prof_raw)), "metrics": prof_raw},
        "growth":    {"score": dim_score(score_dim(grow_raw)), "metrics": grow_raw},
        "health":    {"score": dim_score(score_dim(hlth_raw)), "metrics": hlth_raw},
        "technical": {"score": dim_score(score_dim(tech_raw)), "metrics": tech_raw},
        "analyst":   {"score": None, "metrics": {}},  # yfinance analiz verisi yok
    }

    weighted, total_w = 0.0, 0.0
    for key, w in WEIGHTS.items():
        s = dims[key]["score"]
        if s is not None:
            weighted += s * w
            total_w  += w
    overall = round(weighted / total_w) if total_w else None

    verdict_label, verdict_key = verdict_of(overall)

    return {
        "symbol":     symbol,
        "name":       info.get("longName", symbol),
        "exchange":   "BIST",
        "price":      price,
        "change_pct": change_pct,
        "score":      overall,
        "verdict":    verdict_label,
        "verdict_key": verdict_key,
        "risk":       risk_level(overall),
        "dimensions": dims,
        "pros":       [],
        "cons":       [],
        "dividends":  [],
    }
```

- [ ] **Step 4: Testlerin geçtiğini doğrula**

```bash
pytest tests/test_fetch_bist.py -v
```

Beklenen: 2 PASSED

- [ ] **Step 5: Commit**

```bash
git add scripts/fetch_bist.py tests/test_fetch_bist.py
git commit -m "feat: add yfinance BIST stock fetcher"
```

---

## Task 6: Makro Veri Çekimi

**Files:**
- Create: `scripts/fetch_macro.py`
- Test: `tests/test_analyze.py` (macro bölümü)

- [ ] **Step 1: fetch_macro.py'yi yaz**

`scripts/fetch_macro.py`:
```python
import os
import requests


def fetch_macro(finnhub_key: str, exchange_key: str) -> dict:
    result = {
        "usd_try": None, "eur_try": None, "gold_usd": None,
        "sp500": None, "sp500_change_pct": None,
        "bist100": None, "bist100_change_pct": None,
        "tr_interest_rate": float(os.environ.get("TR_INTEREST_RATE", "46.0")),
    }

    # Döviz kurları — ExchangeRate-API
    try:
        r = requests.get(
            f"https://v6.exchangerate-api.com/v6/{exchange_key}/latest/USD",
            timeout=8
        )
        rates = r.json().get("conversion_rates", {})
        result["usd_try"] = round(rates.get("TRY", 0), 4)
        eur_usd = rates.get("EUR", 1)
        result["eur_try"] = round(result["usd_try"] / eur_usd, 4) if eur_usd else None
    except Exception:
        pass

    # Altın — Finnhub OANDA:XAU_USD
    try:
        import time
        r = requests.get(
            f"https://finnhub.io/api/v1/quote?symbol=OANDA:XAU_USD&token={finnhub_key}",
            timeout=8
        )
        time.sleep(0.5)
        data = r.json()
        result["gold_usd"] = data.get("c")
    except Exception:
        pass

    # S&P 500 — Finnhub SPY
    try:
        import time
        r = requests.get(
            f"https://finnhub.io/api/v1/quote?symbol=SPY&token={finnhub_key}",
            timeout=8
        )
        time.sleep(0.5)
        data = r.json()
        result["sp500"] = data.get("c")
        result["sp500_change_pct"] = data.get("dp")
    except Exception:
        pass

    # BIST 100 — yfinance
    try:
        import yfinance as yf
        xu = yf.Ticker("XU100.IS")
        info = xu.fast_info
        result["bist100"] = round(info.last_price, 2) if info.last_price else None
        result["bist100_change_pct"] = None  # fast_info'da yok, kabul edilebilir
    except Exception:
        pass

    return result
```

- [ ] **Step 2: Manuel test (gerçek API ile)**

```bash
FINNHUB_KEY=<anahtarınız> EXCHANGE_API_KEY=<anahtarınız> python -c "
from scripts.fetch_macro import fetch_macro
import os, json
result = fetch_macro(os.environ['FINNHUB_KEY'], os.environ['EXCHANGE_API_KEY'])
print(json.dumps(result, indent=2))
"
```

Beklenen: `usd_try`, `gold_usd`, `sp500` değerleri dolu, null değil.

- [ ] **Step 3: Commit**

```bash
git add scripts/fetch_macro.py
git commit -m "feat: add macro data fetcher (FX, gold, indices)"
```

---

## Task 7: Ana Analiz Scripti

**Files:**
- Create: `scripts/analyze.py`

- [ ] **Step 1: analyze.py'yi yaz**

`scripts/analyze.py`:
```python
#!/usr/bin/env python3
"""
Ana analiz scripti. GitHub Actions tarafından günlük çalıştırılır.
Ürettiği data/report.json dosyasını dashboard okur.
"""
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts.fetch_us   import fetch_us_stock
from scripts.fetch_bist import fetch_bist_stock
from scripts.fetch_macro import fetch_macro

US_STOCKS   = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "AMD", "TSLA"]
BIST_STOCKS = ["THYAO", "GARAN", "KCHOL", "TUPRS", "EREGL", "SISE", "ASELS"]


def run() -> dict:
    key         = os.environ["FINNHUB_KEY"]
    exchange_key = os.environ.get("EXCHANGE_API_KEY", "")

    print("Makro veriler çekiliyor...")
    macro = fetch_macro(key, exchange_key)

    print("ABD hisseleri analiz ediliyor...")
    stocks = []
    for sym in US_STOCKS:
        print(f"  {sym}")
        stocks.append(fetch_us_stock(sym, key))
        time.sleep(1)  # rate limit

    print("BIST hisseleri analiz ediliyor...")
    for sym in BIST_STOCKS:
        print(f"  {sym}")
        stocks.append(fetch_bist_stock(sym))

    # Hataları filtrele, sırala
    valid = [s for s in stocks if "error" not in s and s.get("score") is not None]
    errors = [s for s in stocks if "error" in s]
    valid.sort(key=lambda s: s["score"], reverse=True)

    if errors:
        print(f"⚠️  {len(errors)} hisse veri alınamadı: {[e['symbol'] for e in errors]}")

    top3       = [s["symbol"] for s in valid[:3]]
    risk_alerts = [s["symbol"] for s in valid if s.get("risk") == "high"]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "macro":        macro,
        "stocks":       valid + errors,
        "top3":         top3,
        "risk_alerts":  risk_alerts,
        "weekly_summary": None,
    }
    return report


if __name__ == "__main__":
    report = run()
    out = Path("data/report.json")
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"✅ report.json yazıldı: {len(report['stocks'])} hisse")
```

- [ ] **Step 2: Gerçek API ile test et**

```bash
FINNHUB_KEY=<anahtarınız> EXCHANGE_API_KEY=<anahtarınız> python -m scripts.analyze
```

Beklenen çıktı:
```
Makro veriler çekiliyor...
ABD hisseleri analiz ediliyor...
  AAPL
  MSFT
  ...
✅ report.json yazıldı: 15 hisse
```

`data/report.json` dosyasını kontrol et: `stocks` dizisi dolu, `macro.usd_try` sayısal değer içeriyor.

- [ ] **Step 3: Commit**

```bash
git add scripts/analyze.py data/report.json
git commit -m "feat: add main analysis runner"
```

---

## Task 8: Bildirimler — Telegram + Gmail

**Files:**
- Create: `scripts/notify.py`
- Create: `tests/test_notify.py`

- [ ] **Step 1: Testleri yaz**

`tests/test_notify.py`:
```python
from unittest.mock import patch, MagicMock
from scripts.notify import build_morning_message, send_telegram

SAMPLE_REPORT = {
    "generated_at": "2026-05-26T06:03:00Z",
    "macro": {"usd_try": 32.45, "gold_usd": 2318.5, "sp500_change_pct": 0.42},
    "top3": ["NVDA", "AAPL", "THYAO"],
    "risk_alerts": ["GARAN"],
    "stocks": [
        {"symbol": "NVDA", "score": 89, "verdict": "GÜÇLÜ AL", "change_pct": 2.4},
        {"symbol": "AAPL", "score": 76, "verdict": "GÜÇLÜ AL", "change_pct": 0.8},
        {"symbol": "THYAO", "score": 71, "verdict": "AL", "change_pct": 1.2},
        {"symbol": "GARAN", "score": 41, "verdict": "SAT", "change_pct": -2.1},
    ],
}

def test_build_morning_message_contains_top3():
    msg = build_morning_message(SAMPLE_REPORT)
    assert "NVDA" in msg
    assert "AAPL" in msg
    assert "THYAO" in msg

def test_build_morning_message_contains_risk_alert():
    msg = build_morning_message(SAMPLE_REPORT)
    assert "GARAN" in msg

def test_build_morning_message_contains_macro():
    msg = build_morning_message(SAMPLE_REPORT)
    assert "32.45" in msg

@patch("scripts.notify.requests.post")
def test_send_telegram_calls_api(mock_post):
    mock_post.return_value = MagicMock(status_code=200)
    send_telegram("test message", bot_token="TOKEN", chat_id="123")
    mock_post.assert_called_once()
    call_json = mock_post.call_args[1]["json"]
    assert call_json["text"] == "test message"
    assert call_json["chat_id"] == "123"
```

- [ ] **Step 2: Testlerin başarısız olduğunu doğrula**

```bash
pytest tests/test_notify.py -v
```

Beklenen: 4 FAILED

- [ ] **Step 3: notify.py'yi yaz**

`scripts/notify.py`:
```python
import os
import smtplib
import requests
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


def build_morning_message(report: dict) -> str:
    now    = datetime.now().strftime("%d %B %Y %H:%M")
    macro  = report.get("macro", {})
    stocks = {s["symbol"]: s for s in report.get("stocks", []) if "error" not in s}
    top3   = report.get("top3", [])
    alerts = report.get("risk_alerts", [])

    lines = [f"☀️ Sabah Raporu — {now}", ""]

    lines.append("📈 Top 3 Fırsat:")
    for i, sym in enumerate(top3[:3], 1):
        s = stocks.get(sym, {})
        chg = s.get("change_pct", 0) or 0
        sign = "+" if chg >= 0 else ""
        lines.append(f"{i}. {sym} — {s.get('score','?')}/100 {s.get('verdict','?')} ({sign}{chg:.1f}%)")

    if alerts:
        lines.append("")
        lines.append("⚠️ Risk Uyarısı:")
        for sym in alerts:
            s = stocks.get(sym, {})
            lines.append(f"• {sym} — {s.get('verdict','?')} ({s.get('score','?')}/100)")

    lines.append("")
    usd_try = macro.get("usd_try")
    gold    = macro.get("gold_usd")
    sp_chg  = macro.get("sp500_change_pct")
    sp_sign = "+" if (sp_chg or 0) >= 0 else ""
    lines.append(f"💱 USD/TRY: {usd_try} | Altın: ${gold} | S&P500: {sp_sign}{sp_chg:.2f}%" if sp_chg else
                 f"💱 USD/TRY: {usd_try} | Altın: ${gold}")

    return "\n".join(lines)


def send_telegram(message: str, bot_token: str, chat_id: str) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"}, timeout=10)


def send_gmail(subject: str, body: str, gmail_address: str, gmail_password: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = gmail_address
    msg["To"]      = gmail_address
    msg.attach(MIMEText(body, "plain", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(gmail_address, gmail_password)
        server.sendmail(gmail_address, gmail_address, msg.as_string())


def notify_morning(report: dict) -> None:
    message = build_morning_message(report)
    token    = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id  = os.environ.get("TELEGRAM_CHAT_ID", "")
    gmail    = os.environ.get("GMAIL_ADDRESS", "")
    gmail_pw = os.environ.get("GMAIL_APP_PASSWORD", "")

    if token and chat_id:
        send_telegram(message, token, chat_id)
        print("✅ Telegram gönderildi")
    if gmail and gmail_pw:
        send_gmail("☀️ Hisse Sabah Raporu", message, gmail, gmail_pw)
        print("✅ Gmail gönderildi")
```

- [ ] **Step 4: Testlerin geçtiğini doğrula**

```bash
pytest tests/test_notify.py -v
```

Beklenen: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add scripts/notify.py tests/test_notify.py
git commit -m "feat: add Telegram + Gmail notification system"
```

---

## Task 9: Fiyat Alarm Kontrolü

**Files:**
- Create: `scripts/check_alarms.py`

- [ ] **Step 1: check_alarms.py'yi yaz**

`scripts/check_alarms.py`:
```python
#!/usr/bin/env python3
"""
30 dakikada bir çalışır. ALARMS env var'ından kuralları okur,
mevcut fiyatları kontrol eder, tetiklenenleri Telegram'a gönderir.

ALARMS formatı (JSON array string):
[{"symbol":"NVDA","dir":"below","price":900,"label":"NVDA 900 altı"},...]
"""
import json
import os
import requests
import time
from scripts.notify import send_telegram

BASE = "https://finnhub.io/api/v1"


def get_price(symbol: str, api_key: str) -> float | None:
    try:
        r = requests.get(f"{BASE}/quote?symbol={symbol}&token={api_key}", timeout=8)
        time.sleep(0.3)
        return r.json().get("c")
    except Exception:
        return None


def check_alarms() -> None:
    alarms_json = os.environ.get("ALARMS", "[]")
    alarms = json.loads(alarms_json)
    if not alarms:
        print("Aktif alarm yok.")
        return

    api_key  = os.environ["FINNHUB_KEY"]
    token    = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id  = os.environ.get("TELEGRAM_CHAT_ID", "")

    triggered = []
    for alarm in alarms:
        symbol = alarm["symbol"]
        target = alarm["price"]
        direction = alarm["dir"]  # "below" | "above"
        price = get_price(symbol, api_key)
        if price is None:
            continue
        hit = (direction == "below" and price < target) or \
              (direction == "above" and price > target)
        if hit:
            sign = "<" if direction == "below" else ">"
            triggered.append(f"🔔 ALARM: {symbol} {sign} ${target:.2f} (şu an: ${price:.2f})")

    if triggered and token and chat_id:
        message = "\n".join(triggered)
        send_telegram(message, token, chat_id)
        print(f"✅ {len(triggered)} alarm gönderildi")
    else:
        print(f"Alarm tetiklenmedi ({len(alarms)} kural kontrol edildi)")


if __name__ == "__main__":
    check_alarms()
```

- [ ] **Step 2: Commit**

```bash
git add scripts/check_alarms.py
git commit -m "feat: add price alarm checker"
```

---

## Task 10: GitHub Actions Workflows

**Files:**
- Create: `.github/workflows/daily.yml`
- Create: `.github/workflows/weekly.yml`
- Create: `.github/workflows/alarms.yml`

- [ ] **Step 1: daily.yml oluştur**

`.github/workflows/daily.yml`:
```yaml
name: Daily Analysis & Notify

on:
  schedule:
    - cron: "0 6 * * *"   # 09:00 TR (UTC+3 = UTC 06:00)
  workflow_dispatch:        # Manuel tetikleme için

permissions:
  contents: write

jobs:
  analyze:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Run analysis
        env:
          FINNHUB_KEY: ${{ secrets.FINNHUB_KEY }}
          EXCHANGE_API_KEY: ${{ secrets.EXCHANGE_API_KEY }}
          TR_INTEREST_RATE: ${{ secrets.TR_INTEREST_RATE }}
        run: python -m scripts.analyze

      - name: Send notifications
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          GMAIL_ADDRESS: ${{ secrets.GMAIL_ADDRESS }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
        run: |
          python -c "
          import json
          from scripts.notify import notify_morning
          with open('data/report.json') as f:
              report = json.load(f)
          notify_morning(report)
          "

      - name: Commit report.json
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/report.json
          git diff --staged --quiet || git commit -m "chore: daily report $(date -u +%Y-%m-%d)"
          git push
```

- [ ] **Step 2: weekly.yml oluştur**

`.github/workflows/weekly.yml`:
```yaml
name: Weekly Summary

on:
  schedule:
    - cron: "0 6 * * 1"   # Her Pazartesi 09:00 TR
  workflow_dispatch:

permissions:
  contents: write

jobs:
  weekly:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt

      - name: Run analysis
        env:
          FINNHUB_KEY: ${{ secrets.FINNHUB_KEY }}
          EXCHANGE_API_KEY: ${{ secrets.EXCHANGE_API_KEY }}
          TR_INTEREST_RATE: ${{ secrets.TR_INTEREST_RATE }}
        run: python -m scripts.analyze

      - name: Send weekly summary
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
          GMAIL_ADDRESS: ${{ secrets.GMAIL_ADDRESS }}
          GMAIL_APP_PASSWORD: ${{ secrets.GMAIL_APP_PASSWORD }}
        run: |
          python -c "
          import json
          from scripts.notify import notify_morning, send_telegram, send_gmail
          import os
          with open('data/report.json') as f:
              report = json.load(f)
          # Haftalık mesaja ek başlık ekle
          base_msg = '📅 HAFTALIK ÖZET\n\n'
          from scripts.notify import build_morning_message
          msg = base_msg + build_morning_message(report)
          token   = os.environ.get('TELEGRAM_BOT_TOKEN','')
          chat_id = os.environ.get('TELEGRAM_CHAT_ID','')
          gmail   = os.environ.get('GMAIL_ADDRESS','')
          pw      = os.environ.get('GMAIL_APP_PASSWORD','')
          if token and chat_id:
              from scripts.notify import send_telegram
              send_telegram(msg, token, chat_id)
          if gmail and pw:
              from scripts.notify import send_gmail
              send_gmail('📅 Haftalık Hisse Özeti', msg, gmail, pw)
          print('Haftalık özet gönderildi')
          "

      - name: Commit report
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/report.json
          git diff --staged --quiet || git commit -m "chore: weekly report $(date -u +%Y-%m-%d)"
          git push
```

- [ ] **Step 3: alarms.yml oluştur**

`.github/workflows/alarms.yml`:
```yaml
name: Price Alarm Check

on:
  schedule:
    - cron: "*/30 6-16 * * 1-5"  # Hafta içi 09:00-19:00 TR arası her 30 dk
  workflow_dispatch:

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt

      - name: Check alarms
        env:
          FINNHUB_KEY: ${{ secrets.FINNHUB_KEY }}
          ALARMS: ${{ secrets.ALARMS }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}
        run: python -m scripts.check_alarms
```

- [ ] **Step 4: Commit**

```bash
git add .github/
git commit -m "feat: add GitHub Actions workflows (daily, weekly, alarms)"
```

---

## Task 11: Frontend — Makro Şerit (macro.js)

**Files:**
- Create: `assets/js/macro.js`

- [ ] **Step 1: macro.js'yi yaz**

`assets/js/macro.js`:
```javascript
const MacroStrip = (() => {
  function renderMacro(macro) {
    if (!macro) return;
    const strip = document.getElementById("macroStrip");
    if (!strip) return;

    const items = [
      { label: "USD/TRY", value: macro.usd_try?.toFixed(4) },
      { label: "EUR/TRY", value: macro.eur_try?.toFixed(4) },
      { label: "Altın",   value: macro.gold_usd ? `$${macro.gold_usd.toFixed(0)}` : null },
      { label: "S&P 500", value: macro.sp500_change_pct != null
          ? `${macro.sp500_change_pct >= 0 ? "+" : ""}${macro.sp500_change_pct.toFixed(2)}%` : null,
        color: macro.sp500_change_pct >= 0 ? "var(--green)" : "var(--red)" },
      { label: "BIST 100", value: macro.bist100 ? macro.bist100.toFixed(0) : null,
        color: (macro.bist100_change_pct ?? 0) >= 0 ? "var(--green)" : "var(--red)" },
      { label: "TR Faiz", value: macro.tr_interest_rate ? `%${macro.tr_interest_rate}` : null },
    ];

    strip.innerHTML = items
      .filter(i => i.value)
      .map(i => `
        <div class="macro-item">
          <span class="macro-label">${i.label}</span>
          <span class="macro-value" style="color:${i.color || "var(--text)"}">${i.value}</span>
        </div>`)
      .join('<div class="macro-sep">·</div>');
  }

  return { renderMacro };
})();
```

- [ ] **Step 2: style.css'e makro şerit stilleri ekle**

`assets/css/style.css`'in sonuna ekle:
```css
/* === Makro Şerit === */
#macroStrip {
  display: flex;
  align-items: center;
  gap: 0;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  padding: 6px 20px;
  overflow-x: auto;
  white-space: nowrap;
  font-size: 12px;
}
.macro-item {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 0 10px;
}
.macro-label { color: var(--muted); }
.macro-value { font-weight: 600; }
.macro-sep { color: var(--border); padding: 0 2px; }
```

- [ ] **Step 3: Commit**

```bash
git add assets/js/macro.js assets/css/style.css
git commit -m "feat: add macro strip module"
```

---

## Task 12: Frontend — Portföy Modülü (portfolio.js)

**Files:**
- Create: `assets/js/portfolio.js`

- [ ] **Step 1: portfolio.js'yi yaz**

`assets/js/portfolio.js`:
```javascript
const Portfolio = (() => {
  const STORE_KEY = "portfolio_v1";

  function load() {
    try { return JSON.parse(localStorage.getItem(STORE_KEY) || "[]"); }
    catch { return []; }
  }

  function save(entries) {
    localStorage.setItem(STORE_KEY, JSON.stringify(entries));
  }

  function addEntry(symbol, qty, buyPrice, buyDate) {
    const entries = load();
    entries.push({ symbol: symbol.toUpperCase(), qty: +qty, buyPrice: +buyPrice, buyDate });
    save(entries);
  }

  function removeEntry(index) {
    const entries = load();
    entries.splice(index, 1);
    save(entries);
  }

  /** report.json'daki fiyatlarla portföyü hesapla */
  function compute(stocksFromReport) {
    const entries = load();
    if (!entries.length) return { entries: [], total_cost: 0, total_value: 0, total_pnl: 0, total_pnl_pct: 0 };

    const priceMap = {};
    const scoreMap = {};
    const verdictMap = {};
    for (const s of stocksFromReport) {
      priceMap[s.symbol]   = s.price;
      scoreMap[s.symbol]   = s.score;
      verdictMap[s.symbol] = s.verdict;
    }

    let total_cost = 0, total_value = 0;
    const computed = entries.map((e, i) => {
      const current = priceMap[e.symbol];
      const cost    = e.qty * e.buyPrice;
      const value   = current ? e.qty * current : null;
      const pnl     = value != null ? value - cost : null;
      const pnl_pct = pnl != null ? (pnl / cost) * 100 : null;
      const score   = scoreMap[e.symbol];
      const verdict = verdictMap[e.symbol];

      if (value != null) { total_cost += cost; total_value += value; }

      // Kişisel yorum
      let comment = "";
      if (pnl_pct != null && score != null) {
        const pnlStr = `${pnl_pct >= 0 ? "+" : ""}${pnl_pct.toFixed(1)}%`;
        if (pnl_pct > 20 && score < 45)
          comment = `${pnlStr} kârdasınız ancak skor düşük (${score}/100) — kâr realize etmeyi düşünün.`;
        else if (pnl_pct > 0 && score >= 60)
          comment = `${pnlStr} kârdasınız, skor güçlü (${score}/100) — tutun.`;
        else if (pnl_pct < -10 && score < 45)
          comment = `${pnlStr} zarardayken ${verdict} sinyali — zararı kesmek mantıklı olabilir.`;
        else if (pnl_pct < 0 && score >= 60)
          comment = `${pnlStr} zararda olsa da skor güçlü (${score}/100) — uzun vadede toparlanabilir.`;
        else
          comment = `${pnlStr} · Skor: ${score}/100 · ${verdict}`;
      }

      return { ...e, index: i, current, cost, value, pnl, pnl_pct, score, verdict, comment };
    });

    const total_pnl     = total_value - total_cost;
    const total_pnl_pct = total_cost > 0 ? (total_pnl / total_cost) * 100 : 0;
    return { entries: computed, total_cost, total_value, total_pnl, total_pnl_pct };
  }

  /** S&P500 ve BIST100 ile kıyaslama bloğunu üretir. */
  function buildComparisonBlock(totalPnlPct, macro) {
    if (!macro) return "";
    const sp  = macro.sp500_change_pct;
    const bi  = macro.bist100_change_pct;
    const fmt = (n) => n != null ? `${n >= 0 ? "+" : ""}${n.toFixed(2)}%` : "—";
    const color = (n) => n == null ? "" : n >= 0 ? "var(--green)" : "var(--red)";
    const myColor = color(totalPnlPct);
    return `
      <div class="comparison-block">
        <h3 style="font-size:11px;color:var(--muted);text-transform:uppercase;margin-bottom:8px">📊 Endeks Kıyaslaması (bugün)</h3>
        <div class="comparison-row">
          <span class="comp-label">Portföyünüz</span>
          <span class="comp-val" style="color:${myColor}">${fmt(totalPnlPct)}</span>
        </div>
        <div class="comparison-row">
          <span class="comp-label">S&P 500</span>
          <span class="comp-val" style="color:${color(sp)}">${fmt(sp)}</span>
        </div>
        <div class="comparison-row">
          <span class="comp-label">BIST 100</span>
          <span class="comp-val" style="color:${color(bi)}">${fmt(bi)}</span>
        </div>
      </div>`;
  }

  function renderPortfolio(stocksFromReport, macro) {
    const container = document.getElementById("portfolioSection");
    if (!container) return;

    const result = compute(stocksFromReport);

    const fmt = (n, dec=2) => n != null ? n.toFixed(dec) : "—";
    const sign = n => n >= 0 ? "+" : "";
    const color = n => n == null ? "" : n >= 0 ? "var(--green)" : "var(--red)";

    const totalPnlColor = color(result.total_pnl);
    const totalBlock = `
      <div class="portfolio-summary">
        <div class="p-stat"><span class="p-lbl">Toplam Değer</span>
          <span class="p-val">$${fmt(result.total_value)}</span></div>
        <div class="p-stat"><span class="p-lbl">Maliyet</span>
          <span class="p-val">$${fmt(result.total_cost)}</span></div>
        <div class="p-stat"><span class="p-lbl">Kâr/Zarar</span>
          <span class="p-val" style="color:${totalPnlColor}">
            ${sign(result.total_pnl)}$${fmt(result.total_pnl)} (${sign(result.total_pnl_pct)}${fmt(result.total_pnl_pct)}%)
          </span></div>
      </div>`;

    const rows = result.entries.map(e => `
      <tr>
        <td><strong>${e.symbol}</strong></td>
        <td>${e.qty}</td>
        <td>$${fmt(e.buyPrice)}</td>
        <td>$${fmt(e.current)}</td>
        <td style="color:${color(e.pnl_pct)}">${sign(e.pnl_pct)}${fmt(e.pnl_pct)}%</td>
        <td>${e.score != null ? e.score + "/100" : "—"}</td>
        <td style="font-size:11px;color:var(--muted);max-width:200px">${e.comment}</td>
        <td><button onclick="Portfolio.remove(${e.index})" style="background:none;border:none;color:var(--red);cursor:pointer">✕</button></td>
      </tr>`).join("");

    const comparisonBlock = buildComparisonBlock(result.total_pnl_pct, macro);

    container.innerHTML = `
      <h2 class="section-title">💼 Kişisel Portföy</h2>
      ${totalBlock}
      ${comparisonBlock}
      <table class="portfolio-table">
        <thead><tr>
          <th>Hisse</th><th>Adet</th><th>Alış</th><th>Anlık</th>
          <th>P&L %</th><th>Skor</th><th>Yorum</th><th></th>
        </tr></thead>
        <tbody>${rows || "<tr><td colspan='8' style='text-align:center;color:var(--muted)'>Henüz hisse eklenmedi.</td></tr>"}</tbody>
      </table>
      <div class="portfolio-add">
        <input id="p-sym" placeholder="Sembol (ör: AAPL)" />
        <input id="p-qty" type="number" placeholder="Adet" min="1" />
        <input id="p-price" type="number" placeholder="Alış fiyatı ($)" step="0.01" />
        <input id="p-date" type="date" />
        <button onclick="Portfolio.addFromUI()">Ekle</button>
      </div>`;
  }

  function addFromUI() {
    const sym   = document.getElementById("p-sym")?.value?.trim();
    const qty   = document.getElementById("p-qty")?.value;
    const price = document.getElementById("p-price")?.value;
    const date  = document.getElementById("p-date")?.value;
    if (!sym || !qty || !price) return alert("Sembol, adet ve fiyat zorunlu.");
    addEntry(sym, qty, price, date);
    App.refresh();
  }

  function remove(index) {
    removeEntry(index);
    App.refresh();
  }

  return { renderPortfolio, addFromUI, remove, compute, buildComparisonBlock };
})();
```

- [ ] **Step 2: style.css'e portföy stilleri ekle**

`assets/css/style.css`'e ekle:
```css
/* === Portföy === */
.portfolio-summary { display: flex; gap: 24px; padding: 12px 0 16px; }
.p-stat { display: flex; flex-direction: column; gap: 2px; }
.p-lbl  { font-size: 11px; color: var(--muted); text-transform: uppercase; }
.p-val  { font-size: 18px; font-weight: 700; }
.portfolio-table { width: 100%; border-collapse: collapse; margin-bottom: 12px; }
.portfolio-table th { font-size: 10px; color: var(--muted); text-transform: uppercase; padding: 6px 8px; border-bottom: 1px solid var(--border); text-align: left; }
.portfolio-table td { padding: 9px 8px; border-bottom: 1px solid var(--surface); font-size: 12px; }
.portfolio-add { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
.portfolio-add input { background: var(--surface); border: 1px solid var(--border); color: var(--text); border-radius: 6px; padding: 6px 10px; font-size: 12px; width: 140px; }
.portfolio-add button { background: var(--green); color: #000; border: none; border-radius: 6px; padding: 6px 14px; cursor: pointer; font-weight: 600; font-size: 12px; }
```

- [ ] **Step 3: Commit**

```bash
git add assets/js/portfolio.js assets/css/style.css
git commit -m "feat: add portfolio module (localStorage, P&L, commentary)"
```

---

## Task 13: Frontend — Fiyat Alarmları UI (alarms.js)

**Files:**
- Create: `assets/js/alarms.js`

- [ ] **Step 1: alarms.js'yi yaz**

`assets/js/alarms.js`:
```javascript
const Alarms = (() => {
  const STORE_KEY = "alarms_v1";

  function load()       { try { return JSON.parse(localStorage.getItem(STORE_KEY) || "[]"); } catch { return []; } }
  function save(alarms) { localStorage.setItem(STORE_KEY, JSON.stringify(alarms)); }

  function add(symbol, dir, price) {
    const alarms = load();
    alarms.push({ symbol: symbol.toUpperCase(), dir, price: +price, active: true, id: Date.now() });
    save(alarms);
  }

  function remove(id) {
    save(load().filter(a => a.id !== id));
    App.refresh();
  }

  function render(stocksFromReport) {
    const el = document.getElementById("alarmsSection");
    if (!el) return;
    const alarms = load();
    const priceMap = Object.fromEntries(stocksFromReport.map(s => [s.symbol, s.price]));

    const rows = alarms.map(a => {
      const cur = priceMap[a.symbol];
      const sign = a.dir === "below" ? "<" : ">";
      const triggered = cur != null && (
        (a.dir === "below" && cur < a.price) ||
        (a.dir === "above" && cur > a.price)
      );
      return `
        <tr style="${triggered ? "background:rgba(255,214,0,.08)" : ""}">
          <td><strong>${a.symbol}</strong></td>
          <td>${sign} $${a.price}</td>
          <td>${cur != null ? "$" + cur.toFixed(2) : "—"}</td>
          <td>${triggered ? "🔔 Tetiklendi" : "⏳ Bekliyor"}</td>
          <td><button onclick="Alarms.remove(${a.id})" style="background:none;border:none;color:var(--red);cursor:pointer">✕</button></td>
        </tr>`;
    }).join("");

    el.innerHTML = `
      <h2 class="section-title">🔔 Fiyat Alarmları</h2>
      <table class="portfolio-table">
        <thead><tr><th>Hisse</th><th>Kural</th><th>Anlık</th><th>Durum</th><th></th></tr></thead>
        <tbody>${rows || "<tr><td colspan='5' style='text-align:center;color:var(--muted)'>Alarm yok.</td></tr>"}</tbody>
      </table>
      <div class="portfolio-add">
        <input id="al-sym" placeholder="Sembol" style="width:100px" />
        <select id="al-dir" style="background:var(--surface);border:1px solid var(--border);color:var(--text);border-radius:6px;padding:6px 10px;font-size:12px">
          <option value="below">Altına düşünce</option>
          <option value="above">Üstüne çıkınca</option>
        </select>
        <input id="al-price" type="number" placeholder="Hedef fiyat ($)" step="0.01" style="width:140px" />
        <button onclick="Alarms.addFromUI()">Alarm Ekle</button>
      </div>
      <p style="font-size:11px;color:var(--muted);margin-top:8px">
        Alarmlar GitHub Actions tarafından her 30 dakikada kontrol edilir. Telegram'a bildirim gönderilir.
        Kurulumdan sonra tüm alarmları GitHub Secrets → ALARMS alanına JSON olarak girin.
      </p>`;
  }

  function addFromUI() {
    const sym   = document.getElementById("al-sym")?.value?.trim();
    const dir   = document.getElementById("al-dir")?.value;
    const price = document.getElementById("al-price")?.value;
    if (!sym || !price) return alert("Sembol ve fiyat zorunlu.");
    add(sym, dir, price);
    App.refresh();
  }

  return { render, add, remove, addFromUI, load };
})();
```

- [ ] **Step 2: Commit**

```bash
git add assets/js/alarms.js
git commit -m "feat: add price alarms UI module"
```

---

## Task 14: Frontend — Temettü Takvimi (dividend.js)

**Files:**
- Create: `assets/js/dividend.js`

- [ ] **Step 1: dividend.js'yi yaz**

`assets/js/dividend.js`:
```javascript
const Dividends = (() => {
  function render(stocksFromReport) {
    const el = document.getElementById("dividendSection");
    if (!el) return;

    const portfolio = Portfolio.compute(stocksFromReport).entries;
    const now = new Date();

    // report.json'dan gelen temettü verilerini göster
    const divs = [];
    for (const s of stocksFromReport) {
      if (!s.dividends || s.dividends.length === 0) continue;
      const qty = portfolio.find(e => e.symbol === s.symbol)?.qty || 0;
      for (const d of s.dividends) {
        if (!d.exDate) continue;
        const exDate = new Date(d.exDate);
        if (exDate < now) continue;
        const daysUntil = Math.ceil((exDate - now) / (1000 * 60 * 60 * 24));
        divs.push({ symbol: s.symbol, exDate: d.exDate, amount: d.amount, qty, daysUntil,
                    estimated: qty * (d.amount || 0) });
      }
    }
    divs.sort((a, b) => new Date(a.exDate) - new Date(b.exDate));

    const rows = divs.map(d => `
      <tr ${d.daysUntil <= 7 ? 'style="background:rgba(255,214,0,.06)"' : ""}>
        <td><strong>${d.symbol}</strong></td>
        <td>${d.exDate}</td>
        <td>${d.daysUntil} gün</td>
        <td>$${(d.amount || 0).toFixed(4)}/hisse</td>
        <td>${d.qty ? "$" + d.estimated.toFixed(2) : "—"}</td>
      </tr>`).join("");

    el.innerHTML = `
      <h2 class="section-title">📅 Temettü Takvimi</h2>
      <table class="portfolio-table">
        <thead><tr><th>Hisse</th><th>Ex-Date</th><th>Kalan</th><th>Temettü</th><th>Tahmini Gelirim</th></tr></thead>
        <tbody>${rows || "<tr><td colspan='5' style='text-align:center;color:var(--muted)'>Yaklaşan temettü yok (veriler sabah raporuyla güncellenir).</td></tr>"}</tbody>
      </table>`;
  }

  return { render };
})();
```

- [ ] **Step 2: Commit**

```bash
git add assets/js/dividend.js
git commit -m "feat: add dividend calendar module"
```

---

## Task 15: index.html ve app.js — Tümünü Birleştir

**Files:**
- Modify: `index.html`
- Modify: `assets/js/app.js`
- Modify: `assets/js/config.js`

- [ ] **Step 1: config.js'e report.json URL'si ve BIST sembolleri ekle**

`assets/js/config.js`'deki `CONFIG` nesnesine şunları ekle:
```javascript
// data/report.json'un adresi — GitHub Pages'te tam URL olur
REPORT_URL: "./data/report.json",

// BIST hisseleri (mevcut POPULAR listesine ek)
BIST_POPULAR: ["THYAO", "GARAN", "KCHOL", "TUPRS", "EREGL", "SISE", "ASELS"],
```

- [ ] **Step 2: index.html'i güncelle**

`index.html`'e şu bölümleri ekle:

`</header>` satırından hemen sonra:
```html
<!-- Makro Şerit -->
<div id="macroStrip" class="macro-strip-loading">Yükleniyor...</div>
```

`<div id="content">` öncesine:
```html
<!-- Sekmeler -->
<div class="tab-bar">
  <button class="tab active" onclick="App.switchTab('scanner')">📊 Tarayıcı</button>
  <button class="tab" onclick="App.switchTab('portfolio')">💼 Portföy</button>
  <button class="tab" onclick="App.switchTab('alarms')">🔔 Alarmlar</button>
  <button class="tab" onclick="App.switchTab('dividends')">📅 Temettüler</button>
</div>
```

`<div id="content">` içindeki placeholder'ın altına:
```html
<!-- Dashboard bölümleri (sekmelere göre gösterilir/gizlenir) -->
<div id="reportDashboard" style="display:none">
  <!-- Hisse tablosu buraya render edilir (app.js tarafından) -->
</div>
<div id="portfolioSection" style="display:none"></div>
<div id="alarmsSection"    style="display:none"></div>
<div id="dividendSection"  style="display:none"></div>
```

`</body>` öncesine (yeni script'ler):
```html
<script src="assets/js/macro.js"></script>
<script src="assets/js/portfolio.js"></script>
<script src="assets/js/alarms.js"></script>
<script src="assets/js/dividend.js"></script>
```

- [ ] **Step 3: app.js'e yeni modülleri bağla**

`assets/js/app.js`'in başına ekle:
```javascript
let _reportData = null;   // son yüklenen report.json

async function loadReport() {
  try {
    const r = await fetch(CONFIG.REPORT_URL + "?t=" + Date.now());
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
}

async function initDashboard() {
  const report = await loadReport();
  _reportData = report;

  if (report) {
    MacroStrip.renderMacro(report.macro);
    // Hisse tablosunu report.json'dan çiz (mevcut UI.js fonksiyonları kullanılır)
    renderReportStocks(report.stocks);
  }
}

function renderReportStocks(stocks) {
  const el = document.getElementById("reportDashboard");
  if (!el) return;
  // Mevcut UI.js render fonksiyonlarını çağır
  // Stok listesini skorlanmış olarak göster
  el.innerHTML = UIModule.buildStockTable(stocks);
}

function switchTab(tab) {
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  event.target.classList.add("active");

  const sections = ["reportDashboard","portfolioSection","alarmsSection","dividendSection"];
  sections.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = "none";
  });

  const stocks = _reportData?.stocks || [];
  if (tab === "scanner") {
    document.getElementById("reportDashboard").style.display = "";
  } else if (tab === "portfolio") {
    document.getElementById("portfolioSection").style.display = "";
    Portfolio.renderPortfolio(stocks, _reportData?.macro);
  } else if (tab === "alarms") {
    document.getElementById("alarmsSection").style.display = "";
    Alarms.render(stocks);
  } else if (tab === "dividends") {
    document.getElementById("dividendSection").style.display = "";
    Dividends.render(stocks);
  }
}

function refresh() {
  const stocks = _reportData?.stocks || [];
  Portfolio.renderPortfolio(stocks, _reportData?.macro);
  Alarms.render(stocks);
}

// App başlatıldığında dashboard'u yükle
document.addEventListener("DOMContentLoaded", initDashboard);

// Global namespace — HTML onclick'ler ve modüller buradan çağırır
const App = { switchTab, refresh };
```

- [ ] **Step 4: Tab ve section stilleri ekle**

`assets/css/style.css`'e ekle:
```css
/* === Sekmeler === */
.tab-bar { display: flex; gap: 4px; padding: 12px 20px 0; border-bottom: 1px solid var(--border); }
.tab { background: none; border: none; color: var(--muted); padding: 8px 16px; cursor: pointer;
       font-size: 13px; border-bottom: 2px solid transparent; margin-bottom: -1px; }
.tab.active { color: var(--text); border-bottom-color: var(--accent, #448aff); font-weight: 600; }
.section-title { font-size: 14px; font-weight: 700; color: var(--text); margin: 16px 0 12px; }
```

- [ ] **Step 5: Tüm testleri çalıştır**

```bash
pytest -v
```

Beklenen: Tüm testler PASSED.

- [ ] **Step 6: Commit**

```bash
git add index.html assets/js/app.js assets/js/config.js assets/css/style.css
git commit -m "feat: wire up all dashboard modules with tab navigation"
```

---

## Task 16: GitHub Kurulumu + Secrets + Deploy

**Files:** GitHub UI üzerinden yapılır.

- [ ] **Step 1: GitHub repo oluştur ve push et**

```bash
git remote add origin https://github.com/KULLANICI_ADI/finans.git
git push -u origin main
```

> Repo adını istediğiniz gibi seçin. Portföy verisi localStorage'da kaldığından public repo güvenlidir.

- [ ] **Step 2: GitHub Pages aktif et**

GitHub repo → Settings → Pages → Source: "GitHub Actions" seç.

`.github/workflows/daily.yml`'a GitHub Pages deploy adımı ekle (son step olarak):
```yaml
      - name: Deploy to GitHub Pages
        uses: peaceiris/actions-gh-pages@v3
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          publish_dir: .
          keep_files: true
```

> `requirements.txt`'i ve `.github/` klasörünü gizlemek istemezseniz bu deploy adımı zaten mevcut `git push` ile çalışır (main branch Pages kaynağı olarak seçildiyse).

- [ ] **Step 3: GitHub Secrets gir**

Repo → Settings → Secrets and variables → Actions → New repository secret:

| İsim | Değer |
|---|---|
| `FINNHUB_KEY` | finnhub.io'dan aldığınız anahtar |
| `EXCHANGE_API_KEY` | exchangerate-api.com ücretsiz anahtar |
| `TR_INTEREST_RATE` | `46.0` (TCMB faiz oranı, değişince güncelleyin) |
| `TELEGRAM_BOT_TOKEN` | BotFather'dan alınan token |
| `TELEGRAM_CHAT_ID` | @userinfobot'tan öğrenilir |
| `GMAIL_ADDRESS` | Gmail adresiniz |
| `GMAIL_APP_PASSWORD` | Gmail → Güvenlik → Uygulama şifreleri |
| `ALARMS` | `[]` (başlangıç boş; örnek: `[{"symbol":"NVDA","dir":"below","price":900}]`) |

- [ ] **Step 4: Telegram Bot Kurulumu**

1. Telegram'da `@BotFather`'a gidin
2. `/newbot` yazın, isim verin, `@xxxbot` şeklinde kullanıcı adı seçin
3. Verilen token'ı `TELEGRAM_BOT_TOKEN` secret'ına girin
4. Botunuza bir mesaj gönderin, sonra `@userinfobot`'a `/start` yazın → chat_id'nizi öğrenin
5. `TELEGRAM_CHAT_ID` secret'ına girin

- [ ] **Step 5: Gmail Uygulama Şifresi**

1. Gmail → Google Hesabı → Güvenlik → 2 Adımlı Doğrulama (aktif olmalı)
2. Güvenlik → Uygulama şifreleri → "Posta" / "Mac" seç → Oluştur
3. 16 haneli şifreyi `GMAIL_APP_PASSWORD`'a girin

- [ ] **Step 6: İlk manuel çalıştırma**

GitHub repo → Actions → "Daily Analysis & Notify" → "Run workflow" → Run.

Logları izleyin, başarıyla tamamlandığından emin olun. Telegram ve Gmail'e mesaj gelmeli.

- [ ] **Step 7: Dashboard URL'ini kontrol et**

`https://KULLANICI_ADI.github.io/finans/` adresini açın. Dashboard yüklenmeli, makro şerit ve hisse tablosu görünmeli.

---

## Tüm Testleri Çalıştır

```bash
pytest -v --tb=short
```

Beklenen çıktı:
```
tests/test_scoring.py::test_score_pe_low_is_great     PASSED
tests/test_scoring.py::test_score_pe_high_is_bad      PASSED
tests/test_scoring.py::test_score_roe_high_is_great   PASSED
tests/test_scoring.py::test_score_missing_value_returns_none PASSED
tests/test_scoring.py::test_verdict_strong_buy        PASSED
tests/test_scoring.py::test_verdict_sell              PASSED
tests/test_scoring.py::test_dim_score_averages_valid_scores PASSED
tests/test_scoring.py::test_weights_sum_to_one        PASSED
tests/test_fetch_us.py::test_fetch_us_stock_returns_expected_shape PASSED
tests/test_fetch_us.py::test_fetch_us_stock_handles_api_error PASSED
tests/test_fetch_bist.py::test_fetch_bist_returns_expected_shape PASSED
tests/test_fetch_bist.py::test_fetch_bist_handles_error PASSED
tests/test_notify.py::test_build_morning_message_contains_top3 PASSED
tests/test_notify.py::test_build_morning_message_contains_risk_alert PASSED
tests/test_notify.py::test_build_morning_message_contains_macro PASSED
tests/test_notify.py::test_send_telegram_calls_api    PASSED

16 passed in X.XXs
```
