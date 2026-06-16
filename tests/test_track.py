"""Öneri karnesi (track record) testleri — kayıt, çözümleme, özet matematiği."""
# (dip adayları ve hacim kapısı testleri test_technical.py'dedir)
import json

from scripts.track import (
    record_signals, resolve_signals, summarize, prune, update_track,
)

DAY = 86400


def _ph(closes, start_day=0):
    """Kapanış listesinden ardışık günlük barlar (epoch = gün × 86400)."""
    return [
        {"t": (start_day + i) * DAY, "o": c, "h": c, "l": c, "c": c, "v": 1000}
        for i, c in enumerate(closes)
    ]


def _date(day):
    """Gün indeksini ISO tarihe çevir (epoch günü)."""
    import datetime
    return datetime.datetime.fromtimestamp(day * DAY, datetime.timezone.utc).date().isoformat()


def _report(stocks):
    return {"stocks": stocks}


# ── record_signals ──
def test_record_creates_one_per_symbol_and_dedupes():
    report = _report([
        {"symbol": "AAA", "verdict_key": "buy", "score": 70,
         "price_history": _ph([10, 11, 12]), "gates": [],
         "trade_setup": {"stop": 11.0, "target": 14.0}},
        {"symbol": "BBB", "verdict_key": "sell", "score": 30,
         "price_history": _ph([5, 4, 3])},
    ])
    track = {"signals": []}
    added = record_signals(report, track)
    assert added == 2
    # aynı rapor tekrar kaydedilirse (aynı bar tarihi) yeni kayıt eklenmez
    assert record_signals(report, track) == 0
    assert len(track["signals"]) == 2
    sig = next(s for s in track["signals"] if s["symbol"] == "AAA")
    assert sig["price"] == 12 and sig["verdict_key"] == "buy"
    assert sig["stop"] == 11.0 and sig["target"] == 14.0


def test_record_skips_errors_and_missing_history():
    report = _report([
        {"symbol": "ERR", "error": "yok"},
        {"symbol": "NOH", "verdict_key": "buy", "score": 60},
    ])
    track = {"signals": []}
    assert record_signals(report, track) == 0


def test_record_labels_bars_with_tr_trading_day():
    # yfinance BIST günlük barları 00:00 TR (=21:00 UTC önceki gün) damgalı.
    # UTC ile etiketlemek işlem gününü 1 gün geri kaydırır — TR günü esastır.
    midnight_tr = 10 * DAY - 3 * 3600   # gün-10'un 00:00 TR'si = gün-9 21:00 UTC
    report = _report([{
        "symbol": "AAA", "verdict_key": "buy", "score": 60,
        "price_history": [{"t": midnight_tr, "o": 1, "h": 1, "l": 1, "c": 1.0, "v": 1}],
    }])
    track = {"signals": []}
    record_signals(report, track)
    assert track["signals"][0]["date"] == _date(10)   # gün-9 DEĞİL


# ── resolve_signals ──
def test_resolve_exact_trading_day_horizons():
    closes = [100 + i for i in range(16)]   # d0..d15
    report = _report([{"symbol": "AAA", "price_history": _ph(closes)}])
    track = {"signals": [
        {"date": _date(0), "symbol": "AAA", "verdict_key": "buy", "price": 100.0},
        {"date": _date(12), "symbol": "AAA", "verdict_key": "buy", "price": 112.0},
    ]}
    resolve_signals(track, report)
    s0 = track["signals"][0]
    # d0 + 5 işlem günü = d5 kapanışı 105 → +5%; d0+10 = 110 → +10%
    assert abs(s0["fwd5"] - 5.0) < 1e-6 and s0["win5"] is True
    assert abs(s0["fwd10"] - 10.0) < 1e-6 and s0["win10"] is True
    s1 = track["signals"][1]
    # d12 + 5 = d17 yok → çözülmemiş kalır
    assert "fwd5" not in s1 and "fwd10" not in s1


def test_resolve_negative_return_is_loss():
    closes = [100] + [90] * 12
    report = _report([{"symbol": "AAA", "price_history": _ph(closes)}])
    track = {"signals": [{"date": _date(0), "symbol": "AAA",
                          "verdict_key": "buy", "price": 100.0}]}
    resolve_signals(track, report)
    s = track["signals"][0]
    assert s["fwd5"] < 0 and s["win5"] is False


def test_resolve_sell_wins_when_price_falls():
    # SAT sinyalinin isabeti fiyatın DÜŞMESİdir — yön verdict'e göre değerlendirilir
    closes = [100] + [90] * 12
    report = _report([{"symbol": "AAA", "price_history": _ph(closes)}])
    track = {"signals": [{"date": _date(0), "symbol": "AAA",
                          "verdict_key": "sell", "price": 100.0}]}
    resolve_signals(track, report)
    s = track["signals"][0]
    assert s["fwd5"] < 0 and s["win5"] is True


