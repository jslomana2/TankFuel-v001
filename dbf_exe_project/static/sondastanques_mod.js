
(async function(){
  const $ = (sel, ctx=document)=>ctx.querySelector(sel);
  const $$ = (sel, ctx=document)=>Array.from(ctx.querySelectorAll(sel));
  const grid = $("#grid");
  const sel = $("#almacenSel");
  const summary = $("#summary");
  const toggleAll = $("#allToggle");
  const refreshBtn = $("#refreshBtn");

  function fmt(n){ return Intl.NumberFormat('es-ES').format(Math.round(n)); }
  function pct(a,b){ if(!b) return 0; return Math.max(0, Math.min(100, (a/b)*100)); }

  async function fetchJSON(url){
    const r = await fetch(url);
    return r.json();
  }

  function renderAlmacenes(rows){
    const ids = [...new Set(rows.map(r => r.almacen_id || r.CODIGO || r.COD_ALM || r.CODIGO))].filter(Boolean);
    sel.innerHTML = ids.map(id => `<option value="${id}">${id}</option>`).join("");
  }

  function colorOf(row){
    // preferimos color del artículo (color_hex) ya calculado por backend
    if(row.color_hex) return row.color_hex;
    // si viene int
    if(typeof row.COLORPRODU !== "undefined"){
      const c = Number(row.COLORPRODU||0);
      const r = c & 0xFF, g = (c>>8)&0xFF, b=(c>>16)&0xFF;
      return `#${r.toString(16).padStart(2,'0')}${g.toString(16).padStart(2,'0')}${b.toString(16).padStart(2,'0')}`.toUpperCase();
    }
    return "#2AA8FF";
  }

  function render(rows){
    const almFilter = toggleAll.checked ? null : sel.value;
    const data = rows.filter(r => !almFilter || r.almacen_id===almFilter);
    grid.innerHTML = data.map(r => {
      const cap = Number(r.capacidad_l||0);
      const stock = Number(r.stock_l||0);
      const pp = pct(stock, cap);
      const col = colorOf(r);
      const fill = col;
      const fillLight = col + "88";

      return `<div class="card" style="--fill:${fill};--fillLight:${fillLight}">
        <div class="tankWrap">
          <div class="scale">
            <div class="tick"><span>100%</span><span class="line"></span></div>
            <div class="tick"><span>50%</span><span class="line"></span></div>
            <div class="tick"><span>0%</span><span class="line"></span></div>
          </div>
          <div class="tank">
            <div class="liquid" style="height:${pp}%">
              <div class="wave"></div>
              <div class="wave wave2"></div>
              <div class="wave wave3"></div>
            </div>
            <div class="gloss"></div>
            <div class="stripe"></div>
            <div class="pct">${pp.toFixed(0)}%</div>
          </div>
        </div>
        <div>
          <div class="name">${r.producto_nombre||""} · ${r.tanque_codigo||r.tanque_id||""}</div>
          <div class="kv">
            <div>Almacén</div><strong>${r.almacen_id||""}</strong>
            <div>Capacidad</div><strong>${fmt(cap)} L</strong>
            <div>Stock</div><strong>${fmt(stock)} L</strong>
            <div>Temp</div><strong>${(r.temp_ultima_c??"—")} °C</strong>
          </div>
        </div>
      </div>`;
    }).join("");

    const total = rows.reduce((a,r)=>a + Number(r.stock_l||0), 0);
    summary.textContent = `Tanques: ${rows.length} · Stock total: ${fmt(total)} L`;
  }

  async function load(){
    const alm = await fetchJSON("/api/almacenes");
    const tnq = await fetchJSON("/api/tanques_norm");
    renderAlmacenes(tnq.rows);
    render(tnq.rows);
  }

  refreshBtn.addEventListener("click", load);
  toggleAll.addEventListener("change", load);
  sel.addEventListener("change", load);

  load();
})();
