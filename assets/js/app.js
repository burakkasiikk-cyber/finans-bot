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
