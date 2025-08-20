
/**
 * PROCONSI – UI bridge for /api/tanques_norm
 * -----------------------------------------------------------
 * 1) Llama al backend Flask y mapea los campos a un modelo
 *    genérico que suelen usar los front originales.
 * 2) Si existe window.setData (tu front), se lo pasamos tal cual.
 * 3) Si NO existe, pintamos una cuadricula básica como fallback.
 * 
 * Puedes borrar el fallback cuando confirmes que setData() recibe bien los datos.
 */
(function () {
  const fmt = (v, suf="") => (v===null || v===undefined || isNaN(v)) ? "-" : `${v}${suf}`;
  const el = (html) => {
    const t = document.createElement("template");
    t.innerHTML = html.trim();
    return t.content.firstElementChild;
  };

  async function load() {
    const res = await fetch("/api/tanques_norm", { cache: "no-store" });
    const payload = await res.json();
    const rows = payload.rows || payload || [];

    // Adaptador -> modelo que muchos JS esperan
    const mapped = rows.map(r => {
      const cap = Number(r.capacidad_l || 0);
      const vol = Number(r.stock_l || 0);
      const pct = cap > 0 ? Math.max(0, Math.min(100, Math.round((vol / cap) * 100))) : 0;
      const disp = Math.max(0, cap - vol);
      const temp = (r.temp_ultima_c === "" || r.temp_ultima_c === null) ? null : Number(r.temp_ultima_c);
      return {
        id: r.tanque_id,
        codigo: r.tanque_codigo,
        almacen_id: r.almacen_id,
        almacen: r.almacen_nombre,
        nombre: r.descripcion || "TANQUE",
        producto: r.producto_nombre || "-",
        capacidad_l: cap,
        volumen_l: vol,
        disponible_l: disp,
        temperatura_c: temp,
        agua_l: null,          // No disponible en /api/tanques_norm
        porcentaje: pct,
        estado: "ok"           // Puedes calcularlo con umbrales si lo necesitas
      };
    });

    // 1) Si tu front define setData(), úsalo
    if (typeof window.setData === "function") {
      try {
        window.setData(mapped);
        return;
      } catch (err) {
        console.error("setData() falló, uso fallback:", err);
      }
    }

    // 2) Fallback ligero (no interfiere con tus estilos)
    const host =
      document.getElementById("gridTanques") ||
      document.querySelector("#grid, .grid, main") ||
      document.body;

    // Limpia y pinta
    host.innerHTML = "";
    const grid = el(`<div class="gridTanques" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(360px,1fr));gap:16px;"></div>`);
    host.appendChild(grid);

    for (const t of mapped) {
      const card = el(`
        <div class="tank card">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:.5rem;">
            <div style="font-weight:700;">${t.nombre}</div>
            <div style="display:flex;align-items:center;gap:.5rem;">
              <span style="width:8px;height:8px;border-radius:50%;background:#23c552;display:inline-block;"></span>
              <small>OK</small>
            </div>
          </div>
          <div style="display:flex;gap:16px;align-items:center;">
            <div style="position:relative;width:96px;height:160px;border-radius:12px;background:linear-gradient(180deg,#0b2a3a,#142b3a);overflow:hidden;">
              <div class="fill" style="position:absolute;bottom:0;left:0;right:0;height:${t.porcentaje}%;background:linear-gradient(180deg,rgba(0,153,255,.6),rgba(0,55,128,.9));transition:height .6s ease;"></div>
              <div style="position:absolute;top:6px;right:6px;background:rgba(0,0,0,.5);border-radius:6px;padding:2px 6px;">
                <small><strong>${t.porcentaje}%</strong></small>
              </div>
            </div>
            <div style="flex:1;">
              <div style="display:grid;grid-template-columns:1fr auto;row-gap:4px;column-gap:8px;font-size:.95rem;">
                <span>Volumen</span>    <strong>${fmt(t.volumen_l," L")}</strong>
                <span>Capacidad</span>  <strong>${fmt(t.capacidad_l," L")}</strong>
                <span>Disponible</span> <strong>${fmt(t.disponible_l," L")}</strong>
                <span>Producto</span>   <strong>${t.producto || "-"}</strong>
                <span>Temp.</span>      <strong>${t.temperatura_c===null? "-": `${t.temperatura_c} °C`}</strong>
                <span>Agua</span>       <strong>${fmt(t.agua_l," L")}</strong>
              </div>
            </div>
          </div>
        </div>
      `);
      grid.appendChild(card);
    }
  }

  // Auto-carga y botón "Refrescar" si existe
  document.addEventListener("DOMContentLoaded", () => {
    load();
    const btn = document.querySelector('[data-action="refresh"], button#refresh, .btn-refresh');
    if (btn) btn.addEventListener("click", load);
  });
})();

