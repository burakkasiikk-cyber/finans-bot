/* ============================================================
   api.js — Finnhub API istemcisi
   Tüm ağ istekleri buradan geçer. Anahtar tarayıcıda
   (localStorage) saklanır; kaynak dosyaya gömülmez.
   ============================================================ */
const FinnhubAPI = {
  key: localStorage.getItem("finnhub_key") || "",

  setKey(k) {
    this.key = (k || "").trim();
    localStorage.setItem("finnhub_key", this.key);
    return this.key;
  },

  hasKey() { return !!this.key; },

  /** Ham istek. Hata kodlarını anlamlı Error mesajlarına çevirir. */
  async request(path) {
    if (!this.key) throw new Error("NO_KEY");
    const sep = path.includes("?") ? "&" : "?";
    const res = await fetch(`${CONFIG.API_BASE}${path}${sep}token=${encodeURIComponent(this.key)}`);
    if (res.status === 401 || res.status === 403) throw new Error("BAD_KEY");
    if (res.status === 429) throw new Error("RATE");
    if (!res.ok) throw new Error("HTTP_" + res.status);
    return res.json();
  },

  // --- Uç noktalar (hepsi ücretsiz planda çalışır) ---
  quote(symbol)          { return this.request(`/quote?symbol=${symbol}`); },
  profile(symbol)        { return this.request(`/stock/profile2?symbol=${symbol}`); },
  metrics(symbol)        { return this.request(`/stock/metric?symbol=${symbol}&metric=all`); },
  recommendation(symbol) { return this.request(`/stock/recommendation?symbol=${symbol}`); },
  search(q)              { return this.request(`/search?q=${encodeURIComponent(q)}`); },

  companyNews(symbol) {
    const to = new Date(), from = new Date();
    from.setDate(to.getDate() - 30);
    const d = (x) => x.toISOString().slice(0, 10);
    return this.request(`/company-news?symbol=${symbol}&from=${d(from)}&to=${d(to)}`);
  },
};
