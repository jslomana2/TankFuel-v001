
const $ = (q, el=document) => el.querySelector(q);
const $$ = (q, el=document) => Array.from(el.querySelectorAll(q));

const grid = $("#grid");
const btnRefresh = $("#btnRefresh");
const selAlmacen = $("#selAlmacen");
const chkAll = $("#chkAll");
const side = $("#sidepanel");
const spTitle = $("#sp_title");
const spMeta = $("#sp_meta");
const spark = $("#spark");
const spClose = $("#sp_close");

function fmt(x, empty="–") {
  if (x===null || x===undefined || x==="") return empty;
  if (typeof x === "number") {
    return x.toLocaleString("es-ES", {maximumFractionDigits: 0});
  }
  return x;
}

async function loadAlmacenes() {
  const r = await fetch(API.almacenes);
  const j = await r.json();
  selAlmacen.innerHTML = "";
  const opt0 = document.createElement("option");
  opt0.value = ""; opt0.textContent = "— Elige almacén —";
  selAlmacen.appendChild(opt0);
  if (j.ok) {
    j.data.forEach(a => {
      const o = document.createElement("option");
      o.value = a.codigo;
      o.textContent = `${a.codigo} · ${a.nombre}`;
      selAlmacen.appendChild(o);
    });
  }
}

async function loadTanques() {
  grid.textContent = "Cargando…";
  const alm = chkAll.checked ? null : (selAlmacen.value || null);
  const url = API.tanques(alm);
  const r = await fetch(url);
  const j = await r.json();
  if (!j.ok) {
    grid.textContent = "Error: " + j.error;
    return;
  }
  grid.innerHTML = "";
  if (!j.data.length) {
    grid.textContent = "Sin datos.";
    return;
  }
  j.data.forEach(t => {
    const div = document.createElement("article");
    div.className = "card";
    const h = document.createElement("h3");
    h.innerHTML = `<span>${t.nombre}</span><span class="badge" style="background:${t.color}22;border-color:${t.color}88">${t.articulo_nombre || t.articulo}</span>`;
    div.appendChild(h);

    const meta = document.createElement("div");
    meta.className = "meta";
    meta.innerHTML = `<span>Almacén: <strong>${fmt(t.almacen)}</strong></span>
                      <span>Cap: <strong>${fmt(t.capacidad)}</strong> L</span>
                      <span>Agua: <strong>${fmt(t.agua)}</strong> L</span>
                      <span>Temp: <strong>${fmt(t.temperatura)}</strong> ºC</span>`;
    div.appendChild(meta);

    const label = document.createElement("div");
    label.className = "label";
    label.innerHTML = `<span>Nivel: <strong>${fmt(t.litros)}</strong> L${t.litros15? ` · 15º: <strong>${fmt(t.litros15)}</strong> L` : ""}</span>
                       <span><strong>${t.porcentaje ? t.porcentaje.toFixed(1) : "–" }%</strong></span>`;
    div.appendChild(label);

    const bar = document.createElement("div");
    bar.className = "bar";
    const fill = document.createElement("div");
    fill.className = "fill";
    fill.style.background = t.color || "var(--accent)";
    fill.style.width = (t.porcentaje || 0) + "%";
    bar.appendChild(fill);
    div.appendChild(bar);

    div.addEventListener("click", () => openSidepanel(t));
    grid.appendChild(div);
  });
}

async function openSidepanel(tanque) {
  side.classList.remove("hidden");
  spTitle.textContent = `${tanque.nombre} · ${tanque.articulo_nombre || tanque.articulo || ""}`;
  spMeta.innerHTML = `Capacidad: <strong>${fmt(tanque.capacidad)}</strong> L · Agua: <strong>${fmt(tanque.agua)}</strong> L · Temp: <strong>${fmt(tanque.temperatura)}</strong> ºC`;
  await drawSpark(tanque.tanque_id);
}

async function drawSpark(tanqueId) {
  spark.innerHTML = "";
  const r = await fetch(API.calibraciones(tanqueId, 120));
  const j = await r.json();
  if (!j.ok) {
    spark.textContent = "Sin histórico.";
    return;
  }
  const pts = j.data.map(x => +x.litros || 0);
  if (!pts.length) {
    spark.textContent = "Sin histórico.";
    return;
  }
  const w = 400, h = 120, pad = 6;
  const min = Math.min(...pts), max = Math.max(...pts);
  const scaleX = (i) => pad + (i/(pts.length-1))*(w-2*pad);
  const scaleY = (v) => (h-pad) - ((v - min) / (max - min || 1)) * (h-2*pad);
  let d = `M ${scaleX(0)} ${scaleY(pts[0])}`;
  for (let i=1;i<pts.length;i++){
    d += ` L ${scaleX(i)} ${scaleY(pts[i])}`;
  }
  const path = document.createElementNS("http://www.w3.org/2000/svg","path");
  path.setAttribute("d", d);
  path.setAttribute("fill","none");
  path.setAttribute("stroke","currentColor");
  path.setAttribute("stroke-width","2");
  spark.appendChild(path);
}

spClose.addEventListener("click", () => side.classList.add("hidden"));
btnRefresh.addEventListener("click", loadTanques);
selAlmacen.addEventListener("change", loadTanques);
chkAll.addEventListener("change", loadTanques);

(async function init(){
  await loadAlmacenes();
  await loadTanques();
})();
