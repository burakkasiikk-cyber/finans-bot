#!/usr/bin/env python3
"""Backtest laboratuvarı — giriş kuralı × filtre kombinasyonlarını tarihsel veride ölçer.

Araştırma aracıdır; workflow'a girmez. Amaç: skorlamaya eklenecek her filtrenin
KANITLA seçilmesi. Kabul kriteri (sabit): bir filtre ancak HER İKİ yarı dönemde de
hem isabeti hem ortalama getiriyi (beklentiyi) taban kurala göre iyileştiriyorsa
ve n>=150 ise koda girer.

Kullanım:  python3 -m scripts.backtest_lab [period]   (vars: 2y)

Not: bilanço-haftası filtresi tarihsel bilanço tarihleri yfinance'de BIST için
güvenilir olmadığından laboratuvarda test EDİLEMEZ — dürüstçe kapsam dışı.
"""
import sys
import warnings

from scripts.analyze import BIST_STOCKS
from scripts.technical import rsi

HORIZONS = (5, 10)
MIN_TRADES = 150          # kabul için asgari işlem sayısı
TRIM = 0.05               # kırpılmış ortalama için uç dilim


# ──────────────────── Giriş kuralları (taban) ────────────────────
def entry_tf(c, low, vol, i, ictx):
    """Trend takibi — mevcut sistemin backtest kuralı."""
    w = c[: i + 1]
    if len(w) < 51:
        return False
    ma20 = sum(w[-20:]) / 20
    ma50 = sum(w[-50:]) / 50
    r = rsi(w)
    return w[-1] > ma50 and w[-1] > ma20 and r is not None and 40 <= r < 70


def entry_mr(c, low, vol, i, ictx):
    """Dip dönüşü — aşırı satım + yeşil gün teyidi."""
    w = c[: i + 1]
    if len(w) < 16:
        return False
    r = rsi(w)
    return r is not None and r < 30 and c[i] > c[i - 1]


# ──────────────────── Filtreler (eklenebilir şartlar) ────────────────────
def f_vol(c, low, vol, i, ictx):
    """Hacim teyidi: 5g ort hacim >= 1.2 × 20g ort hacim."""
    if i < 20 or not vol or any(v is None for v in vol[i - 19 : i + 1]):
        return False
    s = sum(vol[i - 4 : i + 1]) / 5
    l = sum(vol[i - 19 : i + 1]) / 20
    return l > 0 and s / l >= 1.2


def f_rs(c, low, vol, i, ictx):
    """Göreli güç: hissenin 21g getirisi endeksten iyi."""
    if i < 21 or ictx is None:
        return False
    iret = ictx[i]
    if iret is None:
        return False
    sret = c[i] / c[i - 21] - 1
    return sret > iret


def f_sup(c, low, vol, i, ictx):
    """Desteğe yakınlık: fiyat 20g dibinin %5 bandında (dip yakını giriş)."""
    if i < 20:
        return False
    s = min(low[i - 19 : i + 1])
    return s > 0 and c[i] <= s * 1.05


BASES = {"TF": entry_tf, "MR": entry_mr}
FILTERS = {"hacim": f_vol, "görelig": f_rs, "destek": f_sup}


# ──────────────────── Çekirdek ────────────────────
def load_data(period="2y"):
    import yfinance as yf
    tickers = ["XU100.IS"] + [f"{s}.IS" for s in BIST_STOCKS]
    raw = yf.download(tickers, period=period, interval="1d",
                      progress=False, group_by="ticker")
    idx = raw["XU100.IS"]["Close"].dropna()
    stocks = {}
    for sym in BIST_STOCKS:
        try:
            df = raw[f"{sym}.IS"].dropna(subset=["Close"])
        except KeyError:
            continue
        if len(df) < 60:
            continue
        dates = list(df.index)
        c = [float(x) for x in df["Close"]]
        low = [float(x) for x in df["Low"]]
        vol = [float(x) if x == x else None for x in df["Volume"]]
        # Endeksin 21g getirisi, hissenin her barı için tarih hizalı (asof)
        ictx = []
        for d in dates:
            sl = idx[idx.index <= d]
            ictx.append(float(sl.iloc[-1] / sl.iloc[-22] - 1) if len(sl) > 21 else None)
        stocks[sym] = {"c": c, "low": low, "vol": vol, "ictx": ictx}
    return stocks


