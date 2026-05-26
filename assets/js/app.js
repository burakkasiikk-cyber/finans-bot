/* ============================================================
   Dashboard — report.json'dan beslenen otomatik görünüm
   ============================================================ */
let _reportData = null;
let _activeTab  = "scanner";

function _esc(s) {
  return String(s ?? "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

async function loadReport() {
  try {
    const r = await fetch(CONFIG.REPORT_URL + "?t=" + Date.now());
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
}

function _verdictColor(verdictKey) {
  const map = { strong_buy: "var(--green)", buy: "var(--green-d)", hold: "var(--yellow)", sell: "var(--orange)", strong_sell: "var(--red)" };
  return map[verdictKey] || "var(--muted)";
}

function _riskBadge(risk) {
  if (risk === "low")    return `<span style="color:var(--green);font-size:10px">● DÜŞÜK</span>`;
  if (risk === "high")   return `<span style="color:var(--red);font-size:10px">● YÜKSEK</span>`;
  return `<span style="color:var(--yellow);font-size:10px">● ORTA</span>`;
}

function _dimBars(dimensions) {
  if (!dimensions) return "";
  const order = ["valuation","profit","growth","health","technical","analyst"];
  return order.map(key => {
    const sc = dimensions[key]?.score;
    if (sc == null) return `<div style="width:8px;height:22px;border-radius:2px;background:var(--border)" title="${key}"></div>`;
    const color = sc >= 70 ? "var(--green)" : sc >= 45 ? "var(--yellow)" : "var(--red)";
    return `<div style="width:8px;height:${Math.max(4, Math.round(sc * 0.22))}px;border-radius:2px;background:${color};align-self:flex-end" title="${key}: ${sc}"></div>`;
  }).join("");
}

function _renderRows(stocks) {
  return stocks.map((s, i) => {
    if (s.error) {
      return `<tr><td>${i+1}</td><td><strong>${_esc(s.symbol)}</strong></td><td colspan="6" style="color:var(--muted);font-size:11px">Veri alınamadı</td></tr>`;
    }
    const chg = s.change_pct;
    const chgStr = chg != null ? `${chg >= 0 ? "+" : ""}${chg.toFixed(1)}%` : "—";
    const chgColor = chg != null ? (chg >= 0 ? "var(--green)" : "var(--red)") : "var(--muted)";
    const vColor = _verdictColor(s.verdict_key);
    return `<tr style="cursor:pointer" onclick="App.showDetail(${s._origIndex})">
      <td style="color:var(--muted)">${i+1}</td>
      <td><strong>${_esc(s.symbol)}</strong><br><span style="font-size:10px;color:var(--muted)">${_esc(s.exchange)}</span></td>
      <td><span style="font-size:18px;font-weight:700;color:${vColor}">${s.score ?? "—"}</span><span style="font-size:10px;color:var(--muted)">/100</span></td>
      <td><span style="color:${vColor};font-weight:600;font-size:11px">${_esc(s.verdict)}</span></td>
      <td><div style="display:flex;gap:2px;align-items:flex-end;height:26px">${_dimBars(s.dimensions)}</div></td>
      <td>${_riskBadge(s.risk)}</td>
      <td style="color:${chgColor};font-weight:600">${chgStr}</td>
    </tr>`;
  }).join("");
}

function renderReportStocks(stocks) {
  const el = document.getElementById("reportDashboard");
  if (!el) return;
  if (!stocks || !stocks.length) {
    el.innerHTML = `<div class="placeholder"><div>Henüz analiz verisi yok. GitHub Actions sabah 09:00'da çalışacak.</div></div>`;
    return;
  }

  const indexed = stocks.map((s, i) => ({ ...s, _origIndex: i }));
  const bist    = indexed.filter(s => s.exchange === "BIST");
  const us      = indexed.filter(s => s.exchange !== "BIST");

  const thead = `<thead><tr>
    <th>#</th><th>Hisse</th><th>Skor</th><th>Karar</th>
    <th style="min-width:60px">Boyutlar</th><th>Risk</th><th>Günlük</th>
  </tr></thead>`;

  const sectionHtml = (id, list) => `
    <table class="portfolio-table" style="min-width:500px">
      ${thead}
      <tbody id="${id}">${_renderRows(list)}</tbody>
    </table>`;

  el.innerHTML = `
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:16px;flex-wrap:wrap">
      <h2 class="section-title" style="margin:0;flex:1">📊 Fırsat Tarayıcı</h2>
      <div style="display:flex;align-items:center;gap:6px;background:var(--panel-2);
                  border:1px solid var(--border);border-radius:20px;padding:6px 14px;flex-shrink:0">
        <span style="color:var(--muted);font-size:12px">🔍</span>
        <input id="scannerFilter" type="text" placeholder="Filtrele…"
          style="background:transparent;border:none;color:var(--text);font-size:13px;width:130px;outline:none" />
      </div>
    </div>

    <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
      <span style="font-size:13px;font-weight:700">🇺🇸 ABD</span>
      <span style="font-size:11px;color:var(--muted)">${us.filter(s=>!s.error).length} hisse</span>
    </div>
    ${sectionHtml("usTableBody", us)}

    <div style="display:flex;align-items:center;gap:8px;margin:24px 0 12px">
      <span style="font-size:13px;font-weight:700">🇹🇷 BIST</span>
      <span style="font-size:11px;color:var(--muted)">${bist.filter(s=>!s.error).length} hisse</span>
    </div>
    ${sectionHtml("bistTableBody", bist)}

    <div id="stockDetail"></div>`;

  document.getElementById("scannerFilter").addEventListener("input", function() {
    const q = this.value.trim().toUpperCase();
    const empty = `<tr><td colspan="7" style="text-align:center;color:var(--muted);padding:16px">Sonuç bulunamadı.</td></tr>`;
    const filter = list => list.filter(s => !q || s.symbol.includes(q) || (s.name||"").toUpperCase().includes(q));
    document.getElementById("usTableBody").innerHTML   = _renderRows(filter(us))   || empty;
    document.getElementById("bistTableBody").innerHTML = _renderRows(filter(bist)) || empty;
  });
}

function _autoProscons(dims) {
  const pros = [], cons = [];
  const m = {};
  for (const [k, d] of Object.entries(dims)) { Object.assign(m, d.metrics || {}); }

  const pe = m.pe, pb = m.pb, roe = m.roe, revG = m.rev_growth;
  const cr = m.current_ratio, de = m.debt_equity, r52 = m.ret52, rp = m.range_pos;

  if (pe != null && pe > 0 && pe < 12)  pros.push(`Düşük F/K oranı (${pe.toFixed(1)}×) — değerleme cazip`);
  if (pe != null && pe > 35)             cons.push(`Yüksek F/K oranı (${pe.toFixed(1)}×) — pahalı fiyatlanmış olabilir`);
  if (pb != null && pb < 1.5)            pros.push(`Düşük PD/DD (${pb.toFixed(2)}×) — defter değerinin altında`);
  if (pb != null && pb > 6)              cons.push(`Yüksek PD/DD (${pb.toFixed(2)}×)`);
  if (roe != null && roe > 15)           pros.push(`Güçlü özkaynak kârlılığı (ROE: %${roe.toFixed(1)})`);
  if (roe != null && roe < 5)            cons.push(`Düşük özkaynak kârlılığı (ROE: %${roe != null ? roe.toFixed(1) : "—"})`);
  if (revG != null && revG > 15)         pros.push(`Güçlü gelir büyümesi (%${revG.toFixed(1)} YoY)`);
  if (revG != null && revG < -5)         cons.push(`Gelir daralması (%${revG.toFixed(1)} YoY)`);
  if (cr != null && cr > 1.8)            pros.push(`Sağlıklı cari oran (${cr.toFixed(2)}×)`);
  if (cr != null && cr < 1)              cons.push(`Düşük cari oran (${cr.toFixed(2)}×) — likidite riski`);
  if (de != null && de < 0.5)            pros.push(`Düşük borçluluk (Borç/Özkaynak: ${de.toFixed(2)}×)`);
  if (de != null && de > 2)              cons.push(`Yüksek borç yükü (Borç/Özkaynak: ${de.toFixed(2)}×)`);
  if (r52 != null && r52 > 20)           pros.push(`Güçlü 52 haftalık getiri (%${r52.toFixed(1)})`);
  if (r52 != null && r52 < -20)          cons.push(`Zayıf 52 haftalık performans (%${r52.toFixed(1)})`);
  if (rp != null && rp > 75)             pros.push(`52 hafta zirvesine yakın (konum: %${rp.toFixed(0)})`);
  if (rp != null && rp < 25)             cons.push(`52 hafta tabanına yakın (konum: %${rp.toFixed(0)})`);

  return { pros, cons };
}

function _showStockDetail(stock) {
  if (!stock || stock.error) return;
  const content = document.getElementById("content");
  if (!content) return;

  const dims    = stock.dimensions || {};
  const vColor  = _verdictColor(stock.verdict_key);
  const score   = stock.score ?? null;
  const ringDeg = score != null ? score * 3.6 : 0;

  const dimNames = { valuation:"Değerleme", profit:"Kârlılık", growth:"Büyüme", health:"Finansal Sağlık", technical:"Teknik/Momentum", analyst:"Analist Görüşü" };
  const dimWeights = { valuation:"20%", profit:"20%", growth:"20%", health:"15%", technical:"15%", analyst:"10%" };

  const dimBars = Object.entries(dims).map(([key, dim]) => {
    const sc  = dim.score;
    const col = sc == null ? "var(--muted)" : sc >= 70 ? "var(--green)" : sc >= 45 ? "var(--yellow)" : "var(--red)";
    return `<div class="dim">
      <div class="dim-top">
        <div class="dim-name">${dimNames[key] || key}<span class="w">ağırlık ${dimWeights[key] || ""}</span></div>
        <div class="dim-score" style="color:${col}">${sc ?? "—"}</div>
      </div>
      <div class="track"><div class="fill" style="width:${sc ?? 0}%;background:${col}"></div></div>
    </div>`;
  }).join("");

  // Metrik tablosu — dims içinden topla
  const m = {};
  for (const [, d] of Object.entries(dims)) Object.assign(m, d.metrics || {});
  const fmtPct = v => (v != null ? (v >= 0 ? "+" : "") + v.toFixed(1) + "%" : "—");
  const fmtFx  = v => (v != null ? v.toFixed(2) + "×" : "—");
  const metrics = [
    ["F/K (TTM)",        fmtFx(m.pe)],
    ["PD/DD",            fmtFx(m.pb)],
    ["ROE",              fmtPct(m.roe)],
    ["Gelir Büyümesi",   fmtPct(m.rev_growth)],
    ["Cari Oran",        fmtFx(m.current_ratio)],
    ["Borç/Özkaynak",    fmtFx(m.debt_equity)],
    ["52H Getiri",       fmtPct(m.ret52)],
    ["52H Bant Konum",   m.range_pos != null ? "%" + m.range_pos.toFixed(0) : "—"],
  ].map(([l, v]) => `<div class="metric"><div class="label">${l}</div><div class="val">${v}</div></div>`).join("");

  const { pros, cons } = _autoProscons(dims);
  const prosHtml = pros.length ? pros.map(p => `<div class="pc-item pro"><div class="ic">+</div><div>${p}</div></div>`).join("") : `<div class="pc-empty">Öne çıkan güçlü yön tespit edilmedi.</div>`;
  const consHtml = cons.length ? cons.map(c => `<div class="pc-item con"><div class="ic">!</div><div>${c}</div></div>`).join("") : `<div class="pc-empty">Belirgin risk öne çıkmıyor.</div>`;

  const chg = stock.change_pct;
  const up  = (chg ?? 0) >= 0;
  const chgStr = chg != null ? `${up ? "▲" : "▼"} ${Math.abs(chg).toFixed(2)}%` : "";

  content.style.display = "";
  content.innerHTML = `
    <div class="card">
      <div style="display:flex;align-items:center;gap:6px;font-size:12px;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--border)">
        <span onclick="App.goHome()" style="color:var(--accent);cursor:pointer"
              onmouseover="this.style.opacity='.7'" onmouseout="this.style.opacity='1'">📊 Tarayıcı</span>
        <span style="color:var(--muted)">›</span>
        <span style="color:var(--text);font-weight:600">${_esc(stock.symbol)}</span>
      </div>
    <div class="verdict">
      <div class="ring" style="background:conic-gradient(${vColor} ${ringDeg}deg, var(--border) 0deg)">
        <div class="inner">
          <div class="score-num" style="color:${vColor}">${score ?? "—"}</div>
          <div class="score-100">/ 100</div>
        </div>
      </div>
      <div>
        <div class="head">
          <div class="ph">${stock.symbol[0]}</div>
          <div>
            <div class="name">${_esc(stock.name || stock.symbol)}</div>
            <div class="sub">${_esc(stock.symbol)} · BIST · Borsa İstanbul</div>
          </div>
        </div>
        <div class="badge" style="background:${vColor}22;color:${vColor}">${_esc(stock.verdict)}</div>
        <div style="margin:6px 0 10px">
          <span class="price">${stock.price != null ? stock.price.toFixed(2) + " ₺" : "—"}</span>
          ${chg != null ? `<span class="chg ${up ? "up" : "down"}">${chgStr}</span>` : ""}
        </div>
        <div class="summary">Genel skor ${score ?? "—"}/100 → <strong style="color:${vColor}">${_esc(stock.verdict)}</strong>. ${_riskBadge(stock.risk)} risk seviyesi.</div>
      </div>
    </div></div></div>

    <div class="card"><h2>Boyut Bazlı Skorlama</h2>${dimBars}</div>

    <div class="grid2">
      <div class="card"><h2>✅ Güçlü Yönler</h2><div class="pc-list">${prosHtml}</div></div>
      <div class="card"><h2>⚠️ Zayıf Yönler / Riskler</h2><div class="pc-list">${consHtml}</div></div>
    </div>

    <div class="card"><h2>Temel Veriler</h2><div class="metrics">${metrics}</div></div>

    <div class="disclaimer">⚠️ Bu skor; halka açık temel ve teknik verilerden otomatik, kural tabanlı bir hesaplamadır. Yatırım tavsiyesi değildir.</div>`;
}

async function initDashboard() {
  const report = await loadReport();
  _reportData = report;
  if (report) {
    MacroStrip.renderMacro(report.macro);
    document.getElementById("reportDashboard").style.display = "";
    document.querySelector(".placeholder")?.remove();
    renderReportStocks(report.stocks);
  }
}

function switchTab(tab, btn) {
  _activeTab = tab;
  document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  if (btn) btn.classList.add("active");

  // Tüm sekme bölümlerini ve ana content'i gizle
  ["portfolioSection","alarmsSection","dividendSection"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = "none";
  });
  const contentEl = document.getElementById("content");

  const stocks = _reportData?.stocks || [];
  try {
    if (tab === "scanner") {
      // Tarayıcı: content'i göster, reportDashboard'u yeniden çiz
      if (contentEl) contentEl.style.display = "";
      // Arama sonrası reportDashboard silinmiş olabilir — yoksa yeniden oluştur
      let rd = document.getElementById("reportDashboard");
      if (!rd && contentEl) {
        contentEl.innerHTML = `<div id="reportDashboard"></div>`;
        rd = document.getElementById("reportDashboard");
      }
      if (rd) { rd.style.display = ""; renderReportStocks(stocks); }
    } else {
      // Diğer sekmeler: arama/analiz içeriğini gizle
      if (contentEl) contentEl.style.display = "none";
      if (tab === "portfolio") {
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
  } catch (e) {
    console.error("Tab render error:", e);
  }
}

function refresh() {
  const stocks = _reportData?.stocks || [];
  try {
    if (_activeTab === "portfolio") Portfolio.renderPortfolio(stocks, _reportData?.macro);
    else if (_activeTab === "alarms") Alarms.render(stocks);
    else if (_activeTab === "dividends") Dividends.render(stocks);
  } catch (e) {
    console.error("Refresh error:", e);
  }
}

function goHome() {
  // Aramayı temizle
  const si = document.getElementById("searchInput");
  if (si) si.value = "";
  try { UI.hideSuggestions(); } catch {}
  // Scanner tab'a geç (reportDashboard da yeniden oluşturulur)
  const scannerBtn = document.querySelector('.tab');
  switchTab("scanner", scannerBtn);
}

const App = {
  switchTab,
  refresh,
  goHome,
  showDetail: (index) => {
    const stocks = _reportData?.stocks || [];
    _showStockDetail(stocks[index]);
  }
};

document.addEventListener("DOMContentLoaded", initDashboard);

/* ============================================================
   app.js — Orkestrasyon
   Olayları bağlar; API -> Analyzer -> UI akışını yönetir.
   ============================================================ */
(() => {
  const keyInput = document.getElementById("apiKey");
  const saveBtn = document.getElementById("saveKey");
  const searchInput = document.getElementById("searchInput");
  const chips = document.getElementById("chips");

  // --- API anahtarı ---
  if (FinnhubAPI.hasKey()) { keyInput.value = FinnhubAPI.key; markSaved(); }
  function markSaved() { saveBtn.textContent = "✓ Kayıtlı"; saveBtn.classList.add("key-ok"); }
  saveBtn.addEventListener("click", () => { if (FinnhubAPI.setKey(keyInput.value)) markSaved(); });

  // --- Hızlı erişim çipleri ---
  CONFIG.POPULAR.forEach((sym) => {
    const c = document.createElement("div");
    c.className = "chip"; c.textContent = sym;
    c.onclick = () => loadSymbol(sym);
    chips.appendChild(c);
  });

  // --- Arama (debounce'lu öneri) ---
  let timer;
  searchInput.addEventListener("input", () => {
    const q = searchInput.value.trim();
    clearTimeout(timer);
    if (!q) { UI.hideSuggestions(); return; }
    timer = setTimeout(() => doSearch(q), 280);
  });
  searchInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      const q = searchInput.value.trim().toUpperCase();
      if (q) { UI.hideSuggestions(); loadSymbol(q); }
    }
  });
  document.addEventListener("click", (e) => { if (!e.target.closest(".search")) UI.hideSuggestions(); });

  async function doSearch(q) {
    if (!FinnhubAPI.hasKey()) { UI.renderError("NO_KEY"); return; }
    try {
      const data = await FinnhubAPI.search(q);
      const items = (data.result || []).filter((r) => r.type === "Common Stock" || r.type === "").slice(0, 8);
      UI.renderSuggestions(items, (sym) => {
        searchInput.value = sym; UI.hideSuggestions(); loadSymbol(sym);
      });
    } catch (e) { /* yazmaya devam edilebilir, sessiz geç */ }
  }

  // --- Ana akış: bir sembolü yükle, analiz et, çiz ---
  async function loadSymbol(symbol) {
    symbol = symbol.toUpperCase();
    if (!FinnhubAPI.hasKey()) { UI.renderError("NO_KEY"); return; }
    UI.loading(symbol);
    try {
      const [quote, profile, metricRes, rec] = await Promise.all([
        FinnhubAPI.quote(symbol),
        FinnhubAPI.profile(symbol).catch(() => ({})),
        FinnhubAPI.metrics(symbol).catch(() => ({})),
        FinnhubAPI.recommendation(symbol).catch(() => []),
      ]);
      if (!quote || (quote.c === 0 && quote.pc === 0 && quote.h === 0)) { UI.renderError("NOT_FOUND", symbol); return; }

      const m = metricRes?.metric || {};
      const analysis = Analyzer.analyze(m, quote, rec);
      UI.renderAnalysis(symbol, quote, profile, m, rec, analysis);

      // Haberler arka planda yüklenir
      FinnhubAPI.companyNews(symbol)
        .then((news) => UI.renderNews((news || []).filter((n) => n.headline).slice(0, 6)))
        .catch(() => UI.newsError());
    } catch (e) {
      UI.renderError(e.message, symbol);
    }
  }

  // URL'de ?symbol=AAPL varsa otomatik aç (paylaşılabilir link)
  const params = new URLSearchParams(location.search);
  const initial = params.get("symbol");
  if (initial && FinnhubAPI.hasKey()) loadSymbol(initial);
})();
