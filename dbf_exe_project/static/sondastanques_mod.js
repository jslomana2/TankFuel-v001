(function(){
  const $ = sel => document.querySelector(sel);
  const tanksGrid = $("#tanksGrid");
  const almacenSel = $("#almacenSel");
  const refreshBtn = $("#refreshBtn");
  const verTodosBtn = $("#verTodosBtn");
  const histInfo = $("#histInfo");
  const histTableBody = document.querySelector("#histTable tbody");

  let currentAlm = null;
  let allAlmacenes = [];

  function fmt(n, d=0){
    if(n===null || n===undefined || isNaN(n)) return "-";
    return Number(n).toLocaleString('es-ES', {maximumFractionDigits:d, minimumFractionDigits:d});
  }
  function clamp(v, mi, ma){return Math.min(ma, Math.max(mi, v));}

  async function loadAlmacenes(){
    const res = await fetch("/api/almacenes");
    const js = await res.json();
    allAlmacenes = js.rows || [];
    renderAlmacenSelector();
  }

  function renderAlmacenSelector(){
    almacenSel.innerHTML = "";
    const optAll = document.createElement("option");
    optAll.value = "";
    optAll.textContent = "Todos";
    almacenSel.appendChild(optAll);
    (allAlmacenes||[]).forEach(a=>{
      const o = document.createElement("option");
      o.value = a.CODIGO || a.almacen_id || a.codigo || "";
      o.textContent = (a.NOMBRE || a.nombre || o.value);
      almacenSel.appendChild(o);
    });
    almacenSel.value = currentAlm || "";
  }

  function stateClass(p){
    if(p >= 50) return "p-ok";
    if(p >= 20) return "p-warn";
    return "p-bad";
  }

  function ringSVG(percent, color){
    const p = clamp(percent, 0, 100);
    const r = 40, c = 2*Math.PI*r, off = c*(1-p/100);
    return `<svg width="92" height="92" viewBox="0 0 92 92" aria-hidden="true">
      <circle cx="46" cy="46" r="${r}" fill="none" stroke="#eef2f7" stroke-width="6"/>
      <circle cx="46" cy="46" r="${r}" fill="none" stroke="${color||'#3b82f6'}" stroke-width="6" 
              stroke-dasharray="${c.toFixed(2)}" stroke-dashoffset="${off.toFixed(2)}"
              transform="rotate(-90 46 46)"/>
    </svg>`;
  }

  function colorFrom(r){
    // preferimos color_hex del backend (derivado de FFARTI.COLORPRODU)
    if(r.color_hex) return r.color_hex;
    // fallback por nombre del producto
    const name = (r.producto_nombre||"").toUpperCase();
    if(name.includes("HVO")) return "#ff7f0e";
    if(name.includes("AD-BLUE") || name.includes("ADBLUE")) return "#1d4ed8";
    if(name.includes("GASOLEO A")) return "#10b981";
    if(name.includes("GASOLEO B")) return "#f59e0b";
    if(name.includes("GASOLEO C")) return "#ef4444";
    return "#3b82f6";
  }

  function tankCard(r){
    const cap = Number(r.capacidad_l||0);
    const stk = Number(r.stock_l||0);
    const pct = cap>0 ? (100*stk/cap) : 0;
    const color = colorFrom(r);
    const cls = stateClass(pct);
    const title = (r.descripcion||"").trim() || `Tanque ${r.tanque_codigo||""}`;
    const alm = r.almacen_id||"";
    const pid = r.producto_id||"";
    const pname = r.producto_nombre||"";
    const temp = r.temp_ultima_c!==undefined && r.temp_ultima_c!=="" ? `${fmt(r.temp_ultima_c,1)} °C` : "-";
    const tid = r.tanque_id || `${alm}-${r.tanque_codigo||""}`;

    const el = document.createElement("div");
    el.className = `tank ${cls}`;
    el.innerHTML = `
      <div class="bar-wrap" title="${fmt(pct,0)}%">
        ${ringSVG(pct, color)}
        <div class="fill">${fmt(pct,0)}%</div>
      </div>
      <div class="label">
        <h3>${title}</h3>
        <div class="meta">
          <b>${pname}</b> · ${fmt(stk,0)} / ${fmt(cap,0)} L · T: ${temp} <br/>
          <small>Almacén: ${alm} · Código: ${r.tanque_codigo||"-"}</small>
        </div>
      </div>`;
    el.addEventListener("click", ()=>loadHistorico(tid));
    return el;
  }

  async function loadTanques(){
    const url = currentAlm ? `/api/tanques_norm?almacen=${encodeURIComponent(currentAlm)}` : "/api/tanques_norm";
    const res = await fetch(url);
    const js = await res.json();
    const rows = js.rows || [];
    tanksGrid.innerHTML = "";
    if(!rows.length){
      const div = document.createElement("div");
      div.textContent = "No hay tanques para mostrar.";
      tanksGrid.appendChild(div);
      return;
    }
    rows.forEach(r => tanksGrid.appendChild(tankCard(r)));
  }

  async function loadHistorico(tanqueId){
    histInfo.textContent = `Cargando histórico ${tanqueId}…`;
    histTableBody.innerHTML = "";
    const res = await fetch(`/api/calibraciones/ultimas?tanque_id=${encodeURIComponent(tanqueId)}&n=20`);
    const js = await res.json();
    histInfo.textContent = `Registros: ${js.count||0}`;
    (js.rows||[]).forEach(r=>{
      const tr = document.createElement("tr");
      const fecha = (r.FECHAMOD || r.FECHA || "").toString().slice(0,19);
      tr.innerHTML = `
        <td>${fecha}</td>
        <td>${r.ALMACEN||""}</td>
        <td>${r.TANQUE||""}</td>
        <td>${r.DESCRI||r.ARTICULO||""}</td>
        <td>${(r.LITROS!==undefined)? fmt(r.LITROS,0) : "-"}</td>
        <td>${(r.TEMPERA!==undefined)? fmt(r.TEMPERA,1) : "-"}</td>`;
      histTableBody.appendChild(tr);
    });
  }

  // UI events
  refreshBtn.addEventListener("click", ()=>{
    loadTanques();
  });
  verTodosBtn.addEventListener("click", ()=>{
    currentAlm = null;
    almacenSel.value = "";
    loadTanques();
  });
  almacenSel.addEventListener("change", ()=>{
    currentAlm = almacenSel.value || null;
    loadTanques();
  });

  // boot
  (async function boot(){
    await loadAlmacenes();
    await loadTanques();
  })();
})();