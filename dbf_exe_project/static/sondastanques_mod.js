(function(){
  const grid = document.getElementById("gridTanques");
  const selAlm = document.getElementById("selAlmacen");
  const btnRefresh = document.getElementById("btnRefresh");
  const histPanel = document.getElementById("histPanel");
  const histTankId = document.getElementById("histTankId");
  const histBody = document.querySelector("#histTable tbody");

  function decToHexColor(n){
    if(n === null || n === undefined || n === "" || isNaN(n)) return null;
    const val = parseInt(n,10);
    if(isNaN(val)) return null;
    let hex = val.toString(16);
    hex = hex.padStart(6,"0").slice(-6);
    return "#" + hex;
  }

  function pct(cap, stock){
    const c = parseFloat(cap || 0), s = parseFloat(stock || 0);
    if(c<=0) return 0;
    return Math.max(0, Math.min(100, (s/c)*100));
  }

  function statusColor(p){
    if(p >= 70) return "var(--ok)";
    if(p >= 30) return "var(--warn)";
    return "var(--bad)";
  }

  async function loadAlmacenes(){
    const r = await fetch("/api/almacenes");
    const j = await r.json();
    const codes = new Set();
    (j.rows || []).forEach(a=>{
      const code = (a.CODIGO || a.codigo || "").toString().padStart(4,"0");
      if(!codes.has(code)){
        const opt = document.createElement("option");
        opt.value = code;
        opt.textContent = `${code} · ${(a.NOMBRE || a.nombre || "Almacén")}`;
        selAlm.appendChild(opt);
        codes.add(code);
      }
    });
  }

  async function loadTanques(){
    grid.innerHTML = "<div class='muted'>Cargando tanques…</div>";
    const r = await fetch("/api/tanques_norm");
    const j = await r.json();
    const filter = selAlm.value;
    const rows = (j.rows || []).filter(t => !filter || (t.almacen_id||"") === filter);

    if(rows.length===0){
      grid.innerHTML = "<div class='muted'>Sin datos de tanques para ese almacén.</div>";
      return;
    }

    grid.innerHTML = "";
    rows.forEach(t => {
      const p = pct(t.capacidad_l, t.stock_l);
      const colProd = decToHexColor(t.color_produ) || "#999999";

      const card = document.createElement("div");
      card.className = "tank";
      card.innerHTML = `
        <div class="head">
          <div>
            <div class="title">${t.descripcion || "Tanque"} <span class="badge">${t.tanque_id||""}</span></div>
            <div class="subtitle">${t.almacen_id || ""} · ${t.producto_nombre || ""}</div>
          </div>
          <div title="Color de producto FFARTI.COLORPRODU" class="color-pill" style="background:${colProd}"></div>
        </div>
        <div class="bar"><span style="width:${p}%;background:${statusColor(p)}"></span></div>
        <div class="subtitle">Capacidad: ${t.capacidad_l||0} L · Stock: ${t.stock_l||0} L · Temp: ${t.temp_ultima_c||"-"} ºC</div>
      `;
      card.addEventListener("click", () => openHist(t.tanque_id));
      grid.appendChild(card);
    });
  }

  async function openHist(tanqueId){
    histTankId.textContent = tanqueId;
    histBody.innerHTML = "<tr><td colspan='7' class='muted'>Cargando histórico…</td></tr>";
    histPanel.classList.remove("hidden");
    const url = `/api/calibraciones/ultimas?tanque_id=${encodeURIComponent(tanqueId)}&n=10`;
    const r = await fetch(url);
    const j = await r.json();
    const rows = j.rows || [];
    if(rows.length===0){
      histBody.innerHTML = "<tr><td colspan='7' class='muted'>Sin registros.</td></tr>";
      return;
    }
    histBody.innerHTML = rows.map(x=>{
      const fecha = (x.fecha || x.FECHA || "").toString().split("T")[0].replace("00:00:00","").trim();
      const hora  = x.hora || x.HORA || "";
      const prod  = x.descri || x.DESCRI || "";
      const litros = x.litros || x.LITROS || 0;
      const litros15 = x.litros15 || x.LITROS15 || 0;
      const t = x.tempera || x.TEMPERA || "";
      const dens = x.densidad || x.DENSIDAD || "";
      return `<tr><td>${fecha}</td><td>${hora}</td><td>${prod}</td><td>${litros}</td><td>${litros15}</td><td>${t}</td><td>${dens}</td></tr>`;
    }).join("");
    window.scrollTo({top: document.body.scrollHeight, behavior: "smooth"});
  }

  btnRefresh.addEventListener("click", loadTanques);
  selAlm.addEventListener("change", loadTanques);

  // init
  loadAlmacenes().then(loadTanques);
})();
