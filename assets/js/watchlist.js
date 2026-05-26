/* ============================================================
   watchlist.js — localStorage tabanlı izleme listesi
   ============================================================ */
const Watchlist = (() => {
  const KEY = "watchlist_v1";

  function load()     { try { return JSON.parse(localStorage.getItem(KEY) || "[]"); } catch { return []; } }
  function save(list) { localStorage.setItem(KEY, JSON.stringify(list)); }
  function has(sym)   { return load().includes(sym); }

  function toggle(sym) {
    const list = load();
    const idx  = list.indexOf(sym);
    if (idx >= 0) { list.splice(idx, 1); save(list); return false; }
    else          { list.push(sym);      save(list); return true;  }
  }

  function getAll() { return load(); }
  return { has, toggle, getAll };
})();
