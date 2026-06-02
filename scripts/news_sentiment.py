#!/usr/bin/env python3
"""
Haber duygu analizi — ücretsiz, kelime tabanlı (API gerekmez).

Her hisse için yfinance haber başlıklarını çeker, olumlu/olumsuz finans
kelimelerini sayar ve skora eklenecek bir düzeltme (-8..+8) üretir.
Haberler kullanıcıya GÖSTERİLMEZ; yalnızca skoru olumlu/olumsuz etkiler.

⚠️ Kelime tabanlı analiz kabadır; bu yüzden etki bilinçli olarak DÜŞÜK
tutulur (en fazla ±8 puan) — teknik sinyali ezmemesi için.
"""
import math

# Yalnızca GÜÇLÜ, belirgin kelimeler — "high/top/rise/deal/risk" gibi genel
# kelimeler kasıtlı olarak ÇIKARILDI (yanlış sinyal üretmesinler diye).
POSITIVE = {
    # İngilizce
    "beats", "beat", "record", "surge", "surges", "soars", "soar", "upgrade",
    "upgraded", "rally", "profit", "profits", "outperform", "buyback", "dividend",
    "breakthrough", "approval", "approved", "jumps", "soared", "wins", "won",
    # Türkçe
    "kazanç", "rekor", "yükseldi", "güçlü", "kâr", "temettü", "onay", "ihale",
    "rekortmen", "ihracat", "anlaşma",
}

NEGATIVE = {
    # İngilizce
    "miss", "misses", "missed", "plunge", "plunges", "downgrade", "downgraded",
    "loss", "losses", "lawsuit", "probe", "investigation", "fraud", "slump",
    "crash", "layoff", "layoffs", "recall", "halt", "halts", "default", "selloff",
    "tumble", "tumbles", "bankruptcy", "warns", "warning", "plummet", "plummets",
    # Türkçe
    "zarar", "dava", "soruşturma", "ceza", "iflas", "durduruldu", "geriledi",
    "uyarı", "tahkikat", "kaybetti", "düştü", "zayıfladı",
}

# Şirket adından çıkarılacak genel/kurumsal kelimeler (relevans için)
_STOP_NAME = {
    "inc", "corp", "corporation", "company", "co", "ltd", "limited", "plc", "group",
    "holding", "holdings", "the", "and", "anonim", "ortakligi", "ortaklığı", "sirketi",
    "şirketi", "a.s", "a.ş", "as", "turk", "türk", "ve", "sanayi", "ticaret",
    "yatirim", "yatırım", "gayrimenkul", "bankasi", "bankası", "teknoloji",
}


def _titles(news_list) -> list:
    """yfinance haber listesinden başlıkları çıkar (eski ve yeni şema)."""
    out = []
    for item in news_list or []:
        title = None
        if isinstance(item, dict):
            title = item.get("title")
            if not title and isinstance(item.get("content"), dict):
                title = item["content"].get("title")
        if title:
            out.append(str(title))
    return out


def _relevance_keys(symbol: str, name: str) -> set:
    """Hisseye özgü anahtar kelimeler — sembol + isimden anlamlı parçalar."""
    keys = {symbol.lower()}
    for w in (name or "").lower().replace(".", " ").replace(",", " ").split():
        w = w.strip()
        if len(w) >= 4 and w not in _STOP_NAME:
            keys.add(w)
    return keys


def analyze_titles(titles: list, rel_keys: set = None) -> dict:
    """Başlık listesinden duygu sonucu üret.

    rel_keys verilirse, SADECE o hisseyle ilgili (adı/sembolü geçen) başlıklar
    sayılır — genel piyasa haberleri elenir, yanlış sinyal önlenir."""
    pos = neg = 0
    relevant = 0
    for t in titles:
        low = t.lower()
        if rel_keys and not any(k in low for k in rel_keys):
            continue   # bu haber hisseyle ilgili değil, atla
        relevant += 1
        words = set(low.replace(",", " ").replace(".", " ")
                    .replace("'", " ").replace("’", " ").split())
        pos += len(words & POSITIVE)
        neg += len(words & NEGATIVE)

    net = pos - neg
    # Ölçekle: her net puan ~2.5 skor puanı, ±5 ile sınırla (teknik sinyali ezmesin)
    adjustment = max(-5, min(5, round(net * 2.5)))
    label = "olumlu" if net > 0 else "olumsuz" if net < 0 else "nötr"
    return {
        "adjustment": adjustment,
        "sentiment": label,
        "pos": pos,
        "neg": neg,
        "count": relevant,
    }


def fetch_news_sentiment(yticker: str, symbol: str = "", name: str = "") -> dict:
    """Bir ticker için yfinance haberlerini çekip duygu düzeltmesi döndürür.

    Yalnızca hisseye özel başlıklar sayılır. Ağ hatasında nötr döner — patlamaz."""
    try:
        import yfinance as yf
        news = yf.Ticker(yticker).news
        titles = _titles(news)
        rel = _relevance_keys(symbol or yticker.replace(".IS", ""), name)
        return analyze_titles(titles, rel)
    except Exception:
        return {"adjustment": 0, "sentiment": "nötr", "pos": 0, "neg": 0, "count": 0}


if __name__ == "__main__":
    import sys
    yt = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    print(yt, fetch_news_sentiment(yt, yt.replace(".IS", "")))
