const Portfolio = (() => {
  const STORE_KEY = "portfolio_v1";

  function load() {
    try { return JSON.parse(localStorage.getItem(STORE_KEY) || "[]"); }
    catch { return []; }
  }

  function save(entries) {
    localStorage.setItem(STORE_KEY, JSON.stringify(entries));
  }

  function addEntry(symbol, qty, buyPrice, buyDate) {
    const entries = load();
    entries.push({ symbol: symbol.toUpperCase(), qty: +qty, buyPrice: +buyPrice, buyDate });
    save(entries);
  }

  function removeEntry(index) {
    const entries = load();
    entries.splice(index, 1);
    save(entries);
  }

  function compute(stocksFromReport) {
    const entries = load();
    if (!entries.length) return { entries: [], total_cost: 0, total_value: 0, total_pnl: 0, total_pnl_pct: 0 };

    const priceMap   = {};
    const scoreMap   = {};
    const verdictMap = {};
    for (const s of stocksFromReport) {
      priceMap[s.symbol]   = s.price;
      scoreMap[s.symbol]   = s.score;
      verdictMap[s.symbol] = s.verdict;
    }

    let total_cost = 0, total_value = 0;
    const computed = entries.map((e, i) => {
      const current = priceMap[e.symbol];
      const cost    = e.qty * e.buyPrice;
      const value   = current != null ? e.qty * current : null;
      const pnl     = value != null ? value - cost : null;
      const pnl_pct = pnl != null ? (pnl / cost) * 100 : null;
      const score   = scoreMap[e.symbol];
      const verdict = verdictMap[e.symbol];

      if (value != null) { total_cost += cost; total_value += value; }

      let comment = "";
      if (pnl_pct != null && score != null) {
        const pnlStr = `${pnl_pct >= 0 ? "+" : ""}${pnl_pct.toFixed(1)}%`;
        if (pnl_pct > 20 && score < 45)
          comment = `${pnlStr} kârdasınız ancak skor düşük (${score}/100) — kâr realize etmeyi düşünün.`;
        else if (pnl_pct > 0 && score >= 60)
          comment = `${pnlStr} kârdasınız, skor güçlü (${score}/100) — tutun.`;
        else if (pnl_pct < -10 && score < 45)
          comment = `${pnlStr} zarardayken ${verdict} sinyali — zararı kesmek mantıklı olabilir.`;
        else if (pnl_pct < 0 && score >= 60)
          comment = `${pnlStr} zararda olsa da skor güçlü (${score}/100) — uzun vadede toparlanabilir.`;
        else
          comment = `${pnlStr} · Skor: ${score}/100 · ${verdict}`;
      }

      return { ...e, index: i, current, cost, value, pnl, pnl_pct, score, verdict, comment };
    });

    const total_pnl     = total_value - total_cost;
    const total_pnl_pct = total_cost > 0 ? (total_pnl / total_cost) * 100 : 0;
    return { entries: computed, total_cost, total_value, total_pnl, total_pnl_pct };
  }

  function buildComparisonBlock(totalPnlPct, macro) {
    if (!macro) return "";
    const sp  = macro.sp500_change_pct;
    const bi  = macro.bist100_change_pct;
    const fmt = (n) => n != null ? `${n >= 0 ? "+" : ""}${n.toFixed(2)}%` : "—";
    const color = (n) => n == null ? "" : n >= 0 ? "var(--green)" : "var(--red)";
    return `
      <div class="comparison-block">
        <h3 class="comparison-title">📊 Endeks Kıyaslaması (bugün)</h3>
        <div class="comparison-row">
          <span class="comp-label">Portföyünüz</span>
          <span class="comp-val" style="color:${color(totalPnlPct)}">${fmt(totalPnlPct)}</span>
        </div>
        <div class="comparison-row">
          <span class="comp-label">S&P 500</span>
          <span class="comp-val" style="color:${color(sp)}">${fmt(sp)}</span>
        </div>
        <div class="comparison-row">
          <span class="comp-label">BIST 100</span>
          <span class="comp-val" style="color:${color(bi)}">${fmt(bi)}</span>
        </div>
      </div>`;
  }

  function buildPnlChart(entries) {
    const withPnl = entries.filter(e => e.pnl_pct != null);
    if (!withPnl.length) return "";
    const maxAbs = Math.max(...withPnl.map(e => Math.abs(e.pnl_pct)), 1);
    const bars = withPnl.map(e => {
      const pct   = e.pnl_pct;
      const color = pct >= 0 ? "var(--green)" : "var(--red)";
      const w     = (Math.abs(pct) / maxAbs * 60).toFixed(1);
      const label = `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%`;
      return `
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:7px">
          <div style="width:52px;font-size:11px;font-weight:700;text-align:right;color:var(--text);flex-shrink:0">${e.symbol}</div>
          <div style="flex:1;background:var(--panel-2);border-radius:4px;height:18px;overflow:hidden">
            <div style="height:100%;width:${w}%;background:${color};opacity:.85;border-radius:4px;transition:width .5s ease"></div>
          </div>
          <div style="width:58px;font-size:11px;font-weight:700;color:${color}">${label}</div>
        </div>`;
    }).join("");
    return `<div class="card" style="margin-bottom:14px"><h2>📊 Getiri Grafiği</h2>${bars}</div>`;
  }

  function renderPortfolio(stocksFromReport, macro) {
    const container = document.getElementById("portfolioSection");
    if (!container) return;

    const result = compute(stocksFromReport);
    const fmt    = (n, dec = 2) => n != null ? n.toFixed(dec) : "—";
    const sign   = (n) => n >= 0 ? "+" : "";
    const color  = (n) => n == null ? "" : n >= 0 ? "var(--green)" : "var(--red)";

    const totalBlock = `
      <div class="portfolio-summary">
        <div class="p-stat"><span class="p-lbl">Toplam Değer</span><span class="p-val">$${fmt(result.total_value)}</span></div>
        <div class="p-stat"><span class="p-lbl">Maliyet</span><span class="p-val">$${fmt(result.total_cost)}</span></div>
        <div class="p-stat"><span class="p-lbl">Kâr/Zarar</span>
          <span class="p-val" style="color:${color(result.total_pnl)}">
            ${sign(result.total_pnl)}$${fmt(result.total_pnl)} (${sign(result.total_pnl_pct)}${fmt(result.total_pnl_pct)}%)
          </span>
        </div>
      </div>`;

    const comparisonBlock = buildComparisonBlock(result.total_pnl_pct, macro);
    const chartBlock      = buildPnlChart(result.entries);

    const rows = result.entries.map(e => `
      <tr>
        <td><strong>${e.symbol}</strong></td>
        <td>${e.qty}</td>
        <td>$${fmt(e.buyPrice)}</td>
        <td>$${fmt(e.current)}</td>
        <td style="color:${color(e.pnl_pct)}">${sign(e.pnl_pct)}${fmt(e.pnl_pct)}%</td>
        <td>${e.score != null ? e.score + "/100" : "—"}</td>
        <td style="font-size:11px;color:var(--muted);max-width:200px">${e.comment}</td>
        <td><button onclick="Portfolio.remove(${e.index})" style="background:none;border:none;color:var(--red);cursor:pointer">✕</button></td>
      </tr>`).join("");

    container.innerHTML = `
      <h2 class="section-title">💼 Kişisel Portföy</h2>
      ${totalBlock}
      ${chartBlock}
      ${comparisonBlock}
      <table class="portfolio-table">
        <thead><tr>
          <th>Hisse</th><th>Adet</th><th>Alış</th><th>Anlık</th>
          <th>P&L %</th><th>Skor</th><th>Yorum</th><th></th>
        </tr></thead>
        <tbody>${rows || "<tr><td colspan='8' style='text-align:center;color:var(--muted)'>Henüz hisse eklenmedi.</td></tr>"}</tbody>
      </table>
      <div class="portfolio-add">
        <input id="p-sym"   placeholder="Sembol (ör: AAPL)" />
        <input id="p-qty"   type="number" placeholder="Adet" min="1" />
        <input id="p-price" type="number" placeholder="Alış fiyatı ($)" step="0.01" />
        <input id="p-date"  type="date" />
        <button onclick="Portfolio.addFromUI()">Ekle</button>
      </div>`;
  }

  function addFromUI() {
    const sym   = document.getElementById("p-sym")?.value?.trim();
    const qty   = document.getElementById("p-qty")?.value;
    const price = document.getElementById("p-price")?.value;
    const date  = document.getElementById("p-date")?.value;
    if (!sym || !qty || !price) { alert("Sembol, adet ve fiyat zorunlu."); return; }
    addEntry(sym, qty, price, date);
    if (typeof App !== "undefined") App.refresh();
  }

  function remove(index) {
    removeEntry(index);
    if (typeof App !== "undefined") App.refresh();
  }

  return { renderPortfolio, addFromUI, remove, compute, buildComparisonBlock };
})();
