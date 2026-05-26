const Dividends = (() => {
  function render(stocksFromReport) {
    const el = document.getElementById("dividendSection");
    if (!el) return;

    const portfolioData = (typeof Portfolio !== "undefined")
      ? Portfolio.compute(stocksFromReport).entries
      : [];
    const now = new Date();

    const divs = [];
    for (const s of (stocksFromReport || [])) {
      if (!s.dividends || s.dividends.length === 0) continue;
      const qty = portfolioData.find(e => e.symbol === s.symbol)?.qty || 0;
      for (const d of s.dividends) {
        if (!d.exDate) continue;
        const exDate    = new Date(d.exDate);
        if (exDate < now) continue;
        const daysUntil = Math.ceil((exDate - now) / (1000 * 60 * 60 * 24));
        divs.push({
          symbol: s.symbol, exDate: d.exDate, amount: d.amount || 0,
          qty, daysUntil, estimated: qty * (d.amount || 0)
        });
      }
    }
    divs.sort((a, b) => new Date(a.exDate) - new Date(b.exDate));

    const rows = divs.map(d => `
      <tr ${d.daysUntil <= 7 ? 'style="background:rgba(255,214,0,.06)"' : ""}>
        <td><strong>${d.symbol}</strong></td>
        <td>${d.exDate}</td>
        <td>${d.daysUntil} gün</td>
        <td>$${d.amount.toFixed(4)}/hisse</td>
        <td>${d.qty ? "$" + d.estimated.toFixed(2) : "—"}</td>
      </tr>`).join("");

    el.innerHTML = `
      <h2 class="section-title">📅 Temettü Takvimi</h2>
      <table class="portfolio-table">
        <thead><tr><th>Hisse</th><th>Ex-Date</th><th>Kalan</th><th>Temettü</th><th>Tahmini Gelirim</th></tr></thead>
        <tbody>${rows || "<tr><td colspan='5' style='text-align:center;color:var(--muted)'>Yaklaşan temettü yok (veriler sabah raporuyla güncellenir).</td></tr>"}</tbody>
      </table>`;
  }

  return { render };
})();
