#!/usr/bin/env python3
"""Öneri karnesi — sistemin verdiği sinyallerin GERÇEK sonuçlarını ölçer.

Her çalıştırmada o günün verdict'leri kaydedilir; 5 ve 10 işlem günü dolan
kayıtlara ileri getiri yazılır; son 30/90 günün isabet ve beklenti istatistiği
report["karne"] olarak rapora konur. Amaç: sistem kendi isabetini herkesten
önce kendisi ölçsün ve gösterilsin — iyileştirmeler ancak böyle kanıtlanır.
"""
import datetime
import json
from pathlib import Path

HORIZONS = (5, 10)        # işlem günü cinsinden ölçüm ufukları
PRUNE_DAYS = 180          # bundan eski kayıtlar atılır
WINDOWS = {"30g": 30, "90g": 90}   # özet pencereleri (takvim günü)
TRACK_PATH = "data/track.json"


# BIST işlem günü etiketi: yfinance günlük barları 00:00 TR damgalar
# (= önceki gün 21:00 UTC) — UTC'ye çevirmek işlem gününü 1 gün kaydırır.
TR_TZ = datetime.timezone(datetime.timedelta(hours=3))


def _bar_date(ts: int) -> str:
    return datetime.datetime.fromtimestamp(ts, TR_TZ).date().isoformat()


def record_signals(report: dict, track: dict) -> int:
    """Her hisse için (son bar tarihi, sembol) anahtarıyla sinyal kaydı ekler.

    Aynı gün + sembol zaten kayıtlıysa atlanır (gün içi tekrar çalıştırmalar
    ve hafta sonu çalıştırmaları doğal olarak teklenir). Döndürür: eklenen sayı."""
    existing = {(s["date"], s["symbol"]) for s in track["signals"]}
    dips = {d["symbol"] for d in report.get("dip_adaylari") or []}
    added = 0
    for s in report.get("stocks", []):
        if "error" in s or not s.get("verdict_key"):
            continue
        ph = s.get("price_history") or []
        if not ph or not ph[-1].get("c"):
            continue
        date = _bar_date(ph[-1]["t"])
        if (date, s["symbol"]) in existing:
            continue
        ts = s.get("trade_setup") or {}
        rec = {
            "date": date,
            "symbol": s["symbol"],
            "verdict_key": s["verdict_key"],
            "score": s.get("score"),
            "price": ph[-1]["c"],
        }
        if ts.get("stop") is not None:
            rec["stop"] = ts["stop"]
        if ts.get("target") is not None:
            rec["target"] = ts["target"]
        if s.get("gates"):
            rec["gates"] = s["gates"]
        if s["symbol"] in dips:
            rec["dip"] = True   # dip dönüşü adayı — karnede ayrı satırda ölçülür
        track["signals"].append(rec)
        existing.add((date, s["symbol"]))
        added += 1
    return added


def resolve_signals(track: dict, report: dict) -> int:
    """Ufku dolan kayıtlara fwd5/win5, fwd10/win10 yazar. Döndürür: yazılan alan sayısı.

    İleri getiri, sinyal tarihinden N İŞLEM GÜNÜ sonraki kapanışa göre hesaplanır
    (price_history zaten yalnızca işlem günlerini içerir)."""
    hist = {}
    for s in report.get("stocks", []):
        ph = s.get("price_history") or []
        if "error" not in s and ph:
            hist[s["symbol"]] = ([_bar_date(b["t"]) for b in ph],
                                 [b["c"] for b in ph])
    resolved = 0
    for sig in track["signals"]:
        if all(f"fwd{h}" in sig for h in HORIZONS):
            continue
        dates_closes = hist.get(sig["symbol"])
        if not dates_closes:
            continue
        dates, closes = dates_closes
        try:
            idx = dates.index(sig["date"])
        except ValueError:
            continue   # sinyal günü saklanan pencereden düşmüş — prune temizler
        for h in HORIZONS:
            if f"fwd{h}" in sig or idx + h >= len(closes) or not sig.get("price"):
                continue
            fwd = round((closes[idx + h] / sig["price"] - 1) * 100, 2)
            sig[f"fwd{h}"] = fwd
            # İsabet YÖNLÜdür: AL için yükseliş, SAT için DÜŞÜŞ isabettir
            if sig.get("verdict_key") in SHORTS:
                sig[f"win{h}"] = fwd < 0
            else:
                sig[f"win{h}"] = fwd > 0
            resolved += 1
    return resolved


