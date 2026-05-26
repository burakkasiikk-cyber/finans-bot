/* ============================================================
   ui.js — Görselleştirme katmanı
   Analiz sonucunu HTML'e çevirir. Biçimlendirme yardımcıları
   (num/pct/fx/cap) global olarak burada tanımlanır.
   ============================================================ */

// --- Biçimlendirme yardımcıları (analysis.js de bunları kullanır) ---
const isNum = (v) => v !== undefined && v !== null && !isNaN(v) && v !== "";
function num(v, d = 2) { return isNum(v) ? Number(v).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d }) : "—"; }
function pct(v) { return isNum(v) ? (v > 0 ? "+" : "") + Number(v).toFixed(1) + "%" : "—"; }
function fx(v) { return isNum(v) ? Number(v).toFixed(2) + "×" : "—"; }
function cap(n) { if (!isNum(n)) return "—"; if (n >= 1e6) return (n / 1e6).toFixed(2) + " T"; if (n >= 1e3) return (n / 1e3).toFixed(2) + " B"; return n.toFixed(0) + " M"; }

const UI = (() => {
  const content = document.getElementById("content");
  const suggestions = document.getElementById("suggestions");

  function loading(symbol) {
    content.innerHTML = `<div class="loading"><div class="spinner"></div>${symbol} analiz ediliyor…</div>`;
  }

  function placeholderTag(sc) {
    if (sc == null) return "";
    if (sc >= 74) return ` <small class="tag-good">iyi</small>`;
    if (sc >= 45) return ` <small class="tag-mid">orta</small>`;
    return ` <small class="tag-bad">zayıf</small>`;
  }

  function metricsGrid(m, p, cur) {
    const get = (keys) => Analyzer.pick(m, keys);
    const rows = [
      ["F/K (TTM)", fx(get(["peTTM", "peBasicExclExtraTTM", "peExclExtraTTM"])), scoreFor(get(["peTTM", "peBasicExclExtraTTM"]), "pe")],
      ["PD/DD", fx(get(["pbQuarterly", "pbAnnual"])), scoreFor(get(["pbQuarterly", "pbAnnual"]), "pb")],
      ["P/S", fx(get(["psTTM", "psAnnual"])), scoreFor(get(["psTTM"]), "ps")],
      ["ROE", pct(get(["roeTTM", "roeRfy"])), scoreFor(get(["roeTTM", "roeRfy"]), "roe")],
      ["Net Marj", pct(get(["netProfitMarginTTM", "netProfitMarginAnnual"])), scoreFor(get(["netProfitMarginTTM", "netProfitMarginAnnual"]), "netMargin")],
      ["Brüt Marj", pct(get(["grossMarginTTM", "grossMarginAnnual"])), scoreFor(get(["grossMarginTTM"]), "grossMargin")],
      ["Gelir Büyümesi", pct(get(["revenueGrowthTTMYoy", "revenueGrowthQuarterlyYoy"])), scoreFor(get(["revenueGrowthTTMYoy"]), "revGrowth")],
      ["Borç/Özkaynak", fx(get(["totalDebt/totalEquityQuarterly", "totalDebt/totalEquityAnnual"])), scoreFor(get(["totalDebt/totalEquityQuarterly", "totalDebt/totalEquityAnnual"]), "debtEquity")],
      ["Cari Oran", fx(get(["currentRatioQuarterly", "currentRatioAnnual"])), scoreFor(get(["currentRatioQuarterly"]), "currentRatio")],
      ["Temettü Verimi", pct(get(["currentDividendYieldTTM", "dividendYieldIndicatedAnnual"])), null],
      ["Beta", num(get(["beta"]), 2), null],
      ["Piyasa Değeri", cap(p.marketCapitalization) + " " + cur, null],
    ];
    return rows.map(([l, v, sc]) => `<div class="metric"><div class="label">${l}</div><div class="val">${v}${placeholderTag(sc)}</div></div>`).join("");
  }

  // metricsGrid için eşik bazlı skoru yeniden hesaplar (etiket için)
  function scoreFor(v, key) {
    if (!isNum(v)) return null;
    const cfg = CONFIG.THRESHOLDS[key]; if (!cfg) return null;
    const [a, b, c, d] = cfg.t;
    if (cfg.dir === "up") return v >= a ? 92 : v >= b ? 74 : v >= c ? 55 : v >= d ? 38 : 18;
    return v <= a ? 92 : v <= b ? 74 : v <= c ? 55 : v <= d ? 38 : 18;
  }

  function recCard(rec) {
    if (!rec || !rec.length) return `<div class="card"><h2>Analist Tavsiyeleri</h2><div class="pc-empty">Veri bulunamadı (ücretsiz planda sınırlı olabilir).</div></div>`;
    const r = rec[0], total = (r.strongBuy + r.buy + r.hold + r.sell + r.strongSell) || 1;
    const seg = (v, c, l) => v > 0 ? `<div class="rec-seg" style="width:${v / total * 100}%;background:${c}" title="${l}: ${v}">${v / total > 0.08 ? v : ""}</div>` : "";
    return `<div class="card"><h2>Analist Tavsiyeleri · ${r.period || ""}</h2>
      <div class="rec-bar">${seg(r.strongBuy, "#1f9d57", "Güçlü Al")}${seg(r.buy, "#2ecc71", "Al")}${seg(r.hold, "#f5b942", "Tut")}${seg(r.sell, "#ff8a5c", "Sat")}${seg(r.strongSell, "#ff5c6c", "Güçlü Sat")}</div>
      <div class="rec-legend"><span><i style="background:#1f9d57"></i>Güçlü Al ${r.strongBuy}</span><span><i style="background:#2ecc71"></i>Al ${r.buy}</span><span><i style="background:#f5b942"></i>Tut ${r.hold}</span><span><i style="background:#ff8a5c"></i>Sat ${r.sell}</span><span><i style="background:#ff5c6c"></i>Güçlü Sat ${r.strongSell}</span></div>
    </div>`;
  }

  /** Tam analiz ekranını çizer. */
  function renderAnalysis(symbol, q, p, m, rec, a) {
    const up = (q.d ?? 0) >= 0;
    const logo = p.logo
      ? `<img class="logo" src="${p.logo}" alt="" onerror="this.outerHTML='<div class=\\'ph\\'>${symbol[0]}</div>'" />`
      : `<div class="ph">${symbol[0]}</div>`;
    const ringDeg = a.overall != null ? a.overall * 3.6 : 0;
    const cur = p.currency || "USD";

    let html = `<div class="card"><div class="verdict">
      <div class="ring" style="background: conic-gradient(${a.verdict.color} ${ringDeg}deg, var(--border) 0deg)">
        <div class="inner"><div class="score-num" style="color:${a.verdict.color}">${a.overall ?? "—"}</div><div class="score-100">/ 100</div></div>
      </div>
      <div>
        <div class="head">${logo}
          <div><div class="name">${p.name || symbol}</div><div class="sub">${symbol} · ${p.exchange || "—"} · ${p.finnhubIndustry || ""}</div></div>
        </div>
        <div class="badge" style="background:${a.verdict.color}22;color:${a.verdict.color}">${a.verdict.label}</div>
        <div style="margin:6px 0 10px"><span class="price">${num(q.c)} ${cur}</span> <span class="chg ${up ? "up" : "down"}">${up ? "▲" : "▼"} ${num(q.d)} (${num(q.dp)}%)</span></div>
        <div class="summary">${a.summary}</div>
      </div>
    </div></div>`;

    // Boyut skorları
    html += `<div class="card"><h2>Boyut Bazlı Skorlama</h2>`;
    a.dims.forEach((d) => {
      const sc = d.score, col = sc == null ? "var(--muted)" : Analyzer.verdictOf(sc).color;
      html += `<div class="dim">
        <div class="dim-top"><div class="dim-name">${d.name}<span class="w">ağırlık ${Math.round(d.weight * 100)}% · ${d.q}</span></div>
          <div class="dim-score" style="color:${col}">${sc ?? "—"}</div></div>
        <div class="track"><div class="fill" style="width:${sc ?? 0}%;background:${col}"></div></div>
      </div>`;
    });
    html += `</div>`;

    // Güçlü / Zayıf
    html += `<div class="grid2">
      <div class="card"><h2>✅ Güçlü Yönler</h2><div class="pc-list">${
        a.pros.length ? a.pros.slice(0, 6).map((t) => `<div class="pc-item pro"><div class="ic">+</div><div>${t}</div></div>`).join("") : `<div class="pc-empty">Öne çıkan güçlü yön tespit edilmedi.</div>`
      }</div></div>
      <div class="card"><h2>⚠️ Zayıf Yönler / Riskler</h2><div class="pc-list">${
        a.cons.length ? a.cons.slice(0, 6).map((t) => `<div class="pc-item con"><div class="ic">!</div><div>${t}</div></div>`).join("") : `<div class="pc-empty">Belirgin bir risk öne çıkmıyor.</div>`
      }</div></div>
    </div>`;

    // Teknik: 52 hafta bandı + getiriler
    if (isNum(a.rangePos)) {
      const r = a.returns;
      const cell = (l, v) => `<div class="ret"><span class="rl">${l}</span><span class="rv" style="color:${isNum(v) ? (v >= 0 ? "var(--green)" : "var(--red)") : "var(--muted)"}">${pct(v)}</span></div>`;
      html += `<div class="card"><h2>Teknik Görünüm · 52 Hafta Bandı</h2>
        <div class="range-bar"><div class="range-marker" data-label="Şu an: ${num(q.c)}" style="left:${Math.min(98, Math.max(2, a.rangePos))}%"></div></div>
        <div class="range-ends"><span>Dip: ${num(a.lo)}</span><span>Zirve: ${num(a.hi)}</span></div>
        <div class="returns">${cell("5 Gün", r.d5)}${cell("Bu Ay", r.m1)}${cell("3 Ay", r.m3)}${cell("Yıl İçi", r.ytd)}${cell("1 Yıl", r.y1)}</div>
      </div>`;
    }

    // Temel veriler
    html += `<div class="card"><h2>Temel Veriler</h2><div class="metrics">${metricsGrid(m, p, cur)}</div></div>`;

    // Analist
    html += recCard(rec);

    // Haber yeri
    html += `<div class="card" id="newsCard"><h2>Son Haberler</h2><div class="loading"><div class="spinner"></div>Haberler yükleniyor…</div></div>`;

    // Uyarı
    html += `<div class="disclaimer">⚠️ Bu skor; halka açık temel ve teknik verilerden otomatik, kural tabanlı bir hesaplamadır. Geleceği garanti etmez, yatırım tavsiyesi değildir. Kendi araştırmanızı yapın.</div>`;

    content.innerHTML = html;
  }

  function renderNews(items) {
    const card = document.getElementById("newsCard");
    if (!card) return;
    if (!items || !items.length) { card.innerHTML = `<h2>Son Haberler</h2><div class="pc-empty">Bu hisse için son haber bulunamadı.</div>`; return; }
    card.innerHTML = `<h2>Son Haberler</h2>` + items.map((n) => `
      <a class="news-item" href="${n.url}" target="_blank" rel="noopener">
        ${n.image ? `<img src="${n.image}" alt="" onerror="this.style.display='none'"/>` : `<div style="width:78px;height:58px;border-radius:9px;background:var(--panel-2);flex-shrink:0;display:grid;place-items:center;color:var(--muted)">📰</div>`}
        <div><div class="news-title">${n.headline}</div><div class="news-meta">${n.source || ""} · ${new Date(n.datetime * 1000).toLocaleDateString("tr-TR")}</div></div>
      </a>`).join("");
  }

  function newsError() {
    const card = document.getElementById("newsCard");
    if (card) card.innerHTML = `<h2>Son Haberler</h2><div class="pc-empty">Haberler yüklenemedi.</div>`;
  }

  function renderSuggestions(items, onPick) {
    if (!items.length) { suggestions.classList.remove("show"); return; }
    suggestions.innerHTML = items.map((r) => `<div class="sug-item" data-sym="${r.symbol}"><span class="sym">${r.symbol}</span><span class="desc">${r.description || ""}</span></div>`).join("");
    suggestions.classList.add("show");
    suggestions.querySelectorAll(".sug-item").forEach((it) => { it.onclick = () => onPick(it.dataset.sym); });
  }
  function hideSuggestions() { suggestions.classList.remove("show"); }

  function renderError(code, symbol) {
    const msgs = {
      NO_KEY: `Önce sağ üstten Finnhub API anahtarınızı girin. Ücretsiz: <a href="https://finnhub.io/register" target="_blank" rel="noopener">finnhub.io/register</a>`,
      BAD_KEY: "API anahtarı geçersiz görünüyor. Kontrol edip tekrar kaydedin.",
      RATE: "Çok fazla istek (ücretsiz plan limiti). Birkaç saniye sonra tekrar deneyin.",
      NOT_FOUND: `<b>${symbol || ""}</b> için veri bulunamadı. Sembolü kontrol edin (örn: AAPL).`,
    };
    content.innerHTML = `<div class="${code === "NO_KEY" ? "placeholder" : "error"}"><div class="big">${code === "NO_KEY" ? "🔑" : "⚠️"}</div><div>${msgs[code] || "Hata: " + code}</div></div>`;
  }

  return { loading, renderAnalysis, renderNews, newsError, renderSuggestions, hideSuggestions, renderError };
})();
