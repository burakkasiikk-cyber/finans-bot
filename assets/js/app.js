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

  // Orijinal index'i sakla (detay için)
  const indexed = stocks.map((s, i) => ({ ...s, _origIndex: i }));

  function applyFilter(q) {
    const tbody = document.getElementById("scannerTbody");
    if (!tbody) return;
    const filtered = q
      ? indexed.filter(s => s.symbol.includes(q.toUpperCase()) || (s.name || "").toUpperCase().includes(q.toUpperCase()))
      : indexed;
    tbody.innerHTML = _renderRows(filtered) || `<tr><td colspan="7" style="text-align:center;color:var(--muted);padding:20px">Sonuç bulunamadı.</td></tr>`;
  }

  el.innerHTML = `
    <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:12px">
      <h2 class="section-title" style="margin:0">📊 Fırsat Tarayıcı</h2>
      <input id="scannerFilter" type="text" placeholder="🔍 Hisse filtrele (ör: EKDMR, THYAO…)"
        style="background:var(--panel-2);border:1px solid var(--border);color:var(--text);
               padding:7px 12px;border-radius:9px;font-size:13px;width:240px;outline:none" />
    </div>
    <table class="portfolio-table" style="min-width:500px">
      <thead><tr>
        <th>#</th><th>Hisse</th><th>Skor</th><th>Karar</th>
        <th style="min-width:60px">Boyutlar</th><th>Risk</th><th>Günlük</th>
      </tr></thead>
      <tbody id="scannerTbody">${_renderRows(indexed)}</tbody>
    </table>
    <div id="stockDetail"></div>`;

  document.getElementById("scannerFilter").addEventListener("input", e => applyFilter(e.target.value.trim()));
}

function _showStockDetail(stock) {
  const el = document.getElementById("stockDetail");
  if (!el || !stock || stock.error) return;
  const dims = stock.dimensions || {};
  const dimNames = { valuation:"Değerleme", profit:"Kârlılık", growth:"Büyüme", health:"Finansal Sağlık", technical:"Teknik/Momentum", analyst:"Analist Görüşü" };
  const vColor = _verdictColor(stock.verdict_key);

  const dimRows = Object.entries(dims).map(([key, dim]) => {
    const sc = dim.score;
    const color = sc == null ? "var(--muted)" : sc >= 70 ? "var(--green)" : sc >= 45 ? "var(--yellow)" : "var(--red)";
    return `<div style="margin-bottom:10px">
      <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:3px">
        <span>${dimNames[key] || key}</span>
        <span style="color:${color};font-weight:700">${sc ?? "Veri yok"}</span>
      </div>
      <div style="height:5px;background:var(--border);border-radius:3px">
        <div style="height:100%;width:${sc ?? 0}%;background:${color};border-radius:3px"></div>
      </div>
    </div>`;
  }).join("");

  const prosHtml = (stock.pros || []).map(p => `<li>${_esc(p)}</li>`).join("") || "<li style='color:var(--muted)'>—</li>";
  const consHtml = (stock.cons || []).map(c => `<li>${_esc(c)}</li>`).join("") || "<li style='color:var(--muted)'>—</li>";

  el.innerHTML = `
    <div class="card" style="margin-top:16px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="margin:0">${_esc(stock.symbol)} — ${_esc(stock.name)}</h2>
        <span style="color:${vColor};font-weight:700;font-size:18px">${stock.score ?? "—"}/100 · ${_esc(stock.verdict)}</span>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
        <div>${dimRows}</div>
        <div>
          <div style="margin-bottom:12px">
            <div style="font-size:11px;color:var(--muted);text-transform:uppercase;margin-bottom:6px">✅ Güçlü Yönler</div>
            <ul style="padding-left:16px;margin:0;font-size:12px">${prosHtml}</ul>
          </div>
          <div>
            <div style="font-size:11px;color:var(--muted);text-transform:uppercase;margin-bottom:6px">⚠️ Zayıf Yönler</div>
            <ul style="padding-left:16px;margin:0;font-size:12px">${consHtml}</ul>
          </div>
        </div>
      </div>
    </div>`;
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
