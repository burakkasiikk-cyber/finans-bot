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

  /* --- Push bildirim --- */
  function canNotify() { return "Notification" in window; }

  function notifyIfTriggered(alarm) {
    if (!canNotify() || Notification.permission !== "granted") return;
    const key = `alm_notified_${alarm.id}`;
    if (sessionStorage.getItem(key)) return; // bu oturumda zaten bildirildi
    sessionStorage.setItem(key, "1");
    const dir = alarm.dir === "below" ? "altına düştü" : "üstüne çıktı";
    try {
      new Notification(`⚠️ Alarm: ${alarm.symbol}`, {
        body: `${alarm.symbol} fiyatı ${alarm.price} ${dir}!`,
        tag:  String(alarm.id),
        icon: "/finans-bot/assets/icon.png",
      });
    } catch { /* sessiz geç */ }
  }

  function requestNotification() {
    if (!canNotify()) { alert("Bu tarayıcı push bildirimlerini desteklemiyor."); return; }
    Notification.requestPermission().then(p => {
      const btn = document.getElementById("notifPermBtn");
      if (p === "granted") {
        if (btn) { btn.textContent = "🔔 Bildirimler Aktif"; btn.style.background = "var(--green)"; btn.style.color = "#000"; }
      } else {
        if (btn) btn.textContent = "🔕 İzin Reddedildi";
      }
    });
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
      if (triggered) notifyIfTriggered(a);
      return `
        <tr style="${triggered ? "background:rgba(255,214,0,.08)" : ""}">
          <td><strong>${a.symbol}</strong></td>
          <td>${sign} ${a.price}</td>
          <td>${cur != null ? cur.toFixed(2) : "—"}</td>
          <td>${triggered ? "🔔 Tetiklendi" : "⏳ Bekliyor"}</td>
          <td><button onclick="Alarms.remove(${a.id})" style="background:none;border:none;color:var(--red);cursor:pointer">✕</button></td>
        </tr>`;
    }).join("");

    const notifPerm = canNotify() ? Notification.permission : "denied";
    const notifBtnLabel = notifPerm === "granted" ? "🔔 Bildirimler Aktif" : "🔔 Bildirimlere İzin Ver";
    const notifBtnStyle = notifPerm === "granted"
      ? "background:var(--green);color:#000;border:none;border-radius:8px;padding:7px 14px;font-size:12px;font-weight:700;cursor:default"
      : "background:var(--accent);color:#fff;border:none;border-radius:8px;padding:7px 14px;font-size:12px;font-weight:600;cursor:pointer";

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
        <input id="al-price" type="number" placeholder="Hedef fiyat" step="0.01" style="width:140px" />
        <button onclick="Alarms.addFromUI()">Alarm Ekle</button>
      </div>
      <div style="display:flex;align-items:center;gap:12px;margin-top:14px;flex-wrap:wrap">
        <button id="notifPermBtn" onclick="Alarms.requestNotification()" style="${notifBtnStyle}"
                ${notifPerm === "granted" ? "disabled" : ""}>${notifBtnLabel}</button>
        <p style="font-size:11px;color:var(--muted);margin:0">
          Alarm tetiklendiğinde masaüstü bildirimi alırsınız. GitHub Actions ayrıca Telegram'a bildirim gönderir.
        </p>
      </div>`;
  }

  function addFromUI() {
    const sym   = document.getElementById("al-sym")?.value?.trim();
    const dir   = document.getElementById("al-dir")?.value;
    const price = document.getElementById("al-price")?.value;
    if (!sym || !price) { alert("Sembol ve fiyat zorunlu."); return; }
    add(sym, dir, price);
    if (typeof App !== "undefined") App.refresh();
  }

  return { render, add, remove, addFromUI, load, requestNotification };
})();
