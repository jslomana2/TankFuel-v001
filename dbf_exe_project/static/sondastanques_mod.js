
// sondastanques_mod.js (patch 2025-08-28)
(function () {
  const $app = document.getElementById("app");

  // Helpers ------------------------------------------------------------
  const get = (obj, candidates, def=null) => {
    for (const k of candidates) {
      if (obj && Object.prototype.hasOwnProperty.call(obj, k) && obj[k] != null) return obj[k];
      // allow case-insensitive
      const kk = Object.keys(obj || {}).find(x => x.toLowerCase() === String(k).toLowerCase());
      if (kk && obj[kk] != null) return obj[kk];
    }
    return def;
  };

  const safe = (v, alt="–") => (v === null || v === undefined || v === "" ? alt : v);

  const pct = (tank) => {
    let p = get(tank, ["porc","percent","porcentaje","ocupacion","pct","%","pct_ocup"]);
    if (p == null) {
      const vol = parseFloat(get(tank, ["volumen","stock","nivel","litros","cantidad_actual"], 0)) || 0;
      const cap = parseFloat(get(tank, ["capacidad","capmax","cap_max","maximo"], 0)) || 0;
      if (cap > 0) p = (vol / cap) * 100;
    }
    if (p == null || isNaN(p)) return null;
    return Math.max(0, Math.min(100, Number(p)));
  };

  const statusFromPct = (p) => {
    if (p === null) return {label:"–", icon:"•", class:"status-unknown"};
    if (p <= 20)  return {label:"Bajo",  icon:"⚠", class:"status-low"};
    if (p <= 50)  return {label:"Medio", icon:"•", class:"status-mid"};
    if (p <= 90)  return {label:"Alto",  icon:"•", class:"status-high"};
    return           {label:"Lleno", icon:"•", class:"status-full"};
  };

  const fmtPct = (p) => p==null ? "–" : `${p.toFixed(0)}%`;

  // DOM makers ---------------------------------------------------------
  const tankCard = (t) => {
    const nombre = safe(get(t, ["nombre","tanque","descripcion","id","tanque_id"], "Tanque"));
    const prod   = safe(get(t, ["producto","articulo","prod_descri","producto_desc"]));
    const vol    = get(t, ["volumen","stock","nivel","litros"], null);
    const cap    = get(t, ["capacidad","capmax","cap_max"], null);
    const percent = pct(t);
    const st   = statusFromPct(percent);

    // bar width
    const width = percent==null ? 0 : percent;

    const waterLitros = get(t, ["agua","litros_agua","water_liters"], 0);

    return `
      <div class="tank-card">
        <div class="tank-header">
          <span class="tank-name">${nombre}</span>
          <span class="tank-status ${st.class}">${st.icon} <b>${st.label}</b></span>
        </div>
        <div class="tank-product">${prod}</div>

        <div class="tank-bar">
          <div class="tank-bar-fill" style="width:${width}%"></div>
        </div>
        <div class="tank-stats">
          <span>Ocupación: <b>${fmtPct(percent)}</b></span>
          <span>Volumen: <b>${safe(vol,"–")}</b></span>
          <span>Capacidad: <b>${safe(cap,"–")}</b></span>
          <span class="water">Agua: <b>${safe(waterLitros,"–")}</b></span>
        </div>
      </div>
    `;
  };

  const almacGroup = (almacen, tanks) => {
    const nombreAlm = safe(get(almacen, ["nombre","poblacion","desc","descripcion","label"]));
    const codAlm = safe(get(almacen, ["codigo","cod","almacen","id"]));
    const title = `${codAlm} – ${nombreAlm}`.trim();
    const cards = tanks.map(tankCard).join("");
    // totales por producto
    const totalsByProd = {};
    for (const t of tanks) {
      const prod = safe(get(t, ["producto","prod","articulo","producto_desc"]),"–");
      const vol = parseFloat(get(t, ["volumen","stock","nivel","litros"], 0)) || 0;
      totalsByProd[prod] = (totalsByProd[prod] || 0) + vol;
    }
    const totalsHtml = Object.entries(totalsByProd).map(
      ([p,v]) => `<li><span>${p}</span><b>${v.toLocaleString("es-ES")}</b></li>`
    ).join("");

    return `
      <section class="almacen-group">
        <h3>${title}</h3>
        <div class="tank-grid">${cards}</div>
        <div class="almacen-totales">
          <h4>Totales por producto</h4>
          <ul>${totalsHtml}</ul>
        </div>
      </section>
    `;
  };

  const render = (groups) => {
    if (!groups || !groups.length) {
      $app.innerHTML = `<div class="empty">Sin datos para mostrar.</div>`;
      return;
    }
    $app.innerHTML = groups.map(g => almacGroup(g.header, g.tanks)).join("");
  };

  // Fetchers -----------------------------------------------------------
  async function fetchJson(url) {
    const r = await fetch(url, {cache:"no-store"});
    if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return await r.json();
  }

  async function load() {
    try {
      // 1) Almacenes
      const almacenes = await fetchJson(`/api/almacenes?n=200`);
      // Normalize array of almacenes
      const alms = Array.isArray(almacenes) ? almacenes : (almacenes.items || almacenes.data || []);

      // 2) For each almacen, get tanks
      const groups = [];
      for (const a of alms) {
        const cod = get(a, ["codigo","cod","almacen","id"]);
        if (!cod) continue;
        try {
          const tdata = await fetchJson(`/api/tanques_norm?almacen=${encodeURIComponent(cod)}&n=5`);
          const tanks = Array.isArray(tdata) ? tdata : (tdata.items || tdata.data || []);
          groups.push({ header: a, tanks });
        } catch (e) {
          console.error("Error cargando tanques de", cod, e);
          groups.push({ header: a, tanks: [] });
        }
      }
      render(groups);
    } catch (err) {
      console.error(err);
      $app.innerHTML = `<div class="error">Error cargando datos. Revisa el servidor.</div>`;
    }
  }

  document.addEventListener("DOMContentLoaded", load);
})();
