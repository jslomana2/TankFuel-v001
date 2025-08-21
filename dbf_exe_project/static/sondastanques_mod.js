
/**
 * PROCONSI – Tanques (Vista avanzada)
 * Data adapter + fallback renderer
 */
(function () {
  const cfg = (window.PROCONSI_CONFIG = Object.assign(
    {
      endpoint: "/api/tanques_norm",
      refreshMs: 15000,
      mountId: "proconsiTankRoot",
      locale: "es-ES",
    },
    window.PROCONSI_CONFIG || {}
  ));
  const state = { timer: null };

  function formatNumber(n, digits = 0) {
    if (n === null || n === undefined || Number.isNaN(n)) return "-";
    try {
      return new Intl.NumberFormat(cfg.locale, {
        maximumFractionDigits: digits,
        minimumFractionDigits: digits,
      }).format(n);
    } catch (e) { return String(n); }
  }

  function normalizeRow(r) {
    const capacidad = Number(r.capacidad_l || 0);
    const vol = Number(r.stock_l || 0);
    const vol15 = Number(r.stock15_l || 0);
    const pct = capacidad > 0 ? (vol / capacidad) * 100 : 0;
    const disponible = Math.max(capacidad - vol, 0);
    let estado = "normal";
    if (pct < 10) estado = "alarma";
    else if (pct < 20) estado = "atencion";
    return {
      almacen_id: r.almacen_id,
      almacen_nombre: r.almacen_nombre,
      tanque_id: r.tanque_id,
      tanque_codigo: r.tanque_codigo,
      descripcion: r.descripcion,
      producto_id: r.producto_id,
      producto_nombre: r.producto_nombre,
      capacidad_l: capacidad,
      stock_l: vol,
      stock15_l: vol15,
      temp_ultima_c: r.temp_ultima_c === "" ? null : Number(r.temp_ultima_c),
      porcentaje: pct,
      disponible_l: disponible,
      estado,
    };
  }

  async function fetchData() {
    const res = await fetch(cfg.endpoint, { cache: "no-store" });
    if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
    const data = await res.json();
    const rows = Array.isArray(data?.rows) ? data.rows.map(normalizeRow) : [];
    return rows;
  }

  function ensureMount() {
    let root = document.getElementById(cfg.mountId);
    if (!root) {
      root = document.createElement("div");
      root.id = cfg.mountId;
      const hdr = document.querySelector("header") || document.body.firstElementChild;
      if (hdr && hdr.parentNode) hdr.parentNode.insertBefore(root, hdr.nextSibling);
      else document.body.appendChild(root);
    }
    return root;
  }

  function dotColor(estado) {
    if (estado === "alarma") return "var(--bad, red)";
    if (estado === "atencion") return "var(--warn, orange)";
    return "var(--ok, #21c55d)";
  }

  function renderFallback(rows) {
    const root = ensureMount();
    root.classList.add("proconsi-grid");
    const cards = rows.map((t) => {
      const pct = Math.max(0, Math.min(100, t.porcentaje || 0));
      const temp = t.temp_ultima_c == null ? "-" : `${formatNumber(t.temp_ultima_c, 1)} ºC`;
      return `
      <div class="tank">
        <div class="tank-head">
          <div class="tank-title">${t.descripcion || "TANQUE"}</div>
          <div class="tank-status"><span class="dot" style="background:${dotColor(t.estado)}"></span> ${t.estado[0].toUpperCase()}${t.estado.slice(1)}</div>
        </div>
        <div class="tank-body">
          <div class="tank-gauge">
            <div class="gauge-col">
              <div class="gauge-bar"><div class="gauge-fill" style="height:${pct}%"></div></div>
              <div class="gauge-pct">${formatNumber(pct, 0)}%</div>
            </div>
          </div>
          <div class="tank-meta">
            <div><b>Volumen</b> <span>${formatNumber(t.stock_l, 0)} L</span></div>
            <div><b>Capacidad</b> <span>${formatNumber(t.capacidad_l, 0)} L</span></div>
            <div><b>Disponible</b> <span>${formatNumber(t.disponible_l, 0)} L</span></div>
            <div><b>Producto</b> <span>${t.producto_nombre || "-"}</span></div>
            <div><b>Temp.</b> <span>${temp}</span></div>
            <div><b>Agua</b> <span>-</span></div>
          </div>
        </div>
        <div class="tank-foot">
          <span class="chip"><span class="dot" style="background:var(--ok,green)"></span>Normal</span>
          <span class="chip"><span class="dot" style="background:var(--warn,orange)"></span>Atención</span>
          <span class="chip"><span class="dot" style="background:var(--bad,red)"></span>Alarma</span>
        </div>
      </div>`;
    }).join("");
    root.innerHTML = `<div class="tank-grid">${cards}</div>`;
  }

  function deliver(rows) {
    const hook = window.__PROCONSI_SET_TANQUES__;
    if (typeof hook === "function") {
      try { hook(rows); } catch (e) { console.error("Error en __PROCONSI_SET_TANQUES__:", e); }
    } else {
      renderFallback(rows);
    }
    const evt = new CustomEvent("proconsi:tanques", { detail: rows });
    window.dispatchEvent(evt);
  }

  async function cycle() {
    try {
      const rows = await fetchData();
      deliver(rows);
    } catch (e) {
      console.error("PROCONSI fetch error:", e);
    }
  }

  function start() { stop(); cycle(); state.timer = setInterval(cycle, cfg.refreshMs); }
  function stop() { if (state.timer) clearInterval(state.timer); state.timer = null; }

  // Minimal styles for fallback
  const style = document.createElement("style");
  style.textContent = `
  .proconsi-grid { margin-top: 12px; }
  .tank-grid { display: grid; grid-template-columns: repeat(auto-fill,minmax(360px,1fr)); gap: 16px; }
  .tank { border:1px solid #2a2f3a; border-radius: 12px; padding: 12px; background: rgba(20, 24, 33, 0.35); backdrop-filter: blur(6px); }
  .tank-head { display:flex; align-items:center; justify-content:space-between; margin-bottom:8px; }
  .tank-title { font-weight: 700; letter-spacing: .02em; }
  .tank-status { font-size: 12px; opacity: .9; }
  .dot { display:inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right:6px; vertical-align: -1px; }
  .tank-body { display:flex; gap: 12px; align-items: stretch; }
  .tank-gauge { display:flex; align-items:center; }
  .gauge-col { display:flex; flex-direction:column; align-items:center; gap: 6px; }
  .gauge-bar { width: 70px; height: 180px; border-radius: 14px; background: linear-gradient(180deg,#0c121a,#1f2b38); position: relative; overflow: hidden; box-shadow: inset 0 0 0 1px rgba(255,255,255,.06); }
  .gauge-fill { position:absolute; bottom:0; left:0; right:0; background: linear-gradient(180deg, rgba(120,170,255,.35), rgba(120,170,255,.8)); }
  .gauge-pct { font-weight:700; font-size: 12px; }
  .tank-meta { flex:1; display:grid; grid-template-columns: 1fr 1fr; gap: 4px 12px; align-content: start; }
  .tank-meta > div { display:flex; justify-content: space-between; font-size: 13px; border-bottom: 1px dashed rgba(255,255,255,.08); padding: 4px 0; }
  .tank-foot { margin-top: 6px; font-size: 12px; opacity: .9; display:flex; gap: 10px; }
  .chip { display:inline-flex; align-items:center; gap:6px; }
  `;
  document.head.appendChild(style);

  window.PROCONSI = Object.assign(window.PROCONSI || {}, { start, stop });

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
