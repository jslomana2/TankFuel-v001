const $ = (sel, el=document) => el.querySelector(sel);
const $$ = (sel, el=document) => Array.from(el.querySelectorAll(sel));

function statusFromPercent(p){
  if (p <= 20)  return {icon:"⚠", color:"var(--bad)",   text:"Bajo"};
  if (p <= 50)  return {icon:"●", color:"var(--warn)",  text:"Medio"};
  if (p <= 90)  return {icon:"●", color:"var(--ok)",    text:"Alto"};
  return               {icon:"●", color:"var(--very)",  text:"Muy alto"};
}

function tankCard(t){
  const pct = Number(t.porcentaje ?? 0);
  const s   = statusFromPercent(pct);

  return `
  <section class="card" data-tanque-id="${t.id ?? ""}">
    <h3>
      ${t.nombre ?? "TANQUE"}
      <span class="status">
        <span class="dot" style="background:${s.color}"></span>
        <span class="status-text">${s.text}</span>
      </span>
    </h3>

    <div class="tank-body">
      <div class="tank-fill" style="height:${pct}%"></div>
    </div>
    <span class="badge">${pct}%</span>

    <div class="row"><strong>Volumen</strong><span>${t.volumen ?? "–"} L</span></div>
    <div class="row"><strong>Capacidad</strong><span>${t.capacidad ?? "–"} L</span></div>
    <div class="row"><strong>Disponible</strong><span>${t.disponible ?? "–"} L</span></div>
    <div class="row"><strong>Producto</strong><span>${t.producto ?? "–"}</span></div>
    <div class="row"><strong>Temp.</strong><span>${t.temperatura ?? "–"} °C</span></div>
    <div class="row"><strong>Agua</strong><span>${t.agua ?? "–"} mm</span></div>
  </section>`;
}

async function fetchJSON(url){
  const r = await fetch(url);
  return r.ok ? r.json() : [];
}

async function loadTanques(){
  const sel = $('#sel-almacen');
  const almParam = sel.value ? `?almacen=${encodeURIComponent(sel.value)}` : "";
  const data = await fetchJSON(`/api/tanques_norm${almParam}`);
  const grid = $('#grid-tanques');
  grid.innerHTML = (data ?? []).map(tankCard).join("");
}

async function loadAlmacenes(){
  const sel = $('#sel-almacen');
  const almacenes = await fetchJSON('/api/almacenes');
  sel.innerHTML = `<option value="">Ver todos</option>` + (almacenes ?? []).map(a=>`<option value="${a.id}">${a.nombre}</option>`).join("");
}

document.addEventListener('DOMContentLoaded', async ()=>{
  await loadAlmacenes();
  await loadTanques();
  $('#btn-refresh').addEventListener('click', loadTanques);
  $('#sel-almacen').addEventListener('change', loadTanques);
});