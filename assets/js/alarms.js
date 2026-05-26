const Alarms = (() => {
  const STORE_KEY = "alarms_v1";

  function load()       { try { return JSON.parse(localStorage.getItem(STORE_KEY) || "[]"); } catch { return []; } }
  function save(alarms) { localStorage.setItem(STORE_KEY, JSON.stringify(alarms)); }

  function add(symbol, dir, price) {
    const alarms = load();
    alarms.push({ symbol: symbol.toUpperCase(), dir, price: +price, active: true, id: Date.now() });
    save(alarms);
  }

  function remove(id) {
    save(load().filter(a => a.id !== id));
    if (typeof App !== "undefined") App.refresh();
  }

  function render(stocksFromReport) {
    const el = document.getElementById("alarmsSection");
    if (!el) return;
    const alarms   = load();
    const priceMap = Object.fromEntries((stocksFromReport || []).map(s => [s.symbol, s.price]));

    const rows = alarms.map(a => {
      const cur       = priceMap[a.symbol];
      const sign      = a.dir === "below" ? "<" : ">";
      const triggered = cur != null && (
        (a.dir === "below" && cur < a.price) ||
        (a.dir === "above" && cur > a.price)
      );
      return `
        <tr style="${triggered ? "background:rgba(255,214,0,.08)" : ""}">
          <td><strong>${a.symbol}</strong></td>
          <td>${sign} $${a.price}</td>
          <td>${cur != null ? "$" + cur.toFixed(2) : "—"}</td>
          <td>${triggered ? "🔔 Tetiklendi" : "⏳ Bekliyor"}</td>
          <td><button onclick="Alarms.remove(${a.id})" style="background:none;border:none;color:var(--red);cursor:pointer">✕</button></td>
        </tr>`;
    }).join("");

    el.innerHTML = `
      <h2 class="section-title">🔔 Fiyat Alarmları</h2>
      <table class="portfolio-table">
        <thead><tr><th>Hisse</th><th>Kural</th><th>Anlık</th><th>Durum</th><th></th></tr></thead>
        <tbody>${rows || "<tr><td colspan='5' style='text-align:center;color:var(--muted)'>Alarm yok.</td></tr>"}</tbody>
      </table>
      <div class="portfolio-add">
        <input id="al-sym" placeholder="Sembol" style="width:100px" />
        <select id="al-dir" style="background:var(--panel);border:1px solid var(--border);color:var(--text);border-radius:6px;padding:6px 10px;font-size:12px">
          <option value="below">Altına düşünce</option>
          <option value="above">Üstüne çıkınca</option>
        </select>
        <input id="al-price" type="number" placeholder="Hedef fiyat ($)" step="0.01" style="width:140px" />
        <button onclick="Alarms.addFromUI()">Alarm Ekle</button>
      </div>
      <p style="font-size:11px;color:var(--muted);margin-top:8px">
        Alarmlar GitHub Actions tarafından her 30 dakikada kontrol edilir. Telegram'a bildirim gönderilir.
      </p>`;
  }

  function addFromUI() {
    const sym   = document.getElementById("al-sym")?.value?.trim();
    const dir   = document.getElementById("al-dir")?.value;
    const price = document.getElementById("al-price")?.value;
    if (!sym || !price) { alert("Sembol ve fiyat zorunlu."); return; }
    add(sym, dir, price);
    if (typeof App !== "undefined") App.refresh();
  }

  return { render, add, remove, addFromUI, load };
})();