def _ph_dates(pairs):
    """[(gün_indeksi, kapanış)] → bar listesi (epoch = gün × 86400)."""
    return [{"t": d * DAY, "o": c, "h": c, "l": c, "c": c, "v": 1000} for d, c in pairs]


def test_resolve_uses_market_calendar_across_gaps():
    # B hissesinde d4 eksik (likidite boşluğu). "5 gün sonra" ORTAK takvimde d5'tir;
    # her hisse kendi index'iyle saymaz → ikisi de aynı piyasa gününe göre ölçülür.
    report = _report([
        {"symbol": "A", "price_history": _ph_dates(
            [(0, 100), (1, 101), (2, 102), (3, 103), (4, 104), (5, 110)])},
        {"symbol": "B", "price_history": _ph_dates(
            [(0, 200), (1, 201), (2, 202), (3, 203), (5, 230)])},   # d4 yok
    ])
    track = {"signals": [
        {"date": _date(0), "symbol": "A", "verdict_key": "buy", "price": 100.0},
        {"date": _date(0), "symbol": "B", "verdict_key": "buy", "price": 200.0},
    ]}
    resolve_signals(track, report)
    assert track["signals"][0]["fwd5"] == 10.0   # 100→110
    assert track["signals"][1]["fwd5"] == 15.0   # 200→230 (d4 eksik olsa da d5'e göre)


def test_resolve_missing_target_uses_nearest_prior():
    # Hedef gün hissede yoksa, sinyalden sonraki en yakın önceki bar kullanılır
    report = _report([
        {"symbol": "C", "price_history": _ph_dates(
            [(0, 100), (1, 101), (2, 102), (3, 103), (4, 108)])},     # d5 yok
        {"symbol": "D", "price_history": _ph_dates(
            [(0, 50), (1, 51), (2, 52), (3, 53), (4, 54), (5, 60)])},  # takvime d5 ekler
    ])
    track = {"signals": [{"date": _date(0), "symbol": "C",
                          "verdict_key": "buy", "price": 100.0}]}
    resolve_signals(track, report)
    assert track["signals"][0]["fwd5"] == 8.0   # hedef d5 yok → d4 (108) kullanıldı


def test_resolve_leaves_unknown_symbol_untouched():
    report = _report([{"symbol": "AAA", "price_history": _ph([1, 2, 3])}])
    track = {"signals": [{"date": _date(0), "symbol": "ZZZ",
                          "verdict_key": "buy", "price": 1.0}]}
    resolve_signals(track, report)
    assert "fwd5" not in track["signals"][0]


# ── summarize ──
def test_summarize_math_by_hand():
    today = _date(20)
    track = {"signals": [
        {"date": _date(15), "symbol": "A", "verdict_key": "buy",
         "price": 1, "fwd10": 10.0, "win10": True, "fwd5": 1.0, "win5": True},
        {"date": _date(16), "symbol": "B", "verdict_key": "buy",
         "price": 1, "fwd10": 2.0, "win10": True, "fwd5": -1.0, "win5": False},
        {"date": _date(17), "symbol": "C", "verdict_key": "buy",
         "price": 1, "fwd10": -4.0, "win10": False, "fwd5": -2.0, "win5": False},
        {"date": _date(18), "symbol": "D", "verdict_key": "sell",
         "price": 1, "fwd10": -6.0, "win10": True},   # SAT + düşüş = isabet
        {"date": _date(18), "symbol": "E", "verdict_key": "hold",
         "price": 1, "fwd10": 3.0, "win10": True},
    ]}
    k = summarize(track, today=today)
    o = k["90g"]["overall"]["h10"]
    # genel isabet YÖNLÜ çağrılardan (buy+sell): kazanan buy+10, buy+2, sell−6
    # → 3/4 = %75. TUT yön iddiası olmadığından genel isabete girmez.
    assert o["n"] == 4 and o["win_rate"] == 75
    # avg_ret ham ileri getiri ortalamasıdır: (+10+2−4−6)/4 = +0.5
    assert abs(o["avg_ret"] - 0.5) < 1e-6
    b = k["90g"]["by_verdict"]["buy"]["h10"]
    # buy: +10, +2, −4 → isabet %67, ort +2.67, kazanç ort +6, kayıp ort −4
    assert b["n"] == 3 and b["win_rate"] == 67
    assert abs(b["avg_win"] - 6.0) < 1e-6 and abs(b["avg_loss"] + 4.0) < 1e-6
    # sell kendi yönüyle: düştü → %100 isabet
    assert k["90g"]["by_verdict"]["sell"]["h10"]["win_rate"] == 100
    # hold ayrı raporlanır ama genel isabete dahil değil
    assert k["90g"]["by_verdict"]["hold"]["h10"]["n"] == 1
    # 5g kolonu ayrı sayılır (sadece buy'ların fwd5'i var → n=3)
    assert k["90g"]["overall"]["h5"]["n"] == 3


