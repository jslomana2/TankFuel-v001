(function(){
  const qs = (sel, root=document) => root.querySelector(sel);
  const qsa = (sel, root=document) => Array.from(root.querySelectorAll(sel));
  const grid = qs("#grid");
  const totales = qs("#totales");
  const almacenSel = qs("#almacenSel");
  const summary = qs("#summary");
  const refreshBtn = qs("#refreshBtn");
  const prevBtn = qs("#prevBtn");
  const nextBtn = qs("#nextBtn");

  let allArticulos = [];
  let byArticulo = new Map(); // key: CODIGO (producto_id) [opcionalmente (ALMACEN,CODIGO)]
  let byArticuloAlm = new Map(); // key: `${ALMACEN}|${CODIGO}`

  function winColorToHex(dec){
    try{
      if(dec === null || dec === undefined) return null;
      let n = Number(dec);
      if(!isFinite(n)) return null;
      if(n < 0) n = (n + (2**32)) % (2**32);
      const b = (n >> 16) & 0xFF, g = (n >> 8) & 0xFF, r = n & 0xFF;
      return `#${r.toString(16).padStart(2,'0')}${g.toString(16).padStart(2,'0')}${b.toString(16).padStart(2,'0')}`.toUpperCase();
    }catch(_){ return null; }
  }

  function colorFor(tank){
    // 1) buscar por (almacen, producto_id) en FFARTI
    const key = `${tank.almacen_id}|${tank.producto_id}`;
    const rec = byArticuloAlm.get(key) || byArticulo.get(tank.producto_id);
    if(rec && ("COLORPRODU" in rec)){
      const hex = winColorToHex(rec.COLORPRODU);
      if(hex) return hex;
    }
    // 2) fallback por producto_nombre
    const name = (tank.producto_nombre || "").toUpperCase();
    if(name.includes("GASOLEO A")) return "#3B82F6";
    if(name.includes("GASOLEO B")) return "#22C55E";
    if(name.includes("GASOLEO C")) return "#F59E0B";
    if(name.includes("HVO") || name.includes("NEXAR")) return "#EAB308";
    if(name.includes("AD-BLUE") || name.includes("ADBLUE")) return "#60A5FA";
    // 3) comodín
    return "#2AA8FF";
  }

  function computeFill(hex){
    // Devuelve {fill, fillLight} para CSS variables
    // simple: lighten/darken por mezcla
    function mix(c1, c2, p){
      const a = c1.match(/.{2}/g).map(h=>parseInt(h,16));
      const b = c2.match(/.{2}/g).map(h=>parseInt(h,16));
      const r = a.map((v,i)=>Math.round(v*(1-p)+b[i]*p));
      return r.map(v=>v.toString(16).padStart(2,"0")).join("").toUpperCase();
    }
    const base = hex.replace("#","");
    const dark = mix(base,"000000",0.35);
    const light = mix(base,"FFFFFF",0.45);
    return { fill:`#${dark}`, fillLight:`#${light}` };
  }

  function pct(n){ return Math.max(0, Math.min(100, n)); }

  function render(tanks){
    grid.innerHTML = "";
    let totalsByProduct = new Map();
    let almacenList = Array.from(new Set(tanks.map(t => t.almacen_id))).sort();
    if(almacenSel){
      almacenSel.innerHTML = almacenList.map(a => `<option value="${a}">${a}</option>`).join("");
    }
    for(const t of tanks){
      const cap = Number(t.capacidad_l||0);
      const stock = Number(t.stock_l||0);
      const perc = cap>0 ? (stock*100.0/cap) : 0;
      const hex = colorFor(t);
      const {fill, fillLight} = computeFill(hex);
      const card = document.createElement("div");
      card.className = "card";
      card.innerHTML = `
        <div class="tankWrap">
          <div class="scale">
            <div class="tick"><div class="line"></div>100%</div>
            <div class="tick"><div class="line"></div>75%</div>
            <div class="tick"><div class="line"></div>50%</div>
            <div class="tick"><div class="line"></div>25%</div>
            <div class="tick"><div class="line"></div>0%</div>
          </div>
          <div class="tank" style="--fill:${fill};--fillLight:${fillLight}">
            <div class="liquid" style="height:${pct(perc).toFixed(1)}%">
              <div class="wave"></div>
              <div class="wave wave2"></div>
              <div class="wave wave3"></div>
            </div>
            <div class="water" hidden></div>
            <div class="gloss"></div>
            <div class="stripe"></div>
            <div class="pct">${pct(perc).toFixed(1)}%</div>
          </div>
        </div>
        <div>
          <div class="name">${t.descripcion||"-"}</div>
          <div class="kv">
            <div>Almacén</div><strong>${t.almacen_id||"-"}</strong>
            <div>Producto</div><strong>${t.producto_nombre||t.producto_id||"-"}</strong>
            <div>Capacidad</div><strong>${cap.toLocaleString()} L</strong>
            <div>Stock</div><strong>${stock.toLocaleString()} L</strong>
            <div>Temp</div><strong>${(t.temp_ultima_c ?? "").toString()||"—"}</strong>
            <div>ID</div><strong>${t.tanque_id||"-"}</strong>
          </div>
        </div>
      `;
      grid.appendChild(card);

      const key = t.producto_nombre || t.producto_id || "Otros";
      const cur = totalsByProduct.get(key) || {litros:0, hex:hex};
      cur.litros += stock;
      totalsByProduct.set(key, cur);
    }

    // render totales chips
    totales.innerHTML = "";
    for(const [k,v] of totalsByProduct){
      const chip = document.createElement("span");
      chip.className = "tchip";
      chip.innerHTML = `<span class="sw" style="background:${v.hex}"></span><strong>${k}</strong> ${v.litros.toLocaleString()} L`;
      totales.appendChild(chip);
    }

    summary.textContent = `${tanks.length} tanques`;
  }

  async function fetchJSON(url){
    const r = await fetch(url);
    if(!r.ok) throw new Error(`${r.status} ${r.statusText}`);
    return await r.json();
  }

  async function loadArticulos(){
    const j = await fetchJSON("/api/articulos");
    allArticulos = j.rows || j;
    byArticulo.clear(); byArticuloAlm.clear();
    for(const a of allArticulos){
      const cod = (a.CODIGO||"").toString().trim();
      const alm = (a.ALMACEN||"").toString().trim();
      if(cod){
        byArticulo.set(cod, a);
        if(alm) byArticuloAlm.set(`${alm}|${cod}`, a);
      }
    }
  }

  async function loadAndRender(){
    summary.textContent = "Cargando…";
    try{
      await loadArticulos();
      const j = await fetchJSON("/api/tanques_norm");
      const rows = j.rows || j;
      // Si existe selector de almacén filtramos
      const selected = almacenSel && almacenSel.value ? almacenSel.value : null;
      const filtered = selected ? rows.filter(r => r.almacen_id === selected) : rows;
      render(filtered);
    }catch(err){
      console.error(err);
      summary.textContent = "Error cargando datos";
    }
  }

  refreshBtn && refreshBtn.addEventListener("click", loadAndRender);
  prevBtn && prevBtn.addEventListener("click", ()=>{
    const opts = Array.from(almacenSel.options).map(o=>o.value);
    const i = opts.indexOf(almacenSel.value);
    almacenSel.value = opts[Math.max(0, i-1)] || opts[0];
    loadAndRender();
  });
  nextBtn && nextBtn.addEventListener("click", ()=>{
    const opts = Array.from(almacenSel.options).map(o=>o.value);
    const i = opts.indexOf(almacenSel.value);
    almacenSel.value = opts[Math.min(opts.length-1, i+1)] || opts.at(-1);
    loadAndRender();
  });
  almacenSel && almacenSel.addEventListener("change", loadAndRender);

  window.addEventListener("load", loadAndRender);
})();