LONGS = ("strong_buy", "buy")
SHORTS = ("sell", "strong_sell")


def _stats(items: list) -> dict:
    """items: (ileri_getiri, isabet_mi) çiftleri. avg_ret/avg_win/avg_loss ham
    fiyat hareketidir; win_rate verdict yönüne göre hesaplanmış isabettir."""
    n = len(items)
    if n == 0:
        return {"n": 0, "win_rate": None, "avg_ret": None,
                "avg_win": None, "avg_loss": None}
    rets = [r for r, _ in items]
    ups = [r for r in rets if r > 0]
    downs = [r for r in rets if r <= 0]
    return {
        "n": n,
        "win_rate": round(sum(1 for _, w in items if w) / n * 100),
        "avg_ret": round(sum(rets) / n, 2),    # beklenti (işlem başına ortalama)
        "avg_win": round(sum(ups) / len(ups), 2) if ups else None,
        "avg_loss": round(sum(downs) / len(downs), 2) if downs else None,
    }


def summarize(track: dict, today: str = None) -> dict:
    """Pencere → {overall, by_verdict} → ufuk (h5/h10) → istatistik.

    Genel (overall) isabet yalnızca YÖNLÜ çağrılardan hesaplanır (AL+SAT);
    TUT yön iddiası taşımadığından by_verdict'te ayrı raporlanır."""
    today_d = (datetime.date.fromisoformat(today) if today
               else datetime.datetime.now(datetime.timezone.utc).date())
    out = {}
    for wname, wdays in WINDOWS.items():
        cutoff = (today_d - datetime.timedelta(days=wdays)).isoformat()
        sigs = [s for s in track["signals"] if s["date"] >= cutoff]
        overall, by_v = {}, {}
        for h in HORIZONS:
            done = [s for s in sigs if f"fwd{h}" in s]
            directional = [(s[f"fwd{h}"], s.get(f"win{h}", s[f"fwd{h}"] > 0))
                           for s in done if s.get("verdict_key") in LONGS + SHORTS]
            overall[f"h{h}"] = _stats(directional)
            for s in done:
                by_v.setdefault(s["verdict_key"], {}).setdefault(f"_r{h}", []).append(
                    (s[f"fwd{h}"], s.get(f"win{h}", s[f"fwd{h}"] > 0)))
        for v, d in by_v.items():
            by_v[v] = {f"h{h}": _stats(d.get(f"_r{h}", [])) for h in HORIZONS}
        # Dip adayları ayrı satır: uzun (yükseliş) tezidir — isabet = fwd > 0
        dip = {}
        for h in HORIZONS:
            items = [(s[f"fwd{h}"], s[f"fwd{h}"] > 0)
                     for s in sigs if s.get("dip") and f"fwd{h}" in s]
            dip[f"h{h}"] = _stats(items)
        out[wname] = {"overall": overall, "by_verdict": by_v, "dip": dip}
    return out


def prune(track: dict, today: str = None, days: int = PRUNE_DAYS) -> int:
    today_d = (datetime.date.fromisoformat(today) if today
               else datetime.datetime.now(datetime.timezone.utc).date())
    cutoff = (today_d - datetime.timedelta(days=days)).isoformat()
    before = len(track["signals"])
    track["signals"] = [s for s in track["signals"] if s["date"] >= cutoff]
    return before - len(track["signals"])


def update_track(report: dict, path: str = TRACK_PATH, record: bool = True) -> dict:
    """Yükle → (kaydet) → çözümle → buda → diske yaz → özet döndür.

    record=False: gün içi çalıştırma — yeni kayıt üretmez, yalnız çözümler."""
    p = Path(path)
    try:
        track = json.loads(p.read_text())
        track.setdefault("signals", [])
    except (FileNotFoundError, json.JSONDecodeError):
        track = {"signals": []}
    if record:
        record_signals(report, track)
    resolve_signals(track, report)
    prune(track)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(track, ensure_ascii=False))
    return summarize(track)