def test_summarize_window_filters_old_signals():
    today = _date(200)
    track = {"signals": [
        {"date": _date(195), "symbol": "A", "verdict_key": "buy",
         "price": 1, "fwd10": 5.0, "win10": True},
        {"date": _date(50), "symbol": "B", "verdict_key": "buy",
         "price": 1, "fwd10": -5.0, "win10": False},   # 150 gün önce → 90g dışı
    ]}
    k = summarize(track, today=today)
    assert k["90g"]["overall"]["h10"]["n"] == 1
    assert k["30g"]["overall"]["h10"]["n"] == 1


def test_summarize_empty_track():
    k = summarize({"signals": []}, today=_date(10))
    assert k["90g"]["overall"]["h10"]["n"] == 0


def test_record_marks_dip_candidates():
    report = _report([
        {"symbol": "AAA", "verdict_key": "sell", "score": 40,
         "price_history": _ph([10, 9, 8, 8.2])},
        {"symbol": "BBB", "verdict_key": "hold", "score": 50,
         "price_history": _ph([5, 5, 5, 5])},
    ])
    report["dip_adaylari"] = [{"symbol": "AAA", "rsi": 25.0}]
    track = {"signals": []}
    record_signals(report, track)
    a = next(s for s in track["signals"] if s["symbol"] == "AAA")
    b = next(s for s in track["signals"] if s["symbol"] == "BBB")
    assert a.get("dip") is True and "dip" not in b


def test_summarize_dip_row_uses_long_semantics():
    # Dip adayı uzun (yükseliş) tezidir: verdict SAT olsa bile isabet = yükseliş
    today = _date(20)
    track = {"signals": [
        {"date": _date(15), "symbol": "A", "verdict_key": "sell", "dip": True,
         "price": 1, "fwd10": 4.0, "win10": False},   # SAT için ıska ama dip için isabet
        {"date": _date(16), "symbol": "B", "verdict_key": "sell", "dip": True,
         "price": 1, "fwd10": -2.0, "win10": True},   # SAT isabeti ama dip için ıska
        {"date": _date(17), "symbol": "C", "verdict_key": "hold",
         "price": 1, "fwd10": 9.0, "win10": True},    # dip değil — satıra girmez
    ]}
    k = summarize(track, today=today)
    d = k["90g"]["dip"]["h10"]
    assert d["n"] == 2 and d["win_rate"] == 50
    assert abs(d["avg_ret"] - 1.0) < 1e-6


# ── prune ──
def test_prune_drops_old_records():
    track = {"signals": [
        {"date": _date(10), "symbol": "OLD", "verdict_key": "buy", "price": 1},
        {"date": _date(200), "symbol": "NEW", "verdict_key": "buy", "price": 1},
    ]}
    removed = prune(track, today=_date(210), days=180)
    assert removed == 1
    assert [s["symbol"] for s in track["signals"]] == ["NEW"]


# ── update_track (entegrasyon) ──
def test_update_track_end_to_end(tmp_path):
    import datetime
    path = tmp_path / "track.json"
    # prune gerçek bugüne göre çalışır → yakın geçmiş tarihler kullan
    start = (datetime.date.today() - datetime.date(1970, 1, 1)).days - 30
    closes = [100 + i for i in range(12)]
    report = _report([{"symbol": "AAA", "verdict_key": "buy", "score": 70,
                       "price_history": _ph(closes, start_day=start), "gates": []}])
    karne = update_track(report, path=str(path))
    assert path.exists()
    saved = json.loads(path.read_text())
    assert len(saved["signals"]) == 1
    # geçmiş genişleyince eski sinyal çözülür
    closes2 = closes + [120 + i for i in range(10)]
    report2 = _report([{"symbol": "AAA", "verdict_key": "hold", "score": 50,
                        "price_history": _ph(closes2, start_day=start), "gates": []}])
    karne2 = update_track(report2, path=str(path))
    saved2 = json.loads(path.read_text())
    first = next(s for s in saved2["signals"] if s["date"] == _date(start + 11))
    assert "fwd10" in first and first["win10"] is True
    assert "overall" in karne2["90g"]


def test_update_track_record_false_only_resolves(tmp_path):
    path = tmp_path / "track.json"
    report = _report([{"symbol": "AAA", "verdict_key": "buy", "score": 70,
                       "price_history": _ph([1, 2, 3]), "gates": []}])
    update_track(report, path=str(path), record=False)
    saved = json.loads(path.read_text())
    assert saved["signals"] == []