def run_combo(stocks, base_fn, filter_fns, horizon):
    """(pozisyon_oranı, ileri_getiri) listesi döndürür."""
    trades = []
    for sym, d in stocks.items():
        c, low, vol, ictx = d["c"], d["low"], d["vol"], d["ictx"]
        n = len(c)
        i = 50
        while i < n - horizon:
            if base_fn(c, low, vol, i, ictx) and all(f(c, low, vol, i, ictx) for f in filter_fns):
                trades.append((i / n, (c[i + horizon] / c[i] - 1) * 100))
                i += horizon
            else:
                i += 1
    return trades


def stats(trades):
    rets = [t[1] for t in trades]
    n = len(rets)
    if n == 0:
        return {"n": 0}
    srt = sorted(rets)
    k = int(n * TRIM)
    trim = srt[k : n - k] if n - 2 * k > 0 else srt
    return {
        "n": n,
        "win": round(sum(r > 0 for r in rets) / n * 100),
        "avg": round(sum(rets) / n, 2),
        "trim": round(sum(trim) / len(trim), 2),
    }


def halves(trades):
    return ([t for t in trades if t[0] < 0.5], [t for t in trades if t[0] >= 0.5])


def passes(combo_tr, base_tr):
    """Kabul kriteri: her iki yarıda da isabet VE ortalama taban kuraldan iyi, n>=150."""
    if len(combo_tr) < MIN_TRADES:
        return False
    for ch, bh in zip(halves(combo_tr), halves(base_tr)):
        cs, bs = stats(ch), stats(bh)
        if cs["n"] == 0 or bs["n"] == 0:
            return False
        if cs["win"] <= bs["win"] or cs["avg"] <= bs["avg"]:
            return False
    return True


def main(period="2y"):
    warnings.filterwarnings("ignore")
    print(f"Veri indiriliyor ({period})…")
    stocks = load_data(period)
    print(f"{len(stocks)} hisse yüklendi.\n")
    from itertools import combinations
    fnames = list(FILTERS)
    combos = [()] + [(f,) for f in fnames] + list(combinations(fnames, 2))
    results = []
    for bname, bfn in BASES.items():
        base_trades = {h: run_combo(stocks, bfn, [], h) for h in HORIZONS}
        for combo in combos:
            ffns = [FILTERS[f] for f in combo]
            for h in HORIZONS:
                tr = base_trades[h] if not combo else run_combo(stocks, bfn, ffns, h)
                s = stats(tr)
                h1, h2 = (stats(x) for x in halves(tr))
                ok = passes(tr, base_trades[h]) if combo else None
                results.append((bname, "+".join(combo) or "—", h, s, h1, h2, ok))

    hdr = f"{'taban':4s} {'filtre':16s} {'ufuk':4s} {'n':>5s} {'isabet':>7s} {'ort':>7s} {'kırp':>7s} | {'1.yarı':>14s} | {'2.yarı':>14s} | sonuç"
    print(hdr); print("-" * len(hdr))
    for bname, fl, h, s, h1, h2, ok in results:
        if s["n"] == 0:
            print(f"{bname:4s} {fl:16s} {h:3d}g {0:5d}  (işlem yok)")
            continue
        half = lambda x: f"%{x.get('win','—')} {x.get('avg',0):+.2f}%" if x["n"] else "—"
        verdict = "" if ok is None else ("✅ KABUL" if ok else "❌ red")
        print(f"{bname:4s} {fl:16s} {h:3d}g {s['n']:5d}  %{s['win']:5d} {s['avg']:+6.2f}% {s['trim']:+6.2f}% | {half(h1):>14s} | {half(h2):>14s} | {verdict}")
    return results


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "2y")
