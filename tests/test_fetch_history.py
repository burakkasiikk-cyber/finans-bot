"""fetch_history yardımcıları — günlük değişim veri hatasına karşı dayanıklı olmalı."""
from scripts.fetch_history import daily_change_pct


def _bars(closes):
    return [{"t": i, "o": c, "h": c, "l": c, "c": c, "v": 1000} for i, c in enumerate(closes)]


def test_daily_change_from_prev_close():
    # 6.445 → 6.54 = +1.47% (gerçek TURSG hareketi)
    assert daily_change_pct(6.54, _bars([6.445, 6.54])) == 1.47


def test_daily_change_uses_live_price_over_last_bar():
    # canlı fiyat son bardan farklıysa değişim canlıya göre, önceki kapanıştan
    assert daily_change_pct(10.5, _bars([10.0, 10.2])) == 5.0


def test_daily_change_ignores_garbage_info_value():
    # info.regularMarketChangePercent = -49 gibi bozuk değer ARTIK kullanılmaz;
    # değişim daima bar verisinden iç tutarlı hesaplanır
    ch = daily_change_pct(6.54, _bars([6.445, 6.54]))
    assert abs(ch) < 20   # makul gün içi sınır — split artığı sızmaz


def test_daily_change_none_when_no_prev():
    assert daily_change_pct(10.0, _bars([10.0])) is None
    assert daily_change_pct(10.0, []) is None
