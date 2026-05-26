/* ============================================================
   Dashboard — report.json'dan beslenen otomatik görünüm
   ============================================================ */
let _reportData     = null;
let _activeTab      = "scanner";
let _scannerRefresh = null; // watchlist/segment refresh için closure ref

const BIST_SECTORS = {
  "Bankacılık":   ["VAKBN","YKBNK","AKBNK","HALKB","TURSG","GARAN","ISCTR","SKBNK","ALBRK"],
  "Sigorta":      ["ANHYT","AKGRT"],
  "Holding":      ["AGHOL","NTHOL","SAHOL","KCHOL","DOHOL","TKFEN","ENKAI"],
  "Enerji":       ["TUPRS","ODAS","AKSEN","ZOREN","KONTR","PETKM","AYEN","EKDMR"],
  "Telecom/Tech": ["TTKOM","NETAS","TCELL","LOGO","ASELS"],
  "Perakende":    ["BIMAS","MAVI","SOKM","BIZIM"],
  "Gıda/İçecek":  ["CCOLA","ULKER","AEFES","GOLTS","GUBRF"],
  "Otomotiv":     ["TOASO","DOAS","FROTO","OTKAR","ARCLK","VESTL"],
  "İnşaat":       ["AKCNS","CIMSA","BSOKE","CEMTS"],
  "GYO":          ["ALGYO","ISGYO","AKFGY"],
  "Çelik/Metal":  ["EREGL","ISDMR","KRDMD","BRSAN","KARSN"],
  "Ulaşım":       ["THYAO","PGSUS","TAVHL","RYSAS"],
  "Sanayi/Diğer": ["INDES","KLNMA","ECZYT","SISE","ECILC","DEVA","HURGZ","GSRAY","FENER","TSPOR","BJKAS","REEDR","ALKIM","EGEEN"],
};

function _getSector(sym) {
  for (const [sec, list] of Object.entries(BIST_SECTORS)) if (list.includes(sym)) return sec;
  return null;
}

