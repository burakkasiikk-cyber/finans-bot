const MacroStrip = (() => {
  function renderMacro(macro) {
    if (!macro) return;
    const strip = document.getElementById("macroStrip");
    if (!strip) return;

    const items = [
      { label: "USD/TRY", value: macro.usd_try != null ? macro.usd_try.toFixed(4) : null },
      { label: "EUR/TRY", value: macro.eur_try != null ? macro.eur_try.toFixed(4) : null },
      { label: "Altın",   value: macro.gold_usd != null ? `$${macro.gold_usd.toFixed(0)}` : null },
      {
        label: "S&P 500",
        value: macro.sp500_change_pct != null
          ? `${macro.sp500_change_pct >= 0 ? "+" : ""}${macro.sp500_change_pct.toFixed(2)}%`
          : null,
        color: macro.sp500_change_pct != null
          ? (macro.sp500_change_pct >= 0 ? "var(--green)" : "var(--red)")
          : null
      },
      {
        label: "BIST 100",
        value: macro.bist100 != null ? macro.bist100.toFixed(0) : null,
        color: macro.bist100_change_pct != null
          ? (macro.bist100_change_pct >= 0 ? "var(--green)" : "var(--red)")
          : null
      },
      { label: "TR Faiz", value: macro.tr_interest_rate != null ? `%${macro.tr_interest_rate}` : null },
    ];

    strip.innerHTML = items
      .filter(i => i.value != null)
      .map(i => `
        <div class="macro-item">
          <span class="macro-label">${i.label}</span>
          <span class="macro-value" style="color:${i.color || "var(--text)"}">${i.value}</span>
        </div>`)
      .join('<div class="macro-sep">·</div>');
  }

  return { renderMacro };
})();
