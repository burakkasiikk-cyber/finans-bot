/* ============================================================
   analysis.js — Analiz motoru
   Temel + teknik verilerden 6 boyutlu skor ve AL/TUT/SAT
   kararı üretir. Saf hesaplama: DOM'a dokunmaz.
   ============================================================ */
const Analyzer = (() => {

  const isNum = (v) => v !== undefined && v !== null && !isNaN(v) && v !== "";

  /** Birden çok olası alan adını dener, ilk sayısal değeri döner. */
  function pick(m, keys) {
    for (const k of keys) if (isNum(m?.[k])) return Number(m[k]);
    return null;
  }

  /** Eşiklere göre 0-100 puan. dir: "up" (yüksek iyi) / "down" (düşük iyi). */
  function score(v, key) {
    if (!isNum(v)) return null;
    const cfg = CONFIG.THRESHOLDS[key];
    if (!cfg) return null;
    const [a, b, c, d] = cfg.t;
    if (cfg.dir === "up")  return v >= a ? 92 : v >= b ? 74 : v >= c ? 55 : v >= d ? 38 : 18;
    /* down */             return v <= a ? 92 : v <= b ? 74 : v <= c ? 55 : v <= d ? 38 : 18;
  }

  const line = (label, display, sc, msg, note = false) => ({ label, display, score: sc, msg, note });

  function makeDim(name, weightKey, subs, question) {
    const scored = subs.filter((s) => s.score != null && s.note !== true);
    const sc = scored.length ? Math.round(scored.reduce((a, s) => a + s.score, 0) / scored.length) : null;
    return { name, weight: CONFIG.WEIGHTS[weightKey], subs, score: sc, q: question };
  }

  function verdictOf(s) {
    if (s == null) return { label: "VERİ YETERSİZ", color: "var(--muted)" };
    return CONFIG.VERDICT_BANDS.find((b) => s >= b.min) || CONFIG.VERDICT_BANDS[CONFIG.VERDICT_BANDS.length - 1];
  }

  function buildSummary(verdict, pros, cons, overall) {
    if (overall == null) return "Bu hisse için yeterli temel veri bulunamadı (ücretsiz planda bazı veriler sınırlı olabilir).";
    let s = `Genel skor <b>${overall}/100</b> → <b style="color:${verdict.color}">${verdict.label}</b>. `;
    if (pros.length) s += `En güçlü yön: ${pros[0].toLowerCase()}. `;
    if (cons.length) s += `Dikkat edilmesi gereken nokta: ${cons[0].toLowerCase()}.`;
    else if (pros.length) s += "Belirgin bir zayıf nokta öne çıkmıyor.";
    return s;
  }

  /** Ana giriş: metric objesi (m), quote (q), recommendation dizisi (rec). */
  function analyze(m, q, rec) {
    const dims = [];

    // 1) Değerleme
    const pe = pick(m, ["peTTM", "peBasicExclExtraTTM", "peExclExtraTTM", "peNormalizedAnnual"]);
    const pb = pick(m, ["pbQuarterly", "pbAnnual"]);
    const ps = pick(m, ["psTTM", "psAnnual"]);
    const valSubs = [];
    if (isNum(pe)) valSubs.push(line("F/K Oranı", pe < 0 ? "Zararda" : fx(pe), pe < 0 ? 14 : score(pe, "pe"),
      pe < 0 ? "Şirket zarar açıklıyor (negatif F/K)" : pe < 15 ? "F/K düşük — ucuz fiyatlanmış olabilir" : pe > 40 ? "F/K yüksek — pahalı, yüksek beklenti fiyatlanmış" : "F/K makul seviyede"));
    if (isNum(pb)) valSubs.push(line("PD/DD", fx(pb), score(pb, "pb"),
      pb < 1.5 ? "Defter değerine göre ucuz" : pb > 6 ? "Defter değerine göre pahalı" : "Defter değeri makul"));
    if (isNum(ps)) valSubs.push(line("FD/Satış (P/S)", fx(ps), score(ps, "ps"),
      ps < 2 ? "Satışlara göre ucuz" : ps > 10 ? "Satışlara göre pahalı" : "Satış çarpanı makul"));
    dims.push(makeDim("Değerleme", "valuation", valSubs, "Hisse pahalı mı ucuz mu?"));

    // 2) Kârlılık
    const roe = pick(m, ["roeTTM", "roeRfy"]);
    const roa = pick(m, ["roaTTM", "roaRfy"]);
    const netM = pick(m, ["netProfitMarginTTM", "netProfitMarginAnnual"]);
    const grossM = pick(m, ["grossMarginTTM", "grossMarginAnnual"]);
    const profSubs = [];
    if (isNum(roe)) profSubs.push(line("Özkaynak Kârlılığı (ROE)", pct(roe), score(roe, "roe"),
      roe >= 20 ? "Özkaynağı çok verimli kullanıyor" : roe < 5 ? "Özkaynak getirisi zayıf" : "Makul özkaynak getirisi"));
    if (isNum(roa)) profSubs.push(line("Aktif Kârlılığı (ROA)", pct(roa), score(roa, "roa"),
      roa >= 12 ? "Varlıklarından güçlü getiri üretiyor" : roa < 3 ? "Varlık getirisi düşük" : "Makul varlık getirisi"));
    if (isNum(netM)) profSubs.push(line("Net Kâr Marjı", pct(netM), score(netM, "netMargin"),
      netM >= 20 ? "Çok yüksek net marj" : netM < 3 ? "İnce kâr marjı — riskli" : "Sağlıklı net marj"));
    if (isNum(grossM)) profSubs.push(line("Brüt Marj", pct(grossM), score(grossM, "grossMargin"),
      grossM >= 50 ? "Güçlü fiyatlama gücü (yüksek brüt marj)" : "Brüt marj orta seviyede"));
    dims.push(makeDim("Kârlılık", "profit", profSubs, "Şirket ne kadar verimli para kazanıyor?"));

    // 3) Büyüme
    const revG = pick(m, ["revenueGrowthTTMYoy", "revenueGrowthQuarterlyYoy", "revenueGrowth5Y"]);
    const epsG = pick(m, ["epsGrowthTTMYoy", "epsGrowthQuarterlyYoy", "epsGrowth5Y"]);
    const rev5 = pick(m, ["revenueGrowth5Y", "revenueGrowth3Y"]);
    const grSubs = [];
    if (isNum(revG)) grSubs.push(line("Gelir Büyümesi (YoY)", pct(revG), score(revG, "revGrowth"),
      revG >= 20 ? "Gelirler hızla büyüyor" : revG < 0 ? "Gelirler daralıyor" : "Ilımlı gelir büyümesi"));
    if (isNum(epsG)) grSubs.push(line("Hisse Başı Kâr Büyümesi", pct(epsG), score(epsG, "epsGrowth"),
      epsG >= 20 ? "Kârlılık güçlü büyüyor" : epsG < 0 ? "Hisse başı kâr geriliyor" : "Ilımlı kâr büyümesi"));
    if (isNum(rev5)) grSubs.push(line("5 Yıllık Gelir Büyümesi", pct(rev5), score(rev5, "rev5y"),
      rev5 >= 15 ? "Uzun vadede istikrarlı yüksek büyüme" : "Uzun vadeli büyüme orta seviyede"));
    dims.push(makeDim("Büyüme", "growth", grSubs, "İş ne hızda büyüyor?"));

    // 4) Finansal Sağlık
    const cr = pick(m, ["currentRatioQuarterly", "currentRatioAnnual"]);
    const de = pick(m, ["totalDebt/totalEquityQuarterly", "totalDebt/totalEquityAnnual", "longTermDebt/equityQuarterly", "longTermDebt/equityAnnual"]);
    const qr = pick(m, ["quickRatioQuarterly", "quickRatioAnnual"]);
    const fhSubs = [];
    if (isNum(cr)) fhSubs.push(line("Cari Oran", fx(cr), score(cr, "currentRatio"),
      cr >= 2 ? "Kısa vadeli yükümlülükleri rahat karşılıyor" : cr < 1 ? "Kısa vadeli likidite baskısı olabilir" : "Likidite yeterli"));
    if (isNum(de)) fhSubs.push(line("Borç / Özkaynak", fx(de), score(de, "debtEquity"),
      de <= 0.5 ? "Düşük borç — güçlü bilanço" : de > 2 ? "Yüksek borç yükü — risk" : "Borç seviyesi yönetilebilir"));
    if (isNum(qr)) fhSubs.push(line("Likidite (Asit-Test)", fx(qr), score(qr, "quickRatio"),
      qr >= 1 ? "Stoksuz da nakit yükümlülüklerini karşılar" : "Likidite sınırlı"));
    dims.push(makeDim("Finansal Sağlık", "health", fhSubs, "Bilanço sağlam mı?"));

    // 5) Teknik / Momentum
    const hi = pick(m, ["52WeekHigh"]), lo = pick(m, ["52WeekLow"]);
    const ret52 = pick(m, ["52WeekPriceReturnDaily"]);
    const ret13 = pick(m, ["13WeekPriceReturnDaily"]);
    const beta = pick(m, ["beta"]);
    let rangePos = null;
    if (isNum(hi) && isNum(lo) && hi > lo) rangePos = ((q.c - lo) / (hi - lo)) * 100;
    const tSubs = [];
    if (isNum(ret52)) tSubs.push(line("52 Haftalık Getiri", pct(ret52), score(ret52, "ret52"),
      ret52 >= 25 ? "Güçlü yıllık yükseliş trendi" : ret52 < -5 ? "Yıllık bazda negatif — zayıf momentum" : "Yatay/ılımlı yıllık seyir"));
    if (isNum(ret13)) tSubs.push(line("3 Aylık Getiri", pct(ret13), score(ret13, "ret13"),
      ret13 >= 15 ? "Kısa vadede güçlü momentum" : ret13 < -5 ? "Kısa vadede satış baskısı" : "Kısa vadede yatay"));
    if (isNum(rangePos)) tSubs.push(line("52H Bandındaki Konum", rangePos.toFixed(0) + "%", score(rangePos, "rangePos"),
      rangePos >= 80 ? "Zirveye yakın — güçlü ama 'ucuz' değil" : rangePos <= 20 ? "Dip bölgesinde — ucuz olabilir ya da zayıflık işareti" : "Bandın orta bölgesinde"));
    if (isNum(beta)) tSubs.push(line("Beta (Oynaklık)", num(beta, 2), null,
      beta > 1.3 ? "Piyasadan daha oynak — yüksek risk/ödül" : beta < 0.8 ? "Piyasadan daha sakin — savunmacı" : "Piyasayla benzer oynaklık", true));
    dims.push(makeDim("Teknik / Momentum", "technical", tSubs, "Fiyat trendi ne yönde?"));

    // 6) Analist Görüşü
    const anSubs = [];
    let anScore = null, recDist = null;
    if (rec && rec.length) {
      const r = rec[0]; recDist = r;
      const total = (r.strongBuy + r.buy + r.hold + r.sell + r.strongSell) || 0;
      if (total > 0) {
        anScore = Math.round((r.strongBuy * 100 + r.buy * 75 + r.hold * 50 + r.sell * 25 + r.strongSell * 0) / total);
        const buyPct = Math.round((r.strongBuy + r.buy) / total * 100);
        anSubs.push(line("Analist Konsensüsü", buyPct + "% AL yönlü", anScore,
          buyPct >= 70 ? "Analistlerin çoğu alım öneriyor" : buyPct <= 30 ? "Analistler temkinli/satış yönlü" : "Analist görüşleri karışık"));
      }
    }
    dims.push({ name: "Analist Görüşü", weight: CONFIG.WEIGHTS.analyst, subs: anSubs, score: anScore, q: "Profesyoneller ne diyor?" });

    // Genel skor (mevcut boyutların ağırlıklı ortalaması)
    let wSum = 0, sSum = 0;
    dims.forEach((d) => { if (d.score != null) { wSum += d.weight; sSum += d.score * d.weight; } });
    const overall = wSum > 0 ? Math.round(sSum / wSum) : null;

    // Güçlü / zayıf yönler
    const pros = [], cons = [];
    dims.forEach((d) => d.subs.forEach((s) => {
      if (s.note === true || s.score == null) return;
      if (s.score >= 74) pros.push(s.msg);
      else if (s.score <= 38) cons.push(s.msg);
    }));

    const verdict = verdictOf(overall);
    const summary = buildSummary(verdict, pros, cons, overall);

    return {
      overall, verdict, summary, dims, pros, cons, rangePos, hi, lo, recDist, anScore,
      returns: {
        d5: pick(m, ["5DayPriceReturnDaily"]),
        m1: pick(m, ["monthToDatePriceReturnDaily", "26WeekPriceReturnDaily"]),
        m3: ret13,
        ytd: pick(m, ["yearToDatePriceReturnDaily"]),
        y1: ret52,
      },
    };
  }

  // Dışarıya açık API
  return { analyze, verdictOf, pick, isNum };
})();