function _esc(s) {
  return String(s ?? "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

async function loadReport() {
  try {
    const r = await fetch(CONFIG.REPORT_URL + "?t=" + Date.now());
    if (!r.ok) return null;
    return await r.json();
  } catch { return null; }
}

function _verdictColor(verdictKey) {
  const map = { strong_buy:"var(--green)", buy:"var(--green-d)", hold:"var(--yellow)", sell:"var(--orange)", strong_sell:"var(--red)" };
  return map[verdictKey] || "var(--muted)";
}

function _riskBadge(risk) {
  if (risk === "low")  return `<span style="color:var(--green);font-size:10px">● DÜŞÜK</span>`;
  if (risk === "high") return `<span style="color:var(--red);font-size:10px">● YÜKSEK</span>`;
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
    const starred  = typeof Watchlist !== "undefined" && Watchlist.has(s.symbol);
    const starIcon = starred ? "⭐" : "☆";
    if (s.error) {
      return `<tr>
        <td style="color:var(--muted)">${i+1}</td>
        <td><strong>${_esc(s.symbol)}</strong><br><span style="font-size:10px;color:var(--muted)">${_esc(s.exchange)}</span></td>
        <td colspan="5" style="color:var(--muted);font-size:11px">Veri alınamadı</td>
        <td><button class="star-btn" onclick="event.stopPropagation();App.toggleWatch('${_esc(s.symbol)}',event)">${starIcon}</button></td>
      </tr>`;
    }
    const chg    = s.change_pct;
    const chgStr = chg != null ? `${chg >= 0 ? "+" : ""}${chg.toFixed(1)}%` : "—";
    const chgCol = chg != null ? (chg >= 0 ? "var(--green)" : "var(--red)") : "var(--muted)";
    const vColor = _verdictColor(s.verdict_key);
    const sector = s.exchange === "BIST" ? _getSector(s.symbol) : null;
    return `<tr style="cursor:pointer" onclick="App.showDetail(${s._origIndex})">
      <td style="color:var(--muted)">${i+1}</td>
      <td>
        <strong>${_esc(s.symbol)}</strong>
        <br><span style="font-size:10px;color:var(--muted)">${_esc(s.exchange)}${sector ? " · " + sector : ""}</span>
      </td>
      <td><span style="font-size:18px;font-weight:700;color:${vColor}">${s.score ?? "—"}</span><span style="font-size:10px;color:var(--muted)">/100</span></td>
      <td><span style="color:${vColor};font-weight:600;font-size:11px">${_esc(s.verdict)}</span></td>
      <td><div style="display:flex;gap:2px;align-items:flex-end;height:26px">${_dimBars(s.dimensions)}</div></td>
      <td>${_riskBadge(s.risk)}</td>
      <td style="color:${chgCol};font-weight:600">${chgStr}</td>
      <td><button class="star-btn" onclick="event.stopPropagation();App.toggleWatch('${_esc(s.symbol)}',event)">${starIcon}</button></td>
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

  const segStyle = (active) =>
    `background:${active ? "var(--accent)" : "var(--panel-2)"};` +
    `color:${active ? "#fff" : "var(--muted)"};` +
    `border:1px solid ${active ? "var(--accent)" : "var(--border)"};` +
    `padding:6px 13px;border-radius:20px;font-size:12px;font-weight:600;cursor:pointer;transition:.15s`;

  const sectorOpts = Object.keys(BIST_SECTORS).map(s => `<option value="${s}">${s}</option>`).join("");

  el.innerHTML = `
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;flex-wrap:wrap">
      <h2 class="section-title" style="margin:0;flex:1">📊 Fırsat Tarayıcı</h2>
      <div style="display:flex;gap:5px;flex-wrap:wrap" id="segBtns">
        <button data-seg="all"   style="${segStyle(true)}">Tümü</button>
        <button data-seg="us"    style="${segStyle(false)}">🇺🇸 ABD</button>
        <button data-seg="bist"  style="${segStyle(false)}">🇹🇷 BIST</button>
        <button data-seg="watch" style="${segStyle(false)}">⭐ İzleme</button>
      </div>
      <div style="display:flex;align-items:center;gap:6px;background:var(--panel-2);
                  border:1px solid var(--border);border-radius:20px;padding:6px 14px;flex-shrink:0">
        <span style="color:var(--muted);font-size:12px">🔍</span>
        <input id="scannerFilter" type="text" placeholder="Filtrele…"
          style="background:transparent;border:none;color:var(--text);font-size:13px;width:120px;outline:none" />
      </div>
    </div>
    <div id="sectorFilterRow" style="display:none;margin-bottom:10px">
      <select id="sectorSelect" style="background:var(--panel-2);border:1px solid var(--border);
              color:var(--text);border-radius:10px;padding:7px 14px;font-size:12px;cursor:pointer;outline:none">
        <option value="">🏭 Tüm Sektörler</option>
        ${sectorOpts}
      </select>
    </div>
    <table class="portfolio-table" style="min-width:500px">
      <thead><tr>
        <th>#</th><th>Hisse</th><th>Skor</th><th>Karar</th>
        <th style="min-width:60px">Boyutlar</th><th>Risk</th><th>Günlük</th><th></th>
      </tr></thead>
      <tbody id="scannerTbody">${_renderRows(indexed)}</tbody>
    </table>
    <div id="stockDetail"></div>`;

  let activeSeg = "all";

  function getBase() {
    if (activeSeg === "us")    return us;
    if (activeSeg === "bist")  return bist;
    if (activeSeg === "watch") {
      const wl = typeof Watchlist !== "undefined" ? Watchlist.getAll() : [];
      return indexed.filter(s => wl.includes(s.symbol));
    }
    return indexed;
  }

  function refresh() {
    const q      = (document.getElementById("scannerFilter")?.value || "").trim().toUpperCase();
    const sector = document.getElementById("sectorSelect")?.value || "";
    let   base   = getBase();
    if (sector) base = base.filter(s => _getSector(s.symbol) === sector);
    const list   = q ? base.filter(s => s.symbol.includes(q) || (s.name||"").toUpperCase().includes(q)) : base;
    const empty  = `<tr><td colspan="8" style="text-align:center;color:var(--muted);padding:20px">Sonuç bulunamadı.</td></tr>`;
    document.getElementById("scannerTbody").innerHTML = _renderRows(list) || empty;
  }

  _scannerRefresh = refresh;

  document.getElementById("segBtns").addEventListener("click", function(e) {
    const btn = e.target.closest("button[data-seg]");
    if (!btn) return;
    activeSeg = btn.dataset.seg;
    this.querySelectorAll("button").forEach(b => {
      const on = b.dataset.seg === activeSeg;
      b.style.background  = on ? "var(--accent)"  : "var(--panel-2)";
      b.style.color       = on ? "#fff"            : "var(--muted)";
      b.style.borderColor = on ? "var(--accent)"   : "var(--border)";
    });
    const sectorRow = document.getElementById("sectorFilterRow");
    if (sectorRow) sectorRow.style.display = activeSeg === "bist" ? "" : "none";
    if (activeSeg !== "bist") {
      const sel = document.getElementById("sectorSelect");
      if (sel) sel.value = "";
    }
    refresh();
  });

  document.getElementById("scannerFilter").addEventListener("input", refresh);
  document.getElementById("sectorSelect")?.addEventListener("change", refresh);
}

/* ---- TradingView widget ---- */
function loadTVWidget(symbol, exchange) {
  const id    = "tv_chart_widget";
  const tvSym = (exchange || "BIST") === "BIST" ? `BIST:${symbol}` : symbol;

  function createWidget() {
    if (!document.getElementById(id)) return;
    try {
      new TradingView.widget({
        container_id:        id,
        symbol:              tvSym,
        theme:               "dark",
        locale:              "tr",
        width:               "100%",
        height:              390,
        interval:            "D",
        hide_side_toolbar:   false,
        allow_symbol_change: false,
        save_image:          false,
        style:               "1",
      });
    } catch (e) {
      const el = document.getElementById(id);
      if (el) el.innerHTML = `<div style="color:var(--muted);text-align:center;padding:40px;font-size:13px">
        Grafik yüklenemedi.
        <a href="https://tr.tradingview.com/chart/?symbol=${encodeURIComponent(tvSym)}" target="_blank" style="color:var(--accent)">TradingView'da Aç →</a>
      </div>`;
    }
  }

  if (typeof TradingView !== "undefined") {
    createWidget();
  } else {
    let s = document.getElementById("tv_script");
    if (!s) {
      s = document.createElement("script");
      s.id  = "tv_script";
      s.src = "https://s3.tradingview.com/tv.js";
      s.onload = createWidget;
      document.head.appendChild(s);
    } else {
      const poll = setInterval(() => {
        if (typeof TradingView !== "undefined") { clearInterval(poll); createWidget(); }
      }, 300);
      setTimeout(() => clearInterval(poll), 8000);
    }
  }
}

/* ---- BIST Haber bölümü ---- */
function loadBISTNews(symbol) {
  const el = document.getElementById("bistNewsSection");
  if (!el) return;

  function showExternal() {
    el.innerHTML = `
      <p style="font-size:12px;color:var(--muted);margin-bottom:10px">Haber kaynakları:</p>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <a href="https://finance.yahoo.com/quote/${encodeURIComponent(symbol)}.IS/" target="_blank" rel="noopener" class="ext-link">📊 Yahoo Finance</a>
        <a href="https://tr.investing.com/search/?q=${encodeURIComponent(symbol)}" target="_blank" rel="noopener" class="ext-link">📈 Investing.com TR</a>
        <a href="https://www.google.com/finance/quote/${encodeURIComponent(symbol)}:BIST" target="_blank" rel="noopener" class="ext-link">🔍 Google Finans</a>
        <a href="https://www.isyatirim.com.tr/analiz-ve-raporlar/bist-sirket-haberleri?hisse=${encodeURIComponent(symbol)}" target="_blank" rel="noopener" class="ext-link">📰 İş Yatırım</a>
      </div>`;
  }

  if (typeof FinnhubAPI !== "undefined" && FinnhubAPI.hasKey()) {
    FinnhubAPI.companyNews(symbol)
      .then(news => {
        const items = (news || []).filter(n => n.headline).slice(0, 5);
        if (!items.length) { showExternal(); return; }
        el.innerHTML = items.map(n => `
          <a href="${_esc(n.url)}" target="_blank" rel="noopener" class="news-item">
            ${n.image ? `<img src="${_esc(n.image)}" alt="" onerror="this.style.display='none'">` : ""}
            <div>
              <div class="news-title">${_esc(n.headline)}</div>
              <div class="news-meta">${_esc(n.source||"")} · ${new Date((n.datetime||0)*1000).toLocaleDateString("tr-TR")}</div>
            </div>
          </a>`).join("");
      })
      .catch(showExternal);
  } else {
    showExternal();
  }
}

/* ---- Hisse detay sayfası (BIST) ---- */
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

  const dims      = stock.dimensions || {};
  const vColor    = _verdictColor(stock.verdict_key);
  const score     = stock.score ?? null;
  const ringDeg   = score != null ? score * 3.6 : 0;
  const isWatched = typeof Watchlist !== "undefined" && Watchlist.has(stock.symbol);

  const dimNames   = { valuation:"Değerleme", profit:"Kârlılık", growth:"Büyüme", health:"Finansal Sağlık", technical:"Teknik/Momentum", analyst:"Analist Görüşü" };
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

  const m = {};
  for (const [, d] of Object.entries(dims)) Object.assign(m, d.metrics || {});
  const fmtPct = v => (v != null ? (v >= 0 ? "+" : "") + v.toFixed(1) + "%" : "—");
  const fmtFx  = v => (v != null ? v.toFixed(2) + "×" : "—");
  const metrics = [
    ["F/K (TTM)",      fmtFx(m.pe)],
    ["PD/DD",          fmtFx(m.pb)],
    ["ROE",            fmtPct(m.roe)],
    ["Gelir Büyümesi", fmtPct(m.rev_growth)],
    ["Cari Oran",      fmtFx(m.current_ratio)],
    ["Borç/Özkaynak",  fmtFx(m.debt_equity)],
    ["52H Getiri",     fmtPct(m.ret52)],
    ["52H Bant Konum", m.range_pos != null ? "%" + m.range_pos.toFixed(0) : "—"],
  ].map(([l, v]) => `<div class="metric"><div class="label">${l}</div><div class="val">${v}</div></div>`).join("");

  const { pros, cons } = _autoProscons(dims);
  const prosHtml = pros.length
    ? pros.map(p => `<div class="pc-item pro"><div class="ic">+</div><div>${p}</div></div>`).join("")
    : `<div class="pc-empty">Öne çıkan güçlü yön tespit edilmedi.</div>`;
  const consHtml = cons.length
    ? cons.map(c => `<div class="pc-item con"><div class="ic">!</div><div>${c}</div></div>`).join("")
    : `<div class="pc-empty">Belirgin risk öne çıkmıyor.</div>`;

  const chg    = stock.change_pct;
  const up     = (chg ?? 0) >= 0;
  const chgStr = chg != null ? `${up ? "▲" : "▼"} ${Math.abs(chg).toFixed(2)}%` : "";

  content.style.display = "";
  content.innerHTML = `
    <div class="card">
      <div style="display:flex;align-items:center;gap:6px;font-size:12px;margin-bottom:16px;padding-bottom:12px;border-bottom:1px solid var(--border)">
        <span onclick="App.goHome()" style="color:var(--accent);cursor:pointer"
              onmouseover="this.style.opacity='.7'" onmouseout="this.style.opacity='1'">📊 Tarayıcı</span>
        <span style="color:var(--muted)">›</span>
        <span style="color:var(--text);font-weight:600">${_esc(stock.symbol)}</span>
        <button onclick="App.toggleWatchDetail('${_esc(stock.symbol)}',this)"
                class="star-btn-detail" style="margin-left:auto"
                title="${isWatched ? "İzlemeden çıkar" : "İzlemeye ekle"}"
        >${isWatched ? "⭐" : "☆"}</button>
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
      </div>
    </div>

    <div class="card"><h2>Boyut Bazlı Skorlama</h2>${dimBars}</div>

    <div class="grid2">
      <div class="card"><h2>✅ Güçlü Yönler</h2><div class="pc-list">${prosHtml}</div></div>
      <div class="card"><h2>⚠️ Zayıf Yönler / Riskler</h2><div class="pc-list">${consHtml}</div></div>
    </div>

    <div class="card"><h2>Temel Veriler</h2><div class="metrics">${metrics}</div></div>

    <div class="card">
      <h2>📈 Fiyat Grafiği</h2>
      <div id="tv_chart_widget" style="min-height:390px;border-radius:8px;overflow:hidden"></div>
    </div>

    <div class="card">
      <h2>📰 Haberler</h2>
      <div id="bistNewsSection"><div style="color:var(--muted);font-size:13px">Yükleniyor…</div></div>
    </div>

    <div class="disclaimer">⚠️ Bu skor; halka açık temel ve teknik verilerden otomatik, kural tabanlı bir hesaplamadır. Yatırım tavsiyesi değildir.</div>`;

  loadTVWidget(stock.symbol, stock.exchange || "BIST");
  loadBISTNews(stock.symbol);
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

  ["portfolioSection","alarmsSection","dividendSection"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = "none";
  });
  const contentEl = document.getElementById("content");

  const stocks = _reportData?.stocks || [];
  try {
    if (tab === "scanner") {
      if (contentEl) contentEl.style.display = "";
      let rd = document.getElementById("reportDashboard");
      if (!rd && contentEl) {
        contentEl.innerHTML = `<div id="reportDashboard"></div>`;
        rd = document.getElementById("reportDashboard");
      }
      if (rd) { rd.style.display = ""; renderReportStocks(stocks); }
    } else {
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
  const si = document.getElementById("searchInput");
  if (si) si.value = "";
  try { UI.hideSuggestions(); } catch {}
  const scannerBtn = document.querySelector(".tab");
  switchTab("scanner", scannerBtn);
}

const App = {
  switchTab,
  refresh,
  goHome,
  showDetail: (index) => {
    const stocks = _reportData?.stocks || [];
    _showStockDetail(stocks[index]);
  },
  toggleWatch: (symbol, event) => {
    if (typeof Watchlist === "undefined") return;
    const nowWatched = Watchlist.toggle(symbol);
    const btn = event?.target?.closest ? event.target.closest("button") : event?.target;
    if (btn) btn.textContent = nowWatched ? "⭐" : "☆";
    if (_scannerRefresh) _scannerRefresh();
  },
  toggleWatchDetail: (symbol, btn) => {
    if (typeof Watchlist === "undefined") return;
    const nowWatched = Watchlist.toggle(symbol);
    if (btn) {
      btn.textContent = nowWatched ? "⭐" : "☆";
      btn.title = nowWatched ? "İzlemeden çıkar" : "İzlemeye ekle";
    }
  },
};

document.addEventListener("DOMContentLoaded", initDashboard);

/* ============================================================
   Orkestrasyon — API → Analyzer → UI akışı
   ============================================================ */
(() => {
  const keyInput    = document.getElementById("apiKey");
  const saveBtn     = document.getElementById("saveKey");
  const searchInput = document.getElementById("searchInput");
  const chips       = document.getElementById("chips");

  if (FinnhubAPI.hasKey()) { keyInput.value = FinnhubAPI.key; markSaved(); }
  function markSaved() { saveBtn.textContent = "✓ Kayıtlı"; saveBtn.classList.add("key-ok"); }
  saveBtn.addEventListener("click", () => { if (FinnhubAPI.setKey(keyInput.value)) markSaved(); });

  CONFIG.POPULAR.forEach((sym) => {
    const c = document.createElement("div");
    c.className = "chip"; c.textContent = sym;
    c.onclick = () => loadSymbol(sym);
    chips.appendChild(c);
  });

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
      const data  = await FinnhubAPI.search(q);
      const items = (data.result || []).filter((r) => r.type === "Common Stock" || r.type === "").slice(0, 8);
      UI.renderSuggestions(items, (sym) => {
        searchInput.value = sym; UI.hideSuggestions(); loadSymbol(sym);
      });
    } catch { /* sessiz geç */ }
  }

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

      const m        = metricRes?.metric || {};
      const analysis = Analyzer.analyze(m, quote, rec);
      UI.renderAnalysis(symbol, quote, profile, m, rec, analysis);

      FinnhubAPI.companyNews(symbol)
        .then((news) => UI.renderNews((news || []).filter((n) => n.headline).slice(0, 6)))
        .catch(() => UI.newsError());
    } catch (e) {
      UI.renderError(e.message, symbol);
    }
  }

  const params  = new URLSearchParams(location.search);
  const initial = params.get("symbol");
  if (initial && FinnhubAPI.hasKey()) loadSymbol(initial);
})();
